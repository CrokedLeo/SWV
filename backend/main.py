"""
FastAPI main application with security hardening
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Sentry SDK for error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
except ImportError:
    sentry_sdk = None

# Prometheus metrics
try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None

from backend.config.settings import settings
from backend.config.security import security_config
from backend.middleware.security_headers import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    OriginValidationMiddleware
)
from backend.routes.detection import router as detection_router
from backend.routes.environmental import router as environmental_router
from backend.routes.monitoring import router as monitoring_router
from backend.routes.health import router as health_router
from backend.models.schemas import ErrorResponse
from backend.models.database import init_db
from backend.utils.logging import setup_logging

# Configure structured logging
setup_logging(json_format=settings.JSON_LOGGING)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {security_config.get_environment_name()}")
    logger.info(f"HTTPS Enforcement: {'ENABLED' if security_config.should_force_https() else 'DISABLED'}")
    logger.info(f"CORS Origins: {security_config.CORS_ALLOWED_ORIGINS}")
    logger.info(f"Environmental Monitoring Mode: ENABLED")
    logger.info(f"YOLO Model: {settings.YOLO_MODEL}")
    logger.info(f"Caching: ENABLED")
    logger.info(f"Rate Limiting: ENABLED")
    
    # Initialize Sentry SDK for error tracking
    if sentry_sdk and settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=security_config.get_environment_name(),
            traces_sample_rate=0.25 if security_config.ENVIRONMENT == "production" else 1.0,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("Sentry SDK initialized")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
    
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")
    from backend.services.cache import rate_limiter
    await rate_limiter.close()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc"
)

# Prometheus metrics endpoint
if Instrumentator:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    logger.info("Prometheus metrics enabled at /metrics")

# ===== SECURITY MIDDLEWARE STACK =====
# Order matters! Add middlewares in reverse order of execution

# 1. HTTPS Redirect Middleware (redirect HTTP to HTTPS in production)
app.add_middleware(HTTPSRedirectMiddleware)

# 2. Origin Validation Middleware (log suspicious requests)
app.add_middleware(OriginValidationMiddleware)

# 3. Security Headers Middleware (add security headers to responses)
app.add_middleware(SecurityHeadersMiddleware)

# 4. CORS Middleware (handle cross-origin requests)
cors_config = security_config.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_config["allow_origins"],
    allow_credentials=cors_config["allow_credentials"],
    allow_methods=cors_config["allow_methods"],
    allow_headers=cors_config["allow_headers"],
    max_age=cors_config["max_age"],
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_ERROR",
            timestamp=datetime.utcnow()
        ).model_dump()
    )


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "description": "Environmental Monitoring & Air Quality Analysis",
        "docs": "/api/docs",
        "openapi": "/api/openapi.json",
        "features": [
            "Smoke detection from images",
            "Pollutant estimation",
            "Air quality indexing",
            "Geographic data integration",
            "Comprehensive environmental reports",
            "Health recommendations",
            "Performance monitoring",
            "Request caching",
            "Rate limiting"
        ]
    }


# Include routers
app.include_router(detection_router)
app.include_router(environmental_router)
app.include_router(monitoring_router)
app.include_router(health_router)


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )

