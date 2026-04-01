"""
Reference Resolution Module
Resolves legal references to canonical IDs for deterministic retrieval
"""

from .reference_resolver import ReferenceResolver, ResolutionResult, CanonicalReference

__all__ = ['ReferenceResolver', 'ResolutionResult', 'CanonicalReference']
