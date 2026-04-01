"""
GCS File Loader

Loads documents from Google Cloud Storage instead of local files.
All source documents should be in GCS, not in git.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from google.cloud import storage
from io import BytesIO
import tempfile

logger = logging.getLogger(__name__)


class GCSFileLoader:
    """
    Load files from Google Cloud Storage.
    
    Replaces local file loading - all documents should be in GCS.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize GCS file loader.
        
        Args:
            bucket_name: GCS bucket name (defaults to env var)
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME must be set in environment variables")
        
        # Initialize GCS client
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
        
        self.supported_extensions = {".pdf", ".txt", ".docx", ".doc", ".PDF", ".DOC", ".DOCX"}
        
        logger.info(f"GCS FileLoader initialized for bucket: {self.bucket_name}")
    
    def load(self, gcs_path: str) -> Optional[Dict[str, Any]]:
        """
        Load a file from GCS and return file info.
        
        Args:
            gcs_path: GCS path (e.g., "documents/go/2025se_ms26_e.pdf")
            
        Returns:
            Dictionary with file info and local temp path, or None if failed
        """
        try:
            # Get blob from GCS
            blob = self.bucket.blob(gcs_path)
            
            if not blob.exists():
                logger.error(f"File not found in GCS: {gcs_path}")
                return None
            
            # Get file metadata
            blob.reload()
            file_name = Path(gcs_path).name
            file_ext = Path(gcs_path).suffix.lower()
            
            if file_ext not in self.supported_extensions:
                logger.warning(f"Unsupported file type: {file_ext}")
                return None
            
            # Download to temporary file
            temp_dir = tempfile.gettempdir()
            temp_file = Path(temp_dir) / f"gcs_{blob.name.replace('/', '_')}"
            
            blob.download_to_filename(str(temp_file))
            
            file_info = {
                "path": str(temp_file),  # Local temp path for processing
                "gcs_path": gcs_path,  # Original GCS path
                "name": file_name,
                "stem": Path(file_name).stem,
                "extension": file_ext,
                "size_bytes": blob.size,
                "size_mb": round(blob.size / (1024 * 1024), 2),
                "temp_file": True,  # Flag to clean up later
            }
            
            logger.info(f"Loaded file from GCS: {gcs_path} ({file_info['size_mb']} MB)")
            return file_info
            
        except Exception as e:
            logger.error(f"Error loading file from GCS {gcs_path}: {e}")
            return None
    
    def list_files(
        self,
        prefix: str = "documents/",
        extensions: Optional[List[str]] = None
    ) -> List[str]:
        """
        List all files in GCS bucket with given prefix.
        
        Args:
            prefix: GCS path prefix (e.g., "documents/go/")
            extensions: Filter by extensions (e.g., [".pdf", ".docx"])
            
        Returns:
            List of GCS paths
        """
        if extensions is None:
            extensions = list(self.supported_extensions)
        
        files = []
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                if not blob.name.endswith('/'):  # Skip directories
                    file_ext = Path(blob.name).suffix.lower()
                    if file_ext in extensions:
                        files.append(blob.name)
            
            logger.info(f"Found {len(files)} files in GCS with prefix: {prefix}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from GCS: {e}")
            return []
    
    def load_batch(
        self,
        prefix: str = "documents/",
        max_files: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Load multiple files from GCS.
        
        Args:
            prefix: GCS path prefix
            max_files: Maximum number of files to load
            
        Returns:
            List of file info dictionaries
        """
        # List files
        gcs_paths = self.list_files(prefix=prefix)
        
        if max_files:
            gcs_paths = gcs_paths[:max_files]
        
        # Load each file
        file_infos = []
        for gcs_path in gcs_paths:
            info = self.load(gcs_path)
            if info:
                file_infos.append(info)
        
        logger.info(f"Loaded {len(file_infos)} files from GCS")
        return file_infos
    
    def cleanup_temp_file(self, file_info: Dict[str, Any]):
        """Clean up temporary file after processing"""
        if file_info.get("temp_file") and "path" in file_info:
            try:
                temp_path = Path(file_info["path"])
                if temp_path.exists():
                    temp_path.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")

