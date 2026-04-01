# ADK RAG System - Testing Guide

## Running Tests

### Integration Tests

```bash
# Run all integration tests
python -m pytest normagraph_core/tests/test_integration.py -v

# Run specific test class
python -m pytest normagraph_core/tests/test_integration.py::TestServiceIntegration -v

# Run with coverage
python -m pytest normagraph_core/tests/test_integration.py --cov=normagraph_core --cov-report=html
```

### Load Tests

```bash
# Run load test with default settings (10 queries, 3 concurrent)
python normagraph_core/tests/test_load.py

# Run with custom settings
python normagraph_core/tests/test_load.py --queries 20 --concurrent 5
```

## Test Categories

### 1. Service Integration Tests
- Verify backend services are accessible
- Test Orchestrator creation
- Check service initialization

### 2. ADK Routing Tests
- Test router timeout (should be < 300ms)
- Test fallback mechanism
- Verify JSON schema compliance

### 3. End-to-End Tests
- Test complete query processing
- Verify response structure
- Check latency targets

### 4. Observability Tests
- Test logging functionality
- Verify metrics collection
- Check trace generation

## Expected Results

### Latency Targets
- Router: < 300ms
- Total: < 3500ms (P95)

### Success Rates
- Service Integration: 100%
- ADK Routing: > 95%
- End-to-End: > 90%

## Troubleshooting

### Services Not Available
If tests fail with "Backend services not available":
1. Check backend/query services exist
2. Verify Python path includes backend directory
3. Check service imports are correct

### ADK Router Timeout
If router tests fail:
1. Check Vertex AI credentials
2. Verify network connectivity
3. Check ADK timeout settings

### High Latency
If latency tests fail:
1. Check retrieval service performance
2. Verify LLM service is responsive
3. Check network latency

