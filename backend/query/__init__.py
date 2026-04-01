"""
NormaGraph query layer (retrieval, reasoning, citations).

This is NOT a toy RAG demo. This system is designed to survive
real policy/legal scrutiny with:
- Legal correctness > LLM fluency
- Temporal + jurisdictional reasoning
- Full explainability with citations
"""

from backend.query.orchestrator import QueryOrchestrator

__all__ = ["QueryOrchestrator"]
