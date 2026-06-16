"""
Health check API routes
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Query
from sqlalchemy import text
import aiohttp
from backend.services.resilience import circuit_breaker, health_monitor
from backend.services.cache import cache_manager
from backend.config.settings import settings
from backend.models.database import engine
from backend.services.detection import get_detector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["health"])


# Health check helpers
async def _ping_database() -> Dict[str, Any]:
    """Ping database with SELECT 1"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _ping_redis() -> Dict[str, Any]:
    """Ping Redis if configured"""
    if not settings.REDIS_URL:
        return {"status": "not_configured"}
    try:
        import redis as redis_client
        r = redis_client.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        r.close()
        return {"status": "ok"}
    except ImportError:
        return {"status": "not_available", "error": "redis-py not installed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _ping_yolo() -> Dict[str, Any]:
    """Check if YOLO model is loaded"""
    try:
        detector = get_detector()
        if detector._model is not None:
            return {"status": "ok", "model": detector._model_name}
        return {"status": "not_loaded"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _ping_external_apis() -> Dict[str, Any]:
    """Ping external APIs (weather)"""
    results = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(settings.OPENMETEO_API, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                results["weather_api"] = {"status": "ok", "status_code": resp.status}
    except Exception as e:
        results["weather_api"] = {"status": "error", "error": str(e)}
    return results


@router.get("/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns:
        - status: "ok" if service is running
        - timestamp: current timestamp
        - version: API version
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@router.get("/health/detailed", tags=["health"])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check - checks all dependencies
    
    Returns:
        - status: overall system status (healthy/degraded/unhealthy)
        - components: health status of each component
        - circuit_breakers: status of all circuit breakers
        - cache_stats: cache usage statistics
    """
    try:
        # Run real health checks
        db_status = await _ping_database()
        redis_status = await _ping_redis()
        yolo_status = await _ping_yolo()
        external_apis = await _ping_external_apis()
        
        # Get circuit breaker status for all endpoints
        circuit_status = {}
        for endpoint in ["weather_api", "aqi_api", "yolo_inference"]:
            circuit_status[endpoint] = circuit_breaker.get_status(endpoint)
        
        # Get cache statistics
        cache_stats = cache_manager.stats()
        
        # Determine overall health
        components = {
            "database": db_status,
            "redis": redis_status,
            "yolo_model": yolo_status,
            "external_apis": external_apis,
        }
        
        failed = [k for k, v in components.items() if v.get("status") == "error"]
        
        if not failed:
            overall_status = "healthy"
        elif len(failed) < len(components):
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_status,
            "components": components,
            "circuit_breakers": circuit_status,
            "cache": {
                "total_entries": cache_stats["total_entries"],
                "max_size": cache_stats["max_size"],
                "usage_percent": round(cache_stats["usage_percent"], 2)
            },
            "recommendations": _get_health_recommendations(overall_status)
        }
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }


@router.get("/health/circuit-breakers", tags=["health"])
async def circuit_breaker_status(
    endpoint: Optional[str] = Query(None, description="Specific endpoint to check, or all if not specified")
) -> Dict[str, Any]:
    """
    Get circuit breaker status
    
    Returns:
        - status per endpoint
        - state: CLOSED, OPEN, or HALF_OPEN
        - failure_count: consecutive failures
        - last_failure: timestamp of last failure
    """
    if endpoint:
        return {
            "endpoint": endpoint,
            **circuit_breaker.get_status(endpoint)
        }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "circuit_breakers": {
            "weather_api": circuit_breaker.get_status("weather_api"),
            "aqi_api": circuit_breaker.get_status("aqi_api"),
            "yolo_inference": circuit_breaker.get_status("yolo_inference")
        }
    }


@router.get("/health/services", tags=["health"])
async def services_status(
    service: Optional[str] = Query(None, description="Specific service to check, or all if not specified")
) -> Dict[str, Any]:
    """
    Get detailed status of all services
    
    Returns:
        - name: service name
        - is_healthy: boolean health status
        - last_check: timestamp of last check
        - error_message: if unhealthy
        - details: service-specific details
    """
    if service:
        status = health_monitor.get_status(service)
        if status:
            return {"service": service, **status}
        return {"error": f"Service '{service}' not found"}
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "services": health_monitor.get_status() or {}
    }


@router.get("/health/cache", tags=["health"])
async def cache_status() -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        - total_entries: number of cached items
        - max_size: cache size limit
        - usage_percent: percentage of cache used
    """
    stats = cache_manager.stats()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cache": {
            "total_entries": stats["total_entries"],
            "max_size": stats["max_size"],
            "usage_percent": round(stats["usage_percent"], 2),
            "is_full": stats["total_entries"] >= stats["max_size"]
        }
    }


def _get_health_recommendations(overall_status: str) -> list:
    """Generate health recommendations based on status"""
    recommendations = []
    
    if overall_status == "unhealthy":
        recommendations.append("System is unhealthy. Check service logs for details.")
        recommendations.append("Verify external API connectivity (weather, AQI)")
        recommendations.append("Check YOLO model availability")
    
    elif overall_status == "degraded":
        recommendations.append("Some services are temporarily unavailable")
        recommendations.append("They may recover automatically")
    
    else:  # healthy
        recommendations.append("All systems operational")
        recommendations.append("Requests are being processed normally")
    
    return recommendations
