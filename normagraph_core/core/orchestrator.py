"""
Main Orchestrator (Phase 5)

Coordinates ADK router + deterministic pipeline execution.
"""
import logging
import time
import uuid
from typing import Dict, List, Optional

from normagraph_core.core.config import get_config
from normagraph_core.core.pipelines import PipelineExecutor, PipelineType
from normagraph_core.adk.router_agent import RouterAgent
from normagraph_core.core.observability import get_observability_logger

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """
    Production-grade orchestrator with ADK routing.
    
    Flow:
    1. ADK router selects pipeline + domains (300ms max)
    2. Deterministic pipeline execution
    3. Streaming response
    """
    
    def __init__(
        self,
        retrieval_service,
        llm_service,
        risk_analyzer,
        citation_generator,
        embedder,
        use_adk: bool = True
    ):
        self.config = get_config()
        self.use_adk = use_adk and self.config["use_adk"]
        
        # Initialize router (only if ADK enabled)
        self.router = RouterAgent() if self.use_adk else None
        
        # Initialize pipeline executor
        self.pipeline_executor = PipelineExecutor(
            retrieval_service=retrieval_service,
            llm_service=llm_service,
            risk_analyzer=risk_analyzer,
            citation_generator=citation_generator
        )
        
        self.embedder = embedder
        self.observability = get_observability_logger()
        
        logger.info(f"RAGOrchestrator initialized (ADK: {self.use_adk})")
    
    def process_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None,
        filters: Optional[Dict] = None,
        force_pipeline: Optional[PipelineType] = None
    ) -> Dict:
        """
        Process query end-to-end.
        
        Args:
            query: User query
            conversation_history: Previous conversation turns
            filters: Additional filters
            force_pipeline: Force specific pipeline (bypasses ADK)
            
        Returns:
            Complete response with answer, citations, risk assessment
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        trace = {}
        stage_latencies = {}
        
        try:
            # Step 1: Generate query embedding
            embedding_start = time.time()
            query_embedding = self.embedder.embed_query(query)
            embedding_ms = (time.time() - embedding_start) * 1000
            trace["embedding_ms"] = embedding_ms
            stage_latencies["embedding"] = embedding_ms
            
            # Step 2: Route query (ADK or fallback)
            routing_start = time.time()
            if force_pipeline:
                # Bypass ADK, use forced pipeline
                routing_decision = {
                    "pipeline": force_pipeline,
                    "primary_domain": "education",
                    "secondary_domains": [],
                    "risk_analysis": False,
                    "fallback_used": False
                }
            elif self.use_adk and self.router:
                routing_decision = self.router.route_query(query, conversation_history)
            else:
                # Fallback: use P1
                routing_decision = {
                    "pipeline": PipelineType.P1_FACTUAL,
                    "primary_domain": "education",
                    "secondary_domains": [],
                    "risk_analysis": False,
                    "fallback_used": True
                }
            
            routing_ms = (time.time() - routing_start) * 1000
            trace["routing_ms"] = routing_ms
            stage_latencies["routing"] = routing_ms
            trace["routing_decision"] = routing_decision
            
            # Step 3: Build domain list
            domains = [routing_decision["primary_domain"]]
            domains.extend(routing_decision.get("secondary_domains", []))
            
            # Step 4: Execute pipeline (deterministic)
            pipeline_start = time.time()
            result = self.pipeline_executor.execute(
                pipeline_type=routing_decision["pipeline"],
                query=query,
                query_embedding=query_embedding,
                domains=domains,
                filters=filters
            )
            pipeline_ms = (time.time() - pipeline_start) * 1000
            trace["pipeline_ms"] = pipeline_ms
            stage_latencies["pipeline"] = pipeline_ms
            
            # Step 5: Build response
            total_time = (time.time() - start_time) * 1000
            
            response = {
                "answer": result["answer"],
                "citations": result.get("citations", []),
                "risk_assessment": result.get("risk_assessment"),
                "timeline": result.get("timeline"),
                "comparison": result.get("comparison"),
                "processing_trace": {
                    **trace,
                    "total_ms": total_time,
                    "pipeline_used": result.get("pipeline", "Unknown"),
                    "domains_used": result.get("domains_used", []),
                    "adk_used": self.use_adk and not routing_decision.get("fallback_used", False)
                },
                "confidence": 0.85  # Default, can be computed from citations
            }
            
            logger.info(f"Query processed in {total_time:.0f}ms (pipeline: {result.get('pipeline')})")
            
            # Log to observability
            self.observability.log_request(
                request_id=request_id,
                query=query,
                routing_decision=routing_decision,
                pipeline_result=result,
                latency_ms=total_time,
                stage_latencies=stage_latencies
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            total_time = (time.time() - start_time) * 1000
            
            # Log error
            self.observability.log_error(
                request_id=request_id,
                query=query,
                error=str(e),
                latency_ms=total_time
            )
            
            return {
                "answer": f"I encountered an error processing your query: {str(e)}. Please try again.",
                "citations": [],
                "risk_assessment": None,
                "processing_trace": {
                    **trace,
                    "total_ms": total_time,
                    "error": str(e)
                },
                "confidence": 0.0
            }

