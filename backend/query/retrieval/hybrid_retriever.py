"""
Hybrid Retrieval System

Combines lexical search (BigQuery) and vector search (Qdrant)
using Reciprocal Rank Fusion (RRF) for optimal results.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from google.cloud import bigquery
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchRequest
import numpy as np

from backend.query.config import get_config
from backend.query.retrieval.authority_weights import calculate_authority_multiplier

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk"""
    chunk_id: str
    doc_id: str
    content: str
    metadata: Dict
    score: float
    source: str  # "lexical" or "vector"
    rank: int


class HybridRetriever:
    """
    Production-grade hybrid retrieval combining:
    - BigQuery full-text search (lexical)
    - Qdrant vector search (semantic)
    - Reciprocal Rank Fusion (RRF) for merging
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None
    ):
        self.config = get_config()
        
        # Initialize BigQuery client
        project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID must be set")
        
        key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if key_path and os.path.exists(key_path):
            self.bq_client = bigquery.Client.from_service_account_json(key_path, project=project_id)
        else:
            self.bq_client = bigquery.Client(project=project_id)
        
        self.dataset_id = f"{project_id}.policy_intelligence"
        
        # Initialize Qdrant client
        qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "")
        qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL must be set")
        
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )
        
        # Collection mapping
        self.collections = {
            "go": "government_orders",
            "legal": "legal_documents",
            "judicial": "judicial_documents",
            "data": "data_reports",
            "scheme": "schemes",
        }
        
        logger.info("HybridRetriever initialized")
    
    def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 20,
        verticals: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        source_priorities: Optional[List[str]] = None
    ) -> List[RetrievedChunk]:
        """
        Perform hybrid retrieval.
        
        Args:
            query: Query text
            query_embedding: Query embedding vector
            top_k: Number of results to return
            verticals: Document verticals to search (None = all)
            filters: Additional filters (temporal, jurisdictional, etc.)
            source_priorities: Priority order for document types
            
        Returns:
            List of RetrievedChunk objects, sorted by RRF score
        """
        verticals = verticals or ["go", "legal", "judicial", "scheme"]
        
        # Step 1: Lexical search (ABSOLUTE PRIMARY)
        lexical_results, candidate_document_ids = self._lexical_search(
            query, top_k * 2, verticals, filters
        )
        
        # 🔒 CHECK 1: Empty candidate set handling
        if not candidate_document_ids:
            logger.warning(
                f"Lexical search returned zero candidate documents for query: '{query[:50]}...'. "
                "No authoritative sources found. Returning empty results."
            )
            return []  # Return empty - do not call vector search or LLM
        
        # Deduplicate candidate document IDs (CHECK 2)
        candidate_document_ids = list(dict.fromkeys(candidate_document_ids))  # Preserves order
        if len(candidate_document_ids) != len(set(candidate_document_ids)):
            original_count = len(candidate_document_ids)
            candidate_document_ids = list(dict.fromkeys(candidate_document_ids))
            logger.debug(
                f"Deduplicated candidate document IDs: {original_count} -> {len(candidate_document_ids)}"
            )
        
        # Step 2: Judicial Constraint Filtering (BEFORE RANKING)
        # Remove overruled judgments so they never reach the LLM
        lexical_results, candidate_document_ids = self._apply_judicial_constraints(
            lexical_results, candidate_document_ids
        )
        
        # Step 3: Vector search (ENRICHMENT ONLY - restricted to candidate set)
        vector_results = self._vector_search(
            query_embedding, top_k * 2, verticals, filters, candidate_document_ids
        )
        
        # Merge using RRF
        merged = self._reciprocal_rank_fusion(
            lexical_results, vector_results, top_k
        )
        
        # Step 4: Authority & Binding-Strength Aware Ranking (AFTER RRF, BEFORE SOURCE PRIORITIES)
        # Apply authority multipliers to improve ranking quality
        merged = self._apply_authority_ranking(merged)
        
        # Apply source priorities if provided
        if source_priorities:
            merged = self._apply_source_priorities(merged, source_priorities)
        
        # Step 5: Logging & Transparency (Top 5 results for auditability)
        self._log_top_results(merged[:5])
        
        return merged[:top_k]
    
    def _lexical_search(
        self,
        query: str,
        top_k: int,
        verticals: List[str],
        filters: Optional[Dict]
    ) -> Tuple[List[RetrievedChunk], List[str]]:
        """
        Perform lexical search using BigQuery unified tables.
        
        🔒 CRITICAL: This is the ABSOLUTE PRIMARY source of candidate documents.
        No document may enter the candidate set unless it passes this filter.
        
        Args:
            query: Query text
            top_k: Number of results to return
            verticals: Document verticals (legacy, will be mapped to domains)
            filters: Additional filters (temporal, jurisdictional, etc.)
            
        Returns:
            Tuple of (List[RetrievedChunk], List[str] document_ids)
            - RetrievedChunk objects with enriched metadata
            - document_id[] candidate set for vector search filtering
        """
        results = []
        candidate_document_ids = []
        
        # Map verticals to domains (backward compatibility)
        # TODO: Remove verticals, use domains directly
        domains = self._map_verticals_to_domains(verticals)
        
        if not domains:
            logger.warning("No domains mapped from verticals, skipping lexical search")
            return results, candidate_document_ids
        
        try:
            # Build query terms for text search
            query_terms = [term.lower() for term in query.split() if len(term) > 3][:5]
            
            if not query_terms:
                logger.debug("No valid query terms for lexical search")
                return results, candidate_document_ids
            
            # Build WHERE conditions for text search
            text_conditions = " OR ".join([
                f"LOWER(c.text) LIKE '%{term}%'"
                for term in query_terms
            ])
            
            # Build query parameters
            query_params = []
            
            # Domain filter (HARD FILTER - mandatory)
            query_params.append(
                bigquery.ArrayQueryParameter("domains", "STRING", domains)
            )
            
            # Temporal filter (optional)
            date_filter = None
            if filters and "temporal" in filters:
                date_filter = filters["temporal"]
                query_params.append(
                    bigquery.ScalarQueryParameter("date_filter", "DATE", date_filter)
                )
            
            # Jurisdictional filter (optional)
            jurisdiction_filter = None
            if filters and "jurisdiction" in filters:
                jurisdiction_filter = filters["jurisdiction"]
                query_params.append(
                    bigquery.ScalarQueryParameter("jurisdiction_filter", "STRING", jurisdiction_filter)
                )
            
            # Build SQL query with unified tables
            # 🔒 CHECK 4: Query shape verification
            # - Predicates (status, primary_domain) are in WHERE clause (not post-filtered)
            # - JOINs are selective (document_id FK relationships, not cartesian)
            # - Filters applied at query time, not in application code
            # - Query plan should use partitioning on date if available
            query_sql = f"""
            SELECT 
                c.chunk_id,
                c.document_id,
                c.text as content,
                c.chunk_type,
                c.page_start,
                c.page_end,
                d.title,
                d.doc_type,
                d.domain,
                d.authority,
                d.jurisdiction,
                d.status,
                d.date,
                d.version,
                d.source_url,
                dm.primary_domain,
                dm.secondary_domains,
                -- Judicial metadata (if applicable)
                jm.court,
                jm.binding_strength,
                jm.bench_strength,
                jm.case_number,
                jm.ratio_present
            FROM `{self.dataset_id}.chunks` c
            JOIN `{self.dataset_id}.documents` d ON c.document_id = d.document_id
            JOIN `{self.dataset_id}.domain_mapping` dm ON d.document_id = dm.document_id
            LEFT JOIN `{self.dataset_id}.judgments_metadata` jm ON d.document_id = jm.document_id
            WHERE 
                -- HARD FILTER: primary_domain is mandatory (in WHERE, not post-filtered)
                dm.primary_domain IN UNNEST(@domains)
                -- Status filtering (active only) - in WHERE clause
                AND d.status = 'active'
                -- Text search - in WHERE clause
                AND ({text_conditions})
                -- Additional filters (temporal, jurisdictional, etc.) - in WHERE clause
                AND (@date_filter IS NULL OR d.date >= @date_filter)
                AND (@jurisdiction_filter IS NULL OR d.jurisdiction = @jurisdiction_filter)
            ORDER BY 
                -- Relevance scoring: primary domain first, then date
                CASE 
                    WHEN dm.primary_domain IN UNNEST(@domains) THEN 1
                    ELSE 2
                END,
                d.date DESC
            LIMIT @top_k
            """
            
            # Add top_k parameter
            query_params.append(
                bigquery.ScalarQueryParameter("top_k", "INT64", top_k)
            )
            
            # Configure query job
            job_config = bigquery.QueryJobConfig(
                query_parameters=query_params
            )
            
            # Execute query
            query_job = self.bq_client.query(query_sql, job_config=job_config)
            rows = query_job.result()
            
            # Process results
            # 🔒 CHECK 2: Deduplicate document IDs (preserve order, first appearance wins)
            seen_doc_ids = set()
            for i, row in enumerate(rows):
                doc_id = row.document_id
                chunk_id = row.chunk_id
                
                # Track candidate document IDs (for vector search filtering)
                # Deduplication: only add if not seen before (preserves order)
                if doc_id not in seen_doc_ids:
                    candidate_document_ids.append(doc_id)
                    seen_doc_ids.add(doc_id)
                
                # Build enriched metadata
                metadata = {
                    "chunk_type": row.chunk_type,
                    "page_start": row.page_start,
                    "page_end": row.page_end,
                    "title": row.title,
                    "doc_type": row.doc_type,
                    "domain": row.domain,
                    "primary_domain": row.primary_domain,
                    "secondary_domains": list(row.secondary_domains) if row.secondary_domains else [],
                    "authority": row.authority,
                    "jurisdiction": row.jurisdiction,
                    "status": row.status,
                    "date": str(row.date) if row.date else None,
                    "version": row.version,
                    "source_url": row.source_url,
                }
                
                # Add judicial metadata if available
                if row.court:
                    metadata.update({
                        "court": row.court,
                        "binding_strength": row.binding_strength,
                        "bench_strength": row.bench_strength,
                        "case_number": row.case_number,
                        "ratio_present": row.ratio_present,
                    })
                
                # Create RetrievedChunk
                chunk = RetrievedChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=row.content or "",
                    metadata=metadata,
                    score=1.0 / (i + 1),  # Simple rank-based score (will be improved)
                    source="lexical",
                    rank=i + 1
                )
                results.append(chunk)
            
            logger.info(
                f"Lexical search returned {len(results)} chunks from {len(candidate_document_ids)} documents "
                f"for domains: {domains}"
            )
            
        except Exception as e:
            logger.error(f"BigQuery lexical search failed: {e}", exc_info=True)
            # Check if unified tables exist, fall back to legacy if needed
            if "does not exist" in str(e) or "not found" in str(e).lower():
                logger.warning(
                    "Unified tables not found, falling back to legacy go_clauses. "
                    "This is a temporary fallback and should be removed after migration."
                )
                # Legacy fallback (will be removed)
                return self._lexical_search_legacy(query, top_k, verticals, filters)
            else:
                # Re-raise for other errors
                raise
        
        return results, candidate_document_ids
    
    def _apply_judicial_constraints(
        self,
        chunks: List[RetrievedChunk],
        candidate_document_ids: List[str]
    ) -> Tuple[List[RetrievedChunk], List[str]]:
        """
        Apply judicial constraints to filter out overruled judgments.
        
        This is Step 2 of the retrieval pipeline, executed BEFORE ranking.
        Overruled judgments must never reach the LLM.
        
        Args:
            chunks: List of retrieved chunks from lexical search
            candidate_document_ids: List of candidate document IDs
            
        Returns:
            Tuple of (filtered_chunks, filtered_document_ids)
        """
        if not candidate_document_ids:
            return chunks, candidate_document_ids
        
        # Log before count
        before_chunk_count = len(chunks)
        before_doc_count = len(candidate_document_ids)
        
        try:
            # Query judgment_relations to find overruled judgments
            # Find all document_ids that are overruled (to_doc_id where relation_type = 'overrules')
            # Use parameterized query to prevent SQL injection
            query_params = [
                bigquery.ArrayQueryParameter("candidate_doc_ids", "STRING", candidate_document_ids),
                bigquery.ScalarQueryParameter("relation_type", "STRING", "overrules")
            ]
            
            query_sql = f"""
            SELECT DISTINCT to_doc_id
            FROM `{self.dataset_id}.judgment_relations`
            WHERE relation_type = @relation_type
            AND to_doc_id IN UNNEST(@candidate_doc_ids)
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            query_job = self.bq_client.query(query_sql, job_config=job_config)
            rows = query_job.result()
            
            # Collect overruled document IDs
            overruled_doc_ids = set()
            for row in rows:
                overruled_doc_id = getattr(row, 'to_doc_id', None)
                if overruled_doc_id:
                    overruled_doc_ids.add(overruled_doc_id)
            
            # Filter out overruled document IDs from candidate set
            filtered_document_ids = [
                doc_id for doc_id in candidate_document_ids
                if doc_id not in overruled_doc_ids
            ]
            
            # Filter out chunks belonging to overruled documents
            filtered_chunks = [
                chunk for chunk in chunks
                if chunk.doc_id not in overruled_doc_ids
            ]
            
            # Log results
            after_chunk_count = len(filtered_chunks)
            after_doc_count = len(filtered_document_ids)
            removed_doc_ids = list(overruled_doc_ids)
            
            if overruled_doc_ids:
                logger.info(
                    f"Judicial constraint filtering: "
                    f"chunks {before_chunk_count} -> {after_chunk_count}, "
                    f"documents {before_doc_count} -> {after_doc_count}. "
                    f"Removed {len(overruled_doc_ids)} overruled judgment(s): {removed_doc_ids}"
                )
            else:
                logger.debug(
                    f"Judicial constraint check: No overruled judgments found. "
                    f"All {before_doc_count} documents are valid."
                )
            
            return filtered_chunks, filtered_document_ids
            
        except Exception as e:
            # If judgment_relations table doesn't exist or query fails, log and return original
            logger.warning(
                f"Judicial constraint check failed: {e}. "
                f"Returning unfiltered results. This should be fixed before production."
            )
            return chunks, candidate_document_ids
    
    def _lexical_search_legacy(
        self,
        query: str,
        top_k: int,
        verticals: List[str],
        filters: Optional[Dict]
    ) -> Tuple[List[RetrievedChunk], List[str]]:
        """
        Legacy lexical search using go_clauses table.
        
        ⚠️ DEPRECATED: This is a temporary fallback and will be removed.
        Emits WARN logs to track usage.
        """
        logger.warning(
            "Using legacy go_clauses table for lexical search. "
            "This should only happen during migration. Unified tables should be used."
        )
        
        results = []
        candidate_document_ids = []
        
        # Legacy implementation (minimal, just to prevent crashes)
        if "go" in verticals:
            try:
                query_terms = query.split()[:5]
                where_conditions = " OR ".join([
                    f"LOWER(clause_text) LIKE '%{term.lower()}%'"
                    for term in query_terms if len(term) > 3
                ])
                
                if where_conditions:
                    query_sql = f"""
                    SELECT 
                        clause_id as chunk_id,
                        go_id as doc_id,
                        clause_text as content
                    FROM `{self.dataset_id}.go_clauses`
                    WHERE {where_conditions}
                    LIMIT {top_k}
                    """
                    
                    query_job = self.bq_client.query(query_sql)
                    rows = query_job.result()
                    
                    for i, row in enumerate(rows):
                        doc_id = getattr(row, 'doc_id', '')
                        if doc_id and doc_id not in candidate_document_ids:
                            candidate_document_ids.append(doc_id)
                        
                        chunk = RetrievedChunk(
                            chunk_id=getattr(row, 'chunk_id', f"clause_{i}"),
                            doc_id=doc_id,
                            content=getattr(row, 'content', ''),
                            metadata={},
                            score=1.0 / (i + 1),
                            source="lexical",
                            rank=i + 1
                        )
                        results.append(chunk)
            except Exception as e:
                logger.debug(f"Legacy BigQuery lexical search failed: {e}")
        
        return results, candidate_document_ids
    
    def _map_verticals_to_domains(self, verticals: List[str]) -> List[str]:
        """
        Map legacy verticals to domains.
        
        ⚠️ DEPRECATED: This mapping is temporary and will be removed.
        ⚠️ REMOVAL DEADLINE: 30 days from implementation date (2024-01-XX)
        
        🔒 CHECK 3: This method emits WARN logs and should be tracked via metrics.
        
        Args:
            verticals: Legacy vertical list (e.g., ["go", "judicial"])
            
        Returns:
            List of domains (e.g., ["education", "judicial"])
        """
        # 🔒 CHECK 3: Log WARN every time this mapping is used
        logger.warning(
            f"⚠️ DEPRECATED: Using legacy vertical-to-domain mapping for verticals: {verticals}. "
            f"This should be replaced with direct domain usage. "
            f"REMOVAL DEADLINE: 30 days from implementation."
        )
        
        # TODO: Increment metric counter here (e.g., legacy_vertical_mapping_count)
        # Example: metrics.increment("retrieval.legacy_vertical_mapping", tags={"verticals": ",".join(verticals)})
        
        # Mapping: vertical -> primary domain
        vertical_to_domain = {
            "go": "education",  # Default GO domain
            "judicial": "judicial",
            "legal": "constitution",
            "scheme": "state_governance",
            "data": "finance",  # Reports often financial
        }
        
        domains = []
        for vertical in verticals:
            domain = vertical_to_domain.get(vertical)
            if domain and domain not in domains:
                domains.append(domain)
        
        # If no mapping found, default to education
        if not domains:
            domains = ["education"]
            logger.warning(
                f"⚠️ No domain mapping for verticals {verticals}, defaulting to 'education'. "
                f"This indicates a missing vertical mapping."
            )
        
        return domains
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int,
        verticals: List[str],
        filters: Optional[Dict],
        candidate_document_ids: Optional[List[str]] = None
    ) -> List[RetrievedChunk]:
        """
        Perform vector search using Qdrant (ENRICHMENT ONLY).
        
        🔒 CRITICAL: Vector search is restricted to candidate_document_ids from lexical search.
        Any results with document_ids not in the candidate set are DISCARDED.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            verticals: Document verticals (legacy, for collection mapping)
            filters: Additional filters (temporal, jurisdictional, etc.)
            candidate_document_ids: Document IDs from lexical search (AFTER judicial filtering)
                                   Vector search is restricted to these IDs only.
        """
        all_results = []
        
        # Enforce BigQuery-first contract
        if not candidate_document_ids:
            logger.warning(
                "No candidate document IDs provided to vector search. "
                "Vector search cannot expand recall beyond lexical candidates."
            )
            return all_results
        
        # Convert to set for fast lookup
        candidate_set = set(candidate_document_ids)
        
        for vertical in verticals:
            collection = self.collections.get(vertical)
            if not collection:
                continue
            
            # Build Qdrant filter
            filter_conditions = []
            
            # CRITICAL: Restrict to candidate document IDs
            # Note: Qdrant doesn't support IN queries directly, so we'll filter after search
            # This is a limitation of current Qdrant setup - will be fixed in Vertex migration
            
            if filters:
                if "temporal" in filters:
                    date = filters["temporal"]
                    filter_conditions.append(
                        FieldCondition(
                            key="year",
                            match=MatchValue(value=int(date))
                        )
                    )
                
                if "jurisdiction" in filters:
                    jurisdiction = filters["jurisdiction"]
                    filter_conditions.append(
                        FieldCondition(
                            key="jurisdiction",
                            match=MatchValue(value=jurisdiction)
                        )
                    )
            
            qdrant_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            try:
                search_results = self.qdrant_client.search(
                    collection_name=collection,
                    query_vector=query_embedding,
                    query_filter=qdrant_filter,
                    limit=top_k * 2,  # Get more results, then filter
                    with_payload=True,
                    with_vectors=False
                )
                
                # ENFORCE: Discard any results not in candidate set
                filtered_count = 0
                for i, result in enumerate(search_results):
                    payload = result.payload or {}
                    doc_id = payload.get("doc_id", payload.get("document_id", ""))
                    
                    # CRITICAL ENFORCEMENT: Discard if not in candidate set
                    if doc_id not in candidate_set:
                        filtered_count += 1
                        continue
                    
                    chunk = RetrievedChunk(
                        chunk_id=payload.get("chunk_id", result.id),
                        doc_id=doc_id,
                        content=payload.get("content", payload.get("text", "")),
                        metadata=payload,
                        score=result.score,
                        source="vector",
                        rank=len(all_results) + 1
                    )
                    all_results.append(chunk)
                
                if filtered_count > 0:
                    logger.debug(
                        f"Filtered out {filtered_count} vector results not in candidate set "
                        f"(collection: {collection})"
                    )
            
            except Exception as e:
                logger.warning(f"Qdrant search failed for {collection}: {e}")
                continue
        
        # Sort by score and limit
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Log if we had to discard results (should be rare)
        if len(all_results) < top_k:
            logger.debug(
                f"Vector search returned {len(all_results)} results after candidate filtering "
                f"(requested: {top_k})"
            )
        
        return all_results[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        lexical_results: List[RetrievedChunk],
        vector_results: List[RetrievedChunk],
        top_k: int,
        k: int = 60
    ) -> List[RetrievedChunk]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score = sum(1 / (k + rank)) for each result set
        
        Args:
            lexical_results: Results from lexical search
            vector_results: Results from vector search
            top_k: Number of results to return
            k: RRF constant (typically 60)
        """
        # Build chunk_id -> RRF score mapping
        rrf_scores = {}
        chunk_map = {}
        
        # Process lexical results
        for chunk in lexical_results:
            chunk_id = chunk.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + chunk.rank)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk
        
        # Process vector results
        for chunk in vector_results:
            chunk_id = chunk.chunk_id
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1.0 / (k + chunk.rank)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk
        
        # Sort by RRF score
        merged = [
            chunk_map[chunk_id] for chunk_id in sorted(
                rrf_scores.keys(),
                key=lambda x: rrf_scores[x],
                reverse=True
            )
        ]
        
        # Update scores to RRF scores
        for chunk in merged:
            chunk.score = rrf_scores[chunk.chunk_id]
        
        return merged[:top_k]
    
    def _apply_source_priorities(
        self,
        chunks: List[RetrievedChunk],
        priorities: List[str]
    ) -> List[RetrievedChunk]:
        """
        Re-rank results based on source type priorities.
        
        Args:
            chunks: Retrieved chunks
            priorities: Ordered list of document types (e.g., ["judicial", "legal", "go"])
        """
        # Build priority map
        priority_map = {doc_type: i for i, doc_type in enumerate(priorities)}
        
        def get_priority(chunk: RetrievedChunk) -> int:
            vertical = chunk.metadata.get("vertical", "")
            return priority_map.get(vertical, 999)  # Unknown types get lowest priority
        
        # Sort by priority, then by score
        chunks.sort(key=lambda x: (get_priority(x), -x.score))
        
        return chunks
    
    def _apply_authority_ranking(
        self,
        chunks: List[RetrievedChunk]
    ) -> List[RetrievedChunk]:
        """
        Apply authority-aware ranking based on court and binding strength.
        
        This method reweights RRF scores using authority multipliers:
        - Supreme Court > High Court > Tribunal/Other
        - binding > persuasive > non_binding
        
        Rules:
        - No new retrieval
        - No new joins
        - Keeps lexical/vector signals intact, just reweights
        
        Args:
            chunks: Retrieved chunks (already merged via RRF)
            
        Returns:
            Re-ranked chunks sorted by authority-weighted score
        """
        # Apply authority multipliers to each chunk's score
        for chunk in chunks:
            court = chunk.metadata.get("court")
            binding_strength = chunk.metadata.get("binding_strength")
            
            # Calculate authority multiplier
            authority_multiplier = calculate_authority_multiplier(court, binding_strength)
            
            # Apply multiplier to existing RRF score
            chunk.score = chunk.score * authority_multiplier
        
        # Re-sort by authority-weighted score
        chunks.sort(key=lambda x: x.score, reverse=True)
        
        return chunks
    
    def _log_top_results(self, top_chunks: List[RetrievedChunk]) -> None:
        """
        Log top 5 results for auditability.
        
        Logs per request:
        - document_id
        - court
        - binding_strength
        - final score
        
        Args:
            top_chunks: Top N chunks (typically 5) from final ranking
        """
        if not top_chunks:
            logger.debug("No results to log for top results audit.")
            return
        
        logger.info("Top results (authority-aware ranking):")
        for i, chunk in enumerate(top_chunks, 1):
            court = chunk.metadata.get("court", "N/A")
            binding_strength = chunk.metadata.get("binding_strength", "N/A")
            doc_id = chunk.doc_id
            score = chunk.score
            
            logger.info(
                f"  {i}. doc_id={doc_id}, "
                f"court={court}, "
                f"binding_strength={binding_strength}, "
                f"final_score={score:.4f}"
            )

