"""
Environmental monitoring API routes
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.config.security import security_config
from backend.models.schemas import (
    EnvironmentalReport, 
    SmokeDetectionRequest,
    ErrorResponse
)
from backend.models.database import get_db
from backend.models.orm import HistoricalReport, PollutantReading
from backend.services.detection import get_detector, ImageProcessor
from backend.services.air_quality import SmokeAnalyzer, PollutantPredictor
from backend.services.geolocation import EnvironmentalDataService
from backend.services.report_generator import ReportGenerator
from backend.security import (
    FileSecurityValidator,
    InputSanitizer,
    RequestValidator,
    log_security_event,
    rate_limiter
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["environmental"])


def _save_report_to_db(report: EnvironmentalReport, db: Session) -> HistoricalReport:
    """
    Helper function to save EnvironmentalReport (Pydantic) to database (SQLAlchemy ORM)
    
    Args:
        report: Validated Pydantic EnvironmentalReport model
        db: SQLAlchemy database session
    
    Returns:
        Saved HistoricalReport ORM model instance
    """
    try:
        # Create HistoricalReport ORM instance
        db_report = HistoricalReport(
            report_id=report.report_id,
            timestamp=report.timestamp,
            
            # Location
            latitude=report.location.latitude,
            longitude=report.location.longitude,
            address=report.location.address,
            city=report.location.city,
            region=report.location.region,
            country=report.location.country,
            accuracy_meters=report.location.accuracy_meters,
            
            # Air quality
            aqi_value=report.air_quality_summary.aqi_value,
            primary_pollutant=report.air_quality_summary.primary_pollutant.value,
            smoke_percentage=report.smoke_analysis.smoke_percentage,
            risk_level=report.air_quality_summary.health_recommendation[:50],
            
            # Image metadata
            image_filename=report.image_metadata.get('filename'),
            image_width=report.image_metadata.get('width'),
            image_height=report.image_metadata.get('height'),
            image_metadata=report.image_metadata,
            
            # Environmental conditions
            temperature=report.environmental_data.temperature if report.environmental_data else None,
            humidity=report.environmental_data.humidity if report.environmental_data else None,
            pressure=report.environmental_data.pressure if report.environmental_data else None,
            wind_speed=report.environmental_data.wind_speed if report.environmental_data else None,
            visibility=report.environmental_data.visibility if report.environmental_data else None,
            
            # Report content
            health_recommendation=report.air_quality_summary.health_recommendation,
            risk_assessment=report.risk_assessment,
            recommendations=report.recommendations,
            affected_groups=report.air_quality_summary.affected_groups,
            
            # Historical context
            comparison_historical=report.comparison_historical,
            trend=report.trend,
        )
        
        # Save to database
        db.add(db_report)
        db.flush()  # Flush to get the ID
        
        # Save pollutant readings
        for pollutant in report.pollutant_readings:
            db_pollutant = PollutantReading(
                report_id=db_report.id,
                pollutant_type=pollutant.pollutant_type.value,
                value=pollutant.value,
                unit=pollutant.unit,
                aqi_index=pollutant.aqi_index,
                risk_level=pollutant.risk_level,
            )
            db.add(db_pollutant)
        
        db.commit()
        logger.info(f"Report {report.report_id} saved to database")
        return db_report
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save report to database: {e}", exc_info=True)
        raise


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Verify API key from header"""
    if settings.API_KEY != "your-secret-key-change-in-production":
        if x_api_key != settings.API_KEY:
            log_security_event("INVALID_API_KEY", {"provided_key": x_api_key[:8] if x_api_key else None}, "WARNING")
            raise HTTPException(status_code=401, detail="Invalid API key")


def validate_request_origin(origin: Optional[str] = Header(None), x_forwarded_for: Optional[str] = Header(None)) -> None:
    """
    Validate request origin for CORS security
    Logs suspicious requests from disallowed origins
    """
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    # Log origin validation for non-development environments
    if security_config.ENVIRONMENT != "development" and origin:
        if not security_config.is_origin_allowed(origin):
            log_security_event(
                "DISALLOWED_ORIGIN_REQUEST",
                {
                    "origin": origin,
                    "ip": client_ip,
                    "environment": security_config.get_environment_name()
                },
                "WARNING"
            )


@router.post("/analyze-smoke", response_model=EnvironmentalReport)
async def analyze_smoke_and_air_quality(
    file: UploadFile = File(...),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    accuracy: Optional[float] = Query(None, ge=0, le=10000, description="GPS accuracy in meters"),
    confidence: float = Query(0.5, ge=0.1, le=0.95),
    include_weather: bool = Query(True, description="Include weather data from APIs"),
    api_key: None = Depends(verify_api_key),
    origin: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    _origin_check: None = Depends(validate_request_origin)
) -> EnvironmentalReport:
    """
    Analyze smoke in image and generate comprehensive environmental report
    
    - **file**: Image file (JPEG, PNG, etc.)
    - **latitude**: Geographic latitude
    - **longitude**: Geographic longitude
    - **accuracy**: GPS accuracy in meters (optional)
    - **confidence**: Detection confidence threshold (0.1-0.95)
    - **include_weather**: Fetch external weather/AQI data
    
    Returns complete environmental report with pollutant estimates and health recommendations
    """
    request_id = str(uuid.uuid4())
    client_ip = x_forwarded_for.split(',')[0] if x_forwarded_for else "unknown"
    
    try:
        # ===== RATE LIMITING =====
        if not rate_limiter.is_allowed(client_ip):
            log_security_event("RATE_LIMIT_EXCEEDED", {"ip": client_ip, "endpoint": "/analyze-smoke"}, "WARNING")
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 100 requests per minute.")
        
        # ===== INPUT VALIDATION =====
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Sanitize filename
        file.filename = InputSanitizer.sanitize_string(file.filename, max_length=100)
        
        # Validate coordinates
        is_valid, error_msg = RequestValidator.validate_coordinates(latitude, longitude)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validate confidence
        is_valid, error_msg = RequestValidator.validate_confidence(confidence)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # ===== FILE SECURITY =====
        ext = file.filename.split('.')[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            log_security_event("INVALID_FILE_TYPE", {"ip": client_ip, "ext": ext}, "WARNING")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            )
        
        # Read file
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            log_security_event("FILE_TOO_LARGE", {"ip": client_ip, "size": len(contents)}, "WARNING")
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB"
            )
        
        # Validate file security
        is_valid, error_msg = FileSecurityValidator.validate_file(contents, file.filename)
        if not is_valid:
            log_security_event("MALICIOUS_FILE_DETECTED", {"ip": client_ip, "error": error_msg}, "CRITICAL")
            raise HTTPException(status_code=400, detail=error_msg)
        
        # ===== IMAGE ANALYSIS =====
        logger.info(f"Request {request_id}: Analyzing smoke in image from {client_ip}")
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        img_height, img_width = image.shape[:2]
        
        # Smoke analysis
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        
        # Validate smoke analysis
        if not RequestValidator.is_reasonable_smoke_percentage(smoke_analysis.smoke_percentage):
            logger.error(f"Request {request_id}: Invalid smoke percentage")
            raise HTTPException(status_code=500, detail="Invalid analysis result")
        
        # Pollutant estimation
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        # ===== GEOLOCATION & ENVIRONMENTAL DATA =====
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
        
        # ===== REPORT GENERATION =====
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
        
        # Validate report
        aqi_value = report.air_quality_summary.aqi_value
        if not RequestValidator.is_reasonable_aqi(aqi_value):
            logger.error(f"Request {request_id}: Invalid AQI value: {aqi_value}")
            raise HTTPException(status_code=500, detail="Invalid analysis result")
        
        log_security_event("ANALYSIS_COMPLETED", {
            "ip": client_ip,
            "request_id": request_id,
            "aqi": aqi_value,
            "smoke": smoke_analysis.smoke_percentage
        }, "INFO")
        
        logger.info(
            f"Request {request_id}: Analysis complete. "
            f"AQI: {aqi_value}, Smoke: {smoke_analysis.smoke_percentage:.1f}%"
        )
        
        # ===== SAVE TO DATABASE =====
        try:
            _save_report_to_db(report, db)
            logger.info(f"Request {request_id}: Report persisted to database")
        except Exception as e:
            logger.warning(f"Request {request_id}: Failed to persist report to database: {e}")
            # Don't fail the request if database save fails
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id}: Analysis failed - {str(e)}", exc_info=True)
        log_security_event("ANALYSIS_ERROR", {
            "ip": client_ip,
            "request_id": request_id,
            "error": str(e)[:50]
        }, "ERROR")
        raise HTTPException(
            status_code=500,
            detail="Analysis failed"
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
        # Basic validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        ext = file.filename.split('.')[-1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Invalid file type")
        
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large")
        
        # File security validation
        is_valid, error_msg = FileSecurityValidator.validate_file(contents, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Analyze
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        img_height, img_width = image.shape[:2]
        
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
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
        
        report = ReportGenerator.generate_report(
            location=location,
            smoke_analysis=smoke_analysis,
            pollutant_readings=pollutant_readings,
            environmental_data=environmental_data,
            image_width=img_width,
            image_height=img_height,
            image_filename=file.filename
        )
        
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
        
        # File security validation
        is_valid, error_msg = FileSecurityValidator.validate_file(contents, file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        image = ImageProcessor.load_from_bytes(contents)
        image = ImageProcessor.resize_image(image)
        
        smoke_analysis = SmokeAnalyzer.analyze_smoke_in_image(image)
        pollutant_readings = PollutantPredictor.estimate_pollutants(smoke_analysis)
        
        env_data_service = EnvironmentalDataService()
        location = env_data_service.geo_service.get_address_from_coordinates(
            latitude, longitude, accuracy
        )
        
        report = ReportGenerator.generate_report(
            location=location,
            smoke_analysis=smoke_analysis,
            pollutant_readings=pollutant_readings
        )
        
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


# ============= HISTORICAL DATA ENDPOINTS =============

@router.get("/reports/history")
async def get_reports_history(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude"),
    radius_km: float = Query(10, ge=1, le=100, description="Search radius in kilometers"),
    days: int = Query(30, ge=1, le=365, description="Days of history to retrieve"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    api_key: None = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Query historical air quality reports by location and date range
    
    - **latitude**: Search center latitude
    - **longitude**: Search center longitude
    - **radius_km**: Search radius in kilometers (default: 10 km)
    - **days**: Days of historical data (default: 30 days)
    - **limit**: Maximum reports to return (default: 50, max: 500)
    
    Returns list of historical reports with AQI, pollutants, and trends
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Rough approximation: 1 degree ≈ 111 km
        # More precise would use haversine formula
        radius_degrees = radius_km / 111.0
        
        min_lat = latitude - radius_degrees
        max_lat = latitude + radius_degrees
        min_lon = longitude - radius_degrees
        max_lon = longitude + radius_degrees
        
        # Query reports within spatial and temporal bounds
        reports = db.query(HistoricalReport).filter(
            HistoricalReport.timestamp >= start_date,
            HistoricalReport.timestamp <= end_date,
            HistoricalReport.latitude >= min_lat,
            HistoricalReport.latitude <= max_lat,
            HistoricalReport.longitude >= min_lon,
            HistoricalReport.longitude <= max_lon,
        ).order_by(HistoricalReport.timestamp.desc()).limit(limit).all()
        
        logger.info(f"Retrieved {len(reports)} historical reports for location ({latitude}, {longitude})")
        
        return {
            "count": len(reports),
            "query": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_km": radius_km,
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "reports": [report.to_dict() for report in reports]
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve historical reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve historical data")


@router.get("/reports/{report_id}")
async def get_report_by_id(
    report_id: str = Query(..., regex=r"^RPT_[A-Z0-9]{8}$", description="Report ID"),
    api_key: None = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Fetch a specific report by report ID
    
    - **report_id**: Unique report identifier (format: RPT_XXXXXXXX)
    
    Returns complete report with all pollutant readings and environmental data
    """
    try:
        report = db.query(HistoricalReport).filter(
            HistoricalReport.report_id == report_id
        ).first()
        
        if not report:
            logger.warning(f"Report {report_id} not found")
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        
        logger.info(f"Retrieved report {report_id}")
        return report.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve report")


@router.get("/reports/stats/location")
async def get_location_stats(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(30, ge=1, le=365),
    api_key: None = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics for a location over time
    
    Returns:
    - Average AQI over period
    - Max/min AQI readings
    - Most common primary pollutant
    - Trend (improving/stable/worsening)
    - Report count
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Approximate bounding box (within ~11km)
        radius_degrees = 0.1
        min_lat = latitude - radius_degrees
        max_lat = latitude + radius_degrees
        min_lon = longitude - radius_degrees
        max_lon = longitude + radius_degrees
        
        reports = db.query(HistoricalReport).filter(
            HistoricalReport.timestamp >= start_date,
            HistoricalReport.timestamp <= end_date,
            HistoricalReport.latitude >= min_lat,
            HistoricalReport.latitude <= max_lat,
            HistoricalReport.longitude >= min_lon,
            HistoricalReport.longitude <= max_lon,
        ).order_by(HistoricalReport.timestamp).all()
        
        if not reports:
            raise HTTPException(status_code=404, detail="No historical data for this location")
        
        # Calculate statistics
        aqi_values = [r.aqi_value for r in reports]
        avg_aqi = sum(aqi_values) / len(aqi_values) if aqi_values else 0
        
        # Trend analysis: compare first half vs second half
        mid = len(reports) // 2
        if mid > 0:
            first_half_avg = sum(aqi_values[:mid]) / mid
            second_half_avg = sum(aqi_values[mid:]) / (len(aqi_values) - mid) if len(aqi_values) > mid else 0
            
            if second_half_avg < first_half_avg * 0.95:
                trend = "improving"
            elif second_half_avg > first_half_avg * 1.05:
                trend = "worsening"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Most common primary pollutant
        pollutants = [r.primary_pollutant for r in reports]
        most_common = max(set(pollutants), key=pollutants.count) if pollutants else "Unknown"
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "period": {
                "days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "statistics": {
                "report_count": len(reports),
                "average_aqi": round(avg_aqi, 2),
                "min_aqi": min(aqi_values) if aqi_values else None,
                "max_aqi": max(aqi_values) if aqi_values else None,
                "most_common_pollutant": most_common,
                "trend": trend,
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate location stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to calculate statistics")


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

