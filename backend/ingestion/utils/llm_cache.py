"""
LLM Response Cache
Simple file-based cache for LLM responses to avoid repeated API calls
"""
import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class LLMCache:
    """
    Simple file-based cache for LLM responses
    Uses content hash as key to ensure cache hits for identical inputs
    """
    
    def __init__(self, cache_dir: str = "cache/llm_responses"):
        """
        Initialize LLM cache
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats
        self.hits = 0
        self.misses = 0
        
        logger.info(f"LLM cache initialized at {cache_dir}")
    
    def _generate_key(self, content: str, model: str = "", task_type: str = "") -> str:
        """
        Generate cache key from content hash
        
        Args:
            content: Input content
            model: Model name
            task_type: Type of task (classification, relation_extraction, etc.)
            
        Returns:
            Cache key
        """
        # Create combined string for hashing
        combined = f"{task_type}:{model}:{content}"
        
        # Generate SHA-256 hash
        hash_object = hashlib.sha256(combined.encode('utf-8'))
        return hash_object.hexdigest()
    
    def get(
        self, 
        content: str, 
        model: str = "", 
        task_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response
        
        Args:
            content: Input content
            model: Model name
            task_type: Task type
            
        Returns:
            Cached response or None
        """
        try:
            key = self._generate_key(content, model, task_type)
            cache_file = self.cache_dir / f"{key}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                self.hits += 1
                logger.debug(f"Cache hit for {task_type} task")
                return cached_data
            else:
                self.misses += 1
                logger.debug(f"Cache miss for {task_type} task")
                return None
                
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            self.misses += 1
            return None
    
    def set(
        self, 
        content: str, 
        response: Dict[str, Any], 
        model: str = "", 
        task_type: str = ""
    ) -> bool:
        """
        Cache response
        
        Args:
            content: Input content
            response: LLM response to cache
            model: Model name
            task_type: Task type
            
        Returns:
            True if cached successfully
        """
        try:
            key = self._generate_key(content, model, task_type)
            cache_file = self.cache_dir / f"{key}.json"
            
            # Add metadata
            cache_data = {
                "response": response,
                "model": model,
                "task_type": task_type,
                "content_length": len(content),
                "cached_at": str(self._get_current_timestamp())
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Cached response for {task_type} task")
            return True
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def clear(self) -> bool:
        """
        Clear all cache files
        
        Returns:
            True if cleared successfully
        """
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.hits = 0
            self.misses = 0
            logger.info("Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        # Count cache files
        cache_files = list(self.cache_dir.glob("*.json"))
        total_cache_files = len(cache_files)
        
        # Calculate total cache size
        total_size = sum(f.stat().st_size for f in cache_files)
        total_size_mb = total_size / (1024 * 1024)
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "total_files": total_cache_files,
            "total_size_mb": f"{total_size_mb:.2f}",
            "cache_dir": str(self.cache_dir)
        }
    
    def cleanup_old_files(self, days_old: int = 30) -> int:
        """
        Remove cache files older than specified days
        
        Args:
            days_old: Remove files older than this many days
            
        Returns:
            Number of files removed
        """
        try:
            from datetime import datetime, timedelta
            cutoff_time = datetime.now() - timedelta(days=days_old)
            
            removed_count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                # Check file modification time
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_time < cutoff_time:
                    cache_file.unlink()
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} old cache files")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0


# Global cache instance
_cache_instance = None


def get_cache(cache_dir: str = "cache/llm_responses") -> LLMCache:
    """
    Get global cache instance
    
    Args:
        cache_dir: Cache directory
        
    Returns:
        LLM cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache(cache_dir)
    return _cache_instance