"""
RAG System Evaluator

Evaluates the legal policy RAG system against golden queries.
"""
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

from backend.query.orchestrator import QueryOrchestrator
from backend.query.evaluation.golden_queries import GoldenQuerySet, GoldenQuery, load_golden_queries
from backend.query.evaluation.metrics import EvaluationMetrics

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    Evaluates RAG system performance against golden queries.
    
    Measures:
    - Citation accuracy
    - Authority correctness
    - Temporal correctness
    - Hallucination rate
    - Risk detection accuracy
    """
    
    def __init__(self, orchestrator: Optional[QueryOrchestrator] = None):
        self.orchestrator = orchestrator or QueryOrchestrator()
        self.metrics = EvaluationMetrics()
    
    def evaluate(
        self,
        golden_queries: Optional[GoldenQuerySet] = None,
        query_file: Optional[Path] = None,
        max_queries: Optional[int] = None
    ) -> Dict:
        """
        Evaluate system against golden queries.
        
        Args:
            golden_queries: GoldenQuerySet to evaluate against
            query_file: Path to JSON file with golden queries
            max_queries: Maximum number of queries to evaluate
            
        Returns:
            Dict with evaluation results
        """
        # Load golden queries
        if golden_queries is None:
            if query_file:
                golden_queries = load_golden_queries(query_file)
            else:
                golden_queries = load_golden_queries()
        
        queries = golden_queries.queries
        if max_queries:
            queries = queries[:max_queries]
        
        logger.info(f"Evaluating system against {len(queries)} golden queries")
        
        # Reset metrics
        self.metrics = EvaluationMetrics()
        
        results = []
        
        for i, golden_query in enumerate(queries, 1):
            logger.info(f"[{i}/{len(queries)}] Evaluating: {golden_query.query_id}")
            
            try:
                # Process query
                response = self.orchestrator.process_query(
                    query=golden_query.query,
                    filters=golden_query.temporal_context
                )
                
                # Evaluate response
                query_result = self._evaluate_single_query(
                    golden_query=golden_query,
                    response=response
                )
                
                results.append(query_result)
                
            except Exception as e:
                logger.error(f"Error evaluating query {golden_query.query_id}: {e}")
                results.append({
                    "query_id": golden_query.query_id,
                    "error": str(e),
                    "success": False
                })
        
        # Build summary
        summary = self.metrics.get_summary()
        
        return {
            "evaluation_date": datetime.now().isoformat(),
            "total_queries": len(queries),
            "successful_queries": len([r for r in results if r.get("success", False)]),
            "failed_queries": len([r for r in results if not r.get("success", True)]),
            "results": results,
            "summary": summary
        }
    
    def _evaluate_single_query(
        self,
        golden_query: GoldenQuery,
        response: Dict
    ) -> Dict:
        """
        Evaluate a single query response.
        
        Args:
            golden_query: Golden query with expected results
            response: System response
            
        Returns:
            Evaluation result for this query
        """
        # Extract response components
        answer = response.get("answer", "")
        citations = response.get("citations", [])
        risk_assessment = response.get("risk_assessment", {})
        retrieved_chunks = response.get("_retrieved_chunks", [])  # If available
        
        # Evaluate citation accuracy
        citation_metrics = self.metrics.evaluate_citation_accuracy(
            actual_citations=citations,
            expected_citations=golden_query.expected_citations
        )
        
        # Evaluate authority correctness
        authority_metrics = self.metrics.evaluate_authority_correctness(
            actual_citations=citations,
            expected_citations=golden_query.expected_citations
        )
        
        # Evaluate temporal correctness
        temporal_metrics = self.metrics.evaluate_temporal_correctness(
            actual_citations=citations,
            expected_citations=golden_query.expected_citations
        )
        
        # Evaluate hallucination (if we have retrieved chunks)
        # Note: We'd need to pass retrieved_chunks from orchestrator
        # For now, skip if not available
        hallucination_metrics = None
        if retrieved_chunks:
            hallucination_metrics = self.metrics.evaluate_hallucination(
                answer=answer,
                retrieved_chunks=retrieved_chunks
            )
        
        # Evaluate risk detection
        actual_risk = risk_assessment.get("level", "none")
        risk_metrics = self.metrics.evaluate_risk_detection(
            actual_risk_level=actual_risk,
            expected_risk_level=golden_query.expected_risk_level
        )
        
        # Build result
        result = {
            "query_id": golden_query.query_id,
            "query": golden_query.query,
            "success": True,
            "citation_accuracy": citation_metrics.to_dict(),
            "authority_correctness": authority_metrics.to_dict(),
            "temporal_correctness": temporal_metrics.to_dict(),
            "risk_detection": {
                "actual": actual_risk,
                "expected": golden_query.expected_risk_level,
                "correct": actual_risk == golden_query.expected_risk_level
            }
        }
        
        if hallucination_metrics:
            result["hallucination"] = hallucination_metrics.to_dict()
        
        return result
    
    def save_results(self, results: Dict, filepath: Path):
        """Save evaluation results to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved evaluation results to {filepath}")
    
    def print_summary(self, results: Dict):
        """Print evaluation summary"""
        summary = results["summary"]
        
        print("\n" + "="*80)
        print("EVALUATION SUMMARY")
        print("="*80)
        print(f"Total Queries: {results['total_queries']}")
        print(f"Successful: {results['successful_queries']}")
        print(f"Failed: {results['failed_queries']}")
        print()
        
        print("Citation Accuracy:")
        ca = summary["citation_accuracy"]
        print(f"  Accuracy: {ca['accuracy']:.2%} ({ca['correct_citations']}/{ca['total_citations']})")
        print(f"  Missing: {ca['missing_citations']}, Incorrect: {ca['incorrect_citations']}")
        print()
        
        print("Authority Correctness:")
        ac = summary["authority_correctness"]
        print(f"  Accuracy: {ac['accuracy']:.2%} ({ac['correct_authority_claims']}/{ac['total_authority_claims']})")
        print()
        
        print("Temporal Correctness:")
        tc = summary["temporal_correctness"]
        print(f"  Accuracy: {tc['accuracy']:.2%} ({tc['correct_date_references']}/{tc['total_date_references']})")
        print()
        
        print("Hallucination Metrics:")
        hm = summary["hallucination_metrics"]
        print(f"  Hallucination Rate: {hm['hallucination_rate']:.2%}")
        print(f"  Supported Claims: {hm['supported_claims']}/{hm['total_claims']}")
        print()
        
        print("Risk Detection:")
        rd = summary["risk_detection"]
        print(f"  Accuracy: {rd['accuracy']:.2%} ({rd['correct_risk_assessments']}/{rd['total_queries']})")
        print(f"  False Positives: {rd['false_positives']}, False Negatives: {rd['false_negatives']}")
        print()
        
        print("Overall Score:")
        print(f"  {summary['overall_score']:.2%}")
        print("="*80)


def run_evaluation(
    query_file: Optional[Path] = None,
    output_file: Optional[Path] = None,
    max_queries: Optional[int] = None
):
    """
    Run evaluation and save results.
    
    Args:
        query_file: Path to golden queries JSON file
        output_file: Path to save evaluation results
        max_queries: Maximum queries to evaluate
    """
    evaluator = RAGEvaluator()
    
    results = evaluator.evaluate(
        query_file=query_file,
        max_queries=max_queries
    )
    
    evaluator.print_summary(results)
    
    if output_file:
        evaluator.save_results(results, Path(output_file))
    else:
        # Save to default location
        output_file = Path("evaluation_results.json")
        evaluator.save_results(results, output_file)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate RAG system")
    parser.add_argument("--queries", type=str, help="Path to golden queries JSON file")
    parser.add_argument("--output", type=str, help="Path to save evaluation results")
    parser.add_argument("--max", type=int, help="Maximum queries to evaluate")
    
    args = parser.parse_args()
    
    run_evaluation(
        query_file=Path(args.queries) if args.queries else None,
        output_file=Path(args.output) if args.output else None,
        max_queries=args.max
    )

