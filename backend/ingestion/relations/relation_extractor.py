"""
Relation Extractor with LLM
Extracts document relationships: supersedes, amends, clarifies, references
Uses Gemini for high accuracy on important documents
"""
import re
import json
import logging
import os
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import google.auth
from google.oauth2 import service_account
from google import genai as genai_new
from ..utils.llm_cache import get_cache
from ..resolution.reference_resolver import ReferenceResolver

logger = logging.getLogger(__name__)


@dataclass
class Relation:
    """Represents a document relation"""
    relation_type: str  # supersedes, cancels, amends, clarifies, references
    source_id: str  # Source document/chunk ID
    target_ref: Dict  # Structured target reference (NOT string)
    confidence: float
    context: str  # Surrounding text
    scope: str = "document"  # document | paragraph
    source_para: Optional[str] = None
    section: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


def adjust_confidence_for_ocr(text: str, base_conf: float) -> float:
    """Downgrade confidence if OCR noise is detected"""
    if re.search(r'\b[0-9][A-Z]\b', text):  # 8B, 1O, etc
        return base_conf * 0.6
    if "vide" in text.lower():
        return base_conf * 0.8
    return base_conf


class RelationExtractor:
    """
    Extract document relations using hybrid approach:
    1. Fast regex patterns for clear cases
    2. LLM for complex/ambiguous cases
    3. Reference resolution for canonical IDs
    
    STRICT RULES:
    - Only 5 allowed relation types: supersedes, cancels, amends, clarifies, references
    - Precedence: supersedes > cancels > amends > clarifies > references
    - No self-references (source_id == target_id)
    - Deduplication on (source_id, target_id, relation_type)
    - Resolution routing: resolved → go_legal_relations, unresolved → go_relation_candidates
    """
    
    # STRICT: Only these 7 relation types are allowed (added overrules/overruled_by for judicial)
    ALLOWED_RELATION_TYPES = {"supersedes", "cancels", "amends", "clarifies", "references", "overrules", "overruled_by"}
    
    # MANDATORY: Relation precedence for conflict resolution
    RELATION_PRECEDENCE = {
        "overrules": 6,  # Highest precedence for judicial overruling
        "supersedes": 5,
        "cancels": 4,
        "amends": 3,
        "clarifies": 2,
        "references": 1,
        "overruled_by": 0  # Inverse relation, lower precedence
    }
    
    def __init__(self, use_llm: bool = True, project_id: str = None, location: str = "asia-south1", 
                 use_resolver: bool = True):
        """
        Initialize relation extractor using Vertex AI
        
        Args:
            use_llm: Whether to use LLM for complex cases
            project_id: GCP Project ID
            location: GCP Region
            use_resolver: Whether to use reference resolver
        """
        self.use_llm = use_llm
        self.location = location
        self.cache = get_cache()
        self.use_resolver = use_resolver
        
        # Initialize reference resolver
        if self.use_resolver:
            try:
                self.resolver = ReferenceResolver()
                logger.info("✅ Reference resolver initialized")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize resolver: {e}")
                self.use_resolver = False
                self.resolver = None
        else:
            self.resolver = None
        
        if self.use_llm:
            try:
                # Resolve Project ID
                self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
                
                # Get credentials
                service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if service_account_file and os.path.exists(service_account_file):
                    scopes = ['https://www.googleapis.com/auth/cloud-platform']
                    creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
                    
                    if not self.project_id:
                        with open(service_account_file, 'r') as f:
                            self.project_id = json.load(f).get('project_id')
                else:
                    creds, computed_project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
                    self.project_id = self.project_id or computed_project

                if not self.project_id:
                    logger.warning("GOOGLE_CLOUD_PROJECT_ID not found - Disabling LLM relations")
                    self.use_llm = False
                else:
                    # Initialize Vertex AI Client
                    self.client = genai_new.Client(
                        vertexai=True,
                        project=self.project_id,
                        location=self.location,
                        credentials=creds,
                    )
                    logger.info("✅ Vertex AI initialized for relation extraction")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Vertex AI: {e}")
                self.use_llm = False
        
        # Compile regex patterns (only for allowed types)
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for relation extraction (ONLY ALLOWED TYPES)"""
        
        # SUPERSEDES patterns
        self.supersedes_patterns = [
            re.compile(r'supersedes?\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in supersession of\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)\s+(?:is|are)\s+hereby\s+(?:rescinded|superseded)', re.IGNORECASE)
        ]
        
        # CANCELS patterns
        self.cancels_patterns = [
            re.compile(r'cancels?\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)\s+(?:is|are)\s+hereby\s+cancelled', re.IGNORECASE),
            re.compile(r'in cancellation of\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE)
        ]
        
        # AMENDS patterns
        self.amends_patterns = [
            re.compile(r'amends?\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in\s+(?:partial\s+)?amendment\s+(?:of|to)\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:Section|Rule)\s+(\d+)\s+(?:is|are)\s+(?:hereby\s+)?amended', re.IGNORECASE)
        ]
        
        # CLARIFIES patterns
        self.clarifies_patterns = [
            re.compile(r'clarifies\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in clarification of\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE)
        ]
        
        # REFERENCES patterns (catch-all for citations)
        self.references_patterns = [
            re.compile(r'(?:as per|under|in accordance with)\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'vide\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'in terms of\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE),
            re.compile(r'(?:read with|with reference to)\s+(?:G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*)?(\d+)', re.IGNORECASE)
        ]
        
        # OVERRULES patterns (judicial vertical only)
        self.overrules_patterns = [
            re.compile(r'overrules?\s+(?:the\s+)?(?:judgment|case|decision|precedent|ruling)\s+(?:in\s+)?(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)', re.IGNORECASE),
            re.compile(r'overruled?\s+(?:by|in)\s+(?:the\s+)?(?:judgment|case|decision|precedent|ruling)\s+(?:in\s+)?(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)', re.IGNORECASE),
            re.compile(r'(?:judgment|case|decision|precedent|ruling)\s+(?:in\s+)?(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)\s+(?:is|has been|was)\s+overruled', re.IGNORECASE),
            re.compile(r'overruling\s+(?:the\s+)?(?:judgment|case|decision|precedent|ruling)\s+(?:in\s+)?(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)', re.IGNORECASE)
        ]
        
        # OVERRULED_BY patterns (inverse relation)
        self.overruled_by_patterns = [
            re.compile(r'(?:this|the)\s+(?:judgment|case|decision|precedent|ruling)\s+(?:is|has been|was)\s+overruled\s+(?:by|in)\s+(?:the\s+)?(?:judgment|case|decision|precedent|ruling)\s+(?:in\s+)?(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)', re.IGNORECASE),
            re.compile(r'overruled\s+(?:by|in)\s+(?:[A-Z][a-z]+\s+)?v\.?\s+(?:[A-Z][a-z]+)', re.IGNORECASE)
        ]
    
    def extract_relations(
        self, 
        text: str, 
        doc_id: str, 
        doc_type: str,
        use_llm_fallback: bool = True,
        entities: Dict = None
    ) -> List[Relation]:
        """
        Extract all relations from text
        
        CRITICAL SEQUENCING:
        1. Extract from entities (Phase 1 LLM)
        2. Extract with regex patterns
        3. Filter to allowed types ONLY
        4. Drop self-references (pre-resolution)
        5. Validate and filter
        6. Apply LLM fallback if needed
        7. Resolve references
        8. Drop self-references (post-resolution)
        9. Apply precedence rules
        10. Deduplicate on (source_id, target_id, relation_type)
        """
        relations = []
        
        # Step 1: Consume Phase 1 high-quality entities
        if entities and "legal_actions" in entities and doc_type == "go":
            phase1_relations = self._convert_entities_to_relations(entities["legal_actions"], doc_id)
            if phase1_relations:
                logger.info(f"✅ Using {len(phase1_relations)} high-precision relations from Phase 1")
                relations.extend(phase1_relations)
        
        # Step 2: Extract with regex patterns (only allowed types)
        relations.extend(self._extract_supersedes(text, doc_id))
        relations.extend(self._extract_cancels(text, doc_id))
        relations.extend(self._extract_amends(text, doc_id))
        relations.extend(self._extract_clarifies(text, doc_id))
        relations.extend(self._extract_references(text, doc_id))
        
        # Extract overrules/overruled_by only for judicial documents
        if doc_type == "judicial":
            relations.extend(self._extract_overrules(text, doc_id))
            relations.extend(self._extract_overruled_by(text, doc_id))
        
        # Step 3: Filter to allowed types ONLY
        relations = self._filter_allowed_types(relations)
        
        # Step 4: Drop self-references (pre-resolution check)
        relations = self._drop_self_references_pre_resolution(relations, doc_id)
        
        # Step 5: Validate and filter
        if relations:
            relations = self._validate_and_filter_relations(relations, text, doc_id)
        
        # Step 6: LLM fallback if needed
        max_conf = max([r.confidence for r in relations]) if relations else 0
        should_use_llm = False
        
        if not relations:
            should_use_llm = True
        elif max_conf < 0.75:
            logger.info(f"Low confidence ({max_conf:.2f}) in regex relations for {doc_id}, triggering LLM")
            should_use_llm = True
        
        if should_use_llm and self.use_llm and use_llm_fallback:
            if doc_type in ('go', 'legal', 'judicial'):
                logger.info(f"No high-confidence relations found, trying LLM for {doc_id}")
                llm_relations = self._extract_with_llm(text, doc_id, doc_type)
                llm_relations = self._filter_allowed_types(llm_relations)
                relations.extend(llm_relations)
        
        # Step 7: Resolve all references to canonical IDs
        if relations and self.use_resolver and self.resolver:
            logger.info(f"🔗 Resolving {len(relations)} references for {doc_id}")
            relations = self._resolve_all_references(relations, text)
        
        # Step 8: Drop self-references (post-resolution check - CRITICAL)
        relations = self._drop_self_references_post_resolution(relations)
        
        # Step 9: Apply precedence rules (keep highest precedence per target)
        relations = self._apply_precedence_rules(relations)
        
        # Step 10: Deduplicate on (source_id, target_id, relation_type)
        relations = self._deduplicate_relations(relations)
        
        logger.info(f"✅ Extracted {len(relations)} final relations from {doc_id}")
        
        return relations
    
    def _filter_allowed_types(self, relations: List[Relation]) -> List[Relation]:
        """
        Filter relations to only allowed types
        DROP everything else
        """
        filtered = []
        dropped_count = 0
        
        for rel in relations:
            if rel.relation_type in self.ALLOWED_RELATION_TYPES:
                filtered.append(rel)
            else:
                dropped_count += 1
                logger.debug(f"Dropped disallowed relation type: {rel.relation_type}")
        
        if dropped_count > 0:
            logger.info(f"Dropped {dropped_count} relations with disallowed types")
        
        return filtered
    
    def _drop_self_references_pre_resolution(self, relations: List[Relation], doc_id: str) -> List[Relation]:
        """
        Drop self-references BEFORE resolution
        Check against raw GO numbers extracted from doc_id
        """
        # Parse source GO number from doc_id
        source_go_num = None
        source_match = re.search(r'(?:ms|rt|go)[._-]?(\d+)', doc_id, re.IGNORECASE)
        if source_match:
            source_go_num = source_match.group(1)
        
        filtered = []
        for rel in relations:
            go_num = rel.target_ref.get("go_number")
            
            # Check for self-reference
            is_self_ref = False
            if go_num and source_go_num and go_num == source_go_num:
                is_self_ref = True
            elif go_num and go_num in doc_id:  # Fallback string check
                is_self_ref = True
            
            if is_self_ref:
                logger.warning(f"⚠️ [PRE-RESOLUTION] Discarding self-reference: GO {go_num} in {doc_id}")
                continue
            
            filtered.append(rel)
        
        dropped = len(relations) - len(filtered)
        if dropped > 0:
            logger.info(f"Dropped {dropped} self-references (pre-resolution)")
        
        return filtered
    
    def _drop_self_references_post_resolution(self, relations: List[Relation]) -> List[Relation]:
        """
        Drop self-references AFTER resolution
        CRITICAL: Check source_id == resolved_doc_id
        This catches cases where different GO numbers resolve to the same document
        """
        filtered = []
        
        for rel in relations:
            source_id = rel.source_id
            target_id = rel.target_ref.get("resolved_doc_id")
            
            # Check for self-reference after resolution
            if target_id and source_id == target_id:
                logger.warning(f"⚠️ [POST-RESOLUTION] Discarding self-reference: {source_id} == {target_id}")
                continue
            
            filtered.append(rel)
        
        dropped = len(relations) - len(filtered)
        if dropped > 0:
            logger.info(f"Dropped {dropped} self-references (post-resolution)")
        
        return filtered
    
    def _apply_precedence_rules(self, relations: List[Relation]) -> List[Relation]:
        """
        Apply precedence rules: supersedes > cancels > amends > clarifies > references
        
        If multiple relations exist between same source and target,
        keep ONLY the highest precedence relation.
        """
        # Group by (source_id, target_id)
        target_groups = {}
        
        for rel in relations:
            # Use resolved ID if available, else GO number, else raw text
            target_key = (
                rel.target_ref.get("resolved_doc_id") or 
                rel.target_ref.get("go_number") or 
                rel.target_ref.get("raw_text", "").lower().strip()
            )
            
            group_key = (rel.source_id, target_key)
            
            if group_key not in target_groups:
                target_groups[group_key] = []
            target_groups[group_key].append(rel)
        
        # Apply precedence for each group
        final_relations = []
        conflicts_resolved = 0
        
        for group_key, group in target_groups.items():
            if len(group) == 1:
                final_relations.append(group[0])
            else:
                # Multiple relations to same target - apply precedence
                conflicts_resolved += 1
                
                # Sort by precedence (descending) then confidence
                sorted_group = sorted(
                    group,
                    key=lambda r: (
                        self.RELATION_PRECEDENCE.get(r.relation_type, 0),
                        r.confidence
                    ),
                    reverse=True
                )
                
                winner = sorted_group[0]
                
                # Log the conflict resolution
                types_in_group = [r.relation_type for r in group]
                logger.info(f"Resolved precedence conflict for {group_key[0]} → {group_key[1]}: "
                           f"{types_in_group} → kept '{winner.relation_type}'")
                
                final_relations.append(winner)
        
        if conflicts_resolved > 0:
            logger.info(f"✅ Resolved {conflicts_resolved} precedence conflicts")
        
        return final_relations
    
    def _deduplicate_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        Deduplicate relations on (source_id, target_id, relation_type)
        
        This is the FINAL deduplication after precedence rules.
        Should rarely find duplicates at this stage.
        """
        seen = set()
        unique_relations = []
        
        for rel in relations:
            # Use resolved ID if available
            target_id = (
                rel.target_ref.get("resolved_doc_id") or
                rel.target_ref.get("go_number") or
                rel.target_ref.get("raw_text", "").lower().strip()
            )
            
            # Deduplication key: (source_id, target_id, relation_type)
            key = (rel.source_id, target_id, rel.relation_type)
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
            else:
                logger.debug(f"Dropped duplicate relation: {key}")
        
        dropped = len(relations) - len(unique_relations)
        if dropped > 0:
            logger.info(f"Dropped {dropped} duplicate relations")
        
        return unique_relations
    
    def _resolve_all_references(self, relations: List[Relation], context: str) -> List[Relation]:
        """
        Resolve all target_refs to canonical IDs
        """
        resolved_relations = []
        resolution_stats = {"resolved": 0, "unresolved": 0, "low_confidence": 0}
        
        for relation in relations:
            try:
                # Get context around this relation
                rel_context = relation.context if relation.context else context[:500]
                
                # Resolve the target reference
                resolved_target_ref = self.resolver.resolve_target_ref(
                    relation.target_ref,
                    context=rel_context
                )
                
                # Update relation with resolved info
                relation.target_ref = resolved_target_ref
                
                # Track resolution stats
                if resolved_target_ref.get("resolution_status") == "resolved":
                    resolution_stats["resolved"] += 1
                    
                    # Adjust relation confidence based on resolution confidence
                    resolution_conf = resolved_target_ref.get("resolution_confidence", 0.0)
                    if resolution_conf < 0.7:
                        resolution_stats["low_confidence"] += 1
                        # Penalize overall relation confidence
                        relation.confidence *= resolution_conf
                else:
                    resolution_stats["unresolved"] += 1
                    # Heavy penalty for unresolved references
                    relation.confidence *= 0.3
                
                resolved_relations.append(relation)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to resolve reference: {e}")
                # Keep relation but mark as unresolved
                relation.target_ref["resolution_status"] = "error"
                relation.target_ref["resolution_error"] = str(e)
                relation.confidence *= 0.2
                resolved_relations.append(relation)
        
        logger.info(f"   📊 Resolution: {resolution_stats['resolved']} resolved, "
                   f"{resolution_stats['unresolved']} unresolved, "
                   f"{resolution_stats['low_confidence']} low confidence")
        
        return resolved_relations
    
    def _convert_entities_to_relations(self, legal_actions: List[Dict], doc_id: str) -> List[Relation]:
        """Convert strict legal actions from Phase 1 (LLM) to Relations"""
        relations = []
        
        for action in legal_actions:
            act_type = action.get("action")
            target = action.get("target")
            
            if not act_type or not target:
                continue
            
            # Strict mapping to allowed types
            rel_type = None
            if act_type == "amends":
                rel_type = "amends"
            elif act_type in ("supersedes", "repeals", "revokes"):
                rel_type = "supersedes"
            elif act_type == "cancels":
                rel_type = "cancels"
            elif act_type == "clarifies":
                rel_type = "clarifies"
            elif act_type == "references":
                rel_type = "references"
            else:
                # Drop any other types (e.g., "issues", "modifies")
                logger.debug(f"Dropping non-standard legal action: {act_type}")
                continue
            
            # Extract GO number
            go_num = None
            num_match = re.search(r'(\d+)', target)
            if num_match:
                go_num = num_match.group(1)
            
            target_ref = {
                "raw_text": target,
                "go_number": go_num,
                "year": None,
                "resolved_doc_id": None,
                "resolution_status": "unresolved"
            }
            
            relations.append(Relation(
                relation_type=rel_type,
                source_id=doc_id,
                target_ref=target_ref,
                confidence=0.99,  # Very high confidence for Phase 1 extraction
                context=f"Legal Action: {act_type} {target}",
                scope="document"
            ))
        
        return relations
    
    def _validate_and_filter_relations(self, relations: List[Relation], text: str, doc_id: str) -> List[Relation]:
        """
        Validate and filter relations
        - Check for hallucinations
        - Flag OCR risks
        - Drop distribution list references
        """
        valid_relations = []
        
        # Find all alphanumeric candidates that could be GO numbers
        all_alnum_in_text = set(re.findall(r'\b[A-Za-z0-9.-]+\b', text))
        
        for rel in relations:
            go_num = rel.target_ref.get("go_number")
            raw_target = rel.target_ref.get("raw_text", "")
            
            # 1. Hallucination Check
            is_present = (
                (go_num and go_num in all_alnum_in_text) or
                (raw_target and raw_target in text) or
                (rel.confidence > 0.98)  # Trust Phase 1 high-confidence
            )
            
            if go_num and not is_present:
                logger.warning(f"⚠️ Discarding LLM hallucination: GO {go_num} not found in text")
                continue
            
            # 2. OCR Awareness
            if go_num and (not go_num.isdigit() or re.search(r'\b[0-9][A-Z]\b', rel.context)):
                rel.metadata = rel.metadata or {}
                rel.metadata["ocr_risk"] = True
                rel.confidence *= 0.5
            
            # 3. Distribution list filter
            context_lower = rel.context.lower()
            if "copy to" in context_lower or "forwarded" in context_lower:
                logger.warning(f"⚠️ Discarding distribution list reference: {raw_target}")
                continue
            
            valid_relations.append(rel)
        
        return valid_relations
    
    def _extract_supersedes(self, text: str, doc_id: str) -> List[Relation]:
        """Extract supersedes relations"""
        relations = []
        
        for pattern in self.supersedes_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                go_number = match.group(1)
                
                target_ref = {
                    "raw_text": f"G.O.MS.No.{go_number}",
                    "go_number": go_number,
                    "year": None,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                scope = "document"
                if "partially" in context.lower():
                    scope = "paragraph"
                
                conf = adjust_confidence_for_ocr(go_number, 0.95)
                
                relations.append(Relation(
                    relation_type="supersedes",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=conf,
                    context=context,
                    scope=scope
                ))
        
        return relations
    
    def _extract_cancels(self, text: str, doc_id: str) -> List[Relation]:
        """Extract cancels relations"""
        relations = []
        
        for pattern in self.cancels_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                go_number = match.group(1)
                
                target_ref = {
                    "raw_text": f"G.O.MS.No.{go_number}",
                    "go_number": go_number,
                    "year": None,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                conf = adjust_confidence_for_ocr(go_number, 0.95)
                
                relations.append(Relation(
                    relation_type="cancels",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=conf,
                    context=context,
                    scope="document"
                ))
        
        return relations
    
    def _extract_amends(self, text: str, doc_id: str) -> List[Relation]:
        """Extract amends relations"""
        relations = []
        
        for pattern in self.amends_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                go_number = match.group(1)
                
                target_ref = {
                    "raw_text": match.group(0),
                    "go_number": go_number,
                    "year": None,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                conf = adjust_confidence_for_ocr(go_number, 0.90)
                
                relations.append(Relation(
                    relation_type="amends",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=conf,
                    context=context,
                    scope="paragraph"
                ))
        
        return relations
    
    def _extract_clarifies(self, text: str, doc_id: str) -> List[Relation]:
        """Extract clarifies relations"""
        relations = []
        
        for pattern in self.clarifies_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                go_number = match.group(1)
                
                target_ref = {
                    "raw_text": match.group(0),
                    "go_number": go_number,
                    "year": None,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                conf = adjust_confidence_for_ocr(go_number, 0.90)
                
                relations.append(Relation(
                    relation_type="clarifies",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=conf,
                    context=context,
                    scope="document"
                ))
        
        return relations
    
    def _extract_references(self, text: str, doc_id: str) -> List[Relation]:
        """Extract references relations (catch-all)"""
        relations = []
        
        for pattern in self.references_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                
                go_number = match.group(1)
                
                target_ref = {
                    "raw_text": match.group(0),
                    "go_number": go_number if go_number.isdigit() else None,
                    "year": None,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                conf = adjust_confidence_for_ocr(go_number, 0.85)
                
                relations.append(Relation(
                    relation_type="references",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=conf,
                    context=context,
                    scope="paragraph"
                ))
        
        return relations
    
    def _extract_overrules(self, text: str, doc_id: str) -> List[Relation]:
        """Extract overrules relations (judicial vertical only)"""
        relations = []
        
        for pattern in self.overrules_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                
                # Extract case name from match
                case_match = match.group(0)
                
                target_ref = {
                    "raw_text": case_match,
                    "case_name": case_match,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                relations.append(Relation(
                    relation_type="overrules",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=0.85,  # Lower confidence for case name extraction
                    context=context,
                    scope="document"
                ))
        
        return relations
    
    def _extract_overruled_by(self, text: str, doc_id: str) -> List[Relation]:
        """Extract overruled_by relations (judicial vertical only)"""
        relations = []
        
        for pattern in self.overruled_by_patterns:
            for match in pattern.finditer(text):
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                
                # Extract case name from match
                case_match = match.group(0)
                
                target_ref = {
                    "raw_text": case_match,
                    "case_name": case_match,
                    "resolved_doc_id": None,
                    "resolution_status": "unresolved"
                }
                
                relations.append(Relation(
                    relation_type="overruled_by",
                    source_id=doc_id,
                    target_ref=target_ref,
                    confidence=0.85,
                    context=context,
                    scope="document"
                ))
        
        return relations
    
    def _extract_with_llm(
        self,
        text: str,
        doc_id: str,
        doc_type: str
    ) -> List[Relation]:
        """
        Extract relations using LLM (Gemini)
        Only use for important documents where regex found nothing
        """
        if not self.use_llm:
            return []
        
        try:
            # Find relation candidates
            candidates = self._find_relation_candidates(text)
            
            if not candidates:
                return []
            
            # Check cache first
            candidates_text = "\\n".join(candidates)
            cache_key_content = f"{doc_id}|{candidates_text}"
            cached_result = self.cache.get(
                content=cache_key_content,
                model="gemini-2.5-flash",
                task_type="relation_extraction"
            )
            
            if cached_result:
                logger.debug(f"Using cached relation extraction for {doc_id}")
                cached_relations = []
                for rel_data in cached_result["response"]:
                    cached_relations.append(Relation(
                        relation_type=rel_data["relation_type"],
                        source_id=rel_data["source_id"],
                        target_ref=rel_data["target_ref"],
                        confidence=rel_data["confidence"],
                        context=rel_data["context"],
                        metadata=rel_data.get("metadata", {})
                    ))
                return cached_relations
            
            # Build prompt
            prompt = self._build_llm_prompt(candidates, doc_type)
            
            # Call LLM
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=genai_new.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            
            # Parse response
            relations = self._parse_llm_response(response.text, doc_id)
            
            # Cache the result
            relations_for_cache = [
                {
                    "relation_type": r.relation_type,
                    "source_id": r.source_id,
                    "target_ref": r.target_ref,
                    "confidence": r.confidence,
                    "context": r.context,
                    "metadata": r.metadata or {}
                }
                for r in relations
            ]
            
            self.cache.set(
                content=cache_key_content,
                response=relations_for_cache,
                model="gemini-2.5-flash",
                task_type="relation_extraction"
            )
            
            return relations
            
        except Exception as e:
            logger.error(f"LLM relation extraction failed: {e}")
            return []
    
    def _find_relation_candidates(self, text: str) -> List[str]:
        """Find text segments likely to contain relations"""
        candidates = []
        
        relation_keywords = [
            'supersedes', 'cancels', 'amends', 'clarifies', 'references',
            'in supersession of', 'in amendment', 'vide', 'G.O.MS', 'G.O.RT'
        ]
        
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            if any(keyword.lower() in sentence.lower() for keyword in relation_keywords):
                candidates.append(sentence.strip())
        
        return candidates[:20]
    
    def _build_llm_prompt(self, candidates: List[str], doc_type: str) -> str:
        """Build prompt for LLM relation extraction (STRICT TYPES ONLY)"""
        candidates_text = "\n\n".join([f"SEGMENT {i+1}:\n{candidate}" for i, candidate in enumerate(candidates)])
        
        prompt = f"""You are an expert in Indian policy document relationships.

Analyze these {doc_type} document segments and extract relationships.

STRICT: Only extract these 5 relation types:
1. SUPERSEDES - This document replaces/cancels another document completely
2. CANCELS - This document cancels another document
3. AMENDS - This document modifies another document
4. CLARIFIES - This document provides clarification without changing
5. REFERENCES - This document cites another document as authority

Document segments:
{candidates_text}

Return ONLY a JSON array in this EXACT format:
[
  {{
    "relation_type": "supersedes",
    "target_go_number": "123",
    "target_year": "2023",
    "raw_text": "G.O.MS.No.123",
    "scope": "document",
    "confidence": 0.95,
    "context": "This order supersedes G.O.MS.No.123"
  }}
]

If NO relations found, return an empty array: []

CRITICAL RULES:
- DO NOT invent document numbers
- DO NOT extract any relation types other than the 5 listed above
- If GO number is not explicit in text, SKIP it
- If unsure, return empty array

JSON only, no explanation:"""
        
        return prompt
    
    def _parse_llm_response(self, response_text: str, doc_id: str) -> List[Relation]:
        """Parse LLM JSON response into Relation objects"""
        try:
            # Clean response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            data = json.loads(response_text)
            
            if not isinstance(data, list):
                logger.error("LLM response is not a list")
                return []
            
            # Convert to Relation objects
            relations = []
            for item in data:
                try:
                    rel_type = item.get('relation_type', '').lower()
                    
                    # Strict type check
                    if rel_type not in self.ALLOWED_RELATION_TYPES:
                        logger.debug(f"Skipping disallowed relation type from LLM: {rel_type}")
                        continue
                    
                    go_number = item.get('target_go_number')
                    raw_text = item.get('raw_text', '')
                    
                    if not go_number and not raw_text:
                        continue
                    
                    target_ref = {
                        "raw_text": raw_text,
                        "go_number": go_number if go_number and str(go_number).isdigit() else None,
                        "year": item.get('target_year'),
                        "resolved_doc_id": None,
                        "resolution_status": "unresolved"
                    }
                    
                    relation = Relation(
                        relation_type=rel_type,
                        source_id=doc_id,
                        target_ref=target_ref,
                        confidence=float(item.get('confidence', 0.8)),
                        context=item.get('context', ''),
                        scope=item.get('scope', 'document')
                    )
                    
                    if target_ref['go_number'] or target_ref['raw_text']:
                        relations.append(relation)
                
                except Exception as e:
                    logger.warning(f"Skipping invalid relation: {e}")
                    continue
            
            return relations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}")
            return []
    
    def relations_to_dict(self, relations: List[Relation]) -> List[Dict]:
        """Convert relations to dictionary format for JSON"""
        return [
            {
                "relation_type": r.relation_type,
                "source_id": r.source_id,
                "target_ref": r.target_ref,
                "confidence": r.confidence,
                "context": r.context,
                "scope": r.scope,
                "source_para": r.source_para,
                "metadata": r.metadata or {}
            }
            for r in relations
        ]