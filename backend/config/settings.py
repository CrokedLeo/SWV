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
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Object Detection API with YOLO"
    
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD = DEBUG
    
    # YOLO Model
    YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.5))
    
    # API
    API_KEY = os.getenv("API_KEY", "your-secret-key-change-in-production")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Upload settings
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "webp"}
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "app.log")

settings = Settings()
