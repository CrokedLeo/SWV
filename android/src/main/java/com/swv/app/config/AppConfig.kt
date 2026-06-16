package com.swv.app.config

object AppConfig {
    // Server Configuration
    const val API_BASE_URL = "http://YOUR_SERVER_IP:8000/"  // Change to your server IP
    const val API_KEY = "your-secret-key-change-in-production"
    const val TIMEOUT_SECONDS = 30
    
    // Model Configuration
    const val DEFAULT_CONFIDENCE = 0.5f
    const val MIN_CONFIDENCE = 0.1f
    const val MAX_CONFIDENCE = 0.95f
    
    // UI Configuration
    const val CAMERA_PREVIEW_WIDTH = 640
    const val CAMERA_PREVIEW_HEIGHT = 480
    
    // App Configuration
    const val LOG_ENABLED = true
    const val CACHE_RESULTS = true
    const val MAX_CACHE_SIZE = 50  // Maximum number of cached results
}
