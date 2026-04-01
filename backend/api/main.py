"""
NormaGraph — FastAPI policy intelligence API

Query endpoints (streaming and non-streaming), health checks, and orchestrated retrieval/answering.
"""
import os
import logging
import json
import asyncio
from typing import List, Optional, Dict, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
from datetime import datetime

# Add backend directory to path
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.query.orchestrator import QueryOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NormaGraph API",
    description="Domain-aware policy intelligence — hybrid retrieval and structured answering",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting (simple in-memory, use Redis for production)
from collections import defaultdict
from time import time
_rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30  # per window

def check_rate_limit(client_id: str) -> bool:
    """Simple rate limiting"""
    now = time()
    requests = _rate_limit_store[client_id]
    # Remove old requests
    requests[:] = [req_time for req_time in requests if now - req_time < RATE_LIMIT_WINDOW]
    
    if len(requests) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    requests.append(now)
    return True

# Initialize orchestrator (lazy loading)
_orchestrator = None

def get_orchestrator() -> QueryOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = QueryOrchestrator()
    return _orchestrator


# Request/Response models
class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., description="User query", min_length=1, max_length=1000)
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation turns"
    )
    filters: Optional[Dict] = Field(
        default=None,
        description="Additional filters (temporal, jurisdictional, etc.)"
    )


class Citation(BaseModel):
    """Citation model"""
    docId: str
    title: str
    authority: str
    date: Optional[str] = None
    section: Optional[str] = None
    binding_strength: str


class QueryResponse(BaseModel):
    """Query response model"""
    answer: str
    citations: List[Citation]
    source_hierarchy: Dict
    risk_assessment: Dict
    processing_trace: Dict
    confidence: float
    reasoning: Optional[str] = None
    timeline: Optional[List[Dict]] = None


# Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NormaGraph API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        orchestrator = get_orchestrator()
        return {
            "status": "healthy",
            "service": "normagraph",
            "components": {
                "classifier": "operational",
                "embedder": "operational",
                "retriever": "operational",
                "answer_generator": "operational",
                "risk_analyzer": "operational"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


async def _process_query_streaming(
    query: str,
    conversation_history: Optional[List[Dict]],
    filters: Optional[Dict],
    request: Request
) -> AsyncGenerator[str, None]:
    """Process query with streaming response"""
    client_id = request.client.host if request.client else "unknown"
    
    # Rate limiting
    if not check_rate_limit(client_id):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Rate limit exceeded'})}\n\n"
        return
    
    try:
        orchestrator = get_orchestrator()
        
        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'stage': 'classifying', 'message': 'Classifying query...'})}\n\n"
        
        # Step 1: Classify (fast, non-blocking)
        classification = orchestrator.classifier.classify(query)
        retrieve_msg = f"Searching {classification['primary_type']} documents..."
        yield f"data: {json.dumps({'type': 'status', 'stage': 'retrieving', 'message': retrieve_msg})}\n\n"
        
        # Step 2: Embed and retrieve (can be parallel)
        query_embedding = orchestrator.embedder.embed_query(query)
        retrieval_params = orchestrator.classifier.get_retrieval_params(classification)
        
        # Retrieve in background
        if orchestrator.use_layered_retrieval:
            retrieval_result = orchestrator.retriever.retrieve_layered(
                query=query,
                query_embedding=query_embedding,
                query_type=classification["primary_type"],
                primary_domain=None,
                top_k=retrieval_params["top_k"],
                filters=filters,
                source_priorities=retrieval_params.get("source_priorities")
            )
            retrieved_chunks = retrieval_result.all_chunks
        else:
            retrieved_chunks = orchestrator.retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=retrieval_params["top_k"],
                filters=filters,
                source_priorities=retrieval_params.get("source_priorities")
            )
        
        yield f"data: {json.dumps({'type': 'status', 'stage': 'analyzing', 'message': f'Found {len(retrieved_chunks)} relevant documents. Analyzing...'})}\n\n"
        
        # Step 3: Generate answer with streaming
        yield f"data: {json.dumps({'type': 'status', 'stage': 'generating', 'message': 'Generating answer...'})}\n\n"
        
        # Generate answer (streaming)
        answer_result = await _generate_answer_streaming(
            orchestrator,
            query,
            retrieved_chunks,
            classification["primary_type"],
            conversation_history
        )
        
        # Stream answer tokens
        async for token in answer_result["answer_stream"]:
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        
        # Step 4: Risk analysis (non-blocking, send after answer)
        yield f"data: {json.dumps({'type': 'status', 'stage': 'risk_analysis', 'message': 'Assessing legal risks...'})}\n\n"
        risk_assessment = orchestrator.risk_analyzer.analyze(
            query=query,
            retrieved_chunks=retrieved_chunks,
            answer=answer_result["answer"]
        )
        
        # Send final metadata
        citations = [
            {
                "docId": c["docId"],
                "title": c["title"],
                "authority": c["authority"],
                "date": c.get("date"),
                "section": c.get("section"),
                "binding_strength": c.get("binding_strength", "medium")
            }
            for c in answer_result["citations"]
        ]
        
        yield f"data: {json.dumps({'type': 'metadata', 'data': {'citations': citations, 'source_hierarchy': answer_result['source_hierarchy'], 'risk_assessment': {'level': risk_assessment['risk_level'], 'score': risk_assessment['risk_score'], 'signals': risk_assessment.get('signals', [])}, 'confidence': answer_result['confidence']}})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    except asyncio.TimeoutError:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Request timeout'})}\n\n"
    except Exception as e:
        logger.error(f"Streaming error: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


async def _generate_answer_streaming(
    orchestrator,
    query: str,
    retrieved_chunks: List,
    query_type: str,
    conversation_history: Optional[List[Dict]]
) -> Dict:
    """Generate answer with streaming support"""
    # Generate answer normally (will be replaced with actual streaming LLM)
    answer_result = orchestrator.answer_generator.generate_answer(
        query=query,
        retrieved_chunks=retrieved_chunks,
        query_type=query_type,
        conversation_history=conversation_history
    )
    
    # Simulate streaming by chunking the answer
    answer_text = answer_result["answer"]
    words = answer_text.split()
    chunks = []
    current_chunk = []
    chunk_size = 3  # words per chunk
    
    for i, word in enumerate(words):
        current_chunk.append(word)
        if len(current_chunk) >= chunk_size or i == len(words) - 1:
            chunks.append(" ".join(current_chunk) + (" " if i < len(words) - 1 else ""))
            current_chunk = []
    
    async def stream_tokens():
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.01)  # Small delay for realistic streaming
    
    answer_result["answer_stream"] = stream_tokens()
    return answer_result


@app.post("/query")
async def query(request: QueryRequest, use_streaming: bool = False):
    """
    Main query endpoint.
    
    Processes legal/policy queries with:
    - Query classification
    - Hybrid retrieval
    - Answer generation with citations
    - Risk analysis
    
    Args:
        use_streaming: If True, returns SSE stream. If False, returns complete response.
    """
    if use_streaming:
        return StreamingResponse(
            _process_query_streaming(
                request.query,
                request.conversation_history,
                request.filters,
                request
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    
    # Non-streaming response (original behavior)
    try:
        logger.info(f"Received query: {request.query[:100]}...")
        
        # Timeout protection
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    get_orchestrator().process_query,
                    request.query,
                    request.conversation_history,
                    request.filters
                ),
                timeout=8.0  # 8 second timeout
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="Query processing timeout. Please try a simpler query."
            )
        
        # Convert citations to response format
        citations = [
            Citation(
                docId=c["docId"],
                title=c["title"],
                authority=c["authority"],
                date=c.get("date"),
                section=c.get("section"),
                binding_strength=c.get("binding_strength", "medium")
            )
            for c in result["citations"]
        ]
        
        response = QueryResponse(
            answer=result["answer"],
            citations=citations,
            source_hierarchy=result["source_hierarchy"],
            risk_assessment=result["risk_assessment"],
            processing_trace=result["processing_trace"],
            confidence=result["confidence"],
            reasoning=result.get("reasoning"),
            timeline=result.get("timeline")
        )
        
        logger.info(f"Query processed successfully (confidence: {result['confidence']:.2f})")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """
    Streaming query endpoint (SSE).
    
    Returns Server-Sent Events stream with:
    - Status updates (classifying, retrieving, generating, etc.)
    - Answer tokens (streaming)
    - Final metadata (citations, risk assessment, etc.)
    """
    return StreamingResponse(
        _process_query_streaming(
            request.query,
            request.conversation_history,
            request.filters,
            request
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/status")
async def status():
    """Get system status"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "/": "Root endpoint",
            "/health": "Health check",
            "/query": "Query endpoint (POST)",
            "/status": "Status endpoint"
        }
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

