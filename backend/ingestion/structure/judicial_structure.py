"""
Judicial Structure Parser
Extracts Court Case structure: Facts, Arguments, Ratio, Judgment
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class JudicialIdentity:
    """Legal identity of the Judicial Document"""
    document_id: str
    court: Optional[str] = None
    bench: Optional[str] = None
    case_number: Optional[str] = None
    citation: Optional[str] = None
    date: Optional[str] = None
    parties: Dict[str, str] = field(default_factory=lambda: {"petitioner": "", "respondent": ""})
    counsel: Dict[str, List[str]] = field(default_factory=lambda: {"petitioner": [], "respondent": []})
    
    # Precedential Authority Metadata
    judicial_authority: Dict[str, Any] = field(default_factory=lambda: {
        "court_level": None,  # supreme_court | high_court | tribunal | district_court
        "binding_scope": "informative",  # binding | persuasive | informative
        "jurisdiction": None,  # AP | India | Nationwide
        "bench_strength": None
    })
    
    # Outcome Direction Metadata
    outcome: Dict[str, Any] = field(default_factory=lambda: {
        "petition_result": None,  # allowed | dismissed | partly_allowed
        "order_type": None  # directions | quashed | upheld | remanded
    })
    
    # Metadata
    doc_type: str = "judgment"  # judgment | guidelines | order
    confidence: str = "high"
    ocr_quality: Dict[str, Any] = field(default_factory=lambda: {
        "engine": "unknown",
        "confidence": 1.0,
        "warnings": []
    })

@dataclass
class JudicialSection:
    """Represents a judicial section"""
    section_type: str  # headnote, facts, issues, arguments_petitioner, arguments_respondent, ratio, judgment, order
    content: str
    start_pos: int
    end_pos: int
    page_no: Optional[int] = None
    visual_anchor: Optional[Dict] = None


class JudicialStructureParser:
    """
    Parse Judicial Document structure
    
    Judicial Structure:
    1. Case Information (parties, case number, court)
    2. Facts
    3. Arguments/Submissions
    4. Ratio Decidendi/Analysis
    5. Judgment/Order
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for judicial structure"""
        
        # Identity Patterns
        self.case_number_pattern = re.compile(
            r'(?:Case|Petition|Appeal|Crl\.A\.|W\.P\.|RT)\s*(?:No\.?|No(?:s)?\.?)\s*(\d+(?:/\d+)?(?:\(?\w+\)?)*)',
            re.IGNORECASE
        )
        self.date_pattern = re.compile(r'(?:Dated?|Date\s+of\s+Decision)[:\s]+(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})', re.IGNORECASE)
        self.court_pattern = re.compile(
            r'(?:Supreme\s+Court\s+of\s+India|High\s+Court\s+of\s+[A-Za-z\s]+|District\s+Court\s+at\s+[A-Za-z\s]+|IN\s+THE\s+HIGH\s+COURT\s+OF\s+[A-Za-z\s]+)',
            re.IGNORECASE
        )
        self.bench_pattern = re.compile(r'(?:BEFORE|CORAM|PRESENT|Bench)[:\s]+(.*?)(?=\n|$)', re.IGNORECASE)
        self.party_between_pattern = re.compile(r'Between[:\s\n]+(.*?)\n\s*AND\s*\n?(.*?)(?=\n\s*(?:JUDGMENT|ORDER|PRESENT|[:A-Z]+|$))', re.DOTALL | re.IGNORECASE)
        
        # Section markers - Relaxing anchors
        self.headnote_pattern = re.compile(
            r'(?:HEADNOTE|CATCHWORDS|SYLLABUS)[:\s]',
            re.IGNORECASE
        )
        
        self.facts_pattern = re.compile(
            r'(?:FACTS?|BACKGROUND|FACTUAL BACKGROUND|BRIEF FACTS)[:\s]',
            re.IGNORECASE
        )
        
        self.issues_pattern = re.compile(
            r'(?:ISSUES?|QUESTIONS? OF LAW|POINTS? FOR DETERMINATION)[:\s]',
            re.IGNORECASE
        )
        
        self.arguments_petitioner_pattern = re.compile(
            r'(?:SUBMISSIONS?\s+BY\s+THE\s+PETITIONER|ARGUMENTS?\s+OF\s+THE\s+APPELLANT|CONTENTIONS?\s+OF\s+THE\s+PETITIONER)[:\s]',
            re.IGNORECASE
        )
        
        self.arguments_respondent_pattern = re.compile(
            r'(?:SUBMISSIONS?\s+BY\s+THE\s+RESPONDENT|ARGUMENTS?\s+OF\s+THE\s+STATE|CONTENTIONS?\s+OF\s+THE\s+RESPONDENT)[:\s]',
            re.IGNORECASE
        )
        
        self.ratio_pattern = re.compile(
            r'(?:RATIO|RATIO DECIDENDI|REASONING|ANALYSIS|DISCUSSION|CONSIDERATION)[:\s]',
            re.IGNORECASE
        )
        
        self.judgment_pattern = re.compile(
            r'(?:JUDGMENT|DECISION|ORDER|HELD|CONCLUSION|COMMON JUDGMENT)[:\s]',
            re.IGNORECASE
        )
        
        # Citation pattern: e.g., (2018) 10 SCC 1
        self.citation_pattern = re.compile(r'\(\d{4}\)\s*\d+\s*[A-Z]{2,}\s*\d+', re.IGNORECASE)
        
        # Outcome Detection Patterns
        self.petition_allowed_pattern = re.compile(r'(?:petition|appeal|writ)\s+(?:is\s+)?(?:allowed|granted|accepted)', re.IGNORECASE)
        self.petition_dismissed_pattern = re.compile(r'(?:petition|appeal|writ)\s+(?:is\s+)?(?:dismissed|rejected)', re.IGNORECASE)
        self.petition_partly_pattern = re.compile(r'(?:petition|appeal|writ)\s+(?:is\s+)?(?:partly|partially)\s+(?:allowed|granted)', re.IGNORECASE)
        
        self.order_quashed_pattern = re.compile(r'(?:order|decision|judgment)\s+(?:is\s+)?(?:quashed|set\s+aside)', re.IGNORECASE)
        self.order_upheld_pattern = re.compile(r'(?:order|decision|judgment)\s+(?:is\s+)?(?:upheld|confirmed|sustained)', re.IGNORECASE)
        self.order_remanded_pattern = re.compile(r'(?:matter|case)\s+(?:is\s+)?(?:remanded|sent\s+back)', re.IGNORECASE)
        self.order_directions_pattern = re.compile(r'(?:direct|direction|order)\s+(?:the|that)', re.IGNORECASE)
    
    def parse(self, text: str, word_coords: Optional[List[Dict]] = None, ocr_metadata: Optional[Dict] = None) -> Dict:
        """
        Parse judicial document structure
        
        Args:
            text: Full judgment text
            word_coords: Optional visual coordinates
            ocr_metadata: Optional OCR quality info
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "identity": {},
                "has_structure": False,
                "sections": [],
            }
        
        # 1. Identity Extraction
        identity = self._extract_identity(text, ocr_metadata)
        
        # 2. Find sections
        sections = self._identify_sections(text, word_coords)
        
        return {
            "identity": asdict(identity),
            "has_structure": len(sections) > 1,
            "sections": [asdict(s) for s in sections],
            "section_types": [s.section_type for s in sections]
        }

    def _extract_identity(self, text: str, ocr_metadata: Optional[Dict]) -> JudicialIdentity:
        """Extract identity with legal precision"""
        header = text[:3000]
        
        # Detect Case Number
        cn_match = self.case_number_pattern.search(header)
        case_number = cn_match.group(1) if cn_match else None
        
        # Detect Court
        court_match = self.court_pattern.search(header)
        court = court_match.group(0) if court_match else None
        
        # Detect Date
        date_match = self.date_pattern.search(header)
        date = date_match.group(1) if date_match else None
        
        # Detect Bench
        bench_match = self.bench_pattern.search(header)
        bench = bench_match.group(0) if bench_match else None
        
        # Detect Citation
        cite_match = self.citation_pattern.search(header)
        citation = cite_match.group(0) if cite_match else None
        
        # Detect Parties
        parties = {"petitioner": "", "respondent": ""}
        party_match = self.party_between_pattern.search(header)
        if party_match:
            parties["petitioner"] = party_match.group(1).strip()
            parties["respondent"] = party_match.group(2).strip()
            
        # Detect Doc Type (Guidelines vs Judgment)
        doc_type = "judgment"
        if "guidelines" in text[:1000].lower() or "manual" in text[:1000].lower():
            doc_type = "guidelines"
        
        # Extract Judicial Authority
        judicial_authority = self._extract_judicial_authority(court, bench, doc_type)
        
        # Extract Outcome (from last 2000 chars - where orders typically appear)
        outcome = self._extract_outcome(text[-2000:])
            
        # Stable Document ID
        safe_cite = citation.replace(" ", "_") if citation else (case_number.replace("/", "_") if case_number else "UNK")
        doc_id = f"AP_JUD_{safe_cite}_{abs(hash(text[:100])) % 10000}"
        
        return JudicialIdentity(
            document_id=doc_id,
            court=court,
            bench=bench,
            case_number=case_number,
            citation=citation,
            date=date,
            parties=parties,
            judicial_authority=judicial_authority,
            outcome=outcome,
            doc_type=doc_type,
            ocr_quality=ocr_metadata or {}
        )
    
    def _extract_judicial_authority(self, court: Optional[str], bench: Optional[str], doc_type: str) -> Dict[str, Any]:
        """Extract precedential authority metadata"""
        authority = {
            "court_level": None,
            "binding_scope": "informative",
            "jurisdiction": "AP",  # Default to AP
            "bench_strength": None
        }
        
        if not court:
            return authority
        
        court_lower = court.lower()
        
        # Determine Court Level
        if "supreme court" in court_lower:
            authority["court_level"] = "supreme_court"
            authority["binding_scope"] = "binding"
            authority["jurisdiction"] = "Nationwide"
        elif "high court" in court_lower:
            authority["court_level"] = "high_court"
            authority["binding_scope"] = "binding"
            # Extract state from court name
            if "andhra pradesh" in court_lower or "ap" in court_lower:
                authority["jurisdiction"] = "AP"
            else:
                authority["jurisdiction"] = "India"
        elif "tribunal" in court_lower:
            authority["court_level"] = "tribunal"
            authority["binding_scope"] = "persuasive"
        elif "district" in court_lower:
            authority["court_level"] = "district_court"
            authority["binding_scope"] = "persuasive"
        
        # Guidelines are informative, not binding
        if doc_type == "guidelines":
            authority["binding_scope"] = "informative"
        
        # Extract Bench Strength
        if bench:
            # Count judges mentioned in bench
            judge_count = bench.lower().count("justice")
            if judge_count > 0:
                authority["bench_strength"] = judge_count
        
        return authority
    
    def _extract_outcome(self, conclusion_text: str) -> Dict[str, Any]:
        """Extract outcome direction from judgment conclusion"""
        outcome = {
            "petition_result": None,
            "order_type": None
        }
        
        if not conclusion_text:
            return outcome
        
        # Detect Petition Result
        if self.petition_partly_pattern.search(conclusion_text):
            outcome["petition_result"] = "partly_allowed"
        elif self.petition_allowed_pattern.search(conclusion_text):
            outcome["petition_result"] = "allowed"
        elif self.petition_dismissed_pattern.search(conclusion_text):
            outcome["petition_result"] = "dismissed"
        
        # Detect Order Type
        if self.order_quashed_pattern.search(conclusion_text):
            outcome["order_type"] = "quashed"
        elif self.order_upheld_pattern.search(conclusion_text):
            outcome["order_type"] = "upheld"
        elif self.order_remanded_pattern.search(conclusion_text):
            outcome["order_type"] = "remanded"
        elif self.order_directions_pattern.search(conclusion_text):
            outcome["order_type"] = "directions"
        
        return outcome
    
    def _identify_sections(self, text: str, word_coords: Optional[List[Dict]] = None) -> List[JudicialSection]:
        """Identify judicial sections with visual anchoring"""
        sections = []
        
        # Find all section markers
        markers = []
        
        for pattern, section_type in [
            (self.headnote_pattern, "headnote"),
            (self.facts_pattern, "facts"),
            (self.issues_pattern, "issues"),
            (self.arguments_petitioner_pattern, "arguments_petitioner"),
            (self.arguments_respondent_pattern, "arguments_respondent"),
            (self.ratio_pattern, "ratio"),
            (self.judgment_pattern, "judgment")
        ]:
            match = pattern.search(text)
            if match:
                markers.append((match.start(), section_type))
        
        # Sort by position
        markers.sort(key=lambda x: x[0])
        
        if not markers:
            # No clear structure
            return [JudicialSection(
                section_type="content",
                content=text,
                start_pos=0,
                end_pos=len(text),
                visual_anchor=self._find_visual_anchor(text[:500], word_coords) if word_coords else None
            )]
        
        # Extract sections
        for i, (start, section_type) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
            section_content = text[start:end].strip()
            
            if section_content:
                visual_anchor = None
                if word_coords:
                    visual_anchor = self._find_visual_anchor(section_content[:200], word_coords)
                    
                sections.append(JudicialSection(
                    section_type=section_type,
                    content=section_content,
                    start_pos=start,
                    end_pos=end,
                    visual_anchor=visual_anchor
                ))
        
        # Add preamble if exists
        if markers[0][0] > 0:
            preamble = text[:markers[0][0]].strip()
            if preamble:
                sections.insert(0, JudicialSection(
                    section_type="preamble",
                    content=preamble,
                    start_pos=0,
                    end_pos=markers[0][0],
                    visual_anchor=self._find_visual_anchor(preamble[:200], word_coords) if word_coords else None
                ))
        
        return sections

    def _find_visual_anchor(self, content: str, word_coords: List[Dict]) -> Optional[Dict]:
        """Find visual coordinates for text"""
        if not word_coords: return None
        search_tokens = content.split()[:5]
        if not search_tokens: return None
        
        # Simple placeholder for visual anchoring (first match of first word)
        first_word = search_tokens[0]
        for word in word_coords:
            if first_word in word.get("text", ""):
                return {"page": word.get("page", 0), "bbox": word.get("bbox")}
        
        return {"page": word_coords[0].get("page", 0)}