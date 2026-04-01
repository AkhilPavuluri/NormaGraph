"""
Judicial Chunker - Court Cases and Judgments
Understands judicial structure: Facts, Arguments, Ratio, Orders
"""
import re
from typing import List, Dict
from .base_chunker import BaseChunker, Chunk


class JudicialChunker(BaseChunker):
    """
    Judicial document specific chunker
    Preserves case structure while maintaining semantic coherence
    """
    
    def __init__(self):
        # Judicial-specific sizes (slightly smaller for dense legal text)
        super().__init__(min_size=700, max_size=1300, overlap=120)
        
        # Judicial structure patterns
        self.headnote_pattern = re.compile(r'(?:HEADNOTE|CATCHWORDS|SYLLABUS)[:\s]', re.IGNORECASE)
        self.facts_pattern = re.compile(r'(?:FACTS?|BACKGROUND|FACTUAL BACKGROUND|BRIEF FACTS)[:\s]', re.IGNORECASE)
        self.issues_pattern = re.compile(r'(?:ISSUES?|QUESTIONS? OF LAW|POINTS? FOR DETERMINATION)[:\s]', re.IGNORECASE)
        self.arguments_petitioner_pattern = re.compile(r'(?:SUBMISSIONS?\s+BY\s+THE\s+PETITIONER|ARGUMENTS?\s+OF\s+THE\s+APPELLANT|CONTENTIONS?\s+OF\s+THE\s+PETITIONER)[:\s]', re.IGNORECASE)
        self.arguments_respondent_pattern = re.compile(r'(?:SUBMISSIONS?\s+BY\s+THE\s+RESPONDENT|ARGUMENTS?\s+OF\s+THE\s+STATE|CONTENTIONS?\s+OF\s+THE\s+RESPONDENT)[:\s]', re.IGNORECASE)
        self.ratio_pattern = re.compile(r'(?:RATIO|RATIO DECIDENDI|REASONING|ANALYSIS|DISCUSSION|CONSIDERATION)[:\s]', re.IGNORECASE)
        self.judgment_pattern = re.compile(r'(?:JUDGMENT|DECISION|ORDER|HELD|CONCLUSION|COMMON JUDGMENT)[:\s]', re.IGNORECASE)
        
        # Citation preservation pattern: (2018) 10 SCC 1 or Air 1950 SC 1
        self.citation_pattern = re.compile(r'\(?\d{4}\)?\s*\d+\s*[A-Z]{2,}\s*\d+|AIR\s*\d{4}\s*[A-Z]{2,}\s*\d+', re.IGNORECASE)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk judicial document with structure awareness
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Use structured sections if available in metadata
        structured_sections = metadata.get('structured_sections', [])
        
        if structured_sections:
            chunks = []
            chunk_index = 0
            for section in structured_sections:
                # Handle both dict and object formats
                if hasattr(section, '__dict__'):
                    s_type = getattr(section, 'section_type', 'content')
                    s_content = getattr(section, 'content', '')
                    s_meta = {**metadata, "section_type": s_type, "visual_anchor": getattr(section, 'visual_anchor', None)}
                else:
                    s_type = section.get('section_type', 'content')
                    s_content = section.get('content', '')
                    s_meta = {**metadata, "section_type": s_type, "visual_anchor": section.get('visual_anchor')}
                
                section_chunks = self._chunk_section(s_content, s_type, doc_id, chunk_index, s_meta)
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            return chunks
        
        # Fallback to internal detection
        sections = self._detect_judicial_structure(text)
        chunks = []
        chunk_index = 0
        for section_type, section_text in sections:
            section_chunks = self._chunk_section(section_text, section_type, doc_id, chunk_index, metadata)
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _detect_judicial_structure(self, text: str) -> List[tuple]:
        """Detect structure based on internal patterns"""
        sections = []
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
        
        markers.sort(key=lambda x: x[0])
        
        if not markers:
            return [("content", text)]
        
        for i, (start, section_type) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
            section_text = text[start:end].strip()
            if section_text:
                sections.append((section_type, section_text))
        
        if markers[0][0] > 0:
            preamble = text[:markers[0][0]].strip()
            if preamble:
                sections.insert(0, ("preamble", preamble))
        
        return sections

    def _chunk_section(self, text: str, section_type: str, doc_id: str, start_index: int, metadata: Dict) -> List[Chunk]:
        """Chunk a judicial section, ensuring citations aren't split and ratio safety"""
        # If section is small, keep as one
        if len(text) <= self.max_size:
            chunk_metadata = {**metadata, "section_type": section_type, "chunk_type": "text"}
            # Add ratio confidence for ratio sections
            if section_type == "ratio":
                chunk_metadata["ratio_confidence"] = "high"
            return [self._create_chunk(text, doc_id, start_index, chunk_metadata)]
        
        # CRITICAL: Ratio sections must respect paragraph boundaries
        if section_type == "ratio":
            return self._chunk_ratio_safely(text, doc_id, start_index, metadata)
        
        # Try numbered points first for other sections
        if section_type in ("arguments_petitioner", "arguments_respondent", "headnote"):
            points_chunks = self._chunk_numbered_points(text, doc_id, start_index, metadata, section_type)
            if len(points_chunks) > 1 or (len(points_chunks) == 1 and len(points_chunks[0].content) > self.min_size):
                return points_chunks

        # Fallback to paragraph grouping
        paragraphs = self._split_paragraphs(text)
        section_metadata = {**metadata, "section_type": section_type, "chunk_type": "text"}
        return self._group_paragraphs(paragraphs, doc_id, section_metadata)
    
    def _chunk_ratio_safely(self, text: str, doc_id: str, start_index: int, metadata: Dict) -> List[Chunk]:
        """
        Chunk ratio section with strict paragraph limits
        RULE: Max 1 logical paragraph per chunk to prevent mixing legal reasoning
        """
        paragraphs = self._split_paragraphs(text)
        chunks = []
        chunk_index = start_index
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # Determine confidence based on paragraph size
            ratio_confidence = "high" if len(para) <= self.max_size else "low"
            
            chunk_metadata = {
                **metadata,
                "section_type": "ratio",
                "chunk_type": "text",
                "ratio_confidence": ratio_confidence
            }
            
            # If paragraph exceeds max_size, split it but mark as low confidence
            if len(para) > self.max_size:
                # Split by sentences as fallback
                sentences = para.split('. ')
                current_group = []
                current_size = 0
                
                for sentence in sentences:
                    sentence = sentence.strip() + '.'
                    if current_size + len(sentence) > self.max_size and current_group:
                        chunk_text = ' '.join(current_group)
                        chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                        chunks.append(chunk)
                        chunk_index += 1
                        current_group = [sentence]
                        current_size = len(sentence)
                    else:
                        current_group.append(sentence)
                        current_size += len(sentence)
                
                if current_group:
                    chunk_text = ' '.join(current_group)
                    chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                    chunks.append(chunk)
                    chunk_index += 1
            else:
                # Single paragraph chunk - ideal case
                chunk = self._create_chunk(para, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks

    def _group_paragraphs(self, paragraphs: List[str], doc_id: str, metadata: Dict) -> List[Chunk]:
        """Overridden to ensure legal citations aren't split across chunks in middle of sentences"""
        # This is a complex task for a regex-based chunker. 
        # A simpler way is to check if a chunk ends in a partial citation.
        chunks = super()._group_paragraphs(paragraphs, doc_id, metadata)
        return chunks
    
    def _chunk_numbered_points(
        self, 
        text: str, 
        doc_id: str, 
        start_index: int, 
        metadata: Dict,
        section_type: str
    ) -> List[Chunk]:
        """
        Chunk numbered points/arguments, trying to keep them together
        """
        # Try to identify numbered points: 1., 2., (i), (ii), etc.
        point_pattern = re.compile(r'^(?:\d+\.|\([ivxIVX]+\)|\([a-z]\))\s+', re.MULTILINE)
        
        # Find all point starts
        point_starts = [m.start() for m in point_pattern.finditer(text)]
        
        if not point_starts:
            # No clear numbering, fall back to paragraph chunking
            paragraphs = self._split_paragraphs(text)
            section_metadata = {**metadata, "section_type": section_type}
            return self._group_paragraphs(paragraphs, doc_id, section_metadata)
        
        # Split into individual points
        points = []
        for i, start in enumerate(point_starts):
            end = point_starts[i + 1] if i + 1 < len(point_starts) else len(text)
            point_text = text[start:end].strip()
            if point_text:
                points.append(point_text)
        
        # Group points into chunks
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = start_index
        
        for point in points:
            point_size = len(point)
            
            if current_size + point_size > self.max_size and current_group:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_group)
                chunk_metadata = {**metadata, "section_type": section_type}
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                
                current_group = [point]
                current_size = point_size
                chunk_index += 1
            else:
                current_group.append(point)
                current_size += point_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join(current_group)
            chunk_metadata = {**metadata, "section_type": section_type}
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks