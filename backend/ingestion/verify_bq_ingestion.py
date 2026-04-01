
import os
import sys
from pathlib import Path
import logging
from google.cloud import bigquery

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.ingestion.io.bq_schemas import DATASET_ID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_ingestion():
    client = bigquery.Client()
    project_id = client.project
    
    logger.info(f"Verifying ingestion for {DATASET_ID} in project {project_id}")
    
    # 1. Master Row Summary
    query_master = f"""
    SELECT 
        COUNT(*) as total_docs,
        COUNT(DISTINCT go_type) as unique_archetypes,
        ARRAY_AGG(DISTINCT go_type) as archetypes
    FROM `{project_id}.{DATASET_ID}.go_master`
    WHERE go_id LIKE '2025se_%' OR go_id LIKE 'g_o_%' OR go_id LIKE 'g.o.%'
    """
    
    # 2. Effects (Dates) Summary
    query_effects = f"""
    SELECT 
        effect_role,
        COUNT(*) as count,
        COUNT(DISTINCT go_id) as unique_docs
    FROM `{project_id}.{DATASET_ID}.go_effects`
    WHERE go_id LIKE '2025se_%' OR go_id LIKE 'g_o_%' OR go_id LIKE 'g.o.%'
    GROUP BY effect_role
    """
    
    # 3. Relations Summary
    query_relations = f"""
    SELECT 
        'Resolved' as type,
        relation_type,
        COUNT(*) as count
    FROM `{project_id}.{DATASET_ID}.go_legal_relations`
    WHERE source_go_id LIKE '2025se_%' OR source_go_id LIKE 'g_o_%' OR source_go_id LIKE 'g.o.%'
    GROUP BY relation_type
    UNION ALL
    SELECT 
        'Unresolved' as type,
        relation_type,
        COUNT(*) as count
    FROM `{project_id}.{DATASET_ID}.go_relation_candidates`
    WHERE source_go_id LIKE '2025se_%' OR source_go_id LIKE 'g_o_%' OR source_go_id LIKE 'g.o.%'
    GROUP BY relation_type
    """
    
    # 4. Act Links Summary
    query_acts = f"""
    SELECT 
        COUNT(*) as total_links,
        COUNT(DISTINCT act_name) as unique_acts
    FROM `{project_id}.{DATASET_ID}.go_act_links`
    WHERE go_id LIKE '2025se_%' OR go_id LIKE 'g_o_%' OR go_id LIKE 'g.o.%'
    """

    queries = {
        "Master Data": query_master,
        "Date Roles (Effects)": query_effects,
        "Relations": query_relations,
        "Act Links": query_acts
    }
    
    print("\n" + "="*60)
    print("INGESTION VERIFICATION REPORT")
    print("="*60)
    
    for title, q in queries.items():
        print(f"\n--- {title} ---")
        try:
            query_job = client.query(q)
            results = query_job.result()
            # Print column names
            headers = [field.name for field in results.schema]
            print(" | ".join(headers))
            print("-" * (len(" | ".join(headers)) + 2))
            
            # Print rows
            for row in results:
                print(" | ".join(str(row[h]) for h in headers))
        except Exception as e:
            print(f"Error running query for {title}: {e}")
            
    print("\n" + "="*60)

if __name__ == "__main__":
    verify_ingestion()
