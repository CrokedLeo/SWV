package com.swv.utils

object Constants {
    const val API_BASE_URL = "http://YOUR_SERVER_IP:8000/"
    const val API_KEY = "your-secret-key-change-in-production"
    const val CONNECT_TIMEOUT_SECONDS = 15L
    const val READ_TIMEOUT_SECONDS = 30L
    const val WRITE_TIMEOUT_SECONDS = 30L

    const val DEFAULT_CONFIDENCE = 0.5f
    const val MIN_CONFIDENCE = 0.1f
    const val MAX_CONFIDENCE = 0.95f

    const val CACHE_NAME = "swv_cache"
    const val CACHE_MAX_SIZE = 50
    const val CACHE_EXPIRY_HOURS = 24

    const val PREFS_NAME = "swv_prefs"
    const val PREFS_API_URL = "api_url"
    const val PREFS_API_KEY = "api_key"
    const val PREFS_LAST_LOCATION_LAT = "last_lat"
    const val PREFS_LAST_LOCATION_LON = "last_lon"
    const val LOG_ENABLED = true

    const val PREFS_LAST_LOCATION_ADDRESS = "last_address"

    const val MAP_DEFAULT_ZOOM = 12f
    const val LOCATION_UPDATE_INTERVAL_MS = 10000L
    const val LOCATION_FASTEST_INTERVAL_MS = 5000L

    const val REQUEST_CODE_CAMERA = 1001
    const val REQUEST_CODE_GALLERY = 1002
    const val REQUEST_CODE_LOCATION = 1003

    const val AQI_EXCELLENT_MAX = 50
    const val AQI_GOOD_MAX = 100
    const val AQI_MODERATE_MAX = 150
    const val AQI_POOR_MAX = 200

    val AQI_RANGES = mapOf(
        "excellent" to "0-50",
        "good" to "51-100",
        "moderate" to "101-150",
        "poor" to "151-200",
        "hazardous" to "201-500"
    )
}
