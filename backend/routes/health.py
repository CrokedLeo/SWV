"""
Health check API routes
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Query
from backend.services.resilience import circuit_breaker, health_monitor
from backend.services.cache import cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["health"])


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
        "service": "SWV Environmental Monitoring API",
        "version": "1.0.0"
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
        # Get overall health
        overall_health = health_monitor.get_overall_health()
        
        # Get detailed service status
        services_status = health_monitor.get_status()
        
        # Get circuit breaker status for all endpoints
        circuit_status = {}
        for endpoint in ["weather_api", "aqi_api", "yolo_inference"]:
            circuit_status[endpoint] = circuit_breaker.get_status(endpoint)
        
        # Get cache statistics
        cache_stats = cache_manager.stats()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": overall_health,
            "services": services_status,
            "circuit_breakers": circuit_status,
            "cache": {
                "total_entries": cache_stats["total_entries"],
                "max_size": cache_stats["max_size"],
                "usage_percent": round(cache_stats["usage_percent"], 2)
            },
            "recommendations": _get_health_recommendations(overall_health)
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


def _get_health_recommendations(overall_health: Dict[str, Any]) -> list:
    """Generate health recommendations based on status"""
    recommendations = []
    
    if overall_health.get("status") == "unhealthy":
        recommendations.append("⚠️ System is unhealthy. Check service logs for details.")
        recommendations.append("📍 Verify external API connectivity (weather, AQI)")
        recommendations.append("🤖 Check YOLO model availability")
    
    elif overall_health.get("status") == "degraded":
        percentage = overall_health.get("health_percentage", 0)
        if percentage < 50:
            recommendations.append("⚠️ Multiple services are failing")
            recommendations.append("🔧 Restart affected services")
        else:
            recommendations.append("ℹ️ Some services are temporarily unavailable")
            recommendations.append("⏳ They may recover automatically")
    
    else:  # healthy
        recommendations.append("✓ All systems operational")
        recommendations.append("✓ Requests are being processed normally")
    
    return recommendations
