#!/usr/bin/env python3
"""
Evaluation Script

Run evaluation of the legal policy RAG system.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from backend.query.evaluation.evaluator import run_evaluation
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate NormaGraph query pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default golden queries
  python scripts/run_evaluation.py
  
  # Run with custom query file
  python scripts/run_evaluation.py --queries data/golden_queries.json
  
  # Run subset and save results
  python scripts/run_evaluation.py --max 5 --output results.json
        """
    )
    
    parser.add_argument(
        "--queries",
        type=str,
        help="Path to golden queries JSON file"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="evaluation_results.json",
        help="Path to save evaluation results (default: evaluation_results.json)"
    )
    
    parser.add_argument(
        "--max",
        type=int,
        help="Maximum number of queries to evaluate"
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    results = run_evaluation(
        query_file=Path(args.queries) if args.queries else None,
        output_file=Path(args.output),
        max_queries=args.max
    )
    
    print(f"\n✅ Evaluation complete. Results saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

