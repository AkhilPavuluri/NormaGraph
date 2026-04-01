"""
ADK Integration with Existing Services

Integrates ADK router with backend/query services.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from normagraph_core.core.orchestrator import RAGOrchestrator
from normagraph_core.core.pipelines import PipelineExecutor
from normagraph_core.adk.router_agent import RouterAgent

# Import existing services
try:
    from backend.query.embeddings.query_embedder import QueryEmbedder
    from backend.query.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk
    from backend.query.answering.answer_generator import AnswerGenerator
    from backend.query.risk.legal_risk_analyzer import LegalRiskAnalyzer
    from backend.query.citations.citation_generator import CitationGenerator
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import backend services: {e}")
    SERVICES_AVAILABLE = False


def create_adk_orchestrator(use_adk: bool = True) -> RAGOrchestrator:
    """
    Create RAG orchestrator with ADK routing.
    
    Integrates:
    - ADK Router Agent (for routing)
    - Existing backend/query services (for execution)
    """
    if not SERVICES_AVAILABLE:
        raise ImportError(
            "Backend services not available. "
            "Ensure backend/query services are accessible."
        )
    
    # Initialize existing services
    embedder = QueryEmbedder()
    retrieval_service = HybridRetriever()
    llm_service = AnswerGenerator()
    risk_analyzer = LegalRiskAnalyzer()
    citation_generator = CitationGenerator()
    
    # Create orchestrator with ADK
    orchestrator = RAGOrchestrator(
        retrieval_service=retrieval_service,
        llm_service=llm_service,
        risk_analyzer=risk_analyzer,
        citation_generator=citation_generator,
        embedder=embedder,
        use_adk=use_adk
    )
    
    return orchestrator

