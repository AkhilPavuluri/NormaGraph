import os
import logging
from typing import Dict, List, Any
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from backend.ingestion.io.bq_schemas import SCHEMAS, UNIFIED_SCHEMAS, ALL_SCHEMAS, DATASET_ID

logger = logging.getLogger(__name__)

class BigQueryClient:
    """Helper client for interacting with BigQuery."""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT must be set or project_id provided")
        
        self.key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if self.key_path and os.path.exists(self.key_path):
            self.client = bigquery.Client.from_service_account_json(self.key_path, project=self.project_id)
        else:
            self.client = bigquery.Client(project=self.project_id)
            
        self.dataset_id = f"{self.project_id}.{DATASET_ID}"
        
    def create_dataset_if_not_exists(self):
        """Create the dataset if it doesn't already exist."""
        try:
            self.client.get_dataset(self.dataset_id)
            logger.info(f"Dataset {self.dataset_id} already exists")
        except NotFound:
            dataset = bigquery.Dataset(self.dataset_id)
            dataset.location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1")
            self.client.create_dataset(dataset, timeout=30)
            logger.info(f"Created dataset {self.dataset_id}")
            
    def create_tables(self, drop_existing: bool = False, unified_only: bool = False):
        """
        Create all tables defined in schemas if they don't exist.
        
        Args:
            drop_existing: If True, drop existing tables before creating
            unified_only: If True, only create unified schema tables (documents, chunks, etc.)
        """
        self.create_dataset_if_not_exists()
        
        # Select which schemas to use
        schemas_to_create = UNIFIED_SCHEMAS if unified_only else ALL_SCHEMAS
        
        for table_name, schema in schemas_to_create.items():
            table_id = f"{self.dataset_id}.{table_name}"
            
            if drop_existing:
                try:
                    self.client.delete_table(table_id, not_found_ok=True)
                    logger.info(f"Dropped table {table_id}")
                except Exception as e:
                    logger.warning(f"Failed to drop table {table_id}: {e}")

            try:
                self.client.get_table(table_id)
                logger.info(f"Table {table_id} already exists")
            except NotFound:
                table = bigquery.Table(table_id, schema=schema)
                self.client.create_table(table)
                logger.info(f"Created table {table_id}")
                
    def load_rows(self, table_name: str, rows: List[Dict[str, Any]]):
        """Insert rows into a BigQuery table using batch load."""
        if not rows:
            return
            
        table_id = f"{self.dataset_id}.{table_name}"
        schema = ALL_SCHEMAS.get(table_name) or SCHEMAS.get(table_name)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            schema=schema
        )
        
        try:
            job = self.client.load_table_from_json(rows, table_id, job_config=job_config)
            job.result()  # Wait for the job to complete
            logger.info(f"Successfully loaded {len(rows)} rows into {table_name}")
        except Exception as e:
            logger.error(f"Error loading rows into {table_name}: {e}")
            raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop existing tables")
    args = parser.parse_args()
    
    # Setup simple logging for CLI usage
    logging.basicConfig(level=logging.INFO)
    client = BigQueryClient()
    client.create_tables(drop_existing=args.drop)
