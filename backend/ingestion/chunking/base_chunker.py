"""
Base Chunker - Production-Grade Foundation for All Vertical Chunkers
Provides robust paragraph splitting, semantic overlap, and sentence-aware chunking
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import re


@dataclass
class Chunk:
    """Represents a text chunk with rich metadata"""
    content: str
    chunk_id: str
    doc_id: str
    chunk_index: int
    word_count: int
    metadata: Dict


class BaseChunker:
    """
    Production-grade base class for all chunkers
    Provides semantic-aware chunking utilities
    """
    
    def __init__(self, min_size: int = 500, max_size: int = 1000, overlap: int = 100):
        """
        Initialize base chunker
        
        Args:
            min_size: Minimum chunk size in characters
            max_size: Maximum chunk size in characters
            overlap: Overlap between chunks in characters (semantic overlap preferred)
        """
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap
        
        # Sentence boundary detection (improved)
        self.sentence_end_pattern = re.compile(r'([.!?])\s+(?=[A-Z])')
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk text (to be implemented by subclasses)
        
        Args:
            text: Text to chunk
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of chunks
        """
        raise NotImplementedError("Subclasses must implement chunk()")
    
    def _create_chunk(
        self, 
        text: str, 
        doc_id: str, 
        chunk_index: int, 
        metadata: Dict
    ) -> Chunk:
        """
        Create a Chunk object with enriched metadata
        
        Args:
            text: Chunk text
            doc_id: Document ID
            chunk_index: Chunk index
            metadata: Chunk metadata
            
        Returns:
            Chunk object
        """
        chunk_id = f"{doc_id}_chunk_{chunk_index}"
        word_count = len(text.split())
        
        # Enrich metadata
        enriched_metadata = {
            **metadata,
            "char_count": len(text),
            "line_count": text.count('\n') + 1
        }
        
        return Chunk(
            content=text,
            chunk_id=chunk_id,
            doc_id=doc_id,
            chunk_index=chunk_index,
            word_count=word_count,
            metadata=enriched_metadata
        )
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """
        Split text into paragraphs with improved detection
        
        Handles:
        - Double newlines (standard paragraphs)
        - Numbered lists (1. 2. 3.)
        - Bullet points (•, -, *)
        - Indented blocks
        
        Args:
            text: Text to split
            
        Returns:
            List of paragraphs
        """
        # First, normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Split by double newlines (primary method)
        paragraphs = re.split(r'\n\s*\n', text)
        
        # Further split numbered/bulleted lists if they're in the same "paragraph"
        refined_paragraphs = []
        for para in paragraphs:
            # Check if this paragraph contains numbered items or bullets
            if re.search(r'^\s*(?:\d+\.|[•\-\*])\s+', para, re.MULTILINE):
                # Split on numbered/bulleted items
                items = re.split(r'\n(?=\s*(?:\d+\.|[•\-\*])\s+)', para)
                refined_paragraphs.extend([item.strip() for item in items if item.strip()])
            else:
                refined_paragraphs.append(para.strip())
        
        # Filter out empty paragraphs
        return [p for p in refined_paragraphs if p and len(p.strip()) > 0]
    
    def _group_paragraphs(
        self, 
        paragraphs: List[str], 
        doc_id: str, 
        metadata: Dict
    ) -> List[Chunk]:
        """
        Group paragraphs into chunks with semantic overlap
        
        CRITICAL FIX: Overlap now preserves complete paragraphs, not character fragments
        
        Args:
            paragraphs: List of paragraphs
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of chunks
        """
        if not paragraphs:
            return []
        
        chunks = []
        current_group = []
        current_size = 0
        chunk_index = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph would exceed max_size
            if current_size + para_size > self.max_size and current_group:
                # Create chunk from current group
                chunk_text = "\n\n".join(current_group)
                
                # Only create if meets minimum size
                if len(chunk_text) >= self.min_size:
                    chunk = self._create_chunk(chunk_text, doc_id, chunk_index, metadata)
                    chunks.append(chunk)
                    chunk_index += 1
                    
                    # FIXED: Semantic overlap - keep last complete paragraph(s)
                    if self.overlap > 0 and current_group:
                        overlap_paras = self._get_overlap_paragraphs(current_group, self.overlap)
                        current_group = overlap_paras + [para]
                        current_size = sum(len(p) for p in current_group)
                    else:
                        current_group = [para]
                        current_size = para_size
                else:
                    # Too small, just add to current group
                    current_group.append(para)
                    current_size += para_size
            else:
                current_group.append(para)
                current_size += para_size
        
        # Add final chunk
        if current_group:
            chunk_text = "\n\n".join(current_group)
            if len(chunk_text) >= self.min_size:
                chunk = self._create_chunk(chunk_text, doc_id, chunk_index, metadata)
                chunks.append(chunk)
            elif chunks:
                # If final group is too small, append to last chunk
                chunks[-1].content += "\n\n" + chunk_text
                chunks[-1].word_count = len(chunks[-1].content.split())
                chunks[-1].metadata["char_count"] = len(chunks[-1].content)
        
        return chunks
    
    def _get_overlap_paragraphs(self, paragraphs: List[str], target_overlap: int) -> List[str]:
        """
        Get paragraphs for overlap, preferring complete paragraphs over fragments
        
        Args:
            paragraphs: List of paragraphs
            target_overlap: Target overlap size in characters
            
        Returns:
            List of paragraphs for overlap
        """
        if not paragraphs:
            return []
        
        # Start from the end and work backwards
        overlap_paras = []
        overlap_size = 0
        
        for para in reversed(paragraphs):
            para_size = len(para)
            if overlap_size + para_size <= target_overlap * 1.5:  # Allow 50% overshoot for semantic coherence
                overlap_paras.insert(0, para)
                overlap_size += para_size
            else:
                break
        
        # If no paragraphs fit, take the last one
        if not overlap_paras:
            overlap_paras = [paragraphs[-1]]
        
        return overlap_paras
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (fallback for very large paragraphs)
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Split on sentence boundaries
        sentences = self.sentence_end_pattern.split(text)
        
        # Recombine punctuation with sentences
        result = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + sentences[i + 1] if i + 1 < len(sentences) else sentences[i]
            result.append(sentence.strip())
        
        # Add last sentence if exists
        if len(sentences) % 2 == 1:
            result.append(sentences[-1].strip())
        
        return [s for s in result if s]
    
    def _group_sentences(
        self,
        sentences: List[str],
        doc_id: str,
        metadata: Dict
    ) -> List[Chunk]:
        """
        Group sentences into chunks (fallback for unstructured text)
        
        Args:
            sentences: List of sentences
            doc_id: Document ID
            metadata: Document metadata
            
        Returns:
            List of chunks
        """
        # Similar logic to _group_paragraphs but for sentences
        return self._group_paragraphs(sentences, doc_id, metadata)
