"""
Security utilities and best practices
"""
import logging
import hashlib
import os
import re
from typing import Optional
from pathlib import Path
import secrets
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """Simple in-memory rate limiter for IP addresses"""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed to make a request"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        self.requests[ip] = [
            req_time for req_time in self.requests[ip]
            if req_time > minute_ago
        ]
        
        # Check if limit exceeded
        if len(self.requests[ip]) >= self.requests_per_minute:
            return False
        
        # Add current request
        self.requests[ip].append(now)
        return True


# Global rate limiter instance
rate_limiter = SimpleRateLimiter(requests_per_minute=100)



class FileSecurityValidator:
    """Validate file uploads for security"""
    
    # Maximum file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/webp'
    }
    
    # File magic numbers (first 4-8 bytes)
    FILE_SIGNATURES = {
        b'\xFF\xD8\xFF': 'jpeg',      # JPEG
        b'\x89PNG\r\n': 'png',        # PNG
        b'GIF8': 'gif',               # GIF
        b'BM': 'bmp',                 # BMP
        b'RIFF': 'webp'               # WEBP
    }
    
    @staticmethod
    def validate_file(
        file_bytes: bytes,
        filename: str,
        max_size: int = MAX_FILE_SIZE
    ) -> tuple[bool, str]:
        """
        Validate uploaded file
        
        Returns:
            (is_valid, error_message)
        """
        # Check file size
        if len(file_bytes) > max_size:
            return False, f"File exceeds maximum size of {max_size / (1024*1024):.1f}MB"
        
        # Check file extension
        if not filename:
            return False, "No filename provided"
        
        ext = filename.split('.')[-1].lower()
        allowed_ext = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
        if ext not in allowed_ext:
            return False, f"File type not allowed. Allowed: {', '.join(allowed_ext)}"
        
        # Check file magic numbers (most important!)
        if not FileSecurityValidator._verify_file_signature(file_bytes):
            return False, "File signature does not match extension. Possible malicious file."
        
        # Check for suspicious content
        if FileSecurityValidator._contains_suspicious_patterns(file_bytes):
            return False, "File contains suspicious patterns"
        
        return True, ""
    
    @staticmethod
    def _verify_file_signature(file_bytes: bytes) -> bool:
        """Verify file magic number"""
        if not file_bytes or len(file_bytes) < 4:
            return False
        
        # Check each known signature
        for signature, file_type in FileSecurityValidator.FILE_SIGNATURES.items():
            if file_bytes.startswith(signature):
                return True
        
        return False
    
    @staticmethod
    def _contains_suspicious_patterns(file_bytes: bytes) -> bool:
        """Check for malicious patterns"""
        # Convert to string to check for embedded scripts
        try:
            content = file_bytes.decode('utf-8', errors='ignore')
            
            # Check for common attack patterns
            suspicious_patterns = [
                '<script',          # JavaScript
                '<?php',            # PHP
                'exec',             # Command execution
                'eval',             # Code evaluation
                'shell_exec',       # Shell commands
                'system(',          # System calls
            ]
            
            for pattern in suspicious_patterns:
                if pattern.lower() in content.lower():
                    logger.warning(f"Suspicious pattern detected: {pattern}")
                    return True
        except:
            pass
        
        return False
    
    @staticmethod
    def generate_safe_filename(original_filename: str) -> str:
        """
        Generate safe filename to prevent path traversal
        
        Examples:
            "../../../etc/passwd" → "safe_filename_abc123.jpg"
            "file.jpg" → "file_abc123.jpg"
        """
        # Get extension only
        ext = original_filename.split('.')[-1].lower()
        
        # Generate random safe name
        random_suffix = secrets.token_hex(6)
        
        return f"upload_{random_suffix}.{ext}"


class InputSanitizer:
    """Sanitize user inputs"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 500) -> str:
        """
        Sanitize string input
        Remove special characters that could cause injection
        """
        if not value:
            return ""
        
        # Truncate
        value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char == '\n')
        
        return value.strip()
    
    @staticmethod
    def sanitize_number(value: float, min_val: float = None, max_val: float = None) -> float:
        """Sanitize numeric input"""
        if min_val is not None:
            value = max(value, min_val)
        if max_val is not None:
            value = min(value, max_val)
        return value
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.match(pattern, url) is not None


class RequestValidator:
    """Validate HTTP requests"""
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> tuple[bool, str]:
        """Validate GPS coordinates"""
        if not -90 <= lat <= 90:
            return False, "Latitude must be between -90 and 90"
        if not -180 <= lon <= 180:
            return False, "Longitude must be between -180 and 180"
        return True, ""
    
    @staticmethod
    def validate_confidence(confidence: float) -> tuple[bool, str]:
        """Validate confidence threshold"""
        if not 0 < confidence < 1:
            return False, "Confidence must be between 0 and 1"
        return True, ""
    
    @staticmethod
    def is_reasonable_processing_time(ms: float) -> bool:
        """Check if processing time is reasonable"""
        # Max 60 seconds for API call
        return 0 < ms < 60000
    
    @staticmethod
    def is_reasonable_aqi(aqi: int) -> bool:
        """Check if AQI value is in valid range"""
        return 0 <= aqi <= 500
    
    @staticmethod
    def is_reasonable_smoke_percentage(percentage: float) -> bool:
        """Check if smoke percentage is valid"""
        return 0 <= percentage <= 100


class EncryptionUtility:
    """Simple encryption for sensitive data"""
    
    @staticmethod
    def hash_string(value: str, salt: Optional[str] = None) -> str:
        """
        Hash string using SHA-256
        Use for API keys, tokens, etc.
        """
        if salt is None:
            salt = os.urandom(16).hex()
        
        hash_obj = hashlib.sha256((value + salt).encode())
        return f"{hash_obj.hexdigest()}${salt}"
    
    @staticmethod
    def verify_hash(value: str, hash_with_salt: str) -> bool:
        """Verify hash"""
        try:
            stored_hash, salt = hash_with_salt.split('$')
            computed_hash = hashlib.sha256((value + salt).encode()).hexdigest()
            return computed_hash == stored_hash
        except:
            return False
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)


class SecurityHeaders:
    """Common security headers for responses"""
    
    @staticmethod
    def get_security_headers() -> dict:
        """
        Get recommended security headers for all responses
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


class APIKeyManager:
    """Manage API keys securely"""
    
    _keys_file = ".api_keys.secure"
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate new secure API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(provided_key: str, stored_hash: str) -> bool:
        """Verify provided key matches stored hash"""
        return APIKeyManager.hash_api_key(provided_key) == stored_hash


# Security logging
def log_security_event(event_type: str, details: dict, severity: str = "INFO"):
    """Log security-related events"""
    logger.log(
        getattr(logging, severity),
        f"SECURITY_EVENT: {event_type} | Details: {details}"
    )
