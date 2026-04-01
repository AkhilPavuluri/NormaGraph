"""
SOTA Embedding Module
Using BGE-large-en-v1.5 - significantly better than old models
This is CRITICAL for retrieval quality
"""
import torch
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding operation"""
    chunk_id: str
    embedding: List[float]
    success: bool
    error: Optional[str] = None


class SOTAEmbedder:
    """
    State-of-the-art embedder using BGE-large-en-v1.5
    
    Why BGE-large?
    - SOTA performance on retrieval tasks
    - 1024-dim embeddings (vs 384 for MiniLM)
    - Much better semantic understanding
    - Optimized for long documents
    
    Key improvements over old system:
    1. Better model (BGE vs MiniLM)
    2. Proper normalization
    3. Batch processing
    4. Device optimization (GPU if available)
    5. Model caching (load once, reuse)
    """
    
    def __init__(
        self, 
        model_name: str = "BAAI/bge-large-en-v1.5",
        batch_size: int = 32,
        device: Optional[str] = None
    ):
        """
        Initialize embedder
        
        Args:
            model_name: Model to use (default: BGE-large-en-v1.5)
            batch_size: Batch size for embedding
            device: Device to use (cuda/cpu, auto-detected if None)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        logger.info(f"Initializing embedder with {model_name} on {self.device}")
        
        # Load model ONCE
        self.model = self._load_model()
        
        logger.info(f"✅ Embedder ready - dimension: {self.get_dimension()}")
    
    def _load_model(self) -> SentenceTransformer:
        """Load the embedding model"""
        try:
            model = SentenceTransformer(self.model_name, device=self.device)
            
            # Set to evaluation mode
            model.eval()
            
            return model
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()
    
    def embed_batch(
        self, 
        texts: List[str], 
        chunk_ids: List[str]
    ) -> List[EmbeddingResult]:
        """
        Embed a batch of texts
        
        Args:
            texts: List of texts to embed
            chunk_ids: Corresponding chunk IDs
            
        Returns:
            List of embedding results
        """
        if not texts:
            return []
        
        if len(texts) != len(chunk_ids):
            raise ValueError("texts and chunk_ids must have same length")
        
        results = []
        
        try:
            # For BGE models, add instruction prefix for better retrieval
            # This is the recommended practice for BGE models
            instruction = "Represent this document for retrieval: "
            texts_with_instruction = [instruction + text for text in texts]
            
            # Generate embeddings in batch
            embeddings = self.model.encode(
                texts_with_instruction,
                batch_size=self.batch_size,
                normalize_embeddings=True,  # CRITICAL: Normalize for cosine similarity
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Create results
            for chunk_id, embedding in zip(chunk_ids, embeddings):
                results.append(EmbeddingResult(
                    chunk_id=chunk_id,
                    embedding=embedding.tolist(),
                    success=True
                ))
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # Return failed results
            for chunk_id in chunk_ids:
                results.append(EmbeddingResult(
                    chunk_id=chunk_id,
                    embedding=[],
                    success=False,
                    error=str(e)
                ))
        
        return results
    
    def embed_single(self, text: str, chunk_id: str) -> EmbeddingResult:
        """Embed a single text (convenience method)"""
        results = self.embed_batch([text], [chunk_id])
        return results[0]
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Embed a list of chunk dictionaries
        
        Args:
            chunks: List of chunk dicts with 'content' and 'chunk_id'
            
        Returns:
            List of chunk dicts with 'embedding' added
        """
        if not chunks:
            return []
        
        # Extract texts and IDs
        texts = [chunk.get("content", "") for chunk in chunks]
        chunk_ids = [chunk.get("chunk_id", f"chunk_{i}") for i, _ in enumerate(chunks)]
        
        # Filter out empty texts
        valid_indices = [i for i, text in enumerate(texts) if text.strip()]
        valid_texts = [texts[i] for i in valid_indices]
        valid_ids = [chunk_ids[i] for i in valid_indices]
        
        if not valid_texts:
            logger.warning("No valid texts to embed")
            return chunks
        
        # Process in batches
        embedded_chunks = []
        
        for i in range(0, len(valid_texts), self.batch_size):
            batch_texts = valid_texts[i:i + self.batch_size]
            batch_ids = valid_ids[i:i + self.batch_size]
            batch_indices = valid_indices[i:i + self.batch_size]
            
            # Embed batch
            results = self.embed_batch(batch_texts, batch_ids)
            
            # Add embeddings to chunks
            for idx, result in zip(batch_indices, results):
                chunk = chunks[idx].copy()
                if result.success:
                    chunk["embedding"] = result.embedding
                    chunk["embedding_model"] = self.model_name
                else:
                    chunk["embedding"] = None
                    chunk["embedding_error"] = result.error
                
                embedded_chunks.append(chunk)
        
        # Add chunks that were skipped (empty text)
        skipped_indices = set(range(len(chunks))) - set(valid_indices)
        for idx in skipped_indices:
            chunk = chunks[idx].copy()
            chunk["embedding"] = None
            chunk["embedding_error"] = "Empty text"
            embedded_chunks.append(chunk)
        
        # Sort back to original order
        embedded_chunks.sort(key=lambda x: chunk_ids.index(x.get("chunk_id", "")))
        
        success_count = sum(1 for c in embedded_chunks if c.get("embedding") is not None)
        logger.info(f"Embedded {success_count}/{len(chunks)} chunks successfully")
        
        return embedded_chunks


class EmbeddingCache:
    """
    Simple embedding cache to avoid re-embedding
    Uses content hash as key
    """
    
    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, content: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = hash(content)
        return self.cache.get(key)
    
    def set(self, content: str, embedding: List[float]):
        """Cache embedding"""
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove oldest (first) item
            self.cache.pop(next(iter(self.cache)))
        
        key = hash(content)
        self.cache[key] = embedding
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()


# Global embedder instance (load once, reuse)
_global_embedder: Optional[SOTAEmbedder] = None


def get_embedder() -> SOTAEmbedder:
    """
    Get global embedder instance
    Loads model once and reuses it
    """
    global _global_embedder
    
    if _global_embedder is None:
        _global_embedder = SOTAEmbedder()
    
    return _global_embedder