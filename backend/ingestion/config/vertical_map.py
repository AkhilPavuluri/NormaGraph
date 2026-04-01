"""
Vertical to Collection Name Mapping

Maps document verticals to Qdrant collection names.
"""


def get_collection_name(vertical: str) -> str:
    """
    Get Qdrant collection name for a vertical.
    
    Args:
        vertical: Document vertical (go, legal, judicial, data, scheme)
        
    Returns:
        Collection name string
        
    Raises:
        ValueError: If vertical is not recognized
    """
    mapping = {
        "go": "government_orders",
        "legal": "legal_documents",
        "judicial": "judicial_documents",
        "data": "data_reports",
        "scheme": "schemes",
    }
    
    # Normalize vertical name
    vertical_lower = vertical.lower().strip()
    
    if vertical_lower not in mapping:
        raise ValueError(f"Unknown vertical: {vertical}. Must be one of: {list(mapping.keys())}")
    
    return mapping[vertical_lower]


def get_all_collections() -> list:
    """
    Get all collection names.
    
    Returns:
        List of all collection names
    """
    return [
        "government_orders",
        "legal_documents",
        "judicial_documents",
        "data_reports",
        "schemes",
    ]

