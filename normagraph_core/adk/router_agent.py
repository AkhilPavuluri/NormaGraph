"""
ADK Router Agent (Phase 3)

STRICT RULES:
- Agent ONLY selects pipeline and domains
- NO legal reasoning
- NO answer generation
- Hard timeout: 300ms
- JSON schema enforced
"""
import logging
import json
import time
from typing import Dict, Optional, List
from google.cloud import aiplatform
from vertexai.preview import generative_models

from normagraph_core.core.config import get_config
from normagraph_core.core.pipelines import PipelineType

logger = logging.getLogger(__name__)


class RouterAgent:
    """
    ADK Router Agent - selects pipeline and domains.
    
    This is the ONLY agentic component.
    It does NOT generate answers or do legal reasoning.
    """
    
    def __init__(self):
        self.config = get_config()
        self._initialize_adk()
        self.timeout_ms = self.config["adk_timeout_ms"]
    
    def _initialize_adk(self):
        """Initialize Vertex AI ADK"""
        if not self.config["vertex_ai"]:
            raise ValueError("ADK requires Vertex AI")
        
        project_id = self.config["project_id"]
        location = self.config["location"]
        aiplatform.init(project=project_id, location=location)
        logger.info("ADK Router Agent initialized")
    
    def route_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Route query to appropriate pipeline.
        
        Returns:
            {
                "pipeline": "P1" | "P2" | "P3" | "P4",
                "primary_domain": str,
                "secondary_domains": List[str],
                "risk_analysis": bool,
                "confidence": float,
                "fallback_used": bool
            }
        """
        start_time = time.time()
        
        try:
            # Build prompt
            prompt = self._build_routing_prompt(query, conversation_history)
            
            # Call ADK with strict schema
            response = self._call_adk_with_schema(prompt)
            
            # Validate response
            routing_decision = self._validate_response(response)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > self.timeout_ms:
                logger.warning(f"Router agent exceeded timeout ({elapsed_ms:.0f}ms > {self.timeout_ms}ms)")
                return self._get_fallback_decision()
            
            logger.info(f"Router decision: {routing_decision['pipeline']} in {elapsed_ms:.0f}ms")
            return routing_decision
        
        except Exception as e:
            logger.error(f"Router agent failed: {e}, using fallback")
            return self._get_fallback_decision()
    
    def _build_routing_prompt(self, query: str, conversation_history: Optional[List[Dict]]) -> str:
        """Build prompt for routing agent"""
        
        prompt = f"""You are a query router for a legal policy AI system. Your ONLY job is to select which pipeline to use and which domains to search.

CRITICAL RULES:
1. You do NOT generate answers
2. You do NOT do legal reasoning
3. You ONLY select pipeline and domains
4. Output MUST be valid JSON matching the schema

AVAILABLE PIPELINES:
- P1: Factual/Clarification - Simple questions, single domain, no risk analysis
- P2: Comparative/Evolution - Compare policies over time, show evolution
- P3: Risk/Constitutionality - Analyze legal risks, constitutional issues
- P4: Multi-Domain Impact - Analyze impact across multiple policy domains
- P5: Judicial Constraint - Validate policy against judicial precedents, check overruling status

AVAILABLE DOMAINS:
- education
- healthcare
- labor
- agriculture
- constitution
- judicial

USER QUERY:
{query}

OUTPUT JSON SCHEMA:
{{
  "pipeline": "P1" | "P2" | "P3" | "P4" | "P5",
  "primary_domain": "education" | "healthcare" | "labor" | "agriculture" | "constitution" | "judicial",
  "secondary_domains": ["domain1", "domain2"],  // Optional, max 2
  "risk_analysis": true | false,
  "reasoning": "Brief explanation of why this pipeline was chosen"
}}

OUTPUT (JSON only, no other text):"""
        
        return prompt
    
    def _call_adk_with_schema(self, prompt: str) -> str:
        """Call ADK with JSON schema enforcement"""
        
        # Define strict JSON schema
        json_schema = {
            "type": "object",
            "properties": {
                "pipeline": {
                    "type": "string",
                    "enum": ["P1", "P2", "P3", "P4", "P5"]
                },
                "primary_domain": {
                    "type": "string",
                    "enum": ["education", "healthcare", "labor", "agriculture", "constitution", "judicial"]
                },
                "secondary_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 2
                },
                "risk_analysis": {"type": "boolean"},
                "reasoning": {"type": "string"}
            },
            "required": ["pipeline", "primary_domain", "risk_analysis"]
        }
        
        # Use Vertex AI with structured output
        model = generative_models.GenerativeModel(
            model_name=self.config["gemini_model"],
            generation_config={
                "temperature": 0.1,  # Low temperature for deterministic routing
                "max_output_tokens": 200,  # Small output
            }
        )
        
        # Generate with schema
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": json_schema
            }
        )
        
        return response.text
    
    def _validate_response(self, response_text: str) -> Dict:
        """Validate and parse router response"""
        try:
            # Parse JSON
            data = json.loads(response_text.strip())
            
            # Validate pipeline
            pipeline = data.get("pipeline", "P1")
            if pipeline not in ["P1", "P2", "P3", "P4", "P5"]:
                raise ValueError(f"Invalid pipeline: {pipeline}")
            
            # Validate primary domain
            primary = data.get("primary_domain", "education")
            valid_domains = ["education", "healthcare", "labor", "agriculture", "constitution", "judicial"]
            if primary not in valid_domains:
                primary = "education"  # Safe fallback
            
            # Validate secondary domains
            secondary = data.get("secondary_domains", [])
            secondary = [d for d in secondary if d in valid_domains][:2]  # Max 2, filter invalid
            
            # Map pipeline string to enum
            pipeline_map = {
                "P1": PipelineType.P1_FACTUAL,
                "P2": PipelineType.P2_COMPARATIVE,
                "P3": PipelineType.P3_RISK_ANALYSIS,
                "P4": PipelineType.P4_MULTI_DOMAIN,
                "P5": PipelineType.P5_JUDICIAL_CONSTRAINT
            }
            
            return {
                "pipeline": pipeline_map[pipeline],
                "primary_domain": primary,
                "secondary_domains": secondary,
                "risk_analysis": data.get("risk_analysis", False),
                "confidence": 0.9,  # High confidence for routing
                "fallback_used": False,
                "reasoning": data.get("reasoning", "")
            }
        
        except Exception as e:
            logger.error(f"Failed to validate router response: {e}")
            raise
    
    def _get_fallback_decision(self) -> Dict:
        """Get safe fallback routing decision"""
        logger.warning("Using fallback routing decision (P1, education)")
        return {
            "pipeline": PipelineType.P1_FACTUAL,
            "primary_domain": "education",
            "secondary_domains": [],
            "risk_analysis": False,
            "confidence": 0.5,
            "fallback_used": True,
            "reasoning": "Fallback due to router failure"
        }

