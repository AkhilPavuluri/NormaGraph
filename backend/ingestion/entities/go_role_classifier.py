"""
GO Role Classifier
Classifies Government Orders into functional roles for ranking
"""
from typing import Dict, Optional

def classify_go_role(go_structure: Dict) -> str:
    """
    Classify the functional role of a GO.
    
    Returns:
        One of: 
        - primary_implementation (Highest Rank)
        - amendment (High Rank)
        - clarification (Medium Rank)
        - procedural_guidelines (Medium-Low Rank)
        - financial_sanction (Low Rank)
        - repeal (Historical)
    """
    # 1. Preamble Analysis
    preamble = go_structure.get("preamble", {})
    preamble_text = preamble.get("text", "").lower() if preamble else ""
    
    # 2. Orders Analysis
    orders = go_structure.get("orders", [])
    orders_text = " ".join([o.get("text", "").lower() for o in orders])
    
    full_text = preamble_text + " " + orders_text
    
    # Classification Logic (Priority Order)
    
    # REPEAL
    if "hereby repeal" in full_text or "stands repealed" in full_text or "entirety superseded" in full_text:
        return "repeal"
        
    # AMENDMENT
    # Explicit amendment mention or structure
    if "amendment" in full_text or "amends" in full_text:
        # Check if it merely "cites" an amendment or IS an amendment
        if "hereby makes the following amendment" in full_text or "substituted" in full_text:
            return "amendment"
            
    # FINANCIAL SANCTION
    if "sanction is hereby accorded" in full_text and ("rupees" in full_text or "rs." in full_text or "only" in full_text):
        return "financial_sanction"
    if "budget" in full_text and "head of account" in full_text:
        return "financial_sanction"
        
    # CLARIFICATION
    if "clarification" in full_text or "clarifies" in full_text or "common understanding" in full_text:
        return "clarification"
        
    # PRIMARY IMPLEMENTATION
    # High confidence keywords in preamble
    if "implementation of" in preamble_text or "rules made under" in preamble_text:
        if "act" in preamble_text or "ordinance" in preamble_text:
            return "primary_implementation"
            
    # PROCEDURAL GUIDELINES (Default fallback for operational orders)
    if "guidelines" in full_text or "instructions" in full_text:
        return "procedural_guidelines"
        
    # Default
    return "primary_implementation" if "act" in full_text else "procedural_guidelines"

def get_role_weight(role: str) -> float:
    """Get ranking weight (0-1) for a GO role"""
    weights = {
        "primary_implementation": 1.0,
        "amendment": 0.95,
        "clarification": 0.70,
        "procedural_guidelines": 0.60,
        "financial_sanction": 0.40,
        "repeal": 0.20
    }
    return weights.get(role, 0.5)
