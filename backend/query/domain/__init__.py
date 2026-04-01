"""
Domain Detection Module

Detects which policy/legal domains are relevant for a query.
Implements the domain-aware retrieval strategy.
"""

from backend.query.domain.domain_detector import DomainDetector, DomainLayer

__all__ = ["DomainDetector", "DomainLayer"]

