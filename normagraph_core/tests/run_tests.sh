#!/bin/bash
# Run all integration tests

echo "Running Integration Tests..."
echo "============================"

# Test 1: Service Integration
echo ""
echo "1. Testing Service Integration..."
python -m pytest normagraph_core/tests/test_integration.py::TestServiceIntegration -v

# Test 2: ADK Routing
echo ""
echo "2. Testing ADK Routing..."
python -m pytest normagraph_core/tests/test_integration.py::TestADKRouting -v

# Test 3: End-to-End
echo ""
echo "3. Testing End-to-End Processing..."
python -m pytest normagraph_core/tests/test_integration.py::TestEndToEnd -v

# Test 4: Observability
echo ""
echo "4. Testing Observability..."
python -m pytest normagraph_core/tests/test_integration.py::TestObservability -v

echo ""
echo "============================"
echo "Tests Complete!"

