"""
Metadata Builder
Builds clean, minimal, retrieval-optimized metadata for Qdrant
NO bloat, only what helps retrieval
"""
import re
from typing import Dict, List, Optional
from datetime import datetime
from backend.ingestion.entities.go_role_classifier import classify_go_role, get_role_weight


class MetadataBuilder:
    """
    Builds optimized metadata for vector search
    
    Philosophy:
    - Only include metadata that helps retrieval
    - Keep it flat and simple
    - No nested complexity
    - No processing timestamps (irrelevant for search)
    """
    
    def __init__(self):
        # GO number extraction pattern
        self.go_pattern = re.compile(r'G\.?O\.?(?:MS|RT)?\.?\s*No\.?\s*(\d+)', re.IGNORECASE)
        
        # Year extraction pattern
        self.year_pattern = re.compile(r'\b(19\d{2}|20\d{2})\b')
        
        # Section extraction pattern
        self.section_pattern = re.compile(r'Section\s+(\d+(?:\([a-z]\))?)', re.IGNORECASE)
    
    def build_chunk_metadata(
        self,
        chunk: Dict,
        doc_metadata: Dict,
        entities: Dict,
        relations: List[Dict],
        vertical: str,
        derived_metadata: Optional[Dict] = None,
        legal_status: Optional[Dict] = None,
        policy_domains: Optional[List[str]] = None
    ) -> Dict:
        """
        Build complete metadata for a single chunk
        
        Args:
            chunk: Chunk dictionary
            doc_metadata: Document-level metadata
            entities: Extracted entities
            relations: Extracted relations
            vertical: Document vertical (go, legal, etc.)
            derived_metadata: Optional derived fields (is_superseded, etc.)
            
        Returns:
            Clean metadata dictionary for Qdrant
        """
        content = chunk.get('content', '')
        chunk_id = chunk.get('chunk_id', '')
        doc_id = chunk.get('doc_id', '')
        
        # Start with minimal core metadata
        metadata = {
            # Core identifiers
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "vertical": vertical,
            "doc_type": vertical,  # For backward compatibility
            
            # Position info
            "chunk_position": chunk.get('chunk_index', chunk.get('position', 0)),
            
            # Content stats (helpful for ranking)
            "word_count": chunk.get('word_count', len(content.split())),
            "char_count": len(content)
        }
        
        # Add vertical-specific metadata
        if vertical == "go":
            metadata.update(self._build_go_metadata(content, doc_metadata))
            
            # Add GO-specific legal entities
            go_fields = [
                "go_effect", "legal_effect", "applicability_scope", 
                "beneficiary_scope", "authority_level", "financial_impact",
                "effective_date", "policy_domain", "key_actions",
                # Flattened Geographic Details (Change 16 - User Feedback)
                "districts", "mandals", "villages",
                # Flattened Beneficiary Details
                "beneficiary_orgs", "beneficiary_types", "beneficiary_count",
                # Flattened Financial Details
                "financial_commitment", "financial_amount", "budget_head",
                # Other
                "implementation_timeline", "linked_schemes", "linked_policies",
                "specialized_terms"
            ]
            for field in go_fields:
                if field in entities:
                    val = entities[field]
                    # Persist complex objects (dicts) as is
                    if isinstance(val, dict):
                        metadata[field] = val
                    # Persist lists for specific fields
                    elif isinstance(val, list) and val:
                        # Fields that should remain lists
                        list_fields = [
                            "beneficiary_scope", "linked_schemes", 
                            "linked_policies", "affected_gos"
                        ]
                        if field in list_fields:
                            metadata[field] = val
                        else:
                            # Default to first value for categorical fields
                            metadata[field] = val[0]
                    else:
                        metadata[field] = val
            
            # Add derived metadata if provided
            if derived_metadata:
                metadata["is_superseded"] = "true" if derived_metadata.get("is_superseded", False) else "false"
                metadata["superseded_by"] = derived_metadata.get("superseded_by")
                metadata["is_most_recent"] = "true" if derived_metadata.get("is_most_recent", True) else "false"
            else:
                # Defaults - Ensure strings for Qdrant Keyword indexing
                metadata["is_superseded"] = "false"
                metadata["is_most_recent"] = "true"

        elif vertical == "legal":
            metadata.update(self._build_legal_metadata(content, doc_metadata))
        elif vertical == "judicial":
            metadata.update(self._build_judicial_metadata(content, doc_metadata))
        elif vertical == "data":
            metadata.update(self._build_data_metadata(content, chunk, doc_metadata))
        elif vertical == "scheme":
            metadata.update(self._build_scheme_metadata(content, doc_metadata))
        
        # Add key entities (only if extracted)
        if entities:
            entity_metadata = self._extract_key_entities(entities, content)
            metadata.update(entity_metadata)
        
        # Add relation info (Enhanced for retrieval)
        if relations:
            metadata["has_relations"] = "true"
            metadata["relation_types"] = list(set(r.get("relation_type", "") for r in relations))
            
            # First-class relations for graph search
            # We store them in a simplified list of dicts or flattened targets
            metadata["relations"] = [
                {
                    "type": r.get("relation_type"),
                    "target": r.get("target_go") or r.get("target"),
                    "scope": r.get("scope", "full"),
                    "section": r.get("section")
                }
                for r in relations if r.get("target_go") or r.get("target")
            ]
            
            # Critical for graph-aware reranking and supersession checks
            metadata["related_docs"] = list(set(r.get("target") or r.get("target_go") for r in relations if r.get("target") or r.get("target_go")))[:5]
        else:
            metadata["has_relations"] = False
            metadata["relations"] = []
            
        # Add precomputed legal status if provided
        if legal_status:
            metadata["legal_weight"] = legal_status.get("legal_weight", 1.0)
            metadata["authority_weight"] = legal_status.get("authority_weight", 0.5)
            metadata["is_current"] = legal_status.get("is_current", True)
            
            # Persist lineage if available
            lineage = legal_status.get("legal_lineage", {})
            if lineage:
                 # Flatten lineage for Qdrant compatibility if needed, but dicts are okay for payload
                 metadata["legal_lineage"] = lineage
        else:
            # Defaults
            metadata["legal_weight"] = 1.0
            metadata["is_current"] = True
            
        # Add policy domains for subject-matter scoping (Change 3)
        if policy_domains:
            metadata["policy_domains"] = policy_domains
            metadata["primary_domain"] = policy_domains[0] if policy_domains else "general"
            
        # Override with LLM extraction if available (Change 15 - User Feedback)
        # LLM extraction of 'policy_domain' is much more accurate than keyword matching
        if metadata.get("policy_domain"):
             metadata["primary_domain"] = metadata["policy_domain"]
        
        # Add date-based override flag (Change 2)
        if legal_status:
            metadata["overrides_by_date"] = "true" if legal_status.get("overrides_by_date", False) else "false"
            
        # NEW: Broadly persist all relevant structural metadata from the chunker
        chunk_internal_metadata = chunk.get("metadata", {})
        
        # List of critical fields to carry forward if present
        critical_fields = [
            # GO specific
            "legal_effect", "is_current", "invalidates_prior", "canonical_id", 
            "override_scope", "effective_from", "effective_to",
            "go_role", "role_weight", "resolution_status",
            
            # Judicial specific
            "ratio_confidence", "court_level", "binding_scope",
            
            # Legal specific
            "section_type", "chapter", "part", "structural_confidence",
            "clause_no", "parent_para", "legal_operator", "has_condition",
            
            # Data specific
            "is_garbled", "numeric_confidence", "contains_financials", "data_intent",
            
            # General
            "priority", "anchor_id", "visual_anchor", "is_atomic", "chunk_type"
        ]
        
        for field in critical_fields:
            if field in chunk_internal_metadata:
                metadata[field] = chunk_internal_metadata[field]
        
        # Special case: mapping chunk_type if not already in metadata
        if "chunk_type" in chunk and "chunk_type" not in metadata:
            metadata["chunk_type"] = chunk["chunk_type"]

        return metadata
    
    def _build_go_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build GO-specific metadata - Trusting structured identity over text extraction"""
        metadata = {}
        
        # REQUIRED — Trust parent identity (Defense against referencing other GOs in text)
        metadata["go_number"] = doc_metadata.get("go_number")
        metadata["year"] = doc_metadata.get("year") or doc_metadata.get("go_year")
        metadata["department"] = doc_metadata.get("department") or doc_metadata.get("owning_department")
        metadata["owning_department"] = metadata["department"]
        
        # Extract title/subject from content if not in doc_metadata
        if not doc_metadata.get("subject"):
            subject_match = re.search(r'(?:Sub|Subject|Re):\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            if subject_match:
                metadata["subject"] = subject_match.group(1).strip()
        else:
            metadata["subject"] = doc_metadata.get("subject")
            
        # Fallback only if missing in doc_metadata
        if not metadata["go_number"]:
            go_match = self.go_pattern.search(content)
            if go_match:
                metadata["go_number"] = go_match.group(1)
        
        # REQUIRED — Authority tier
        if "document_authority" in doc_metadata:
            metadata["document_authority"] = doc_metadata["document_authority"]
        else:
            metadata["document_authority"] = "authoritative" # Default
            
        # NEW: GO Role Classification (Ranking Signal)
        go_structure = doc_metadata.get("go_structure", {})
        metadata["go_role"] = classify_go_role(go_structure)
        metadata["role_weight"] = get_role_weight(metadata["go_role"])
        
        # Year enforcement (numerical)
        if metadata.get("year"):
            try:
                metadata["year"] = int(metadata["year"])
            except (ValueError, TypeError):
                year_match = self.year_pattern.search(str(metadata["year"]))
                if year_match:
                    metadata["year"] = int(year_match.group(1))

        return metadata
    
    def _build_legal_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build legal document-specific metadata"""
        metadata = {}
        
        # Extract section numbers
        section_matches = self.section_pattern.findall(content)
        if section_matches:
            # Store first section (primary)
            metadata["section"] = section_matches[0]
            
            # Store all sections if multiple
            if len(section_matches) > 1:
                metadata["sections"] = section_matches[:5]  # Limit to 5
        
        # Extract year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        # Act name (if present in doc metadata)
        if "act_name" in doc_metadata:
            metadata["act_name"] = doc_metadata["act_name"]
        
        return metadata
    
    def _build_judicial_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build judicial document-specific metadata with precedential authority"""
        metadata = {}
        
        # Identity
        metadata["case_number"] = doc_metadata.get("case_number")
        metadata["court"] = doc_metadata.get("court")
        metadata["citation"] = doc_metadata.get("citation")
        
        # REQUIRED — Precedential Authority (Flattened for Qdrant)
        authority = doc_metadata.get("judicial_authority", {})
        if authority:
            metadata["court_level"] = authority.get("court_level")
            metadata["binding_scope"] = authority.get("binding_scope")
            metadata["jurisdiction"] = authority.get("jurisdiction")
            metadata["bench_strength"] = authority.get("bench_strength")
            
        # REQUIRED — Outcome
        outcome = doc_metadata.get("outcome", {})
        if outcome:
            metadata["petition_result"] = outcome.get("petition_result")
            metadata["order_type"] = outcome.get("order_type")
        
        # Year
        year_val = doc_metadata.get("year")
        if year_val:
            try:
                metadata["year"] = int(year_val)
            except:
                pass
        
        if not metadata.get("year"):
            year_match = self.year_pattern.search(content)
            if year_match:
                metadata["year"] = int(year_match.group(1))
        
        return metadata
    
    def _build_data_metadata(self, content: str, chunk: Dict, doc_metadata: Dict) -> Dict:
        """Build data document-specific metadata with intent and numeric confidence"""
        metadata = {}
        
        # Identity
        metadata["report_type"] = doc_metadata.get("report_type")
        metadata["department"] = doc_metadata.get("department")
        
        # REQUIRED — Intent & Temporal Scope
        metadata["data_intent"] = doc_metadata.get("data_intent", "informational")
        
        temporal = doc_metadata.get("temporal_scope", {})
        if temporal:
            metadata["financial_year"] = temporal.get("financial_year")
            metadata["applicable_period"] = temporal.get("applicable_period")
            metadata["is_historical"] = temporal.get("is_historical", False)
            
        # REQUIRED — Numeric Confidence
        numeric = doc_metadata.get("numeric_metadata", {})
        if numeric:
            metadata["contains_financials"] = numeric.get("contains_financials", False)
            metadata["numeric_confidence"] = numeric.get("numeric_confidence", "high")

        # Table Support
        metadata["is_table"] = False
        metadata["has_table"] = False
        
        chunk_metadata = chunk.get("metadata", {})
        if chunk.get("chunk_type") == "table" or chunk_metadata.get("is_table", False) or chunk_metadata.get("has_table", False):
            metadata["is_table"] = "true"
            metadata["has_table"] = "true"
            
            # Table-specific metadata
            for field in ["table_name", "table_number", "table_title", "table_source", "row_count"]:
                if field in chunk_metadata:
                    metadata[field] = chunk_metadata[field]
            
            if "headers" in chunk_metadata and chunk_metadata["headers"]:
                metadata["columns"] = chunk_metadata["headers"][:10]
                metadata["column_count"] = len(chunk_metadata["headers"])
        
        return metadata
    
    def _build_scheme_metadata(self, content: str, doc_metadata: Dict) -> Dict:
        """Build scheme document-specific metadata"""
        metadata = {}
        
        # Scheme name (from doc metadata or content)
        if "scheme_name" in doc_metadata:
            metadata["scheme_name"] = doc_metadata["scheme_name"]
        else:
            # Try to extract scheme name from content
            scheme_match = re.search(r'(Jagananna\s+[A-Za-z\s]+)', content, re.IGNORECASE)
            if scheme_match:
                metadata["scheme_name"] = scheme_match.group(1).strip()
        
        # Year
        year_match = self.year_pattern.search(content)
        if year_match:
            metadata["year"] = int(year_match.group(1))
        
        return metadata
    
    def _extract_key_entities(self, entities: Dict, content: str) -> Dict:
        """
        Extract key entities for metadata
        Only include entities that are ACTUALLY in this chunk
        """
        metadata = {}
        
        # GO numbers
        if "go_numbers" in entities and entities["go_numbers"]:
            # Filter to only GOs mentioned in this chunk
            chunk_gos = [go for go in entities["go_numbers"] if go in content]
            if chunk_gos:
                metadata["mentioned_gos"] = chunk_gos[:3]  # Limit to 3
        
        # Sections
        if "sections" in entities and entities["sections"]:
            chunk_sections = [sec for sec in entities["sections"] if sec in content]
            if chunk_sections:
                metadata["mentioned_sections"] = chunk_sections[:3]
        
        # Departments
        if "departments" in entities and entities["departments"]:
            chunk_depts = [dept for dept in entities["departments"] if dept.lower() in content.lower()]
            if chunk_depts:
                metadata["departments"] = chunk_depts[:2]
        
        # Schemes
        if "schemes" in entities and entities["schemes"]:
            chunk_schemes = [scheme for scheme in entities["schemes"] if scheme.lower() in content.lower()]
            if chunk_schemes:
                metadata["schemes"] = chunk_schemes[:2]
        
        return metadata
    
    def build_document_metadata(
        self,
        doc_id: str,
        file_path: str,
        vertical: str,
        entities: Dict,
        relations: List[Dict],
        chunks_count: int
    ) -> Dict:
        """
        Build document-level metadata (for manifest/summary)
        
        Args:
            doc_id: Document ID
            file_path: Path to source file
            vertical: Document vertical
            entities: All extracted entities
            relations: All extracted relations
            chunks_count: Number of chunks created
            
        Returns:
            Document metadata dictionary
        """
        metadata = {
            "doc_id": doc_id,
            "file_path": file_path,
            "vertical": vertical,
            "chunks_count": chunks_count,
            "processed_at": datetime.utcnow().isoformat(),
            
            # Entity counts
            "entity_counts": {
                entity_type: len(entity_list) if isinstance(entity_list, list) else 0
                for entity_type, entity_list in entities.items()
            },
            
            # Relation counts
            "relations_count": len(relations),
            "relation_types": list(set(r.get("relation_type", "") for r in relations)) if relations else [],
            
            # Legal status (Document level)
            "legal_weight": 1.0,  # Default
            "authority_weight": 0.5, # Default
            "is_current": "true",
            "overrides_by_date": "false"
        }

        # Enrich with high-value fields from entities
        # Prioritize 'policy_domain' (singular, from LLM) over 'policy_domains' (plural, from keyword scanner)
        policy_domain_llm = entities.get("policy_domain", [])
        policy_domain_kw = entities.get("policy_domains", [])
        
        # Merge or prioritize
        final_domains = policy_domain_llm if policy_domain_llm else policy_domain_kw
        
        metadata["primary_domain"] = final_domains[0] if final_domains else "general"
        metadata["policy_domains"] = final_domains
        metadata["specialized_terms"] = entities.get("specialized_terms", [])
        metadata["key_actions"] = entities.get("key_actions", [])
        
        return metadata