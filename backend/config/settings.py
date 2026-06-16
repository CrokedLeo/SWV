"""
Configuration settings for the application
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings"""
    
    # App info
    APP_NAME = "SWV - Smart Vision"
    APP_VERSION = "2.0.0"
    APP_DESCRIPTION = "Environmental Monitoring & Air Quality Analysis"
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD = DEBUG
    
    # YOLO Model
    YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.onnx")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))
    
    # API
    API_KEY = os.getenv("API_KEY", "your-secret-key-change-in-production")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Upload settings
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    
    # Environmental APIs
    WAQI_TOKEN = os.getenv("WAQI_TOKEN")  # Optional: World Air Quality Index token
    OPENMETEO_API = "https://api.open-meteo.com/v1/forecast"  # Free weather API
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "app.log")
    
    # Redis (for rate limiting persistence)
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    
    # Database (for future use with reports storage)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./swv.db")

    # Sentry / Error Tracking
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")

    # Structured Logging
    JSON_LOGGING: bool = os.getenv("JSON_LOGGING", "false").lower() == "true"
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return getattr(self, key, default)

settings = Settings()

