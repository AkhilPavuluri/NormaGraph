"""
Evaluation Metrics

Measures for citation accuracy, legal correctness, and system quality.
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CitationAccuracy:
    """Citation accuracy metrics"""
    total_citations: int
    correct_citations: int
    incorrect_citations: int
    missing_citations: int
    accuracy: float  # correct / total expected
    
    def to_dict(self) -> Dict:
        return {
            "total_citations": self.total_citations,
            "correct_citations": self.correct_citations,
            "incorrect_citations": self.incorrect_citations,
            "missing_citations": self.missing_citations,
            "accuracy": self.accuracy
        }


@dataclass
class AuthorityCorrectness:
    """Authority correctness metrics"""
    total_authority_claims: int
    correct_authority_claims: int
    incorrect_authority_claims: int
    accuracy: float
    
    def to_dict(self) -> Dict:
        return {
            "total_authority_claims": self.total_authority_claims,
            "correct_authority_claims": self.correct_authority_claims,
            "incorrect_authority_claims": self.incorrect_authority_claims,
            "accuracy": self.accuracy
        }


@dataclass
class TemporalCorrectness:
    """Temporal correctness metrics"""
    total_date_references: int
    correct_date_references: int
    incorrect_date_references: int
    accuracy: float
    
    def to_dict(self) -> Dict:
        return {
            "total_date_references": self.total_date_references,
            "correct_date_references": self.correct_date_references,
            "incorrect_date_references": self.incorrect_date_references,
            "accuracy": self.accuracy
        }


@dataclass
class HallucinationMetrics:
    """Hallucination detection metrics"""
    total_claims: int
    supported_claims: int
    unsupported_claims: int
    hallucination_rate: float  # unsupported / total
    
    def to_dict(self) -> Dict:
        return {
            "total_claims": self.total_claims,
            "supported_claims": self.supported_claims,
            "unsupported_claims": self.unsupported_claims,
            "hallucination_rate": self.hallucination_rate
        }


@dataclass
class RiskDetectionMetrics:
    """Risk detection accuracy metrics"""
    total_queries: int
    correct_risk_assessments: int
    incorrect_risk_assessments: int
    false_positives: int  # Detected risk when none exists
    false_negatives: int  # Missed risk when it exists
    accuracy: float
    
    def to_dict(self) -> Dict:
        return {
            "total_queries": self.total_queries,
            "correct_risk_assessments": self.correct_risk_assessments,
            "incorrect_risk_assessments": self.incorrect_risk_assessments,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "accuracy": self.accuracy
        }


class EvaluationMetrics:
    """
    Comprehensive evaluation metrics for RAG system.
    """
    
    def __init__(self):
        self.citation_accuracy = CitationAccuracy(0, 0, 0, 0, 0.0)
        self.authority_correctness = AuthorityCorrectness(0, 0, 0, 0.0)
        self.temporal_correctness = TemporalCorrectness(0, 0, 0, 0.0)
        self.hallucination_metrics = HallucinationMetrics(0, 0, 0, 0.0)
        self.risk_detection = RiskDetectionMetrics(0, 0, 0, 0, 0, 0.0)
    
    def evaluate_citation_accuracy(
        self,
        actual_citations: List[Dict],
        expected_citations: List[Dict]
    ) -> CitationAccuracy:
        """
        Evaluate citation accuracy.
        
        Args:
            actual_citations: Citations from system response
            expected_citations: Expected citations from golden query
            
        Returns:
            CitationAccuracy metrics
        """
        expected_doc_ids = {c.get("doc_id") for c in expected_citations if c.get("doc_id")}
        actual_doc_ids = {c.get("docId") for c in actual_citations if c.get("docId")}
        
        correct = len(expected_doc_ids & actual_doc_ids)
        incorrect = len(actual_doc_ids - expected_doc_ids)
        missing = len(expected_doc_ids - actual_doc_ids)
        total = len(expected_doc_ids) if expected_doc_ids else len(actual_doc_ids)
        
        accuracy = correct / total if total > 0 else 0.0
        
        self.citation_accuracy = CitationAccuracy(
            total_citations=total,
            correct_citations=correct,
            incorrect_citations=incorrect,
            missing_citations=missing,
            accuracy=accuracy
        )
        
        return self.citation_accuracy
    
    def evaluate_authority_correctness(
        self,
        actual_citations: List[Dict],
        expected_citations: List[Dict]
    ) -> AuthorityCorrectness:
        """
        Evaluate authority correctness.
        
        Checks if authority claims (Supreme Court, High Court, etc.) are correct.
        """
        # Build authority map from expected citations
        expected_authorities = {}
        for c in expected_citations:
            doc_id = c.get("doc_id")
            authority = c.get("authority")
            if doc_id and authority:
                expected_authorities[doc_id] = authority
        
        # Check actual citations
        correct = 0
        incorrect = 0
        
        for actual in actual_citations:
            doc_id = actual.get("docId")
            authority = actual.get("authority")
            
            if doc_id in expected_authorities:
                if authority == expected_authorities[doc_id]:
                    correct += 1
                else:
                    incorrect += 1
        
        total = len(expected_authorities)
        accuracy = correct / total if total > 0 else 0.0
        
        self.authority_correctness = AuthorityCorrectness(
            total_authority_claims=total,
            correct_authority_claims=correct,
            incorrect_authority_claims=incorrect,
            accuracy=accuracy
        )
        
        return self.authority_correctness
    
    def evaluate_temporal_correctness(
        self,
        actual_citations: List[Dict],
        expected_citations: List[Dict]
    ) -> TemporalCorrectness:
        """
        Evaluate temporal correctness.
        
        Checks if dates in citations are correct.
        """
        # Build date map from expected citations
        expected_dates = {}
        for c in expected_citations:
            doc_id = c.get("doc_id")
            date = c.get("date")
            if doc_id and date:
                # Extract year from date
                year = str(date)[:4] if len(str(date)) >= 4 else str(date)
                expected_dates[doc_id] = year
        
        # Check actual citations
        correct = 0
        incorrect = 0
        
        for actual in actual_citations:
            doc_id = actual.get("docId")
            date = actual.get("date")
            
            if doc_id in expected_dates and date:
                actual_year = str(date)[:4] if len(str(date)) >= 4 else str(date)
                if actual_year == expected_dates[doc_id]:
                    correct += 1
                else:
                    incorrect += 1
        
        total = len(expected_dates)
        accuracy = correct / total if total > 0 else 0.0
        
        self.temporal_correctness = TemporalCorrectness(
            total_date_references=total,
            correct_date_references=correct,
            incorrect_date_references=incorrect,
            accuracy=accuracy
        )
        
        return self.temporal_correctness
    
    def evaluate_hallucination(
        self,
        answer: str,
        retrieved_chunks: List,
        threshold: float = 0.7
    ) -> HallucinationMetrics:
        """
        Evaluate hallucination rate.
        
        Checks if claims in answer are supported by retrieved chunks.
        Uses simple keyword matching - in production, use semantic similarity.
        
        Args:
            answer: Generated answer text
            retrieved_chunks: Retrieved document chunks
            threshold: Similarity threshold for support (not used in simple version)
        """
        # Simple heuristic: check if key terms from answer appear in chunks
        # In production, use semantic similarity or LLM-based verification
        
        answer_lower = answer.lower()
        chunk_texts = " ".join([
            chunk.content if hasattr(chunk, 'content') else str(chunk)
            for chunk in retrieved_chunks
        ]).lower()
        
        # Extract key claims (simplified - just sentences)
        sentences = answer.split('.')
        total_claims = len([s for s in sentences if len(s.strip()) > 20])
        
        supported = 0
        for sentence in sentences:
            if len(sentence.strip()) < 20:
                continue
            
            # Check if sentence keywords appear in chunks
            sentence_words = set(sentence.lower().split())
            sentence_words = {w for w in sentence_words if len(w) > 3}  # Filter short words
            
            if sentence_words:
                # Check if at least 30% of keywords appear in chunks
                matches = sum(1 for w in sentence_words if w in chunk_texts)
                if matches / len(sentence_words) >= 0.3:
                    supported += 1
        
        unsupported = total_claims - supported
        hallucination_rate = unsupported / total_claims if total_claims > 0 else 0.0
        
        self.hallucination_metrics = HallucinationMetrics(
            total_claims=total_claims,
            supported_claims=supported,
            unsupported_claims=unsupported,
            hallucination_rate=hallucination_rate
        )
        
        return self.hallucination_metrics
    
    def evaluate_risk_detection(
        self,
        actual_risk_level: str,
        expected_risk_level: Optional[str]
    ) -> RiskDetectionMetrics:
        """
        Evaluate risk detection accuracy.
        
        Args:
            actual_risk_level: Risk level from system
            expected_risk_level: Expected risk level from golden query
        """
        if expected_risk_level is None:
            # No expected risk - can't evaluate
            return self.risk_detection
        
        self.risk_detection.total_queries += 1
        
        if actual_risk_level == expected_risk_level:
            self.risk_detection.correct_risk_assessments += 1
        else:
            self.risk_detection.incorrect_risk_assessments += 1
            
            # Check for false positives/negatives
            risk_levels = ["none", "low", "medium", "high", "critical"]
            actual_idx = risk_levels.index(actual_risk_level) if actual_risk_level in risk_levels else -1
            expected_idx = risk_levels.index(expected_risk_level) if expected_risk_level in risk_levels else -1
            
            if expected_idx == 0 and actual_idx > 0:  # Expected none, got risk
                self.risk_detection.false_positives += 1
            elif expected_idx > 0 and actual_idx == 0:  # Expected risk, got none
                self.risk_detection.false_negatives += 1
        
        # Update accuracy
        if self.risk_detection.total_queries > 0:
            self.risk_detection.accuracy = (
                self.risk_detection.correct_risk_assessments / 
                self.risk_detection.total_queries
            )
        
        return self.risk_detection
    
    def get_summary(self) -> Dict:
        """Get summary of all metrics"""
        return {
            "citation_accuracy": self.citation_accuracy.to_dict(),
            "authority_correctness": self.authority_correctness.to_dict(),
            "temporal_correctness": self.temporal_correctness.to_dict(),
            "hallucination_metrics": self.hallucination_metrics.to_dict(),
            "risk_detection": self.risk_detection.to_dict(),
            "overall_score": self._calculate_overall_score()
        }
    
    def _calculate_overall_score(self) -> float:
        """Calculate overall evaluation score"""
        weights = {
            "citation_accuracy": 0.3,
            "authority_correctness": 0.25,
            "temporal_correctness": 0.15,
            "hallucination": 0.2,  # Lower is better, so invert
            "risk_detection": 0.1
        }
        
        citation_score = self.citation_accuracy.accuracy
        authority_score = self.authority_correctness.accuracy
        temporal_score = self.temporal_correctness.accuracy
        hallucination_score = 1.0 - self.hallucination_metrics.hallucination_rate
        risk_score = self.risk_detection.accuracy
        
        overall = (
            citation_score * weights["citation_accuracy"] +
            authority_score * weights["authority_correctness"] +
            temporal_score * weights["temporal_correctness"] +
            hallucination_score * weights["hallucination"] +
            risk_score * weights["risk_detection"]
        )
        
        return overall

