"""
Data Structure Parser
Extracts Data Report structure: Tables, Charts, Analysis Sections
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class DataIdentity:
    """Legal identity of the Data Report"""
    document_id: str
    report_type: Optional[str] = None  # UDISE+, NAS, Budget, Annexure, etc.
    year: Optional[str] = None
    period: Optional[str] = None
    state: Optional[str] = "Andhra Pradesh"
    scope: Optional[str] = "State"  # State, District, Block, National
    department: Optional[str] = None
    
    # Document Intent Classification
    data_intent: str = "informational"  # informational | recommendatory | financial | statistical
    
    # Temporal Scope Metadata
    temporal_scope: Dict[str, Any] = field(default_factory=lambda: {
        "financial_year": None,  # "2023-24"
        "applicable_period": None,  # "2023-2026"
        "is_historical": False
    })
    
    # Numeric Confidence Control
    numeric_metadata: Dict[str, Any] = field(default_factory=lambda: {
        "contains_financials": False,
        "numeric_confidence": "high"  # high | medium | low
    })
    
    # Confidence & Quality
    confidence: str = "high"
    ocr_quality: Dict[str, Any] = field(default_factory=lambda: {
        "engine": "unknown",
        "confidence": 1.0,
        "warnings": []
    })

@dataclass
class DataSection:
    """Represents a data report section"""
    section_type: str  # table, chart, analysis, summary, metric_summary, geographic_breakdown
    title: Optional[str]
    content: str
    start_pos: int
    end_pos: int
    page_no: Optional[int] = None
    table_number: Optional[str] = None
    table_data: Optional[List[List[str]]] = None
    columns: Optional[List[str]] = None
    visual_anchor: Optional[Dict] = None
    is_garbled: bool = False


class DataStructureParser:
    """
    Parse Data Report structure
    
    Data Structure:
    1. Executive Summary
    2. Tables
    3. Charts/Figures
    4. Analysis Sections
    5. Conclusions
    """
    
    def __init__(self):
        # Compile patterns
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for data structure"""
        
        # Identity Patterns
        self.report_type_patterns = {
            "UDISE+": [r'UDISE\+', r'Unified\s+District\s+Information\s+System'],
            "NAS": [r'National\s+Achievement\s+Survey', r'NAS\s*20\d{2}'],
            "Budget": [r'Budget\s+Analysis', r'Budget\s+Estimates', r'Demand\s+for\s+Grants'],
            "Annexure": [r'Annexure', r'Appendix'],
        }
        
        self.year_pattern = re.compile(r'20\d{2}[-\s/]\d{2,4}')
        self.dept_pattern = re.compile(r'(?:Department|Dept\.?)\s+of\s+([A-Z][A-Za-z\s&]+?)(?:,|\.|\n|$)', re.IGNORECASE)
        self.budget_volume_pattern = re.compile(r'Volume\s*[-:\s]*([IVX0-9]+)', re.IGNORECASE)
        
        # Enhanced table caption patterns (including Bilingual support)
        self.table_caption_patterns = [
            re.compile(r'(?:Table|TABLE)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?=\n|$)', re.IGNORECASE),
            re.compile(r'(?:Table|TABLE)\s+(\d+(?:\.\d+)?)\s*[:-]\s*(.+?)(?=\n|$)', re.IGNORECASE),
            re.compile(r'(?:Annexure|ANNEXURE)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?=\n|$)', re.IGNORECASE),
            # Telugu/Bilingual support placeholder (e.g., Demand Reference)
            # Adding a second optional group to match the expected index (table_num, table_title)
            re.compile(r'(?:Demand\s+Reference|Demand\s*Number)\s*[:\.]?\s*([A-Za-z0-9]+)(.*)', re.IGNORECASE)
        ]
        
        # Table content detection patterns
        self.table_content_patterns = [
            re.compile(r'(\s{3,}\S+){3,}'),  # Multiple columns separated by spaces
            re.compile(r'\|[^\n]*\|[^\n]*\|'),  # Pipe-separated data
            re.compile(r'\t[^\n]*\t[^\n]*\t'),  # Tab-separated data
            re.compile(r'^\s*\d+[\.\)]\s+[^\n]*\d+[^\n]*$', re.MULTILINE)  # Numbered rows with data
        ]
        
        # GARBLED detection (OCR fallback trigger)
        self.garbled_pattern = re.compile(r'\(cid:\d+\)')
        
        # Chart/Figure markers
        self.chart_pattern = re.compile(
            r'(?:Figure|Chart|Graph|FIGURE|CHART|GRAPH)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)(?:\n|$)',
            re.IGNORECASE
        )
        
        # Chapter/Section markers
        self.section_pattern = re.compile(
            r'^(?:Chapter|Section|CHAPTER|SECTION)\s+(\d+(?:\.\d+)?)[:\.]?\s*(.+?)$',
            re.MULTILINE
        )
        
        # Metric patterns (Financial, Demographic)
        self.metric_patterns = {
            "currency": re.compile(r'(?:Rs\.?|Rupees|INR)\s*(?:in\s+)?(?:Lakhs|Crores|Millions)?', re.IGNORECASE),
            "percentage": re.compile(r'\d+(?:\.\d+)?\s*%'),
            "growth": re.compile(r'(?:growth|increase|decrease)\s+of\s+\d+', re.IGNORECASE)
        }
        
        # Summary markers
        self.summary_pattern = re.compile(
            r'^(?:SUMMARY|EXECUTIVE SUMMARY|CONCLUSION|CONCLUSIONS)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
    
    def parse(self, text: str, word_coords: Optional[List[Dict]] = None, ocr_metadata: Optional[Dict] = None) -> Dict:
        """
        Parse data report structure
        
        Args:
            text: Full report text
            word_coords: Optional visual coordinates
            ocr_metadata: Optional OCR quality info
            
        Returns:
            Dictionary with structure info
        """
        if not text:
            return {
                "identity": {},
                "has_structure": False,
                "tables": [],
                "charts": [],
                "sections": []
            }
        
        # 1. Identity Extraction
        identity = self._extract_identity(text, ocr_metadata)
        
        # 2. Find tables
        tables = self._find_tables(text, word_coords)
        
        # 3. Find charts
        charts = self._find_charts(text)
        
        # 4. Find sections
        sections = self._find_sections(text)
        
        return {
            "identity": asdict(identity),
            "has_structure": len(tables) > 0 or len(charts) > 0 or len(sections) > 0,
            "tables": [asdict(t) for t in tables],
            "charts": [asdict(c) for c in charts],
            "sections": [asdict(s) for s in sections],
            "table_count": len(tables),
            "chart_count": len(charts),
            "section_count": len(sections),
            "table_numbers": [t.table_number for t in tables if t.table_number],
            "structured_tables": [asdict(t) for t in tables if t.table_data],
            "is_garbled": bool(self.garbled_pattern.search(text[:2000]))
        }

    def _extract_identity(self, text: str, ocr_metadata: Optional[Dict]) -> DataIdentity:
        """Extract report identity with validation"""
        # Default identity
        report_type = "Other Data Report"
        year = None
        period = None
        dept = None
        confidence = "high"
        
        text_top = text[:2000]
        
        # Detect Report Type
        for r_type, patterns in self.report_type_patterns.items():
            for p in patterns:
                if re.search(p, text_top, re.IGNORECASE):
                    report_type = r_type
                    break
            if report_type != "Other Data Report":
                break
                
        # Handle cases like "Volume-III"
        vol_match = self.budget_volume_pattern.search(text_top)
        if vol_match and report_type == "Budget":
            report_type = f"Budget Volume {vol_match.group(1)}"
            
        # Detect Year/Period
        year_match = self.year_pattern.search(text_top)
        if year_match:
            period = year_match.group(0)
            year = period.split('-')[0] if '-' in period else period
            
        # Detect Department
        dept_match = self.dept_pattern.search(text_top)
        dept = dept_match.group(1).strip() if dept_match else None
        
        # Stable Document ID
        safe_type = report_type.replace(" ", "_").upper()
        safe_year = year or "UNK"
        doc_id = f"AP_DATA_{safe_type}_{safe_year}_{abs(hash(text[:100])) % 10000}"
        
        # Garbled Detection
        if self.garbled_pattern.search(text_top):
            confidence = "low"
        
        # Extract Data Intent
        data_intent = self._classify_data_intent(report_type, text_top)
        
        # Extract Temporal Scope
        temporal_scope = self._extract_temporal_scope(text_top, period, year)
        
        # Extract Numeric Metadata
        numeric_metadata = self._extract_numeric_metadata(text, confidence)
            
        return DataIdentity(
            document_id=doc_id,
            report_type=report_type,
            year=year,
            period=period,
            department=dept,
            data_intent=data_intent,
            temporal_scope=temporal_scope,
            numeric_metadata=numeric_metadata,
            confidence=confidence,
            ocr_quality=ocr_metadata or {}
        )
    
    def _classify_data_intent(self, report_type: str, text_sample: str) -> str:
        """Classify document intent based on report type and content"""
        # Budget/Financial reports
        if "budget" in report_type.lower() or "financial" in report_type.lower():
            return "financial"
        
        # Statistical reports (UDISE, NAS)
        if any(x in report_type.upper() for x in ["UDISE", "NAS", "STATISTICS"]):
            return "statistical"
        
        # Guidelines are recommendatory
        if "guideline" in text_sample.lower() or "recommendation" in text_sample.lower():
            return "recommendatory"
        
        # Default
        return "informational"
    
    def _extract_temporal_scope(self, text_sample: str, period: Optional[str], year: Optional[str]) -> Dict[str, Any]:
        """Extract temporal scope metadata"""
        temporal = {
            "financial_year": None,
            "applicable_period": None,
            "is_historical": False
        }
        
        # Financial Year detection: "2023-24", "FY 2023-24"
        fy_match = re.search(r'(?:FY|Financial Year)\s*(\d{4}-\d{2,4})', text_sample, re.IGNORECASE)
        if fy_match:
            temporal["financial_year"] = fy_match.group(1)
        elif period and '-' in period:
            temporal["financial_year"] = period
        
        # Applicable Period: "2023-2026", "2023 to 2026"
        period_match = re.search(r'(\d{4})\s*(?:to|-)\s*(\d{4})', text_sample)
        if period_match:
            temporal["applicable_period"] = f"{period_match.group(1)}-{period_match.group(2)}"
        
        # Historical flag: if year is more than 2 years old
        if year:
            try:
                from datetime import datetime
                current_year = datetime.now().year
                doc_year = int(year)
                temporal["is_historical"] = (current_year - doc_year) > 2
            except:
                pass
        
        return temporal
    
    def _extract_numeric_metadata(self, text: str, confidence: str) -> Dict[str, Any]:
        """Extract numeric confidence metadata"""
        numeric_meta = {
            "contains_financials": False,
            "numeric_confidence": "high"
        }
        
        # Detect financial content
        if self.metric_patterns["currency"].search(text[:3000]):
            numeric_meta["contains_financials"] = True
        
        # Numeric confidence is low if document is garbled
        if confidence == "low":
            numeric_meta["numeric_confidence"] = "low"
        else:
            # Check for high density of numbers (could indicate tables)
            digit_density = sum(c.isdigit() for c in text[:2000]) / max(1, len(text[:2000]))
            if digit_density > 0.15:
                numeric_meta["numeric_confidence"] = "high"
            else:
                numeric_meta["numeric_confidence"] = "medium"
        
        return numeric_meta
    
    def _find_tables(self, text: str, word_coords: Optional[List[Dict]] = None) -> List[DataSection]:
        """Find all tables in the document with enhanced detection"""
        tables = []
        
        # Find table captions first
        table_captions = self.detect_table_captions(text)
        
        for caption in table_captions:
            table_num = caption['number']
            table_title = caption['title']
            caption_pos = caption['position']
            
            # Find table content after caption
            table_block = self.detect_table_block(text, caption_pos)
            
            if table_block:
                # Detect if garbled
                is_garbled = bool(self.garbled_pattern.search(table_block['content']))
                
                # Visual Anchor (Placeholder)
                visual_anchor = None
                if word_coords:
                    visual_anchor = self._find_visual_anchor(table_block['content'], word_coords)
                
                tables.append(DataSection(
                    section_type="table",
                    title=f"Table {table_num}: {table_title}" if table_title else f"Table {table_num}",
                    content=table_block['content'],
                    start_pos=caption_pos,
                    end_pos=table_block['end_pos'],
                    table_number=table_num,
                    table_data=table_block.get('table_data'),
                    columns=table_block.get('columns'),
                    is_garbled=is_garbled,
                    visual_anchor=visual_anchor
                ))
        
        return tables
    
    def detect_table_captions(self, text: str) -> List[Dict]:
        """Detect table captions using enhanced patterns"""
        captions = []
        
        for pattern in self.table_caption_patterns:
            for match in pattern.finditer(text):
                table_num = match.group(1)
                table_title = match.group(2).strip() if match.group(2) else ""
                
                captions.append({
                    'number': table_num,
                    'title': table_title,
                    'position': match.start(),
                    'caption_end': match.end()
                })
        
        # Sort by position
        captions.sort(key=lambda x: x['position'])
        return captions
    
    def detect_table_block(self, text: str, caption_pos: int) -> Optional[Dict]:
        """Detect table content block after caption"""
        # Start search after caption
        search_start = caption_pos
        caption_match = None
        
        # Find the caption end
        for pattern in self.table_caption_patterns:
            match = pattern.search(text[caption_pos:caption_pos+200])
            if match:
                caption_match = match
                break
        
        if not caption_match:
            return None
        
        content_start = caption_pos + caption_match.end()
        
        # Look for table content in next 2000 characters
        search_text = text[content_start:content_start+2000]
        
        # Find table boundaries
        table_content_lines = []
        table_data = []
        columns = []
        
        lines = search_text.split('\n')
        in_table = False
        table_end_pos = content_start
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines at start
            if not line_stripped and not in_table:
                continue
            
            # Check if this line looks like table content
            if self.is_table_content_line(line):
                in_table = True
                table_content_lines.append(line)
                
                # Parse table data
                row_data = self.parse_table_row(line)
                if row_data:
                    table_data.append(row_data)
                    
                    # Extract column headers from first data row
                    if len(table_data) == 1 and not columns:
                        columns = row_data[:]
                
                table_end_pos = content_start + len('\n'.join(lines[:i+1]))
            
            # Stop if we hit another table caption or section
            elif in_table and (self.is_new_section(line) or len(table_content_lines) > 50):
                break
            
            # Continue collecting if we're in a table
            elif in_table:
                table_content_lines.append(line)
                table_end_pos = content_start + len('\n'.join(lines[:i+1]))
        
        if table_content_lines:
            full_content = text[caption_pos:table_end_pos]
            return {
                'content': full_content,
                'end_pos': table_end_pos,
                'table_data': table_data if table_data else None,
                'columns': columns if columns else None
            }
        
        # Fallback: include some text after caption
        fallback_end = min(content_start + 1000, len(text))
        return {
            'content': text[caption_pos:fallback_end],
            'end_pos': fallback_end,
            'table_data': None,
            'columns': None
        }
    
    def is_table_content_line(self, line: str) -> bool:
        """Check if a line contains table content"""
        if not line.strip():
            return False
        
        # Check against table content patterns
        for pattern in self.table_content_patterns:
            if pattern.search(line):
                return True
        
        # Additional heuristics
        # High digit density
        digits = sum(c.isdigit() for c in line)
        if digits > 5 and digits / len(line) > 0.1:
            return True
        
        # Multiple numeric values
        numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', line)
        if len(numbers) >= 3:
            return True
        
        return False
    
    def parse_table_row(self, line: str) -> Optional[List[str]]:
        """Parse a table row into columns"""
        line = line.strip()
        
        # Try different separators
        separators = ['|', '\t', '  ', '   ', '    ']
        
        for sep in separators:
            if sep in line:
                cols = [col.strip() for col in line.split(sep)]
                # Filter out empty columns
                cols = [col for col in cols if col]
                if len(cols) >= 2:
                    return cols
        
        # Fallback: split on multiple spaces
        cols = re.split(r'\s{2,}', line)
        if len(cols) >= 2:
            return [col.strip() for col in cols if col.strip()]
        
        return None
    
    def is_new_section(self, line: str) -> bool:
        """Check if line starts a new section"""
        for pattern in self.table_caption_patterns + [self.chart_pattern, self.section_pattern]:
            if pattern.search(line):
                return True
        return False
    
    def _find_charts(self, text: str) -> List[DataSection]:
        """Find all charts/figures in the document"""
        charts = []
        
        for match in self.chart_pattern.finditer(text):
            chart_num = match.group(1)
            chart_title = match.group(2).strip() if match.group(2) else None
            
            # Extract chart content (description)
            start_pos = match.end()
            
            # Find end (next marker or 500 chars)
            remaining_text = text[start_pos:]
            next_marker = None
            

            # Check for next table or chart
            for pattern in self.table_caption_patterns + [self.chart_pattern]:
                next_match = pattern.search(remaining_text)
                if next_match:
                    if next_marker is None or next_match.start() < next_marker:
                        next_marker = next_match.start()
            
            if next_marker:
                end_pos = start_pos + next_marker
            else:
                end_pos = min(start_pos + 500, len(text))
            
            chart_content = text[match.start():end_pos].strip()
            
            charts.append(DataSection(
                section_type="chart",
                title=f"Figure {chart_num}: {chart_title}" if chart_title else f"Figure {chart_num}",
                content=chart_content,
                start_pos=match.start(),
                end_pos=end_pos
            ))
        
        return charts
    
    def _find_sections(self, text: str) -> List[DataSection]:
        """Find analysis sections"""
        sections = []
        
        for match in self.section_pattern.finditer(text):
            section_num = match.group(1)
            section_title = match.group(2).strip() if match.group(2) else None
            
            # Find section content (until next section)
            start_pos = match.end()
            
            remaining_text = text[start_pos:]
            next_match = self.section_pattern.search(remaining_text)
            
            if next_match:
                end_pos = start_pos + next_match.start()
            else:
                end_pos = len(text)
            
            section_content = text[start_pos:end_pos].strip()
            
            sections.append(DataSection(
                section_type="analysis",
                title=f"Section {section_num}: {section_title}" if section_title else f"Section {section_num}",
                content=section_content,
                start_pos=match.start(),
                end_pos=end_pos
            ))
        
        return sections
    
    def is_table_content(self, text: str) -> bool:
        """
        Heuristic to detect if text is a table
        Checks for high density of numbers, pipes, tabs
        """
        if not text:
            return False
        
        # Count indicators
        pipe_count = text.count('|')
        tab_count = text.count('\t')
        digit_count = sum(c.isdigit() for c in text)
        total_chars = len(text)
        
        # High ratio suggests table
        if pipe_count / max(1, total_chars) > 0.05:
            return True
        if tab_count / max(1, total_chars) > 0.03:
            return True
        if digit_count / max(1, total_chars) > 0.2:
            return True
        
        return False
    def _find_visual_anchor(self, content: str, word_coords: List[Dict]) -> Optional[Dict]:
        """Find visual coordinates for text (simplified from go_structure.py)"""
        if not word_coords: return None
        search_tokens = content.split()[:10]
        if not search_tokens: return None
        
        # Implementation placeholder: Return first page number found
        return {"page": word_coords[0].get("page", 0) if word_coords else 0}
