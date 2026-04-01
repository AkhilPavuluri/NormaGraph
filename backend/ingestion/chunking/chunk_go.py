"""
GO Chunker - Legal Grade Implementation
Enforces atomic paragraph chunking based on strict GOStructureParser output.
"""
from typing import List, Dict, Any
from .base_chunker import BaseChunker, Chunk

class GOChunker(BaseChunker):
    """
    Government Order specific chunker
    Strictly follows the 'one-para-one-chunk' rule using pre-parsed structure.
    """
    
    def __init__(self):
        # We don't rely on size-based splitting for legal paras, 
        # but keep defaults for fallback protection
        super().__init__(min_size=100, max_size=4000, overlap=0)
    
    def chunk(self, text: str, doc_id: str, metadata: Dict) -> List[Chunk]:
        """
        Chunk GO document using strictly parsed structure.
        
        Args:
            text: Full document text
            doc_id: Retrieval document ID
            metadata: Metadata dict containing 'go_structure'
            
        Raises:
            ValueError: If 'go_structure' is missing (Enforced Invariant)
        """
        go_structure = metadata.get("go_structure")
        
        if not go_structure:
            # STRICT INVARIANT: No structure = No ingestion
            raise ValueError(f"GO Structure missing for {doc_id}. All GOs must be structurally parsed before chunking.")
            
        chunks = []
        identity = go_structure.get("identity", {})
        doc_authority = identity.get("document_authority", "authoritative")
        
        # 1. Preamble Chunk (Low Priority)
        preamble = go_structure.get("preamble")
        if preamble and preamble.get("text"):
            chunks.append(self._create_preamble_chunk(
                preamble, doc_id, identity, metadata
            ))
            
        # 2. Order Chunks (Atomic & Authoritative)
        orders = go_structure.get("orders", [])
        # 2. Order Chunks (Atomic & Authoritative)
        orders = go_structure.get("orders", [])
        for i, order in enumerate(orders):
            # NEW: Clause-Level Chunking
            if order.get("clauses"):
                for clause in order["clauses"]:
                    chunks.append(self._create_clause_chunk(
                        clause, order, doc_id, i, identity, metadata
                    ))
            else:
                # Fallback to paragraph chunking
                chunks.append(self._create_order_chunk(
                    order, doc_id, i, identity, metadata
                ))
            
        # 3. Annexure Chunks (Supporting)
        annexures = go_structure.get("annexures", [])
        for i, annex in enumerate(annexures):
            chunks.append(self._create_annexure_chunk(
                annex, doc_id, i, identity, metadata
            ))
            
        return chunks

    def _create_clause_chunk(self, clause: Dict, order: Dict, doc_id: str, index: int, identity: Dict, base_metadata: Dict) -> Chunk:
        """Create atomic chunk for a single legal clause"""
        # Format: AP_GO_83_2008_P4(I)
        go_num = identity.get("go_number", "UNK")
        year = identity.get("year", "UNK")
        para_no = order.get("para_no", f"SEQ_{index}")
        clause_id = clause.get("clause_id", "main")
        
        # ID is already shaped like "4(I)" in structure parser
        canonical_id = f"AP_GO_{go_num}_{year}_P{clause_id}"

        chunk_metadata = {
            **base_metadata,
            "section_type": "order_clause",
            "priority": "high",
            "is_atomic": True,
            
            # Identity
            "go_number": go_num,
            "year": year,
            "department": identity.get("department"),
            
            # Canonical Anchors
            "para_no": para_no,
            "clause_no": clause_id,
            "canonical_id": canonical_id,
            "parent_para": f"AP_GO_{go_num}_{year}_P{para_no}",
            
            # Legal Semantics (Inherited + Clause Specific)
            "legal_effect": order.get("legal_effect"), # Inherit effect
            "legal_operator": clause.get("legal_operator"),
            "has_condition": clause.get("has_condition"),
            
            "effective_from": order.get("effective_from"),
            "is_current": order.get("is_current", True),
            
            # Visuals
            "visual_anchor": order.get("visual_anchor") # Fallback to para anchor
        }
        
        if "go_structure" in chunk_metadata:
            del chunk_metadata["go_structure"]
            
        return self._create_chunk(
            clause["text"],
            doc_id,
            index + 1,
            chunk_metadata
        )

    def _create_preamble_chunk(self, preamble: Dict, doc_id: str, identity: Dict, base_metadata: Dict) -> Chunk:
        """Create a single chunk for the preamble"""
        chunk_metadata = {
            **base_metadata,
            "section_type": "preamble",
            "priority": "low",
            "document_authority": identity.get("document_authority"),
            "visual_anchor": preamble.get("visual_anchor")
            # Preamble useful for context but not binding rules
        }
        
        return self._create_chunk(
            preamble["text"],
            doc_id,
            0, # Index 0 usually
            chunk_metadata
        )

    def _create_order_chunk(self, order: Dict, doc_id: str, index: int, identity: Dict, base_metadata: Dict) -> Chunk:
        """Create an atomic chunk for a single order paragraph"""
        
        # Construct Canonical ID
        # Format: AP_GO_83_2008_P4
        go_num = identity.get("go_number", "UNK")
        year = identity.get("year", "UNK")
        para_no = order.get("para_no", f"SEQ_{index}")
        
        canonical_id = f"AP_GO_{go_num}_{year}_P{para_no}"
        
        # Metadata Map (Flattening for retrieval)
        chunk_metadata = {
            **base_metadata,
            "section_type": "order",
            "priority": "high",
            "is_atomic": True,
            
            # Identity
            "go_number": go_num,
            "year": year,
            "department": identity.get("department"),
            
            # Canonical Anchors
            "para_no": para_no,
            "canonical_id": canonical_id,
            
            # Authority & Quality
            "document_authority": identity.get("document_authority"),
            "structural_confidence": order.get("structural_confidence"),
            
            # Legal Semantics
            "legal_effect": order.get("legal_effect"),
            "override_scope": order.get("override_scope"),
            "invalidates_prior": order.get("invalidates_prior"),
            "effective_from": order.get("effective_from"),
            "is_current": order.get("is_current", True),
            
            # Visuals
            "visual_anchor": order.get("visual_anchor")
        }
        
        # Remove bulky structure to save space
        if "go_structure" in chunk_metadata:
            del chunk_metadata["go_structure"]

        return self._create_chunk(
            order["text"],
            doc_id,
            index + 1, # Offset after preamble
            chunk_metadata
        )

    def _create_annexure_chunk(self, annex: Dict, doc_id: str, index: int, identity: Dict, base_metadata: Dict) -> Chunk:
        """Create chunk for annexure"""
        chunk_metadata = {
            **base_metadata,
            "section_type": "annexure",
            "priority": "supporting",
            "annexure_id": annex.get("annexure_id"),
            "linked_para": annex.get("linked_para"),
            "document_authority": identity.get("document_authority"),
            "visual_anchor": annex.get("visual_anchor")
        }
        
        if "go_structure" in chunk_metadata:
            del chunk_metadata["go_structure"]
            
        return self._create_chunk(
            annex["text"],
            doc_id,
            1000 + index, # distinctive index range
            chunk_metadata
        )