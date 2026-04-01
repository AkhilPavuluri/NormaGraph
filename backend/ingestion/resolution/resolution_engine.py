import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from google.cloud import bigquery
from backend.ingestion.io.bigquery_client import BigQueryClient
from backend.ingestion.io.bq_schemas import DATASET_ID

logger = logging.getLogger(__name__)

class LegalResolutionEngine:
    """
    Engine to resolve legal statuses and current policy state across GO chains.
    Logic:
    1. Group GOs by functional threads.
    2. Order by date.
    3. Apply relations (supersession, amendment, clarification).
    4. Update BigQuery statuses.
    """
    
    def __init__(self, project_id: str = None):
        self.bq_client = BigQueryClient(project_id)
        self.client = self.bq_client.client
        self.dataset_id = self.bq_client.dataset_id

    def resolve_all(self):
        """Find all threads and resolve them one by one."""
        logger.info("Starting global legal resolution...")
        
        # 1. Get all unique functional threads
        query = f"SELECT DISTINCT thread_id FROM `{self.dataset_id}.go_functional_threads`"
        threads = [row.thread_id for row in self.client.query(query).result()]
        
        logger.info(f"Found {len(threads)} functional threads to resolve.")
        
        for thread_id in threads:
            self.resolve_thread(thread_id)
            
        logger.info("Legal resolution completed.")

    def resolve_thread(self, thread_id: str):
        """Resolve the legal state for a specific functional thread."""
        logger.info(f"Resolving thread: {thread_id}")
        
        # 1. Get all GOs in this thread with their dates
        query = f"""
            SELECT m.go_id, m.go_date, m.go_number, m.effective_from_date, m.effective_to_date, m.go_type
            FROM `{self.dataset_id}.go_master` m
            JOIN `{self.dataset_id}.go_functional_threads` t ON m.go_id = t.go_id
            WHERE t.thread_id = @thread_id
            ORDER BY m.go_date ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("thread_id", "STRING", thread_id)
            ]
        )
        gos = list(self.client.query(query, job_config=job_config).result())
        
        if not gos:
            return

        go_ids = [row.go_id for row in gos]
        go_map = {row.go_id: row for row in gos}

        # 2. Get all CLAUSES for these GOs
        # We need clause IDs to handle partial supersession
        query_clauses = f"""
            SELECT clause_id, go_id, section_path, clause_text, effective_to_date
            FROM `{self.dataset_id}.go_clauses`
            WHERE go_id IN UNNEST(@go_ids)
        """
        job_config_clauses = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("go_ids", "STRING", go_ids)
            ]
        )
        clauses = list(self.client.query(query_clauses, job_config_clauses).result())
        
        # Build clause map: go_id -> list of clauses
        go_clauses = {go_id: [] for go_id in go_ids}
        clause_map = {} # clause_id -> clause row
        clause_status_map = {} # clause_id -> status (ACTIVE/SUPERSEDED/INACTIVE)
        
        for c in clauses:
            go_clauses[c.go_id].append(c)
            clause_map[c.clause_id] = c
            clause_status_map[c.clause_id] = "ACTIVE" # Default to ACTIVE

        # 3. Get all LEGAL RELATIONS
        query_rels = f"""
            SELECT source_go_id, target_go_id, relation_type, scope, section
            FROM `{self.dataset_id}.go_legal_relations`
            WHERE source_go_id IN UNNEST(@go_ids) OR target_go_id IN UNNEST(@go_ids)
        """
        job_config_rels = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("go_ids", "STRING", go_ids)
            ]
        )
        rels = list(self.client.query(query_rels, job_config_rels).result())

        # 5. Clause-Level Resolution Logic
        # Iterate chronologically (GOs are already sorted by date)
        
        for current_go in gos:
            current_id = current_go.go_id
            
            # TASK 11: Respect Archetype in Resolution
            # Only Normative Policies (and perhaps Amendments if we mapped them to archetype?)
            # Phase 1 archetypes: normative_policy, administrative_action, financial_sanction, procedural_notice.
            # We assume only 'normative_policy' defines the "Legal State".
            # Administrative actions are transactional and shouldn't affect the Policy Graph usually, 
            # OR they operate in a parallel graph?
            # User instruction: "Exclude administrative/procedural GOs from resolution"
            if current_go.go_type not in ("normative_policy", "amendment"): # "amendment" might be legacy value, strict is normative_policy
                # Check strict Phase 1 values
                if current_go.go_type in ("administrative_action", "procedural_notice", "financial_sanction"):
                    logger.debug(f"Skipping resolution for non-normative GO: {current_id} ({current_go.go_type})")
                    continue
            
            current_date = current_go.go_date

            # A. Check outgoing relations (this GO affecting others)
            # Find relations where source is current_go
            current_rels = [r for r in rels if r.source_go_id == current_id]

            for rel in current_rels:
                target_go_id = rel.target_go_id
                
                # Skip if target not in this thread/batch
                if target_go_id not in go_map:
                    continue
                
                # Ensure we don't supersede a Normative Policy with an Administrative one? 
                # (Already filtered above by skipping loop for non-normative source)
                
                # Skip clarifications (non-destructive)
                if rel.relation_type == "clarifies":
                    continue
                
                # Handle Supersession / Amendment
                if rel.relation_type in ["supersedes", "amends", "cancels", "replaces"]:
                    # Partial Scope
                    if rel.scope == "paragraph" and rel.section: # Changed 'partial' to 'paragraph' matching Extractor
                        # Find matching clauses in target GO
                        # This is a heuristic matching - in prod we'd need robust ID linking
                        target_clauses = go_clauses.get(target_go_id, [])
                        matched_any = False
                        for clause in target_clauses:
                            # If clause section path roughly matches relation section
                            # e.g. "Rule 4" matches "4" or "4(1)"
                            if self._match_section(clause.section_path, rel.section):
                                clause_status_map[clause.clause_id] = "SUPERSEDED"
                                matched_any = True
                                logger.info(f"Clause {clause.clause_id} ({clause.section_path}) SUPERSEDED by {current_id}")
                        
                        if not matched_any:
                            logger.warning(f"Could not find target clause '{rel.section}' in {target_go_id} to supersede")
                    
                    # Full Scope
                    else:
                        # Supersede ALL clauses of target GO
                        for clause in go_clauses.get(target_go_id, []):
                            clause_status_map[clause.clause_id] = "SUPERSEDED"
                        logger.info(f"All clauses of GO {target_go_id} SUPERSEDED by {current_id}")

        # 5. Temporal Validity Check
        today = datetime.now().date()
        for clause_id, status in clause_status_map.items():
            if status == "ACTIVE":
                clause = clause_map[clause_id]
                
                # Check clause specific expiry
                if clause.effective_to_date and clause.effective_to_date < today:
                    clause_status_map[clause_id] = "INACTIVE"
                    continue
                
                # Check parent GO expiry
                parent_go = go_map.get(clause.go_id)
                if parent_go and parent_go.effective_to_date and parent_go.effective_to_date < today:
                    clause_status_map[clause_id] = "INACTIVE"

        # 6. Derive GO Status & Update
        go_status_map = {}
        for go_id in go_ids:
            clauses = go_clauses.get(go_id, [])
            if not clauses:
                # If no clauses parsed, fallback to simplistic logic or mark UNRESOLVED
                # For now, assume ACTIVE if not explicitly superseded via full relation
                # But since we initialized clause_status_map based on DB clauses, 
                # if there are no clauses in DB, we can't do clause-level resolution.
                # Use 'ACTIVE' as fallback but this signals a parsing gap.
               go_status_map[go_id] = "ACTIVE" 
            else:
                active_count = sum(1 for c in clauses if clause_status_map[c.clause_id] == "ACTIVE")
                if active_count == 0:
                    go_status_map[go_id] = "SUPERSEDED" # Or INACTIVE
                elif active_count < len(clauses):
                    go_status_map[go_id] = "PARTIALLY_ACTIVE"
                else:
                    go_status_map[go_id] = "ACTIVE"

        # 7. Batch Update BigQuery
        # Update Clauses
        for clause_id, status in clause_status_map.items():
            self._update_clause_status(clause_id, status)
            
        # Update GO Masters
        for go_id, status in go_status_map.items():
            self._update_go_status(go_id, status)

        # 8. Record Resolution
        # Collect all ACTIVE clauses across the thread
        all_active_clause_ids = [cid for cid, status in clause_status_map.items() if status == "ACTIVE"]
        
        # Which GOs are contributing?
        active_go_ids = list(set(clause_map[cid].go_id for cid in all_active_clause_ids))
        
        self._record_resolution(thread_id, active_go_ids, all_active_clause_ids)

    def _match_section(self, clause_path: str, target_section: str) -> bool:
        """
        Simple heuristic to match 'Rule 4' to '4'.
        In a real system, this would be a rigorous graph match.
        """
        if not clause_path or not target_section:
            return False
            
        # Normalize: remove "rule", "section", "para", spaces, lowercase
        def normalize(s):
            s = s.lower().replace(".", "")
            for prefix in ["rule", "section", "para", "phrase"]:
                s = s.replace(prefix, "")
            return s.strip()
            
        return normalize(clause_path) == normalize(target_section)

    def _update_clause_status(self, clause_id: str, status: str):
        """Update clause status in BigQuery"""
        query = f"""
            UPDATE `{self.dataset_id}.go_clauses`
            SET status = @status
            WHERE clause_id = @clause_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("clause_id", "STRING", clause_id)
            ]
        )
        self.client.query(query, job_config=job_config).result()

    def _update_go_status(self, go_id: str, status: str):
        """Update the legal_status of a GO in BigQuery."""
        query = f"""
            UPDATE `{self.dataset_id}.go_master`
            SET legal_status = @status
            WHERE go_id = @go_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("go_id", "STRING", go_id)
            ]
        )
        self.client.query(query, job_config=job_config).result()

    def _record_resolution(self, thread_id: str, active_go_ids: List[str], effective_clauses: List[str]):
        """Record the current resolved state of a thread."""
        resolution_id = f"res_{thread_id}_{datetime.now().strftime('%Y%m%d')}"
        
        row = {
            "resolution_id": resolution_id,
            "functional_thread_id": thread_id,
            "active_go_ids": active_go_ids,
            "effective_clauses": effective_clauses,
            "legal_status": "ACTIVE" if effective_clauses else "INACTIVE",
            "resolution_confidence": 1.0,
            "last_updated": datetime.now().isoformat()
        }
        
        self.bq_client.load_rows("go_thread_resolution", [row])

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--thread-id", type=str, help="Resolve a specific thread")
    parser.add_argument("--all", action="store_true", help="Resolve all threads")
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    engine = LegalResolutionEngine()
    
    if args.all:
        engine.resolve_all()
    elif args.thread_id:
        engine.resolve_thread(args.thread_id)
    else:
        parser.print_help()
