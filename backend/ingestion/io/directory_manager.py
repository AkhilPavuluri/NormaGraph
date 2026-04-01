"""
Directory management for ingestion_v2 outputs.
"""
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class DirectoryManager:
    """Manage output directory structure."""
    
    def __init__(self, base_output_dir: Path):
        """
        Initialize directory manager.
        
        Args:
            base_output_dir: Base output directory
        """
        self.base_dir = base_output_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_vertical_dirs(self, verticals: list) -> Dict[str, Path]:
        """
        Create directories for all verticals.
        
        Args:
            verticals: List of vertical names
            
        Returns:
            Dictionary mapping vertical names to paths
        """
        vertical_dirs = {}
        
        for vertical in verticals:
            vertical_dir = self.base_dir / vertical
            vertical_dir.mkdir(parents=True, exist_ok=True)
            vertical_dirs[vertical] = vertical_dir
            logger.debug(f"Created directory: {vertical_dir}")
        
        return vertical_dirs
    
    def get_doc_output_dir(self, vertical: str, doc_id: str) -> Path:
        """
        Get output directory for a specific document.
        
        Args:
            vertical: Vertical name
            doc_id: Document ID
            
        Returns:
            Path to document output directory
        """
        doc_dir = self.base_dir / vertical / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir
    
    def get_output_paths(self, vertical: str, doc_id: str) -> Dict[str, Path]:
        """
        Get all standard output paths for a document.
        
        Args:
            vertical: Vertical name
            doc_id: Document ID
            
        Returns:
            Dictionary with output paths
        """
        doc_dir = self.get_doc_output_dir(vertical, doc_id)
        
        return {
            "doc_dir": doc_dir,
            "raw_text": doc_dir / "raw_text.txt",
            "cleaned_text": doc_dir / "cleaned_text.txt",
            "chunks": doc_dir / "chunks.jsonl",
            "entities": doc_dir / "entities.json",
            "relations": doc_dir / "relations.json",
            "metadata": doc_dir / "metadata.json",
        }
    
    def cleanup(self, vertical: str = None):
        """
        Clean up output directories.
        
        Args:
            vertical: Specific vertical to clean, or None for all
        """
        if vertical:
            vertical_dir = self.base_dir / vertical
            if vertical_dir.exists():
                import shutil
                shutil.rmtree(vertical_dir)
                logger.info(f"Cleaned up {vertical} directory")
        else:
            import shutil
            shutil.rmtree(self.base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Cleaned up all output directories")