"""
Reference Resolver
Resolves legal references (Sections, Rules, GOs) to canonical IDs
"""
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class CanonicalReference:
    """Represents a canonical legal reference"""
    canonical_id: str
    ref_type: str  # "section" | "rule" | "go"
    source_document: str
    title: Optional[str] = None
    implemented_by: List[str] = field(default_factory=list)
    amended_by: List[str] = field(default_factory=list)
    clarified_by: List[str] = field(default_factory=list)


@dataclass
class ResolutionResult:
    """Result of reference resolution"""
    canonical_id: Optional[str]
    confidence: float
    resolution_method: str  # "exact" | "fuzzy" | "inferred" | "failed"
    canonical_ref: Optional[CanonicalReference] = None
    alternatives: List[str] = field(default_factory=list)
    error_reason: Optional[str] = None


class ReferenceResolver:
    """
    Resolves legal references to canonical IDs
    
    Handles:
    - Section references (e.g., "Section 12", "Section 12(2)")
    - Rule references (e.g., "Rule 4", "Rule 4(I)")
    - GO references (e.g., "G.O.MS.No.20", "GO MS No 83")
    
    Features:
    - Exact matching
    - Fuzzy matching for OCR errors
    - Context-aware disambiguation
    - Confidence scoring
    """
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize resolver with canonical registry
        
        Args:
            registry_path: Path to canonical_registry.json
        """
        if registry_path is None:
            registry_path = Path(__file__).parent / "canonical_registry.json"
        
        self.registry_path = registry_path
        self.registry = self._load_registry()
        
        # Build lookup indexes
        self._build_indexes()
        
        logger.info(f"✅ Reference resolver initialized with {len(self.section_index)} sections, "
                   f"{len(self.rule_index)} rules, {len(self.go_index)} GOs")
    
    def _load_registry(self) -> Dict:
        """Load canonical registry from JSON"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {"acts": {}, "rules": {}, "go_index": {}}
    
    def _build_indexes(self):
        """Build fast lookup indexes"""
        self.section_index = {}  # section_num -> List[CanonicalReference]
        self.rule_index = {}     # rule_num -> List[CanonicalReference]
        self.go_index = {}       # go_num -> {year -> CanonicalReference}
        
        # Index sections
        for act_id, act_data in self.registry.get("acts", {}).items():
            for section_num, section_data in act_data.get("sections", {}).items():
                ref = CanonicalReference(
                    canonical_id=section_data["canonical_id"],
                    ref_type="section",
                    source_document=act_data["full_name"],
                    title=section_data.get("title"),
                    implemented_by=section_data.get("implemented_by", []),
                    amended_by=section_data.get("amended_by", []),
                    clarified_by=section_data.get("clarified_by", [])
                )
                
                if section_num not in self.section_index:
                    self.section_index[section_num] = []
                self.section_index[section_num].append(ref)
        
        # Index rules
        for rule_id, rule_data in self.registry.get("rules", {}).items():
            for rule_num, rule_info in rule_data.get("rules", {}).items():
                ref = CanonicalReference(
                    canonical_id=rule_info["canonical_id"],
                    ref_type="rule",
                    source_document=rule_data["full_name"],
                    title=rule_info.get("title"),
                    implemented_by=rule_info.get("implemented_by", []),
                    amended_by=rule_info.get("amended_by", []),
                    clarified_by=rule_info.get("clarified_by", [])
                )
                
                if rule_num not in self.rule_index:
                    self.rule_index[rule_num] = []
                self.rule_index[rule_num].append(ref)
        
        # Index GOs
        for go_num, go_data in self.registry.get("go_index", {}).items():
            if go_num not in self.go_index:
                self.go_index[go_num] = {}
            
            # Handle multiple years for same GO number
            if isinstance(go_data, dict) and "year" in go_data:
                year = str(go_data["year"])
                self.go_index[go_num][year] = go_data
            else:
                # Legacy format: go_data is year -> info
                for year, info in go_data.items():
                    if isinstance(info, dict):
                        self.go_index[go_num][year] = info
    
    def resolve_section(
        self, 
        section_text: str, 
        context: Optional[str] = None
    ) -> ResolutionResult:
        """
        Resolve a section reference
        
        Args:
            section_text: Raw section text (e.g., "Section 12", "Section 12(2)")
            context: Optional context for disambiguation
            
        Returns:
            ResolutionResult
        """
        # Extract section number
        section_match = re.search(r'Section\s+(\d+(?:\([a-z0-9]+\))?)', section_text, re.IGNORECASE)
        if not section_match:
            return ResolutionResult(
                canonical_id=None,
                confidence=0.0,
                resolution_method="failed",
                error_reason="Could not extract section number"
            )
        
        section_num = section_match.group(1)
        base_section = section_num.split('(')[0]  # "12(2)" -> "12"
        
        # Exact match
        if base_section in self.section_index:
            candidates = self.section_index[base_section]
            
            # If multiple candidates, use context to disambiguate
            if len(candidates) == 1:
                return ResolutionResult(
                    canonical_id=candidates[0].canonical_id,
                    confidence=0.95,
                    resolution_method="exact",
                    canonical_ref=candidates[0]
                )
            else:
                # Disambiguate using context
                best_candidate = self._disambiguate_by_context(candidates, context)
                return ResolutionResult(
                    canonical_id=best_candidate.canonical_id,
                    confidence=0.85,
                    resolution_method="exact_with_disambiguation",
                    canonical_ref=best_candidate,
                    alternatives=[c.canonical_id for c in candidates if c != best_candidate]
                )
        
        # Fuzzy match for OCR errors
        fuzzy_result = self._fuzzy_match_section(base_section)
        if fuzzy_result:
            return fuzzy_result
        
        return ResolutionResult(
            canonical_id=None,
            confidence=0.0,
            resolution_method="failed",
            error_reason=f"Section {section_num} not found in registry"
        )
    
    def resolve_rule(
        self, 
        rule_text: str, 
        context: Optional[str] = None
    ) -> ResolutionResult:
        """
        Resolve a rule reference
        
        Args:
            rule_text: Raw rule text (e.g., "Rule 4", "Rule 4(I)")
            context: Optional context for disambiguation
            
        Returns:
            ResolutionResult
        """
        # Extract rule number
        rule_match = re.search(r'Rule\s+(\d+(?:\([IVXivx0-9a-z]+\))?)', rule_text, re.IGNORECASE)
        if not rule_match:
            return ResolutionResult(
                canonical_id=None,
                confidence=0.0,
                resolution_method="failed",
                error_reason="Could not extract rule number"
            )
        
        rule_num = rule_match.group(1)
        base_rule = rule_num.split('(')[0]
        
        # Exact match
        if base_rule in self.rule_index:
            candidates = self.rule_index[base_rule]
            
            if len(candidates) == 1:
                return ResolutionResult(
                    canonical_id=candidates[0].canonical_id,
                    confidence=0.95,
                    resolution_method="exact",
                    canonical_ref=candidates[0]
                )
            else:
                best_candidate = self._disambiguate_by_context(candidates, context)
                return ResolutionResult(
                    canonical_id=best_candidate.canonical_id,
                    confidence=0.85,
                    resolution_method="exact_with_disambiguation",
                    canonical_ref=best_candidate,
                    alternatives=[c.canonical_id for c in candidates if c != best_candidate]
                )
        
        return ResolutionResult(
            canonical_id=None,
            confidence=0.0,
            resolution_method="failed",
            error_reason=f"Rule {rule_num} not found in registry"
        )
    
    def resolve_go(
        self, 
        go_number: str, 
        year: Optional[str] = None,
        context: Optional[str] = None
    ) -> ResolutionResult:
        """
        Resolve a GO reference
        
        Args:
            go_number: GO number (e.g., "20", "83")
            year: Optional year (e.g., "2011", "2008")
            context: Optional context for year inference
            
        Returns:
            ResolutionResult
        """
        # Normalize GO number (remove non-digits)
        go_num_clean = re.sub(r'\D', '', go_number)
        
        if not go_num_clean:
            return ResolutionResult(
                canonical_id=None,
                confidence=0.0,
                resolution_method="failed",
                error_reason="Invalid GO number"
            )
        
        # Check if GO exists in index
        if go_num_clean not in self.go_index:
            # Try fuzzy match
            fuzzy_result = self._fuzzy_match_go(go_num_clean)
            if fuzzy_result:
                return fuzzy_result
            
            return ResolutionResult(
                canonical_id=None,
                confidence=0.0,
                resolution_method="failed",
                error_reason=f"GO {go_num_clean} not found in registry"
            )
        
        go_years = self.go_index[go_num_clean]
        
        # If year provided, exact match
        if year:
            year_clean = str(year)
            if year_clean in go_years:
                go_data = go_years[year_clean]
                canonical_id = go_data.get("canonical_id") or f"GO.MS.No.{go_num_clean}_{year_clean}"
                return ResolutionResult(
                    canonical_id=canonical_id,
                    confidence=0.95,
                    resolution_method="exact",
                    canonical_ref=CanonicalReference(
                        canonical_id=canonical_id,
                        ref_type="go",
                        source_document=go_data.get("subject", ""),
                        implemented_by=[],
                        amended_by=[],
                        clarified_by=[]
                    )
                )
        
        # No year provided - infer from context or return most recent
        if len(go_years) == 1:
            year_clean = list(go_years.keys())[0]
            go_data = go_years[year_clean]
            canonical_id = go_data.get("canonical_id") or f"GO.MS.No.{go_num_clean}_{year_clean}"
            return ResolutionResult(
                canonical_id=canonical_id,
                confidence=0.90,
                resolution_method="inferred_single_year",
                canonical_ref=CanonicalReference(
                    canonical_id=canonical_id,
                    ref_type="go",
                    source_document=go_data.get("subject", ""),
                    implemented_by=[],
                    amended_by=[],
                    clarified_by=[]
                )
            )
        
        # Multiple years - return most recent with lower confidence
        most_recent_year = max(go_years.keys(), key=lambda y: int(y))
        go_data = go_years[most_recent_year]
        canonical_id = go_data.get("canonical_id") or f"GO.MS.No.{go_num_clean}_{most_recent_year}"
        
        return ResolutionResult(
            canonical_id=canonical_id,
            confidence=0.70,
            resolution_method="inferred_most_recent",
            canonical_ref=CanonicalReference(
                canonical_id=canonical_id,
                ref_type="go",
                source_document=go_data.get("subject", ""),
                implemented_by=[],
                amended_by=[],
                clarified_by=[]
            ),
            alternatives=[f"GO.MS.No.{go_num_clean}_{y}" for y in go_years.keys() if y != most_recent_year]
        )
    
    def resolve_target_ref(self, target_ref: Dict, context: Optional[str] = None) -> Dict:
        """
        Resolve a target_ref dictionary (from relation extraction)
        
        Args:
            target_ref: Dictionary with raw_text, go_number, year, etc.
            context: Optional context text
            
        Returns:
            Updated target_ref with canonical_id and resolution metadata
        """
        raw_text = target_ref.get("raw_text", "")
        go_number = target_ref.get("go_number")
        year = target_ref.get("year")
        
        # Determine reference type
        if "section" in raw_text.lower():
            result = self.resolve_section(raw_text, context)
        elif "rule" in raw_text.lower():
            result = self.resolve_rule(raw_text, context)
        elif go_number:
            result = self.resolve_go(go_number, year, context)
        else:
            # Try to infer from raw_text
            if re.search(r'G\.?O\.?(?:MS|RT)?', raw_text, re.IGNORECASE):
                # Extract GO number
                go_match = re.search(r'No\.?\s*(\d+)', raw_text, re.IGNORECASE)
                if go_match:
                    result = self.resolve_go(go_match.group(1), year, context)
                else:
                    result = ResolutionResult(None, 0.0, "failed", error_reason="Could not extract GO number")
            else:
                result = ResolutionResult(None, 0.0, "failed", error_reason="Unknown reference type")
        
        # Update target_ref
        target_ref["canonical_id"] = result.canonical_id
        target_ref["resolution_status"] = "resolved" if result.canonical_id else "unresolved"
        target_ref["resolution_confidence"] = result.confidence
        target_ref["resolution_method"] = result.resolution_method
        
        if result.canonical_ref:
            target_ref["resolved_doc_id"] = result.canonical_ref.canonical_id
            target_ref["implemented_by"] = result.canonical_ref.implemented_by
            target_ref["amended_by"] = result.canonical_ref.amended_by
            target_ref["clarified_by"] = result.canonical_ref.clarified_by
        
        if result.alternatives:
            target_ref["alternatives"] = result.alternatives
        
        if result.error_reason:
            target_ref["resolution_error"] = result.error_reason
        
        return target_ref
    
    def _disambiguate_by_context(
        self, 
        candidates: List[CanonicalReference], 
        context: Optional[str]
    ) -> CanonicalReference:
        """Disambiguate multiple candidates using context"""
        if not context:
            return candidates[0]  # Default to first
        
        context_lower = context.lower()
        
        # Score each candidate by context match
        scores = []
        for candidate in candidates:
            score = 0
            
            # Check if source document mentioned in context
            if candidate.source_document.lower() in context_lower:
                score += 10
            
            # Check for keywords
            if "rte" in context_lower and "rte" in candidate.source_document.lower():
                score += 5
            if "education act" in context_lower and "education act" in candidate.source_document.lower():
                score += 5
            
            scores.append(score)
        
        # Return candidate with highest score
        best_idx = scores.index(max(scores))
        return candidates[best_idx]
    
    def _fuzzy_match_section(self, section_num: str) -> Optional[ResolutionResult]:
        """Fuzzy match for OCR-damaged section numbers"""
        best_match = None
        best_ratio = 0.0
        
        for candidate_num in self.section_index.keys():
            ratio = SequenceMatcher(None, section_num, candidate_num).ratio()
            if ratio > best_ratio and ratio > 0.8:  # 80% similarity threshold
                best_ratio = ratio
                best_match = candidate_num
        
        if best_match:
            candidates = self.section_index[best_match]
            return ResolutionResult(
                canonical_id=candidates[0].canonical_id,
                confidence=0.70 * best_ratio,  # Penalize fuzzy matches
                resolution_method="fuzzy",
                canonical_ref=candidates[0],
                alternatives=[c.canonical_id for c in candidates[1:]]
            )
        
        return None
    
    def _fuzzy_match_go(self, go_num: str) -> Optional[ResolutionResult]:
        """Fuzzy match for OCR-damaged GO numbers"""
        best_match = None
        best_ratio = 0.0
        
        for candidate_num in self.go_index.keys():
            ratio = SequenceMatcher(None, go_num, candidate_num).ratio()
            if ratio > best_ratio and ratio > 0.85:  # Higher threshold for GOs
                best_ratio = ratio
                best_match = candidate_num
        
        if best_match:
            go_years = self.go_index[best_match]
            most_recent_year = max(go_years.keys(), key=lambda y: int(y))
            go_data = go_years[most_recent_year]
            canonical_id = go_data.get("canonical_id") or f"GO.MS.No.{best_match}_{most_recent_year}"
            
            return ResolutionResult(
                canonical_id=canonical_id,
                confidence=0.65 * best_ratio,
                resolution_method="fuzzy",
                canonical_ref=CanonicalReference(
                    canonical_id=canonical_id,
                    ref_type="go",
                    source_document=go_data.get("subject", ""),
                    implemented_by=[],
                    amended_by=[],
                    clarified_by=[]
                )
            )
        
        return None
