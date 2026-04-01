"""
Relation Rules and Patterns
Centralized rules for relation extraction
"""
from typing import Dict, List, Set

# ==================================================
# RELATION TYPES
# ==================================================

RELATION_TYPES = {
    "supersedes": {
        "description": "This document replaces/cancels another",
        "keywords": ["supersedes", "supersession", "rescinded", "cancelled", "revoked", "replaced"],
        "confidence_base": 0.95
    },
    "amends": {
        "description": "This document modifies another",
        "keywords": ["amends", "amendment", "modified", "revised"],
        "confidence_base": 0.90
    },
    "cites": {
        "description": "This document references another as authority",
        "keywords": ["as per", "under", "in accordance with", "in terms of", "vide"],
        "confidence_base": 0.85
    },
    "implements": {
        "description": "This document implements a law/policy/scheme",
        "keywords": ["implementation", "implementing", "gives effect to"],
        "confidence_base": 0.80
    },
    "governed_by": {
        "description": "This document is governed by a law/act",
        "keywords": ["governed by", "under the provisions of", "as per act"],
        "confidence_base": 0.80
    },
    "clarifies": {
        "description": "This document provides clarification without overriding",
        "keywords": ["clarifies", "clarification", "clarified", "explanation"],
        "confidence_base": 0.90
    },
    "reiterates": {
        "description": "This document repeats existing instructions for emphasis",
        "keywords": ["reiterates", "revisited", "reaffirmed", "once again ordered"],
        "confidence_base": 0.85
    },
    "financial_sanctioned_by": {
        "description": "Indicates budget approval for an action",
        "keywords": ["sanctioned by finance", "budgetized", "financial concurrence"],
        "confidence_base": 0.90
    },
    "implemented_by_department": {
        "description": "Operational link to executing agency",
        "keywords": ["implemented by", "executed by", "nodal agency"],
        "confidence_base": 0.85
    }
}

# ==================================================
# AUTHORITY HIERARCHY
# ==================================================

AUTHORITY_WEIGHTS = {
    "judicial_supreme": 1.0,
    "judicial_high": 0.9,
    "act": 0.85,
    "rules": 0.8,
    "go": 0.7,
    "circular": 0.5,
    "memo": 0.4
}

# ==================================================
# DOCUMENT IDENTIFIER PATTERNS
# ==================================================

DOCUMENT_ID_FORMATS = {
    "GO": [
        "G.O.MS.No.{num}",
        "G.O.RT.No.{num}",
        "GO.MS.No.{num}",
        "GO.RT.No.{num}",
        "G.O.No.{num}"
    ],
    "Section": [
        "Section {num}",
        "Sec. {num}",
        "§ {num}"
    ],
    "Rule": [
        "Rule {num}",
        "R. {num}"
    ],
    "Act": [
        "{name} Act",
        "{name} Act, {year}"
    ]
}

# ==================================================
# VALIDATION RULES
# ==================================================

def validate_relation(relation_type: str, target: str) -> bool:
    """
    Validate if a relation makes sense
    
    Args:
        relation_type: Type of relation
        target: Target document identifier
        
    Returns:
        True if valid, False otherwise
    """
    # Basic checks
    if not relation_type or not target:
        return False
    
    if relation_type not in RELATION_TYPES:
        return False
    
    # Check target format
    target = target.strip()
    if len(target) < 3:
        return False
    
    # Relation-specific validation
    if relation_type == "supersedes":
        # Supersedes should reference GO numbers
        return "G.O" in target or "GO" in target or target.isdigit()
    
    elif relation_type == "amends":
        # Amends can reference GOs or Sections
        return any(keyword in target for keyword in ["G.O", "GO", "Section", "Rule"])
    
    elif relation_type == "cites":
        # Cites usually references sections or GOs
        return True  # Accept all
    
    elif relation_type in ("implements", "governed_by"):
        # Should reference Acts, Schemes, or Policies
        return any(keyword in target for keyword in ["Act", "Rule", "Policy", "Scheme"]) or len(target) > 10
    
    return True


def normalize_target(target: str) -> str:
    """
    Normalize target identifier
    
    Args:
        target: Raw target identifier
        
    Returns:
        Normalized target
    """
    target = target.strip()
    
    # Remove extra whitespace
    target = " ".join(target.split())
    
    # Standardize GO format
    if "GO" in target.upper() and not "G.O" in target:
        target = target.replace("GO", "G.O.")
    
    # Capitalize Act/Rule
    if "act" in target.lower():
        target = target.replace("act", "Act").replace(" Act Act", " Act")
    
    if "rule" in target.lower():
        target = target.replace("rule", "Rule").replace(" Rule Rule", " Rule")
    
    return target


def get_relation_priority(relation_type: str) -> int:
    """
    Get priority for relation type (for deduplication)
    Higher number = higher priority
    
    Args:
        relation_type: Type of relation
        
    Returns:
        Priority score
    """
    priorities = {
        "supersedes": 5,
        "amends": 4,
        "implements": 3,
        "governed_by": 2,
        "cites": 1
    }
    
    return priorities.get(relation_type, 0)


def should_extract_relations(doc_type: str, text_length: int) -> bool:
    """
    Determine if we should extract relations from this document
    
    Args:
        doc_type: Document type (go, legal, judicial, data, scheme)
        text_length: Length of document text
        
    Returns:
        True if should extract relations
    """
    # Only extract for important document types
    if doc_type not in ('go', 'legal', 'judicial'):
        return False
    
    # Only if document is substantial
    if text_length < 500:
        return False
    
    return True


def get_llm_verticals() -> Set[str]:
    """
    Get verticals where LLM extraction is enabled
    
    Returns:
        Set of vertical names
    """
    return {'go', 'legal', 'judicial'}