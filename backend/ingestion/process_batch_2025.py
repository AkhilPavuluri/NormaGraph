
import os
import sys
import logging
from pathlib import Path
import time

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.ingestion.pipeline import IngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "Data" / "2025"
    output_dir = base_dir / "backend" / "ingestion" / "output_comparison" / "2025_batch"
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        return

    # Initialize pipeline
    pipeline = IngestionPipeline(
        output_dir=output_dir
    )
    
    # Get all PDF files
    files = sorted(list(data_dir.glob("*.pdf")))
    logger.info(f"Found {len(files)} files to process in {data_dir}")
    
    # Process batch
    start_time = time.time()
    results = pipeline.process_batch(files)
    end_time = time.time()
    
    # Summary
    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = len(files) - success_count
    
    logger.info("=" * 60)
    logger.info("BATCH PROCESSING COMPLETE")
    logger.info(f"Total files: {len(files)}")
    logger.info(f"Success:     {success_count}")
    logger.info(f"Failed:      {failed_count}")
    logger.info(f"Total time:  {end_time - start_time:.2f} seconds")
    logger.info(f"Outputs at:  {output_dir}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
