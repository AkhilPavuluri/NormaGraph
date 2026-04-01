"""
Department Sanitizer
Removes garbage from department names extracted by regex/LLM
Filters out signature blocks, distribution lists, and other noise
"""
import re
from typing import List


class DepartmentSanitizer:
    """
    Deterministic cleanup for department names
    
    Purpose:
    - Remove signature blocks (e.g., "KONA SASIDHAR\nSECRETARY TO GOVERNMENT")
    - Remove distribution lists (e.g., "To\nThe Commission")
    - Filter out newline-heavy blocks
    - Maintain whitelist of valid department patterns
    """
    
    def __init__(self):
        # Patterns that indicate garbage (not real department names)
        self.garbage_patterns = [
            re.compile(r'SECRETARY TO GOVERNMENT', re.IGNORECASE),
            re.compile(r'To\n', re.MULTILINE),
            re.compile(r'Copy to', re.IGNORECASE),
            re.compile(r'Forwarded', re.IGNORECASE),
            re.compile(r'\n.*\n.*\n', re.MULTILINE),  # 3+ newlines = signature block
        ]
        
        # Valid department keywords (whitelist approach)
        self.valid_keywords = {
            'department', 'ministry', 'directorate', 'board', 
            'commission', 'authority', 'council', 'secretariat'
        }
    
    def sanitize(self, departments: List[str]) -> List[str]:
        """
        Clean department list
        
        Args:
            departments: Raw department names from extraction
            
        Returns:
            Cleaned department names
        """
        cleaned = []
        
        for dept in departments:
            if not dept or not isinstance(dept, str):
                continue
            
            # Skip if matches garbage patterns
            if self._is_garbage(dept):
                continue
            
            # Skip if too short or too long
            if len(dept) < 5 or len(dept) > 200:
                continue
            
            # Skip if has too many newlines (signature block)
            if dept.count('\n') > 2:
                continue
            
            # Clean up the string
            cleaned_dept = self._clean_string(dept)
            
            # Verify it has valid department keywords
            if self._has_valid_keywords(cleaned_dept):
                cleaned.append(cleaned_dept)
        
        return cleaned
    
    def _is_garbage(self, text: str) -> bool:
        """Check if text matches garbage patterns"""
        for pattern in self.garbage_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _clean_string(self, text: str) -> str:
        """Clean up whitespace and formatting"""
        # Replace multiple newlines with space
        text = re.sub(r'\n+', ' ', text)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Strip
        text = text.strip()
        return text
    
    def _has_valid_keywords(self, text: str) -> bool:
        """Check if text contains valid department keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.valid_keywords)


def create_department_sanitizer() -> DepartmentSanitizer:
    """Factory function to create department sanitizer"""
    return DepartmentSanitizer()
