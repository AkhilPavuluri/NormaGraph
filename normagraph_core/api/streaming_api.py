"""
Streaming API with SSE (Phase 6, 8)

Server-Sent Events for real-time response streaming.
"""
import json
import logging
import time
import asyncio
from typing import AsyncGenerator, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Query request model"""
    query: str
    conversation_history: Optional[list] = None
    filters: Optional[dict] = None
    force_pipeline: Optional[str] = None


class StreamingRAGAPI:
    """
    FastAPI server with SSE streaming.
    
    Streams:
    - Stage updates ("Analyzing precedents...")
    - Answer chunks
    - Final structured response
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.app = FastAPI(
            title="NormaGraph API (ADK streaming)",
            description="Production-grade legal policy RAG with ADK routing",
            version="2.0.0"
        )
        
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {
                "service": "NormaGraph API (ADK)",
                "version": "2.0.0",
                "status": "operational"
            }
        
        @self.app.get("/health")
        async def health():
            return {
                "status": "healthy",
                "adk_enabled": self.orchestrator.use_adk
            }
        
        @self.app.post("/chat/stream")
        async def chat_stream(request: QueryRequest):
            """Streaming chat endpoint"""
            try:
                return StreamingResponse(
                    self._stream_response(request),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    }
                )
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/chat")
        async def chat(request: QueryRequest):
            """Non-streaming chat endpoint (for compatibility)"""
            try:
                result = self.orchestrator.process_query(
                    query=request.query,
                    conversation_history=request.conversation_history,
                    filters=request.filters,
                    force_pipeline=request.force_pipeline
                )
                return result
            except Exception as e:
                logger.error(f"Chat error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _stream_response(self, request: QueryRequest) -> AsyncGenerator[str, None]:
        """Stream response with SSE"""
        
        # Send initial status
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...'})}\n\n"
        
        try:
            # Process query (non-blocking where possible)
            result = self.orchestrator.process_query(
                query=request.query,
                conversation_history=request.conversation_history,
                filters=request.filters,
                force_pipeline=request.force_pipeline
            )
            
            # Stream answer chunks
            answer = result.get("answer", "")
            words = answer.split()
            
            # Send answer in chunks
            chunk_size = 5  # Words per chunk
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            # Send final structured response
            yield f"data: {json.dumps({'type': 'complete', 'data': result})}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"



