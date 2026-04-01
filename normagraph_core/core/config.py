"""
Configuration for RAG System
"""
import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass


def get_config():
    """Get configuration dictionary"""
    return {
        "project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "",
        "location": os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1"),
        "qdrant_url": os.getenv("QDRANT_URL", "").strip(),
        "qdrant_api_key": os.getenv("QDRANT_API_KEY", ""),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "models/text-embedding-004"),
        "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "768")),
        "vertex_ai": os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").lower() == "true",
        "gemini_model": os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash"),
        "use_adk": os.getenv("USE_ADK_ROUTER", "True").lower() == "true",
        "adk_timeout_ms": int(os.getenv("ADK_TIMEOUT_MS", "300")),
    }

