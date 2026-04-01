"""
Lightweight, retrieval-optimized file metadata extraction.

Purpose:
- Provide strong FILTERS for vector retrieval
- Avoid high-cardinality or noisy fields
- Extract semantic hints from filename + folder structure
"""

from pathlib import Path
from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

YEAR_PATTERN = re.compile(r'\b(19\d{2}|20\d{2})\b')
GO_PATTERN = re.compile(r'G\.?O\.?', re.IGNORECASE)
COURT_PATTERN = re.compile(r'(supreme|high|district|tribunal)', re.IGNORECASE)


def extract_basic_metadata(file_path: Path) -> Dict:
    """
    Extract minimal, retrieval-safe file metadata.
    """
    try:
        stat = file_path.stat()

        return {
            # Identity
            "file_name": file_path.name,
            "file_extension": file_path.suffix.lower(),

            # Size bucket (useful, low-cardinality)
            "file_size_kb": round(stat.st_size / 1024),

            # Type hint
            "source_type": "pdf" if file_path.suffix.lower() == ".pdf" else "document"
        }

    except Exception as e:
        logger.error(f"Basic metadata error: {e}")
        return {
            "file_name": file_path.name,
            "source_type": "unknown"
        }


def extract_path_metadata(file_path: Path, base_path: Optional[Path] = None) -> Dict:
    """
    Extract normalized, semantic path metadata.
    """
    try:
        if base_path and file_path.is_relative_to(base_path):
            relative_path = file_path.relative_to(base_path)
            folders = list(relative_path.parent.parts)
        else:
            folders = list(file_path.parent.parts[-4:])

        folders_lower = [f.lower() for f in folders]

        metadata = {
            # Normalized folder info
            "folder_depth": len(folders),
            "top_folder": folders_lower[0] if folders_lower else "",
            "immediate_parent": folders_lower[-1] if folders_lower else "",

            # Semantic hints
            "contains_go": any(GO_PATTERN.search(f) for f in folders_lower),
            "contains_court": any(COURT_PATTERN.search(f) for f in folders_lower),
            "contains_budget": any("budget" in f for f in folders_lower),
        }

        # Authority hint (VERY important for filtering)
        if metadata["contains_court"]:
            metadata["authority_hint"] = "judicial"
        elif metadata["contains_go"]:
            metadata["authority_hint"] = "executive"
        else:
            metadata["authority_hint"] = "informational"

        return metadata

    except Exception as e:
        logger.error(f"Path metadata error: {e}")
        return {
            "authority_hint": "unknown"
        }


def extract_filename_signals(file_path: Path) -> Dict:
    """
    Extract semantic signals from filename.
    """
    name = file_path.stem.lower()

    metadata = {}

    year_match = YEAR_PATTERN.search(name)
    if year_match:
        metadata["year_hint"] = int(year_match.group(1))

    if GO_PATTERN.search(name):
        metadata["doc_family"] = "go"
    elif COURT_PATTERN.search(name):
        metadata["doc_family"] = "judicial"
    elif "budget" in name:
        metadata["doc_family"] = "financial"
    else:
        metadata["doc_family"] = "general"

    return metadata


def combine_metadata(file_path: Path, base_path: Optional[Path] = None) -> Dict:
    """
    Combine all lightweight metadata into one retrieval-safe dict.
    """
    metadata = {}

    metadata.update(extract_basic_metadata(file_path))
    metadata.update(extract_path_metadata(file_path, base_path))
    metadata.update(extract_filename_signals(file_path))

    return metadata
