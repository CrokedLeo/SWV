"""
Environmental monitoring API routes
"""
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse

from backend.config.settings import settings
from backend.models.schemas import (
    EnvironmentalReport, 
    SmokeDetectionRequest,
    ErrorResponse
)
from backend.services.detection import get_detector, ImageProcessor
from backend.services.air_quality import SmokeAnalyzer, PollutantPredictor
from backend.services.geolocation import EnvironmentalDataService
from backend.services.report_generator import ReportGenerator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["environmental"])


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Verify API key from header"""
    if settings.API_KEY != "your-secret-key-change-in-production":
        if x_api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/analyze-smoke", response_model=EnvironmentalReport)
async def analyze_smoke_and_air_quality(
    file: UploadFile = File(...),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    accuracy: Optional[float] = Query(None, ge=0, description="GPS accuracy in meters"),
    confidence: float = Query(0.5, ge=0, le=1),
    include_weather: bool = Query(True, description="Include weather data from APIs"),
    api_key: None = Depends(verify_api_key)
) -> EnvironmentalReport:
    """
    Analyze smoke in image and generate comprehensive environmental report
    
    - **file**: Image file (JPEG, PNG, etc.)
    - **latitude**: Geographic latitude
    - **longitude**: Geographic longitude
    - **accuracy**: GPS accuracy in meters (optional)
    - **confidence**: Detection confidence threshold
    - **include_weather**: Fetch external weather/AQI data
    
    Returns complete environmental report with pollutant estimates and health recommendations
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = file.filename.split('.')[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Read file
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
            )
        
        # Load and process image
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        img_height, img_width = image.shape[:2]
        
        # ============ SMOKE ANALYSIS ============
        logger.info(f"Request {request_id}: Analyzing smoke in image")
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        # ============ POLLUTANT ESTIMATION ============
        logger.info(f"Request {request_id}: Estimating pollutants from smoke level")
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # ============ GEOLOCATION & ENVIRONMENTAL DATA ============
        logger.info(f"Request {request_id}: Fetching geolocation data")
        env_data_service = EnvironmentalDataService(aqi_token=settings.get("WAQI_TOKEN"))
        
        location, environmental_data, aqi_data = await env_data_service.get_complete_environmental_data(
            latitude,
            longitude,
            accuracy
        ) if include_weather else (
            env_data_service.geo_service.get_address_from_coordinates(latitude, longitude, accuracy),
            None,
            None
        )
        
        # ============ REPORT GENERATION ============
        logger.info(f"Request {request_id}: Generating comprehensive report")
        report = ReportGenerator.generate_report(
            location=location,
            smoke_analysis=smoke_analysis,
            pollutant_readings=pollutant_readings,
            environmental_data=environmental_data,
            image_width=img_width,
            image_height=img_height,
            image_filename=file.filename,
            timestamp=datetime.utcnow()
        )
        
        logger.info(
            f"Request {request_id}: Analysis complete. "
            f"AQI: {report.air_quality_summary.aqi_value}, "
            f"Smoke: {smoke_analysis.smoke_percentage:.1f}%"
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id}: Analysis failed - {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/analyze-smoke/html")
async def analyze_smoke_html(
    file: UploadFile = File(...),
    latitude: float = Query(...),
    longitude: float = Query(...),
    accuracy: Optional[float] = Query(None),
    confidence: float = Query(0.5),
    include_weather: bool = Query(True),
    api_key: None = Depends(verify_api_key)
):
    """
    Analyze smoke and return HTML report
    
    Same as /analyze-smoke but returns formatted HTML report
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = file.filename.split('.')[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Invalid file type")
        
        # Read file
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large")
        
        # Load and process image
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        img_height, img_width = image.shape[:2]
        
        # Analyze
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # Get location
        env_data_service = EnvironmentalDataService(aqi_token=settings.get("WAQI_TOKEN"))
        location, environmental_data, _ = await env_data_service.get_complete_environmental_data(
            latitude,
            longitude,
            accuracy
        ) if include_weather else (
            env_data_service.geo_service.get_address_from_coordinates(latitude, longitude, accuracy),
            None,
            None
        )
        
        # Generate report
        report = ReportGenerator.generate_report(
            location=location,
            smoke_analysis=smoke_analysis,
            pollutant_readings=pollutant_readings,
            environmental_data=environmental_data,
            image_width=img_width,
            image_height=img_height,
            image_filename=file.filename
        )
        
        # Generate HTML
        html_content = ReportGenerator.create_html_report(report)
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id}: HTML report failed - {str(e)}")
        raise HTTPException(status_code=500, detail="Report generation failed")


@router.post("/analyze-smoke/summary")
async def get_analysis_summary(
    file: UploadFile = File(...),
    latitude: float = Query(...),
    longitude: float = Query(...),
    accuracy: Optional[float] = Query(None),
    api_key: None = Depends(verify_api_key)
):
    """
    Get quick text summary of smoke analysis
    
    Lighter endpoint for mobile apps needing quick summary
    """
    try:
        contents = await file.read()
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        
        # Quick analysis
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # Get location
        env_data_service = EnvironmentalDataService()
        location = env_data_service.geo_service.get_address_from_coordinates(
            latitude, longitude, accuracy
        )
        
        # Generate report
        report = ReportGenerator.generate_report(
            location=location,
            smoke_analysis=smoke_analysis,
            pollutant_readings=pollutant_readings
        )
        
        # Create summary
        summary = ReportGenerator.create_summary(report)
        
        return {
            "report_id": report.report_id,
            "timestamp": report.timestamp,
            "aqi": report.air_quality_summary.aqi_value,
            "smoke_percent": smoke_analysis.smoke_percentage,
            "location": {
                "city": location.city,
                "region": location.region,
                "country": location.country
            },
            "summary": summary,
            "recommendation": report.air_quality_summary.health_recommendation
        }
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail="Summary generation failed")


@router.get("/aqi-reference")
async def get_aqi_reference():
    """
    Get AQI reference guide and thresholds
    
    Useful for mobile apps to display locally
    """
    return {
        "aqi_ranges": {
            "excellent": {"min": 0, "max": 50, "description": "Air quality is satisfactory"},
            "good": {"min": 51, "max": 100, "description": "Air quality is acceptable"},
            "moderate": {"min": 101, "max": 150, "description": "Unhealthy for sensitive groups"},
            "poor": {"min": 151, "max": 200, "description": "Unhealthy for general population"},
            "hazardous": {"min": 201, "max": 500, "description": "Hazardous - avoid outdoor activities"}
        },
        "pollutant_units": {
            "PM2.5": "µg/m³",
            "PM10": "µg/m³",
            "NO2": "ppb",
            "O3": "ppb",
            "SO2": "ppb",
            "CO": "ppm"
        },
        "health_effects": {
            "excellent": "No health impacts expected",
            "good": "No health impacts expected for general population",
            "moderate": "Some members of sensitive groups may experience health effects",
            "poor": "General public more likely to be affected",
            "hazardous": "Health alert - everyone affected"
        }
    }


@router.get("/pollution-info")
async def get_pollution_info(
    pollutant: str = Query(...),
    api_key: None = Depends(verify_api_key)
):
    """Get detailed info about a specific pollutant"""
    
    pollutant_info = {
        "PM2.5": {
            "name": "Fine Particulate Matter (2.5 µm or less)",
            "sources": ["Vehicle emissions", "Wildfires", "Coal burning", "Industrial processes"],
            "health_effects": ["Lung damage", "Asthma", "Reduced lung function", "Premature death"],
            "description": "Ultra-fine particles that can penetrate deep into lungs and bloodstream"
        },
        "PM10": {
            "name": "Coarse Particulate Matter (10 µm or less)",
            "sources": ["Dust", "Construction", "Vehicle wear", "Agricultural activity"],
            "health_effects": ["Respiratory issues", "Reduced lung function", "Asthma exacerbation"],
            "description": "Larger particles that primarily affect respiratory system"
        },
        "NO2": {
            "name": "Nitrogen Dioxide",
            "sources": ["Vehicle emissions", "Power plants", "Industrial facilities", "Boilers"],
            "health_effects": ["Airway inflammation", "Reduced lung function", "Asthma symptoms"],
            "description": "Brown gas produced from combustion at high temperatures"
        },
        "O3": {
            "name": "Ozone (Ground-level)",
            "sources": ["Vehicle emissions + sunlight", "Industrial emissions"],
            "health_effects": ["Lung damage", "Asthma", "Respiratory tract damage", "Coughing"],
            "description": "Formed by reaction of pollutants with sunlight in lower atmosphere"
        },
        "SO2": {
            "name": "Sulfur Dioxide",
            "sources": ["Coal burning", "Oil refining", "Metal smelting", "Volcanic emissions"],
            "health_effects": ["Breathing problems", "Chest tightness", "Wheezing", "Asthma"],
            "description": "Colorless gas with sharp smell produced from fossil fuel combustion"
        },
        "CO": {
            "name": "Carbon Monoxide",
            "sources": ["Vehicle emissions", "Boilers", "Furnaces", "Incomplete combustion"],
            "health_effects": ["Reduced oxygen in blood", "Chest pain", "Brain damage", "Death"],
            "description": "Colorless, odorless gas that binds to hemoglobin preventing oxygen transport"
        }
    }
    
    if pollutant not in pollutant_info:
        raise HTTPException(status_code=404, detail=f"Pollutant '{pollutant}' not found")
    
    return pollutant_info[pollutant]
