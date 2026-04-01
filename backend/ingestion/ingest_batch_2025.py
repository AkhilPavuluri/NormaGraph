
import os
import sys
from pathlib import Path
import logging
import time

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.ingestion.io.bq_ingestor import BQIngestor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ingest_2025_batch():
    base_dir = Path(__file__).parent.parent
    go_output_dir = base_dir / "backend" / "ingestion" / "output" / "go"
    
    if not go_output_dir.exists():
        logger.error(f"Output directory not found: {go_output_dir}")
        return
        
    # Initialize ingestor
    ingestor = BQIngestor()
        
    doc_dirs = sorted([d for d in go_output_dir.iterdir() if d.is_dir()])
    logger.info(f"Found {len(doc_dirs)} processed documents to ingest")
    
    start_time = time.time()
    success_count = 0
    fail_count = 0
    
    for i, doc_dir in enumerate(doc_dirs, 1):
        logger.info(f"[{i}/{len(doc_dirs)}] Ingesting {doc_dir.name}...")
        try:
            ingestor.ingest_document(doc_dir)
            success_count += 1
        except Exception as e:
            logger.error(f"❌ Failed to ingest {doc_dir.name}: {e}")
            fail_count += 1
            
    total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("BATCH INGESTION COMPLETE")
    logger.info(f"Total processed: {len(doc_dirs)}")
    logger.info(f"Success:         {success_count}")
    logger.info(f"Failed:          {fail_count}")
    logger.info(f"Total time:      {total_time:.2f} seconds")
    logger.info("=" * 60)

if __name__ == "__main__":
    ingest_2025_batch()
