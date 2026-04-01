"""
Query Embedding System

Generates embeddings for queries using Google Vertex AI.
"""
import os
import logging
from typing import List, Union
import google.generativeai as genai
from google.cloud import aiplatform

from backend.query.config import get_config

logger = logging.getLogger(__name__)


class QueryEmbedder:
    """
    Generates embeddings for queries using Google Vertex AI.
    
    Uses the same model as ingestion for consistency.
    """
    
    def __init__(self):
        self.config = get_config()
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google AI client"""
        project_id = self.config["project_id"]
        location = self.config["location"]
        use_vertex = self.config["vertex_ai"]
        
        if use_vertex:
            # Initialize Vertex AI
            aiplatform.init(project=project_id, location=location)
            logger.info(f"Initialized Vertex AI for embeddings (project: {project_id})")
        else:
            # Use API key
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                logger.info("Initialized Google AI with API key")
            else:
                raise ValueError("Either Vertex AI credentials or API key required")
    
    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector (list of floats)
        """
        try:
            if self.config["vertex_ai"]:
                # Use Vertex AI Embeddings API
                try:
                    from vertexai.preview.language_models import TextEmbeddingModel
                    model = TextEmbeddingModel.from_pretrained(self.config["embedding_model"])
                    embeddings = model.get_embeddings([query])
                    return embeddings[0].values
                except ImportError:
                    # Fallback to REST API approach
                    from google.cloud import aiplatform_v1beta1
                    client = aiplatform_v1beta1.PredictionServiceClient()
                    endpoint = f"projects/{self.config['project_id']}/locations/{self.config['location']}/publishers/google/models/{self.config['embedding_model']}"
                    
                    instance = aiplatform_v1beta1.types.PredictRequest.Instance(
                        struct_value={
                            "task_type": "RETRIEVAL_QUERY",
                            "content": query
                        }
                    )
                    
                    response = client.predict(
                        endpoint=endpoint,
                        instances=[instance]
                    )
                    return list(response.predictions[0].embeddings.values)
            
            else:
                # Use Google Generative AI (Gemini) API
                import google.generativeai as genai
                
                # Note: Gemini doesn't have direct embedding API
                # For API key mode, you'd need to use a different service
                # or fall back to Vertex AI
                logger.warning("API key mode - falling back to Vertex AI embeddings")
                from vertexai.preview.language_models import TextEmbeddingModel
                model = TextEmbeddingModel.from_pretrained(self.config["embedding_model"])
                embeddings = model.get_embeddings([query])
                return embeddings[0].values
        
        except ImportError:
            # Fallback: try using the ingestion embedder if available
            try:
                from backend.ingestion.embedding.google_embedder import get_embedder
                embedder = get_embedder()
                return embedder.embed_query(query)
            except:
                logger.error("No embedding system available")
                raise ValueError("Embedding generation failed - check Vertex AI setup")
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def embed_batch(self, queries: List[str]) -> List[List[float]]:
        """
        Embed multiple queries in batch.
        
        Args:
            queries: List of query texts
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for query in queries:
            embeddings.append(self.embed_query(query))
        return embeddings

