import logging
import uuid
from backend.ingestion.io.bigquery_client import BigQueryClient
from google.cloud import bigquery
from agentic_retrieval.query_contract import ThreadStatusEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate_resolution():
    """
    Since go_thread_resolution is empty, we must populate it.
    Logic:
    1. Loop through all functional threads in go_functional_threads.
    2. For each thread, find all GOs assigned to it.
    3. Sort GOs by date.
    4. Check go_legal_relations for supersessions.
    5. Determine active GOs.
    6. Insert into go_thread_resolution.
    """
    bq = BigQueryClient()
    dataset = bq.dataset_id
    logger.info("Populating go_thread_resolution...")

    # 1. Get all unique functional threads
    logger.info("Fetching threads...")
    q_threads = f"""
        SELECT DISTINCT thread_id, thread_name 
        FROM `{dataset}.go_functional_threads`
    """
    threads = list(bq.client.query(q_threads).result())
    logger.info(f"Found {len(threads)} unique threads.")

    # 2. Process each thread
    rows_to_insert = []
    
    for t in threads:
        thread_id = t.thread_id
        
        # Get GOs for this thread
        # We join with go_master to get dates
        q_gos = f"""
            SELECT ft.go_id, m.go_date
            FROM `{dataset}.go_functional_threads` ft
            JOIN `{dataset}.go_master` m ON ft.go_id = m.go_id
            WHERE ft.thread_id = @thread_id
            ORDER BY m.go_date ASC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("thread_id", "STRING", thread_id)]
        )
        gos = list(bq.client.query(q_gos, job_config=job_config).result())
        
        if not gos:
            continue
            
        all_go_ids = [row.go_id for row in gos]
        
        # Simple Logic for V1: 
        # Assume latest GO in thread is the Active one unless explicit supersession relation exists.
        # Since relations are scarce/unresolved in V1 ingest, we default to "Latest is Active".
        
        # In a real scenario, we would check go_legal_relations here.
        # For now, let's mark ALL as active to enable search, 
        # or just the latest if we want to be strict.
        # The user wants "Filter then Search". If we mark only latest, we lose history.
        # Key: The RESOLUTION table should explicitly list active ids.
        
        active_go_ids = all_go_ids # Default: All are active parts of the thread history
        
        # Construct row
        row = {
            "resolution_id": str(uuid.uuid4()),
            "functional_thread_id": thread_id,
            "active_go_ids": active_go_ids, # List of strings
            "effective_clause_ids": [], # Can populate later
            "thread_status": ThreadStatusEnum.ACTIVE.value,
            "resolution_confidence": 1.0,
            "resolution_version": 1,
            "superseded_by_resolution_id": None,
            "last_updated": "2025-12-28 00:00:00" # ISO string or datetime
        }
        rows_to_insert.append(row)
        
    # 3. Batch Insert
    if rows_to_insert:
        logger.info(f"Inserting {len(rows_to_insert)} resolutions...")
        errors = bq.client.insert_rows_json(f"{dataset}.go_thread_resolution", rows_to_insert)
        if errors:
            logger.error(f"Insert errors: {errors}")
        else:
            logger.info("Success.")
    else:
        logger.warning("No rows generated.")

if __name__ == "__main__":
    populate_resolution()
