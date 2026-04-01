"""
Entity Extraction Patterns
Fast, deterministic regex patterns for common entities
No heavy NLP - just clean regex
"""
import re
from typing import Dict, List, Set


class EntityPatterns:
    """
    Centralized entity extraction patterns
    Fast and deterministic
    """
    
    def __init__(self):
        # GO number patterns
        self.go_patterns = [
            re.compile(r'G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)', re.IGNORECASE),
            re.compile(r'GO\s+No\.?\s*(\d+)', re.IGNORECASE),
            re.compile(r'Government Order\s+No\.?\s*(\d+)', re.IGNORECASE)
        ]
        
        # Section patterns
        self.section_patterns = [
            re.compile(r'Section\s+(\d+[A-Z]?(?:\([a-z0-9]+\))?)', re.IGNORECASE),
            re.compile(r'Sec\.?\s+(\d+[A-Z]?)', re.IGNORECASE),
            re.compile(r'§\s*(\d+[A-Z]?)')
        ]
        
        # Rule patterns
        self.rule_patterns = [
            re.compile(r'Rule\s+(\d+[A-Z]?(?:\([a-z0-9]+\))?)', re.IGNORECASE),
            re.compile(r'Rules?,?\s+\d{4}', re.IGNORECASE)  # "Rules, 2023"
        ]
        
        # Date patterns
        self.date_patterns = [
            re.compile(r'\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b'),
            re.compile(r'\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b', re.IGNORECASE),
            re.compile(r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b', re.IGNORECASE)
        ]
        
        # Department/Ministry patterns
        self.dept_patterns = [
            re.compile(r'(?:Department|Ministry|Directorate)\s+of\s+([A-Z][A-Za-z\s&,]+?)(?:\s+Department|\s+Ministry|\.|\,|$)', re.IGNORECASE),
            re.compile(r'((?:[A-Z][a-z]+\s+)+(?:Department|Ministry|Directorate|Board|Commission))', re.IGNORECASE)
        ]
        
        # Scheme patterns
        self.scheme_patterns = [
            re.compile(r'(Jagananna\s+[A-Z][A-Za-z\s]+(?:Scheme)?)', re.IGNORECASE),
            re.compile(r'((?:[A-Z][a-z]+\s+){1,4}Scheme)', re.IGNORECASE),
            re.compile(r'(Midday\s+Meal\s+Scheme)', re.IGNORECASE),
            re.compile(r'(Sarva\s+Shiksha\s+Abhiyan)', re.IGNORECASE)
        ]
        
        # Year patterns
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        
        # Act patterns - Fixed to avoid false positives by requiring word boundaries
        self.act_patterns = [
            # Full act with year: "Education Act, 2020" or "The Education Act, 2020"
            re.compile(r'(?:The\s+)?([A-Z][A-Za-z\s,]+?\bAct\b,?\s+\d{4})', re.IGNORECASE),
            # Act with specific markers: "Education Act:" or "Education Act."
            re.compile(r'(?:The\s+)?([A-Z][A-Za-z\s,]+?\bAct\b)(?:,|:|\.)(?:\s|$)', re.IGNORECASE),
            # Act number patterns: "Act No. 25 of 2020"
            re.compile(r'([A-Z][A-Za-z\s,]+?\bAct\b\s+No\.?\s+\d+\s+of\s+\d{4})', re.IGNORECASE),
            # Act references with "under": but only if followed by specific markers
            re.compile(r'under\s+(?:the\s+)?([A-Z][A-Za-z\s,]+?\bAct\b)(?:\s+of\s+\d{4}|,|:|\.)', re.IGNORECASE)
        ]
    
    def extract_go_numbers(self, text: str) -> List[str]:
        """Extract GO numbers"""
        numbers = set()
        
        for pattern in self.go_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                numbers.add(f"GO.MS.No.{match}")
        
        return sorted(list(numbers))
    
    def extract_sections(self, text: str) -> List[str]:
        """Extract section references"""
        sections = set()
        
        for pattern in self.section_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                sections.add(f"Section {match}")
        
        return sorted(list(sections))
    
    def extract_rules(self, text: str) -> List[str]:
        """Extract rule references"""
        rules = set()
        
        for pattern in self.rule_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                rules.add(match if match.startswith("Rule") else f"Rule {match}")
        
        return sorted(list(rules))
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract dates"""
        dates = set()
        
        for pattern in self.date_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                dates.add(match)
        
        return sorted(list(dates))
    
    def extract_departments(self, text: str) -> List[str]:
        """Extract department/ministry names"""
        departments = set()
        
        for pattern in self.dept_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # Clean up
                dept = match.strip().strip(',').strip('.')
                if len(dept) > 5:  # Avoid very short matches
                    departments.add(dept)
        
        return sorted(list(departments))[:10]  # Limit to top 10
    
    def extract_schemes(self, text: str) -> List[str]:
        """Extract scheme names"""
        schemes = set()
        
        for pattern in self.scheme_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                scheme = match.strip()
                if len(scheme) > 5:
                    schemes.add(scheme)
        
        return sorted(list(schemes))[:10]
    
    def extract_years(self, text: str) -> List[str]:
        """Extract years"""
        years = set()
        
        matches = self.year_pattern.findall(text)
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            year = match + matches[matches.index(match) + 1] if match in ['19', '20'] else match
            if 1900 <= int(year) <= 2100:  # Reasonable year range
                years.add(year)
        
        return sorted(list(years))
    
    def extract_acts(self, text: str) -> List[str]:
        """Extract Act references - with strict filtering to avoid false positives"""
        acts = set()
        
        for pattern in self.act_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                act = match.strip().strip(',').strip('.')
                
                # Skip if too short
                if len(act) <= 10:
                    continue
                
                act_lower = act.lower()
                
                # STRICT FALSE POSITIVE FILTERING
                
                # 1. Must end with "Act" as a complete word (not "attract", "exact", etc.)
                if not re.search(r'\bact\s*$', act_lower):
                    continue
                
                # 2. Skip specific problematic patterns found in the document
                false_positive_patterns = [
                    r'officers.*for.*act',      # "officers...for...act"
                    r'state.*for.*act',         # "state...for...act"  
                    r'for\s+\w+\s+act',         # "for [word] act"
                    r'providing\s+\w+.*act',    # "providing...act"
                    r'necessary\s+act',         # "necessary act"
                    r'attract\w*',              # "attract", "attractive"
                    r'exact\w*',                # "exact", "exactly"
                    r'nutritious.*act'          # "nutritious...act"
                ]
                
                if any(re.search(pattern, act_lower) for pattern in false_positive_patterns):
                    continue
                
                # 3. Extract words before "Act"
                words_before_act = re.sub(r'\s+act\s*$', '', act, flags=re.IGNORECASE).strip().split()
                
                # 4. Must have at least 2 substantial words before "Act"
                substantial_words = [w for w in words_before_act 
                                   if len(w) > 2 and w.lower() not in ['the', 'and', 'of', 'for', 'in', 'to', 'a', 'an']]
                if len(substantial_words) < 2:
                    continue
                
                # 5. Must have at least one proper noun (uppercase)
                if not any(word[0].isupper() for word in words_before_act if word and len(word) > 1):
                    continue
                
                # 6. Must not contain common non-Act words
                non_act_words = {'necessary', 'nutritious', 'attract', 'exact', 'impact', 'contact', 
                               'practical', 'actual', 'officers', 'state', 'providing'}
                if any(non_word in act_lower for non_word in non_act_words):
                    continue
                
                # 7. Must have proper Act structure indicators
                valid_act_indicators = [
                    re.search(r'\bact\b,', act_lower),      # "Act,"
                    re.search(r'\bact\b\.', act_lower),     # "Act."
                    re.search(r'\bact\b\s+of\s+\d{4}', act_lower), # "Act of 2020"
                    re.search(r'\bact\b\s+no', act_lower),  # "Act No."
                    re.search(r'\bact\b:', act_lower),      # "Act:"
                    act_lower.strip().endswith('act')       # Ends with "act"
                ]
                
                if not any(valid_act_indicators):
                    continue
                
                acts.add(act)
        
        return sorted(list(acts))[:10]
    
    def extract_all(self, text: str) -> Dict[str, List[str]]:
        """Extract all entities"""
        return {
            "go_numbers": self.extract_go_numbers(text),
            "sections": self.extract_sections(text),
            "rules": self.extract_rules(text),
            "dates": self.extract_dates(text),
            "departments": self.extract_departments(text),
            "schemes": self.extract_schemes(text),
            "acts": self.extract_acts(text)
        }