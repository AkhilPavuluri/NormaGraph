#!/usr/bin/env python3
"""
BigQuery Unified Schema Migration Script

Migrates from GO-centric tables to unified document-centric schema.

CRITICAL: This is Phase 1 - Foundation. Do NOT touch Vertex Vector Search yet.

Migration Strategy:
1. Create unified tables (documents, chunks, judgments_metadata, judgment_relations, domain_mapping)
2. Migrate existing GO data to unified documents table
3. Map go_clauses to chunks table
4. Map go_legal_relations to judgment_relations (for judicial docs)
5. Populate domain_mapping from go_functional_threads

This script is idempotent - safe to run multiple times.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from backend.ingestion.io.bigquery_client import BigQueryClient
from backend.ingestion.io.bq_schemas import DATASET_ID, UNIFIED_SCHEMAS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedSchemaMigrator:
    """Migrates data from GO-centric to unified document-centric schema"""
    
    def __init__(self, project_id: str = None):
        self.bq_client = BigQueryClient(project_id)
        self.client = self.bq_client.client
        self.dataset_id = self.bq_client.dataset_id
        
    def create_unified_tables(self):
        """Create unified schema tables if they don't exist"""
        logger.info("Creating unified schema tables...")
        self.bq_client.create_tables(unified_only=True, drop_existing=False)
        logger.info("✅ Unified tables created/verified")
    
    def migrate_go_to_documents(self, batch_size: int = 1000):
        """
        Migrate GO documents to unified documents table.
        
        Maps:
        - go_master.go_id → documents.document_id
        - go_master.go_number → documents.title (or derived)
        - go_master.go_date → documents.date
        - go_master.raw_pdf_uri → documents.raw_pdf_uri
        - doc_type = "go"
        - domain = from go_functional_threads
        - status = "active" (default, can be updated from relations)
        """
        logger.info("Migrating GO documents to unified documents table...")
        
        # SQL to migrate GO data
        migrate_query = f"""
        INSERT INTO `{self.dataset_id}.documents` (
            document_id,
            title,
            doc_type,
            domain,
            authority,
            jurisdiction,
            date,
            version,
            source_url,
            status,
            raw_pdf_uri,
            ingested_at
        )
        SELECT DISTINCT
            gm.go_id AS document_id,
            COALESCE(gm.go_number, CONCAT('GO-', gm.go_id)) AS title,
            'go' AS doc_type,
            COALESCE(
                (SELECT thread_name 
                 FROM `{self.dataset_id}.go_functional_threads` gft
                 WHERE gft.go_id = gm.go_id 
                   AND gft.role = 'primary'
                 LIMIT 1),
                'general'
            ) AS domain,
            COALESCE(
                (SELECT authority_name
                 FROM `{self.dataset_id}.go_authorities` ga
                 WHERE ga.go_id = gm.go_id
                 LIMIT 1),
                'State Government'
            ) AS authority,
            'AP' AS jurisdiction,  -- Default, can be enhanced
            gm.go_date AS date,
            NULL AS version,
            NULL AS source_url,
            'active' AS status,  -- Default, can be updated from relations
            gm.raw_pdf_uri,
            gm.ingested_at
        FROM `{self.dataset_id}.go_master` gm
        WHERE NOT EXISTS (
            SELECT 1 
            FROM `{self.dataset_id}.documents` d
            WHERE d.document_id = gm.go_id
        )
        """
        
        try:
            query_job = self.client.query(migrate_query)
            result = query_job.result()
            rows_migrated = result.total_rows if hasattr(result, 'total_rows') else 0
            logger.info(f"✅ Migrated {rows_migrated} GO documents to unified documents table")
            return rows_migrated
        except Exception as e:
            logger.error(f"❌ Failed to migrate GO documents: {e}")
            raise
    
    def migrate_clauses_to_chunks(self, batch_size: int = 1000):
        """
        Migrate GO clauses to unified chunks table.
        
        Maps:
        - go_clauses.clause_id → chunks.chunk_id
        - go_clauses.go_id → chunks.document_id
        - go_clauses.clause_text → chunks.text
        - go_clauses.embedding → chunks.embedding
        - chunk_type = "clause"
        """
        logger.info("Migrating GO clauses to unified chunks table...")
        
        migrate_query = f"""
        INSERT INTO `{self.dataset_id}.chunks` (
            chunk_id,
            document_id,
            chunk_type,
            text,
            page_start,
            page_end,
            embedding,
            created_at
        )
        SELECT
            gc.clause_id AS chunk_id,
            gc.go_id AS document_id,
            'clause' AS chunk_type,
            gc.clause_text AS text,
            gc.visual_anchor_page AS page_start,
            gc.visual_anchor_page AS page_end,  -- Same page if not specified
            gc.embedding,
            CURRENT_TIMESTAMP() AS created_at
        FROM `{self.dataset_id}.go_clauses` gc
        WHERE NOT EXISTS (
            SELECT 1
            FROM `{self.dataset_id}.chunks` c
            WHERE c.chunk_id = gc.clause_id
        )
        """
        
        try:
            query_job = self.client.query(migrate_query)
            result = query_job.result()
            rows_migrated = result.total_rows if hasattr(result, 'total_rows') else 0
            logger.info(f"✅ Migrated {rows_migrated} clauses to unified chunks table")
            return rows_migrated
        except Exception as e:
            logger.error(f"❌ Failed to migrate clauses: {e}")
            raise
    
    def migrate_relations_to_judgment_relations(self):
        """
        Migrate GO legal relations to judgment_relations (for judicial documents).
        
        Only migrates relations where both source and target are judicial documents.
        Maps:
        - go_legal_relations.source_go_id → judgment_relations.from_doc_id
        - go_legal_relations.target_go_id → judgment_relations.to_doc_id
        - go_legal_relations.relation_type → judgment_relations.relation_type
        - Maps "supersedes" → "overrules" for judicial context
        """
        logger.info("Migrating GO legal relations to judgment_relations...")
        
        # Map relation types for judicial context
        # "supersedes" in GO context might mean "overrules" in judicial context
        migrate_query = f"""
        INSERT INTO `{self.dataset_id}.judgment_relations` (
            from_doc_id,
            to_doc_id,
            relation_type,
            confidence,
            source,
            created_at
        )
        SELECT DISTINCT
            glr.source_go_id AS from_doc_id,
            glr.target_go_id AS to_doc_id,
            CASE 
                WHEN glr.relation_type = 'supersedes' THEN 'overrules'
                WHEN glr.relation_type = 'cancels' THEN 'overrules'
                ELSE glr.relation_type
            END AS relation_type,
            glr.confidence,
            glr.source,
            glr.created_at
        FROM `{self.dataset_id}.go_legal_relations` glr
        WHERE glr.relation_type IN ('supersedes', 'cancels', 'amends', 'clarifies', 'references')
          AND EXISTS (
              SELECT 1 FROM `{self.dataset_id}.documents` d1
              WHERE d1.document_id = glr.source_go_id
                AND d1.doc_type = 'judgment'
          )
          AND EXISTS (
              SELECT 1 FROM `{self.dataset_id}.documents` d2
              WHERE d2.document_id = glr.target_go_id
                AND d2.doc_type = 'judgment'
          )
          AND NOT EXISTS (
              SELECT 1 FROM `{self.dataset_id}.judgment_relations` jr
              WHERE jr.from_doc_id = glr.source_go_id
                AND jr.to_doc_id = glr.target_go_id
                AND jr.relation_type = CASE 
                    WHEN glr.relation_type = 'supersedes' THEN 'overrules'
                    WHEN glr.relation_type = 'cancels' THEN 'overrules'
                    ELSE glr.relation_type
                END
          )
        """
        
        try:
            query_job = self.client.query(migrate_query)
            result = query_job.result()
            rows_migrated = result.total_rows if hasattr(result, 'total_rows') else 0
            logger.info(f"✅ Migrated {rows_migrated} relations to judgment_relations table")
            return rows_migrated
        except Exception as e:
            logger.error(f"❌ Failed to migrate relations: {e}")
            raise
    
    def migrate_threads_to_domain_mapping(self):
        """
        Migrate GO functional threads to domain_mapping table.
        
        Maps:
        - go_functional_threads.go_id → domain_mapping.document_id
        - go_functional_threads.thread_name → domain_mapping.primary_domain (if role=primary)
        - All threads → domain_mapping.secondary_domains
        """
        logger.info("Migrating functional threads to domain_mapping...")
        
        migrate_query = f"""
        INSERT INTO `{self.dataset_id}.domain_mapping` (
            document_id,
            primary_domain,
            secondary_domains,
            confidence,
            source,
            created_at
        )
        SELECT
            go_id AS document_id,
            MAX(CASE WHEN role = 'primary' THEN thread_name END) AS primary_domain,
            ARRAY_AGG(DISTINCT CASE WHEN role != 'primary' THEN thread_name END IGNORE NULLS) AS secondary_domains,
            MAX(confidence) AS confidence,
            MAX(source) AS source,
            CURRENT_TIMESTAMP() AS created_at
        FROM `{self.dataset_id}.go_functional_threads`
        WHERE NOT EXISTS (
            SELECT 1 FROM `{self.dataset_id}.domain_mapping` dm
            WHERE dm.document_id = go_id
        )
        GROUP BY go_id
        HAVING MAX(CASE WHEN role = 'primary' THEN thread_name END) IS NOT NULL
        """
        
        try:
            query_job = self.client.query(migrate_query)
            result = query_job.result()
            rows_migrated = result.total_rows if hasattr(result, 'total_rows') else 0
            logger.info(f"✅ Migrated {rows_migrated} domain mappings")
            return rows_migrated
        except Exception as e:
            logger.error(f"❌ Failed to migrate domain mappings: {e}")
            raise
    
    def run_full_migration(self):
        """Run complete migration from GO tables to unified schema"""
        logger.info("=" * 80)
        logger.info("Starting BigQuery Unified Schema Migration")
        logger.info("=" * 80)
        
        try:
            # Step 1: Create unified tables
            self.create_unified_tables()
            
            # Step 2: Migrate documents
            docs_migrated = self.migrate_go_to_documents()
            
            # Step 3: Migrate chunks
            chunks_migrated = self.migrate_clauses_to_chunks()
            
            # Step 4: Migrate relations (for judicial docs)
            relations_migrated = self.migrate_relations_to_judgment_relations()
            
            # Step 5: Migrate domain mappings
            domains_migrated = self.migrate_threads_to_domain_mapping()
            
            logger.info("=" * 80)
            logger.info("Migration Summary:")
            logger.info(f"  Documents migrated: {docs_migrated}")
            logger.info(f"  Chunks migrated: {chunks_migrated}")
            logger.info(f"  Relations migrated: {relations_migrated}")
            logger.info(f"  Domain mappings migrated: {domains_migrated}")
            logger.info("=" * 80)
            logger.info("✅ Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate BigQuery schema to unified format")
    parser.add_argument("--create-tables-only", action="store_true", 
                       help="Only create unified tables, don't migrate data")
    parser.add_argument("--project-id", type=str, 
                       help="Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT)")
    
    args = parser.parse_args()
    
    migrator = UnifiedSchemaMigrator(project_id=args.project_id)
    
    if args.create_tables_only:
        migrator.create_unified_tables()
        logger.info("✅ Unified tables created. Run without --create-tables-only to migrate data.")
    else:
        migrator.run_full_migration()

