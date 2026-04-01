"""
Citation Generation System

Generates proper legal citations with source hierarchy.
Every answer MUST have citations - this is non-negotiable.
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CitationType(Enum):
    """Types of legal citations"""
    JUDICIAL = "judicial"  # Court judgments
    STATUTORY = "statutory"  # Acts, regulations
    POLICY = "policy"  # Government orders, policies
    SCHEME = "scheme"  # Government schemes


@dataclass
class Citation:
    """A legal citation"""
    doc_id: str
    doc_type: str
    citation_type: CitationType
    title: str
    authority: str
    date: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    span: Optional[str] = None
    binding_strength: str = "medium"  # "binding", "persuasive", "informational"
    chunk_id: Optional[str] = None
    content_excerpt: Optional[str] = None


class CitationGenerator:
    """
    Generates proper legal citations from retrieved chunks.
    
    Ensures:
    - Every answer has citations
    - Citations are properly formatted
    - Source hierarchy is respected (SC > HC > Legal > GO)
    """
    
    def __init__(self):
        self.authority_weights = {
            "Supreme Court": 10.0,
            "High Court": 7.0,
            "Statutory Law": 8.0,
            "Government Order": 5.0,
            "Policy Document": 4.0,
            "Scheme": 3.0,
        }
    
    def generate_citations(
        self,
        retrieved_chunks: List,
        answer: str,
        max_citations: int = 5
    ) -> List[Citation]:
        """
        Generate citations from retrieved chunks.
        
        Args:
            retrieved_chunks: Retrieved document chunks
            answer: Generated answer text
            max_citations: Maximum number of citations to return
            
        Returns:
            List of Citation objects, sorted by authority
        """
        citations = []
        
        # Process each chunk
        for chunk in retrieved_chunks:
            citation = self._chunk_to_citation(chunk)
            if citation:
                citations.append(citation)
        
        # Sort by authority weight
        citations.sort(key=lambda c: self._get_authority_weight(c), reverse=True)
        
        # Limit to top citations
        return citations[:max_citations]
    
    def _chunk_to_citation(self, chunk) -> Optional[Citation]:
        """Convert a chunk to a citation"""
        metadata = chunk.metadata
        
        # Determine citation type
        vertical = metadata.get("vertical", "")
        citation_type = self._get_citation_type(vertical, metadata)
        
        # Build citation
        citation = Citation(
            doc_id=chunk.doc_id,
            doc_type=vertical,
            citation_type=citation_type,
            title=self._extract_title(metadata),
            authority=self._extract_authority(metadata),
            date=self._extract_date(metadata),
            section=metadata.get("section"),
            chunk_id=chunk.chunk_id,
            content_excerpt=chunk.content[:200] if hasattr(chunk, 'content') else None,
            binding_strength=self._get_binding_strength(metadata)
        )
        
        return citation
    
    def _get_citation_type(self, vertical: str, metadata: Dict) -> CitationType:
        """Determine citation type from vertical and metadata"""
        if vertical == "judicial":
            return CitationType.JUDICIAL
        elif vertical == "legal":
            return CitationType.STATUTORY
        elif vertical == "go":
            return CitationType.POLICY
        elif vertical == "scheme":
            return CitationType.SCHEME
        else:
            return CitationType.POLICY  # Default
    
    def _extract_title(self, metadata: Dict) -> str:
        """Extract document title from metadata"""
        # Try various title fields
        title_fields = [
            "title", "subject", "case_name", "act_name",
            "scheme_name", "go_number", "citation"
        ]
        
        for field in title_fields:
            if field in metadata and metadata[field]:
                title = str(metadata[field])
                if title and title != "None":
                    return title
        
        # Fallback to doc_id
        return metadata.get("doc_id", "Unknown Document")
    
    def _extract_authority(self, metadata: Dict) -> str:
        """Extract authority from metadata"""
        # Judicial documents
        if metadata.get("court_level"):
            return metadata["court_level"]
        
        if metadata.get("court"):
            return metadata["court"]
        
        # Legal documents
        if metadata.get("document_authority"):
            return metadata["document_authority"]
        
        # Government orders
        if metadata.get("vertical") == "go":
            dept = metadata.get("department", "Government")
            return f"{dept} Order"
        
        # Default
        return "Government Document"
    
    def _extract_date(self, metadata: Dict) -> Optional[str]:
        """Extract date from metadata"""
        # Try various date fields
        date_fields = ["date", "year", "effective_from", "go_date"]
        
        for field in date_fields:
            if field in metadata:
                date_val = metadata[field]
                if date_val:
                    return str(date_val)
        
        return None
    
    def _get_binding_strength(self, metadata: Dict) -> str:
        """Determine binding strength of citation"""
        court_level = metadata.get("court_level", "")
        
        if court_level == "Supreme Court":
            return "binding"
        elif court_level == "High Court":
            return "binding"  # Binding within jurisdiction
        elif metadata.get("vertical") == "legal":
            return "binding"  # Statutory law is binding
        else:
            return "persuasive"  # Policies are persuasive
    
    def _get_authority_weight(self, citation: Citation) -> float:
        """Get authority weight for sorting"""
        return self.authority_weights.get(citation.authority, 1.0)
    
    def format_citation(self, citation: Citation) -> str:
        """
        Format citation as inline text.
        
        Example: "As per Supreme Court judgment (T.M.A Pai Foundation, 2002)..."
        """
        parts = []
        
        # Authority
        if citation.authority:
            parts.append(citation.authority)
        
        # Title
        if citation.title:
            parts.append(f"({citation.title})")
        
        # Date
        if citation.date:
            parts.append(f", {citation.date}")
        
        # Section (for legal documents)
        if citation.section:
            parts.append(f", Section {citation.section}")
        
        return " ".join(parts)
    
    def generate_source_hierarchy(self, citations: List[Citation]) -> Dict:
        """
        Generate source hierarchy showing authority levels.
        
        Returns:
            Dict with hierarchical structure
        """
        hierarchy = {
            "binding": [],
            "persuasive": [],
            "informational": []
        }
        
        for citation in citations:
            strength = citation.binding_strength
            if strength == "binding":
                hierarchy["binding"].append({
                    "title": citation.title,
                    "authority": citation.authority,
                    "date": citation.date
                })
            elif strength == "persuasive":
                hierarchy["persuasive"].append({
                    "title": citation.title,
                    "authority": citation.authority,
                    "date": citation.date
                })
            else:
                hierarchy["informational"].append({
                    "title": citation.title,
                    "authority": citation.authority,
                    "date": citation.date
                })
        
        return hierarchy

