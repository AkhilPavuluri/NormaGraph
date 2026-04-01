"""
Main API Entry Point

FastAPI server with ADK routing and streaming.
"""
import os
import logging
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from normagraph_core.integration.adk_integration import create_adk_orchestrator
from normagraph_core.api.streaming_api import StreamingRAGAPI
import uvicorn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Create FastAPI app with ADK orchestrator"""
    
    # Create orchestrator
    use_adk = os.getenv("USE_ADK_ROUTER", "True").lower() == "true"
    orchestrator = create_adk_orchestrator(use_adk=use_adk)
    
    # Create API
    api = StreamingRAGAPI(orchestrator)
    
    logger.info(f"API created (ADK: {use_adk})")
    return api.app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "normagraph_core.api.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

