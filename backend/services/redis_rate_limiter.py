"""
Redis-based rate limiter with in-memory fallback
"""
import os
import json
import time
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisRateLimiter:
    """
    Rate limiter using Redis for persistence across workers/restarts
    Falls back to in-memory when Redis is unavailable
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_client: Optional[aioredis.Redis] = None
        self._in_memory: dict = {}
        self._redis_available = False
    
    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Get or create Redis connection"""
        if not REDIS_AVAILABLE:
            return None
        if self.redis_client is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self.redis_client = aioredis.from_url(redis_url, decode_responses=True)
                await self.redis_client.ping()
                self._redis_available = True
                logger.info("Connected to Redis for rate limiting")
            except Exception as e:
                logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
                self._redis_available = False
                self.redis_client = None
        return self.redis_client if self._redis_available else None
    
    async def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed
        Returns (allowed: bool, remaining: int)
        """
        redis = await self._get_redis()
        if redis is not None:
            return await self._redis_check(redis, identifier)
        return self._memory_check(identifier)
    
    async def _redis_check(self, redis: aioredis.Redis, identifier: str) -> Tuple[bool, int]:
        """Check rate limit using Redis sorted set"""
        now = time.time()
        window_start = now - self.window_seconds
        key = f"ratelimit:{identifier}"
        
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self.window_seconds)
        _, count, _, _ = await pipe.execute()
        
        exceeded = count >= self.max_requests
        remaining = max(0, self.max_requests - count - 1) if not exceeded else 0
        
        if exceeded:
            logger.warning(f"Rate limit exceeded (Redis) for {identifier}")
        
        return (not exceeded, remaining)
    
    def _memory_check(self, identifier: str) -> Tuple[bool, int]:
        """Fallback in-memory check"""
        now = time.time()
        
        if identifier not in self._in_memory:
            self._in_memory[identifier] = []
        
        self._in_memory[identifier] = [
            t for t in self._in_memory[identifier]
            if now - t < self.window_seconds
        ]
        
        count = len(self._in_memory[identifier])
        exceeded = count >= self.max_requests
        
        if not exceeded:
            self._in_memory[identifier].append(now)
        
        remaining = max(0, self.max_requests - count - 1) if not exceeded else 0
        
        if exceeded:
            logger.warning(f"Rate limit exceeded (memory) for {identifier}")
        
        return (not exceeded, remaining)
    
    async def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in current window"""
        redis = await self._get_redis()
        if redis is not None:
            now = time.time()
            window_start = now - self.window_seconds
            key = f"ratelimit:{identifier}"
            count = await redis.zcount(key, window_start, now)
            return max(0, self.max_requests - count)
        
        now = time.time()
        if identifier not in self._in_memory:
            return self.max_requests
        self._in_memory[identifier] = [
            t for t in self._in_memory[identifier]
            if now - t < self.window_seconds
        ]
        return max(0, self.max_requests - len(self._in_memory[identifier]))
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    async def reset(self, identifier: Optional[str] = None):
        """Reset rate limit for identifier or all"""
        redis = await self._get_redis()
        if redis is not None:
            if identifier:
                await redis.delete(f"ratelimit:{identifier}")
            else:
                keys = await redis.keys("ratelimit:*")
                if keys:
                    await redis.delete(*keys)
        else:
            if identifier:
                self._in_memory.pop(identifier, None)
            else:
                self._in_memory.clear()
