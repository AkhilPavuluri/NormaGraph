#!/usr/bin/env python3
"""
Production Flagship Data Embedding & Upload Script - FINAL
===========================================================
Merges all sidecar metadata (entities, relations, structure) into chunks.
Complete metadata in Qdrant for LLM context - no two-tier complexity.
Simple, fast, production-ready.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, PayloadSchemaType
import logging
from datetime import datetime
import math

# Load environment variables - try to load from root or use dotenv
try:
    import sys
    root_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(root_path))
    from load_env import load_backend_env
    load_backend_env()
except ImportError:
    # Fallback to dotenv
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass  # dotenv not available, will use environment variables directly
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

# Add paths for imports
import sys
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Import from backend.ingestion config
from backend.ingestion.config import settings as ingestion_config

OUTPUT_DIR = ingestion_config.OUTPUT_DIR
VERTICALS = ingestion_config.VERTICALS
EMBEDDING_PROVIDER = ingestion_config.EMBEDDING_PROVIDER
EMBEDDING_MODEL = ingestion_config.EMBEDDING_MODEL

from backend.ingestion.embedding.google_embedder import get_embedder
from backend.ingestion.config.vertical_map import (
    get_collection_name, get_all_collections
)

# Configuration
EMBED_BATCH_SIZE = 32
UPLOAD_BATCH_SIZE = 25  # Reduced from 100 to prevent 33MB payload limit errors
MAX_RETRIES = 3
MAX_TEXT_LENGTH = 20000  # Safety limit for Google API
CHECKPOINT_FILE = "upload_progress.json"
METRICS_FILE = "upload_metrics.json"
FAILED_CHUNKS_FILE = "failed_chunks.jsonl"

# Google API rate limiting
GOOGLE_REQUESTS_PER_MINUTE = 1500  # Adjust based on your tier
GOOGLE_BATCH_ENABLED = True

@dataclass
class UploadMetrics:
    """Track upload metrics"""
    chunks_total: int = 0
    chunks_embedded: int = 0
    chunks_uploaded: int = 0
    embedding_failures: int = 0
    upload_failures: int = 0
    total_characters: int = 0
    total_cost: float = 0.0
    start_time: float = 0
    collections_created: int = 0

def setup_logging():
    """Setup comprehensive logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('flagship_upload.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def setup_qdrant():
    """Setup Qdrant client with validation"""
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        collections = client.get_collections()
        logging.info(f"✅ Connected to Qdrant. Found {len(collections.collections)} existing collections.")
        return client
    except Exception as e:
        logging.error(f"❌ Failed to connect to Qdrant: {e}")
        raise

def load_sidecar_metadata(doc_dir: Path) -> Dict:
    """
    Load all sidecar metadata files (entities, relations, structure, etc.)
    from the document directory.
    
    Returns merged metadata dict.
    """
    metadata = {}
    
    # Define sidecar files to load
    sidecar_files = {
        'entities': 'entities.json',
        'relations': 'relations.json',
        'structure': 'structure.json',
        'metadata': 'metadata.json',
        'tables': 'tables.json',
        'statistics': 'statistics.json'
    }
    
    for key, filename in sidecar_files.items():
        filepath = doc_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata[key] = data
                    logging.debug(f"      ✓ Loaded {filename}")
            except Exception as e:
                logging.warning(f"      ⚠️ Could not load {filename}: {e}")
    
    return metadata

def merge_sidecar_into_chunks(chunks: List[Dict], doc_dir: Path) -> List[Dict]:
    """
    Merge sidecar metadata into chunks.
    
    Args:
        chunks: List of chunks from chunks.jsonl
        doc_dir: Document directory containing sidecar files
        
    Returns:
        Chunks with enriched metadata
    """
    # Load all sidecar metadata once
    sidecar = load_sidecar_metadata(doc_dir)
    
    if not sidecar:
        logging.debug(f"      ℹ️ No sidecar metadata found in {doc_dir.name}")
        return chunks
    
    # Merge into each chunk
    for chunk in chunks:
        meta = chunk.get('metadata', {})
        
        # Merge entities
        if 'entities' in sidecar:
            entities_data = sidecar['entities']
            if isinstance(entities_data, dict):
                # If entities.json has chunk-specific data
                chunk_entities = entities_data.get(chunk['chunk_id'], [])
            else:
                # If entities.json is a flat list (doc-level)
                chunk_entities = entities_data if isinstance(entities_data, list) else []
            
            meta['entities'] = chunk_entities
            meta['entity_count'] = len(chunk_entities)
            # Extract entity types
            entity_types = list(set([e.get('type', 'unknown') for e in chunk_entities if isinstance(e, dict)]))
            meta['entity_types'] = entity_types
        
        # Merge relations
        if 'relations' in sidecar:
            relations_data = sidecar['relations']
            if isinstance(relations_data, dict):
                chunk_relations = relations_data.get(chunk['chunk_id'], [])
            else:
                chunk_relations = relations_data if isinstance(relations_data, list) else []
            
            meta['relations'] = chunk_relations
            meta['relation_count'] = len(chunk_relations)
            meta['has_relations'] = "true" if len(chunk_relations) > 0 else "false"
            # Extract relation types
            relation_types = list(set([r.get('type', 'unknown') for r in chunk_relations if isinstance(r, dict)]))
            meta['relation_types'] = relation_types
        
        # Merge structure info
        if 'structure' in sidecar:
            structure = sidecar['structure']
            if isinstance(structure, dict):
                for key, value in structure.items():
                    if key not in meta:
                        meta[key] = value
        
        # Merge general metadata
        if 'metadata' in sidecar:
            general_meta = sidecar['metadata']
            if isinstance(general_meta, dict):
                for key, value in general_meta.items():
                    if key not in meta:
                        meta[key] = value
        
        # Merge table info
        if 'tables' in sidecar:
            tables = sidecar['tables']
            if isinstance(tables, dict):
                chunk_tables = tables.get(chunk['chunk_id'], {})
                if chunk_tables:
                    meta['is_table'] = "true"
                    meta.update(chunk_tables)
            elif isinstance(tables, list) and tables:
                # If tables is a list, merge first table
                meta['is_table'] = "true"
                if isinstance(tables[0], dict):
                    meta.update(tables[0])
        
        # Merge statistics
        if 'statistics' in sidecar:
            stats = sidecar['statistics']
            if isinstance(stats, dict):
                meta['statistics'] = stats
        
        chunk['metadata'] = meta
    
    return chunks

def load_chunks_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load chunks from jsonl file and merge sidecar metadata.
    
    This is the KEY function that enriches chunks with all processed metadata.
    """
    chunks = []
    doc_dir = file_path.parent
    
    # Load chunks from JSONL
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        chunk = json.loads(line)
                        required_fields = ['text', 'doc_id', 'chunk_id']
                        if all(field in chunk for field in required_fields):
                            # Skip chunks with empty or whitespace-only text
                            if not chunk['text'] or not chunk['text'].strip():
                                logging.warning(f"⚠️ Skipping empty chunk at {file_path}:{line_no}")
                                continue
                            # Initialize metadata if missing
                            if 'metadata' not in chunk:
                                chunk['metadata'] = {}
                            chunks.append(chunk)
                        else:
                            logging.warning(f"⚠️ Invalid chunk at {file_path}:{line_no}")
                    except json.JSONDecodeError as e:
                        logging.warning(f"⚠️ JSON error at {file_path}:{line_no}: {e}")
    except Exception as e:
        logging.error(f"❌ Error loading {file_path}: {e}")
        return []
    
    if not chunks:
        return []
    
    # Merge sidecar metadata into chunks
    logging.info(f"      🔗 Merging sidecar metadata from {doc_dir.name}")
    enriched_chunks = merge_sidecar_into_chunks(chunks, doc_dir)
    
    # Log enrichment stats
    entity_counts = [len(c.get('metadata', {}).get('entities', [])) for c in enriched_chunks]
    relation_counts = [len(c.get('metadata', {}).get('relations', [])) for c in enriched_chunks]
    
    if entity_counts:
        logging.info(f"      📊 Entities: {sum(entity_counts)} total, avg {sum(entity_counts)/len(entity_counts):.1f} per chunk")
    if relation_counts:
        logging.info(f"      📊 Relations: {sum(relation_counts)} total, avg {sum(relation_counts)/len(relation_counts):.1f} per chunk")
    
    return enriched_chunks

def create_complete_payload(chunk: Dict) -> Dict:
    """
    Create COMPLETE payload with ALL metadata for LLM context.
    No two-tier - everything in Qdrant.
    """
    metadata = chunk.get('metadata', {})
    
    # Truncate text for embedding safety (but keep full text reference)
    text = chunk.get('text', '')
    full_text = text
    if len(text) > 8000:  # Keep reasonable length for payload
        text = text[:8000] + "..."
    
    payload = {
        # Core identifiers
        "doc_id": chunk['doc_id'],
        "chunk_id": chunk['chunk_id'],
        "text": text,
        
        # Chunk info
        "chunk_index": chunk.get('chunk_index', 0),
        "word_count": chunk.get('word_count', len(text.split())),
        "char_count": len(full_text),
        
        # Vertical info
        "vertical": metadata.get('vertical', 'unknown'),
        "doc_type": metadata.get('doc_type', 'unknown'),
    }
    
    # Add ALL metadata fields directly (no summarization)
    for key, value in metadata.items():
        if key in payload:
            continue  # Skip duplicates
        
        # Handle complex types
        if isinstance(value, (list, dict)):
            # Keep as-is - Qdrant supports nested structures
            payload[key] = value
        else:
            payload[key] = value
    
    # Ensure critical fields exist (for filtering) - unified string flags
    payload.setdefault('entity_count', 0)
    payload.setdefault('relation_count', 0)
    payload.setdefault('has_relations', "false")
    payload.setdefault('entity_types', [])
    payload.setdefault('relation_types', [])
    
    # Standardize common operational flags if present as booleans
    for flag in ['is_most_recent', 'is_superseded', 'is_current', 'overrides_by_date', 'is_table', 'has_table']:
        if flag in payload and isinstance(payload[flag], bool):
            payload[flag] = "true" if payload[flag] else "false"
    
    return {k: v for k, v in payload.items() if v is not None}

def ensure_collection_exists(client: QdrantClient, vertical: str):
    """Ensure collection exists with correct schema AND payload indexes"""
    try:
        collection_name = get_collection_name(vertical)
        # Use default vector params for now
        from qdrant_client.models import VectorParams, Distance
        vector_params = VectorParams(size=768, distance=Distance.COSINE)
        
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if collection_name in existing:
            collection_info = client.get_collection(collection_name)
            current_size = collection_info.config.params.vectors.size
            if current_size != vector_params.size:
                logging.warning(f"🔧 Collection {collection_name} has wrong vector size. Recreating...")
                client.delete_collection(collection_name)
                time.sleep(2)
                existing.remove(collection_name)
            else:
                logging.info(f"✅ Collection {collection_name} exists")
                
                # CRITICAL FIX: Ensure payload indexes exist
                try:
                    _ensure_payload_indexes(client, collection_name, vertical)
                except Exception as e:
                    logging.warning(f"⚠️ Could not create payload indexes: {e}")
                
                return collection_name
        
        if collection_name not in existing:
            logging.info(f"🆕 Creating collection: {collection_name}")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=vector_params
            )
            logging.info(f"✅ Created: {collection_name} (dim={vector_params.size})")
            
            # CRITICAL FIX: Create payload indexes immediately
            try:
                _ensure_payload_indexes(client, collection_name, vertical)
                logging.info(f"✅ Created payload indexes for {collection_name}")
            except Exception as e:
                logging.error(f"❌ Failed to create payload indexes: {e}")
                
        return collection_name
        
    except Exception as e:
        logging.error(f"❌ Failed to ensure collection: {e}")
        raise


def _ensure_payload_indexes(client: QdrantClient, collection_name: str, vertical: str):
    """
    CRITICAL FIX: Create payload indexes for filterable fields.
    
    This is THE KEY FIX for the 57.1% → 100% improvement.
    Without this, Qdrant can't filter on list fields like 'sections'.
    """
    
    # Comprehensive Index List from create_qdrant_indexes.py
    common_indexes = [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("vertical", PayloadSchemaType.KEYWORD),
        ("mentioned_gos", PayloadSchemaType.KEYWORD),
        ("mentioned_sections", PayloadSchemaType.KEYWORD),
        ("departments", PayloadSchemaType.KEYWORD),
        ("schemes", PayloadSchemaType.KEYWORD),
        ("acts", PayloadSchemaType.KEYWORD),
        ("rules", PayloadSchemaType.KEYWORD),
        ("relations[].type", PayloadSchemaType.KEYWORD),
        ("relations[].relation_type", PayloadSchemaType.KEYWORD),
        ("has_relations", PayloadSchemaType.KEYWORD),
        ("anchor_id", PayloadSchemaType.KEYWORD),
        ("year", PayloadSchemaType.INTEGER),
        ("date_issued_ts", PayloadSchemaType.INTEGER),
        ("legal_weight", PayloadSchemaType.FLOAT),
        ("authority_weight", PayloadSchemaType.FLOAT),
        ("is_superseded", PayloadSchemaType.KEYWORD),
        ("is_most_recent", PayloadSchemaType.KEYWORD),
        ("is_current", PayloadSchemaType.KEYWORD),
    ]

    # Vertical-specific additions
    index_fields = {
        "legal": [
            ("section_type", PayloadSchemaType.KEYWORD),
            ("chapter", PayloadSchemaType.KEYWORD),
            ("part", PayloadSchemaType.KEYWORD),
            ("structural_confidence", PayloadSchemaType.FLOAT),
        ],
        "go": [
            ("go_number", PayloadSchemaType.KEYWORD),
            ("primary_domain", PayloadSchemaType.KEYWORD),
            ("policy_domains", PayloadSchemaType.KEYWORD),
            # GO-specific logical entities
            ("go_effect", PayloadSchemaType.KEYWORD),
            ("legal_effect", PayloadSchemaType.KEYWORD),
            ("applicability_scope", PayloadSchemaType.KEYWORD),
            ("beneficiary_scope", PayloadSchemaType.KEYWORD),
            ("authority_level", PayloadSchemaType.KEYWORD),
            ("financial_impact", PayloadSchemaType.KEYWORD),
            ("policy_domain", PayloadSchemaType.KEYWORD),
            # Geographic entities
            ("districts", PayloadSchemaType.KEYWORD),
            ("mandals", PayloadSchemaType.KEYWORD),
            ("villages", PayloadSchemaType.KEYWORD),
            # Beneficiary entities
            ("beneficiary_orgs", PayloadSchemaType.KEYWORD),
            ("beneficiary_types", PayloadSchemaType.KEYWORD),
            # Financial entities
            ("financial_commitment", PayloadSchemaType.KEYWORD),
            ("budget_head", PayloadSchemaType.KEYWORD),
        ],
        "judicial": [
            ("court_level", PayloadSchemaType.KEYWORD),
            ("binding_scope", PayloadSchemaType.KEYWORD),
            ("jurisdiction", PayloadSchemaType.KEYWORD),
            ("petition_result", PayloadSchemaType.KEYWORD),
            ("order_type", PayloadSchemaType.KEYWORD),
            ("court", PayloadSchemaType.KEYWORD),
            ("case_number", PayloadSchemaType.KEYWORD),
        ],
        "data": [
            ("data_intent", PayloadSchemaType.KEYWORD),
            ("contains_financials", PayloadSchemaType.KEYWORD),
            ("numeric_confidence", PayloadSchemaType.KEYWORD),
        ],
        "schemes": [
            ("scheme_name", PayloadSchemaType.KEYWORD),
        ]
    }
    
    fields_to_index = common_indexes + index_fields.get(vertical, [])
    
    for field_name, field_type in fields_to_index:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=field_type,
                wait=True
            )
            logging.info(f"   ✅ Indexed: {field_name} ({field_type})")
        except Exception as e:
            # Index might already exist, that's okay
            if "already exists" not in str(e).lower():
                logging.warning(f"   ⚠️ Could not index {field_name}: {e}")

def generate_stable_id(doc_id: str, chunk_id: str) -> str:
    """Generate stable UUID for Qdrant"""
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}|{chunk_id}"))

def validate_embedding_quality(embedding: List[float]) -> Tuple[bool, str]:
    """Validate embedding is not corrupt"""
    if all(x == 0 for x in embedding):
        return False, "all_zeros"
    if any(not math.isfinite(x) for x in embedding):
        return False, "nan_or_inf"
    magnitude = sum(x*x for x in embedding) ** 0.5
    if magnitude < 0.01:
        return False, "magnitude_too_small"
    if magnitude > 100:
        return False, "magnitude_too_large"
    return True, "valid"

def calculate_embedding_cost(chunks: List[Dict]) -> Tuple[int, float]:
    """Calculate embedding cost"""
    total_chars = sum(len(chunk['text']) for chunk in chunks)
    cost = (total_chars / 1000) * 0.00001  # Google pricing
    return total_chars, cost

def calculate_rate_limit_delay() -> float:
    """Calculate delay between API calls"""
    if GOOGLE_BATCH_ENABLED:
        delay = 60.0 / GOOGLE_REQUESTS_PER_MINUTE
    else:
        delay = (60.0 / GOOGLE_REQUESTS_PER_MINUTE) * EMBED_BATCH_SIZE
    return delay * 1.1

def save_failed_chunk(chunk: Dict, reason: str):
    """Save failed chunk for retry"""
    with open(FAILED_CHUNKS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({
            "doc_id": chunk.get('doc_id'),
            "chunk_id": chunk.get('chunk_id'),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }) + '\n')

def embed_chunks_with_retries(
    embedder, 
    chunks: List[Dict], 
    batch_size: int,
    metrics: UploadMetrics
) -> Tuple[List[Dict], List[List[float]]]:
    """Embed chunks with validation and retry logic"""
    all_embeddings = []
    successful_chunks = []
    rate_limit_delay = calculate_rate_limit_delay()
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(chunks) - 1) // batch_size + 1
        
        chars, cost = calculate_embedding_cost(batch)
        metrics.total_characters += chars
        metrics.total_cost += cost
        
        logging.info(f"   🔄 Batch {batch_num}/{total_batches} ({len(batch)} chunks, ${cost:.6f})")
        
        # Truncate texts for API safety
        texts = []
        for chunk in batch:
            text = chunk['text']
            if len(text) > MAX_TEXT_LENGTH:
                text = text[:MAX_TEXT_LENGTH] + "..."
                logging.debug(f"      ✂️ Truncated text for {chunk['chunk_id']}")
            texts.append(text)
        
        batch_embeddings = None
        
        # Retry logic
        for attempt in range(MAX_RETRIES):
            try:
                batch_embeddings = embedder.embed_texts(texts)
                
                # Validate
                expected_dim = embedder.embedding_dimension
                valid_embeddings = []
                valid_chunks = []
                
                for j, embedding in enumerate(batch_embeddings):
                    if len(embedding) != expected_dim:
                        raise ValueError(f"Wrong dimension: {len(embedding)} vs {expected_dim}")
                    
                    is_valid, reason = validate_embedding_quality(embedding)
                    if not is_valid:
                        logging.warning(f"   ⚠️ Bad embedding: {reason}")
                        save_failed_chunk(batch[j], f"quality_{reason}")
                        metrics.embedding_failures += 1
                        continue
                    
                    valid_embeddings.append([float(x) for x in embedding])
                    valid_chunks.append(batch[j])
                
                batch_embeddings = valid_embeddings
                batch = valid_chunks
                
                if len(batch_embeddings) == 0:
                    raise ValueError("All embeddings failed quality check")
                
                break
                
            except Exception as e:
                wait_time = 2 ** attempt
                logging.warning(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    logging.info(f"   ⏳ Retry in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"   ❌ All retries failed")
                    for chunk in batch:
                        save_failed_chunk(chunk, f"embed_failed_after_{MAX_RETRIES}_retries")
                    metrics.embedding_failures += len(batch)
                    batch_embeddings = None
        
        if batch_embeddings and len(batch_embeddings) > 0:
            all_embeddings.extend(batch_embeddings)
            successful_chunks.extend(batch)
            logging.info(f"   ✅ Embedded {len(batch_embeddings)} chunks")
        
        # Rate limiting
        if embedder.is_using_google and batch_num < total_batches:
            time.sleep(rate_limit_delay)
    
    return successful_chunks, all_embeddings

def upload_with_retries(client: QdrantClient, collection_name: str, points: List[PointStruct]) -> bool:
    """Upload with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            client.upsert(collection_name=collection_name, points=points)
            return True
        except Exception as e:
            wait_time = 2 ** attempt
            logging.warning(f"   ⚠️ Upload attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait_time)
            else:
                return False

def upload_to_qdrant(
    client: QdrantClient, 
    collection_name: str, 
    chunks: List[Dict], 
    embeddings: List,
    metrics: UploadMetrics
) -> int:
    """Upload chunks with complete metadata"""
    points = []
    
    for chunk, embedding in zip(chunks, embeddings):
        point_id = generate_stable_id(chunk['doc_id'], chunk['chunk_id'])
        payload = create_complete_payload(chunk)
        
        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload=payload
        ))
    
    # Upload in batches
    uploaded = 0
    for i in range(0, len(points), UPLOAD_BATCH_SIZE):
        batch = points[i:i + UPLOAD_BATCH_SIZE]
        batch_num = i // UPLOAD_BATCH_SIZE + 1
        total_batches = (len(points) - 1) // UPLOAD_BATCH_SIZE + 1
        
        if upload_with_retries(client, collection_name, batch):
            uploaded += len(batch)
            logging.info(f"   ✅ Uploaded batch {batch_num}/{total_batches}")
        else:
            logging.error(f"   ❌ Failed batch {batch_num}")
            metrics.upload_failures += len(batch)
    
    return uploaded

def load_progress() -> Dict:
    """Load checkpoint"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_progress(progress: Dict):
    """Save checkpoint"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def get_all_chunk_files() -> Dict[str, List[Path]]:
    """Get all chunk files by vertical"""
    output_dir = Path(OUTPUT_DIR)
    chunk_files_by_vertical = {}
    
    for vertical in VERTICALS:
        vertical_dir = output_dir / vertical
        if vertical_dir.exists():
            chunk_files = list(vertical_dir.glob("*/chunks.jsonl"))
            vertical_key = "schemes" if vertical == "scheme" else vertical
            chunk_files_by_vertical[vertical_key] = chunk_files
            logging.info(f"📁 {vertical_key}: {len(chunk_files)} files")
    
    return chunk_files_by_vertical

def save_metrics(metrics: UploadMetrics):
    """Save final metrics"""
    duration = time.time() - metrics.start_time
    
    with open(METRICS_FILE, 'w') as f:
        json.dump({
            "chunks_total": metrics.chunks_total,
            "chunks_embedded": metrics.chunks_embedded,
            "chunks_uploaded": metrics.chunks_uploaded,
            "embedding_failures": metrics.embedding_failures,
            "upload_failures": metrics.upload_failures,
            "total_characters": metrics.total_characters,
            "total_cost_usd": round(metrics.total_cost, 4),
            "duration_seconds": round(duration, 2),
            "chunks_per_second": round(metrics.chunks_uploaded / duration, 2) if duration > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)

def main():
    """Main execution"""
    setup_logging()
    metrics = UploadMetrics()
    metrics.start_time = time.time()
    
    logging.info("🚀 Starting FINAL embedding & upload with sidecar metadata merge")
    
    try:
        embedder = get_embedder()
        client = setup_qdrant()
        progress = load_progress()
        logging.info(f"🔍 Debug: Progress dict has {len(progress)} entries")
        if len(progress) > 0:
            logging.info(f"🔍 Debug: First few progress entries: {list(progress.items())[:3]}")
        
        logging.info(f"📡 Model: {EMBEDDING_MODEL} ({embedder.embedding_dimension}d)")
        logging.info(f"📊 Batches: embed={EMBED_BATCH_SIZE}, upload={UPLOAD_BATCH_SIZE}")
        logging.info(f"💾 Storage: Complete metadata in Qdrant (entities, relations, all fields)")
        
        chunk_files_by_vertical = get_all_chunk_files()
        
        if not chunk_files_by_vertical:
            logging.error("❌ No chunk files found!")
            return
        
        total_files = sum(len(files) for files in chunk_files_by_vertical.values())
        logging.info(f"📊 Found {total_files} files across {len(chunk_files_by_vertical)} verticals")
        
        # Process each vertical
        for vertical, chunk_files in chunk_files_by_vertical.items():
            if not chunk_files:
                continue
            
            try:
                collection_name = get_collection_name(vertical)
            except ValueError:
                logging.warning(f"Unknown vertical: {vertical}, skipping")
                continue
            
            logging.info(f"\n🎯 Processing: {vertical} → {collection_name}")
            ensure_collection_exists(client, vertical)
            metrics.collections_created += 1
            
            for chunk_file in chunk_files:
                # FIX: Use document directory name, not just "chunks.jsonl"
                doc_id = chunk_file.parent.name
                file_key = f"{vertical}:{doc_id}"
                progress_value = progress.get(file_key, 0)
                logging.info(f"🔍 Debug: {file_key} -> progress value: {progress_value}")
                
                if progress_value > 0:
                    logging.info(f"   ⏭️ Skip: {doc_id} (already processed)")
                    continue
                
                logging.info(f"   📖 Loading: {doc_id}/chunks.jsonl")
                chunks = load_chunks_from_file(chunk_file)
                
                if not chunks:
                    continue
                
                metrics.chunks_total += len(chunks)
                logging.info(f"      📊 {len(chunks)} chunks loaded")
                
                # Embed
                logging.info(f"   🧠 Embedding...")
                chunks_ok, embeddings = embed_chunks_with_retries(
                    embedder, chunks, EMBED_BATCH_SIZE, metrics
                )
                
                metrics.chunks_embedded += len(embeddings)
                
                if not embeddings:
                    continue
                
                # Upload
                logging.info(f"   ☁️ Uploading {len(embeddings)} chunks...")
                uploaded = upload_to_qdrant(
                    client, collection_name, chunks_ok, embeddings, metrics
                )
                metrics.chunks_uploaded += uploaded
                
                progress[file_key] = uploaded
                save_progress(progress)
                
                logging.info(f"   ✅ Done: {uploaded} chunks, ${metrics.total_cost:.4f} total")
        
        # Final summary
        logging.info("\n🎉 Upload complete!")
        logging.info(f"💰 Cost: ${metrics.total_cost:.4f}")
        logging.info(f"📊 Characters: {metrics.total_characters:,}")
        
        collections = client.get_collections()
        logging.info(f"\n📈 Collections:")
        for col in collections.collections:
            if col.name in get_all_collections():
                try:
                    count = client.count(col.name)
                    logging.info(f"   {col.name}: {count.count} points")
                except:
                    pass
        
        save_metrics(metrics)
        
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        
        if os.path.exists(FAILED_CHUNKS_FILE):
            with open(FAILED_CHUNKS_FILE, 'r') as f:
                failed = sum(1 for _ in f)
            if failed > 0:
                logging.warning(f"⚠️ {failed} chunks failed - see {FAILED_CHUNKS_FILE}")
        
        logging.info(f"\n✅ Final: {metrics.chunks_uploaded}/{metrics.chunks_total} uploaded")
            
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        save_metrics(metrics)
        raise

if __name__ == "__main__":
    main()