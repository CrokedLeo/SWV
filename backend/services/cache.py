"""
Caching and performance optimization service
"""
import logging
import time
import inspect
import threading
from typing import Optional, Callable, Any
from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with TTL"""
    def __init__(self, value: Any, ttl_seconds: int = 3600):
        self.value = value
        self.created_at = datetime.utcnow()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if entry expired"""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def get_value(self) -> Optional[Any]:
        """Get value if not expired"""
        if self.is_expired():
            return None
        return self.value


class SimpleCache:
    """Simple in-memory cache with TTL (thread-safe)"""
    
    def __init__(self, max_size: int = 1000):
        self.cache: dict = {}
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cache entry"""
        with self._lock:
            if len(self.cache) >= self.max_size:
                self._cleanup_expired()
                # If still full, evict oldest entry
                if len(self.cache) >= self.max_size:
                    oldest = min(self.cache.items(), key=lambda x: x[1].created_at)
                    del self.cache[oldest[0]]
            
            self.cache[key] = CacheEntry(value, ttl_seconds)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_seconds}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache entry if not expired"""
        with self._lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            value = entry.get_value()
            
            if value is None:
                del self.cache[key]
                logger.debug(f"Cache HIT (expired): {key}")
                return None
            
            logger.debug(f"Cache HIT: {key}")
            return value
    
    def invalidate(self, key: str):
        """Invalidate cache entry"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Cache INVALIDATE: {key}")
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def _cleanup_expired(self):
        """Remove expired entries (caller must hold _lock)"""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for key in expired_keys:
            del self.cache[key]
        logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
    
    def stats(self) -> dict:
        """Get cache statistics"""
        with self._lock:
            self._cleanup_expired()
            return {
                "total_entries": len(self.cache),
                "max_size": self.max_size,
                "usage_percent": (len(self.cache) / self.max_size) * 100
            }


class CacheManager:
    """Centralized cache management"""
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.cache = SimpleCache(max_size=1000)
        return cls._instance
    
    @staticmethod
    def make_key(*args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = json.dumps({
            "args": str(args),
            "kwargs": str(kwargs)
        }, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_geolocation_cache_key(self, lat: float, lon: float) -> str:
        """Cache key for geolocation"""
        return f"geo_{lat:.4f}_{lon:.4f}"
    
    def get_weather_cache_key(self, lat: float, lon: float) -> str:
        """Cache key for weather"""
        return f"weather_{lat:.4f}_{lon:.4f}"
    
    def cache_geolocation(self, location, lat: float, lon: float, ttl: int = 86400):
        """Cache geolocation for 24 hours"""
        key = self.get_geolocation_cache_key(lat, lon)
        self.cache.set(key, location, ttl_seconds=ttl)
    
    def get_cached_geolocation(self, lat: float, lon: float):
        """Get cached geolocation"""
        key = self.get_geolocation_cache_key(lat, lon)
        return self.cache.get(key)
    
    def cache_weather(self, weather_data, lat: float, lon: float, ttl: int = 1800):
        """Cache weather for 30 minutes"""
        key = self.get_weather_cache_key(lat, lon)
        self.cache.set(key, weather_data, ttl_seconds=ttl)
    
    def get_cached_weather(self, lat: float, lon: float):
        """Get cached weather"""
        key = self.get_weather_cache_key(lat, lon)
        return self.cache.get(key)


class RateLimiter:
    """Simple rate limiting (thread-safe)"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict = {}
        self._lock = threading.Lock()
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed, returns (allowed, remaining)"""
        now = datetime.utcnow().timestamp()
        
        with self._lock:
            if identifier not in self.requests:
                self.requests[identifier] = []
            
            # Remove old requests outside window
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
            
            # Check if limit exceeded
            remaining = max(0, self.max_requests - len(self.requests[identifier]))
            if len(self.requests[identifier]) >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {identifier}")
                return (False, 0)
            
            # Add new request
            self.requests[identifier].append(now)
            return (True, remaining - 1)
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in window"""
        now = datetime.utcnow().timestamp()
        
        with self._lock:
            if identifier not in self.requests:
                return self.max_requests
            
            # Remove old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window_seconds
            ]
            
            return max(0, self.max_requests - len(self.requests[identifier]))


class PerformanceMonitor:
    """Monitor endpoint performance (thread-safe)"""
    
    def __init__(self):
        self.metrics: dict = {}
        self._lock = threading.Lock()
    
    def record(self, endpoint: str, duration_ms: float, success: bool = True):
        """Record endpoint call"""
        with self._lock:
            if endpoint not in self.metrics:
                self.metrics[endpoint] = {
                    "calls": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0,
                    "errors": 0
                }
            
            m = self.metrics[endpoint]
            m["calls"] += 1
            m["total_time"] += duration_ms
            m["avg_time"] = m["total_time"] / m["calls"]
            m["min_time"] = min(m["min_time"], duration_ms)
            m["max_time"] = max(m["max_time"], duration_ms)
            if not success:
                m["errors"] += 1
    
    def get_stats(self) -> dict:
        """Get all metrics"""
        with self._lock:
            return dict(self.metrics)
    
    def get_endpoint_stats(self, endpoint: str) -> Optional[dict]:
        """Get stats for specific endpoint"""
        with self._lock:
            m = self.metrics.get(endpoint)
            return dict(m) if m else None


# Global instances
cache_manager = CacheManager()
from backend.services.redis_rate_limiter import RedisRateLimiter
rate_limiter = RedisRateLimiter(max_requests=100, window_seconds=60)
perf_monitor = PerformanceMonitor()


def timed_operation(func):
    """Decorator to time operations"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            perf_monitor.record(func.__name__, duration, success=True)
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            perf_monitor.record(func.__name__, duration, success=False)
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000
            perf_monitor.record(func.__name__, duration, success=True)
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            perf_monitor.record(func.__name__, duration, success=False)
            raise
    
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
