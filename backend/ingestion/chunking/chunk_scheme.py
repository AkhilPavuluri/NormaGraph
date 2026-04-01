"""
Scheme Chunker - Government Schemes and Programs
Understands scheme structure: Eligibility, Benefits, Application, Implementation
"""
import re
from typing import List, Dict
from .base_chunker import BaseChunker, Chunk


class SchemeChunker(BaseChunker):
    """
    Scheme document specific chunker
    Preserves scheme structure and benefit details
    """
    
    def __init__(self):
        # Scheme-specific sizes
        super().__init__(min_size=600, max_size=1200, overlap=100)
        
        # Scheme structure patterns
        self.eligibility_pattern = re.compile(
            r'^(?:ELIGIBILITY|ELIGIBLE|WHO CAN APPLY)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        self.benefits_pattern = re.compile(
            r'^(?:BENEFITS?|ASSISTANCE|FINANCIAL AID)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        self.application_pattern = re.compile(
            r'^(?:HOW TO APPLY|APPLICATION|PROCEDURE)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
        self.implementation_pattern = re.compile(
            r'^(?:IMPLEMENTATION|EXECUTION|MONITORING)[:\s]',
            re.IGNORECASE | re.MULTILINE
        )
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk scheme document with structure awareness
        
        Strategy:
        1. Identify scheme sections (eligibility, benefits, application)
        2. Keep each section coherent
        3. Split only if section is too large
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Detect scheme structure
        sections = self._detect_scheme_structure(text)
        
        # Chunk each section appropriately
        chunks = []
        chunk_index = 0
        
        for section_type, section_text in sections:
            section_chunks = self._chunk_section(
                section_text, section_type, doc_id, chunk_index, metadata
            )
            chunks.extend(section_chunks)
            chunk_index += len(section_chunks)
        
        return chunks
    
    def _detect_scheme_structure(self, text: str) -> List[tuple]:
        """
        Detect scheme document structure
        Returns list of (section_type, text) tuples
        """
        sections = []
        
        # Find section markers
        markers = []
        
        for pattern, section_type in [
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
            # No clear structure, treat as single section
            return [("content", text)]
        
        # Extract sections
        for i, (start, section_type) in enumerate(markers):
            end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
            section_text = text[start:end].strip()
            
            if section_text:
                sections.append((section_type, section_text))
        
        # Add any text before first marker (usually scheme overview)
        if markers[0][0] > 0:
            overview = text[:markers[0][0]].strip()
            if overview:
                sections.insert(0, ("overview", overview))
        
        return sections
    
    def _chunk_section(
        self, 
        text: str, 
        section_type: str, 
        doc_id: str, 
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Chunk a scheme section appropriately"""
        
        # If section is small enough, keep as single chunk
        if len(text) <= self.max_size:
            chunk_metadata = {**metadata, "section_type": section_type}
            return [self._create_chunk(text, doc_id, start_index, chunk_metadata)]
        
        # For eligibility/benefits sections with bullet points
        if section_type in ("eligibility", "benefits"):
            return self._chunk_bullet_points(text, doc_id, start_index, metadata, section_type)
        
        # Otherwise use base paragraph-based chunking
        paragraphs = self._split_paragraphs(text)
        section_metadata = {**metadata, "section_type": section_type}
        return self._group_paragraphs(paragraphs, doc_id, section_metadata)
    
    def _chunk_bullet_points(
        self, 
        text: str, 
        doc_id: str, 
        start_index: int, 
        metadata: Dict,
        section_type: str
    ) -> List[Chunk]:
        """
        Chunk bullet points/list items, trying to keep them together
        """
        # Try to identify list items: •, -, *, 1., (a), etc.
        bullet_pattern = re.compile(r'^(?:[\•\-\*]|\d+\.|\([a-z]\))\s+', re.MULTILINE)
        
        # Find all bullet starts
        bullet_starts = [m.start() for m in bullet_pattern.finditer(text)]
        
        if not bullet_starts:
            # No clear bullets, fall back to paragraph chunking
            paragraphs = self._split_paragraphs(text)
            section_metadata = {**metadata, "section_type": section_type}
            return self._group_paragraphs(paragraphs, doc_id, section_metadata)
        
        # Split into individual points
        points = []
        for i, start in enumerate(bullet_starts):
            end = bullet_starts[i + 1] if i + 1 < len(bullet_starts) else len(text)
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
                chunk_text = "\n".join(current_group)
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
            chunk_text = "\n".join(current_group)
            chunk_metadata = {**metadata, "section_type": section_type}
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks