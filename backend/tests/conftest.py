"""
Shared pytest fixtures and configuration for all tests
"""
import pytest
import asyncio
import numpy as np
import cv2
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from io import BytesIO
from PIL import Image

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.cache import SimpleCache, CacheManager, RateLimiter, PerformanceMonitor
from backend.models.schemas import (
    SmokeLevel, PollutantType, GeoLocation, EnvironmentalData, 
    SmokeAnalysis, PollutantReading
)


# ============= PYTEST CONFIGURATION =============

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "async_test: mark test as async"
    )


# ============= FASTAPI TEST CLIENT =============

@pytest.fixture(scope="session")
def test_client():
    """Create FastAPI test client"""
    return TestClient(app)



# ============= CACHE FIXTURES =============

@pytest.fixture
def cache():
    """Create a fresh cache instance"""
    cache_inst = SimpleCache(max_size=100)
    yield cache_inst
    cache_inst.clear()


@pytest.fixture
def cache_manager_instance():
    """Create a fresh CacheManager instance (resets singleton)"""
    # Create new instance
    manager = CacheManager()
    manager.cache.clear()
    yield manager
    manager.cache.clear()


@pytest.fixture
def rate_limiter():
    """Create a fresh RateLimiter instance"""
    return RateLimiter(max_requests=10, window_seconds=60)


@pytest.fixture
def performance_monitor():
    """Create a fresh PerformanceMonitor instance"""
    return PerformanceMonitor()


# ============= SAMPLE DATA FIXTURES =============

@pytest.fixture
def sample_coordinates():
    """Sample GPS coordinates"""
    return {
        "valid": {"lat": 43.7701, "lon": 11.2556},  # Florence, Italy
        "invalid_lat_high": {"lat": 91.0, "lon": 0.0},
        "invalid_lat_low": {"lat": -91.0, "lon": 0.0},
        "invalid_lon_high": {"lat": 0.0, "lon": 181.0},
        "invalid_lon_low": {"lat": 0.0, "lon": -181.0},
        "equator": {"lat": 0.0, "lon": 0.0},
        "north_pole": {"lat": 90.0, "lon": 0.0},
        "south_pole": {"lat": -90.0, "lon": 0.0},
    }


@pytest.fixture
def sample_geolocation():
    """Sample GeoLocation object"""
    return GeoLocation(
        latitude=43.7701,
        longitude=11.2556,
        address="Firenze, Italy",
        country="Italy",
        region="Tuscany",
        city="Florence",
        accuracy_meters=10.5
    )


@pytest.fixture
def sample_environmental_data():
    """Sample EnvironmentalData object"""
    return EnvironmentalData(
        temperature=22.5,
        humidity=65.0,
        pressure=1013.25,
        wind_speed=3.5,
        visibility=10000.0
    )


@pytest.fixture
def sample_smoke_analysis():
    """Sample SmokeAnalysis object"""
    return SmokeAnalysis(
        smoke_percentage=15.5,
        smoke_level=SmokeLevel.EXCELLENT,
        density_distribution={
            "top_left": 10.0, "top_center": 12.0, "top_right": 8.0,
            "mid_left": 11.0, "mid_center": 18.0, "mid_right": 14.0,
            "bottom_left": 12.0, "bottom_center": 20.0, "bottom_right": 16.0,
        },
        dominant_color=(200, 200, 200),
        particles_detected=5,
        opacity=0.2
    )


@pytest.fixture
def sample_pollutant_reading():
    """Sample PollutantReading object"""
    return PollutantReading(
        pollutant_type=PollutantType.PM25,
        value=12.5,
        unit="µg/m³",
        aqi_index=45,
        risk_level="low"
    )


# ============= IMAGE FIXTURES =============

@pytest.fixture
def create_sample_image():
    """Factory fixture to create sample images"""
    def _create_image(width=640, height=480, color=(100, 100, 100), format_type="rgb"):
        """
        Create a sample image
        
        Args:
            width: Image width
            height: Image height
            color: RGB color tuple
            format_type: 'rgb' or 'hsv'
        """
        # Create numpy array
        image = np.full((height, width, 3), color, dtype=np.uint8)
        
        if format_type == "rgb":
            return image
        elif format_type == "hsv":
            return cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
        
        return image
    
    return _create_image


@pytest.fixture
def sample_image_rgb():
    """Sample RGB image (numpy array)"""
    # Create a 640x480 image with mostly blue sky
    image = np.full((480, 640, 3), (100, 150, 200), dtype=np.uint8)
    # Add some smoke-like gray areas
    image[100:200, 100:300] = (128, 128, 128)
    return image


@pytest.fixture
def clean_image_bytes():
    """Create a clean JPEG image bytes"""
    # Create PIL image
    img = Image.new('RGB', (100, 100), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def clean_png_bytes():
    """Create a clean PNG image bytes"""
    img = Image.new('RGB', (100, 100), color='green')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def malicious_file_bytes():
    """Create malicious file with embedded script"""
    # Create a valid JPEG header but with embedded JavaScript
    jpeg_header = b'\xFF\xD8\xFF'
    malicious_content = b'<script>alert("xss")</script>'
    return jpeg_header + malicious_content


@pytest.fixture
def oversized_file_bytes():
    """Create an oversized file"""
    # Create a file larger than 10MB
    size = 11 * 1024 * 1024  # 11MB
    return b'\xFF\xD8\xFF' + b'A' * size


# ============= MOCK API FIXTURES =============

@pytest.fixture
def mock_nominatim():
    """Mock Nominatim geocoder"""
    mock = Mock()
    mock.reverse.return_value = Mock(
        address="Via dell'Oriuolo, Firenze, Tuscany, Italy"
    )
    return mock


@pytest.fixture
def mock_weather_response():
    """Mock weather API response"""
    return {
        "latitude": 43.7701,
        "longitude": 11.2556,
        "current": {
            "temperature_2m": 22.5,
            "relative_humidity_2m": 65.0,
            "wind_speed_10m": 3.5,
            "visibility": 10000
        }
    }


@pytest.fixture
def mock_aqi_response():
    """Mock AQI API response"""
    return {
        "status": "ok",
        "data": {
            "aqi": 85,
            "pm25": 35,
            "pm10": 55,
            "no2": 40,
            "o3": 70,
            "so2": 15,
            "co": 800
        }
    }


@pytest.fixture
async def mock_aiohttp_session():
    """Mock aiohttp session"""
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"current": {
        "temperature_2m": 20.0,
        "relative_humidity_2m": 60.0,
        "wind_speed_10m": 2.5,
        "visibility": 9000
    }})
    mock_session.get.return_value.__aenter__.return_value = mock_response
    return mock_session


# ============= SECURITY TEST FIXTURES =============

@pytest.fixture
def valid_email_samples():
    """Valid email addresses"""
    return [
        "user@example.com",
        "test.user+tag@example.co.uk",
        "name.surname@company.org",
    ]


@pytest.fixture
def invalid_email_samples():
    """Invalid email addresses"""
    return [
        "invalid@",
        "@invalid.com",
        "no-at-sign.com",
        "spaces in@email.com",
        "double@@email.com",
    ]


@pytest.fixture
def valid_url_samples():
    """Valid URLs"""
    return [
        "https://example.com",
        "http://sub.example.org",
        "https://example.co.uk/path",
    ]


@pytest.fixture
def invalid_url_samples():
    """Invalid URLs"""
    return [
        "not-a-url",
        "ftp://invalid.com",
        "https://",
        "//example.com",
    ]


@pytest.fixture
def xss_injection_samples():
    """XSS injection payloads"""
    return [
        "<script>alert('xss')</script>",
        "<img src=x onerror='alert(1)'>",
        "javascript:alert('xss')",
        "<iframe src='evil.com'></iframe>",
    ]


@pytest.fixture
def sql_injection_samples():
    """SQL injection payloads"""
    return [
        "'; DROP TABLE users--",
        "1' OR '1'='1",
        "admin'--",
    ]


# ============= ASYNC TEST HELPERS =============

@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """Use asyncio backend for anyio tests"""
    return "asyncio"


# ============= CONTEXT MANAGERS =============

@pytest.fixture
def mock_external_apis(monkeypatch):
    """Mock all external API calls"""
    # Mock geopy.geocoders.Nominatim
    mock_geocoder = Mock()
    mock_geocoder.reverse.return_value = Mock(
        address="Via dell'Oriuolo, Firenze, Tuscany, Italy"
    )
    monkeypatch.setattr(
        "backend.services.geolocation.Nominatim",
        Mock(return_value=mock_geocoder)
    )
    
    # Mock aiohttp
    mock_session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "current": {
            "temperature_2m": 20.0,
            "relative_humidity_2m": 60.0,
            "wind_speed_10m": 2.5,
            "visibility": 9000
        }
    })
    mock_session.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
    
    return {
        "geocoder": mock_geocoder,
        "session": mock_session,
    }
