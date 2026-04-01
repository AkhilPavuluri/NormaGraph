"""
Google Embedding API client for ingestion pipeline.
Reuses the retrieval embedder so embeddings stay consistent.
"""

from typing import List, Union

from retrieval_v3.embeddings.embedder import get_embedder as get_retrieval_embedder


class GoogleEmbedder:
    """Thin wrapper that proxies to the shared retrieval embedder"""
    
    def __init__(self):
        self._embedder = get_retrieval_embedder()
    
    def embed_texts(self, texts: Union[str, List[str]]):
        """Embed text(s) using the shared embedder"""
        model_type = "fast"
        return self._embedder.embed(texts, model_type)
    
    def embed_query(self, query: str, model_type: str = "fast"):
        """Embed a single query"""
        return self._embedder.embed_query(query, model_type)
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension for the default model"""
        return self._embedder.get_embedding_dim("fast")
    
    @property
    def is_using_google(self) -> bool:
        """Expose whether the underlying embedder is using Google API"""
        return getattr(self._embedder, "_backend", "lite") == "google"


_embedder = None


def get_embedder() -> GoogleEmbedder:
    """Get the global ingestion embedder"""
    global _embedder
    if _embedder is None:
        _embedder = GoogleEmbedder()
    return _embedder
