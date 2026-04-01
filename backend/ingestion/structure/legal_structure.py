"""
Legal Structure Parser
Extracts Legal Document structure: Sections, Subsections, Clauses
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class LegalSection:
    """Represents a legal section, article, or schedule"""
    section_type: str  # section, article, schedule, chapter, part
    section_number: str
    title: Optional[str] = None
    content: str = ""
    clauses: List[str] = field(default_factory=list)
    chapter: Optional[str] = None
    part: Optional[str] = None
    structural_confidence: float = 1.0
    start_pos: int = 0
    end_pos: int = 0


class LegalStructureParser:
    """
    Parse Legal Document structure with legal-grade precision.
    Supports Articles (Constitution), Sections (Acts), Schedules, and Chapters.
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for legal structure"""
        
        # Identity reinforcement
        self.enacted_anchor = re.compile(r'be\s+it\s+enacted', re.IGNORECASE)
        
        # Section patterns
        self.section_pattern = re.compile(
            r'^\s*Section\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )

        # GAP 1: Article pattern (Constitution)
        self.article_pattern = re.compile(
            r'^\s*Article\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Universal Legal Support: Rule pattern (RTE, Service Rules)
        self.rule_pattern = re.compile(
            r'^\s*Rule\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )

        # Universal Legal Support: Regulation & Norm (NCTE)
        self.regulation_pattern = re.compile(
            r'^\s*Regulation\s+(\d+|[IVX]+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )

        self.norm_pattern = re.compile(
            r'^\s*Norm\s*(?:[sS])?\s+(\d+|[IVX]+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # GAP 2: Schedule pattern
        self.schedule_pattern = re.compile(
            r'^\s*(?:THE\s+)?SCHEDULE\s+([IXV0-9A-Z]+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )

        # Universal Legal Support: Appendix
        self.appendix_pattern = re.compile(
            r'^\s*APPENDIX\s+([IXV0-9A-Z]+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # Chapter/Part patterns
        self.chapter_pattern = re.compile(
            r'^\s*CHAPTER\s+([IVXLCDM]+|\d+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        self.part_pattern = re.compile(
            r'^\s*PART\s+([IVXLCDM]+|\d+)(?:[:\.\s]+(.+?))?$',
            re.IGNORECASE | re.MULTILINE
        )
        
        # GAP 3: Universal Boundary Pattern (Anti-bleed)
        self.boundary_pattern = re.compile(
            r'^\s*(Section|Sec\.?|Article|Rule|Regulation|Norm\s*s?|CHAPTER|PART|(?:THE\s+)?SCHEDULE|APPENDIX)\s+',
            re.IGNORECASE | re.MULTILINE
        )
        
        # GAP 4: Clause pattern
        self.clause_pattern = re.compile(
            r'^\s*\(([0-9a-zA-Z]|[ivx]+)\)\s+',
            re.IGNORECASE | re.MULTILINE
        )
    
    def parse(self, text: str) -> Dict:
        """Parse legal document structure"""
        if not text:
            return {"has_structure": False, "sections": [], "chapters": [], "act_name": None}
        
        # GAP 6: Reinforced Act Identity
        act_name = self._extract_act_name(text)
        
        # Find structural containers
        chapters = self._find_markers(text, self.chapter_pattern, "chapter")
        parts = self._find_markers(text, self.part_pattern, "part")
        
        # Find content nodes (Universal)
        sections = self._find_content_nodes(text, self.section_pattern, "section")
        articles = self._find_content_nodes(text, self.article_pattern, "article")
        rules = self._find_content_nodes(text, self.rule_pattern, "rule")
        regulations = self._find_content_nodes(text, self.regulation_pattern, "regulation")
        norms = self._find_content_nodes(text, self.norm_pattern, "norm")
        schedules = self._find_content_nodes(text, self.schedule_pattern, "schedule")
        appendices = self._find_content_nodes(text, self.appendix_pattern, "appendix")
        
        all_content_nodes = sorted(
            sections + articles + rules + regulations + norms + schedules + appendices, 
            key=lambda x: x.start_pos
        )
        
        # GAP 7: Hierarchical Binding (Chapter -> Section)
        self._bind_hierarchy(all_content_nodes, chapters, parts)
        
        return {
            "has_structure": len(all_content_nodes) > 0,
            "sections": all_content_nodes,
            "chapters": chapters,
            "parts": parts,
            "act_name": act_name,
            "node_count": len(all_content_nodes)
        }
    
    def _extract_act_name(self, text: str) -> Optional[str]:
        """Extract act/rule/regulation name with reinforcement check"""
        # GAP 6: Requirement check for "Be it enacted", Constitution, or Rules/Norms
        text_start = text[:3000].lower()
        keywords = ["be it enacted", "constitution of india", "notified", "regulation", "rules", "norms", "appendix", "ordinance"]
        if not any(x in text_start for x in keywords):
            return None

        # Try to find the title line (usually all caps or containing the suffix)
        # We look for lines containing key legal suffixes
        suffixes_pattern = r"\b(Act|Rules|Regulations|Regulation|Rule|Norms|Norm|Appendix|Ordinance)\b"
        act_pattern = re.compile(
            rf'(?:THE\s+)?(.+?)\s+{suffixes_pattern}(?:,?\s+(\d{{4}}))?',
            re.IGNORECASE
        )
        
        # Search line by line
        lines = text[:2500].split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5: 
                continue
            
            # Use finditer to find the LAST matching suffix in the line
            # (e.g., "Norms" might appear internally in "Regulations")
            matches = list(act_pattern.finditer(line))
            if matches:
                last_match = matches[-1]
                act_name = last_match.group(1).strip()
                suffix = last_match.group(2)
                year = last_match.group(3)
                
                # Validation: act_name shouldn't be too long
                if len(act_name) > 150:
                    continue
                    
                full_name = f"{act_name} {suffix}"
                if year:
                    full_name += f", {year}"
                return full_name
            
            # Special case for NCTE Norms which might be on their own line
            if "norms" in line.lower() and len(line) < 100:
                 return line
        
        if "constitution of india" in text_start:
            return "Constitution of India"
            
        return None
    
    def _find_markers(self, text: str, pattern: re.Pattern, s_type: str) -> List[LegalSection]:
        """Find structural markers (Chapter, Part)"""
        markers = []
        for match in pattern.finditer(text):
            markers.append(LegalSection(
                section_type=s_type,
                section_number=match.group(1),
                title=match.group(2).strip() if match.group(2) else None,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return markers

    def _find_content_nodes(self, text: str, pattern: re.Pattern, s_type: str) -> List[LegalSection]:
        """Find content-carrying nodes (Sections, Articles) with boundary safety"""
        nodes = []
        matches = list(pattern.finditer(text))
        
        for i, match in enumerate(matches):
            num = match.group(1)
            raw_title = match.group(2).strip() if match.group(2) else ""
            
            # Logic: If title contains '—', split it (Same-line content)
            if "—" in raw_title:
                parts = raw_title.split("—", 1)
                title = parts[0].strip()
                same_line_content = parts[1].strip()
            else:
                title = raw_title if raw_title else None
                same_line_content = ""
            
            # GAP 3: Multi-boundary stop condition (Anti-bleed)
            start_pos = match.end()
            remaining_text = text[start_pos:]
            
            next_boundary = self.boundary_pattern.search(remaining_text)
            if next_boundary:
                end_pos = start_pos + next_boundary.start()
            else:
                end_pos = len(text)
            
            # Combine same-line content with following block
            following_content = text[start_pos:end_pos].strip()
            content = (same_line_content + "\n" + following_content).strip() if same_line_content else following_content
            
            # GAP 4: Clause Detection
            clauses = self.clause_pattern.findall(content)
            
            # GAP 5: Structural Confidence
            conf = self._calculate_confidence(num, content)
            
            nodes.append(LegalSection(
                section_type=s_type,
                section_number=num,
                title=title,
                content=content,
                clauses=clauses,
                structural_confidence=conf,
                start_pos=match.start(),
                end_pos=end_pos
            ))
            
        return nodes

    def _calculate_confidence(self, number: str, content: str) -> float:
        """GAP 5: Structural confidence logic"""
        conf = 1.0
        # Text too short
        if len(content) < 30: # Relaxed slightly
            conf -= 0.3
        # OCR Noise in number (e.g., 3B)
        if re.search(r'[0-9][A-Z]', number):
            conf -= 0.4
        # Suspect symbols (Replacement characters)
        if "\ufffd" in content or "\x00" in content:
            conf -= 0.2
            
        return max(conf, 0.3)

    def _bind_hierarchy(self, nodes: List[LegalSection], chapters: List[LegalSection], parts: List[LegalSection]):
        """GAP 7: Hierarchy binding (Chapter -> Sections)"""
        # Part -> Chapters -> Sections
        for node in nodes:
            # Find containing Part
            for p in reversed(parts):
                if p.start_pos < node.start_pos:
                    node.part = p.section_number
                    break
            
            # Find containing Chapter
            for c in reversed(chapters):
                if c.start_pos < node.start_pos:
                     # Validate chapter belongs to same Part or no part
                     node.chapter = c.section_number
                     break

    def get_section_text(self, text: str, section_number: str) -> Optional[str]:
        """Get text of a specific section (backward compatibility)"""
        res = self.parse(text)
        for node in res["sections"]:
            if node.section_number == section_number:
                return node.content
        return None