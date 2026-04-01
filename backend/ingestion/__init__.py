"""
Ingestion Pipeline V2

Clean, minimal, battle-tested ingestion for policy documents.

Usage:
    from backend.ingestion.pipeline import IngestionPipeline
    
    pipeline = IngestionPipeline()
    result = pipeline.process_document(Path("document.pdf"))
"""

__version__ = "2.0.0"
__author__ = "Policy Intelligence Team"

from .pipeline import IngestionPipeline

__all__ = ["IngestionPipeline"]