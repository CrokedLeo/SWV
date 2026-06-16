"""
Unit tests for geolocation.py module
Tests: GeolocationService, WeatherService, EnvironmentalDataService
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.services.geolocation import (
    GeolocationService, WeatherService, EnvironmentalDataService
)
from backend.models.schemas import GeoLocation, EnvironmentalData


# ============= GEOLOCATION SERVICE TESTS =============

class TestGeolocationService:
    """Test GeolocationService class"""
    
    @pytest.mark.unit
    def test_geolocation_service_creation(self):
        """Test creating geolocation service"""
        service = GeolocationService()
        assert service.geocoder is not None
    
    @pytest.mark.unit
    def test_extract_country_from_address(self):
        """Test country extraction"""
        address = "Via dell'Oriuolo, Firenze, Tuscany, Italy"
        country = GeolocationService._extract_country(address)
        assert country == "Italy"
    
    @pytest.mark.unit
    def test_extract_region_from_address(self):
        """Test region extraction"""
        address = "Via dell'Oriuolo, Firenze, Tuscany, Italy"
        region = GeolocationService._extract_region(address)
        assert region == "Tuscany"
    
    @pytest.mark.unit
    def test_extract_city_from_address(self):
        """Test city extraction"""
        address = "Via dell'Oriuolo, Firenze, Tuscany, Italy"
        city = GeolocationService._extract_city(address)
        assert city == "Firenze"
    
    @pytest.mark.unit
    def test_extract_from_short_address(self):
        """Test extraction from short address"""
        address = "Florence, Italy"
        country = GeolocationService._extract_country(address)
        city = GeolocationService._extract_city(address)
        assert country == "Italy"
        assert city == "Florence"
    
    @pytest.mark.unit
    def test_calculate_distance_same_location(self):
        """Test distance calculation for same location"""
        distance = GeolocationService.calculate_distance(43.7701, 11.2556, 43.7701, 11.2556)
        assert distance == 0.0 or distance < 0.01  # Should be very close to 0
    
    @pytest.mark.unit
    def test_calculate_distance_between_locations(self):
        """Test distance calculation between two locations"""
        # Florence to Rome (approximately 280 km)
        florence_lat, florence_lon = 43.7701, 11.2556
        rome_lat, rome_lon = 41.9028, 12.4964
        
        distance = GeolocationService.calculate_distance(
            florence_lat, florence_lon, rome_lat, rome_lon
        )
        
        # Should be approximately 230 km (±10)
        assert 220 < distance < 240
    
    @pytest.mark.unit
    def test_calculate_distance_symmetry(self):
        """Test distance calculation is symmetric"""
        lat1, lon1 = 43.7701, 11.2556
        lat2, lon2 = 41.9028, 12.4964
        
        dist1 = GeolocationService.calculate_distance(lat1, lon1, lat2, lon2)
        dist2 = GeolocationService.calculate_distance(lat2, lon2, lat1, lon1)
        
        assert abs(dist1 - dist2) < 0.01
    
    @pytest.mark.unit
    def test_get_address_from_coordinates_valid(self):
        """Test getting address from valid coordinates"""
        with patch('backend.services.geolocation.Nominatim') as mock_nominatim:
            mock_geocoder = Mock()
            mock_geocoder.reverse.return_value = Mock(
                address="Via dell'Oriuolo, Firenze, Tuscany, Italy"
            )
            mock_nominatim.return_value = mock_geocoder
            
            service = GeolocationService()
            service.geocoder = mock_geocoder
            
            result = service.get_address_from_coordinates(43.7701, 11.2556)
            
            assert isinstance(result, GeoLocation)
            assert result.latitude == 43.7701
            assert result.longitude == 11.2556
            assert result.country == "Italy"
    
    @pytest.mark.unit
    def test_get_address_caching(self):
        """Test address caching"""
        with patch('backend.services.geolocation.cache_manager') as mock_cache:
            mock_cache.get_cached_geolocation.return_value = GeoLocation(
                latitude=43.7701,
                longitude=11.2556,
                address="Cached Result"
            )
            
            with patch('backend.services.geolocation.Nominatim') as mock_nominatim:
                mock_geocoder = Mock()
                mock_nominatim.return_value = mock_geocoder
                
                service = GeolocationService()
                service.geocoder = mock_geocoder
                
                result = service.get_address_from_coordinates(43.7701, 11.2556)
                
                # Should use cached result
                mock_cache.get_cached_geolocation.assert_called_once()
    
    @pytest.mark.unit
    def test_get_address_timeout_handling(self):
        """Test handling of geocoding timeout"""
        from geopy.exc import GeocoderTimedOut
        
        with patch('backend.services.geolocation.Nominatim') as mock_nominatim:
            mock_geocoder = Mock()
            mock_geocoder.reverse.side_effect = GeocoderTimedOut()
            
            with patch('backend.services.geolocation.cache_manager') as mock_cache:
                mock_cache.get_cached_geolocation.return_value = None
                service = GeolocationService()
                service.geocoder = mock_geocoder
                
                result = service.get_address_from_coordinates(43.7701, 11.2556)
                
                # Should return partial result without address
                assert result.latitude == 43.7701
                assert result.longitude == 11.2556
                assert result.address is None


# ============= WEATHER SERVICE TESTS =============

class TestWeatherService:
    """Test WeatherService class"""
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_weather_data_success(self):
        """Test successful weather data retrieval"""
        mock_response = {
            "current": {
                "temperature_2m": 22.5,
                "relative_humidity_2m": 65.0,
                "wind_speed_10m": 3.5,
                "visibility": 10000
            }
        }
        
        with patch('backend.services.geolocation._get_http_session') as mock_get_session:
            mock_session_obj = MagicMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_obj.get.return_value = mock_ctx
            mock_get_session.return_value = mock_session_obj
            
            with patch('backend.services.geolocation.cache_manager') as mock_cache:
                mock_cache.get_cached_weather.return_value = None
                result = await WeatherService.get_weather_data(43.7701, 11.2556)
                
                assert isinstance(result, EnvironmentalData)
                assert result.temperature == 22.5
                assert result.humidity == 65.0
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_weather_data_api_error(self):
        """Test weather API error handling"""
        with patch('backend.services.geolocation._get_http_session') as mock_get_session:
            mock_session_obj = MagicMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 500
            
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_obj.get.return_value = mock_ctx
            mock_get_session.return_value = mock_session_obj
            
            with patch('backend.services.geolocation.cache_manager') as mock_cache:
                mock_cache.get_cached_weather.return_value = None
                result = await WeatherService.get_weather_data(43.7701, 11.2556)
                
                assert result is None
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_aqi_data_success(self):
        """Test successful AQI data retrieval"""
        mock_response = {
            "status": "ok",
            "data": {
                "aqi": 85,
                "pm25": 35,
                "pm10": 55
            }
        }
        
        with patch('backend.services.geolocation._get_http_session') as mock_get_session:
            mock_session_obj = MagicMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_obj.get.return_value = mock_ctx
            mock_get_session.return_value = mock_session_obj
            
            result = await WeatherService.get_aqi_data(43.7701, 11.2556, aqi_token="test_token")
            
            assert result is not None
            assert result["aqi"] == 85
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_aqi_data_no_token(self):
        """Test AQI data retrieval without token"""
        result = await WeatherService.get_aqi_data(43.7701, 11.2556, aqi_token=None)
        
        assert result is None
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_aqi_data_non_ok_status(self):
        """Test AQI data with non-ok status"""
        mock_response = {
            "status": "error",
            "data": {}
        }
        
        with patch('backend.services.geolocation._get_http_session') as mock_get_session:
            mock_session_obj = MagicMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.status = 200
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_obj.get.return_value = mock_ctx
            mock_get_session.return_value = mock_session_obj
            
            result = await WeatherService.get_aqi_data(43.7701, 11.2556, aqi_token="test_token")
            
            assert result is None


# ============= ENVIRONMENTAL DATA SERVICE TESTS =============

class TestEnvironmentalDataService:
    """Test EnvironmentalDataService class"""
    
    @pytest.mark.unit
    def test_service_creation(self):
        """Test creating environmental data service"""
        service = EnvironmentalDataService(aqi_token="test_token")
        assert service.geo_service is not None
        assert service.weather_service is not None
        assert service.aqi_token == "test_token"
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_complete_environmental_data(self):
        """Test getting complete environmental data"""
        with patch.object(
            GeolocationService, 'get_address_from_coordinates',
            return_value=GeoLocation(latitude=43.7701, longitude=11.2556)
        ):
            with patch.object(
                WeatherService, 'get_weather_data',
                new_callable=AsyncMock,
                return_value=EnvironmentalData(temperature=22.5, humidity=65.0)
            ):
                with patch.object(
                    WeatherService, 'get_aqi_data',
                    new_callable=AsyncMock,
                    return_value={"aqi": 85}
                ):
                    service = EnvironmentalDataService(aqi_token="test_token")
                    geo, env, aqi = await service.get_complete_environmental_data(
                        43.7701, 11.2556, accuracy=10.0
                    )
                    
                    assert geo.latitude == 43.7701
                    assert env.temperature == 22.5
                    assert aqi["aqi"] == 85
    
    @pytest.mark.async_test
    @pytest.mark.unit
    async def test_get_complete_environmental_data_with_error(self):
        """Test error handling in complete environmental data"""
        with patch.object(
            GeolocationService, 'get_address_from_coordinates',
            return_value=GeoLocation(latitude=43.7701, longitude=11.2556)
        ):
            with patch.object(
                WeatherService, 'get_weather_data',
                new_callable=AsyncMock,
                side_effect=Exception("API Error")
            ):
                with patch.object(
                    WeatherService, 'get_aqi_data',
                    new_callable=AsyncMock,
                    return_value={"aqi": 85}
                ):
                    service = EnvironmentalDataService(aqi_token="test_token")
                    geo, env, aqi = await service.get_complete_environmental_data(
                        43.7701, 11.2556
                    )
                    
                    assert geo.latitude == 43.7701
                    assert env is None  # Should handle error gracefully


# ============= EDGE CASE TESTS =============

class TestGeolocationEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.mark.unit
    def test_coordinate_edge_cases(self):
        """Test calculation at coordinate boundaries"""
        # Calculate distance across international date line
        dist = GeolocationService.calculate_distance(0, 179.9, 0, -179.9)
        assert dist > 0  # Should be small distance
    
    @pytest.mark.unit
    def test_address_extraction_single_part(self):
        """Test extraction from address with single part"""
        address = "Florence"
        country = GeolocationService._extract_country(address)
        assert country == "Florence"
    
    @pytest.mark.unit
    def test_address_extraction_empty(self):
        """Test extraction from empty address"""
        address = ""
        country = GeolocationService._extract_country(address)
        assert country == ""
    
    @pytest.mark.unit
    def test_coordinate_validation_precision(self):
        """Test coordinate precision handling"""
        # Test with high precision coordinates
        lat = 43.77010123456789
        lon = 11.25560123456789
        
        distance = GeolocationService.calculate_distance(lat, lon, lat, lon)
        assert distance < 0.001


# ============= CACHING TESTS =============

class TestGeolocationCaching:
    """Test caching behavior"""
    
    @pytest.mark.unit
    def test_cache_hit_rate(self):
        """Test cache hit rate improvement"""
        with patch('backend.services.geolocation.cache_manager') as mock_cache:
            mock_cache.get_cached_geolocation.return_value = None
            
            with patch('backend.services.geolocation.Nominatim') as mock_nominatim:
                mock_geocoder = Mock()
                mock_geocoder.reverse.return_value = Mock(
                    address="Via dell'Oriuolo, Firenze, Tuscany, Italy"
                )
                mock_nominatim.return_value = mock_geocoder
                
                service = GeolocationService()
                service.geocoder = mock_geocoder
                
                # First call - cache miss, should call geocoder and cache the result
                mock_cache.get_cached_geolocation.return_value = None
                result = service.get_address_from_coordinates(43.7701, 11.2556)
                
                assert mock_cache.get_cached_geolocation.call_count >= 1
                assert result.city == "Firenze"
