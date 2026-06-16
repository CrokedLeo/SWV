"""
Security configuration - environment-specific settings
Handles CORS, HTTPS/TLS, security headers for development, staging, and production
"""
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class SecurityConfig:
    """Base security configuration"""
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    HTTPS_ENABLED = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
    
    # CORS configuration per environment
    CORS_ALLOWED_ORIGINS: List[str] = []
    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS = ["*"]
    CORS_MAX_AGE = 600
    
    # Security headers
    SECURITY_HEADERS: Dict[str, str] = {}
    
    # API key validation
    API_KEY_HEADER = "x-api-key"
    REQUIRE_API_KEY = True
    
    # Request validation
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    REQUEST_TIMEOUT = 60  # seconds
    
    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_REQUESTS_PER_MINUTE = 100
    
    # Logging
    LOG_SECURITY_EVENTS = True
    LOG_SUSPICIOUS_REQUESTS = True
    
    def __init__(self):
        """Initialize security config based on environment"""
        self._setup_cors()
        self._setup_security_headers()
        
    def _setup_cors(self):
        """Setup CORS configuration based on environment"""
        if self.ENVIRONMENT == "development":
            # Development: Allow localhost
            self.CORS_ALLOWED_ORIGINS = [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "http://localhost:19006",  # Expo web
                "http://localhost:19000",  # Expo bundler
            ]
        
        elif self.ENVIRONMENT == "staging":
            # Staging: Allow staging domain
            staging_origins = os.getenv("CORS_ORIGINS", "https://staging.example.com")
            self.CORS_ALLOWED_ORIGINS = [
                origin.strip() 
                for origin in staging_origins.split(",")
            ]
        
        elif self.ENVIRONMENT == "production":
            # Production: Strict CORS - only allow specified origins
            cors_origins_env = os.getenv("CORS_ORIGINS", "")
            if cors_origins_env:
                self.CORS_ALLOWED_ORIGINS = [
                    origin.strip() 
                    for origin in cors_origins_env.split(",")
                ]
            else:
                # Fallback: Android app and frontend only
                self.CORS_ALLOWED_ORIGINS = [
                    "https://app.example.com",
                    # Android app origins (if applicable)
                    "https://android-app.example.com",
                ]
        
        else:
            # Unknown environment: Fail secure
            self.CORS_ALLOWED_ORIGINS = []
    
    def _setup_security_headers(self):
        """Setup security headers based on environment"""
        # Common headers for all environments
        base_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }
        
        if self.ENVIRONMENT in ["staging", "production"]:
            # HSTS only for HTTPS environments
            if self.HTTPS_ENABLED:
                base_headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains; preload"
                )
        
        elif self.ENVIRONMENT == "development":
            # Relaxed CSP for development
            base_headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; "
                "connect-src 'self' https:"
            )
        
        self.SECURITY_HEADERS = base_headers
    
    def get_cors_config(self) -> Dict:
        """Get CORS middleware configuration"""
        return {
            "allow_origins": self.CORS_ALLOWED_ORIGINS,
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": self.CORS_ALLOW_METHODS,
            "allow_headers": self.CORS_ALLOW_HEADERS,
            "max_age": self.CORS_MAX_AGE,
        }
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for response middleware"""
        return self.SECURITY_HEADERS
    
    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed (for additional validation)"""
        if not origin:
            return False
        if self.ENVIRONMENT == "development":
            # Allow all localhost origins in development
            return any(
                origin.startswith(allowed) 
                for allowed in self.CORS_ALLOWED_ORIGINS
            )
        return origin in self.CORS_ALLOWED_ORIGINS
    
    def should_force_https(self) -> bool:
        """Check if HTTPS should be enforced"""
        return self.ENVIRONMENT == "production" and self.HTTPS_ENABLED
    
    def get_environment_name(self) -> str:
        """Get human-readable environment name"""
        return self.ENVIRONMENT.upper()


# Create global instance
security_config = SecurityConfig()
