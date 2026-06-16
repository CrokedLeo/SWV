"""
Monitoring and health check routes
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.services.cache import cache_manager, rate_limiter, perf_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["monitoring"])


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Verify API key from header"""
    if settings.API_KEY != "your-secret-key-change-in-production":
        if x_api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")


@router.get("/monitor/cache-stats")
async def get_cache_stats(api_key: None = Depends(verify_api_key)):
    """Get cache statistics"""
    return {
        "cache_stats": cache_manager.cache.stats(),
        "timestamp": datetime.utcnow()
    }


@router.get("/monitor/performance")
async def get_performance_stats(api_key: None = Depends(verify_api_key)):
    """Get performance statistics"""
    return {
        "endpoints": perf_monitor.get_stats(),
        "timestamp": datetime.utcnow()
    }


@router.get("/monitor/rate-limit/{identifier}")
async def get_rate_limit_status(identifier: str, api_key: None = Depends(verify_api_key)):
    """Check rate limit status for identifier"""
    return {
        "identifier": identifier,
        "remaining_requests": rate_limiter.get_remaining(identifier),
        "max_requests": rate_limiter.max_requests,
        "window_seconds": rate_limiter.window_seconds
    }


@router.post("/monitor/cache-clear")
async def clear_cache(api_key: None = Depends(verify_api_key)):
    """Clear all cache (admin only)"""
    cache_manager.cache.clear()
    logger.info("Cache cleared by admin request")
    return {"status": "cache cleared", "timestamp": datetime.utcnow()}


@router.get("/monitor/health-detailed")
async def get_detailed_health():
    """Detailed health check with system info"""
    cache_stats = cache_manager.cache.stats()
    
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "components": {
            "yolo_model": settings.YOLO_MODEL,
            "database": "N/A (roadmap)",
            "cache": "healthy" if cache_stats["usage_percent"] < 90 else "warning",
            "external_apis": "operational"
        },
        "performance": {
            "cache_usage_percent": cache_stats["usage_percent"],
            "cached_entries": cache_stats["total_entries"]
        }
    }
