"""
Geolocation and environmental data service
"""
import logging
import aiohttp
from typing import Optional, Dict, Any, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from datetime import datetime
import asyncio

from backend.models.schemas import GeoLocation, EnvironmentalData

logger = logging.getLogger(__name__)


class GeolocationService:
    """Handle geolocation and reverse geocoding"""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="swv_air_quality_monitor")
        self.cache = {}  # Simple cache for coordinates
    
    def get_address_from_coordinates(
        self, 
        latitude: float, 
        longitude: float,
        accuracy: Optional[float] = None
    ) -> GeoLocation:
        """
        Get address from coordinates using reverse geocoding
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            accuracy: GPS accuracy in meters
            
        Returns:
            GeoLocation object
        """
        try:
            # Check cache
            cache_key = f"{latitude:.4f},{longitude:.4f}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Reverse geocode
            location = self.geocoder.reverse(f"{latitude}, {longitude}", language="it")
            
            # Parse address
            address_parts = location.address.split(",")
            
            geo_location = GeoLocation(
                latitude=latitude,
                longitude=longitude,
                address=location.address,
                country=self._extract_country(location.address),
                region=self._extract_region(location.address),
                city=self._extract_city(location.address),
                accuracy_meters=accuracy
            )
            
            # Cache result
            self.cache[cache_key] = geo_location
            
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
        # This is a simplified approach - in production, use proper parsing
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
    """Fetch weather and environmental data from external APIs"""
    
    # Open-Meteo API (free, no key required)
    OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
    
    # Air Quality Index API (free)
    AQI_API = "https://api.waqi.info/feed"
    
    @staticmethod
    async def get_weather_data(
        latitude: float, 
        longitude: float
    ) -> Optional[EnvironmentalData]:
        """
        Fetch current weather data from Open-Meteo API
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            EnvironmentalData object or None if failed
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather,wind_speed_10m,visibility",
                "timezone": "auto"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(WeatherService.OPEN_METEO_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"Weather API returned {response.status}")
                        return None
                    
                    data = await response.json()
                    current = data.get("current", {})
                    
                    return EnvironmentalData(
                        temperature=current.get("temperature_2m"),
                        humidity=current.get("relative_humidity_2m"),
                        wind_speed=current.get("wind_speed_10m"),
                        visibility=current.get("visibility")
                    )
        
        except asyncio.TimeoutError:
            logger.warning("Weather API timeout")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return None
    
    @staticmethod
    async def get_aqi_data(
        latitude: float,
        longitude: float,
        aqi_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch AQI data from WAQI API
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            aqi_token: WAQI API token (optional)
            
        Returns:
            AQI data dictionary or None
        """
        if not aqi_token:
            logger.info("AQI token not provided, skipping external AQI data")
            return None
        
        try:
            params = {
                "token": aqi_token,
                "latlng": f"{latitude},{longitude}"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(WeatherService.AQI_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.warning(f"AQI API returned {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if data.get("status") != "ok":
                        logger.warning("AQI API returned non-ok status")
                        return None
                    
                    return data.get("data", {})
        
        except asyncio.TimeoutError:
            logger.warning("AQI API timeout")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch AQI data: {e}")
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
        
        Returns:
            Tuple of (GeoLocation, EnvironmentalData, AQI_data)
        """
        # Get location info
        geo_location = self.geo_service.get_address_from_coordinates(latitude, longitude, accuracy)
        
        # Get weather data (async)
        environmental_data = await self.weather_service.get_weather_data(latitude, longitude)
        
        # Get AQI data (async)
        aqi_data = await self.weather_service.get_aqi_data(latitude, longitude, self.aqi_token)
        
        return geo_location, environmental_data, aqi_data
