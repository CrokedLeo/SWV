"""
Environmental report generation service
"""
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from backend.models.schemas import (
    EnvironmentalReport,
    AirQualitySummary,
    SmokeAnalysis,
    EnvironmentalData,
    PollutantReading,
    GeoLocation,
    PollutantType,
    SmokeLevel
)
from backend.services.air_quality import PollutantPredictor

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive environmental reports"""
    
    @staticmethod
    def generate_report(
        location: GeoLocation,
        smoke_analysis: SmokeAnalysis,
        pollutant_readings: List[PollutantReading],
        environmental_data: Optional[EnvironmentalData] = None,
        image_width: int = 1920,
        image_height: int = 1080,
        image_filename: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> EnvironmentalReport:
        """
        Generate complete environmental report
        
        Args:
            location: Geographic location data
            smoke_analysis: Smoke analysis results
            pollutant_readings: List of pollutant measurements
            environmental_data: Optional weather data
            image_width: Image width in pixels
            image_height: Image height in pixels
            image_filename: Original image filename
            timestamp: Report timestamp
            
        Returns:
            Complete EnvironmentalReport
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Get overall AQI
        overall_aqi = PollutantPredictor.get_overall_aqi(pollutant_readings)
        
        # Get primary pollutant (highest AQI)
        primary_pollutant = max(pollutant_readings, key=lambda x: x.aqi_index).pollutant_type if pollutant_readings else PollutantType.PM25
        
        # Get health recommendations
        health_recommendation, recommendations = PollutantPredictor.get_health_recommendations(overall_aqi)
        affected_groups = PollutantPredictor.get_affected_groups(overall_aqi)
        
        # Create air quality summary
        air_quality_summary = AirQualitySummary(
            primary_pollutant=primary_pollutant,
            aqi_value=overall_aqi,
            health_recommendation=health_recommendation,
            affected_groups=affected_groups
        )
        
        # Create risk assessment
        risk_assessment = ReportGenerator._create_risk_assessment(smoke_analysis, overall_aqi)
        
        # Image metadata
        image_metadata = {
            "width": image_width,
            "height": image_height,
            "filename": image_filename,
            "smoke_coverage_percent": smoke_analysis.smoke_percentage,
            "smoke_level": smoke_analysis.smoke_level.value,
            "opacity": smoke_analysis.opacity,
            "particles_detected": smoke_analysis.particles_detected
        }
        
        # Create report
        report = EnvironmentalReport(
            report_id=f"RPT_{uuid.uuid4().hex[:8].upper()}",
            timestamp=timestamp,
            location=location,
            image_metadata=image_metadata,
            smoke_analysis=smoke_analysis,
            environmental_data=environmental_data,
            pollutant_readings=pollutant_readings,
            air_quality_summary=air_quality_summary,
            risk_assessment=risk_assessment,
            recommendations=recommendations
        )
        
        return report
    
    @staticmethod
    def _create_risk_assessment(smoke_analysis: SmokeAnalysis, aqi_index: int) -> str:
        """Create textual risk assessment"""
        smoke_level = smoke_analysis.smoke_level.value
        
        risk_text = f"Risk Assessment:\n\n"
        risk_text += f"Air Quality Index (AQI): {aqi_index}\n"
        risk_text += f"Smoke Level: {smoke_level.upper()}\n"
        risk_text += f"Smoke Coverage: {smoke_analysis.smoke_percentage:.1f}%\n"
        risk_text += f"Image Opacity: {smoke_analysis.opacity*100:.1f}%\n"
        risk_text += f"Particle Clusters: {smoke_analysis.particles_detected}\n\n"
        
        # Add assessment
        if aqi_index <= 50:
            risk_text += "Status: ✅ SAFE - Air quality is satisfactory"
        elif aqi_index <= 100:
            risk_text += "Status: ⚠️ ACCEPTABLE - Air quality is acceptable for most"
        elif aqi_index <= 150:
            risk_text += "Status: ⚠️ UNHEALTHY FOR SENSITIVE - Sensitive groups at risk"
        elif aqi_index <= 200:
            risk_text += "Status: ❌ UNHEALTHY - General public affected"
        elif aqi_index <= 300:
            risk_text += "Status: 🚨 VERY UNHEALTHY - Avoid outdoor activities"
        else:
            risk_text += "Status: 🚨 HAZARDOUS - Health emergency"
        
        return risk_text
    
    @staticmethod
    def create_html_report(report: EnvironmentalReport) -> str:
        """Generate HTML version of report for display"""
        html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SWV Environmental Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2196F3;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #1976D2;
        }}
        .report-id {{
            color: #666;
            font-size: 12px;
        }}
        .aqi-indicator {{
            font-size: 48px;
            font-weight: bold;
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            color: white;
        }}
        .aqi-excellent {{ background-color: #2ecc71; }}
        .aqi-good {{ background-color: #8bc34a; }}
        .aqi-moderate {{ background-color: #f39c12; }}
        .aqi-poor {{ background-color: #e74c3c; }}
        .aqi-hazardous {{ background-color: #8b0000; }}
        .section {{
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #2196F3;
            background-color: #f9f9f9;
        }}
        .section h2 {{
            margin-top: 0;
            color: #1976D2;
        }}
        .metric {{
            display: inline-block;
            width: 48%;
            margin: 10px 1%;
            padding: 10px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .metric-label {{
            color: #666;
            font-size: 12px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1976D2;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        .risk-high {{ color: #e74c3c; font-weight: bold; }}
        .risk-moderate {{ color: #f39c12; font-weight: bold; }}
        .risk-low {{ color: #2ecc71; font-weight: bold; }}
        .recommendation {{
            padding: 10px;
            margin: 10px 0;
            background: #e3f2fd;
            border-left: 4px solid #2196F3;
            border-radius: 3px;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌍 SWV Environmental Report</h1>
            <p class="report-id">Report ID: {report.report_id}</p>
            <p>{report.timestamp.strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>

        <div class="aqi-indicator aqi-{ReportGenerator._get_aqi_class(report.air_quality_summary.aqi_value)}">
            AQI: {report.air_quality_summary.aqi_value}
        </div>

        <div class="section">
            <h2>📍 Location</h2>
            <div class="metric">
                <div class="metric-label">Coordinates</div>
                <div class="metric-value">{report.location.latitude:.4f}°, {report.location.longitude:.4f}°</div>
            </div>
            <div class="metric">
                <div class="metric-label">Accuracy</div>
                <div class="metric-value">{report.location.accuracy_meters}m</div>
            </div>
            <p><strong>Address:</strong> {report.location.address or 'N/A'}</p>
            {f'<p><strong>City:</strong> {report.location.city}</p>' if report.location.city else ''}
            {f'<p><strong>Region:</strong> {report.location.region}</p>' if report.location.region else ''}
        </div>

        <div class="section">
            <h2>💨 Smoke Analysis</h2>
            <div class="metric">
                <div class="metric-label">Smoke Coverage</div>
                <div class="metric-value">{report.smoke_analysis.smoke_percentage:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Smoke Level</div>
                <div class="metric-value">{report.smoke_analysis.smoke_level.value.upper()}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Image Opacity</div>
                <div class="metric-value">{report.smoke_analysis.opacity*100:.1f}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Particle Clusters</div>
                <div class="metric-value">{report.smoke_analysis.particles_detected}</div>
            </div>
            <p><strong>Dominant Smoke Color:</strong> RGB({report.smoke_analysis.dominant_color[0]}, {report.smoke_analysis.dominant_color[1]}, {report.smoke_analysis.dominant_color[2]})</p>
        </div>

        <div class="section">
            <h2>⚠️ Air Quality Summary</h2>
            <p><strong>Primary Pollutant:</strong> {report.air_quality_summary.primary_pollutant.value}</p>
            <p><strong>Health Recommendation:</strong> {report.air_quality_summary.health_recommendation}</p>
            <p><strong>Affected Groups:</strong> {', '.join(report.air_quality_summary.affected_groups)}</p>
        </div>

        <div class="section">
            <h2>🏭 Pollutant Readings</h2>
            <table>
                <tr>
                    <th>Pollutant</th>
                    <th>Concentration</th>
                    <th>Unit</th>
                    <th>AQI Index</th>
                    <th>Risk Level</th>
                </tr>
                {"".join(f'''
                <tr>
                    <td>{p.pollutant_type.value}</td>
                    <td>{p.value}</td>
                    <td>{p.unit}</td>
                    <td>{p.aqi_index}</td>
                    <td class="risk-{p.risk_level}">{p.risk_level.upper()}</td>
                </tr>
                ''' for p in report.pollutant_readings)}
            </table>
        </div>

        {f'''<div class="section">
            <h2>🌡️ Environmental Conditions</h2>
            <div class="metric">
                <div class="metric-label">Temperature</div>
                <div class="metric-value">{report.environmental_data.temperature}°C</div>
            </div>
            <div class="metric">
                <div class="metric-label">Humidity</div>
                <div class="metric-value">{report.environmental_data.humidity}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Wind Speed</div>
                <div class="metric-value">{report.environmental_data.wind_speed} m/s</div>
            </div>
            <div class="metric">
                <div class="metric-label">Visibility</div>
                <div class="metric-value">{report.environmental_data.visibility}m</div>
            </div>
        </div>''' if report.environmental_data else ''}

        <div class="section">
            <h2>💡 Recommendations</h2>
            {"".join(f'<div class="recommendation">✓ {rec}</div>' for rec in report.recommendations)}
        </div>

        <div class="footer">
            <p>Generated by SWV - Smart Vision Environmental Monitoring</p>
            <p>Report ID: {report.report_id}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    @staticmethod
    def _get_aqi_class(aqi_value: int) -> str:
        """Get CSS class for AQI indicator"""
        if aqi_value <= 50:
            return "excellent"
        elif aqi_value <= 100:
            return "good"
        elif aqi_value <= 150:
            return "moderate"
        elif aqi_value <= 200:
            return "poor"
        else:
            return "hazardous"
    
    @staticmethod
    def export_to_json(report: EnvironmentalReport) -> Dict[str, Any]:
        """Export report to JSON-serializable dictionary"""
        return report.model_dump(mode="json")
    
    @staticmethod
    def create_summary(report: EnvironmentalReport) -> str:
        """Create text summary of report"""
        summary = f"""
╔════════════════════════════════════════╗
║   SWV Environmental Report Summary     ║
╚════════════════════════════════════════╝

📋 Report ID: {report.report_id}
🕐 Timestamp: {report.timestamp.strftime('%d/%m/%Y %H:%M:%S')}

📍 LOCATION
  Coordinates: {report.location.latitude:.4f}°, {report.location.longitude:.4f}°
  Address: {report.location.address or 'N/A'}
  City: {report.location.city or 'N/A'}

💨 SMOKE ANALYSIS
  Coverage: {report.smoke_analysis.smoke_percentage:.1f}%
  Level: {report.smoke_analysis.smoke_level.value.upper()}
  Opacity: {report.smoke_analysis.opacity*100:.1f}%
  Particles: {report.smoke_analysis.particles_detected}

⚠️  AIR QUALITY
  AQI Index: {report.air_quality_summary.aqi_value}
  Primary Pollutant: {report.air_quality_summary.primary_pollutant.value}
  
🏭 POLLUTANTS
"""
        for reading in report.pollutant_readings:
            summary += f"  • {reading.pollutant_type.value}: {reading.value} {reading.unit} (AQI: {reading.aqi_index})\n"
        
        summary += f"""
💡 RECOMMENDATION
{report.air_quality_summary.health_recommendation}

📌 ACTIONS
"""
        for rec in report.recommendations:
            summary += f"  ✓ {rec}\n"
        
        return summary
