"""
Text file writing utilities.
"""
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def write_text(text: str, output_path: Path) -> bool:
    """
    Write text to file.
    
    Args:
        text: Text content
        output_path: Output file path
        
    Returns:
        True if successful
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.debug(f"Wrote text to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing text to {output_path}: {e}")
        return False


def read_text(file_path: Path) -> str:
    """Read text from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading text from {file_path}: {e}")
        return ""