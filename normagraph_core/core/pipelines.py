"""
Fixed Pipelines (Phase 2)

Deterministic pipelines that execute legal reasoning.
These are NOT agentic - they are fixed, testable workflows.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PipelineType(Enum):
    """Fixed pipeline types"""
    P1_FACTUAL = "P1"  # Factual / Clarification
    P2_COMPARATIVE = "P2"  # Comparative / Evolution
    P3_RISK_ANALYSIS = "P3"  # Risk / Constitutionality
    P4_MULTI_DOMAIN = "P4"  # Multi-Domain Policy Impact
    P5_JUDICIAL_CONSTRAINT = "P5"  # Judicial Constraint / Precedent Validation


@dataclass
class PipelineConfig:
    """Configuration for a pipeline"""
    pipeline_id: PipelineType
    name: str
    description: str
    requires_risk_analysis: bool
    requires_timeline: bool
    requires_comparison: bool
    max_domains: int
    retrieval_top_k: int
    max_latency_ms: int


# Pipeline Definitions (Deterministic)
PIPELINES = {
    PipelineType.P1_FACTUAL: PipelineConfig(
        pipeline_id=PipelineType.P1_FACTUAL,
        name="Factual/Clarification",
        description="Simple factual queries, no risk analysis needed",
        requires_risk_analysis=False,
        requires_timeline=False,
        requires_comparison=False,
        max_domains=1,
        retrieval_top_k=15,
        max_latency_ms=2000
    ),
    PipelineType.P2_COMPARATIVE: PipelineConfig(
        pipeline_id=PipelineType.P2_COMPARATIVE,
        name="Comparative/Evolution",
        description="Compare policies over time, show evolution",
        requires_risk_analysis=False,
        requires_timeline=True,
        requires_comparison=True,
        max_domains=1,
        retrieval_top_k=30,
        max_latency_ms=3000
    ),
    PipelineType.P3_RISK_ANALYSIS: PipelineConfig(
        pipeline_id=PipelineType.P3_RISK_ANALYSIS,
        name="Risk/Constitutionality",
        description="Analyze legal risks, constitutional issues",
        requires_risk_analysis=True,
        requires_timeline=False,
        requires_comparison=False,
        max_domains=2,  # Core + judicial
        retrieval_top_k=25,
        max_latency_ms=3500
    ),
    PipelineType.P4_MULTI_DOMAIN: PipelineConfig(
        pipeline_id=PipelineType.P4_MULTI_DOMAIN,
        name="Multi-Domain Impact",
        description="Analyze impact across multiple policy domains",
        requires_risk_analysis=True,
        requires_timeline=True,
        requires_comparison=True,
        max_domains=3,
        retrieval_top_k=40,
        max_latency_ms=4000
    ),
    PipelineType.P5_JUDICIAL_CONSTRAINT: PipelineConfig(
        pipeline_id=PipelineType.P5_JUDICIAL_CONSTRAINT,
        name="Judicial Constraint",
        description="Validate policy against judicial precedents, check overruling status",
        requires_risk_analysis=True,
        requires_timeline=False,
        requires_comparison=False,
        max_domains=2,  # Core domain + judicial
        retrieval_top_k=30,  # Higher for judicial validation
        max_latency_ms=4000
    ),
}


class PipelineExecutor:
    """
    Executes fixed pipelines deterministically.
    
    This is where ALL legal reasoning happens.
    NO agentic behavior here - just deterministic execution.
    """
    
    def __init__(self, retrieval_service, llm_service, risk_analyzer, citation_generator):
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.risk_analyzer = risk_analyzer
        self.citation_generator = citation_generator
    
    def execute(
        self,
        pipeline_type: PipelineType,
        query: str,
        query_embedding: List[float],
        domains: List[str],
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Execute a fixed pipeline.
        
        Args:
            pipeline_type: Which pipeline to run
            query: User query
            query_embedding: Query embedding vector
            domains: List of domains to search
            filters: Additional filters
            
        Returns:
            Pipeline execution result
        """
        config = PIPELINES[pipeline_type]
        logger.info(f"Executing pipeline {config.name} for domains: {domains}")
        
        # Step 1: Parallel retrieval across domains
        # Map domains to verticals (education -> go/legal, etc.)
        domain_to_verticals = {
            "education": ["go", "legal", "scheme"],
            "healthcare": ["go", "legal"],
            "labor": ["go", "legal"],
            "agriculture": ["go", "scheme"],
            "constitution": ["legal", "judicial"],
            "judicial": ["judicial"]
        }
        
        all_chunks = []
        verticals_to_search = []
        for domain in domains:
            verticals = domain_to_verticals.get(domain, ["go", "legal"])
            verticals_to_search.extend(verticals)
        
        # Remove duplicates
        verticals_to_search = list(set(verticals_to_search))
        
        # Retrieve from all relevant verticals
        chunks = self.retrieval_service.retrieve(
            query=query,
            query_embedding=query_embedding,
            top_k=config.retrieval_top_k,
            verticals=verticals_to_search,
            filters=filters
        )
        all_chunks = chunks
        
        # Step 2: Rerank (if service supports it)
        if hasattr(self.retrieval_service, 'rerank') and len(all_chunks) > config.retrieval_top_k:
            all_chunks = self.retrieval_service.rerank(query, all_chunks, top_k=config.retrieval_top_k)
        elif len(all_chunks) > config.retrieval_top_k:
            # Simple truncation if no rerank available
            all_chunks = all_chunks[:config.retrieval_top_k]
        
        # Step 3: Generate timeline (if required)
        timeline = None
        if config.requires_timeline:
            timeline = self._generate_timeline(all_chunks)
        
        # Step 4: Generate comparison (if required)
        comparison = None
        if config.requires_comparison:
            comparison = self._generate_comparison(all_chunks, query)
        
        # Step 5: Generate answer
        # Check if service accepts timeline/comparison
        if hasattr(self.llm_service, 'generate_answer'):
            answer_result = self.llm_service.generate_answer(
                query=query,
                retrieved_chunks=all_chunks,
                query_type="factual"  # Default, can be enhanced
            )
        else:
            # Fallback if interface doesn't match
            answer_result = {
                "answer": "Answer generation service not available",
                "citations": [],
                "confidence": 0.0
            }
        
        # Step 6: Judicial constraint validation (P5 only)
        judicial_constraints = None
        if pipeline_type == PipelineType.P5_JUDICIAL_CONSTRAINT:
            judicial_constraints = self._validate_judicial_constraints(all_chunks)
        
        # Step 7: Risk analysis (if required)
        risk_assessment = None
        if config.requires_risk_analysis:
            risk_assessment = self.risk_analyzer.analyze(
                query=query,
                retrieved_chunks=all_chunks,
                answer=answer_result["answer"]
            )
            # Merge judicial constraints into risk assessment for P5
            if judicial_constraints and risk_assessment:
                risk_assessment["judicial_constraints"] = judicial_constraints
        
        # Step 7: Generate citations
        if hasattr(self.citation_generator, 'generate_citations'):
            citations = self.citation_generator.generate_citations(
                retrieved_chunks=all_chunks,
                answer=answer_result.get("answer", "")
            )
        else:
            citations = []
        
        result = {
            "answer": answer_result["answer"],
            "citations": citations,
            "risk_assessment": risk_assessment,
            "timeline": timeline,
            "comparison": comparison,
            "domains_used": domains,
            "chunks_retrieved": len(all_chunks),
            "pipeline": config.name
        }
        
        # Add judicial constraints for P5
        if judicial_constraints:
            result["judicial_constraints"] = judicial_constraints
        
        return result
    
    def _generate_timeline(self, chunks: List) -> List[Dict]:
        """Generate chronological timeline from chunks"""
        # Extract dates and sort
        timeline_items = []
        for chunk in chunks:
            date = chunk.metadata.get("date") or chunk.metadata.get("year")
            if date:
                timeline_items.append({
                    "date": str(date),
                    "title": chunk.metadata.get("title", chunk.metadata.get("subject", "Unknown")),
                    "doc_id": chunk.doc_id,
                    "excerpt": chunk.content[:150] if hasattr(chunk, 'content') else ""
                })
        
        # Sort by date
        timeline_items.sort(key=lambda x: x["date"])
        return timeline_items
    
    def _generate_comparison(self, chunks: List, query: str) -> Dict:
        """Generate comparison between documents"""
        # Group by document
        docs = {}
        for chunk in chunks:
            doc_id = chunk.doc_id
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "title": chunk.metadata.get("title", "Unknown"),
                    "date": chunk.metadata.get("date"),
                    "chunks": []
                }
            docs[doc_id]["chunks"].append(chunk)
        
        # Simple comparison structure
        return {
            "documents_compared": len(docs),
            "documents": list(docs.values())
        }
    
    def _validate_judicial_constraints(self, chunks: List) -> Dict:
        """
        Validate retrieved chunks against judicial precedents.
        
        Uses judgment_relations table to check:
        - Overruled judgments (should not be cited)
        - Binding strength (SC > HC > Tribunal)
        - Followed/distinguished relationships
        
        Returns:
            Dict with validation results and warnings
        """
        import os
        from google.cloud import bigquery
        
        # Get document IDs from chunks
        doc_ids = list(set([chunk.doc_id for chunk in chunks if hasattr(chunk, 'doc_id')]))
        
        if not doc_ids:
            return {
                "validated": False,
                "warnings": [],
                "overruled_docs": [],
                "binding_strength": {}
            }
        
        # Query BigQuery for judgment relations
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.warning("Cannot validate judicial constraints: GOOGLE_CLOUD_PROJECT not set")
            return {
                "validated": False,
                "warnings": ["BigQuery not configured for judicial validation"],
                "overruled_docs": [],
                "binding_strength": {}
            }
        
        try:
            client = bigquery.Client(project=project_id)
            dataset_id = f"{project_id}.policy_intelligence"
            
            # Check for overruled documents
            overrule_query = f"""
            SELECT DISTINCT
                jr.from_doc_id,
                jr.to_doc_id,
                jr.relation_type,
                d1.title AS overruled_title,
                d2.title AS overruling_title
            FROM `{dataset_id}.judgment_relations` jr
            JOIN `{dataset_id}.documents` d1 ON d1.document_id = jr.from_doc_id
            JOIN `{dataset_id}.documents` d2 ON d2.document_id = jr.to_doc_id
            WHERE jr.relation_type = 'overrules'
              AND jr.from_doc_id IN UNNEST(@doc_ids)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("doc_ids", "STRING", doc_ids)
                ]
            )
            
            query_job = client.query(overrule_query, job_config=job_config)
            overruled_results = list(query_job.result())
            
            # Get binding strength for judicial documents
            binding_query = f"""
            SELECT DISTINCT
                d.document_id,
                jm.binding_strength,
                jm.court,
                jm.bench_strength
            FROM `{dataset_id}.documents` d
            LEFT JOIN `{dataset_id}.judgments_metadata` jm ON jm.document_id = d.document_id
            WHERE d.document_id IN UNNEST(@doc_ids)
              AND d.doc_type = 'judgment'
            """
            
            query_job = client.query(binding_query, job_config=job_config)
            binding_results = list(query_job.result())
            
            # Build warnings
            warnings = []
            overruled_docs = []
            binding_strength = {}
            
            for row in overruled_results:
                warnings.append(
                    f"⚠️ Document '{row.overruled_title}' has been overruled by '{row.overruling_title}'. "
                    f"Do not cite the overruled judgment."
                )
                overruled_docs.append({
                    "doc_id": row.from_doc_id,
                    "title": row.overruled_title,
                    "overruled_by": row.to_doc_id,
                    "overruling_title": row.overruling_title
                })
            
            for row in binding_results:
                binding_strength[row.document_id] = {
                    "strength": row.binding_strength or "unknown",
                    "court": row.court or "unknown",
                    "bench_strength": row.bench_strength
                }
            
            return {
                "validated": True,
                "warnings": warnings,
                "overruled_docs": overruled_docs,
                "binding_strength": binding_strength,
                "documents_checked": len(doc_ids)
            }
            
        except Exception as e:
            logger.error(f"Error validating judicial constraints: {e}")
            return {
                "validated": False,
                "warnings": [f"Validation error: {str(e)}"],
                "overruled_docs": [],
                "binding_strength": {}
            }

