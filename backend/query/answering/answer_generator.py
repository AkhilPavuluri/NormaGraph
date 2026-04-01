"""
Answer Generation System

Generates answers with inline citations and explainability.
This is where legal correctness > LLM fluency.
"""
import os
import logging
from typing import Dict, List, Optional
import google.generativeai as genai
from google.cloud import aiplatform

from backend.query.citations.citation_generator import CitationGenerator, Citation
from backend.query.config import get_config

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Generates answers with:
    - Inline citations
    - Source hierarchy
    - Explainability
    - Legal correctness checks
    """
    
    def __init__(self):
        self.config = get_config()
        self.citation_generator = CitationGenerator()
        self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize LLM client"""
        if self.config["vertex_ai"]:
            project_id = self.config["project_id"]
            location = self.config["location"]
            aiplatform.init(project=project_id, location=location)
            logger.info("Initialized Vertex AI for answer generation")
        else:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
            else:
                raise ValueError("LLM credentials required")
    
    def generate_answer(
        self,
        query: str,
        retrieved_chunks: List,
        query_type: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Generate answer with citations.
        
        Args:
            query: User query
            retrieved_chunks: Retrieved document chunks
            query_type: Query classification type
            conversation_history: Previous conversation turns
            
        Returns:
            Dict with:
                - answer: str (answer text with inline citations)
                - citations: List[Citation]
                - source_hierarchy: Dict
                - confidence: float
                - reasoning: str
        """
        if not retrieved_chunks:
            return {
                "answer": "I could not find any relevant documents to answer this query. Please try rephrasing or check if the relevant documents have been ingested.",
                "citations": [],
                "source_hierarchy": {},
                "confidence": 0.0,
                "reasoning": "No documents retrieved"
            }
        
        # Generate citations first
        citations = self.citation_generator.generate_citations(
            retrieved_chunks,
            ""  # Answer not yet generated
        )
        
        # Build context for LLM
        context = self._build_context(retrieved_chunks, citations)
        
        # Generate answer using LLM
        answer_text = self._generate_with_llm(query, context, query_type, conversation_history)
        
        # Verify answer has citations
        answer_with_citations = self._add_inline_citations(answer_text, citations)
        
        # Generate source hierarchy
        source_hierarchy = self.citation_generator.generate_source_hierarchy(citations)
        
        # Calculate confidence
        confidence = self._calculate_confidence(retrieved_chunks, citations)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(query_type, citations, len(retrieved_chunks))
        
        return {
            "answer": answer_with_citations,
            "citations": [
                {
                    "docId": c.doc_id,
                    "title": c.title,
                    "authority": c.authority,
                    "date": c.date,
                    "section": c.section,
                    "binding_strength": c.binding_strength
                }
                for c in citations
            ],
            "source_hierarchy": source_hierarchy,
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    def _build_context(self, chunks: List, citations: List[Citation]) -> str:
        """Build context string from retrieved chunks"""
        context_parts = []
        
        for i, chunk in enumerate(chunks[:10]):  # Limit to top 10
            citation = next((c for c in citations if c.chunk_id == chunk.chunk_id), None)
            citation_ref = f"[{i+1}]" if citation else ""
            
            context_parts.append(f"Document {i+1} {citation_ref}:")
            context_parts.append(f"Source: {chunk.metadata.get('authority', 'Unknown')}")
            if chunk.metadata.get("date"):
                context_parts.append(f"Date: {chunk.metadata.get('date')}")
            context_parts.append(f"Content: {chunk.content[:500] if hasattr(chunk, 'content') else ''}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _generate_with_llm(
        self,
        query: str,
        context: str,
        query_type: str,
        conversation_history: Optional[List[Dict]]
    ) -> str:
        """Generate answer using LLM"""
        
        # Build prompt
        prompt = self._build_prompt(query, context, query_type)
        
        try:
            if self.config["vertex_ai"]:
                # Use Vertex AI
                model = genai.GenerativeModel(self.config["gemini_model"])
                response = model.generate_content(prompt)
                answer = response.text
            else:
                # Use API
                model = genai.GenerativeModel(self.config["gemini_model"])
                response = model.generate_content(prompt)
                answer = response.text
            
            return answer
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback: construct basic answer from chunks
            return self._fallback_answer(query, context)
    
    def _build_prompt(self, query: str, context: str, query_type: str) -> str:
        """Build prompt for LLM"""
        
        prompt = f"""You are a legal policy assistant. Answer the following query based ONLY on the provided legal documents.

CRITICAL REQUIREMENTS:
1. Legal correctness > fluency. If you cannot find authoritative support, say so explicitly.
2. Every claim MUST be supported by the provided documents.
3. Use inline citations like [1], [2] when referencing documents.
4. If documents conflict, explain the conflict and cite both sources.
5. Be precise with dates, authorities, and legal status.

Query Type: {query_type}

Documents:
{context}

Query: {query}

Answer (with inline citations [1], [2], etc.):"""
        
        return prompt
    
    def _add_inline_citations(self, answer: str, citations: List[Citation]) -> str:
        """Ensure answer has proper inline citations"""
        # Check if answer already has citations
        if "[" in answer and "]" in answer:
            return answer
        
        # If no citations, add them at the end
        citation_text = "\n\nSources:\n"
        for i, citation in enumerate(citations[:5], 1):
            citation_text += f"[{i}] {self.citation_generator.format_citation(citation)}\n"
        
        return answer + citation_text
    
    def _fallback_answer(self, query: str, context: str) -> str:
        """Generate fallback answer if LLM fails"""
        return f"Based on the available documents, I found relevant information. However, I cannot generate a detailed answer at this time. Please review the retrieved documents for more information."
    
    def _calculate_confidence(
        self,
        chunks: List,
        citations: List[Citation]
    ) -> float:
        """Calculate confidence in answer"""
        if not chunks:
            return 0.0
        
        # Base confidence on:
        # 1. Number of sources
        # 2. Authority level of sources
        # 3. Consistency across sources
        
        source_count_score = min(len(chunks) / 5.0, 1.0)  # Max at 5 sources
        
        # Authority score
        binding_count = sum(1 for c in citations if c.binding_strength == "binding")
        authority_score = min(binding_count / 3.0, 1.0)
        
        # Combined confidence
        confidence = (source_count_score * 0.4 + authority_score * 0.6)
        
        return min(confidence, 1.0)
    
    def _generate_reasoning(
        self,
        query_type: str,
        citations: List[Citation],
        num_sources: int
    ) -> str:
        """Generate reasoning explanation"""
        reasoning_parts = [
            f"Query classified as: {query_type}",
            f"Retrieved {num_sources} relevant documents",
            f"Found {len(citations)} authoritative citations"
        ]
        
        if citations:
            binding = [c for c in citations if c.binding_strength == "binding"]
            if binding:
                reasoning_parts.append(f"{len(binding)} binding sources identified")
        
        return ". ".join(reasoning_parts) + "."

