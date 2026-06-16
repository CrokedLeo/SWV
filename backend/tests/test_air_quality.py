"""
Unit tests for air_quality.py module
Tests: SmokeAnalyzer, PollutantPredictor, AQI calculations
"""
import pytest
import numpy as np
import cv2
from backend.services.air_quality import SmokeAnalyzer, PollutantPredictor
from backend.models.schemas import (
    SmokeLevel, PollutantType, SmokeAnalysis, PollutantReading
)


# ============= SMOKE ANALYZER TESTS =============

class TestSmokeAnalyzer:
    """Test SmokeAnalyzer class"""
    
    @pytest.mark.unit
    def test_categorize_smoke_level_excellent(self):
        """Test smoke level categorization - excellent"""
        level = SmokeAnalyzer._categorize_smoke_level(10.0)
        assert level == SmokeLevel.EXCELLENT
    
    @pytest.mark.unit
    def test_categorize_smoke_level_good(self):
        """Test smoke level categorization - good"""
        level = SmokeAnalyzer._categorize_smoke_level(30.0)
        assert level == SmokeLevel.GOOD
    
    @pytest.mark.unit
    def test_categorize_smoke_level_moderate(self):
        """Test smoke level categorization - moderate"""
        level = SmokeAnalyzer._categorize_smoke_level(50.0)
        assert level == SmokeLevel.MODERATE
    
    @pytest.mark.unit
    def test_categorize_smoke_level_poor(self):
        """Test smoke level categorization - poor"""
        level = SmokeAnalyzer._categorize_smoke_level(70.0)
        assert level == SmokeLevel.POOR
    
    @pytest.mark.unit
    def test_categorize_smoke_level_hazardous(self):
        """Test smoke level categorization - hazardous"""
        level = SmokeAnalyzer._categorize_smoke_level(90.0)
        assert level == SmokeLevel.HAZARDOUS
    
    @pytest.mark.unit
    def test_categorize_smoke_level_boundaries(self):
        """Test smoke level categorization boundaries"""
        # Test exact boundaries
        assert SmokeAnalyzer._categorize_smoke_level(19.9) == SmokeLevel.EXCELLENT
        assert SmokeAnalyzer._categorize_smoke_level(20.0) == SmokeLevel.GOOD
        assert SmokeAnalyzer._categorize_smoke_level(39.9) == SmokeLevel.GOOD
        assert SmokeAnalyzer._categorize_smoke_level(40.0) == SmokeLevel.MODERATE
    
    @pytest.mark.unit
    def test_analyze_smoke_in_clear_image(self, create_sample_image):
        """Test smoke analysis on clear image"""
        # Create clear blue sky image
        image = create_sample_image(width=640, height=480, color=(100, 150, 200))
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert isinstance(result, SmokeAnalysis)
        assert result.smoke_percentage >= 0
        assert result.smoke_percentage <= 100
        assert result.smoke_level in [sl for sl in SmokeLevel]
    
    @pytest.mark.unit
    def test_analyze_smoke_in_smoky_image(self, create_sample_image):
        """Test smoke analysis on smoky image"""
        # Create image with smoke (gray areas)
        image = create_sample_image(width=640, height=480, color=(128, 128, 128))
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert result.smoke_percentage > 0
        assert result.dominant_color is not None
        assert len(result.dominant_color) == 3
    
    @pytest.mark.unit
    def test_analyze_smoke_density_distribution(self, create_sample_image):
        """Test smoke density distribution analysis"""
        image = create_sample_image(width=600, height=600, color=(100, 100, 100))
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        # Check all 9 regions are present
        assert len(result.density_distribution) == 9
        assert "top_left" in result.density_distribution
        assert "mid_center" in result.density_distribution
        assert "bottom_right" in result.density_distribution
        
        # All densities should be 0-100
        for density in result.density_distribution.values():
            assert 0 <= density <= 100
    
    @pytest.mark.unit
    def test_analyze_smoke_opacity_calculation(self, create_sample_image):
        """Test opacity calculation"""
        image = create_sample_image(width=640, height=480, color=(100, 100, 100))
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert 0 <= result.opacity <= 1.0
    
    @pytest.mark.unit
    def test_analyze_smoke_particle_detection(self, create_sample_image):
        """Test particle cluster detection"""
        image = create_sample_image(width=640, height=480, color=(200, 200, 200))
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert result.particles_detected >= 0
    
    @pytest.mark.unit
    def test_get_dominant_color(self, sample_image_rgb):
        """Test dominant color extraction"""
        # Create mask of mid-gray area
        mask = np.zeros((480, 640), dtype=np.uint8)
        mask[100:200, 100:300] = 255
        
        color = SmokeAnalyzer._get_dominant_color(sample_image_rgb, mask)
        
        assert len(color) == 3
        assert all(0 <= c <= 255 for c in color)
    
    @pytest.mark.unit
    def test_get_dominant_color_empty_mask(self, sample_image_rgb):
        """Test dominant color with empty mask"""
        mask = np.zeros((480, 640), dtype=np.uint8)
        
        color = SmokeAnalyzer._get_dominant_color(sample_image_rgb, mask)
        
        # Should return default gray
        assert color == (128, 128, 128)


# ============= POLLUTANT PREDICTOR TESTS =============

class TestPollutantPredictor:
    """Test PollutantPredictor class"""
    
    @pytest.mark.unit
    def test_calculate_aqi_low_pollutant(self):
        """Test AQI calculation for low pollutant level"""
        # PM2.5 at excellent level (< 12)
        aqi = PollutantPredictor._calculate_aqi(PollutantType.PM25, 10.0)
        assert 0 <= aqi <= 50
    
    @pytest.mark.unit
    def test_calculate_aqi_good_level(self):
        """Test AQI calculation for good level"""
        aqi = PollutantPredictor._calculate_aqi(PollutantType.PM25, 20.0)
        assert 50 < aqi <= 100
    
    @pytest.mark.unit
    def test_calculate_aqi_moderate_level(self):
        """Test AQI calculation for moderate level"""
        aqi = PollutantPredictor._calculate_aqi(PollutantType.PM25, 45.0)
        assert 100 < aqi <= 150
    
    @pytest.mark.unit
    def test_calculate_aqi_high_level(self):
        """Test AQI calculation for high level"""
        aqi = PollutantPredictor._calculate_aqi(PollutantType.PM25, 75.0)
        assert 150 < aqi <= 200
    
    @pytest.mark.unit
    def test_calculate_aqi_very_high_level(self):
        """Test AQI calculation for very high level"""
        aqi = PollutantPredictor._calculate_aqi(PollutantType.PM25, 200.0)
        assert aqi > 200
    
    @pytest.mark.unit
    def test_calculate_aqi_all_pollutants(self):
        """Test AQI calculation for all pollutant types"""
        pollutants = [
            (PollutantType.PM25, 25.0),
            (PollutantType.PM10, 75.0),
            (PollutantType.NO2, 50.0),
            (PollutantType.O3, 80.0),
            (PollutantType.SO2, 30.0),
            (PollutantType.CO, 800.0),
        ]
        
        for pollutant_type, concentration in pollutants:
            aqi = PollutantPredictor._calculate_aqi(pollutant_type, concentration)
            assert 0 <= aqi <= 500
    
    @pytest.mark.unit
    def test_determine_risk_level_low(self):
        """Test risk level determination - low"""
        risk = PollutantPredictor._determine_risk_level(40)
        assert risk == "low"
    
    @pytest.mark.unit
    def test_determine_risk_level_moderate(self):
        """Test risk level determination - moderate"""
        risk = PollutantPredictor._determine_risk_level(80)
        assert risk == "moderate"
    
    @pytest.mark.unit
    def test_determine_risk_level_high(self):
        """Test risk level determination - high"""
        risk = PollutantPredictor._determine_risk_level(180)
        assert risk == "high"
    
    @pytest.mark.unit
    def test_determine_risk_level_hazardous(self):
        """Test risk level determination - hazardous"""
        risk = PollutantPredictor._determine_risk_level(450)
        assert risk == "hazardous"
    
    @pytest.mark.unit
    def test_get_unit_for_pm25(self):
        """Test unit retrieval for PM2.5"""
        unit = PollutantPredictor._get_unit(PollutantType.PM25)
        assert unit == "µg/m³"
    
    @pytest.mark.unit
    def test_get_unit_for_gas_pollutants(self):
        """Test unit retrieval for gas pollutants"""
        assert PollutantPredictor._get_unit(PollutantType.NO2) == "ppb"
        assert PollutantPredictor._get_unit(PollutantType.O3) == "ppb"
        assert PollutantPredictor._get_unit(PollutantType.CO) == "ppm"
    
    @pytest.mark.unit
    def test_estimate_pollutants(self, sample_smoke_analysis):
        """Test pollutant estimation from smoke analysis"""
        readings = PollutantPredictor.estimate_pollutants(sample_smoke_analysis)
        
        assert len(readings) == 6  # 6 pollutant types
        assert all(isinstance(r, PollutantReading) for r in readings)
        assert all(0 <= r.aqi_index <= 500 for r in readings)
        assert all(r.value >= 0 for r in readings)
    
    @pytest.mark.unit
    def test_estimate_pollutants_hazardous_smoke(self):
        """Test pollutant estimation with hazardous smoke level"""
        smoke_analysis = SmokeAnalysis(
            smoke_percentage=85.0,
            smoke_level=SmokeLevel.HAZARDOUS,
            density_distribution={
                "top_left": 80.0, "top_center": 85.0, "top_right": 88.0,
                "mid_left": 86.0, "mid_center": 90.0, "mid_right": 87.0,
                "bottom_left": 82.0, "bottom_center": 84.0, "bottom_right": 83.0,
            },
            dominant_color=(100, 100, 100),
            particles_detected=500,
            opacity=0.8
        )
        
        readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # Hazardous smoke should result in higher pollutant levels
        avg_aqi = sum(r.aqi_index for r in readings) / len(readings)
        assert avg_aqi > 150  # Should be elevated
    
    @pytest.mark.unit
    def test_get_overall_aqi(self):
        """Test overall AQI calculation"""
        readings = [
            PollutantReading(
                pollutant_type=PollutantType.PM25,
                value=25.0,
                unit="µg/m³",
                aqi_index=75,
                risk_level="moderate"
            ),
            PollutantReading(
                pollutant_type=PollutantType.PM10,
                value=60.0,
                unit="µg/m³",
                aqi_index=100,
                risk_level="moderate"
            ),
            PollutantReading(
                pollutant_type=PollutantType.NO2,
                value=40.0,
                unit="ppb",
                aqi_index=80,
                risk_level="moderate"
            ),
        ]
        
        overall_aqi = PollutantPredictor.get_overall_aqi(readings)
        assert overall_aqi == 100  # Maximum of all
    
    @pytest.mark.unit
    def test_get_overall_aqi_empty_list(self):
        """Test overall AQI with empty list"""
        overall_aqi = PollutantPredictor.get_overall_aqi([])
        assert overall_aqi == 0
    
    @pytest.mark.unit
    def test_get_health_recommendations_good(self):
        """Test health recommendations for good air quality"""
        summary, recommendations = PollutantPredictor.get_health_recommendations(40)
        assert "satisfactory" in summary.lower()
        assert len(recommendations) > 0
    
    @pytest.mark.unit
    def test_get_health_recommendations_poor(self):
        """Test health recommendations for poor air quality"""
        summary, recommendations = PollutantPredictor.get_health_recommendations(180)
        assert "unhealthy" in summary.lower()
        assert len(recommendations) > 0
    
    @pytest.mark.unit
    def test_get_health_recommendations_hazardous(self):
        """Test health recommendations for hazardous air quality"""
        summary, recommendations = PollutantPredictor.get_health_recommendations(450)
        assert "hazardous" in summary.lower()
        assert len(recommendations) > 0
    
    @pytest.mark.unit
    def test_get_affected_groups_good_aqi(self):
        """Test affected groups for good AQI"""
        groups = PollutantPredictor.get_affected_groups(40)
        assert "None - Air quality is good" in groups or len(groups) == 0
    
    @pytest.mark.unit
    def test_get_affected_groups_moderate_aqi(self):
        """Test affected groups for moderate AQI"""
        groups = PollutantPredictor.get_affected_groups(120)
        assert "Children and elderly" in groups or len([g for g in groups if g]) > 0
    
    @pytest.mark.unit
    def test_get_affected_groups_hazardous_aqi(self):
        """Test affected groups for hazardous AQI"""
        groups = PollutantPredictor.get_affected_groups(400)
        assert len(groups) > 0
        assert "General population" in groups


# ============= EDGE CASE AND BOUNDARY TESTS =============

class TestSmokeAnalyzerEdgeCases:
    """Test edge cases for smoke analyzer"""
    
    @pytest.mark.unit
    def test_analyze_very_small_image(self):
        """Test analysis on very small image"""
        image = np.full((10, 10, 3), (100, 100, 100), dtype=np.uint8)
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert result is not None
        assert result.smoke_percentage >= 0
    
    @pytest.mark.unit
    def test_analyze_large_image(self):
        """Test analysis on large image"""
        image = np.full((2000, 2000, 3), (100, 100, 100), dtype=np.uint8)
        
        result = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        assert result is not None
        assert 0 <= result.smoke_percentage <= 100
    
    @pytest.mark.unit
    def test_smoke_percentage_boundaries(self):
        """Test smoke percentage at boundaries"""
        assert SmokeAnalyzer._categorize_smoke_level(0.0) == SmokeLevel.EXCELLENT
        assert SmokeAnalyzer._categorize_smoke_level(100.0) == SmokeLevel.HAZARDOUS


# ============= AQI THRESHOLD TESTS =============

class TestAQIThresholds:
    """Test AQI threshold calculations"""
    
    @pytest.mark.unit
    def test_aqi_thresholds_exist_for_all_pollutants(self):
        """Test that AQI thresholds exist for all pollutants"""
        for pollutant_type in PollutantType:
            assert pollutant_type in SmokeAnalyzer.AQI_THRESHOLDS
    
    @pytest.mark.unit
    def test_aqi_level_progression(self):
        """Test AQI levels progress correctly"""
        levels = SmokeAnalyzer.AQI_LEVELS
        
        for i in range(len(levels) - 1):
            assert levels[i] < levels[i + 1]
    
    @pytest.mark.unit
    def test_aqi_montonicity(self):
        """Test that AQI increases monotonically with concentration"""
        pollutant_type = PollutantType.PM25
        concentrations = [0, 10, 20, 50, 100, 200, 300]
        aqi_values = [
            PollutantPredictor._calculate_aqi(pollutant_type, c) 
            for c in concentrations
        ]
        
        for i in range(len(aqi_values) - 1):
            assert aqi_values[i] <= aqi_values[i + 1]


# ============= INTEGRATION TESTS =============

class TestAirQualityIntegration:
    """Integration tests for air quality module"""
    
    @pytest.mark.integration
    def test_complete_analysis_workflow(self, create_sample_image):
        """Test complete smoke analysis workflow"""
        # Create test image
        image = create_sample_image(width=640, height=480, color=(120, 120, 120))
        
        # Analyze smoke
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        # Estimate pollutants
        readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # Get overall AQI
        overall_aqi = PollutantPredictor.get_overall_aqi(readings)
        
        # Get recommendations
        summary, recommendations = PollutantPredictor.get_health_recommendations(overall_aqi)
        
        assert smoke_analysis is not None
        assert len(readings) > 0
        assert overall_aqi >= 0
        assert summary is not None
        assert len(recommendations) > 0
    
    @pytest.mark.integration
    def test_varying_smoke_levels(self, create_sample_image):
        """Test analysis with varying smoke levels"""
        smoke_levels = [
            (20, SmokeLevel.EXCELLENT),
            (50, SmokeLevel.MODERATE),
            (80, SmokeLevel.POOR),
        ]
        
        for smoke_color_intensity, expected_level_range in smoke_levels:
            # Create image with specific smoke color
            color = (smoke_color_intensity, smoke_color_intensity, smoke_color_intensity)
            image = create_sample_image(width=640, height=480, color=color)
            
            result = SmokeAnalyzer.analyze_smoke_in_image(image)
            
            # Verify analysis produces valid results
            assert result.smoke_level in [sl for sl in SmokeLevel]
            assert 0 <= result.smoke_percentage <= 100
