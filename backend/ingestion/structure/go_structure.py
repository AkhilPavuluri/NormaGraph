"""
GO Structure Parser - Legal Grade Implementation
Extracts Government Order structure with legal precision, confidence scoring, and OCR defense.
"""
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class GOIdentity:
    """Legal identity of the Government Order"""
    document_id: str
    go_type: Optional[str] = None
    go_number: Optional[str] = None
    raw_go_number: Optional[str] = None
    year: Optional[str] = None
    department: Optional[str] = None
    date: Optional[str] = None
    issuing_authority: Optional[str] = None
    
    # Confidence & Authority
    go_number_confidence: str = "high"  # high | low
    document_authority: str = "authoritative"  # authoritative | non_authoritative | advisory
    
    ocr_quality: Dict[str, Any] = field(default_factory=lambda: {
        "engine": "unknown",
        "confidence": 1.0,
        "warnings": []
    })

@dataclass
class GOReference:
    """Reference to another document"""
    ref_text: str
    confidence: str = "explicit"  # explicit | implicit

@dataclass
class GOPreamble:
    """Preamble context"""
    text: str
    references: List[GOReference] = field(default_factory=list)
    visual_anchor: Optional[Dict] = None

@dataclass
class GOTargetReference:
    """Specific target of a legal action"""
    go_number: Optional[str] = None
    year: Optional[str] = None
    para: Optional[str] = None
    raw_text: Optional[str] = None

@dataclass
class GOClause:
    """Atomic legal clause within an order"""
    clause_id: str
    text: str
    legal_operator: Optional[str] = None  # shall | may | must
    has_condition: bool = False

@dataclass
class GOOrder:
    """Operative part of the GO"""
    para_no: str
    text: str
    
    # Clauses (Atomic Units)
    clauses: List[GOClause] = field(default_factory=list)
    
    # Legal Effect
    legal_effect: Optional[str] = None  # supersedes_entirely | supersedes_partially | amends | clarifies | rescinds | operational_instruction
    override_scope: Optional[str] = None  # entire_go | specific_para | subject_only
    invalidates_prior: bool = False
    
    # References & Validity
    target_refs: List[GOTargetReference] = field(default_factory=list)
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    is_current: bool = True
    
    # Anchors
    structural_confidence: str = "high"  # high | low
    visual_anchor: Optional[Dict] = None

@dataclass
class GOAnnexure:
    """Annexure attachment"""
    annexure_id: str
    text: str
    linked_para: Optional[str] = None
    type: str = "text"  # text | table | form
    visual_anchor: Optional[Dict] = None

class GOStructureParser:
    """
    Legal-Grade Government Order Parser
    
    Implements:
    1. Structure-First Ingestion
    2. Legal Logic Extraction (Effects, Scope, Validity)
    3. OCR Defense (Confidence Scoring, Safe Recovery)
    """
    
    def __init__(self):
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile comprehensive regex patterns"""
        # Identity Patterns
        self.go_num_pattern = re.compile(r'G\.?O\.?(?:Ms|Rt)?\.?\s*No\.?\s*([0-9A-Z]+)', re.IGNORECASE)
        self.date_pattern = re.compile(r'Dated?[:\.]?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})', re.IGNORECASE)
        self.dept_pattern = re.compile(r'(?:Department|Dept\.?)\s+of\s+([A-Z][A-Za-z\s&]+?)(?:,|\.|\n)', re.IGNORECASE)
        
        # Structure Markers
        self.order_start = re.compile(r'^\s*ORDER[S]?\s*:?\s*$', re.IGNORECASE | re.MULTILINE)
        self.annexure_start = re.compile(r'^\s*ANNEXURE', re.IGNORECASE | re.MULTILINE)
        self.preamble_end = re.compile(r'(?:NOW,?\s+THEREFORE|WHEREAS|In exercise of)', re.IGNORECASE)
        
        # Paragraph Numbering (Robust)
        # Matches: 1. | 1) | (1) | 4(I). | 4(a)
        self.para_pattern = re.compile(r'^\s*((?:(?:\d+|[a-zA-Z]+)[\.\)]|(?:\d+|[a-zA-Z]+)\([0-9a-zA-Z]+\)\.?|\([0-9a-zA-Z]+\)))\s+', re.MULTILINE)
        
        # Legal Effects
        self.effect_patterns = {
            "supersedes_entirely": [r'supersedes?\s+orders?', r'in\s+supersession\s+of'],
            "amends": [r'amendment\s+to', r'following\s+amendment', r'substituted'],
            "rescinds": [r'hereby\s+rescinded', r'cancelled'],
            "clarifies": [r'clarification', r'clarified'],
        }
        
        # Temporal Validity
        self.validity_patterns = {
            "effective_from": [
                r'comes?\s+into\s+force\s+(?:with\s+effect\s+)?from\s+([0-9\-\./]+)',
                r'effective\s+from\s+([0-9\-\./]+)'
            ],
            "academic_year": [r'academic\s+year\s+(\d{4}-\d{2,4})']
        }

    def parse(self, text: str, word_coords: Optional[List[Dict]] = None, ocr_metadata: Optional[Dict] = None) -> Dict:
        """
        Parse text into strict legal schema.
        
        Args:
            text: Full document text
            word_coords: Optional visual coordinates
            ocr_metadata: Optional OCR quality info
            
        Returns:
            Dictionary matching the Legal GO Schema
        """
        if not text:
            return {}

        # 1. Identity Extraction (Dual Strategy Placeholder)
        identity = self._extract_identity(text, ocr_metadata)
        
        # 2. Section Splitting
        preamble_text, orders_text, annexures_text = self._split_sections(text)
        
        # 3. Preamble Parsing
        preamble = self._parse_preamble(preamble_text, word_coords)
        
        # 4. Order Parsing (The Core)
        orders = self._parse_orders(orders_text, identity.year, word_coords)
        
        # 5. Annexure Parsing
        annexures = self._parse_annexures(annexures_text, word_coords)
        
        # Construct Final Result
        return {
            "identity": asdict(identity),
            "preamble": asdict(preamble),
            "orders": [asdict(o) for o in orders],
            "annexures": [asdict(a) for a in annexures],
            "has_structure": bool(orders)
        }

    def _extract_identity(self, text: str, ocr_metadata: Optional[Dict]) -> GOIdentity:
        """Extract identity with strict validation"""
        # Default defaults
        confidence = "high"
        authority = "authoritative"
        
        # Extract GO Number
        go_match = self.go_num_pattern.search(text[:1000])
        raw_go_number = go_match.group(1) if go_match else None
        go_number = None
        
        # GAP 1: Strict Validation
        if raw_go_number and raw_go_number.isdigit():
            go_number = raw_go_number
        elif raw_go_number:
            # Capture it but don't trust it
            confidence = "low"
            authority = "non_authoritative"
        else:
            confidence = "low"
            authority = "non_authoritative"
            
        # Extract Date/Year
        date_match = self.date_pattern.search(text[:1000])
        date = date_match.group(1) if date_match else None
        year = date.split('-')[-1] if date else None
        if year and len(year) == 2:
            year = "20" + year
            
        # Extract Department
        dept_match = self.dept_pattern.search(text[:1000])
        dept = dept_match.group(1) if dept_match else None
        
        # GAP 2: Stable Document ID
        if confidence == "high" and go_number and year:
            doc_id = f"AP_GO_{go_number}_{year}"
        else:
            # Fallback that doesn't look authoritative
            doc_id = f"AP_GO_UNKNOWN_{year or 'UNK'}_{abs(hash(text[:100]))}"
        
        return GOIdentity(
            document_id=doc_id,
            go_number=go_number,
            raw_go_number=raw_go_number,
            year=year,
            date=date,
            department=dept,
            go_number_confidence=confidence,
            document_authority=authority,
            ocr_quality=ocr_metadata or {}
        )

    def _split_sections(self, text: str):
        """Split text into Preamble, Orders, Annexures"""
        # Find Order Start
        order_match = self.order_start.search(text)
        if not order_match:
            # Fallback 1: Try splitting by preamble end (e.g., "NOW THEREFORE")
            preamble_match = self.preamble_end.search(text)
            if preamble_match:
                preamble = text[:preamble_match.end()].strip()
                rest = text[preamble_match.end():].strip()
                # Check for Annexure in rest
                annex_match = self.annexure_start.search(rest)
                if annex_match:
                     return preamble, rest[:annex_match.start()].strip(), rest[annex_match.start()].strip()
                return preamble, rest, ""
            
            # Fallback 2: Treat everything as "Order" context so we at least process it
            # This allows _parse_orders to pick it up as "Para 1" via Safe Para Recovery
            logger.warning("No structure markers found, treating entire text as Order content")
            return "", text, "" 
            
        preamble = text[:order_match.start()].strip()
        rest = text[order_match.end():].strip()
        
        # Find Annexure Start
        annex_match = self.annexure_start.search(rest)
        if annex_match:
            orders = rest[:annex_match.start()].strip()
            annexures = rest[annex_match.start()].strip()
        else:
            orders = rest
            annexures = ""
            
        return preamble, orders, annexures

    def _parse_preamble(self, text: str, word_coords: Optional[List[Dict]] = None) -> GOPreamble:
        """Parse preamble for references"""
        refs = []
        # Basic reference extraction logic
        ref_pattern = re.compile(r'G\.?O\.?(?:Ms|Rt)?\.?\s*No\.?\s*(\d+)', re.IGNORECASE)
        for m in ref_pattern.finditer(text):
            refs.append(GOReference(ref_text=m.group(0), confidence="explicit"))
            
        visual_anchor = None
        if word_coords:
            visual_anchor = self._find_visual_anchor(text, word_coords)

        return GOPreamble(text=text, references=refs, visual_anchor=visual_anchor)

    def _parse_orders(self, text: str, current_year: Optional[str], word_coords: Optional[List[Dict]]) -> List[GOOrder]:
        """Parse orders into atomic paragraphs with legal metadata"""
        if not text:
            return []
            
        orders = []
        
        # Split by paragraphs
        # This is a critical step. We identify numbered paragraphs.
        # If no numbering is found, we might treat it as a single block or use layout detection.
        
        matches = list(self.para_pattern.finditer(text))
        
        if not matches:
            # Safe Para Recovery: Treat as one single order if no numbering
            orders.append(self._analyze_order_content(
                "1", text, current_year, word_coords, confidence="low"
            ))
            return orders
            
        for i, match in enumerate(matches):
            para_no = match.group(1).strip('.)') # clean numbers like "1." -> "1"
            
            # GAP 3: Exclude the number token from the content
            # match.end() gives the end of the pattern (number + whitespace due to \s+ in regex)
            start_content = match.end() 
            
            end = matches[i+1].start() if i+1 < len(matches) else len(text)
            content = text[start_content:end].strip()
            
            # Create Order Object
            order = self._analyze_order_content(
                para_no, content, current_year, word_coords
            )
            orders.append(order)
            
        return orders

    def _analyze_order_content(self, para_no: str, text: str, current_year: Optional[str], 
                             word_coords: Optional[List[Dict]], confidence: str = "high") -> GOOrder:
        """
        Analyze the text of a single order paragraph to extract legal semantics.
        """
        # 1. Detect Legal Effect
        legal_effect = None
        invalidates_prior = False
        override_scope = None
        
        text_lower = text.lower()
        
        if "supersedes" in text_lower or "supersession" in text_lower:
            if "partially" in text_lower or "to the extent" in text_lower or "subject" in text_lower:
                legal_effect = "supersedes_partially"
                override_scope = "specific_para" if "orders issued" in text_lower else "subject_only"
            else:
                 legal_effect = "supersedes_entirely"
                 override_scope = "entire_go"
                 
        elif "amend" in text_lower:
            legal_effect = "amends"
            override_scope = "specific_para"
        elif "clarif" in text_lower:
            legal_effect = "clarifies"
        
        # GAP 4: Strict Invalidation
        # Only true if explicit repeal/rescind
        if "hereby rescinded" in text_lower or "stands repealed" in text_lower or ("supersedes" in text_lower and "entirety" in text_lower):
            invalidates_prior = True
        else:
            invalidates_prior = False
            
        # 2. Extract Target References (e.g., "G.O.Ms.No. 24")
        target_refs = []
        ref_matches = self.go_num_pattern.finditer(text)
        for m in ref_matches:
            target_refs.append(GOTargetReference(
                go_number=m.group(1),
                raw_text=m.group(0)
            ))
            
        # 3. Extract Validity
        effective_from = None
        for pattern in self.validity_patterns["effective_from"]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                effective_from = m.group(1)
                break
        
        # GAP 5: Calculate is_current
        is_current = True
        if self.validity_patterns.get("effective_to"): 
            # Placeholder for effective_to logic if extracted
            pass
                
        # 4. Visual Anchor (Placeholder logic)
        visual_anchor = None
        if word_coords:
            visual_anchor = self._find_visual_anchor(text, word_coords)

        # 5. Split into Atomic Clauses
        clauses = self._split_into_clauses(text, para_no)

        return GOOrder(
            para_no=para_no,
            text=text,
            clauses=clauses,
            legal_effect=legal_effect,
            override_scope=override_scope,
            invalidates_prior=invalidates_prior,
            target_refs=target_refs,
            effective_from=effective_from,
            structural_confidence=confidence,
            visual_anchor=visual_anchor
        )

    def _split_into_clauses(self, para_text: str, para_no: str) -> List[GOClause]:
        """
        Split a paragraph into atomic legal clauses.
        """
        clauses = []
        
        # 1. Detect sub-numbering like (1), (2), (a), (b), (i), (ii)
        sub_pattern = re.compile(r'(?:\s|^)\(([IVXivx0-9a-z]+)\)')
        sub_matches = list(sub_pattern.finditer(para_text))
        
        if sub_matches and len(sub_matches) > 0:
            # We have sub-clauses
            
            # Text before first match
            first_start = sub_matches[0].start()
            if first_start > 0:
                preamble = para_text[:first_start].strip()
                if preamble:
                     clauses.append(GOClause(
                         clause_id=f"{para_no}(pre)",
                         text=preamble
                     ))
            
            for i, match in enumerate(sub_matches):
                sub_id = match.group(1)
                start = match.end() # Start of content
                
                # End is start of next match or end of text
                if i + 1 < len(sub_matches):
                    end = sub_matches[i+1].start()
                else:
                    end = len(para_text)
                
                clause_text = para_text[start:end].strip(" ;,.")
                
                # Check for legal operator
                op = None
                if "shall" in clause_text.lower(): op = "shall"
                elif "must" in clause_text.lower(): op = "must"
                elif "may" in clause_text.lower(): op = "may"
                
                clauses.append(GOClause(
                    clause_id=f"{para_no}({sub_id})",
                    text=clause_text,
                    legal_operator=op,
                    has_condition="subject to" in clause_text.lower() or "provided" in clause_text.lower()
                ))
                
        else:
            # No explicitly numbered sub-clauses.
            clause_text = para_text
            op = None
            if "shall" in clause_text.lower(): op = "shall"
            elif "must" in clause_text.lower(): op = "must"
            elif "may" in clause_text.lower(): op = "may"
            
            # Split by "Provided that" or "Subject to" at sentence boundaries
            parts = re.split(r'\.\s+(Provided that|Subject to)', clause_text, flags=re.IGNORECASE)
            if len(parts) > 1:
                # Part 0 is main clause
                clauses.append(GOClause(
                    clause_id=f"{para_no}(main)",
                    text=parts[0].strip(),
                    legal_operator=op
                ))
                
                # Remaining parts are condition clauses
                current_clause_id = 1
                i = 1
                while i < len(parts):
                    cond_marker = parts[i]
                    cond_text = parts[i+1] if i+1 < len(parts) else ""
                    full_cond = f"{cond_marker} {cond_text}".strip()
                    
                    clauses.append(GOClause(
                        clause_id=f"{para_no}(proviso_{current_clause_id})",
                        text=full_cond,
                        has_condition=True 
                    ))
                    current_clause_id += 1
                    i += 2
            else:
                # Single clause
                clauses.append(GOClause(
                    clause_id=f"{para_no}",
                    text=clause_text,
                    legal_operator=op,
                    has_condition="subject to" in clause_text.lower()
                ))
                
        return clauses

    def _parse_annexures(self, text: str, word_coords: Optional[List[Dict]] = None) -> List[GOAnnexure]:
        """Parse annexures with splitting"""
        if not text:
            return []
            
        # GAP 6: Safe Splitting
        # Split by "ANNEXURE X"
        splitter = re.compile(r'(ANNEXURE\s*[-:\s]?[IVX0-9]+)', re.IGNORECASE)
        parts = splitter.split(text)
        
        annexures = []
        if len(parts) > 1:
            # parts[0] is preamble before first annexure (usually empty or noise)
            # parts[1] is header 1, parts[2] is content 1, parts[3] is header 2...
            for i in range(1, len(parts), 2):
                header = parts[i].strip()
                content = parts[i+1].strip() if i+1 < len(parts) else ""
                
                # Check for table markers
                a_type = "text"
                if re.search(r'\|.*\|', content) or re.search(r'\s{4,}', content):
                    a_type = "table"
                    
                # Visual Anchor
                v_anchor = None
                if word_coords:
                    v_anchor = self._find_visual_anchor(content, word_coords)

                annexures.append(GOAnnexure(
                    annexure_id=header.replace(" ", "-").upper(),
                    text=content,
                    type=a_type,
                    visual_anchor=v_anchor
                ))
        else:
             # Fallback if no explicit Annexure X found
             v_anchor = None
             if word_coords:
                 v_anchor = self._find_visual_anchor(text, word_coords)
             annexures.append(GOAnnexure(annexure_id="ANNEXURE-GEN", text=text, visual_anchor=v_anchor))
             
        return annexures

    def _find_visual_anchor(self, content: str, word_coords: List[Dict]) -> Optional[Dict]:
        """
        Calculates bounding box for a paragraph by matching its first few words
        against the captured word coordinates.
        """
        if not word_coords or not content.strip():
            return None

        # Clean and tokenize the first few words of the paragraph
        # We use a subset for faster matching and because OCR/Text extraction
        # can have slight variations in long paragraphs.
        content_tokens = [t.strip('.,()') for t in content.split() if len(t.strip('.,()')) > 1]
        if not content_tokens:
            return None
        
        # We'll try to find a sequence of 4-6 tokens
        window_size = min(len(content_tokens), 5)
        search_sequence = content_tokens[:window_size]
        
        # Simple sliding window search over word_coords
        for i in range(len(word_coords) - window_size + 1):
            match = True
            for j in range(window_size):
                coord_text = word_coords[i+j]["text"].strip('.,()')
                if search_sequence[j].lower() != coord_text.lower():
                    match = False
                    break
            
            if match:
                # Found the start! Now expand to get the full para bbox?
                # Actually, for "anchoring", the start of the para is usually enough
                # but let's try to find the "end" token to get a better box if possible.
                # For now, let's return the bbox of the first line or first few words.
                
                # Get page from the first word
                page = word_coords[i]["page"]
                
                # Calculate aggregated bbox [x0, y0, x1, y1] for the sequence
                x0 = min(word_coords[i+k]["bbox"][0] for k in range(window_size))
                y0 = min(word_coords[i+k]["bbox"][1] for k in range(window_size))
                x1 = max(word_coords[i+k]["bbox"][2] for k in range(window_size))
                y1 = max(word_coords[i+k]["bbox"][3] for k in range(window_size))
                
                return {
                    "page": page,
                    "bbox": [round(x, 2) for x in [x0, y0, x1, y1]],
                    "text_snippet": " ".join(search_sequence)
                }
                
        return None