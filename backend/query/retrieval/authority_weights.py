"""
Authority and Binding Strength Weights

Defines legal authority hierarchy for ranking:
- Supreme Court > High Court > Tribunal/Other
- binding > persuasive > non_binding

These weights are FROZEN and should not be tuned without legal review.
"""
from typing import Optional

# ============================================================================
# COURT AUTHORITY WEIGHTS
# ============================================================================
# Higher weight = higher ranking priority
# These weights are applied as multipliers to RRF scores

COURT_WEIGHTS = {
    "Supreme Court": 1.5,      # Highest authority
    "High Court": 1.2,         # High authority
    "Tribunal": 1.0,           # Standard authority
    "Other": 1.0,              # Default for unknown courts
}

# Normalized court name mappings (case-insensitive matching)
COURT_NORMALIZATIONS = {
    "sc": "Supreme Court",
    "supreme court": "Supreme Court",
    "supreme court of india": "Supreme Court",
    "hc": "High Court",
    "high court": "High Court",
    "tribunal": "Tribunal",
}


# ============================================================================
# BINDING STRENGTH WEIGHTS
# ============================================================================
# Applied in combination with court weights

BINDING_STRENGTH_WEIGHTS = {
    "binding": 1.3,            # Binding precedent
    "persuasive": 1.1,         # Persuasive but not binding
    "non_binding": 1.0,        # Non-binding
    None: 1.0,                 # Default for non-judicial documents
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_court_weight(court: Optional[str]) -> float:
    """
    Get authority weight for a court.
    
    Args:
        court: Court name (e.g., "Supreme Court", "High Court")
        
    Returns:
        Weight multiplier (default: 1.0)
    """
    if not court:
        return 1.0
    
    # Normalize court name
    court_normalized = court.strip()
    for key, normalized in COURT_NORMALIZATIONS.items():
        if key.lower() == court_normalized.lower():
            court_normalized = normalized
            break
    
    return COURT_WEIGHTS.get(court_normalized, COURT_WEIGHTS["Other"])


def get_binding_strength_weight(binding_strength: Optional[str]) -> float:
    """
    Get weight for binding strength.
    
    Args:
        binding_strength: Binding strength value (e.g., "binding", "persuasive")
        
    Returns:
        Weight multiplier (default: 1.0)
    """
    if not binding_strength:
        return BINDING_STRENGTH_WEIGHTS[None]
    
    return BINDING_STRENGTH_WEIGHTS.get(
        binding_strength.lower(),
        BINDING_STRENGTH_WEIGHTS[None]
    )


def calculate_authority_multiplier(court: Optional[str], binding_strength: Optional[str]) -> float:
    """
    Calculate combined authority multiplier.
    
    Formula: court_weight * binding_strength_weight
    
    Args:
        court: Court name
        binding_strength: Binding strength value
        
    Returns:
        Combined multiplier (minimum: 1.0)
    """
    court_weight = get_court_weight(court)
    binding_weight = get_binding_strength_weight(binding_strength)
    
    return court_weight * binding_weight

