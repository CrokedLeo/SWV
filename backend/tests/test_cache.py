"""
Unit tests for cache.py module
Tests: SimpleCache, RateLimiter, CacheManager, PerformanceMonitor
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from backend.services.cache import (
    SimpleCache, CacheEntry, CacheManager, RateLimiter, PerformanceMonitor
)


# ============= CACHE ENTRY TESTS =============

class TestCacheEntry:
    """Test CacheEntry class"""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry"""
        entry = CacheEntry("test_value", ttl_seconds=3600)
        assert entry.value == "test_value"
        assert entry.ttl_seconds == 3600
        assert entry.created_at is not None
    
    def test_cache_entry_not_expired_immediately(self):
        """Test entry is not expired immediately after creation"""
        entry = CacheEntry("value", ttl_seconds=3600)
        assert not entry.is_expired()
    
    def test_cache_entry_expired_after_ttl(self):
        """Test entry is expired after TTL passes"""
        entry = CacheEntry("value", ttl_seconds=1)
        # Artificially age the entry
        entry.created_at = datetime.utcnow() - timedelta(seconds=2)
        assert entry.is_expired()
    
    def test_get_value_returns_value_if_not_expired(self):
        """Test get_value returns value when not expired"""
        entry = CacheEntry("test_value", ttl_seconds=3600)
        assert entry.get_value() == "test_value"
    
    def test_get_value_returns_none_if_expired(self):
        """Test get_value returns None when expired"""
        entry = CacheEntry("test_value", ttl_seconds=1)
        entry.created_at = datetime.utcnow() - timedelta(seconds=2)
        assert entry.get_value() is None
    
    def test_cache_entry_with_dict_value(self):
        """Test cache entry with dictionary value"""
        data = {"key": "value", "number": 42}
        entry = CacheEntry(data, ttl_seconds=3600)
        assert entry.get_value() == data
    
    def test_cache_entry_with_list_value(self):
        """Test cache entry with list value"""
        data = [1, 2, 3, 4, 5]
        entry = CacheEntry(data, ttl_seconds=3600)
        assert entry.get_value() == data


# ============= SIMPLE CACHE TESTS =============

class TestSimpleCache:
    """Test SimpleCache class"""
    
    @pytest.mark.unit
    def test_cache_set_and_get(self, cache):
        """Test basic set and get operations"""
        cache.set("key1", "value1", ttl_seconds=3600)
        assert cache.get("key1") == "value1"
    
    @pytest.mark.unit
    def test_cache_get_nonexistent_key(self, cache):
        """Test getting non-existent key returns None"""
        assert cache.get("nonexistent") is None
    
    @pytest.mark.unit
    def test_cache_multiple_entries(self, cache):
        """Test caching multiple entries"""
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.set("key2", "value2", ttl_seconds=3600)
        cache.set("key3", {"nested": "dict"}, ttl_seconds=3600)
        
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == {"nested": "dict"}
    
    @pytest.mark.unit
    def test_cache_invalidate(self, cache):
        """Test cache invalidation"""
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.invalidate("key1")
        assert cache.get("key1") is None
    
    @pytest.mark.unit
    def test_cache_invalidate_nonexistent_key(self, cache):
        """Test invalidating non-existent key doesn't raise error"""
        cache.invalidate("nonexistent")  # Should not raise
    
    @pytest.mark.unit
    def test_cache_clear(self, cache):
        """Test clearing all cache entries"""
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.set("key2", "value2", ttl_seconds=3600)
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    @pytest.mark.unit
    def test_cache_ttl_expiration(self, cache):
        """Test TTL expiration"""
        cache.set("key1", "value1", ttl_seconds=1)
        assert cache.get("key1") == "value1"
        
        # Manually expire the entry
        cache.cache["key1"].created_at = datetime.utcnow() - timedelta(seconds=2)
        assert cache.get("key1") is None
    
    @pytest.mark.unit
    def test_cache_stats(self, cache):
        """Test cache statistics"""
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.set("key2", "value2", ttl_seconds=3600)
        
        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["max_size"] == 100
        assert 1.0 < stats["usage_percent"] < 3.0
    
    @pytest.mark.unit
    def test_cache_max_size_enforcement(self, cache):
        """Test max size limit enforcement"""
        # Create a small cache
        small_cache = SimpleCache(max_size=3)
        
        # Fill it beyond max size
        small_cache.set("key1", "value1", ttl_seconds=3600)
        small_cache.set("key2", "value2", ttl_seconds=3600)
        small_cache.set("key3", "value3", ttl_seconds=3600)
        small_cache.set("key4", "value4", ttl_seconds=3600)
        
        # Cache should trigger cleanup
        stats = small_cache.stats()
        assert stats["total_entries"] <= 3
    
    @pytest.mark.unit
    def test_cache_hit_with_expired_entries(self, cache):
        """Test cache hit when there are expired entries"""
        cache.set("expired", "old_value", ttl_seconds=1)
        cache.cache["expired"].created_at = datetime.utcnow() - timedelta(seconds=2)
        
        cache.set("fresh", "new_value", ttl_seconds=3600)
        
        assert cache.get("expired") is None
        assert cache.get("fresh") == "new_value"
    
    @pytest.mark.unit
    def test_cache_with_complex_types(self, cache):
        """Test caching complex data types"""
        data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"}
            ],
            "count": 2,
            "metadata": {"version": 1}
        }
        cache.set("complex", data, ttl_seconds=3600)
        assert cache.get("complex") == data


# ============= CACHE MANAGER TESTS =============

class TestCacheManager:
    """Test CacheManager singleton"""
    
    @pytest.mark.unit
    def test_cache_manager_singleton(self):
        """Test CacheManager is a singleton"""
        manager1 = CacheManager()
        manager2 = CacheManager()
        assert manager1 is manager2
    
    @pytest.mark.unit
    def test_cache_manager_make_key(self):
        """Test cache key generation"""
        key1 = CacheManager.make_key(1, 2, 3)
        key2 = CacheManager.make_key(1, 2, 3)
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hex digest
    
    @pytest.mark.unit
    def test_cache_manager_make_key_different_args(self):
        """Test cache keys differ for different arguments"""
        key1 = CacheManager.make_key(1, 2, 3)
        key2 = CacheManager.make_key(1, 2, 4)
        assert key1 != key2
    
    @pytest.mark.unit
    def test_cache_manager_geolocation_key(self, cache_manager_instance):
        """Test geolocation cache key generation"""
        key = cache_manager_instance.get_geolocation_cache_key(43.7701, 11.2556)
        assert key == "geo_43.7701_11.2556"
    
    @pytest.mark.unit
    def test_cache_manager_weather_key(self, cache_manager_instance):
        """Test weather cache key generation"""
        key = cache_manager_instance.get_weather_cache_key(43.7701, 11.2556)
        assert key == "weather_43.7701_11.2556"
    
    @pytest.mark.unit
    def test_cache_manager_cache_geolocation(self, cache_manager_instance, sample_geolocation):
        """Test caching geolocation"""
        cache_manager_instance.cache_geolocation(
            sample_geolocation, 43.7701, 11.2556, ttl=86400
        )
        cached = cache_manager_instance.get_cached_geolocation(43.7701, 11.2556)
        assert cached == sample_geolocation
    
    @pytest.mark.unit
    def test_cache_manager_cache_weather(self, cache_manager_instance, sample_environmental_data):
        """Test caching weather"""
        cache_manager_instance.cache_weather(
            sample_environmental_data, 43.7701, 11.2556, ttl=1800
        )
        cached = cache_manager_instance.get_cached_weather(43.7701, 11.2556)
        assert cached == sample_environmental_data
    
    @pytest.mark.unit
    def test_cache_manager_geolocation_cache_miss(self, cache_manager_instance):
        """Test geolocation cache miss"""
        cached = cache_manager_instance.get_cached_geolocation(0.0, 0.0)
        assert cached is None
    
    @pytest.mark.unit
    def test_cache_manager_weather_cache_miss(self, cache_manager_instance):
        """Test weather cache miss"""
        cached = cache_manager_instance.get_cached_weather(0.0, 0.0)
        assert cached is None


# ============= RATE LIMITER TESTS =============

class TestRateLimiter:
    """Test RateLimiter class"""
    
    @pytest.mark.unit
    def test_rate_limiter_creation(self):
        """Test rate limiter creation"""
        limiter = RateLimiter(max_requests=100, window_seconds=60)
        assert limiter.max_requests == 100
        assert limiter.window_seconds == 60
    
    @pytest.mark.unit
    def test_rate_limiter_first_request_allowed(self, rate_limiter):
        """Test first request is always allowed"""
        allowed, _ = rate_limiter.is_allowed("user_1")
        assert allowed
    
    @pytest.mark.unit
    def test_rate_limiter_multiple_requests_under_limit(self, rate_limiter):
        """Test multiple requests under limit are allowed"""
        identifier = "user_1"
        for i in range(5):
            allowed, _ = rate_limiter.is_allowed(identifier)
            assert allowed
    
    @pytest.mark.unit
    def test_rate_limiter_exceeds_limit(self):
        """Test request denied when limit exceeded"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        identifier = "user_1"
        
        # Fill up the limit
        assert limiter.is_allowed(identifier)[0]
        assert limiter.is_allowed(identifier)[0]
        assert limiter.is_allowed(identifier)[0]
        
        # Next request should be denied
        assert not limiter.is_allowed(identifier)[0]
    
    @pytest.mark.unit
    def test_rate_limiter_different_identifiers(self, rate_limiter):
        """Test rate limiting per identifier"""
        # Each user should have their own limit
        assert rate_limiter.is_allowed("user_1")[0]
        assert rate_limiter.is_allowed("user_2")[0]
        assert rate_limiter.is_allowed("user_3")[0]
    
    @pytest.mark.unit
    def test_rate_limiter_get_remaining(self, rate_limiter):
        """Test getting remaining requests"""
        identifier = "user_1"
        
        remaining = rate_limiter.get_remaining(identifier)
        assert remaining == 10  # max_requests=10
        
        rate_limiter.is_allowed(identifier)
        remaining = rate_limiter.get_remaining(identifier)
        assert remaining == 9
    
    @pytest.mark.unit
    def test_rate_limiter_remaining_after_exceed(self):
        """Test remaining requests after exceeding limit"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        identifier = "user_1"
        
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)
        limiter.is_allowed(identifier)  # Denied
        
        remaining = limiter.get_remaining(identifier)
        assert remaining == 0
    
    @pytest.mark.unit
    def test_rate_limiter_new_user_full_remaining(self, rate_limiter):
        """Test new user has full remaining requests"""
        identifier = "new_user"
        remaining = rate_limiter.get_remaining(identifier)
        assert remaining == 10
    
    @pytest.mark.slow
    def test_rate_limiter_window_reset(self):
        """Test rate limiter window resets"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        identifier = "user_1"
        
        assert limiter.is_allowed(identifier)[0]
        assert limiter.is_allowed(identifier)[0]
        assert not limiter.is_allowed(identifier)[0]
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should allow new requests now
        assert limiter.is_allowed(identifier)[0]


# ============= PERFORMANCE MONITOR TESTS =============

class TestPerformanceMonitor:
    """Test PerformanceMonitor class"""
    
    @pytest.mark.unit
    def test_perf_monitor_record_single_call(self, performance_monitor):
        """Test recording a single operation"""
        performance_monitor.record("endpoint_a", duration_ms=100, success=True)
        
        stats = performance_monitor.get_endpoint_stats("endpoint_a")
        assert stats["calls"] == 1
        assert stats["total_time"] == 100
        assert stats["avg_time"] == 100
        assert stats["min_time"] == 100
        assert stats["max_time"] == 100
        assert stats["errors"] == 0
    
    @pytest.mark.unit
    def test_perf_monitor_multiple_calls(self, performance_monitor):
        """Test recording multiple calls"""
        performance_monitor.record("endpoint_a", 100, success=True)
        performance_monitor.record("endpoint_a", 200, success=True)
        performance_monitor.record("endpoint_a", 150, success=True)
        
        stats = performance_monitor.get_endpoint_stats("endpoint_a")
        assert stats["calls"] == 3
        assert stats["total_time"] == 450
        assert stats["avg_time"] == 150
        assert stats["min_time"] == 100
        assert stats["max_time"] == 200
    
    @pytest.mark.unit
    def test_perf_monitor_failed_call(self, performance_monitor):
        """Test recording failed calls"""
        performance_monitor.record("endpoint_a", 100, success=False)
        performance_monitor.record("endpoint_a", 150, success=True)
        
        stats = performance_monitor.get_endpoint_stats("endpoint_a")
        assert stats["calls"] == 2
        assert stats["errors"] == 1
    
    @pytest.mark.unit
    def test_perf_monitor_multiple_endpoints(self, performance_monitor):
        """Test tracking multiple endpoints"""
        performance_monitor.record("endpoint_a", 100, success=True)
        performance_monitor.record("endpoint_b", 200, success=True)
        performance_monitor.record("endpoint_c", 150, success=True)
        
        all_stats = performance_monitor.get_stats()
        assert len(all_stats) == 3
        assert "endpoint_a" in all_stats
        assert "endpoint_b" in all_stats
        assert "endpoint_c" in all_stats
    
    @pytest.mark.unit
    def test_perf_monitor_nonexistent_endpoint(self, performance_monitor):
        """Test getting stats for non-existent endpoint"""
        stats = performance_monitor.get_endpoint_stats("nonexistent")
        assert stats is None
    
    @pytest.mark.unit
    def test_perf_monitor_stats_empty(self):
        """Test stats for empty monitor"""
        monitor = PerformanceMonitor()
        stats = monitor.get_stats()
        assert stats == {}


# ============= INTEGRATION TESTS =============

class TestCacheIntegration:
    """Integration tests for cache module"""
    
    @pytest.mark.integration
    def test_cache_full_lifecycle(self):
        """Test full cache lifecycle"""
        cache = SimpleCache(max_size=10)
        
        # Set values
        cache.set("key1", "value1", ttl_seconds=3600)
        cache.set("key2", {"data": "value"}, ttl_seconds=3600)
        
        # Get values
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == {"data": "value"}
        
        # Invalidate one
        cache.invalidate("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == {"data": "value"}
        
        # Clear all
        cache.clear()
        assert cache.get("key2") is None
    
    @pytest.mark.integration
    def test_rate_limiter_with_cache_manager(self):
        """Test rate limiter working with cache"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        cache = SimpleCache(max_size=100)
        
        # Simulate API calls with rate limiting
        for i in range(5):
            allowed, _ = limiter.is_allowed("api_client_1")
            assert allowed
            cache.set(f"result_{i}", f"data_{i}", ttl_seconds=3600)
        
        # Next call should be rate limited
        assert not limiter.is_allowed("api_client_1")[0]
        
        # But cache should still have data
        assert cache.get("result_0") == "data_0"
