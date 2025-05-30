"""
Caching Module

This module implements a flexible caching system for performance optimization.
It provides:
1. In-memory and Redis-based caching
2. Cache key management
3. TTL-based expiration
4. Cache invalidation
5. Cache statistics

The caching system helps reduce load on external services and
improve response times for frequently accessed data.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set, Union
import json
import logging
import redis
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

class CacheBackend(ABC):
    """
    Abstract base class for cache implementations.
    
    This defines the interface that all cache backends must implement,
    allowing for different storage mechanisms (memory, Redis, etc).
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Any]: Cached value if found
        """
        pass
        
    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Store value in cache.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
            ttl (Optional[int]): Time to live in seconds
        """
        pass
        
    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Remove value from cache.
        
        Args:
            key (str): Cache key to remove
        """
        pass
        
    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass

class MemoryCache(CacheBackend):
    """
    Simple in-memory cache implementation.
    
    This cache stores data in memory with optional TTL expiration.
    Useful for development and testing.
    """
    
    def __init__(self):
        """Initialize empty cache."""
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key not in self._cache:
            return None
            
        # Check expiration
        if key in self._expiry:
            if datetime.utcnow() > self._expiry[key]:
                self.delete(key)
                return None
                
        return self._cache[key]
        
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in memory cache."""
        self._cache[key] = value
        
        if ttl:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
            
    def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        
    def clear(self) -> None:
        """Clear memory cache."""
        self._cache.clear()
        self._expiry.clear()

class RedisCache(CacheBackend):
    """
    Redis-based cache implementation.
    
    This cache uses Redis for distributed caching with automatic
    TTL management and atomic operations.
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None
    ):
        """
        Initialize Redis connection.
        
        Args:
            host (str): Redis host
            port (int): Redis port
            db (int): Redis database number
            password (Optional[str]): Redis password
        """
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        value = self._redis.get(key)
        if value is None:
            return None
            
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
            
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set value in Redis."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
            
        if ttl:
            self._redis.setex(key, ttl, value)
        else:
            self._redis.set(key, value)
            
    def delete(self, key: str) -> None:
        """Delete value from Redis."""
        self._redis.delete(key)
        
    def clear(self) -> None:
        """Clear Redis cache."""
        self._redis.flushdb()

class CacheManager:
    """
    High-level cache management interface.
    
    This class provides:
    - Cache key generation
    - Multiple backend support
    - Cache statistics
    - Decorator support
    """
    
    def __init__(
        self,
        backend: CacheBackend,
        default_ttl: int = 3600,
        namespace: str = ""
    ):
        """
        Initialize cache manager.
        
        Args:
            backend (CacheBackend): Cache implementation
            default_ttl (int): Default TTL in seconds
            namespace (str): Key namespace
        """
        self._backend = backend
        self._default_ttl = default_ttl
        self._namespace = namespace
        self._hits = 0
        self._misses = 0
        
    def _make_key(self, key: str) -> str:
        """Generate namespaced cache key."""
        return f"{self._namespace}:{key}" if self._namespace else key
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            key (str): Cache key
            
        Returns:
            Optional[Any]: Cached value if found
        """
        full_key = self._make_key(key)
        value = self._backend.get(full_key)
        
        if value is None:
            self._misses += 1
        else:
            self._hits += 1
            
        return value
        
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Set cache value.
        
        Args:
            key (str): Cache key
            value (Any): Value to cache
            ttl (Optional[int]): Custom TTL in seconds
        """
        full_key = self._make_key(key)
        self._backend.set(full_key, value, ttl or self._default_ttl)
        
    def delete(self, key: str) -> None:
        """
        Delete cached value.
        
        Args:
            key (str): Cache key
        """
        full_key = self._make_key(key)
        self._backend.delete(full_key)
        
    def clear(self) -> None:
        """Clear all cached values."""
        self._backend.clear()
        self._hits = 0
        self._misses = 0
        
    @property
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total": total,
            "hit_rate": hit_rate
        }

def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    manager: Optional[CacheManager] = None
):
    """
    Cache decorator for function results.
    
    Args:
        key_prefix (str): Prefix for cache keys
        ttl (Optional[int]): Custom TTL in seconds
        manager (Optional[CacheManager]): Cache manager instance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not manager:
                return func(*args, **kwargs)
                
            # Generate cache key from arguments
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Check cache
            result = manager.get(cache_key)
            if result is not None:
                return result
                
            # Execute function and cache result
            result = func(*args, **kwargs)
            manager.set(cache_key, result, ttl)
            return result
            
        return wrapper
    return decorator 