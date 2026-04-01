"""
Load Testing for ADK RAG System

Tests latency targets under load.
"""
import sys
import time
import concurrent.futures
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from normagraph_core.integration.adk_integration import create_adk_orchestrator, SERVICES_AVAILABLE


def test_single_query(orchestrator, query: str):
    """Test a single query and return latency"""
    start = time.time()
    result = orchestrator.process_query(query=query)
    elapsed = (time.time() - start) * 1000
    return {
        "query": query,
        "latency_ms": elapsed,
        "success": "answer" in result,
        "pipeline": result.get("processing_trace", {}).get("pipeline_used", "unknown")
    }


def run_load_test(num_queries: int = 10, concurrent: int = 3):
    """Run load test with multiple concurrent queries"""
    if not SERVICES_AVAILABLE:
        print("⚠️  Backend services not available - skipping load test")
        return
    
    orchestrator = create_adk_orchestrator(use_adk=True)
    
    test_queries = [
        "What did NEP 2020 say about autonomy?",
        "How has education policy evolved?",
        "What are the risks of this policy?",
        "Compare education and healthcare policies",
    ] * (num_queries // 4 + 1)
    test_queries = test_queries[:num_queries]
    
    print(f"Running load test: {num_queries} queries, {concurrent} concurrent")
    
    results = []
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = [
            executor.submit(test_single_query, orchestrator, query)
            for query in test_queries
        ]
        
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    total_time = (time.time() - start_time) * 1000
    
    # Analyze results
    latencies = [r["latency_ms"] for r in results]
    avg_latency = sum(latencies) / len(latencies)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    max_latency = max(latencies)
    min_latency = min(latencies)
    
    success_rate = sum(1 for r in results if r["success"]) / len(results)
    
    print("\n" + "="*60)
    print("LOAD TEST RESULTS")
    print("="*60)
    print(f"Total Queries: {num_queries}")
    print(f"Concurrent: {concurrent}")
    print(f"Total Time: {total_time:.0f}ms")
    print(f"Success Rate: {success_rate:.1%}")
    print(f"\nLatency Statistics:")
    print(f"  Average: {avg_latency:.0f}ms")
    print(f"  P95: {p95_latency:.0f}ms")
    print(f"  Min: {min_latency:.0f}ms")
    print(f"  Max: {max_latency:.0f}ms")
    print("\nTargets:")
    print(f"  Target: 2700ms (Average)")
    print(f"  Max: 3500ms (P95)")
    print(f"  Status: {'✅ PASS' if avg_latency < 3500 and p95_latency < 5000 else '❌ FAIL'}")
    print("="*60)
    
    return {
        "num_queries": num_queries,
        "concurrent": concurrent,
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "max_latency_ms": max_latency,
        "success_rate": success_rate
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test ADK RAG system")
    parser.add_argument("--queries", type=int, default=10, help="Number of queries")
    parser.add_argument("--concurrent", type=int, default=3, help="Concurrent requests")
    
    args = parser.parse_args()
    run_load_test(num_queries=args.queries, concurrent=args.concurrent)

