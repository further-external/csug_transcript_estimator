"""
Rate Limiting Module

This module implements API rate limiting and request throttling.
It provides:
1. Token bucket rate limiting
2. Per-user and global limits
3. Limit customization
4. Limit tracking
5. Limit violation handling

The rate limiting system helps protect APIs from abuse while
ensuring fair resource allocation among users.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import time
import logging
import redis
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class RateLimit:
    """
    Rate limit configuration.
    
    Attributes:
        requests (int): Number of allowed requests
        window (int): Time window in seconds
        burst (int): Maximum burst size
    """
    requests: int
    window: int
    burst: Optional[int] = None

class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    This implements the token bucket algorithm for rate limiting,
    allowing for bursts while maintaining average rate limits.
    """
    
    def __init__(
        self,
        rate: float,
        capacity: int,
        initial_tokens: Optional[int] = None
    ):
        """
        Initialize token bucket.
        
        Args:
            rate (float): Token refill rate per second
            capacity (int): Maximum token capacity
            initial_tokens (int): Initial token count
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.last_update = time.time()
        
    def update(self) -> None:
        """Update token count based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.rate
        )
        self.last_update = now
        
    def try_consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens (int): Number of tokens to consume
            
        Returns:
            bool: True if tokens were consumed
        """
        self.update()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class RedisRateLimiter:
    """
    Redis-based distributed rate limiter.
    
    This implements rate limiting using Redis for distributed
    environments, with atomic operations and TTL management.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "ratelimit"
    ):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_client (redis.Redis): Redis client
            key_prefix (str): Key prefix for Redis
        """
        self._redis = redis_client
        self._prefix = key_prefix
        
    def _make_key(self, key: str) -> str:
        """Generate Redis key with prefix."""
        return f"{self._prefix}:{key}"
        
    def is_allowed(
        self,
        key: str,
        limit: RateLimit
    ) -> Tuple[bool, Dict]:
        """
        Check if request is allowed.
        
        Args:
            key (str): Rate limit key
            limit (RateLimit): Rate limit config
            
        Returns:
            Tuple[bool, Dict]: (allowed, limit info)
        """
        redis_key = self._make_key(key)
        now = int(time.time())
        window_start = now - limit.window
        
        # Use pipeline for atomic operations
        pipe = self._redis.pipeline()
        
        # Remove old requests
        pipe.zremrangebyscore(redis_key, 0, window_start)
        
        # Count requests in window
        pipe.zcard(redis_key)
        
        # Add current request
        pipe.zadd(redis_key, {str(now): now})
        
        # Set key expiration
        pipe.expire(redis_key, limit.window)
        
        # Execute pipeline
        _, current, _, _ = pipe.execute()
        
        # Check if under limit
        allowed = current <= limit.requests
        reset_time = now + limit.window
        
        return allowed, {
            "limit": limit.requests,
            "remaining": max(0, limit.requests - current),
            "reset": reset_time,
            "window": limit.window
        }

class RateLimiter:
    """
    High-level rate limiting interface.
    
    This class provides:
    - Multiple backend support
    - Limit configuration
    - Usage tracking
    - Violation handling
    """
    
    def __init__(
        self,
        backend: Union[TokenBucket, RedisRateLimiter],
        default_limit: RateLimit
    ):
        """
        Initialize rate limiter.
        
        Args:
            backend: Rate limit backend
            default_limit (RateLimit): Default limit
        """
        self._backend = backend
        self._default_limit = default_limit
        self._custom_limits: Dict[str, RateLimit] = {}
        
    def add_limit(self, key: str, limit: RateLimit) -> None:
        """
        Add custom rate limit.
        
        Args:
            key (str): Limit key
            limit (RateLimit): Rate limit config
        """
        self._custom_limits[key] = limit
        
    def get_limit(self, key: str) -> RateLimit:
        """
        Get rate limit for key.
        
        Args:
            key (str): Limit key
            
        Returns:
            RateLimit: Rate limit config
        """
        return self._custom_limits.get(key, self._default_limit)
        
    def is_allowed(
        self,
        key: str,
        cost: int = 1
    ) -> Tuple[bool, Dict]:
        """
        Check if request is allowed.
        
        Args:
            key (str): Rate limit key
            cost (int): Request cost
            
        Returns:
            Tuple[bool, Dict]: (allowed, limit info)
        """
        limit = self.get_limit(key)
        return self._backend.is_allowed(key, limit)
        
    @contextmanager
    def check_limit(
        self,
        key: str,
        cost: int = 1,
        raise_on_limit: bool = True
    ):
        """
        Context manager for rate limiting.
        
        Args:
            key (str): Rate limit key
            cost (int): Request cost
            raise_on_limit (bool): Raise on limit
            
        Raises:
            RateLimitExceeded: If limit exceeded
        """
        allowed, info = self.is_allowed(key, cost)
        
        if not allowed and raise_on_limit:
            raise RateLimitExceeded(key, info)
            
        try:
            yield allowed
        finally:
            pass

class RateLimitExceeded(Exception):
    """
    Exception raised when rate limit is exceeded.
    
    Attributes:
        key (str): Rate limit key
        info (Dict): Limit information
    """
    
    def __init__(self, key: str, info: Dict):
        """Initialize exception."""
        self.key = key
        self.info = info
        super().__init__(
            f"Rate limit exceeded for {key}. "
            f"Limit: {info['limit']}, "
            f"Reset in {info['reset']} seconds"
        )

# Example usage:
"""
# Redis backend
redis_client = redis.Redis(host='localhost', port=6379)
limiter = RateLimiter(
    RedisRateLimiter(redis_client),
    RateLimit(100, 3600)  # 100 requests per hour
)

# Add custom limits
limiter.add_limit(
    "api:high_priority",
    RateLimit(1000, 3600)  # 1000 requests per hour
)

# Check limit
with limiter.check_limit("user:123"):
    # Handle request
    pass
""" 