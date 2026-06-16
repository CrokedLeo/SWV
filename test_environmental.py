#!/usr/bin/env python3
"""
Test script for SWV Environmental Monitoring API
"""
import requests
import sys
from pathlib import Path
import time
import json

API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-secret-key-change-in-production"

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Health Check: {data['status']}")
        return True
    except Exception as e:
        print(f"❌ Health Check failed: {e}")
        return False

def test_aqi_reference():
    """Get AQI reference guide"""
    try:
        response = requests.get(f"{API_URL}/aqi-reference", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ AQI Reference loaded")
        return True
    except Exception as e:
        print(f"❌ AQI Reference failed: {e}")
        return False

def test_smoke_analysis(image_path: str, latitude: float = 41.9028, longitude: float = 12.4964):
    """
    Test comprehensive smoke analysis
    Default coords: Rome, Italy
    """
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            headers = {'X-API-Key': API_KEY}
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'accuracy': 10,
                'confidence': 0.5,
                'include_weather': True
            }
            
            print(f"\n📤 Analyzing smoke in: {image_path}")
            print(f"📍 Location: ({latitude}, {longitude})")
            start = time.time()
            
            response = requests.post(
                f"{API_URL}/analyze-smoke",
                files=files,
                headers=headers,
                params=params,
                timeout=60
            )
            elapsed = time.time() - start
            
            response.raise_for_status()
            report = response.json()
            
            # Display results
            print(f"\n✅ Analysis completed in {elapsed:.2f}s:")
            print(f"\n📋 Report ID: {report['report_id']}")
            print(f"⏰ Timestamp: {report['timestamp']}")
            
            print(f"\n📍 Location:")
            print(f"   Address: {report['location']['address']}")
            if report['location']['city']:
                print(f"   City: {report['location']['city']}")
            if report['location']['region']:
                print(f"   Region: {report['location']['region']}")
            
            print(f"\n💨 Smoke Analysis:")
            smoke = report['smoke_analysis']
            print(f"   Coverage: {smoke['smoke_percentage']:.1f}%")
            print(f"   Level: {smoke['smoke_level'].upper()}")
            print(f"   Opacity: {smoke['opacity']*100:.1f}%")
            print(f"   Particles: {smoke['particles_detected']}")
            
            print(f"\n⚠️  Air Quality Summary:")
            aqi = report['air_quality_summary']
            print(f"   AQI Index: {aqi['aqi_value']}")
            print(f"   Primary Pollutant: {aqi['primary_pollutant']}")
            print(f"   Health Recommendation: {aqi['health_recommendation']}")
            
            print(f"\n🏭 Pollutant Readings:")
            for pollutant in report['pollutant_readings']:
                print(f"   {pollutant['pollutant_type']}: {pollutant['value']} {pollutant['unit']} (AQI: {pollutant['aqi_index']}, Risk: {pollutant['risk_level']})")
            
            if report.get('environmental_data'):
                print(f"\n🌡️  Environmental Conditions:")
                env = report['environmental_data']
                if env.get('temperature'):
                    print(f"   Temperature: {env['temperature']}°C")
                if env.get('humidity'):
                    print(f"   Humidity: {env['humidity']}%")
                if env.get('wind_speed'):
                    print(f"   Wind Speed: {env['wind_speed']} m/s")
            
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   ✓ {rec}")
            
            # Save report
            report_file = f"report_{report['report_id']}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n💾 Full report saved to: {report_file}")
            
            return True
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error. Is the server running at {API_URL}?")
        return False
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return False

def test_smoke_summary(image_path: str, latitude: float = 41.9028, longitude: float = 12.4964):
    """Test quick summary endpoint"""
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            headers = {'X-API-Key': API_KEY}
            params = {
                'latitude': latitude,
                'longitude': longitude
            }
            
            print(f"\n📤 Getting quick summary for: {image_path}")
            response = requests.post(
                f"{API_URL}/analyze-smoke/summary",
                files=files,
                headers=headers,
                params=params,
                timeout=60
            )
            
            response.raise_for_status()
            summary = response.json()
            
            print(f"\n✅ Summary retrieved:")
            print(summary['summary'])
            
            return True
            
    except Exception as e:
        print(f"❌ Summary failed: {e}")
        return False

def main():
    print("🔍 SWV Environmental Monitoring Test Suite\n")
    
    # Test 1: Health
    print("Test 1: Health Check")
    if not test_health():
        print("⚠️  Server is not responding. Start it with:")
        print("   python -m uvicorn backend.main:app --reload")
        sys.exit(1)
    print()
    
    # Test 2: AQI Reference
    print("Test 2: AQI Reference Guide")
    test_aqi_reference()
    print()
    
    # Test 3: Smoke Analysis (if image provided)
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        
        # Optional: custom coordinates
        latitude = float(sys.argv[2]) if len(sys.argv) > 2 else 41.9028
        longitude = float(sys.argv[3]) if len(sys.argv) > 3 else 12.4964
        
        print(f"Test 3: Comprehensive Smoke Analysis")
        test_smoke_analysis(image_path, latitude, longitude)
        print()
        
        print(f"Test 4: Quick Summary")
        test_smoke_summary(image_path, latitude, longitude)
        print()
    else:
        print("Test 3: Comprehensive Smoke Analysis (skipped)")
        print("   Usage: python test_environmental.py /path/to/image.jpg [latitude] [longitude]\n")
        print("Test 4: Quick Summary (skipped)\n")
    
    print("✅ All available tests completed!")
    print("\n📚 API Documentation: http://localhost:8000/api/docs")

if __name__ == "__main__":
    main()
