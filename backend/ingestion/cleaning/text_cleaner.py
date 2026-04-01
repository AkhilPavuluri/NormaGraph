"""
Text cleaning and normalization.

Reusing proven cleaning functions from old pipeline, but simplified.
"""
import re
import unicodedata
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """Clean and normalize extracted text."""
    
    def __init__(self):
        """Initialize text cleaner."""
        pass
    
    def clean(self, text: str) -> str:
        """
        Apply all cleaning steps.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Step 1: Normalize Unicode
        text = self.normalize_unicode(text)
        
        # Step 2: Fix hyphenation
        text = self.fix_hyphenation(text)
        
        # Step 3: Remove page markers
        text = self.remove_page_markers(text)
        
        # Step 4: Remove artifacts
        text = self.remove_artifacts(text)
        
        # Step 5: Normalize whitespace
        text = self.normalize_whitespace(text)
        
        # Step 6: Fix common OCR errors
        text = self.fix_ocr_errors(text)
        
        return text.strip()
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode characters."""
        # Normalize to NFKC form
        text = unicodedata.normalize('NFKC', text)
        
        # Replace various quote marks
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Replace various dashes
        text = text.replace('–', '-').replace('—', '-')
        text = text.replace('−', '-')
        
        # Replace ellipsis
        text = text.replace('…', '...')
        
        # Fix common encoding issues
        text = text.replace('Â', '')
        text = text.replace('â€™', "'")
        text = text.replace('â€œ', '"').replace('â€', '"')
        
        # Remove zero-width and formatting chars
        text = re.sub(r'[\u200b-\u200f\u2028-\u202f\u205f-\u206f]', '', text)
        text = re.sub(r'[\ufeff\ufffe]', '', text)
        
        # Replace non-breaking spaces
        text = text.replace('\u00a0', ' ')
        
        # Handle Telugu/Indic scripts - Remove OCR garbage
        # Telugu script range: U+0C00-U+0C7F
        # If it's not clean Telugu, it's likely OCR garbage - remove it
        text = self.remove_ocr_garbage(text)
        text = text.replace('\u2007', ' ')
        
        return text
    
    def fix_hyphenation(self, text: str) -> str:
        """Fix words broken by hyphens at line endings."""
        # Fix hyphenated words: "educa-\ntion" -> "education"
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        return text
    
    def remove_page_markers(self, text: str) -> str:
        """Remove page numbers and markers."""
        # Remove various page marker patterns
        text = re.sub(r'\n\s*[-–—]\s*\d+\s*[-–—]\s*\n', '\n', text)
        text = re.sub(r'\nPage\s+\d+\s*\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\d+\s+of\s+\d+\s*\n', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*[-–—]{1,}\s*Page\s+\d+\s*[-–—]{1,}\s*\n', '\n', text, flags=re.IGNORECASE)
        
        return text
    
    def remove_artifacts(self, text: str) -> str:
        """Remove PDF extraction artifacts."""
        # Remove common artifacts
        text = re.sub(r'\[Image:.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Chart:.*?\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<.*?>', '', text)  # HTML tags
        
        # Remove delimiter artifacts
        text = re.sub(r'\n\s*&{2,}.*?\n', '\n', text)
        text = re.sub(r'\n\s*#{2,}.*?\n', '\n', text)
        text = re.sub(r'\n\s*\*{3,}.*?\n', '\n', text)
        
        # Remove copyright symbols
        text = re.sub(r'[©®™]+', '', text)
        
        return text
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        # Replace multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove spaces at line boundaries
        text = re.sub(r'^ +', '', text, flags=re.MULTILINE)
        text = re.sub(r' +$', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors in government documents."""
        # Common OCR mistakes
        ocr_fixes = {
            r'\bGovemment\b': 'Government',
            r'\bEducalion\b': 'Education',
            r'\bAndhra\s+Pradcsh\b': 'Andhra Pradesh',
            r'\b0rder\b': 'Order',
            r'\bSec[il]on\b': 'Section',
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def remove_ocr_garbage(self, text: str) -> str:
        """
        Remove OCR garbage from bilingual documents.
        
        Strategy:
        - Remove lines that are mostly non-English/non-ASCII
        - Keep clean English text
        - Remove symbol-heavy lines that are OCR errors
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                cleaned_lines.append(line)
                continue
            
            # Count different character types
            total_chars = len(line.strip())
            if total_chars == 0:
                continue
            
            # Count ASCII printable chars (English + numbers + punctuation)
            ascii_count = sum(1 for c in line if 32 <= ord(c) <= 126)
            ascii_ratio = ascii_count / total_chars
            
            # Count letter-like characters
            alpha_count = sum(1 for c in line if c.isalpha())
            
            # Count special symbols that indicate OCR garbage
            special_symbols = sum(1 for c in line if c in '~•@_{}[]<>|\\^°±§¶')
            special_ratio = special_symbols / total_chars if total_chars > 0 else 0
            
            # Decision logic
            keep_line = True
            
            # Rule 1: Line is mostly ASCII (English text)
            if ascii_ratio >= 0.7:
                keep_line = True
            # Rule 2: Line has too many special symbols (OCR garbage)
            elif special_ratio > 0.15:
                keep_line = False
            # Rule 3: Line is mostly non-ASCII with few actual letters (Telugu OCR garbage)
            elif ascii_ratio < 0.4 and alpha_count < 5:
                keep_line = False
            # Rule 4: Very short lines with weird characters
            elif total_chars < 10 and ascii_ratio < 0.5:
                keep_line = False
            # Rule 5: Lines that are mostly symbols/numbers (table fragments)
            elif alpha_count < total_chars * 0.3:
                # Check if it's a proper table row or reference
                if any(keyword in line.lower() for keyword in ['no.', 'dt.', 'dated', 'memo', 'govt', 'rc.', 'procs.']):
                    keep_line = True
                else:
                    keep_line = False
            
            if keep_line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)


def clean_text(text: str) -> str:
    """
    Convenience function for text cleaning.
    
    Args:
        text: Raw text
        
    Returns:
        Cleaned text
    """
    cleaner = TextCleaner()
    return cleaner.clean(text)