"""
Evaluation utilities for the NormaGraph query pipeline.

Measures:
- Citation accuracy
- Authority correctness
- Temporal correctness
- Hallucination rate
- Risk detection accuracy
"""

from backend.query.evaluation.evaluator import RAGEvaluator
from backend.query.evaluation.metrics import EvaluationMetrics
from backend.query.evaluation.golden_queries import GoldenQuery, load_golden_queries

__all__ = ["RAGEvaluator", "EvaluationMetrics", "GoldenQuery", "load_golden_queries"]

