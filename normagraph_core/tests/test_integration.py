"""
Integration Tests for ADK RAG System

Tests:
1. Service accessibility
2. ADK routing
3. End-to-end query processing
4. Observability
"""
import sys
import os
from pathlib import Path
import pytest
import time

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from normagraph_core.integration.adk_integration import create_adk_orchestrator, SERVICES_AVAILABLE
from normagraph_core.core.observability import get_observability_logger


class TestServiceIntegration:
    """Test backend service integration"""
    
    def test_services_available(self):
        """Test that backend services can be imported"""
        assert SERVICES_AVAILABLE, "Backend services should be available"
    
    def test_orchestrator_creation(self):
        """Test orchestrator can be created"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Backend services not available")
        
        orchestrator = create_adk_orchestrator(use_adk=False)
        assert orchestrator is not None
        assert orchestrator.use_adk == False


class TestADKRouting:
    """Test ADK router functionality"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for testing"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Backend services not available")
        return create_adk_orchestrator(use_adk=True)
    
    def test_router_timeout(self, orchestrator):
        """Test router respects timeout"""
        if not orchestrator.router:
            pytest.skip("ADK router not available")
        
        start = time.time()
        decision = orchestrator.router.route_query("test query")
        elapsed = (time.time() - start) * 1000
        
        assert elapsed < 500, f"Router should complete in <500ms, took {elapsed}ms"
        assert "pipeline" in decision
        assert "primary_domain" in decision
    
    def test_router_fallback(self, orchestrator):
        """Test router fallback mechanism"""
        if not orchestrator.router:
            pytest.skip("ADK router not available")
        
        # Router should always return a decision, even on error
        decision = orchestrator.router._get_fallback_decision()
        assert decision["pipeline"] is not None
        assert decision["fallback_used"] == True


class TestEndToEnd:
    """Test end-to-end query processing"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for testing"""
        if not SERVICES_AVAILABLE:
            pytest.skip("Backend services not available")
        return create_adk_orchestrator(use_adk=True)
    
    def test_simple_query(self, orchestrator):
        """Test simple factual query"""
        result = orchestrator.process_query(
            query="What is education policy?",
            force_pipeline=None  # Use ADK routing
        )
        
        assert "answer" in result
        assert "citations" in result
        assert "processing_trace" in result
        assert result["processing_trace"]["total_ms"] < 5000  # Should complete in <5s
    
    def test_without_adk(self, orchestrator):
        """Test query processing without ADK"""
        orchestrator.use_adk = False
        result = orchestrator.process_query(
            query="What is education policy?"
        )
        
        assert "answer" in result
        assert result["processing_trace"].get("adk_used") == False


class TestObservability:
    """Test observability logging"""
    
    def test_observability_logger(self):
        """Test observability logger works"""
        logger = get_observability_logger()
        assert logger is not None
    
    def test_metrics_collection(self):
        """Test metrics can be collected"""
        logger = get_observability_logger()
        metrics = logger.get_metrics()
        assert isinstance(metrics, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

