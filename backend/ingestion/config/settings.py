"""
Configuration settings for ingestion_v2 pipeline.

Clean, minimal, centralized configuration.
"""
from pathlib import Path
from typing import Dict, List
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from project root (3 levels up from this file)
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️  .env file not found at {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed - .env file will not be loaded")
except Exception as e:
    print(f"⚠️  Error loading .env file: {e}")

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "backend" / "ingestion" / "output"

# ============================================================================
# VERTICALS
# ============================================================================
VERTICALS = ["go", "legal", "judicial", "data", "scheme"]

# ============================================================================
# EXTRACTION SETTINGS
# ============================================================================
# OCR
ENABLE_OCR = True
OCR_CONFIDENCE_THRESHOLD = 0.3  # Pages below this score get OCR
MIN_WORDS_PER_PAGE = 10  # Minimum words to consider text extraction successful

# PDF Extraction
USE_PDFPLUMBER = True  # Primary extraction method
FALLBACK_TO_PYPDF = True  # Fallback if pdfplumber fails

# ============================================================================
# CHUNKING SETTINGS
# ============================================================================
# Vertical-specific chunk sizes (in characters)
CHUNK_SIZES = {
    "go": {"min": 800, "max": 1200, "overlap": 100},
    "legal": {"min": 600, "max": 1000, "overlap": 100},
    "judicial": {"min": 1000, "max": 1500, "overlap": 150},
    "data": {"min": 500, "max": 900, "overlap": 80},
    "scheme": {"min": 700, "max": 1100, "overlap": 100},
}

# ============================================================================
# LLM SETTINGS
# ============================================================================
# Use LLM sparingly - only where absolutely necessary
USE_LLM_FOR_CLASSIFICATION = True  # Document classification
USE_LLM_FOR_RELATIONS = True  # Complex relation extraction
USE_LLM_FOR_ENTITIES = True  # Enabled for complex GOs and legal docs
USE_LLM_FOR_CHUNKING = False  # Deterministic chunking is better

# Gemini API
# Check both GEMINI_API_KEY and GOOGLE_API_KEY (common aliases)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = "models/gemini-2.5-flash"  # Using project-specific gemini-2.5-flash alias
GEMINI_MAX_RETRIES = 3
GEMINI_TIMEOUT = 30

# ============================================================================
# QDRANT SETTINGS
# ============================================================================
# Support both QDRANT_URL (full URL) and separate HOST/PORT
QDRANT_URL = os.getenv("QDRANT_URL", "")
if QDRANT_URL:
    # Parse URL if provided
    from urllib.parse import urlparse
    parsed = urlparse(QDRANT_URL)
    QDRANT_HOST = parsed.hostname or "localhost"
    QDRANT_PORT = parsed.port or 6333
else:
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))

QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)

# Collection names
QDRANT_COLLECTIONS = {
    "go": "government_orders",
    "legal": "legal_documents",
    "judicial": "judicial_documents",
    "data": "data_reports",
    "scheme": "schemes",
}

# ============================================================================
# EMBEDDING SETTINGS
# ============================================================================
# Embedding settings - using Google API for lighter resource usage
EMBEDDING_PROVIDER = "google"  # "local" or "google"
EMBEDDING_MODEL = "models/text-embedding-004"  # Google's high-performance model
EMBEDDING_DIMENSION = 768

# Fallback local model if Google API fails
LOCAL_EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
BATCH_SIZE = 32  # For batch embedding

# ============================================================================
# QUALITY CONTROL
# ============================================================================
MIN_TEXT_QUALITY_SCORE = 20  # Out of 100
MIN_CHUNK_WORDS = 20  # Minimum words in a chunk
MAX_CHUNK_WORDS = 500  # Maximum words in a chunk

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "logs" / "ingestion_v2.log"

# ============================================================================
# LLM ENABLED VERTICALS
# ============================================================================
LLM_ENABLED_VERTICALS = {"go", "legal", "judicial"}
RELATION_ENABLED_VERTICALS = {"go", "legal", "judicial"}

# ============================================================================
# VALIDATION
# ============================================================================
def validate_settings():
    """Validate settings at startup."""
    errors = []
    
    if USE_LLM_FOR_CLASSIFICATION or USE_LLM_FOR_RELATIONS:
        # Check for Vertex AI credentials
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not project_id and not creds and not GEMINI_API_KEY:
             import logging
             logger = logging.getLogger(__name__)
             logger.warning("No Google Credentials found (Project ID or API Key) - LLM features may fail")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    return True


def validate_config():
    """Alias for validate_settings for backward compatibility."""
    return validate_settings()