"""
I/O modules for ingestion pipeline.
"""

from backend.ingestion.io.file_loader import FileLoader
from backend.ingestion.io.gcs_file_loader import GCSFileLoader

__all__ = ["FileLoader", "GCSFileLoader"]

