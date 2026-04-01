"""
Layered Retrieval Strategy

Implements domain-aware layered retrieval:
- Layer 1: Primary domain (always retrieved)
- Layer 2: Binding constraints (constitutional, judicial)
- Layer 3: Impact domains (labor, finance, social justice)
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from backend.query.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk
from backend.query.domain.domain_detector import DomainDetector

logger = logging.getLogger(__name__)


@dataclass
class LayerRetrievalResult:
    """Result from layered retrieval"""
    layer_1_chunks: List[RetrievedChunk]  # Primary domain
    layer_2_chunks: List[RetrievedChunk]  # Binding constraints
    layer_3_chunks: List[RetrievedChunk]  # Impact domains
    all_chunks: List[RetrievedChunk]  # Combined and deduplicated
    strategy: Dict  # Retrieval strategy used


class LayeredRetriever:
    """
    Implements domain-aware layered retrieval.
    
    Retrieves documents in layers:
    1. Primary domain (always)
    2. Binding constraints (if detected)
    3. Impact domains (if triggered)
    """
    
    def __init__(
        self,
        hybrid_retriever: Optional[HybridRetriever] = None,
        domain_detector: Optional[DomainDetector] = None
    ):
        """
        Initialize layered retriever.
        
        Args:
            hybrid_retriever: HybridRetriever instance (creates new if None)
            domain_detector: DomainDetector instance (creates new if None)
        """
        self.hybrid_retriever = hybrid_retriever or HybridRetriever()
        self.domain_detector = domain_detector or DomainDetector()
    
    def retrieve_layered(
        self,
        query: str,
        query_embedding: List[float],
        query_type: Optional[str] = None,
        primary_domain: Optional[str] = None,
        top_k: int = 20,
        filters: Optional[Dict] = None,
        source_priorities: Optional[List[str]] = None
    ) -> LayerRetrievalResult:
        """
        Perform layered retrieval based on domain detection.
        
        Args:
            query: User query
            query_embedding: Query embedding vector
            query_type: Query classification type
            primary_domain: Known primary domain (e.g., "education")
            top_k: Total number of results to return
            filters: Additional filters
            source_priorities: Source type priorities
            
        Returns:
            LayerRetrievalResult with chunks from each layer
        """
        # Step 1: Detect domains
        detected_domains = self.domain_detector.detect_domains(
            query=query,
            query_type=query_type,
            primary_domain=primary_domain
        )
        
        # Step 2: Get retrieval strategy
        strategy = self.domain_detector.get_retrieval_strategy(detected_domains)
        
        logger.info(f"Domain detection: {len(detected_domains['all_domains'])} domains detected")
        logger.info(f"  Primary: {[d.domain for d in detected_domains['primary']]}")
        logger.info(f"  Binding: {[d.domain for d in detected_domains['binding_constraints']]}")
        logger.info(f"  Impact: {[d.domain for d in detected_domains['impact_domains']]}")
        
        # Step 3: Retrieve from each layer
        layer_1_chunks = []
        layer_2_chunks = []
        layer_3_chunks = []
        
        # Layer 1: Primary domain (always)
        if strategy["layer_1_verticals"]:
            layer_1_k = int(top_k * 0.5)  # 50% of results from primary
            layer_1_chunks = self.hybrid_retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=layer_1_k,
                verticals=strategy["layer_1_verticals"],
                filters=filters,
                source_priorities=source_priorities
            )
            logger.info(f"Layer 1 (primary): {len(layer_1_chunks)} chunks from {strategy['layer_1_verticals']}")
        
        # Layer 2: Binding constraints (if detected)
        if strategy["layer_2_verticals"] and strategy["has_binding_constraints"]:
            layer_2_k = int(top_k * 0.3)  # 30% from binding constraints
            layer_2_chunks = self.hybrid_retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=layer_2_k,
                verticals=strategy["layer_2_verticals"],
                filters=filters,
                source_priorities=["judicial", "legal"]  # Prioritize judicial/legal for constraints
            )
            logger.info(f"Layer 2 (binding): {len(layer_2_chunks)} chunks from {strategy['layer_2_verticals']}")
        
        # Layer 3: Impact domains (if detected)
        if strategy["layer_3_verticals"] and strategy["has_impact_domains"]:
            layer_3_k = int(top_k * 0.2)  # 20% from impact domains
            layer_3_chunks = self.hybrid_retriever.retrieve(
                query=query,
                query_embedding=query_embedding,
                top_k=layer_3_k,
                verticals=strategy["layer_3_verticals"],
                filters=filters,
                source_priorities=source_priorities
            )
            logger.info(f"Layer 3 (impact): {len(layer_3_chunks)} chunks from {strategy['layer_3_verticals']}")
        
        # Step 4: Combine and deduplicate
        all_chunks = self._combine_and_deduplicate(
            layer_1_chunks,
            layer_2_chunks,
            layer_3_chunks,
            top_k
        )
        
        logger.info(f"Layered retrieval complete: {len(all_chunks)} total chunks "
                   f"({len(layer_1_chunks)} L1, {len(layer_2_chunks)} L2, {len(layer_3_chunks)} L3)")
        
        return LayerRetrievalResult(
            layer_1_chunks=layer_1_chunks,
            layer_2_chunks=layer_2_chunks,
            layer_3_chunks=layer_3_chunks,
            all_chunks=all_chunks,
            strategy=strategy
        )
    
    def _combine_and_deduplicate(
        self,
        layer_1: List[RetrievedChunk],
        layer_2: List[RetrievedChunk],
        layer_3: List[RetrievedChunk],
        top_k: int
    ) -> List[RetrievedChunk]:
        """
        Combine chunks from all layers and deduplicate.
        
        Priority: Layer 1 > Layer 2 > Layer 3
        """
        seen_chunk_ids = set()
        combined = []
        
        # Add Layer 1 first (highest priority)
        for chunk in layer_1:
            chunk_id = chunk.chunk_id
            if chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                combined.append(chunk)
        
        # Add Layer 2 (medium priority)
        for chunk in layer_2:
            chunk_id = chunk.chunk_id
            if chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                combined.append(chunk)
        
        # Add Layer 3 (lower priority)
        for chunk in layer_3:
            chunk_id = chunk.chunk_id
            if chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk_id)
                combined.append(chunk)
        
        # Sort by score (descending) and limit
        combined.sort(key=lambda x: x.score, reverse=True)
        
        return combined[:top_k]

