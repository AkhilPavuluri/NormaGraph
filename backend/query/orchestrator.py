"""
Main Query Orchestrator

Orchestrates the entire query pipeline:
1. Query classification
2. Embedding generation
3. Hybrid retrieval
4. Temporal/jurisdictional reasoning
5. Answer generation
6. Risk analysis
7. Citation generation
"""
import logging
import time
from typing import Dict, List, Optional

from backend.query.classification.query_classifier import QueryClassifier
from backend.query.embeddings.query_embedder import QueryEmbedder
from backend.query.retrieval.hybrid_retriever import HybridRetriever
from backend.query.retrieval.layered_retriever import LayeredRetriever
from backend.query.domain.domain_detector import DomainDetector
from backend.query.reasoning.temporal_reasoner import TemporalReasoner
from backend.query.answering.answer_generator import AnswerGenerator
from backend.query.risk.legal_risk_analyzer import LegalRiskAnalyzer

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """
    Production-grade query orchestrator for legal policy RAG.
    
    Handles end-to-end query processing with:
    - Query understanding
    - Hybrid retrieval
    - Legal reasoning
    - Risk analysis
    - Citation generation
    """
    
    def __init__(self, use_layered_retrieval: bool = True):
        """
        Initialize query orchestrator.
        
        Args:
            use_layered_retrieval: Use domain-aware layered retrieval (default: True)
        """
        self.classifier = QueryClassifier(use_llm=False)
        self.embedder = QueryEmbedder()
        self.temporal_reasoner = TemporalReasoner()
        self.answer_generator = AnswerGenerator()
        self.risk_analyzer = LegalRiskAnalyzer()
        
        # Initialize retrieval components
        self.use_layered_retrieval = use_layered_retrieval
        if use_layered_retrieval:
            self.domain_detector = DomainDetector()
            self.retriever = LayeredRetriever(
                hybrid_retriever=HybridRetriever(),
                domain_detector=self.domain_detector
            )
            logger.info("QueryOrchestrator initialized with domain-aware layered retrieval")
        else:
            self.retriever = HybridRetriever()
            logger.info("QueryOrchestrator initialized with standard hybrid retrieval")
    
    def process_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        filters: Optional[Dict] = None
    ) -> Dict:
        """
        Process a query end-to-end.
        
        Args:
            query: User query
            conversation_history: Previous conversation turns
            filters: Additional filters (temporal, jurisdictional, etc.)
            
        Returns:
            Dict with complete response including:
                - answer: str
                - citations: List
                - source_hierarchy: Dict
                - risk_assessment: Dict
                - processing_trace: Dict
                - confidence: float
        """
        start_time = time.time()
        
        try:
            # Step 1: Classify query
            classification_start = time.time()
            classification = self.classifier.classify(query)
            classification_time = (time.time() - classification_start) * 1000
            
            logger.info(f"Query classified as: {classification['primary_type']} "
                       f"(confidence: {classification['confidence']:.2f})")
            
            # Step 2: Get retrieval parameters
            retrieval_params = self.classifier.get_retrieval_params(classification)
            
            # Step 3: Generate query embedding
            embedding_start = time.time()
            query_embedding = self.embedder.embed_query(query)
            embedding_time = (time.time() - embedding_start) * 1000
            
            # Step 4: Extract temporal context if needed
            temporal_context = None
            if classification["primary_type"] == "temporal":
                temporal_context = self.temporal_reasoner.extract_temporal_context(query)
                if temporal_context and filters:
                    filters["temporal"] = temporal_context["date"]
            
            # Step 5: Domain-aware layered retrieval or standard retrieval
            retrieval_start = time.time()
            
            if self.use_layered_retrieval:
                # Use domain-aware layered retrieval
                retrieval_result = self.retriever.retrieve_layered(
                    query=query,
                    query_embedding=query_embedding,
                    query_type=classification["primary_type"],
                    primary_domain=None,  # Can be detected from query or passed explicitly
                    top_k=retrieval_params["top_k"],
                    filters=filters,
                    source_priorities=retrieval_params.get("source_priorities")
                )
                retrieved_chunks = retrieval_result.all_chunks
                
                # Add domain detection info to processing trace
                domain_info = {
                    "domains_detected": retrieval_result.strategy.get("all_verticals", []),
                    "layer_1_count": len(retrieval_result.layer_1_chunks),
                    "layer_2_count": len(retrieval_result.layer_2_chunks),
                    "layer_3_count": len(retrieval_result.layer_3_chunks),
                    "has_binding_constraints": retrieval_result.strategy.get("has_binding_constraints", False),
                    "has_impact_domains": retrieval_result.strategy.get("has_impact_domains", False)
                }
            else:
                # Use standard hybrid retrieval
                retrieved_chunks = self.retriever.retrieve(
                    query=query,
                    query_embedding=query_embedding,
                    top_k=retrieval_params["top_k"],
                    filters=filters,
                    source_priorities=retrieval_params.get("source_priorities")
                )
                domain_info = {}
            
            retrieval_time = (time.time() - retrieval_start) * 1000
            
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
            
            # Step 6: Apply temporal filtering if needed
            if temporal_context:
                retrieved_chunks = self.temporal_reasoner.filter_by_temporal(
                    retrieved_chunks, temporal_context
                )
                logger.info(f"After temporal filtering: {len(retrieved_chunks)} chunks")
            
            # Step 7: Generate answer
            answer_start = time.time()
            answer_result = self.answer_generator.generate_answer(
                query=query,
                retrieved_chunks=retrieved_chunks,
                query_type=classification["primary_type"],
                conversation_history=conversation_history
            )
            answer_time = (time.time() - answer_start) * 1000
            
            # Step 8: Risk analysis
            risk_start = time.time()
            risk_assessment = self.risk_analyzer.analyze(
                query=query,
                retrieved_chunks=retrieved_chunks,
                answer=answer_result["answer"]
            )
            risk_time = (time.time() - risk_start) * 1000
            
            # Step 9: Build timeline if comparative query
            timeline = None
            if classification["primary_type"] == "comparative":
                timeline = self.temporal_reasoner.build_timeline(retrieved_chunks)
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            
            # Build processing trace
            processing_trace = {
                "query_classification": {
                    "type": classification["primary_type"],
                    "confidence": classification["confidence"],
                    "time_ms": classification_time
                },
                "embedding": {
                    "time_ms": embedding_time
                },
                "retrieval": {
                    "chunks_retrieved": len(retrieved_chunks),
                    "time_ms": retrieval_time,
                    "method": "layered" if self.use_layered_retrieval else "hybrid",
                    **domain_info
                },
                "answer_generation": {
                    "time_ms": answer_time,
                    "confidence": answer_result["confidence"]
                },
                "risk_analysis": {
                    "time_ms": risk_time,
                    "risk_level": risk_assessment["risk_level"]
                },
                "total_time_ms": total_time
            }
            
            # Build response
            response = {
                "answer": answer_result["answer"],
                "citations": answer_result["citations"],
                "source_hierarchy": answer_result["source_hierarchy"],
                "risk_assessment": {
                    "level": risk_assessment["risk_level"],
                    "score": risk_assessment["risk_score"],
                    "signals": risk_assessment["signals"],
                    "explanation": risk_assessment["explanation"]
                },
                "processing_trace": processing_trace,
                "confidence": answer_result["confidence"],
                "reasoning": answer_result["reasoning"],
                "timeline": timeline,
                # Include retrieved chunks for evaluation (can be removed in production)
                "_retrieved_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "doc_id": chunk.doc_id,
                        "content": chunk.content if hasattr(chunk, 'content') else str(chunk),
                        "metadata": chunk.metadata,
                        "score": chunk.score
                    }
                    for chunk in retrieved_chunks
                ] if hasattr(self, '_include_chunks_for_eval') else None
            }
            
            logger.info(f"Query processed in {total_time:.0f}ms")
            return response
        
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while processing your query: {str(e)}. Please try again or rephrase your question.",
                "citations": [],
                "source_hierarchy": {},
                "risk_assessment": {
                    "level": "none",
                    "score": 0.0,
                    "signals": [],
                    "explanation": "Error occurred during processing"
                },
                "processing_trace": {
                    "error": str(e),
                    "total_time_ms": (time.time() - start_time) * 1000
                },
                "confidence": 0.0,
                "reasoning": "Error during processing"
            }

