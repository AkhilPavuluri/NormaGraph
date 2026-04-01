"""
Metadata Retrieval Utility
===========================
Retrieve full metadata from JSON store when needed.
Use this after Qdrant retrieval to enrich results.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

METADATA_STORE_DIR = "metadata_store"


class MetadataRetriever:
    """Retrieve full metadata from JSON store"""
    
    def __init__(self, store_dir: str = METADATA_STORE_DIR):
        self.store_dir = Path(store_dir)
        if not self.store_dir.exists():
            raise ValueError(f"Metadata store not found: {store_dir}")
    
    def get_full_metadata(self, doc_id: str, chunk_id: str) -> Optional[Dict]:
        """
        Retrieve full metadata for a specific chunk.
        
        Args:
            doc_id: Document ID
            chunk_id: Chunk ID
            
        Returns:
            Full metadata dict or None if not found
        """
        metadata_file = self.store_dir / doc_id / f"{chunk_id}.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata for {doc_id}/{chunk_id}: {e}")
            return None
    
    def enrich_qdrant_results(self, results: List[Dict]) -> List[Dict]:
        """
        Enrich Qdrant results with full metadata.
        
        Args:
            results: List of Qdrant results (each has payload with doc_id, chunk_id)
            
        Returns:
            Results enriched with full_metadata field
        """
        enriched = []
        
        for result in results:
            payload = result.get('payload', {})
            doc_id = payload.get('doc_id')
            chunk_id = payload.get('chunk_id')
            
            if doc_id and chunk_id:
                full_metadata = self.get_full_metadata(doc_id, chunk_id)
                if full_metadata:
                    result['full_metadata'] = full_metadata
            
            enriched.append(result)
        
        return enriched
    
    def get_all_entities(self, doc_id: str, chunk_id: str) -> List[Dict]:
        """Get all entities for a chunk"""
        metadata = self.get_full_metadata(doc_id, chunk_id)
        if metadata:
            return metadata.get('entities', [])
        return []
    
    def get_all_relations(self, doc_id: str, chunk_id: str) -> List[Dict]:
        """Get all relations for a chunk"""
        metadata = self.get_full_metadata(doc_id, chunk_id)
        if metadata:
            return metadata.get('relations', [])
        return []
    
    def get_table_data(self, doc_id: str, chunk_id: str) -> Optional[Dict]:
        """Get full table data if chunk is a table"""
        metadata = self.get_full_metadata(doc_id, chunk_id)
        if metadata and metadata.get('is_table'):
            return {
                'columns': metadata.get('columns', []),
                'row_count': metadata.get('row_count', 0),
                'table_source': metadata.get('table_source', ''),
                'data': metadata.get('table_data', [])
            }
        return None
    
    def search_by_entity_type(self, entity_type: str, max_results: int = 100) -> List[Dict]:
        """
        Search metadata store for chunks containing specific entity types.
        
        Note: This is a brute-force search. For production, consider indexing.
        """
        results = []
        
        for doc_dir in self.store_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            
            for metadata_file in doc_dir.glob("*.json"):
                if len(results) >= max_results:
                    break
                
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    entities = metadata.get('entities', [])
                    matching_entities = [
                        e for e in entities 
                        if isinstance(e, dict) and e.get('type') == entity_type
                    ]
                    
                    if matching_entities:
                        results.append({
                            'doc_id': doc_dir.name,
                            'chunk_id': metadata_file.stem,
                            'matching_entities': matching_entities,
                            'entity_count': len(matching_entities)
                        })
                
                except Exception:
                    continue
        
        return results


# Global instance
_retriever_instance = None


def get_metadata_retriever() -> MetadataRetriever:
    """Get global metadata retriever instance"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = MetadataRetriever()
    return _retriever_instance


# Usage examples
if __name__ == "__main__":
    retriever = get_metadata_retriever()
    
    # Example 1: Get full metadata for a specific chunk
    metadata = retriever.get_full_metadata(
        doc_id="legal_doc_001",
        chunk_id="chunk_0"
    )
    
    if metadata:
        print(f"Found {len(metadata.get('entities', []))} entities")
        print(f"Found {len(metadata.get('relations', []))} relations")
    
    # Example 2: Enrich Qdrant results
    # After Qdrant search:
    qdrant_results = [
        {
            'id': 'some_id',
            'score': 0.95,
            'payload': {
                'doc_id': 'legal_doc_001',
                'chunk_id': 'chunk_0',
                'text': 'Sample text...',
                'entity_count': 15,
                'relation_count': 8
            }
        }
    ]
    
    enriched_results = retriever.enrich_qdrant_results(qdrant_results)
    
    # Now each result has full_metadata:
    for result in enriched_results:
        if 'full_metadata' in result:
            full_entities = result['full_metadata'].get('entities', [])
            print(f"Full entities: {len(full_entities)}")
            for entity in full_entities[:3]:
                print(f"  - {entity.get('text')}: {entity.get('type')}")