"""
Legal Status Resolver
=====================
Computes the ground-truth status of a document based on its extracted relations.
Determines if a document is current, its legal weight, and its place in the lineage.
"""

from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class LegalStatusResolver:
    """
    Computes document status and legal truth from relations.
    """
    
    def __init__(self, authority_weights: Dict[str, float]):
        self.authority_weights = authority_weights

    def compute_document_status(self, doc_id: str, doc_type: str, relations: List[Dict]) -> Dict[str, Any]:
        """
        Compute ground-truth status for a document.
        
        Args:
            doc_id: ID of the source document
            doc_type: Type/Category of the source document
            relations: List of extracted relations (resolved preferred)
            
        Returns:
            Dictionary containing legal status metadata
        """
        status = {
            "is_current": True,
            "superseded_by": None,
            "amended_by": [],
            "legal_weight": 1.0,
            "valid_scope": "entire_document",
            "authority_weight": self.authority_weights.get(doc_type, 0.5),
            "legal_lineage": {
                "previous": [],
                "current": doc_id,
                "overridden_by": []
            }
        }
        
        # Adjust legal weight and currency based on relations where THIS doc is the TARGET
        # In a batch process, we might look at incoming relations.
        # But here we look at OUTGOING relations from THIS doc that affect its own status?
        # Typically: status is computed by looking at who SUPERSEDES this doc.
        
        # However, for ingestion of a NEW doc, we often see that it supersedes OLDER docs.
        # That means this NEW doc is likely current.
        
        # If we are re-processing or checking an older doc:
        for rel in relations:
            rel_type = rel.get("relation_type")
            
            # If THIS doc is SUPERSEDED by something else
            # (Note: this requires knowing relations where this doc is the target)
            # For now, let's assume the relation list passed in are those where THIS doc 
            # mentions other docs, OR incoming relations collected by a chain builder.
            
            # If relation says "this doc supersedes X", then this doc is likely the CURRENT one for that family.
            if rel_type == "supersedes":
                target_id = rel.get("target_ref", {}).get("resolved_doc_id")
                if target_id:
                    status["legal_lineage"]["previous"].append(target_id)
            
            # If relation says "this doc amends X", then X is a predecessor
            if rel_type == "amends":
                target_id = rel.get("target_ref", {}).get("resolved_doc_id")
                if target_id:
                    status["legal_lineage"]["previous"].append(target_id)
                    status["valid_scope"] = "partial" # This doc is an amendment
            
            # Judicial Override check
            if rel_type == "governed_by" and "Judgment" in str(rel.get("target_ref", {}).get("raw_text")):
                status["legal_lineage"]["overridden_by"].append(rel.get("target_ref", {}).get("raw_text"))

        return status

    def resolve_conflicting_authority(self, doc_a_type: str, doc_b_type: str) -> str:
        """Determines which document type has higher legal authority"""
        weight_a = self.authority_weights.get(doc_a_type, 0.0)
        weight_b = self.authority_weights.get(doc_b_type, 0.0)
        
        if weight_a > weight_b:
            return "doc_a"
        elif weight_b > weight_a:
            return "doc_b"
        return "equal"
