import logging
from backend.ingestion.io.bigquery_client import BigQueryClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_view():
    bq = BigQueryClient()
    dataset = bq.dataset_id
    logger.info(f"Creating view in dataset: {dataset}")

    query = f"""
    CREATE OR REPLACE VIEW `{dataset}.go_active_status` AS
    SELECT
      gm.go_id,
      gm.go_number,
      gm.go_date,
      gm.department,
      gm.go_type,
      CASE
        WHEN EXISTS (
          SELECT 1
          FROM `{dataset}.go_legal_relations` r
          WHERE r.target_go_id = gm.go_id
            AND r.relation_type IN ('supersedes', 'cancels')
            AND r.scope = 'full_go'
        )
        THEN 'INACTIVE'
        ELSE 'ACTIVE'
      END AS go_status
    FROM `{dataset}.go_master` gm;
    """

    try:
        bq.client.query(query).result()
        logger.info("✅ Successfully created/replaced view `go_active_status`.")
    except Exception as e:
        logger.error(f"❌ Failed to create view: {e}")

if __name__ == "__main__":
    create_view()
