"""
Smoke and air quality analysis service
"""
import logging
import numpy as np
import cv2
from typing import Tuple, Dict, Any, List
from backend.models.schemas import SmokeAnalysis, SmokeLevel, PollutantReading, PollutantType

logger = logging.getLogger(__name__)


class SmokeAnalyzer:
    """Analyze smoke levels and air quality from images"""
    
    # Color ranges for smoke detection in HSV
    SMOKE_HSV_LOWER = np.array([0, 0, 50])      # Lower bound for gray/brown smoke
    SMOKE_HSV_UPPER = np.array([180, 50, 200])  # Upper bound for smoke
    
    # Pollutant correlations with smoke levels
    POLLUTANT_CORRELATION = {
        "excellent": {"PM2.5": 0, "PM10": 0, "NO2": 5, "O3": 40, "SO2": 2, "CO": 300},
        "good": {"PM2.5": 12, "PM10": 30, "NO2": 40, "O3": 70, "SO2": 10, "CO": 600},
        "moderate": {"PM2.5": 35, "PM10": 55, "NO2": 70, "O3": 100, "SO2": 25, "CO": 1000},
        "poor": {"PM2.5": 55, "PM10": 150, "NO2": 120, "O3": 150, "SO2": 50, "CO": 2000},
        "hazardous": {"PM2.5": 150, "PM10": 250, "NO2": 200, "O3": 200, "SO2": 100, "CO": 4000}
    }
    
    # AQI thresholds
    AQI_THRESHOLDS = {
        PollutantType.PM25: [12, 35.5, 55.5, 150.5, 250.5],
        PollutantType.PM10: [54, 155, 255, 355, 500],
        PollutantType.NO2: [53, 100, 360, 649, 1249],
        PollutantType.O3: [54, 70, 85, 105, 200],
        PollutantType.SO2: [35, 75, 185, 304, 604],
        PollutantType.CO: [4.4, 9.4, 12.4, 15.4, 30.4]
    }
    
    AQI_LEVELS = [50, 100, 150, 200, 300, 500]
    
    @staticmethod
    def analyze_smoke_in_image(image: np.ndarray) -> SmokeAnalysis:
        """
        Analyze smoke levels in image
        
        Args:
            image: Image as numpy array (RGB)
            
        Returns:
            SmokeAnalysis object with results
        """
        try:
            # Convert to HSV for better smoke detection
            image_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            
            # Detect smoke/particles using color range
            mask = cv2.inRange(image_hsv, SmokeAnalyzer.SMOKE_HSV_LOWER, SmokeAnalyzer.SMOKE_HSV_UPPER)
            
            # Calculate smoke percentage
            total_pixels = mask.size
            smoke_pixels = cv2.countNonZero(mask)
            smoke_percentage = (smoke_pixels / total_pixels) * 100
            
            # Categorize smoke level
            smoke_level = SmokeAnalyzer._categorize_smoke_level(smoke_percentage)
            
            # Analyze smoke density distribution across regions
            density_distribution = SmokeAnalyzer._analyze_density_distribution(mask, image.shape)
            
            # Find dominant smoke color
            dominant_color = SmokeAnalyzer._get_dominant_color(image, mask)
            
            # Detect particles (clusters)
            particles_detected = SmokeAnalyzer._detect_particle_clusters(mask)
            
            # Calculate opacity (overall darkening)
            opacity = SmokeAnalyzer._calculate_opacity(image)
            
            return SmokeAnalysis(
                smoke_percentage=round(smoke_percentage, 2),
                smoke_level=smoke_level,
                density_distribution=density_distribution,
                dominant_color=dominant_color,
                particles_detected=particles_detected,
                opacity=round(opacity, 3)
            )
            
        except Exception as e:
            logger.error(f"Smoke analysis failed: {e}")
            raise
    
    @staticmethod
    def _categorize_smoke_level(smoke_percentage: float) -> SmokeLevel:
        """Categorize smoke level from percentage"""
        if smoke_percentage < 20:
            return SmokeLevel.EXCELLENT
        elif smoke_percentage < 40:
            return SmokeLevel.GOOD
        elif smoke_percentage < 60:
            return SmokeLevel.MODERATE
        elif smoke_percentage < 80:
            return SmokeLevel.POOR
        else:
            return SmokeLevel.HAZARDOUS
    
    @staticmethod
    def _analyze_density_distribution(mask: np.ndarray, image_shape: Tuple) -> Dict[str, float]:
        """Analyze smoke density across image regions"""
        height, width = image_shape[:2]
        
        # Divide image into 9 regions (3x3 grid)
        regions = {}
        region_names = [
            "top_left", "top_center", "top_right",
            "mid_left", "mid_center", "mid_right",
            "bottom_left", "bottom_center", "bottom_right"
        ]
        
        h_step = height // 3
        w_step = width // 3
        
        idx = 0
        for row in range(3):
            for col in range(3):
                y_start = row * h_step
                y_end = (row + 1) * h_step if row < 2 else height
                x_start = col * w_step
                x_end = (col + 1) * w_step if col < 2 else width
                
                region_mask = mask[y_start:y_end, x_start:x_end]
                region_density = (cv2.countNonZero(region_mask) / region_mask.size) * 100
                regions[region_names[idx]] = round(region_density, 2)
                idx += 1
        
        return regions
    
    @staticmethod
    def _get_dominant_color(image: np.ndarray, mask: np.ndarray) -> Tuple[int, int, int]:
        """Get dominant smoke color"""
        # Apply mask to image
        masked_image = cv2.bitwise_and(image, image, mask=mask)
        
        # Flatten and remove black pixels
        pixels = masked_image.reshape(-1, 3)
        pixels = pixels[np.any(pixels != 0, axis=1)]
        
        if len(pixels) == 0:
            return (128, 128, 128)  # Gray if no smoke detected
        
        # Calculate mean color
        mean_color = pixels.mean(axis=0).astype(int)
        return tuple(map(int, mean_color))
    
    @staticmethod
    def _detect_particle_clusters(mask: np.ndarray) -> int:
        """Detect number of particle clusters"""
        # Apply morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated = cv2.dilate(mask, kernel, iterations=2)
        
        # Find contours (clusters)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return len(contours)
    
    @staticmethod
    def _calculate_opacity(image: np.ndarray) -> float:
        """Calculate overall image opacity/darkening"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # Mean brightness (0 = dark, 255 = bright)
        mean_brightness = gray.mean() / 255.0
        
        # Opacity is inverse of brightness
        opacity = 1.0 - mean_brightness
        
        return opacity


class PollutantPredictor:
    """Predict pollutant levels based on smoke analysis"""
    
    @staticmethod
    def estimate_pollutants(smoke_analysis: SmokeAnalysis) -> List[PollutantReading]:
        """
        Estimate pollutant concentrations based on smoke analysis
        
        Args:
            smoke_analysis: Smoke analysis results
            
        Returns:
            List of estimated pollutant readings
        """
        smoke_level_key = smoke_analysis.smoke_level.value
        pollutant_values = SmokeAnalyzer.POLLUTANT_CORRELATION[smoke_level_key]
        
        readings = []
        for pollutant_type_str, base_value in pollutant_values.items():
            pollutant_type = PollutantType(pollutant_type_str)
            
            # Adjust value based on opacity and particles
            adjusted_value = base_value * (1 + smoke_analysis.opacity) * (1 + smoke_analysis.particles_detected / 100)
            
            # Get AQI index
            aqi_index = PollutantPredictor._calculate_aqi(pollutant_type, adjusted_value)
            
            # Determine risk level
            risk_level = PollutantPredictor._determine_risk_level(aqi_index)
            
            # Get unit
            unit = PollutantPredictor._get_unit(pollutant_type)
            
            readings.append(PollutantReading(
                pollutant_type=pollutant_type,
                value=round(adjusted_value, 2),
                unit=unit,
                aqi_index=aqi_index,
                risk_level=risk_level
            ))
        
        return readings
    
    @staticmethod
    def _calculate_aqi(pollutant_type: PollutantType, concentration: float) -> int:
        """
        Calculate AQI for a specific pollutant
        Using simplified EPA AQI calculation
        """
        thresholds = SmokeAnalyzer.AQI_THRESHOLDS[pollutant_type]
        aqi_levels = SmokeAnalyzer.AQI_LEVELS
        
        if concentration <= thresholds[0]:
            aqi = (concentration / thresholds[0]) * aqi_levels[0]
        else:
            for i in range(len(thresholds) - 1):
                if concentration <= thresholds[i + 1]:
                    bp_hi = thresholds[i + 1]
                    bp_lo = thresholds[i]
                    aqi_hi = aqi_levels[i + 1]
                    aqi_lo = aqi_levels[i]
                    
                    aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + aqi_lo
                    return int(aqi)
            
            aqi = aqi_levels[-1]
        
        return int(aqi)
    
    @staticmethod
    def _determine_risk_level(aqi_index: int) -> str:
        """Determine health risk level from AQI"""
        if aqi_index <= 50:
            return "low"
        elif aqi_index <= 100:
            return "moderate"
        elif aqi_index <= 150:
            return "moderate_high"
        elif aqi_index <= 200:
            return "high"
        elif aqi_index <= 300:
            return "very_high"
        else:
            return "hazardous"
    
    @staticmethod
    def _get_unit(pollutant_type: PollutantType) -> str:
        """Get measurement unit for pollutant"""
        units = {
            PollutantType.PM25: "µg/m³",
            PollutantType.PM10: "µg/m³",
            PollutantType.NO2: "ppb",
            PollutantType.O3: "ppb",
            PollutantType.SO2: "ppb",
            PollutantType.CO: "ppm"
        }
        return units.get(pollutant_type, "µg/m³")
    
    @staticmethod
    def get_overall_aqi(readings: List[PollutantReading]) -> int:
        """Get overall AQI (maximum of all pollutants)"""
        return max([r.aqi_index for r in readings]) if readings else 0
    
    @staticmethod
    def get_health_recommendations(aqi_index: int) -> Tuple[str, List[str]]:
        """Get health recommendations based on AQI"""
        if aqi_index <= 50:
            return "Air quality is satisfactory.", [
                "Enjoy outdoor activities",
                "Perfect conditions for outdoor sports"
            ]
        elif aqi_index <= 100:
            return "Air quality is acceptable.", [
                "Outdoor activities are acceptable",
                "Unusually sensitive people should consider limiting outdoor exposure"
            ]
        elif aqi_index <= 150:
            return "Air quality is unhealthy for sensitive groups.", [
                "Members of sensitive groups may experience health effects",
                "General public unlikely to be affected"
            ]
        elif aqi_index <= 200:
            return "Air quality is unhealthy.", [
                "Everyone may experience health effects",
                "Minimize outdoor activities"
            ]
        elif aqi_index <= 300:
            return "Air quality is very unhealthy.", [
                "Health alert: everyone should avoid outdoor activities",
                "Stay indoors and keep activity levels low"
            ]
        else:
            return "Air quality is hazardous.", [
                "Health warning: avoid all outdoor exertion",
                "Stay indoors completely"
            ]
    
    @staticmethod
    def get_affected_groups(aqi_index: int) -> List[str]:
        """Get list of groups affected at current AQI level"""
        groups = []
        
        if aqi_index > 50:
            groups.append("Children and elderly")
        if aqi_index > 100:
            groups.extend(["People with respiratory disease", "People with heart disease"])
        if aqi_index > 150:
            groups.append("General population")
        if aqi_index > 200:
            groups.append("Athletes and active people")
        
        return groups if groups else ["None - Air quality is good"]
