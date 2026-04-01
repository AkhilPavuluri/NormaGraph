import logging
import re
from backend.ingestion.io.bigquery_client import BigQueryClient
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Strict Department Vocabulary
# The user wants ONLY these departments. Everything else is UNKNOWN.
ALLOWED_DEPARTMENTS = {
    "SCHOOL_EDUCATION",
    "SOCIAL_WELFARE",
    "LAW",
    "FINANCE",
    "HEALTH",
    "REVENUE",
    "GENERAL_ADMINISTRATION"
}

def normalize_metadata():
    bq = BigQueryClient()
    dataset = bq.dataset_id
    logger.info(f"Normalizing metadata in {dataset}.go_master")

    # 1. Fetch all unique departments
    query_dept = f"SELECT DISTINCT department FROM `{dataset}.go_master`"
    rows = bq.client.query(query_dept).result()
    
    normalization_map = {}
    for row in rows:
        raw_dept = str(row.department).strip().upper()
        if not raw_dept or raw_dept == "None":
            continue
            
        norm_dept = "UNKNOWN"
        
        # Rule 1: Heuristic Mapping using Keywords
        if "SCHOOL" in raw_dept and "EDUCATION" in raw_dept:
            norm_dept = "SCHOOL_EDUCATION"
        elif "EDUCATION" in raw_dept: 
            norm_dept = "SCHOOL_EDUCATION" 
        elif "WELFARE" in raw_dept or "SOCIAL" in raw_dept:
             norm_dept = "SOCIAL_WELFARE"
        elif "LAW" in raw_dept:
             norm_dept = "LAW"
        elif "FINANCE" in raw_dept:
             norm_dept = "FINANCE"
        elif "HEALTH" in raw_dept:
             norm_dept = "HEALTH"
        elif "REVENUE" in raw_dept:
             norm_dept = "REVENUE"
        elif "GENERAL" in raw_dept and "ADMIN" in raw_dept:
             norm_dept = "GENERAL_ADMINISTRATION"
        
        # Rule 2: Strict Validation
        # If the mapped department is NOT in our allow-list, force UNKNOWN
        if norm_dept not in ALLOWED_DEPARTMENTS:
            norm_dept = "UNKNOWN"
        
        # Only update if the raw value isn't already the correct normalized value
        if raw_dept != norm_dept:
             normalization_map[row.department] = norm_dept

    logger.info(f"Found {len(normalization_map)} departments to normalize.")

    # 2. Update BigQuery in batch
    updates = 0
    for raw, norm in normalization_map.items():
        update_query = f"""
            UPDATE `{dataset}.go_master`
            SET department = @norm_dept
            WHERE department = @raw_dept
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("norm_dept", "STRING", norm),
                bigquery.ScalarQueryParameter("raw_dept", "STRING", raw)
            ]
        )
        try:
            bq.client.query(update_query, job_config=job_config).result()
            updates += 1
            logger.info(f"Normalized '{raw}' -> '{norm}'")
        except Exception as e:
            logger.error(f"Failed to update '{raw}': {e}")
            
    # 3. Fix Unknown Types
    # If go_type is unknown, default to 'administrative' for now unless we have strong signal
    # Actually, let's keep it simple: if unknown, set to 'administrative' as valid default for GOs
    logger.info("Fixing unknown GO types...")
    type_query = f"""
        UPDATE `{dataset}.go_master`
        SET go_type = 'administrative'
        WHERE go_type IS NULL OR go_type = 'unknown'
    """
    bq.client.query(type_query).result()
    logger.info("GO types updated.")

if __name__ == "__main__":
    normalize_metadata()
