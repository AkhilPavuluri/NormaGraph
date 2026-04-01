"""
Observability Layer (Phase 7)

Logging, metrics, and tracing for production monitoring.
"""
import os
import logging
import time
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class RequestTrace:
    """Request trace for observability"""
    request_id: str
    query: str
    timestamp: str
    routing_decision: Optional[Dict] = None
    pipeline_used: Optional[str] = None
    domains_used: Optional[list] = None
    adk_used: bool = False
    fallback_used: bool = False
    latency_ms: float = 0.0
    stage_latencies: Dict[str, float] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class ObservabilityLogger:
    """
    Production observability logger.
    
    Logs:
    - Agent decisions
    - Pipeline usage
    - Latency per stage
    - Fallbacks
    - Errors
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.traces = []
    
    def log_request(
        self,
        request_id: str,
        query: str,
        routing_decision: Dict,
        pipeline_result: Dict,
        latency_ms: float,
        stage_latencies: Dict[str, float]
    ):
        """Log a complete request"""
        
        trace = RequestTrace(
            request_id=request_id,
            query=query[:200],  # Truncate for logging
            timestamp=datetime.now().isoformat(),
            routing_decision=routing_decision,
            pipeline_used=pipeline_result.get("pipeline"),
            domains_used=pipeline_result.get("domains_used"),
            adk_used=routing_decision.get("adk_used", False),
            fallback_used=routing_decision.get("fallback_used", False),
            latency_ms=latency_ms,
            stage_latencies=stage_latencies
        )
        
        # Log to console
        logger.info(f"Request {request_id}: {trace.pipeline_used} pipeline, {latency_ms:.0f}ms")
        
        # Log to file if configured
        if self.log_file:
            self._write_trace(trace)
        
        self.traces.append(trace)
    
    def log_error(self, request_id: str, query: str, error: str, latency_ms: float):
        """Log an error"""
        trace = RequestTrace(
            request_id=request_id,
            query=query[:200],
            timestamp=datetime.now().isoformat(),
            error=error,
            latency_ms=latency_ms
        )
        
        logger.error(f"Request {request_id} failed: {error}")
        
        if self.log_file:
            self._write_trace(trace)
    
    def _write_trace(self, trace: RequestTrace):
        """Write trace to file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(trace.to_dict()) + '\n')
        except Exception as e:
            logger.warning(f"Failed to write trace: {e}")
    
    def get_metrics(self, last_n: int = 100) -> Dict:
        """Get metrics from last N requests"""
        recent = self.traces[-last_n:] if len(self.traces) > last_n else self.traces
        
        if not recent:
            return {}
        
        # Calculate metrics
        total = len(recent)
        adk_used = sum(1 for t in recent if t.adk_used)
        fallbacks = sum(1 for t in recent if t.fallback_used)
        errors = sum(1 for t in recent if t.error)
        
        avg_latency = sum(t.latency_ms for t in recent) / total if total > 0 else 0
        
        # Pipeline distribution
        pipeline_dist = {}
        for trace in recent:
            pipeline = trace.pipeline_used or "unknown"
            pipeline_dist[pipeline] = pipeline_dist.get(pipeline, 0) + 1
        
        return {
            "total_requests": total,
            "adk_usage_rate": adk_used / total if total > 0 else 0,
            "fallback_rate": fallbacks / total if total > 0 else 0,
            "error_rate": errors / total if total > 0 else 0,
            "avg_latency_ms": avg_latency,
            "pipeline_distribution": pipeline_dist
        }


# Global observability logger
_observability_logger = None

def get_observability_logger() -> ObservabilityLogger:
    """Get or create global observability logger"""
    global _observability_logger
    if _observability_logger is None:
        log_file = os.getenv("OBSERVABILITY_LOG_FILE", "normagraph_observability.log")
        _observability_logger = ObservabilityLogger(log_file=log_file)
    return _observability_logger

