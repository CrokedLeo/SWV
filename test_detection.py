#!/usr/bin/env python3
"""
Test script for SWV Detection API
"""
import requests
import sys
from pathlib import Path
import time

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

def test_info():
    """Get API info"""
    try:
        response = requests.get(f"{API_URL}/info", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"✅ API Info:")
        print(f"   Model: {data['yolo_model']}")
        print(f"   Max Size: {data['max_upload_size_mb']}MB")
        print(f"   Formats: {', '.join(data['allowed_formats'])}")
        return True
    except Exception as e:
        print(f"❌ Get Info failed: {e}")
        return False

def test_detection(image_path):
    """Test detection on image"""
    if not Path(image_path).exists():
        print(f"❌ Image file not found: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': f}
            headers = {'X-API-Key': API_KEY}
            params = {'confidence': 0.5}
            
            print(f"📤 Detecting objects in: {image_path}")
            start = time.time()
            response = requests.post(
                f"{API_URL}/detect",
                files=files,
                headers=headers,
                params=params,
                timeout=60
            )
            elapsed = time.time() - start
            
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Detection completed in {elapsed:.2f}s:")
            print(f"   Total Detections: {data['total_detections']}")
            print(f"   Processing Time: {data['processing_time_ms']:.2f}ms")
            
            if data['detections']:
                print(f"   Detected Objects:")
                for i, det in enumerate(data['detections'], 1):
                    print(f"      {i}. {det['class_name']} ({det['confidence']*100:.1f}%)")
            
            return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error. Is the server running at {API_URL}?")
        return False
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        return False

def main():
    print("🔍 SWV Detection API Test Suite\n")
    
    # Test 1: Health
    print("Test 1: Health Check")
    if not test_health():
        print("⚠️  Server is not responding. Start it with:")
        print("   python -m uvicorn backend.main:app --reload")
        sys.exit(1)
    print()
    
    # Test 2: Info
    print("Test 2: API Info")
    if not test_info():
        sys.exit(1)
    print()
    
    # Test 3: Detection (if image provided)
    if len(sys.argv) > 1:
        print(f"Test 3: Detection")
        test_detection(sys.argv[1])
        print()
    else:
        print("Test 3: Detection (skipped - provide image path as argument)")
        print("   Usage: python test_detection.py /path/to/image.jpg\n")
    
    print("✅ All available tests passed!")

if __name__ == "__main__":
    main()
