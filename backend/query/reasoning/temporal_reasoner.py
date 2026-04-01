"""
Temporal Reasoning Engine

Handles date-based queries and temporal validity of documents.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class TemporalReasoner:
    """
    Reasons about temporal aspects of legal documents.
    
    Handles:
    - Date extraction from queries
    - Temporal validity checks
    - Policy evolution timelines
    """
    
    def __init__(self):
        self.date_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        self.date_keywords = {
            "before": -1,
            "after": 1,
            "since": 1,
            "until": -1,
            "during": 0,
            "in": 0,
        }
    
    def extract_temporal_context(self, query: str) -> Optional[Dict]:
        """
        Extract temporal context from query.
        
        Returns:
            Dict with:
                - date: int (year)
                - operator: str ("before", "after", "exact", etc.)
                - temporal_type: str ("query_date", "document_date")
        """
        # Extract year from query
        year_matches = self.date_pattern.findall(query)
        if not year_matches:
            return None
        
        year = int(year_matches[0])
        
        # Determine operator
        query_lower = query.lower()
        operator = "exact"
        
        for keyword, op_val in self.date_keywords.items():
            if keyword in query_lower:
                if op_val == -1:
                    operator = "before"
                elif op_val == 1:
                    operator = "after"
                else:
                    operator = "during"
                break
        
        return {
            "date": year,
            "operator": operator,
            "temporal_type": "query_date"
        }
    
    def filter_by_temporal(
        self,
        chunks: List,
        temporal_context: Dict
    ) -> List:
        """
        Filter chunks based on temporal context.
        
        Args:
            chunks: Document chunks
            temporal_context: Temporal context from query
            
        Returns:
            Filtered chunks
        """
        if not temporal_context:
            return chunks
        
        target_year = temporal_context["date"]
        operator = temporal_context["operator"]
        
        filtered = []
        
        for chunk in chunks:
            chunk_year = self._get_chunk_year(chunk)
            if not chunk_year:
                # If no year, include it (better to have than miss)
                filtered.append(chunk)
                continue
            
            if operator == "exact":
                if chunk_year == target_year:
                    filtered.append(chunk)
            elif operator == "before":
                if chunk_year < target_year:
                    filtered.append(chunk)
            elif operator == "after":
                if chunk_year > target_year:
                    filtered.append(chunk)
            elif operator == "during":
                # Include chunks around the target year (±2 years)
                if abs(chunk_year - target_year) <= 2:
                    filtered.append(chunk)
            else:
                # Unknown operator - include
                filtered.append(chunk)
        
        return filtered
    
    def _get_chunk_year(self, chunk) -> Optional[int]:
        """Extract year from chunk metadata"""
        metadata = chunk.metadata
        
        # Try various year fields
        year_fields = ["year", "date", "effective_from", "go_date"]
        
        for field in year_fields:
            if field in metadata:
                year_val = metadata[field]
                if year_val:
                    try:
                        # If it's a date string, extract year
                        if isinstance(year_val, str):
                            year_match = self.date_pattern.search(year_val)
                            if year_match:
                                return int(year_match.group(1))
                        # If it's already an int
                        elif isinstance(year_val, int):
                            return year_val
                    except:
                        continue
        
        return None
    
    def build_timeline(self, chunks: List) -> List[Dict]:
        """
        Build chronological timeline of documents.
        
        Returns:
            List of dicts with chronological order
        """
        timeline = []
        
        for chunk in chunks:
            year = self._get_chunk_year(chunk)
            if year:
                timeline.append({
                    "year": year,
                    "doc_id": chunk.doc_id,
                    "title": chunk.metadata.get("title", chunk.metadata.get("subject", "Unknown")),
                    "authority": chunk.metadata.get("authority", "Unknown"),
                    "content_excerpt": chunk.content[:150] if hasattr(chunk, 'content') else None
                })
        
        # Sort by year
        timeline.sort(key=lambda x: x["year"])
        
        return timeline

