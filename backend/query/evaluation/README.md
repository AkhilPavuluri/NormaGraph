# Evaluation Framework

## Overview

The evaluation framework measures the quality and accuracy of the legal policy RAG system across multiple dimensions:

1. **Citation Accuracy**: Are citations correct?
2. **Authority Correctness**: Are authority claims (SC, HC, etc.) accurate?
3. **Temporal Correctness**: Are date references correct?
4. **Hallucination Rate**: Are claims supported by retrieved documents?
5. **Risk Detection Accuracy**: Are risk assessments correct?

## Golden Queries

Golden queries are curated queries with known correct answers. They serve as the ground truth for evaluation.

### Structure

```json
{
  "query_id": "edu_001",
  "query": "What did NEP 2020 say about university autonomy?",
  "expected_answer": "NEP 2020 emphasizes enhanced autonomy...",
  "expected_citations": [
    {
      "doc_id": "nep_2020",
      "title": "National Education Policy 2020",
      "authority": "Ministry of Education",
      "date": "2020"
    }
  ],
  "expected_risk_level": "low",
  "query_type": "factual",
  "domain": "education",
  "temporal_context": {"date": 2020, "operator": "exact"},
  "notes": "Additional context"
}
```

### Creating Golden Queries

1. **Identify Key Queries**: Select representative queries from your domain
2. **Define Expected Answers**: Write correct answers with proper citations
3. **Specify Risk Levels**: Determine expected risk assessment
4. **Add Context**: Include temporal, jurisdictional context if relevant

### Example

```python
from query.evaluation.golden_queries import GoldenQuery, GoldenQuerySet

query = GoldenQuery(
    query_id="edu_001",
    query="What did NEP 2020 say about autonomy?",
    expected_answer="NEP 2020 emphasizes enhanced autonomy...",
    expected_citations=[...],
    expected_risk_level="low",
    query_type="factual",
    domain="education"
)

# Save to file
query_set = GoldenQuerySet([query])
query_set.save(Path("golden_queries.json"))
```

## Running Evaluation

### Command Line

```bash
# Evaluate with default golden queries
python -m query.evaluation.evaluator

# Evaluate with custom query file
python -m query.evaluation.evaluator --queries golden_queries.json --output results.json

# Evaluate subset of queries
python -m query.evaluation.evaluator --max 10
```

### Python API

```python
from query.evaluation.evaluator import RAGEvaluator
from query.evaluation.golden_queries import load_golden_queries
from pathlib import Path

# Load golden queries
golden_queries = load_golden_queries(Path("golden_queries.json"))

# Create evaluator
evaluator = RAGEvaluator()

# Run evaluation
results = evaluator.evaluate(golden_queries=golden_queries)

# Print summary
evaluator.print_summary(results)

# Save results
evaluator.save_results(results, Path("evaluation_results.json"))
```

## Metrics Explained

### Citation Accuracy

Measures if the system cites the correct documents.

- **Correct**: Citation doc_id matches expected doc_id
- **Incorrect**: Citation doc_id doesn't match any expected
- **Missing**: Expected citation not found in actual citations

**Formula**: `accuracy = correct_citations / total_expected_citations`

### Authority Correctness

Measures if authority claims (Supreme Court, High Court, etc.) are accurate.

- **Correct**: Authority matches expected authority for the document
- **Incorrect**: Authority doesn't match

**Formula**: `accuracy = correct_authority_claims / total_authority_claims`

### Temporal Correctness

Measures if dates in citations are correct.

- **Correct**: Date/year matches expected date
- **Incorrect**: Date doesn't match

**Formula**: `accuracy = correct_date_references / total_date_references`

### Hallucination Rate

Measures if claims in answers are supported by retrieved documents.

- **Supported**: Claim keywords appear in retrieved chunks
- **Unsupported**: Claim not found in retrieved chunks

**Formula**: `hallucination_rate = unsupported_claims / total_claims`

**Note**: Current implementation uses keyword matching. For production, use semantic similarity or LLM-based verification.

### Risk Detection Accuracy

Measures if risk assessments are correct.

- **Correct**: Risk level matches expected
- **False Positive**: Detected risk when none exists
- **False Negative**: Missed risk when it exists

**Formula**: `accuracy = correct_risk_assessments / total_queries`

## Evaluation Results

Results are saved as JSON with:

```json
{
  "evaluation_date": "2024-01-15T10:30:00",
  "total_queries": 10,
  "successful_queries": 10,
  "failed_queries": 0,
  "results": [...],
  "summary": {
    "citation_accuracy": {...},
    "authority_correctness": {...},
    "temporal_correctness": {...},
    "hallucination_metrics": {...},
    "risk_detection": {...},
    "overall_score": 0.85
  }
}
```

## Best Practices

1. **Diverse Query Set**: Include queries across all types (factual, comparative, risk, etc.)
2. **Domain Coverage**: Cover all policy domains (education, healthcare, etc.)
3. **Regular Evaluation**: Run evaluation after major changes
4. **Track Trends**: Monitor metrics over time
5. **Expert Review**: Have legal experts validate golden queries

## Improving Evaluation

### Better Hallucination Detection

Current implementation uses keyword matching. For production:

1. **Semantic Similarity**: Use embeddings to measure claim-document similarity
2. **LLM Verification**: Use LLM to verify if claim is supported
3. **Claim Extraction**: Extract structured claims from answers

### More Granular Metrics

1. **Citation Precision/Recall**: Separate precision and recall
2. **Authority Granularity**: Check court level, bench strength
3. **Temporal Granularity**: Check exact dates vs. years

### Domain-Specific Metrics

1. **Legal Precedent Accuracy**: For judicial queries
2. **Policy Evolution Tracking**: For comparative queries
3. **Constitutional Compliance**: For risk analysis queries

## Troubleshooting

### Low Citation Accuracy

- Check if document IDs match between ingestion and queries
- Verify Qdrant collections are populated
- Check retrieval top_k settings

### High Hallucination Rate

- Increase retrieval top_k
- Improve answer generation prompt
- Add more context to LLM

### Poor Risk Detection

- Review risk detection rules
- Add more risk signals
- Validate golden query risk levels

