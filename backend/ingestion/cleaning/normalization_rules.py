"""
Normalization rules for government documents.

Standardize references, dates, and common patterns.
"""
import re
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class NormalizationRules:
    """Apply normalization rules to text."""
    
    @staticmethod
    def standardize_go_references(text: str) -> str:
        """
        Standardize Government Order references.
        
        Examples:
            "G.O.Ms.No.123" -> "G.O.Ms.No. 123"
            "GO MS No 123" -> "G.O.Ms.No. 123"
        """
        # Normalize spacing
        text = re.sub(r'G\.O\.(Ms|MS)\.?No\.?(\d+)', r'G.O.Ms.No. \2', text, flags=re.IGNORECASE)
        text = re.sub(r'G\.O\.(Rt|RT)\.?No\.?(\d+)', r'G.O.Rt.No. \2', text, flags=re.IGNORECASE)
        text = re.sub(r'GO\s+(MS|Ms)\.?\s*No\.?\s*(\d+)', r'G.O.Ms.No. \2', text, flags=re.IGNORECASE)
        text = re.sub(r'GO\s+(RT|Rt)\.?\s*No\.?\s*(\d+)', r'G.O.Rt.No. \2', text, flags=re.IGNORECASE)
        
        return text
    
    @staticmethod
    def standardize_section_references(text: str) -> str:
        """
        Standardize legal section references.
        
        Examples:
            "Sec.12" -> "Section 12"
            "§12" -> "Section 12"
        """
        text = re.sub(r'Sec\.?\s*(\d+)', r'Section \1', text, flags=re.IGNORECASE)
        text = re.sub(r'§\s*(\d+)', r'Section \1', text)
        
        return text
    
    @staticmethod
    def standardize_dates(text: str) -> str:
        """
        Standardize date formats to DD-MM-YYYY.
        
        Examples:
            "12/05/2024" -> "12-05-2024"
            "12.05.2024" -> "12-05-2024"
        """
        # Replace / and . with -
        text = re.sub(r'(\d{1,2})[/.](\d{1,2})[/.](\d{4})', r'\1-\2-\3', text)
        
        return text
    
    @staticmethod
    def apply_all(text: str) -> str:
        """Apply all normalization rules."""
        text = NormalizationRules.standardize_go_references(text)
        text = NormalizationRules.standardize_section_references(text)
        text = NormalizationRules.standardize_dates(text)
        return text


def normalize_text(text: str) -> str:
    """
    Convenience function for normalization.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    return NormalizationRules.apply_all(text)