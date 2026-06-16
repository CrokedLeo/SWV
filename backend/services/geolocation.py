"""
Geolocation and environmental data service with resilience patterns
"""
import logging
import aiohttp
from typing import Optional, Dict, Any, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from datetime import datetime
import asyncio

from backend.models.schemas import GeoLocation, EnvironmentalData
from backend.services.cache import cache_manager
from backend.services.resilience import (
    circuit_breaker,
    retry_policy,
    ErrorRecovery,
    health_monitor
)

logger = logging.getLogger(__name__)


class GeolocationService:
    """Handle geolocation and reverse geocoding"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="swv_air_quality_monitor")
    
    def get_address_from_coordinates(
        self, 
        latitude: float, 
        longitude: float,
        accuracy: Optional[float] = None
    ) -> GeoLocation:
        """
        Get address from coordinates using reverse geocoding
        With caching for performance
        """
        try:
            # Check cache first
            cached = cache_manager.get_cached_geolocation(latitude, longitude)
            if cached:
                logger.info(f"✓ Geolocation cache HIT: ({latitude}, {longitude})")
                return cached
            
            # Reverse geocode
            location = self.geocoder.reverse(f"{latitude}, {longitude}", language="it")
            
            # Parse address
            geo_location = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=location.address,
                country=self._extract_country(location.address),
                region=self._extract_region(location.address),
                city=self._extract_city(location.address),
                accuracy_meters=accuracy
            )
            
            # Cache for 24 hours
            cache_manager.cache_geolocation(geo_location, latitude, longitude, ttl=86400)
            logger.info(f"✓ Geolocation cache SET: ({latitude}, {longitude})")
            
            return geo_location
            
        except GeocoderTimedOut:
            logger.warning(f"Geocoding timeout for {latitude}, {longitude}")
            return GeoLocation(
                latitude=latitude,
                longitude=longitude,
                accuracy_meters=accuracy
            )
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            return GeoLocation(
                latitude=latitude,
                longitude=longitude,
                accuracy_meters=accuracy
            )
    
    @staticmethod
    def _extract_country(address: str) -> Optional[str]:
        """Extract country from address string"""
        parts = address.split(",")
        return parts[-1].strip() if parts else None
    
    @staticmethod
    def _extract_region(address: str) -> Optional[str]:
        """Extract region/state from address string"""
        parts = address.split(",")
        if len(parts) >= 3:
            return parts[-2].strip()
        return None
    
    @staticmethod
    def _extract_city(address: str) -> Optional[str]:
        """Extract city from address string"""
        parts = address.split(",")
        if len(parts) >= 2:
            return parts[-3].strip() if len(parts) >= 3 else parts[0].strip()
        return None
    
    @staticmethod
    def calculate_distance(
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two coordinates in km
        Using Haversine formula
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth's radius in km
        
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c


class WeatherService:
    """Fetch weather and environmental data from external APIs with resilience"""
    
    # Open-Meteo API (free, no key required)
    OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
    
    # Air Quality Index API (free)
    AQI_API = "https://api.waqi.info/feed"
    
    @staticmethod
    async def _fetch_weather_api(
        latitude: float, 
        longitude: float
    ) -> Optional[EnvironmentalData]:
        """Internal method to fetch weather from API (used by retry logic)"""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather,wind_speed_10m,visibility",
            "timezone": "auto"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WeatherService.OPEN_METEO_API, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Weather API returned {response.status}")
                    raise Exception(f"Weather API returned {response.status}")
                
                data = await response.json()
                current = data.get("current", {})
                
                env_data = EnvironmentalData(
                    temperature=current.get("temperature_2m"),
                    humidity=current.get("relative_humidity_2m"),
                    wind_speed=current.get("wind_speed_10m"),
                    visibility=current.get("visibility")
                )
                
                return env_data
    
    @staticmethod
    async def get_weather_data(
        latitude: float, 
        longitude: float
    ) -> Optional[EnvironmentalData]:
        """
        Fetch current weather data from Open-Meteo API with retry + circuit breaker
        
        Flow:
        1. Check cache first
        2. Try API call with circuit breaker + retry
        3. On failure: use cached data or return None
        """
        endpoint = "weather_api"
        
        try:
            # Check cache first
            cached = cache_manager.get_cached_weather(latitude, longitude)
            if cached:
                logger.info(f"✓ Weather cache HIT: ({latitude}, {longitude})")
                return cached
            
            # Execute with circuit breaker + retry
            env_data = await circuit_breaker.execute_async(
                endpoint,
                retry_policy.execute_async,
                WeatherService._fetch_weather_api,
                latitude,
                longitude
            )
            
            # Cache for 30 minutes
            cache_manager.cache_weather(env_data, latitude, longitude, ttl=1800)
            logger.info(f"✓ Weather cache SET: ({latitude}, {longitude})")
            health_monitor.update_status("weather_api", True)
            
            return env_data
        
        except asyncio.TimeoutError:
            logger.warning(f"✗ Weather API timeout for ({latitude}, {longitude})")
            health_monitor.update_status("weather_api", False, error_message="Timeout")
            # Fall back to cached data
            return cache_manager.get_cached_weather(latitude, longitude)
        
        except Exception as e:
            logger.error(f"✗ Weather API failed: {str(e)[:100]}")
            health_monitor.update_status("weather_api", False, error_message=str(e))
            # Fall back to cached data
            return cache_manager.get_cached_weather(latitude, longitude)
    
    @staticmethod
    async def _fetch_aqi_api(
        latitude: float,
        longitude: float,
        aqi_token: str
    ) -> Optional[Dict[str, Any]]:
        """Internal method to fetch AQI from API (used by retry logic)"""
        params = {
            "token": aqi_token,
            "latlng": f"{latitude},{longitude}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WeatherService.AQI_API, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    logger.warning(f"AQI API returned {response.status}")
                    raise Exception(f"AQI API returned {response.status}")
                
                data = await response.json()
                
                if data.get("status") != "ok":
                    logger.warning("AQI API returned non-ok status")
                    raise Exception("AQI API returned non-ok status")
                
                return data.get("data", {})
    
    @staticmethod
    async def get_aqi_data(
        latitude: float,
        longitude: float,
        aqi_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch AQI data from WAQI API with retry + circuit breaker
        
        Flow:
        1. Try API call with circuit breaker + retry
        2. On failure: graceful degradation (return None)
        """
        if not aqi_token:
            logger.debug("AQI token not provided, skipping external AQI data")
            return None
        
        endpoint = "aqi_api"
        
        try:
            # Execute with circuit breaker + retry
            aqi_data = await circuit_breaker.execute_async(
                endpoint,
                retry_policy.execute_async,
                WeatherService._fetch_aqi_api,
                latitude,
                longitude,
                aqi_token
            )
            
            health_monitor.update_status("aqi_api", True)
            return aqi_data
        
        except asyncio.TimeoutError:
            logger.warning(f"✗ AQI API timeout for ({latitude}, {longitude})")
            health_monitor.update_status("aqi_api", False, error_message="Timeout")
            return None
        
        except Exception as e:
            logger.error(f"✗ AQI API failed: {str(e)[:100]}")
            health_monitor.update_status("aqi_api", False, error_message=str(e))
            return None


class EnvironmentalDataService:
    """Combined service for environmental data"""
    
    def __init__(self, aqi_token: Optional[str] = None):
        self.geo_service = GeolocationService()
        self.weather_service = WeatherService()
        self.aqi_token = aqi_token
    
    async def get_complete_environmental_data(
        self,
        latitude: float,
        longitude: float,
        accuracy: Optional[float] = None
    ) -> Tuple[GeoLocation, Optional[EnvironmentalData], Optional[Dict]]:
        """
        Get complete environmental data for a location
        
        Now uses parallel requests instead of sequential
        
        Returns:
            Tuple of (GeoLocation, EnvironmentalData, AQI_data)
        """
        # Get location info (sync, already cached)
        geo_location = self.geo_service.get_address_from_coordinates(latitude, longitude, accuracy)
        
        # Get weather and AQI data in parallel (much faster!)
        weather_task = self.weather_service.get_weather_data(latitude, longitude)
        aqi_task = self.weather_service.get_aqi_data(latitude, longitude, self.aqi_token)
        
        # Wait for both concurrently
        environmental_data, aqi_data = await asyncio.gather(weather_task, aqi_task, return_exceptions=True)
        
        # Handle exceptions
        if isinstance(environmental_data, Exception):
            logger.error(f"Weather fetch error: {environmental_data}")
            environmental_data = None
        if isinstance(aqi_data, Exception):
            logger.error(f"AQI fetch error: {aqi_data}")
            aqi_data = None
        
        return geo_location, environmental_data, aqi_data

