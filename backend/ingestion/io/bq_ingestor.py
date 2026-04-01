import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import re

from backend.ingestion.io.bigquery_client import BigQueryClient

logger = logging.getLogger(__name__)


class BQIngestor:
    """
    Ingests processed document data from local files into BigQuery.
    
    DUAL-WRITE STRATEGY:
    - Writes to legacy GO tables (backward compatibility)
    - Writes to unified tables (documents, chunks, domain_mapping, etc.)
    - Unified tables are the source of truth for future systems
    
    STRICT RULES FOR RELATIONS:
    - resolved relations → go_legal_relations (legacy) + judgment_relations (unified, if judicial)
    - unresolved relations → go_relation_candidates
    - NEVER mix them
    - NO entity cleanup here (handled by entity extractor)
    """
    
    def __init__(self, project_id: str = None, write_unified: bool = True):
        """
        Initialize BigQuery ingestor.
        
        Args:
            project_id: GCP project ID
            write_unified: If True, write to unified tables (default: True)
        """
        self.bq_client = BigQueryClient(project_id)
        self.write_unified = write_unified
        
    def ingest_document(self, doc_dir: Path):
        """Perform full ingestion for a single document directory."""
        if not doc_dir.is_dir():
            logger.error(f"Not a directory: {doc_dir}")
            return
            
        logger.info(f"Ingesting document from {doc_dir}")
        
        # 1. Load data
        metadata = self._load_json(doc_dir / "metadata.json")
        entities = self._load_json(doc_dir / "entities.json")
        relations = self._load_json(doc_dir / "relations.json")
        structure = self._load_json(doc_dir / "structure.json")
        
        if not metadata:
            logger.error(f"Metadata missing for {doc_dir}")
            return
            
        doc_id = metadata.get("doc_id")
        
        # 2. Prepare go_master row
        go_master_row = self._prepare_go_master(metadata, entities, structure)
        
        if not go_master_row:
            logger.error(f"Failed to prepare master row for {doc_id}")
            return

        # Validation: Skip if essential identity is missing
        if go_master_row.get("go_number") == "UNKNOWN" or go_master_row.get("go_date") == "1970-01-01":
            logger.warning(
                f"⚠️ Skipping ingestion for {doc_id}: "
                f"Invalid Identity (Number={go_master_row.get('go_number')}, Date={go_master_row.get('go_date')})"
            )
            return
        
        # Initialize embedder if needed (only for valid GOs)
        from backend.ingestion.embedding.google_embedder import get_embedder
        self.embedder = get_embedder()

        # 3. Prepare all table rows
        clause_rows = self._prepare_go_clauses(doc_id, structure)
        thread_rows = self._prepare_functional_threads(doc_id, metadata, entities)
        act_link_rows = self._prepare_act_links(doc_id, entities)
        
        # 4. CRITICAL: Route relations by resolution status
        resolved_relation_rows = self._prepare_legal_relations(doc_id, relations)
        unresolved_candidate_rows = self._prepare_relation_candidates(doc_id, relations)
        
        # 5. Prepare side tables
        beneficiary_rows = self._prepare_go_beneficiaries(doc_id, entities)
        applicability_rows = self._prepare_go_applicability(doc_id, entities)
        authority_rows = self._prepare_go_authorities(doc_id, entities)
        financial_rows = self._prepare_go_financials(doc_id, entities)
        effect_rows = self._prepare_go_effects(doc_id, entities)
        
        # 6. Prepare unified table rows (if enabled)
        if self.write_unified:
            document_row = self._prepare_document_row(go_master_row, metadata, entities, structure)
            chunk_rows = self._prepare_chunks_from_clauses(doc_id, clause_rows)
            domain_mapping_row = self._prepare_domain_mapping(doc_id, thread_rows)
            
            # Judicial-specific metadata (if applicable)
            vertical = metadata.get("vertical", "go")
            judgments_metadata_row = None
            judgment_relation_rows = []
            
            if vertical == "judicial":
                judgments_metadata_row = self._prepare_judgments_metadata(doc_id, metadata, entities, structure)
                judgment_relation_rows = self._prepare_judgment_relations(doc_id, resolved_relation_rows)
        
        # 7. Load to BigQuery (legacy tables - backward compatibility)
        try:
            self.bq_client.load_rows("go_master", [go_master_row])
            self.bq_client.load_rows("go_clauses", clause_rows)
            self.bq_client.load_rows("go_functional_threads", thread_rows)
            self.bq_client.load_rows("go_act_links", act_link_rows)
            
            # CRITICAL: Route relations to correct tables
            if resolved_relation_rows:
                self.bq_client.load_rows("go_legal_relations", resolved_relation_rows)
                logger.info(f"✅ Loaded {len(resolved_relation_rows)} RESOLVED relations to go_legal_relations")
            
            if unresolved_candidate_rows:
                self.bq_client.load_rows("go_relation_candidates", unresolved_candidate_rows)
                logger.info(f"⚠️ Loaded {len(unresolved_candidate_rows)} UNRESOLVED candidates to go_relation_candidates")
            
            # Load side tables
            if beneficiary_rows:
                self.bq_client.load_rows("go_beneficiaries", beneficiary_rows)
            if applicability_rows:
                self.bq_client.load_rows("go_applicability", applicability_rows)
            if authority_rows:
                self.bq_client.load_rows("go_authorities", authority_rows)
            if financial_rows:
                self.bq_client.load_rows("go_financials", financial_rows)
            if effect_rows:
                self.bq_client.load_rows("go_effects", effect_rows)
            
            # 8. Load to unified tables (if enabled)
            if self.write_unified:
                if document_row:
                    self.bq_client.load_rows("documents", [document_row])
                    logger.info(f"✅ Loaded document to unified documents table")
                
                if chunk_rows:
                    self.bq_client.load_rows("chunks", chunk_rows)
                    logger.info(f"✅ Loaded {len(chunk_rows)} chunks to unified chunks table")
                
                if domain_mapping_row:
                    self.bq_client.load_rows("domain_mapping", [domain_mapping_row])
                    logger.info(f"✅ Loaded domain mapping to unified domain_mapping table")
                
                if judgments_metadata_row:
                    self.bq_client.load_rows("judgments_metadata", [judgments_metadata_row])
                    logger.info(f"✅ Loaded judicial metadata to judgments_metadata table")
                
                if judgment_relation_rows:
                    self.bq_client.load_rows("judgment_relations", judgment_relation_rows)
                    logger.info(f"✅ Loaded {len(judgment_relation_rows)} judgment relations")
            
            logger.info(f"✅ Successfully ingested document {doc_id} into BigQuery")
            
        except Exception as e:
            logger.error(f"❌ Failed to ingest {doc_id}: {e}")
            raise

    def _load_json(self, path: Path) -> Dict:
        """Load JSON file safely"""
        if not path.exists():
            return {}
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return {}
            
    def _prepare_go_master(self, metadata: Dict, entities: Dict, structure: Dict) -> Dict:
        """
        Prepare go_master row
        
        NOTE: NO entity cleanup here - entities are already cleaned by entity extractor
        We just use them as-is
        """
        # Prioritize structure.identity for date and number
        identity = structure.get("identity", {})
        
        go_date_str = identity.get("date") or metadata.get("go_date")
        if not go_date_str and entities.get("dates"):
            # Fallback to entities (already cleaned by entity extractor)
            dates = entities["dates"]
            if dates and isinstance(dates[0], dict):
                # New structured format
                go_date_str = dates[0].get("value")
            elif dates and isinstance(dates[0], str):
                go_date_str = dates[0]
        
        go_number = identity.get("go_number") or metadata.get("go_number")
        if not go_number and entities.get("go_numbers"):
            go_number = entities["go_numbers"][0]
        
        # Normalize date to YYYY-MM-DD
        go_date = "1970-01-01"  # Default
        if go_date_str:
            # Try various formats
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
                try:
                    dt = datetime.strptime(go_date_str, fmt)
                    go_date = dt.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
        
        # Handle cases like "02-2025" (missing day)
        if go_date == "1970-01-01" and go_date_str and re.match(r'^\d{2}-\d{4}$', go_date_str):
            go_date = f"{go_date_str.split('-')[1]}-{go_date_str.split('-')[0]}-01"
        
        # Get go_archetype (already validated by entity extractor)
        go_type = entities.get("go_archetype", "unknown")
        if isinstance(go_type, list):
            go_type = go_type[0] if go_type else "unknown"
        
        return {
            "go_id": metadata.get("doc_id"),
            "go_number": go_number or "UNKNOWN",
            "go_date": go_date,
            "department": (entities.get("departments") or ["UNKNOWN"])[0],
            "go_type": go_type,
            "raw_pdf_uri": metadata.get("file_path")
        }
        
    def _prepare_go_clauses(self, go_id: str, structure: Dict) -> List[Dict]:
        """Prepare clause rows with embeddings"""
        rows = []
        
        # Collect all potential clause sources
        clauses = []
        
        # 1. Preamble
        if structure.get("preamble"):
            pre_data = structure["preamble"]
            clauses.append({
                "para_no": "PREAMBLE",
                "text": pre_data.get("text"),
                "legal_effect": "preamble",
                "visual_anchor": pre_data.get("visual_anchor")
            })
        
        # 2. Orders (main body)
        if structure.get("orders"):
            clauses.extend(structure["orders"])
        
        # 3. Fallbacks
        if not clauses:
            clauses = structure.get("hierarchical_orders", []) or \
                      structure.get("paragraphs", []) or \
                      structure.get("sections", [])
        
        if not clauses:
            return []
        
        # Generate embeddings
        texts_to_embed = [p.get("text") for p in clauses if p.get("text")]
        embeddings = []
        if texts_to_embed:
            logger.info(f"Generating embeddings for {len(texts_to_embed)} clauses...")
            embeddings = self.embedder.embed_texts(texts_to_embed)
        
        for i, para in enumerate(clauses):
            para_no = str(para.get("para_no", ""))
            clause_id = f"{go_id}_{para_no}_{str(uuid.uuid4())[:8]}"
            visual_anchor = para.get("visual_anchor") or {}
            
            rows.append({
                "clause_id": clause_id,
                "go_id": go_id,
                "section_path": para_no,
                "clause_text": para.get("text"),
                "clause_effect_type": para.get("legal_effect") or "introduce",
                "functional_thread_ids": [],
                "effective_from_date": None,
                "effective_to_date": None,
                "conditional_flags": None,
                "visual_anchor_page": visual_anchor.get("page"),
                "visual_anchor_bbox": json.dumps(visual_anchor.get("bbox")) if visual_anchor.get("bbox") else None,
                "embedding": embeddings[i] if i < len(embeddings) else []
            })
        
        return rows

    def _prepare_functional_threads(self, go_id: str, metadata: Dict, entities: Dict) -> List[Dict]:
        """Prepare functional thread rows"""
        domains = metadata.get("policy_domains", [])
        if not domains:
            domains = entities.get("policy_domains", [])
        if not domains:
            domains = [metadata.get("primary_domain", "general")]
        
        rows = []
        for domain in domains:
            if not domain:
                continue
            thread_id = domain.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
            rows.append({
                "thread_id": thread_id,
                "go_id": go_id,
                "thread_name": domain,
                "role": "primary",
                "confidence": 0.9,
                "source": "llm"
            })
        return rows
        
    def _prepare_legal_relations(self, go_id: str, relations: Any) -> List[Dict]:
        """
        Prepare ONLY RESOLVED relations for go_legal_relations table
        
        CRITICAL RULE: resolution_status == "resolved" ONLY
        """
        rows = []
        
        if not isinstance(relations, list):
            return rows
        
        resolved_count = 0
        for rel in relations:
            target_ref = rel.get("target_ref", {})
            resolution_status = target_ref.get("resolution_status", "unresolved")
            
            # STRICT: Only include resolved relations
            if resolution_status == "resolved":
                resolved_doc_id = target_ref.get("resolved_doc_id")
                
                if not resolved_doc_id:
                    logger.warning(f"⚠️ Relation marked as resolved but missing resolved_doc_id: {target_ref}")
                    continue
                
                rows.append({
                    "relation_id": str(uuid.uuid4()),
                    "source_go_id": go_id,
                    "target_go_id": resolved_doc_id,
                    "relation_type": rel.get("relation_type", "references"),
                    "scope": rel.get("scope", "document"),
                    "affected_thread_ids": None,
                    "confidence": rel.get("confidence", 0.8),
                    "source": "llm" if rel.get("confidence", 0) > 0.9 else "rule"
                })
                resolved_count += 1
        
        if resolved_count > 0:
            logger.info(f"   ✅ Prepared {resolved_count} resolved relations for go_legal_relations")
        
        return rows
    
    def _prepare_relation_candidates(self, go_id: str, relations: Any) -> List[Dict]:
        """
        Prepare UNRESOLVED relations for go_relation_candidates table
        
        CRITICAL RULE: resolution_status != "resolved"
        """
        rows = []
        
        if not isinstance(relations, list):
            return rows
        
        unresolved_count = 0
        for rel in relations:
            target_ref = rel.get("target_ref", {})
            resolution_status = target_ref.get("resolution_status", "unresolved")
            
            # STRICT: Only include unresolved relations
            if resolution_status != "resolved":
                rows.append({
                    "candidate_id": str(uuid.uuid4()),
                    "source_go_id": go_id,
                    "target_ref_raw": target_ref.get("raw_text", "") or rel.get("target", ""),
                    "relation_type": rel.get("relation_type", "references"),
                    "confidence": rel.get("confidence", 0.8),
                    "resolution_status": resolution_status,
                    "resolution_error": target_ref.get("resolution_error")
                })
                unresolved_count += 1
        
        if unresolved_count > 0:
            logger.info(f"   ⚠️ Prepared {unresolved_count} unresolved candidates for go_relation_candidates")
        
        return rows
        
    def _prepare_act_links(self, go_id: str, entities: Dict) -> List[Dict]:
        """
        Prepare act links from normalized Acts structure
        
        NOTE: Acts are already normalized by entity extractor
        """
        acts = entities.get("acts", [])
        rows = []
        
        for act in acts:
            # Handle normalized dict format (from entity extractor)
            if isinstance(act, dict):
                act_name = act.get("act_name")
                act_year = act.get("act_year")
            else:
                # Fallback for old string format (shouldn't happen with new entity extractor)
                logger.warning(f"⚠️ Found non-normalized act: {act}")
                act_name = str(act)
                act_year = None
            
            if act_name:
                rows.append({
                    "link_id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "act_name": act_name,
                    "act_year": act_year,
                    "section_reference": None,
                    "relation_type": "references",
                    "confidence": 0.8
                })
        
        return rows

    def _prepare_go_beneficiaries(self, go_id: str, entities: Dict) -> List[Dict]:
        """
        Prepare beneficiary rows
        
        NOTE: NO cleanup here - entities already cleaned by entity extractor
        """
        rows = []
        
        # New structure (from entity extractor)
        if "beneficiary_types" in entities:
            for b_type in entities["beneficiary_types"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "beneficiary_type": "beneficiary_types",
                    "beneficiary_name": str(b_type),
                    "count": None
                })
        
        if "beneficiary_orgs" in entities:
            for org in entities["beneficiary_orgs"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "beneficiary_type": "specific_orgs",
                    "beneficiary_name": str(org),
                    "count": None
                })
        
        # Old structure fallback
        if not rows and "beneficiaries" in entities:
            for ben in entities["beneficiaries"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "beneficiary_type": "general",
                    "beneficiary_name": str(ben),
                    "count": None
                })
        
        return rows

    def _prepare_go_applicability(self, go_id: str, entities: Dict) -> List[Dict]:
        """Prepare geographic applicability rows"""
        rows = []
        
        for key in ["districts", "mandals", "villages"]:
            if key in entities:
                for item in entities[key]:
                    rows.append({
                        "id": str(uuid.uuid4()),
                        "go_id": go_id,
                        "region_type": key[:-1],  # singular
                        "region_name": str(item)
                    })
        
        return rows

    def _prepare_go_authorities(self, go_id: str, entities: Dict) -> List[Dict]:
        """
        Prepare authority rows
        
        NOTE: Departments are already sanitized by entity extractor
        """
        rows = []
        
        # Departments (already sanitized)
        if "departments" in entities:
            for dept in entities["departments"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "authority_role": "department",
                    "authority_name": str(dept)
                })
        
        # Authorities
        if "authorities" in entities:
            for auth in entities["authorities"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "authority_role": "signatory",
                    "authority_name": str(auth)
                })
        
        return rows

    def _prepare_go_financials(self, go_id: str, entities: Dict) -> List[Dict]:
        """Prepare financial rows"""
        rows = []
        
        if "financial_amount" in entities:
            for amt in entities["financial_amount"]:
                rows.append({
                    "id": str(uuid.uuid4()),
                    "go_id": go_id,
                    "amount": None,  # Parsing to float is risky without proper validation
                    "budget_head": entities.get("budget_head", [None])[0],
                    "commitment_type": entities.get("financial_commitment", [None])[0]
                })
        
        return rows

    def _prepare_go_effects(self, go_id: str, entities: Dict) -> List[Dict]:
        """
        Prepare effect rows (dates with roles)
        
        NOTE: Dates are already structured and validated by entity extractor
        """
        rows = []
        
        if "dates" in entities:
            for item in entities["dates"]:
                # New structured format (from entity extractor)
                if isinstance(item, dict) and "role" in item:
                    rows.append({
                        "id": str(uuid.uuid4()),
                        "go_id": go_id,
                        "effect_type": "date",
                        "effect_value": item.get("value"),
                        "effect_role": item.get("role")
                    })
                # Old flat date format - skip (entity extractor should have cleaned this)
                elif isinstance(item, str):
                    logger.debug(f"Skipping flat date string (should be cleaned by entity extractor): {item}")
        
        return rows
    
    # ============================================================================
    # UNIFIED SCHEMA PREPARATION METHODS
    # ============================================================================
    
    def _prepare_document_row(
        self, 
        go_master_row: Dict, 
        metadata: Dict, 
        entities: Dict, 
        structure: Dict
    ) -> Optional[Dict]:
        """
        Prepare unified documents table row from go_master data.
        
        Maps:
        - go_master.go_id → documents.document_id
        - go_master.go_number → documents.title
        - go_master.go_date → documents.date
        - Extract doc_type from vertical/metadata
        - Extract domain from functional threads
        - Extract authority from entities
        - Set status based on relations
        """
        doc_id = go_master_row.get("go_id")
        if not doc_id:
            return None
        
        # Determine doc_type from vertical or metadata
        vertical = metadata.get("vertical", "go")
        doc_type_map = {
            "go": "go",
            "judicial": "judgment",
            "legal": "regulation",
            "scheme": "policy",
            "data": "report"
        }
        doc_type = doc_type_map.get(vertical, "go")
        
        # Extract domain from functional threads (primary domain)
        domains = metadata.get("policy_domains", [])
        if not domains:
            domains = entities.get("policy_domains", [])
        if not domains:
            domains = [metadata.get("primary_domain", "general")]
        
        primary_domain = domains[0] if domains else "general"
        
        # Extract authority
        authority = None
        if entities.get("departments"):
            authority = entities["departments"][0]
        elif entities.get("authorities"):
            authority = entities["authorities"][0]
        else:
            authority = "State Government"  # Default for GOs
        
        # Determine status (default to active, can be updated from relations later)
        status = "active"
        
        # Extract title
        title = go_master_row.get("go_number", f"Document {doc_id}")
        if go_master_row.get("go_number") and go_master_row.get("go_number") != "UNKNOWN":
            title = go_master_row.get("go_number")
        
        return {
            "document_id": doc_id,
            "title": title,
            "doc_type": doc_type,
            "domain": primary_domain,
            "authority": authority,
            "jurisdiction": "AP",  # Default, can be enhanced
            "date": go_master_row.get("go_date"),
            "version": None,
            "source_url": None,
            "status": status,
            "raw_pdf_uri": go_master_row.get("raw_pdf_uri")
        }
    
    def _prepare_chunks_from_clauses(
        self, 
        doc_id: str, 
        clause_rows: List[Dict]
    ) -> List[Dict]:
        """
        Prepare unified chunks table rows from go_clauses data.
        
        Maps:
        - go_clauses.clause_id → chunks.chunk_id
        - go_clauses.go_id → chunks.document_id
        - go_clauses.clause_text → chunks.text
        - go_clauses.embedding → chunks.embedding
        - Determine chunk_type from clause_effect_type
        """
        chunk_rows = []
        
        for clause in clause_rows:
            clause_id = clause.get("clause_id")
            if not clause_id:
                continue
            
            # Map clause_effect_type to chunk_type
            effect_type = clause.get("clause_effect_type", "introduce")
            chunk_type_map = {
                "preamble": "paragraph",
                "introduce": "clause",
                "amend": "clause",
                "delete": "clause",
                "clarify": "clause"
            }
            chunk_type = chunk_type_map.get(effect_type, "clause")
            
            # Get page info
            page_start = clause.get("visual_anchor_page")
            page_end = page_start  # Same page if not specified
            
            chunk_rows.append({
                "chunk_id": clause_id,
                "document_id": doc_id,
                "chunk_type": chunk_type,
                "text": clause.get("clause_text", ""),
                "page_start": page_start,
                "page_end": page_end,
                "embedding": clause.get("embedding", [])
            })
        
        return chunk_rows
    
    def _prepare_domain_mapping(
        self, 
        doc_id: str, 
        thread_rows: List[Dict]
    ) -> Optional[Dict]:
        """
        Prepare unified domain_mapping table row from functional_threads.
        
        Maps:
        - Primary thread → primary_domain
        - Other threads → secondary_domains array
        """
        if not thread_rows:
            return None
        
        # Find primary domain
        primary_thread = next(
            (t for t in thread_rows if t.get("role") == "primary"),
            thread_rows[0] if thread_rows else None
        )
        
        if not primary_thread:
            return None
        
        primary_domain = primary_thread.get("thread_name", "general")
        
        # Collect secondary domains
        secondary_domains = [
            t.get("thread_name")
            for t in thread_rows
            if t.get("role") != "primary" and t.get("thread_name")
        ]
        
        # Get confidence and source from primary thread
        confidence = primary_thread.get("confidence", 0.9)
        source = primary_thread.get("source", "llm")
        
        return {
            "document_id": doc_id,
            "primary_domain": primary_domain,
            "secondary_domains": secondary_domains if secondary_domains else [],
            "confidence": confidence,
            "source": source
        }
    
    def _prepare_judgments_metadata(
        self,
        doc_id: str,
        metadata: Dict,
        entities: Dict,
        structure: Dict
    ) -> Optional[Dict]:
        """
        Prepare judgments_metadata table row for judicial documents.
        
        Extracts:
        - court from metadata/structure
        - bench_strength from metadata
        - case_number from metadata
        - binding_strength from metadata
        - ratio_present from structure
        """
        # Extract court
        court = None
        judicial_identity = structure.get("identity", {})
        if isinstance(judicial_identity, dict):
            court = judicial_identity.get("court")
        
        if not court:
            # Try metadata
            court = metadata.get("court") or metadata.get("authority")
        
        if not court:
            court = "Unknown Court"
        
        # Extract bench strength
        bench_strength = None
        if isinstance(judicial_identity, dict):
            bench_strength = judicial_identity.get("bench_strength")
        
        if not bench_strength:
            bench_strength = metadata.get("bench_strength")
        
        # Extract case number
        case_number = None
        if isinstance(judicial_identity, dict):
            case_number = judicial_identity.get("case_number")
        
        if not case_number:
            case_number = metadata.get("case_number")
        
        # Extract binding strength
        binding_strength = None
        if isinstance(judicial_identity, dict):
            binding_strength = judicial_identity.get("binding_strength")
        
        if not binding_strength:
            binding_strength = metadata.get("binding_strength", "informative")
        
        # Check if ratio is present (from structure)
        ratio_present = False
        if structure.get("sections"):
            # Check if ratio section exists
            for section in structure.get("sections", []):
                if section.get("section_type") == "ratio" or "ratio" in section.get("title", "").lower():
                    ratio_present = True
                    break
        
        # Extract petition result and order type
        petition_result = None
        order_type = None
        if isinstance(judicial_identity, dict):
            outcome = judicial_identity.get("outcome", {})
            if isinstance(outcome, dict):
                petition_result = outcome.get("petition_result")
                order_type = outcome.get("order_type")
        
        return {
            "document_id": doc_id,
            "court": court,
            "bench_strength": bench_strength,
            "case_number": case_number,
            "ratio_present": ratio_present,
            "binding_strength": binding_strength,
            "petition_result": petition_result,
            "order_type": order_type
        }
    
    def _prepare_judgment_relations(
        self,
        doc_id: str,
        resolved_relation_rows: List[Dict]
    ) -> List[Dict]:
        """
        Prepare judgment_relations table rows from go_legal_relations.
        
        Only includes relations where both source and target are judicial documents.
        Maps relation types for judicial context:
        - "supersedes" → "overrules"
        - "cancels" → "overrules"
        """
        judgment_relations = []
        
        for rel in resolved_relation_rows:
            source_id = rel.get("source_go_id")
            target_id = rel.get("target_go_id")
            relation_type = rel.get("relation_type", "references")
            
            # Map relation types for judicial context
            judicial_relation_type = relation_type
            if relation_type in ["supersedes", "cancels"]:
                judicial_relation_type = "overrules"
            elif relation_type == "amends":
                judicial_relation_type = "followed"  # Amends in judicial context often means followed
            elif relation_type == "clarifies":
                judicial_relation_type = "distinguished"
            
            # Only include if both documents are judicial
            # Note: We can't verify this without querying documents table,
            # so we'll include all resolved relations and let migration script filter
            judgment_relations.append({
                "from_doc_id": source_id,
                "to_doc_id": target_id,
                "relation_type": judicial_relation_type,
                "confidence": rel.get("confidence", 0.8),
                "source": rel.get("source", "llm")
            })
        
        return judgment_relations


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-dir", type=str, required=True)
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    ingestor = BQIngestor()
    ingestor.ingest_document(Path(args.doc_dir))