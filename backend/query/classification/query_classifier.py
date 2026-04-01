"""
Query Classification System

Classifies queries into types that control retrieval strategy,
source prioritization, and answer format.
"""
import re
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query classification types"""
    FACTUAL = "factual"  # "What did NEP 2020 say about autonomy?"
    COMPARATIVE = "comparative"  # "How did UGC autonomy evolve pre and post NEP?"
    RISK_ANALYSIS = "risk_analysis"  # "Can states mandate admissions bypassing UGC?"
    JUDICIAL_CONSTRAINT = "judicial_constraint"  # "Has SC restricted private university autonomy?"
    TEMPORAL = "temporal"  # "What was the policy in 2015?"
    JURISDICTIONAL = "jurisdictional"  # "Does this apply to Andhra Pradesh?"


class QueryClassifier:
    """
    Classifies legal/policy queries to determine retrieval strategy.
    
    Uses rule-based patterns for speed, with optional LLM fallback
    for ambiguous cases.
    """
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self._build_patterns()
    
    def _build_patterns(self):
        """Build regex patterns for query classification"""
        
        # Factual patterns
        self.factual_patterns = [
            r'\b(what|which|who|where|when)\b.*\b(said|stated|mentioned|specified|defined|requires?|mandates?|allows?|prohibits?)\b',
            r'\b(what|which)\b.*\b(does|did|is|are|was|were)\b',
            r'\b(according to|as per|per|under)\b',
        ]
        
        # Comparative patterns
        self.comparative_patterns = [
            r'\b(compare|comparison|difference|differences|versus|vs\.?|versus)\b',
            r'\b(how did|how has|how have|evolution|evolved|changed|changes)\b',
            r'\b(pre|post|before|after|earlier|later)\b.*\b(and|versus)\b',
            r'\b(over time|across|between)\b',
        ]
        
        # Risk analysis patterns
        self.risk_patterns = [
            r'\b(can|could|may|might|would|should)\b.*\b(legal|constitutional|valid|permissible|allowed|prohibited)\b',
            r'\b(risk|risks|conflict|conflicts|contradict|contradiction|violate|violation)\b',
            r'\b(compliance|compliant|non-compliance|non-compliant)\b',
            r'\b(constitutional|constitutionally|unconstitutional)\b',
        ]
        
        # Judicial constraint patterns
        self.judicial_patterns = [
            r'\b(supreme court|high court|sc|hc|judgment|judgement|case|precedent|binding)\b',
            r'\b(court|judicial|judiciary|ruled|ruling|order|decided|decision)\b',
            r'\b(overruled|overrules|precedent|stare decisis)\b',
        ]
        
        # Temporal patterns
        self.temporal_patterns = [
            r'\b(in|during|on|by|before|after|since|until)\s+\d{4}\b',
            r'\b(year|years|decade|decades|period|timeframe)\b',
            r'\b(historical|historically|past|previous|earlier|later|recent)\b',
        ]
        
        # Jurisdictional patterns
        self.jurisdictional_patterns = [
            r'\b(state|states|union|central|federal|provincial)\b',
            r'\b(andhra pradesh|ap|telangana|karnataka|tamil nadu|kerala|maharashtra)\b',
            r'\b(jurisdiction|jurisdictional|applicable|applies|applies to)\b',
            r'\b(territorial|geographic|region|regional)\b',
        ]
    
    def classify(self, query: str, context: Optional[Dict] = None) -> Dict:
        """
        Classify a query into one or more types.
        
        Args:
            query: User query string
            context: Optional context (conversation history, etc.)
            
        Returns:
            Dict with:
                - primary_type: QueryType enum
                - secondary_types: List of QueryType enums
                - confidence: float (0-1)
                - reasoning: str
        """
        query_lower = query.lower()
        
        # Score each type
        scores = {
            QueryType.FACTUAL: self._score_patterns(query_lower, self.factual_patterns),
            QueryType.COMPARATIVE: self._score_patterns(query_lower, self.comparative_patterns),
            QueryType.RISK_ANALYSIS: self._score_patterns(query_lower, self.risk_patterns),
            QueryType.JUDICIAL_CONSTRAINT: self._score_patterns(query_lower, self.judicial_patterns),
            QueryType.TEMPORAL: self._score_patterns(query_lower, self.temporal_patterns),
            QueryType.JURISDICTIONAL: self._score_patterns(query_lower, self.jurisdictional_patterns),
        }
        
        # Get primary type (highest score)
        primary_type = max(scores.items(), key=lambda x: x[1])[0]
        primary_score = scores[primary_type]
        
        # Get secondary types (score > 0.3)
        secondary_types = [
            qtype for qtype, score in scores.items()
            if score > 0.3 and qtype != primary_type
        ]
        
        # Default to factual if no strong signal
        if primary_score < 0.2:
            primary_type = QueryType.FACTUAL
            primary_score = 0.5  # Default confidence
            reasoning = "No strong classification signals - defaulting to factual query"
        else:
            reasoning = f"Detected {primary_type.value} query with {primary_score:.2f} confidence"
        
        # Build result
        result = {
            "primary_type": primary_type.value,
            "secondary_types": [t.value for t in secondary_types],
            "confidence": min(primary_score, 1.0),
            "reasoning": reasoning,
            "all_scores": {k.value: v for k, v in scores.items()}
        }
        
        logger.debug(f"Query classification: {result}")
        return result
    
    def _score_patterns(self, text: str, patterns: List[str]) -> float:
        """Score text against a list of patterns"""
        matches = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
        
        # Normalize by number of patterns
        if not patterns:
            return 0.0
        
        score = matches / len(patterns)
        
        # Boost score if multiple patterns match
        if matches > 1:
            score = min(score * 1.5, 1.0)
        
        return score
    
    def get_retrieval_params(self, classification: Dict) -> Dict:
        """
        Get retrieval parameters based on query classification.
        
        Returns:
            Dict with retrieval configuration
        """
        primary_type = classification["primary_type"]
        
        params = {
            "top_k": 20,  # Default
            "retrieval_depth": "standard",
            "source_priorities": [],
            "temporal_filter": None,
            "jurisdictional_filter": None,
        }
        
        if primary_type == QueryType.FACTUAL.value:
            params["top_k"] = 15
            params["source_priorities"] = ["judicial", "legal", "go", "scheme"]
        
        elif primary_type == QueryType.COMPARATIVE.value:
            params["top_k"] = 30  # Need more docs for comparison
            params["retrieval_depth"] = "deep"
            params["source_priorities"] = ["go", "legal", "judicial"]
        
        elif primary_type == QueryType.RISK_ANALYSIS.value:
            params["top_k"] = 25
            params["source_priorities"] = ["judicial", "legal", "go"]  # Judicial first for constraints
            params["retrieval_depth"] = "deep"
        
        elif primary_type == QueryType.JUDICIAL_CONSTRAINT.value:
            params["top_k"] = 20
            params["source_priorities"] = ["judicial", "legal"]  # Only judicial/legal matter
            params["retrieval_depth"] = "deep"
        
        elif primary_type == QueryType.TEMPORAL.value:
            params["top_k"] = 20
            params["temporal_filter"] = "extract_from_query"  # Will extract date from query
        
        elif primary_type == QueryType.JURISDICTIONAL.value:
            params["top_k"] = 20
            params["jurisdictional_filter"] = "extract_from_query"  # Will extract jurisdiction
        
        return params

