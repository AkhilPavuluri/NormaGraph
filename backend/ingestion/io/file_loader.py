"""
File loading utilities for ingestion_v2.

Clean, simple file loading with proper error handling.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FileLoader:
    """Load files from disk."""
    
    def __init__(self):
        """Initialize file loader."""
        self.supported_extensions = {".pdf", ".txt", ".docx"}
    
    def load(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load a file and return file info.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary with file info or None if failed
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None
        
        if file_path.suffix.lower() not in self.supported_extensions:
            logger.warning(f"Unsupported file type: {file_path.suffix}")
            return None
        
        try:
            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "stem": file_path.stem,
                "extension": file_path.suffix.lower(),
                "size_bytes": file_path.stat().st_size,
                "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
            }
            
            logger.info(f"Loaded file: {file_path.name} ({file_info['size_mb']} MB)")
            return file_info
            
        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            return None
    
    def load_batch(self, directory: Path, recursive: bool = True) -> list:
        """
        Load all supported files from a directory.
        
        Args:
            directory: Directory to scan
            recursive: Scan subdirectories
            
        Returns:
            List of file info dictionaries
        """
        if not directory.exists() or not directory.is_dir():
            logger.error(f"Invalid directory: {directory}")
            return []
        
        files = []
        
        if recursive:
            for ext in self.supported_extensions:
                # Search for both lowercase and uppercase extensions
                files.extend(directory.rglob(f"*{ext}"))
                files.extend(directory.rglob(f"*{ext.upper()}"))
        else:
            for ext in self.supported_extensions:
                # Search for both lowercase and uppercase extensions
                files.extend(directory.glob(f"*{ext}"))
                files.extend(directory.glob(f"*{ext.upper()}"))
        
        logger.info(f"Found {len(files)} files in {directory}")
        
        file_infos = []
        for file_path in files:
            info = self.load(file_path)
            if info:
                file_infos.append(info)
        
        return file_infos


def load_text_file(file_path: Path) -> Optional[str]:
    """
    Load a text file and return its content.
    
    Args:
        file_path: Path to text file
        
    Returns:
        File content or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None