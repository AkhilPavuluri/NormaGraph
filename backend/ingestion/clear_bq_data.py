
import os
import sys
from pathlib import Path
import logging
from google.cloud import bigquery

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.ingestion.io.bq_schemas import SCHEMAS, DATASET_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_2025_data():
    client = bigquery.Client()
    project_id = client.project
    
    logger.info(f"Clearing 2025 documents from project {project_id}, dataset {DATASET_ID}")
    
    # Tables to clear
    tables = list(SCHEMAS.keys())
    
    for table_name in tables:
        table_id = f"{project_id}.{DATASET_ID}.{table_name}"
        
        # Check if table exists
        try:
            client.get_table(table_id)
        except Exception:
            logger.warning(f"Table {table_id} does not exist, skipping.")
            continue
            
        # Construct delete query
        # Most tables have go_id or source_go_id or candidate_id (where candidate refers to a document)
        # We target documents starting with 2025se_ or similar patterns used for 2025 data
        
        # Table-specific ID field mapping
        id_field_map = {
            "go_legal_relations": "source_go_id",
            "go_relation_candidates": "source_go_id",
            "go_thread_resolution": None, # Skip derived table
        }
        
        id_field = id_field_map.get(table_name, "go_id")
        
        if id_field is None:
            logger.info(f"Skipping table {table_name} (no direct go_id mapping)")
            continue
            
        query = f"DELETE FROM `{table_id}` WHERE {id_field} LIKE '2025se_%' OR {id_field} LIKE 'g_o_%' OR {id_field} LIKE 'g.o.%'"
        
        logger.info(f"Running: {query}")
        
        try:
            query_job = client.query(query)
            query_job.result()  # Wait for job to complete
            logger.info(f"✅ Cleared 2025 data from {table_name}")
        except Exception as e:
            logger.error(f"❌ Failed to clear {table_name}: {e}")

if __name__ == "__main__":
    clear_2025_data()
