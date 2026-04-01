"""
Legal Chunker - Legal Document Specific Chunking
Understands legal structure: Sections, Articles, Rules, Regulations, Norms, Schedules, Appendices
"""
import re
from typing import List, Dict, Tuple, Optional
from .base_chunker import BaseChunker, Chunk


class LegalChunker(BaseChunker):
    """
    Legal document specific chunker
    Preserves legal section boundaries and hierarchies
    Supports: Acts, Rules, Regulations, Norms, Constitution, Schedules, Appendices
    """
    
    def __init__(self):
        # Legal-specific sizes
        super().__init__(min_size=800, max_size=1500, overlap=150)
        
        # Universal Legal Structure Patterns (aligned with LegalStructureParser)
        self.section_pattern = re.compile(
            r'^\s*Section\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.article_pattern = re.compile(
            r'^\s*Article\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.rule_pattern = re.compile(
            r'^\s*Rule\s+(\d+[A-Z]?(?:\([0-9a-zA-Z]+\))?)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.regulation_pattern = re.compile(
            r'^\s*Regulation\s+(\d+|[IVX]+)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.norm_pattern = re.compile(
            r'^\s*Norm\s*(?:[sS])?\s+(\d+|[IVX]+)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.schedule_pattern = re.compile(
            r'^\s*(?:THE\s+)?SCHEDULE\s+([IXV0-9A-Z]+)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        self.appendix_pattern = re.compile(
            r'^\s*APPENDIX\s+([IXV0-9A-Z]+)(?:[:\.\s]+(.+?))?$',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Subsection/Clause pattern
        self.clause_pattern = re.compile(
            r'^\s*\(([0-9a-zA-Z]|[ivx]+)\)\s+',
            re.MULTILINE
        )
        
        self.chapter_pattern = re.compile(
            r'^(?:CHAPTER|Chapter)\s+([IVXLCDM]+|\d+)\s*[.:-]?\s*(.*?)$',
            re.MULTILINE | re.IGNORECASE
        )
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk legal document with structure awareness
        
        Strategy:
        1. Use structured sections if available from LegalStructureParser
        2. Identify sections/articles/rules/regulations/norms
        3. Keep complete nodes together when possible
        4. Split large nodes at clause boundaries
        """
        if not text or len(text.strip()) < 50:
            return []
        
        # Check if we have structured input from LegalStructureParser
        structured_sections = metadata.get('structured_sections', [])
        
        if structured_sections:
            chunks = []
            chunk_index = 0
            for section in structured_sections:
                # Handle both dict and LegalSection object formats
                if hasattr(section, '__dict__'):
                    s_type = getattr(section, 'section_type', 'section')
                    s_num = getattr(section, 'section_number', '')
                    s_title = getattr(section, 'title', None)
                    s_content = getattr(section, 'content', '')
                    s_meta = {
                        **metadata,
                        "section_type": s_type,
                        "section_number": s_num,
                        "section_title": s_title,
                        "chapter": getattr(section, 'chapter', None),
                        "part": getattr(section, 'part', None),
                        "structural_confidence": getattr(section, 'structural_confidence', 1.0)
                    }
                else:
                    s_type = section.get('section_type', 'section')
                    s_num = section.get('section_number', '')
                    s_title = section.get('title')
                    s_content = section.get('content', '')
                    s_meta = {
                        **metadata,
                        "section_type": s_type,
                        "section_number": s_num,
                        "section_title": s_title,
                        "chapter": section.get('chapter'),
                        "part": section.get('part'),
                        "structural_confidence": section.get('structural_confidence', 1.0)
                    }
                
                section_chunks = self._chunk_legal_node(s_content, s_num, s_type, doc_id, chunk_index, s_meta)
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            return chunks
        
        # Fallback: Try to identify structure internally
        legal_nodes = self._identify_legal_nodes(text)
        
        if not legal_nodes:
            # No clear structure, fall back to paragraph-based chunking
            paragraphs = self._split_paragraphs(text)
            return self._group_paragraphs(paragraphs, doc_id, metadata)
        
        # Chunk each legal node
        chunks = []
        chunk_index = 0
        
        for node_type, node_num, node_title, node_text in legal_nodes:
            node_meta = {
                **metadata,
                "section_type": node_type,
                "section_number": node_num,
                "section_title": node_title
            }
            
            node_chunks = self._chunk_legal_node(
                node_text, node_num, node_type, doc_id, chunk_index, node_meta
            )
            chunks.extend(node_chunks)
            chunk_index += len(node_chunks)
        
        return chunks
    
    def _identify_legal_nodes(self, text: str) -> List[Tuple[str, str, str, str]]:
        """
        Identify legal nodes (Sections, Articles, Rules, etc.)
        Returns list of (type, number, title, text) tuples
        """
        all_nodes = []
        
        # Try all patterns
        for pattern, node_type in [
            (self.section_pattern, "section"),
            (self.article_pattern, "article"),
            (self.rule_pattern, "rule"),
            (self.regulation_pattern, "regulation"),
            (self.norm_pattern, "norm"),
            (self.schedule_pattern, "schedule"),
            (self.appendix_pattern, "appendix")
        ]:
            matches = list(pattern.finditer(text))
            for i, match in enumerate(matches):
                node_num = match.group(1)
                node_title = match.group(2).strip() if match.group(2) else ""
                
                # Get node text
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                node_text = text[start:end].strip()
                
                all_nodes.append((node_type, node_num, node_title, node_text, start))
        
        # Sort by position and remove duplicates
        all_nodes.sort(key=lambda x: x[4])
        return [(t, n, title, txt) for t, n, title, txt, _ in all_nodes]
    
    def _chunk_legal_node(
        self,
        text: str,
        node_num: str,
        node_type: str,
        doc_id: str,
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Chunk a legal node (Section/Article/Rule/etc.) appropriately"""
        
        # If node fits in one chunk, keep it together
        if len(text) <= self.max_size:
            chunk_metadata = {**metadata, "chunk_type": "text"}
            return [self._create_chunk(text, doc_id, start_index, chunk_metadata)]
        
        # Try to split at clause boundaries
        clauses = self._identify_clauses(text)
        
        if clauses:
            return self._chunk_clauses(clauses, doc_id, start_index, metadata)
        
        # Otherwise use paragraph-based chunking
        paragraphs = self._split_paragraphs(text)
        return self._group_paragraphs(paragraphs, doc_id, metadata)
    
    def _identify_clauses(self, text: str) -> List[Tuple[str, str]]:
        """
        Identify clauses within a legal node
        Returns list of (clause_num, text) tuples
        """
        clauses = []
        clause_matches = list(self.clause_pattern.finditer(text))
        
        if not clause_matches:
            return []
        
        for i, match in enumerate(clause_matches):
            clause_num = match.group(1)
            start = match.start()
            end = clause_matches[i + 1].start() if i + 1 < len(clause_matches) else len(text)
            clause_text = text[start:end].strip()
            
            clauses.append((clause_num, clause_text))
        
        return clauses
    
    def _chunk_clauses(
        self,
        clauses: List[Tuple[str, str]],
        doc_id: str,
        start_index: int,
        metadata: Dict
    ) -> List[Chunk]:
        """Group clauses into optimal chunks"""
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = start_index
        
        for clause_num, clause_text in clauses:
            clause_size = len(clause_text)
            
            if current_size + clause_size > self.max_size and current_group:
                # Finalize current chunk
                chunk_text = "\n\n".join([text for _, text in current_group])
                chunk_metadata = {
                    **metadata,
                    "clauses": [num for num, _ in current_group],
                    "chunk_type": "text"
                }
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
                chunks.append(chunk)
                
                # Start new chunk with overlap
                if self.overlap > 0 and current_group:
                    current_group = [current_group[-1], (clause_num, clause_text)]
                    current_size = len(current_group[-1][1]) + clause_size
                else:
                    current_group = [(clause_num, clause_text)]
                    current_size = clause_size
                
                chunk_index += 1
            else:
                current_group.append((clause_num, clause_text))
                current_size += clause_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join([text for _, text in current_group])
            chunk_metadata = {
                **metadata,
                "clauses": [num for num, _ in current_group],
                "chunk_type": "text"
            }
            chunk = self._create_chunk(chunk_text, doc_id, chunk_index, chunk_metadata)
            chunks.append(chunk)
        
        return chunks