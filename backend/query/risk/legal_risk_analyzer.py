"""
Legal Risk Analysis System

Rule-driven risk detection with LLM explanation.
This is NOT just LLM opinion - it's rule-based + LLM explanation.
"""
import logging
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk severity levels"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskSignal:
    """A detected risk signal"""
    signal_type: str
    risk_level: RiskLevel
    description: str
    source_doc: Optional[str] = None
    conflicting_doc: Optional[str] = None
    evidence: Optional[str] = None


class LegalRiskAnalyzer:
    """
    Analyzes legal and constitutional risks in proposed policies.
    
    Uses rule-based heuristics to detect risks, then LLM for explanation.
    """
    
    def __init__(self):
        self._build_risk_rules()
    
    def _build_risk_rules(self):
        """Build risk detection rules"""
        
        # Risk signals and their severity
        self.risk_signals = {
            "conflicts_with_sc_judgment": {
                "level": RiskLevel.HIGH,
                "weight": 10.0,
                "description": "Conflicts with binding Supreme Court judgment"
            },
            "conflicts_with_hc_judgment": {
                "level": RiskLevel.MEDIUM,
                "weight": 7.0,
                "description": "Conflicts with High Court judgment"
            },
            "conflicts_with_legal_act": {
                "level": RiskLevel.HIGH,
                "weight": 8.0,
                "description": "Conflicts with statutory law"
            },
            "policy_only_contradiction": {
                "level": RiskLevel.LOW,
                "weight": 3.0,
                "description": "Contradicts other policy documents"
            },
            "jurisdiction_mismatch": {
                "level": RiskLevel.HIGH,
                "weight": 9.0,
                "description": "Jurisdictional mismatch (state vs central)"
            },
            "retrospective_application": {
                "level": RiskLevel.HIGH,
                "weight": 8.5,
                "description": "Retrospective application may be unconstitutional"
            },
            "constitutional_violation": {
                "level": RiskLevel.CRITICAL,
                "weight": 15.0,
                "description": "Potential constitutional violation"
            },
            "overruled_precedent": {
                "level": RiskLevel.MEDIUM,
                "weight": 6.0,
                "description": "Relies on overruled precedent"
            },
            "temporal_conflict": {
                "level": RiskLevel.MEDIUM,
                "weight": 5.0,
                "description": "Temporal conflict with newer/older documents"
            },
        }
    
    def analyze(
        self,
        query: str,
        retrieved_chunks: List,
        answer: str
    ) -> Dict:
        """
        Analyze legal risks based on retrieved documents and generated answer.
        
        Args:
            query: User query
            retrieved_chunks: Retrieved document chunks
            answer: Generated answer text
            
        Returns:
            Dict with:
                - risk_level: RiskLevel enum value
                - risk_score: float (0-100)
                - signals: List of RiskSignal objects
                - explanation: str (LLM-generated explanation)
        """
        signals = []
        
        # Analyze retrieved chunks for conflicts
        signals.extend(self._detect_judicial_conflicts(retrieved_chunks))
        signals.extend(self._detect_legal_conflicts(retrieved_chunks))
        signals.extend(self._detect_jurisdictional_issues(retrieved_chunks))
        signals.extend(self._detect_temporal_issues(retrieved_chunks))
        signals.extend(self._detect_constitutional_issues(retrieved_chunks, answer))
        
        # Calculate overall risk
        risk_score = self._calculate_risk_score(signals)
        risk_level = self._score_to_level(risk_score)
        
        # Generate explanation
        explanation = self._generate_explanation(signals, risk_level, query)
        
        return {
            "risk_level": risk_level.value,
            "risk_score": risk_score,
            "signals": [
                {
                    "type": s.signal_type,
                    "level": s.risk_level.value,
                    "description": s.description,
                    "source_doc": s.source_doc,
                    "conflicting_doc": s.conflicting_doc,
                    "evidence": s.evidence
                }
                for s in signals
            ],
            "explanation": explanation
        }
    
    def _detect_judicial_conflicts(self, chunks: List) -> List[RiskSignal]:
        """Detect conflicts with judicial precedents"""
        signals = []
        
        # Group chunks by court level
        sc_chunks = [c for c in chunks if c.metadata.get("court_level") == "Supreme Court"]
        hc_chunks = [c for c in chunks if c.metadata.get("court_level") == "High Court"]
        
        # Check for overruled judgments
        for chunk in sc_chunks + hc_chunks:
            if chunk.metadata.get("overruled_by"):
                signals.append(RiskSignal(
                    signal_type="overruled_precedent",
                    risk_level=RiskLevel.MEDIUM,
                    description=f"Relies on overruled precedent: {chunk.metadata.get('overruled_by')}",
                    source_doc=chunk.doc_id,
                    evidence=chunk.content[:200]
                ))
        
        # Check for conflicting judicial positions
        if len(sc_chunks) > 1:
            # Multiple SC judgments - check if they conflict
            # This is simplified - real implementation would need semantic comparison
            signals.append(RiskSignal(
                signal_type="conflicts_with_sc_judgment",
                risk_level=RiskLevel.HIGH,
                description="Multiple Supreme Court judgments found - potential conflict",
                source_doc=sc_chunks[0].doc_id,
                conflicting_doc=sc_chunks[1].doc_id if len(sc_chunks) > 1 else None
            ))
        
        return signals
    
    def _detect_legal_conflicts(self, chunks: List) -> List[RiskSignal]:
        """Detect conflicts with statutory law"""
        signals = []
        
        legal_chunks = [c for c in chunks if c.metadata.get("vertical") == "legal"]
        go_chunks = [c for c in chunks if c.metadata.get("vertical") == "go"]
        
        # If GO contradicts legal act, that's high risk
        if legal_chunks and go_chunks:
            # Simplified: if both present, flag for review
            signals.append(RiskSignal(
                signal_type="conflicts_with_legal_act",
                risk_level=RiskLevel.HIGH,
                description="Government order may conflict with statutory law",
                source_doc=go_chunks[0].doc_id,
                conflicting_doc=legal_chunks[0].doc_id
            ))
        
        return signals
    
    def _detect_jurisdictional_issues(self, chunks: List) -> List[RiskSignal]:
        """Detect jurisdictional mismatches"""
        signals = []
        
        jurisdictions = set()
        for chunk in chunks:
            jurisdiction = chunk.metadata.get("jurisdiction")
            if jurisdiction:
                jurisdictions.add(jurisdiction)
        
        # If mixing state and central jurisdictions, flag
        if len(jurisdictions) > 1:
            has_state = any("State" in j or "Andhra" in j or "Telangana" in j for j in jurisdictions)
            has_central = "India" in jurisdictions or "Central" in jurisdictions
            
            if has_state and has_central:
                signals.append(RiskSignal(
                    signal_type="jurisdiction_mismatch",
                    risk_level=RiskLevel.HIGH,
                    description="Mixing state and central jurisdictions",
                    evidence=f"Jurisdictions: {', '.join(jurisdictions)}"
                ))
        
        return signals
    
    def _detect_temporal_issues(self, chunks: List) -> List[RiskSignal]:
        """Detect temporal conflicts"""
        signals = []
        
        # Check for superseded documents
        for chunk in chunks:
            if chunk.metadata.get("is_superseded") == "true":
                signals.append(RiskSignal(
                    signal_type="temporal_conflict",
                    risk_level=RiskLevel.MEDIUM,
                    description="Relies on superseded document",
                    source_doc=chunk.doc_id,
                    evidence=f"Superseded by: {chunk.metadata.get('superseded_by', 'unknown')}"
                ))
        
        return signals
    
    def _detect_constitutional_issues(self, chunks: List, answer: str) -> List[RiskSignal]:
        """Detect potential constitutional violations"""
        signals = []
        
        # Check answer text for constitutional keywords
        constitutional_keywords = [
            "unconstitutional", "violates article", "fundamental right",
            "discrimination", "arbitrary", "violates constitution"
        ]
        
        answer_lower = answer.lower()
        for keyword in constitutional_keywords:
            if keyword in answer_lower:
                signals.append(RiskSignal(
                    signal_type="constitutional_violation",
                    risk_level=RiskLevel.CRITICAL,
                    description=f"Potential constitutional issue detected: {keyword}",
                    evidence=answer[:300]
                ))
        
        return signals
    
    def _calculate_risk_score(self, signals: List[RiskSignal]) -> float:
        """Calculate overall risk score from signals"""
        if not signals:
            return 0.0
        
        total_weight = sum(self.risk_signals.get(s.signal_type, {}).get("weight", 1.0) for s in signals)
        
        # Normalize to 0-100
        max_possible = 100.0
        score = min(total_weight * 5, max_possible)  # Scale factor
        
        return score
    
    def _score_to_level(self, score: float) -> RiskLevel:
        """Convert risk score to level"""
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 20:
            return RiskLevel.LOW
        else:
            return RiskLevel.NONE
    
    def _generate_explanation(
        self,
        signals: List[RiskSignal],
        risk_level: RiskLevel,
        query: str
    ) -> str:
        """
        Generate human-readable risk explanation.
        
        In production, this would use LLM. For now, rule-based.
        """
        if not signals:
            return "No legal risks detected. The answer is based on current, authoritative sources."
        
        explanations = []
        
        # Group by risk level
        critical = [s for s in signals if s.risk_level == RiskLevel.CRITICAL]
        high = [s for s in signals if s.risk_level == RiskLevel.HIGH]
        medium = [s for s in signals if s.risk_level == RiskLevel.MEDIUM]
        low = [s for s in signals if s.risk_level == RiskLevel.LOW]
        
        if critical:
            explanations.append(f"**CRITICAL RISKS ({len(critical)}):**")
            for signal in critical:
                explanations.append(f"- {signal.description}")
                if signal.source_doc:
                    explanations.append(f"  Source: {signal.source_doc}")
        
        if high:
            explanations.append(f"\n**HIGH RISKS ({len(high)}):**")
            for signal in high:
                explanations.append(f"- {signal.description}")
                if signal.conflicting_doc:
                    explanations.append(f"  Conflicts with: {signal.conflicting_doc}")
        
        if medium:
            explanations.append(f"\n**MEDIUM RISKS ({len(medium)}):**")
            for signal in medium[:3]:  # Limit to top 3
                explanations.append(f"- {signal.description}")
        
        if low:
            explanations.append(f"\n**LOW RISKS ({len(low)}):**")
            explanations.append(f"- {len(low)} minor issues detected")
        
        return "\n".join(explanations)

