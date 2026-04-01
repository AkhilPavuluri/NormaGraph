"""
JSON writing utilities for ingestion_v2.

Simple, clean JSON output handling.
"""
import json
import jsonlines
from pathlib import Path
from typing import Any, List, Dict
import logging

logger = logging.getLogger(__name__)


class JSONWriter:
    """Write JSON and JSONL files."""
    
    @staticmethod
    def write_json(data: Any, output_path: Path, indent: int = 2) -> bool:
        """
        Write data to JSON file.
        
        Args:
            data: Data to write
            output_path: Output file path
            indent: JSON indentation
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            logger.debug(f"Wrote JSON to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSON to {output_path}: {e}")
            return False
    
    @staticmethod
    def write_jsonl(items: List[Dict], output_path: Path) -> bool:
        """
        Write list of dictionaries to JSONL file.
        
        Args:
            items: List of dictionaries
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with jsonlines.open(output_path, mode='w') as writer:
                writer.write_all(items)
            
            logger.debug(f"Wrote {len(items)} items to JSONL: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSONL to {output_path}: {e}")
            return False
    
    @staticmethod
    def append_jsonl(item: Dict, output_path: Path) -> bool:
        """
        Append a single item to JSONL file.
        
        Args:
            item: Dictionary to append
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with jsonlines.open(output_path, mode='a') as writer:
                writer.write(item)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending to JSONL {output_path}: {e}")
            return False
    
    @staticmethod
    def read_json(file_path: Path) -> Any:
        """Read JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading JSON from {file_path}: {e}")
            return None
    
    @staticmethod
    def read_jsonl(file_path: Path) -> List[Dict]:
        """Read JSONL file."""
        try:
            items = []
            with jsonlines.open(file_path) as reader:
                for item in reader:
                    items.append(item)
            return items
        except Exception as e:
            logger.error(f"Error reading JSONL from {file_path}: {e}")
            return []


# Convenience functions
def write_json(data: Any, output_path: Path, indent: int = 2) -> bool:
    """Write JSON file."""
    return JSONWriter.write_json(data, output_path, indent)


def write_jsonl(items: List[Dict], output_path: Path) -> bool:
    """Write JSONL file."""
    return JSONWriter.write_jsonl(items, output_path)


def append_jsonl(item: Dict, output_path: Path) -> bool:
    """Append to JSONL file."""
    return JSONWriter.append_jsonl(item, output_path)


def read_json(file_path: Path) -> Any:
    """Read JSON file."""
    return JSONWriter.read_json(file_path)


def read_jsonl(file_path: Path) -> List[Dict]:
    """Read JSONL file."""
    return JSONWriter.read_jsonl(file_path)