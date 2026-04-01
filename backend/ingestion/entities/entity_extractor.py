"""
Entity Extractor
Smart entity extraction: regex for simple, LLM for complex, GO-specific for legal
"""
import logging
import re
import json
from typing import Dict, List, Optional, Tuple
from .patterns import EntityPatterns

logger = logging.getLogger(__name__)


class DepartmentSanitizer:
    """
    Deterministic department name sanitizer
    Removes signature blocks, distribution lists, and invalid department names
    """
    
    # Patterns to identify invalid departments
    INVALID_PATTERNS = [
        r'SECRETARY TO GOVERNMENT',
        r'To\n',
        r'\n\n+',  # Excessive newlines
        r'Copy to',
        r'Forwarded',
        r'/Sd/-',
        r'\(Sd\)',
        r'Date:',
        r'From:',
        r'Subject:',
    ]
    
    def sanitize(self, departments: List[str]) -> List[str]:
        """
        Sanitize department names
        
        Args:
            departments: Raw department strings
            
        Returns:
            Cleaned department strings
        """
        clean_depts = []
        
        for dept in departments:
            if not isinstance(dept, str):
                continue
            
            dept = dept.strip()
            
            # Skip empty
            if not dept:
                continue
            
            # Check against invalid patterns
            is_invalid = False
            for pattern in self.INVALID_PATTERNS:
                if re.search(pattern, dept, re.IGNORECASE):
                    is_invalid = True
                    break
            
            if is_invalid:
                logger.debug(f"Dropped invalid department: {dept[:50]}")
                continue
            
            # Skip if too short (likely fragment)
            if len(dept) < 5:
                continue
            
            # Skip if contains suspicious characters
            if dept.count('\n') > 2:
                continue
            
            # Clean up whitespace
            dept = re.sub(r'\s+', ' ', dept)
            dept = dept.strip()
            
            clean_depts.append(dept)
        
        logger.info(f"Department sanitization: {len(departments)} -> {len(clean_depts)}")
        return clean_depts


class OutputValidator:
    """
    Validates entity extraction output against strict contract
    """
    
    # Forbidden fields that must never appear
    FORBIDDEN_FIELDS = {
        "go_effect", "legal_effect", "authority_level",
        "applicability_scope", "years", "effective_until"
    }
    
    # Required archetype values
    VALID_ARCHETYPES = {"normative", "administrative", "financial", "procedural"}
    
    # Valid date roles
    VALID_DATE_ROLES = {"issue_date", "effective_from", "retrospective_from", "reference_date"}
    
    def validate(self, entities: Dict[str, List]) -> None:
        """
        Validate entities against output contract
        Raises AssertionError if contract violated
        
        Args:
            entities: Entity dictionary to validate
        """
        # 1. Check for forbidden fields
        forbidden_found = set(entities.keys()) & self.FORBIDDEN_FIELDS
        assert not forbidden_found, f"FORBIDDEN FIELDS IN OUTPUT: {forbidden_found}"
        
        # 2. Validate go_archetype if present
        if "go_archetype" in entities:
            assert isinstance(entities["go_archetype"], str), \
                f"go_archetype must be STRING, got {type(entities['go_archetype'])}"
            assert entities["go_archetype"] in self.VALID_ARCHETYPES, \
                f"Invalid go_archetype: {entities['go_archetype']}"
        
        # 3. Validate dates are structured only
        if "dates" in entities:
            assert isinstance(entities["dates"], list), "dates must be a list"
            for date_item in entities["dates"]:
                assert isinstance(date_item, dict), \
                    f"Date must be dict, got: {type(date_item)}"
                assert "value" in date_item and "role" in date_item, \
                    f"Date missing required fields: {date_item}"
                assert re.match(r'^\d{4}-\d{2}-\d{2}$', date_item["value"]), \
                    f"Date not in YYYY-MM-DD format: {date_item['value']}"
                assert date_item["role"] in self.VALID_DATE_ROLES, \
                    f"Invalid date role: {date_item['role']}"
        
        # 4. Validate departments are sanitized (no forbidden patterns)
        if "departments" in entities:
            for dept in entities["departments"]:
                assert not re.search(r'SECRETARY TO GOVERNMENT', dept, re.IGNORECASE), \
                    f"Unsanitized department: {dept}"
                assert not re.search(r'To\n', dept), \
                    f"Unsanitized department: {dept}"
        
        # 5. Validate acts are normalized
        if "acts" in entities:
            for act in entities["acts"]:
                assert isinstance(act, dict), \
                    f"Act must be dict, got: {type(act)}"
                assert "act_name" in act and "act_year" in act, \
                    f"Act missing required fields: {act}"
        
        logger.info("✅ Output validation passed")


class EntityExtractor:
    """
    Smart entity extractor
    - Fast regex extraction for all documents
    - Optional LLM enhancement for important documents
    - Strict output validation
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_enabled_verticals: Optional[set] = None
    ):
        """
        Initialize entity extractor
        
        Args:
            use_llm: Whether to use LLM enhancement
            llm_enabled_verticals: Verticals where LLM is enabled
        """
        self.use_llm = use_llm
        self.llm_enabled_verticals = llm_enabled_verticals or {"go", "legal", "judicial"}
        
        # Initialize pattern matcher
        self.patterns = EntityPatterns()
        
        # Initialize sanitizer and validator
        self.dept_sanitizer = DepartmentSanitizer()
        self.validator = OutputValidator()
        
        # LLM extractor (lazy load)
        self._llm_extractor = None
        
        # GO-specific extractors (lazy load)
        self._go_logic_extractor = None
        self._go_relation_extractor = None
        
        logger.info(f"Entity extractor initialized - LLM: {use_llm}")
    
    def extract(
        self, 
        text: str, 
        vertical: str,
        doc_id: str = ""
    ) -> Tuple[Dict[str, List], List[Dict]]:
        """
        Extract entities and relations from text
        
        Args:
            text: Text to extract from
            vertical: Document vertical
            doc_id: Document ID
            
        Returns:
            Tuple of (entities, relations)
            - entities: Dictionary of entity types and values
            - relations: List of relation dictionaries (for GO vertical)
        """
        if not text or not text.strip():
            return {}, []
        
        # Always do regex extraction (fast and reliable)
        entities = self.patterns.extract_all(text)
        relations = []
        
        # GO-specific extraction
        if vertical == "go":
            # Extract GO logic entities
            go_logic_entities = self._extract_go_logic(text)
            entities = self._merge_entities(entities, go_logic_entities)
            
            # Extract GO relations (RELATIONS TEAM HANDLES THIS)
            relations = self._extract_go_relations(text, doc_id)
            
            # Optionally enhance with LLM for legal context
            if self.use_llm and len(text) > 500:
                llm_context = self._extract_go_llm_context(text, doc_id)
                entities = self._merge_entities(entities, llm_context)
        
        # Non-GO verticals: use LLM enhancement if enabled
        elif self.use_llm and vertical in self.llm_enabled_verticals:
            if len(text) > 500:  # Only for substantial documents
                llm_entities = self._extract_with_llm(text, vertical, doc_id)
                entities = self._merge_entities(entities, llm_entities)
        
        # Clean up entities (includes department sanitization and Act normalization)
        logger.debug(f"Entities before clean for {doc_id}: {list(entities.keys())}")
        entities = self._clean_entities(entities)
        logger.debug(f"Entities after clean for {doc_id}: {list(entities.keys())}")
        
        # Validate output contract
        try:
            self.validator.validate(entities)
        except AssertionError as e:
            logger.error(f"OUTPUT CONTRACT VIOLATION for {doc_id}: {e}")
            raise
        
        return entities, relations
    
    def _extract_go_logic(self, text: str) -> Dict[str, List[str]]:
        """
        Extract GO logic entities using deterministic rules
        """
        if self._go_logic_extractor is None:
            try:
                from .go_logic_extractor import GOLogicExtractor
                self._go_logic_extractor = GOLogicExtractor()
            except Exception as e:
                logger.error(f"Failed to load GO logic extractor: {e}")
                return {}
        
        try:
            return self._go_logic_extractor.extract(text)
        except Exception as e:
            logger.error(f"GO logic extraction failed: {e}")
            return {}
    
    def _extract_go_relations(self, text: str, doc_id: str) -> List[Dict]:
        """
        Extract GO relations using deterministic rules
        NOTE: Relations are handled by relations team, not entity team
        """
        if self._go_relation_extractor is None:
            try:
                from .go_relation_extractor import GORelationExtractor
                self._go_relation_extractor = GORelationExtractor()
            except Exception as e:
                logger.error(f"Failed to load GO relation extractor: {e}")
                return []
        
        try:
            # Extract source GO number from doc_id if available
            source_go = self._extract_source_go_from_doc_id(doc_id)
            return self._go_relation_extractor.extract(text, source_go)
        except Exception as e:
            logger.error(f"GO relation extraction failed: {e}")
            return []
    
    def _extract_go_llm_context(self, text: str, doc_id: str) -> Dict[str, List[str]]:
        """
        Extract GO legal context using LLM
        """
        if self._llm_extractor is None:
            try:
                from .llm_entity_extraction import LLMEntityExtractor
                self._llm_extractor = LLMEntityExtractor()
            except Exception as e:
                logger.error(f"Failed to load LLM extractor: {e}")
                return {}
        
        try:
            return self._llm_extractor.extract_go_legal_context(text, doc_id)
        except Exception as e:
            logger.error(f"LLM GO context extraction failed: {e}")
            return {}
    
    def _extract_source_go_from_doc_id(self, doc_id: str) -> str:
        """
        Extract GO number from doc_id
        Example: "2023se_ms45" -> "G.O.MS.No.45"
        """
        match = re.search(r'(?:ms|rt)(\d+)', doc_id, re.IGNORECASE)
        if match:
            return f"G.O.MS.No.{match.group(1)}"
        return ""
    
    def _extract_with_llm(
        self, 
        text: str, 
        vertical: str,
        doc_id: str
    ) -> Dict[str, List[str]]:
        """
        Extract entities using LLM
        This is expensive - only call for important documents
        """
        if self._llm_extractor is None:
            # Lazy load LLM extractor
            try:
                from .llm_entity_extraction import LLMEntityExtractor
                self._llm_extractor = LLMEntityExtractor()
            except Exception as e:
                logger.error(f"Failed to load LLM extractor: {e}")
                return {}
        
        try:
            return self._llm_extractor.extract(text, vertical, doc_id)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {}
    
    def _merge_entities(
        self, 
        regex_entities: Dict[str, List], 
        llm_entities: Dict[str, List]
    ) -> Dict[str, List]:
        """
        Merge regex and LLM entities (LLM adds, doesn't replace)
        
        Special handling:
        - For go_archetype: LLM value takes precedence (must be string)
        - For structured fields: smart merge with deduplication
        """
        merged = regex_entities.copy()
        
        for entity_type, values in llm_entities.items():
            # Special case: go_archetype is a string, not a list
            if entity_type == "go_archetype":
                if isinstance(values, str):
                    merged[entity_type] = values
                elif isinstance(values, list) and values:
                    merged[entity_type] = values[0]  # Take first if mistakenly list
                else:
                    logger.warning(f"Invalid go_archetype value: {values}")
                continue
            
            # For all other types, merge as lists
            if entity_type in merged:
                # Handle both string and dict values
                existing_values = merged[entity_type]
                
                # Check if values are dicts (e.g., structured dates)
                if values and isinstance(values[0], dict):
                    # For dicts, use JSON serialization for comparison
                    existing_strs = {
                        json.dumps(v, sort_keys=True) if isinstance(v, dict) else str(v) 
                        for v in existing_values
                    }
                    for value in values:
                        value_str = json.dumps(value, sort_keys=True) if isinstance(value, dict) else str(value)
                        if value_str not in existing_strs:
                            merged[entity_type].append(value)
                            existing_strs.add(value_str)
                else:
                    # For strings, use set as before
                    existing = set(str(v) for v in existing_values)
                    for value in values:
                        if str(value) not in existing:
                            merged[entity_type].append(value)
            else:
                merged[entity_type] = values
        
        return merged
    
    def _clean_entities(self, entities: Dict[str, List]) -> Dict[str, List]:
        """
        Clean up extracted entities
        
        Cleaning steps:
        1. Remove forbidden fields
        2. Remove duplicates
        3. Drop raw date strings (keep only structured dates)
        4. Sanitize departments
        5. Normalize acts
        6. Ensure go_archetype is string
        """
        cleaned = {}
        
        # 1. Remove forbidden fields
        forbidden_fields = {
            "go_effect", "legal_effect", "authority_level",
            "applicability_scope", "years", "effective_until"
        }
        
        for entity_type, values in entities.items():
            # Skip forbidden fields
            if entity_type in forbidden_fields:
                logger.warning(f"Dropping forbidden field: {entity_type}")
                continue
            
            # Special handling for go_archetype (must be string)
            if entity_type == "go_archetype":
                if isinstance(values, str):
                    cleaned[entity_type] = values
                elif isinstance(values, list) and values:
                    cleaned[entity_type] = values[0]  # Convert to string
                else:
                    logger.warning(f"Invalid go_archetype: {values}")
                continue
            
            # 2. Remove duplicates while preserving order
            seen = set()
            unique_values = []
            for value in values:
                if not value:
                    continue
                
                # Handle dict values (e.g., structured dates)
                if isinstance(value, dict):
                    value_key = json.dumps(value, sort_keys=True)
                else:
                    value_key = str(value)
                
                if value_key not in seen:
                    # Special handling for dates to ensure they follow the structured contract
                    if entity_type == "dates":
                        if isinstance(value, dict) and "value" in value and "role" in value:
                            unique_values.append(value)
                            seen.add(value_key)
                        elif isinstance(value, str):
                            # Try to convert raw string to structured format
                            structured = self._auto_structure_date(value)
                            if structured:
                                # Only add if we don't already have this date value with a more specific role
                                date_val = structured["value"]
                                if not any(v.get("value") == date_val for v in unique_values if isinstance(v, dict)):
                                    unique_values.append(structured)
                                    seen.add(value_key)
                    else:
                        seen.add(value_key)
                        unique_values.append(value)
            
            # 4. Apply entity-specific cleanup
            if entity_type == "departments" and unique_values:
                unique_values = self.dept_sanitizer.sanitize(unique_values)
            elif entity_type == "acts" and unique_values:
                unique_values = self._normalize_acts(unique_values)
            
            # Only include if has values
            if unique_values:
                cleaned[entity_type] = unique_values
        
        return cleaned
    
    def _normalize_acts(self, acts: List) -> List[Dict]:
        """
        Normalize Acts into {act_name, act_year} structure
        
        Args:
            acts: Raw act strings or dicts
            
        Returns:
            List of normalized act dicts
        """
        normalized = []
        seen = set()
        
        for act in acts:
            # Skip if already normalized
            if isinstance(act, dict) and "act_name" in act:
                act_key = json.dumps(act, sort_keys=True)
                if act_key not in seen:
                    normalized.append(act)
                    seen.add(act_key)
                continue
            
            if not isinstance(act, str):
                continue
            
            # Extract year from act string
            year_match = re.search(r'\b(19|20)\d{2}\b', act)
            year = year_match.group(0) if year_match else None
            
            # Clean act name (remove year, commas, extra spaces)
            act_name = re.sub(r',?\s*(19|20)\d{2}', '', act)
            act_name = act_name.strip().strip(',')
            
            # Skip if empty after cleaning
            if not act_name:
                continue
            
            act_dict = {
                "act_name": act_name,
                "act_year": year
            }
            
            act_key = json.dumps(act_dict, sort_keys=True)
            if act_key not in seen:
                normalized.append(act_dict)
                seen.add(act_key)
        
        return normalized
    
    def _auto_structure_date(self, date_str: str) -> Optional[Dict]:
        """
        Attempt to convert a raw date string to structured {value, role} format
        Returns None if format is unrecognized
        """
        if not date_str:
            return None
        
        # Clean string
        date_str = date_str.strip()
        
        # 1. Try to extract YYYY-MM-DD directly
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match:
            return {"value": match.group(0), "role": "reference_date"}
            
        # 2. Try common Indian format DD.MM.YYYY or DD-MM-YYYY
        match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{4})', date_str)
        if match:
            day, month, year = match.groups()
            try:
                # Format to YYYY-MM-DD
                val = f"{year}-{int(month):02d}-{int(day):02d}"
                return {"value": val, "role": "reference_date"}
            except (ValueError, TypeError):
                pass
                
        return None

    def extract_from_chunks(self, chunks: List[Dict], vertical: str) -> List[Dict]:
        """
        Extract entities and relations from chunks
        
        Args:
            chunks: List of chunk dicts
            vertical: Document vertical
            
        Returns:
            Chunks with entities and relations added
        """
        for chunk in chunks:
            content = chunk.get("content", "")
            doc_id = chunk.get("doc_id", "")
            
            if content:
                try:
                    entities, relations = self.extract(content, vertical, doc_id)
                    chunk["entities"] = entities
                    
                    # Add relations for GO vertical (handled by relations team)
                    if vertical == "go" and relations:
                        chunk["relations"] = relations
                except Exception as e:
                    logger.error(f"Entity extraction failed for chunk in {doc_id}: {e}")
                    chunk["entities"] = {}
                    if vertical == "go":
                        chunk["relations"] = []
        
        return chunks


def create_department_sanitizer() -> DepartmentSanitizer:
    """Factory function to create department sanitizer"""
    return DepartmentSanitizer()