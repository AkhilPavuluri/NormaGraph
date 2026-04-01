"""
Data Chunker - Reports and Statistical Documents
Optimized for tables, charts, and data analysis sections
"""
import re
from typing import List, Dict
from .base_chunker import BaseChunker, Chunk


class DataChunker(BaseChunker):
    """
    Data document specific chunker
    Handles tables, charts, and analytical content
    """
    
    def __init__(self):
        # Data-specific sizes (smaller for dense tabular data)
        super().__init__(min_size=500, max_size=1000, overlap=80)
        
        # Table detection patterns
        self.table_marker = re.compile(r'(?:Table|Chart|Figure)\s+\d+', re.IGNORECASE)
        self.section_marker = re.compile(r'^(?:Chapter|Section)\s+\d+', re.IGNORECASE | re.MULTILINE)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk data document with enhanced table and identity awareness
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Identity enrichment
        identity = metadata.get('identity', {})
        is_garbled = metadata.get('is_garbled', False)
        
        # Check for structured input
        structured_sections = metadata.get('structured_sections', [])
        
        if structured_sections:
            chunks = self._chunk_with_structured_sections(
                text, doc_id, metadata, structured_sections
            )
        else:
            # Fallback to pattern-based table detection
            chunks = self._chunk_with_table_awareness(text, doc_id, metadata)
            
        # Enrich all chunks with identity and garbled status
        for chunk in chunks:
            chunk.metadata.update({
                "report_type": identity.get("report_type"),
                "year": identity.get("year"),
                "state": identity.get("state"),
                "is_garbled": is_garbled,
                "confidence": identity.get("confidence", "high")
            })
        
        return chunks
    
    def _chunk_with_structured_sections(
        self,
        text: str,
        doc_id: str,
        metadata: Dict,
        structured_sections: List[Dict]
    ) -> List[Chunk]:
        """
        Chunk text using structured sections from DataStructureParser
        """
        chunks = []
        chunk_index = 0
        
        for section in structured_sections:
            # Handle both dict and object formats
            if hasattr(section, '__dict__'):
                s_type = getattr(section, 'section_type', 'content')
                s_content = getattr(section, 'content', '')
                s_meta = {
                    **metadata, 
                    "section_type": s_type,
                    "section_title": getattr(section, 'title', None),
                    "visual_anchor": getattr(section, 'visual_anchor', None),
                    "is_garbled_section": getattr(section, 'is_garbled', False)
                }
            else:
                s_type = section.get('section_type', 'content')
                s_content = section.get('content', '')
                s_meta = {
                    **metadata, 
                    "section_type": s_type,
                    "section_title": section.get('title'),
                    "visual_anchor": section.get('visual_anchor'),
                    "is_garbled_section": section.get('is_garbled', False)
                }
            
            # Specialized chunking for tables
            if s_type == 'table':
                table_chunk = self._create_chunk(s_content, doc_id, chunk_index, s_meta)
                table_chunk.metadata.update({"chunk_type": "table", "is_table": True})
                chunks.append(table_chunk)
                chunk_index += 1
            else:
                # Generic section chunking
                paras = self._split_paragraphs(s_content)
                section_chunks = self._group_paragraphs(paras, doc_id, s_meta)
                for chunk in section_chunks:
                    chunk.chunk_index = chunk_index
                    chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                    chunk.metadata["chunk_type"] = "text"
                    chunks.append(chunk)
                    chunk_index += 1
                    
        return chunks
    
    def _remove_table_content(self, text: str, tables: List[Dict]) -> str:
        """
        Remove table content from text to get non-table sections
        """
        remaining_text = text
        
        # Remove structured table content based on positions
        for table in tables:
            if table['type'] == 'structured' and 'start_pos' in table:
                start_pos = table['start_pos']
                end_pos = table.get('end_pos', start_pos + len(table['content']))
                
                # Remove this section from text
                before = remaining_text[:start_pos]
                after = remaining_text[end_pos:]
                remaining_text = before + "\n\n" + after
        
        # Clean up multiple newlines
        remaining_text = re.sub(r'\n{3,}', '\n\n', remaining_text)
        
        return remaining_text.strip()
    
    def _chunk_with_table_awareness(
        self, 
        text: str, 
        doc_id: str, 
        metadata: Dict
    ) -> List[Chunk]:
        """
        Fallback: Chunk text while preserving table integrity using pattern detection
        """
        chunks = []
        chunk_index = 0
        
        # Find table positions
        table_positions = [(m.start(), m.end(), m.group()) 
                          for m in self.table_marker.finditer(text)]
        
        if not table_positions:
            # No tables, use standard paragraph chunking
            paragraphs = self._split_paragraphs(text)
            return self._group_paragraphs(paragraphs, doc_id, metadata)
        
        # Split text around tables
        current_pos = 0
        
        for table_start, table_end, table_name in table_positions:
            # Get text before table
            before_table = text[current_pos:table_start].strip()
            
            if before_table:
                # Chunk the text before table
                paras = self._split_paragraphs(before_table)
                para_chunks = self._group_paragraphs(paras, doc_id, metadata)
                for chunk in para_chunks:
                    chunk.chunk_index = chunk_index
                    chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                    chunks.append(chunk)
                    chunk_index += 1
            
            # Extract table content (table + description)
            # Find the end of table (next double newline or next table)
            next_table_start = table_positions[table_positions.index((table_start, table_end, table_name)) + 1][0] \
                if table_positions.index((table_start, table_end, table_name)) + 1 < len(table_positions) \
                else len(text)
            
            # Look for double newline as end of table section
            table_section_end = text.find('\n\n\n', table_start)
            if table_section_end == -1 or table_section_end > next_table_start:
                table_section_end = next_table_start
            
            table_content = text[table_start:table_section_end].strip()
            
            if table_content:
                # Create table chunk with enhanced metadata
                table_metadata = {
                    **metadata,
                    "chunk_type": "table",
                    "is_table": True,
                    "table_name": table_name,
                    "table_source": "pattern_detected"
                }
                table_chunk = self._create_chunk(
                    table_content, doc_id, chunk_index, table_metadata
                )
                chunks.append(table_chunk)
                chunk_index += 1
            
            current_pos = table_section_end
        
        # Get remaining text after last table
        remaining = text[current_pos:].strip()
        if remaining:
            paras = self._split_paragraphs(remaining)
            para_chunks = self._group_paragraphs(paras, doc_id, metadata)
            for chunk in para_chunks:
                chunk.chunk_index = chunk_index
                chunk.chunk_id = f"{doc_id}_chunk_{chunk_index}"
                chunk.metadata["is_table"] = False
                chunk.metadata["chunk_type"] = "text"
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _is_table_content(self, text: str) -> bool:
        """
        Detect if text is likely a table
        Simple heuristic: high ratio of digits, pipes, or tabs
        """
        if not text:
            return False
        
        # Count special characters
        special_chars = text.count('|') + text.count('\t')
        digit_count = sum(c.isdigit() for c in text)
        total_chars = len(text)
        
        # High ratio suggests table
        if special_chars / max(1, total_chars) > 0.05:
            return True
        if digit_count / max(1, total_chars) > 0.2:
            return True
        
        return False