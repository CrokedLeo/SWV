"""
Security headers middleware
Adds security headers to all responses
"""
import logging
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config.security import security_config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    
    Headers:
    - X-Content-Type-Options: nosniff (prevent MIME type sniffing)
    - X-Frame-Options: DENY (prevent clickjacking)
    - X-XSS-Protection: 1; mode=block (enable XSS filter)
    - Strict-Transport-Security: HSTS (enforce HTTPS)
    - Content-Security-Policy: CSP (prevent injection attacks)
    - Referrer-Policy: (control referrer information)
    - Permissions-Policy: (control browser features)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response"""
        try:
            response = await call_next(request)
            
            # Add security headers from config
            security_headers = security_config.get_security_headers()
            for header_name, header_value in security_headers.items():
                response.headers[header_name] = header_value
            
            # Add custom headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in SecurityHeadersMiddleware: {e}")
            raise


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP to HTTPS in production
    Only active when ENVIRONMENT=production and HTTPS_ENABLED=true
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Redirect HTTP to HTTPS"""
        
        # Only redirect in production with HTTPS enabled
        if not security_config.should_force_https():
            return await call_next(request)
        
        # Check if request is HTTP
        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        
        if scheme == "http":
            # Extract host and path
            host = request.headers.get("host", "")
            path = request.url.path
            query = request.url.query
            
            redirect_url = f"https://{host}{path}"
            if query:
                redirect_url += f"?{query}"
            
            logger.info(f"Redirecting HTTP to HTTPS: {redirect_url}")
            
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=redirect_url, status_code=301)
        
        return await call_next(request)


class OriginValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate and log suspicious origin requests
    Helps detect CORS bypasses and suspicious requests
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate origin header"""
        
        origin = request.headers.get("origin")
        method = request.method
        
        # Log suspicious requests
        if security_config.LOG_SUSPICIOUS_REQUESTS and origin:
            # Check if origin is allowed
            if not security_config.is_origin_allowed(origin):
                logger.warning(
                    f"SECURITY: Request from disallowed origin | "
                    f"origin={origin} | method={method} | "
                    f"path={request.url.path} | "
                    f"environment={security_config.get_environment_name()}"
                )
        
        response = await call_next(request)
        return response
