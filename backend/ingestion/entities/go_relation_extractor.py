"""
GO Relation Extractor
Extract first-class relations between Government Orders
Relations decide truth - not just metadata decoration
"""
import re
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GORelationExtractor:
    """
    Extract relations between Government Orders
    
    Relation Types:
    - supersedes: This GO replaces another GO
    - amends: This GO modifies another GO
    - clarifies: This GO explains another GO
    - references: This GO mentions another GO
    
    Strategy:
    1. Rule-based extraction first (cheap & reliable)
    2. LLM fallback for complex cases (expensive but accurate)
    """
    
    def __init__(self):
        """Initialize relation extraction patterns"""
        
        # GO number pattern (to extract target GOs)
        self.go_number_pattern = re.compile(
            r'G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
            re.IGNORECASE
        )
        
        # Supersession patterns
        self.supersession_patterns = [
            # "supersedes G.O.MS.No.123"
            re.compile(
                r'supersede[sd]?\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
            # "in supersession of G.O.MS.No.123"
            re.compile(
                r'in\s+supersession\s+of\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
            # "replaces G.O.MS.No.123"
            re.compile(
                r'replaces?\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
        ]
        
        # Amendment patterns
        self.amendment_patterns = [
            # "amends G.O.MS.No.123"
            re.compile(
                r'amend[sment]*\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
            # "in modification of G.O.MS.No.123"
            re.compile(
                r'in\s+(?:partial\s+)?modification\s+of\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
            # "modifies G.O.MS.No.123"
            re.compile(
                r'modif(?:y|ies|ied)\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
        ]
        
        # Clarification patterns
        self.clarification_patterns = [
            # "clarifies G.O.MS.No.123"
            re.compile(
                r'clarif(?:y|ies|ied|ication)\s+(?:of\s+)?G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
            # "for clarification of G.O.MS.No.123"
            re.compile(
                r'for\s+clarification\s+of\s+G\.?O\.?\s*(?:MS|RT|Rt)\.?\s*No\.?\s*(\d+)',
                re.IGNORECASE
            ),
        ]
        
        # Partial modification indicators
        self.partial_indicators = [
            re.compile(r'\bpartial\s+modification\b', re.IGNORECASE),
            re.compile(r'\bpara(?:graph)?\s+(\d+[A-Z]?)', re.IGNORECASE),
            re.compile(r'\bsection\s+(\d+[A-Z]?)', re.IGNORECASE),
            re.compile(r'\bclause\s+(\d+[A-Z]?)', re.IGNORECASE),
        ]
        
        logger.info("GO Relation Extractor initialized")
    
    def extract(self, text: str, source_go: str = "") -> List[Dict]:
        """
        Extract relations from GO text
        
        Args:
            text: GO document text
            source_go: Source GO number (e.g., "G.O.MS.No.45")
            
        Returns:
            List of relation dictionaries
        """
        if not text or not text.strip():
            return []
        
        relations = []
        
        # Extract supersession relations
        supersedes = self._extract_supersession_relations(text, source_go)
        relations.extend(supersedes)
        
        # Extract amendment relations
        amendments = self._extract_amendment_relations(text, source_go)
        relations.extend(amendments)
        
        # Extract clarification relations
        clarifications = self._extract_clarification_relations(text, source_go)
        relations.extend(clarifications)
        
        # Extract general references (if no specific relations found)
        if not relations:
            references = self._extract_reference_relations(text, source_go)
            relations.extend(references)
        
        # Deduplicate relations
        relations = self._deduplicate_relations(relations)
        
        return relations
    
    def _extract_supersession_relations(self, text: str, source_go: str) -> List[Dict]:
        """Extract supersession relations"""
        relations = []
        
        for pattern in self.supersession_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                target_go = f"G.O.MS.No.{match}"
                scope = self._determine_scope(text, target_go)
                section = self._extract_section_reference(text, target_go)
                
                relations.append({
                    "relation_type": "supersedes",
                    "source_go": source_go,
                    "target_go": target_go,
                    "scope": scope,
                    "section": section,
                    "confidence": 0.95
                })
        
        return relations
    
    def _extract_amendment_relations(self, text: str, source_go: str) -> List[Dict]:
        """Extract amendment relations"""
        relations = []
        
        for pattern in self.amendment_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                target_go = f"G.O.MS.No.{match}"
                scope = self._determine_scope(text, target_go)
                section = self._extract_section_reference(text, target_go)
                
                relations.append({
                    "relation_type": "amends",
                    "source_go": source_go,
                    "target_go": target_go,
                    "scope": scope,
                    "section": section,
                    "confidence": 0.95
                })
        
        return relations
    
    def _extract_clarification_relations(self, text: str, source_go: str) -> List[Dict]:
        """Extract clarification relations"""
        relations = []
        
        for pattern in self.clarification_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                target_go = f"G.O.MS.No.{match}"
                
                relations.append({
                    "relation_type": "clarifies",
                    "source_go": source_go,
                    "target_go": target_go,
                    "scope": "full",  # Clarifications typically apply to full GO
                    "section": None,
                    "confidence": 0.90
                })
        
        return relations
    
    def _extract_reference_relations(self, text: str, source_go: str) -> List[Dict]:
        """Extract general GO references (when no specific relation found)"""
        relations = []
        
        # Find all GO numbers mentioned
        matches = self.go_number_pattern.findall(text)
        
        for match in matches:
            if isinstance(match, tuple):
                match = match[0]
            
            target_go = f"G.O.MS.No.{match}"
            
            # Only add as reference if not already in a specific relation
            relations.append({
                "relation_type": "references",
                "source_go": source_go,
                "target_go": target_go,
                "scope": "unknown",
                "section": None,
                "confidence": 0.70
            })
        
        return relations
    
    def _determine_scope(self, text: str, target_go: str) -> str:
        """Determine if relation is full or partial"""
        # Look for partial modification indicators near the target GO
        # Simple heuristic: check 200 chars before and after GO mention
        
        go_pos = text.find(target_go)
        if go_pos == -1:
            return "unknown"
        
        context_start = max(0, go_pos - 200)
        context_end = min(len(text), go_pos + 200)
        context = text[context_start:context_end]
        
        # Check for partial indicators
        for pattern in self.partial_indicators:
            if pattern.search(context):
                return "partial"
        
        # Check for "full" keyword
        if re.search(r'\bfull\b', context, re.IGNORECASE):
            return "full"
        
        # Default to full for supersession, unknown for others
        return "full"
    
    def _extract_section_reference(self, text: str, target_go: str) -> Optional[str]:
        """Extract section/paragraph reference if partial modification"""
        go_pos = text.find(target_go)
        if go_pos == -1:
            return None
        
        context_start = max(0, go_pos - 200)
        context_end = min(len(text), go_pos + 200)
        context = text[context_start:context_end]
        
        # Look for paragraph/section references
        for pattern in self.partial_indicators[1:]:  # Skip the first (partial modification)
            match = pattern.search(context)
            if match:
                if len(match.groups()) > 0:
                    return match.group(0)  # Return full match (e.g., "Para 4")
        
        return None
    
    def _deduplicate_relations(self, relations: List[Dict]) -> List[Dict]:
        """Remove duplicate relations, keeping highest confidence"""
        seen = {}
        
        for relation in relations:
            key = (
                relation["relation_type"],
                relation["target_go"]
            )
            
            if key not in seen or relation["confidence"] > seen[key]["confidence"]:
                seen[key] = relation
        
        return list(seen.values())
    
    def extract_with_context(
        self, 
        text: str, 
        source_go: str,
        doc_id: str = ""
    ) -> Tuple[List[Dict], Dict[str, any]]:
        """
        Extract relations with additional context
        
        Returns:
            Tuple of (relations, context_info)
        """
        relations = self.extract(text, source_go)
        
        context = {
            "total_relations": len(relations),
            "relation_types": list(set(r["relation_type"] for r in relations)),
            "has_supersession": any(r["relation_type"] == "supersedes" for r in relations),
            "has_amendment": any(r["relation_type"] == "amends" for r in relations),
            "partial_modifications": sum(1 for r in relations if r.get("scope") == "partial"),
        }
        
        logger.info(
            f"Extracted {len(relations)} relations from {doc_id}: "
            f"{context['relation_types']}"
        )
        
        return relations, context
