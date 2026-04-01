"""
Scheme Structure Parser
Extracts Government Scheme structure: Eligibility, Benefits, Application, Implementation
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SchemeSection:
    """Represents a scheme section"""
    section_type: str  # overview, eligibility, benefits, application, implementation
    content: str
    start_pos: int
    end_pos: int


class SchemeStructureParser:
    """
    Parse Government Scheme structure
    
    Scheme Structure:
    1. Scheme Overview/Objective
    2. Eligibility Criteria
    3. Benefits/Assistance
    4. Application Process
    5. Implementation Details
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for scheme structure"""
        
        # Section markers
        self.eligibility_pattern = re.compile(
            r'^(?:ELIGIBILITY|ELIGIBLE|WHO CAN APPLY|ELIGIBILITY CRITERIA)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.benefits_pattern = re.compile(
            r'^(?:BENEFITS?|ASSISTANCE|FINANCIAL AID|PROVISIONS)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.application_pattern = re.compile(
            r'^(?:HOW TO APPLY|APPLICATION|APPLICATION PROCESS|PROCEDURE)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.implementation_pattern = re.compile(
            r'^(?:IMPLEMENTATION|EXECUTION|MONITORING|ADMINISTRATION)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.objective_pattern = re.compile(
            r'^(?:OBJECTIVE|OBJECTIVES|PURPOSE|AIM)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Scheme name pattern
        self.scheme_name_pattern = re.compile(
            r'(Jagananna\s+[A-Za-z\s]+|Amma\s+[A-Za-z\s]+(?:Scheme|Program)|\w+\s+(?:Scheme|Yojana|Program))',
            re.IGNORECASE
        )
    
    def parse(self, text: str) -> Dict:
        """
        Parse scheme document structure
        
        Args:
            text: Full scheme document text
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "has_structure": False,
                "sections": [],
                "scheme_name": None
            }
        
        # Extract scheme name
        scheme_name = self._extract_scheme_name(text)
        
        # Find sections
        sections = self._identify_sections(text)
        
        return {
            "has_structure": len(sections) > 1,
            "sections": sections,
            "scheme_name": scheme_name,
            "section_types": [s.section_type for s in sections]
        }
    
    def _extract_scheme_name(self, text: str) -> Optional[str]:
        """Extract scheme name"""
        # Check first 500 chars
        header = text[:500]
        
        match = self.scheme_name_pattern.search(header)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _identify_sections(self, text: str) -> List[SchemeSection]:
        """Identify scheme sections"""
        sections = []
        
        # Find all section markers
        markers = []
        
        for pattern, section_type in [
            (self.objective_pattern, "objective"),
            (self.eligibility_pattern, "eligibility"),
            (self.benefits_pattern, "benefits"),
            (self.application_pattern, "application"),
            (self.implementation_pattern, "implementation")
        ]:
            match = pattern.search(text)
            if match:
                markers.append((match.start(), section_type))
        
        # Sort by position
        markers.sort(key=lambda x: x[0])
        
        if not markers:
            # No clear structure
            return [SchemeSection(
                section_type="content",
                content=text,
                start_pos=0,
                end_pos=len(text)
            )]
        
        # Extract sections
        for i, (start, section_type) in enumerate(markers):
            # Find end position
            if i + 1 < len(markers):
                end = markers[i + 1][0]
            else:
                end = len(text)
            
            section_content = text[start:end].strip()
            
            if section_content:
                sections.append(SchemeSection(
                    section_type=section_type,
                    content=section_content,
                    start_pos=start,
                    end_pos=end
                ))
        
        # Add overview if exists (before first marker)
        if markers[0][0] > 0:
            overview = text[:markers[0][0]].strip()
            if overview:
                sections.insert(0, SchemeSection(
                    section_type="overview",
                    content=overview,
                    start_pos=0,
                    end_pos=markers[0][0]
                ))
        
        return sections
    
    def extract_eligibility_criteria(self, text: str) -> List[str]:
        """Extract eligibility criteria as list"""
        sections = self._identify_sections(text)
        
        for section in sections:
            if section.section_type == "eligibility":
                # Split by bullet points or numbered items
                criteria = []
                
                # Pattern for bullets/numbers
                bullet_pattern = re.compile(r'^(?:[\•\-\*]|\d+\.|\([a-z]\))\s+(.+?)$', re.MULTILINE)
                
                for match in bullet_pattern.finditer(section.content):
                    criteria.append(match.group(1).strip())
                
                return criteria
        
        return []
    
    def extract_benefits(self, text: str) -> List[str]:
        """Extract scheme benefits as list"""
        sections = self._identify_sections(text)
        
        for section in sections:
            if section.section_type == "benefits":
                # Split by bullet points or numbered items
                benefits = []
                
                bullet_pattern = re.compile(r'^(?:[\•\-\*]|\d+\.|\([a-z]\))\s+(.+?)$', re.MULTILINE)
                
                for match in bullet_pattern.finditer(section.content):
                    benefits.append(match.group(1).strip())
                
                return benefits
        
        return []