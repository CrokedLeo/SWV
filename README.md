# SWV - Smart Vision Object Detection Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com/)
[![Android](https://img.shields.io/badge/Android-24+-brightgreen)](https://www.android.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Production-ready object detection platform combining a FastAPI backend with YOLO v8 computer vision and a native Android mobile application.

## 🚀 Features

### Backend (FastAPI + YOLO v8)
- ✅ Real-time object detection with YOLO v8
- ✅ REST API with full documentation (Swagger/OpenAPI)
- ✅ Support for single and batch image processing
- ✅ API key authentication
- ✅ CORS support for cross-origin requests
- ✅ Configurable confidence thresholds
- ✅ Image validation and size limits
- ✅ Comprehensive error handling
- ✅ Docker support for easy deployment
- ✅ Health check endpoints
- ✅ Detailed logging

### Android App
- 🎥 Live camera capture
- 📷 Image gallery selection
- 🎯 Real-time object detection visualization
- 📊 Detailed detection results with bounding boxes
- ⚙️ Server configuration settings
- 🔐 API key management
- 🌐 Offline configuration storage
- 📱 Material Design UI

## 📋 Prerequisites

### Backend
- Python 3.11+
- pip package manager
- 2GB+ free disk space (for YOLO models)

### Android
- Android Studio Arctic Fox or later
- Android SDK 24+
- Java 11+

### General
- Docker & Docker Compose (optional, for containerized deployment)
- Git

## 🔧 Setup & Installation

### Backend Setup

#### 1. Clone and Navigate
```bash
cd path/to/SWV
```

#### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment
```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings (optional)
# Default settings are production-ready
```

#### 5. Run Backend
```bash
# Development mode
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/api/docs`
- OpenAPI Schema: `http://localhost:8000/api/openapi.json`

### Android Setup

#### 1. Open Project in Android Studio
```bash
# Option 1: Via Android Studio GUI
Open → Select the 'android' folder

# Option 2: Via command line
cd android
```

#### 2. Build Configuration
- Android Studio will auto-detect and download required SDKs
- Gradle will download all dependencies

#### 3. Configure Server Connection
Edit `android/src/main/java/com/swv/app/config/AppConfig.kt`:
```kotlin
object AppConfig {
    const val API_BASE_URL = "http://your-server-ip:8000/"
    const val API_KEY = "your-api-key"
    const val DEFAULT_CONFIDENCE = 0.5f
}
```

#### 4. Build APK
```bash
# Debug build
./gradlew assembleDebug

# Release build
./gradlew assembleRelease
```

### Docker Deployment

#### 1. Build Image
```bash
docker build -t swv-api:latest .
```

#### 2. Run Container
```bash
docker run -p 8000:8000 \
  -e API_KEY=your-secret-key \
  -e YOLO_MODEL=yolov8n.pt \
  -v ./uploads:/app/uploads \
  swv-api:latest
```

#### 3. Using Docker Compose (Recommended)
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 📡 API Documentation

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Include API key in request header:
```
X-API-Key: your-api-key
```

### Endpoints

#### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Application Info
```http
GET /info
```
**Response:**
```json
{
  "name": "SWV - Smart Vision",
  "version": "1.0.0",
  "description": "Object Detection API with YOLO",
  "yolo_model": "yolov8n.pt",
  "max_upload_size_mb": 10.0,
  "allowed_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"]
}
```

#### Detect Objects in Image
```http
POST /detect
Content-Type: multipart/form-data
X-API-Key: your-api-key

Parameters:
- file: Image file (required)
- confidence: Float between 0-1 (optional, default: 0.5)
```

**Response:**
```json
{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2024-01-15T10:30:00Z",
  "image_width": 640,
  "image_height": 480,
  "total_detections": 3,
  "processing_time_ms": 150.5,
  "model_used": "yolov8n.pt",
  "detections": [
    {
      "x_min": 100,
      "y_min": 150,
      "x_max": 300,
      "y_max": 400,
      "confidence": 0.95,
      "class_name": "person",
      "class_id": 0
    },
    {
      "x_min": 50,
      "y_min": 200,
      "x_max": 180,
      "y_max": 350,
      "confidence": 0.87,
      "class_name": "dog",
      "class_id": 16
    }
  ]
}
```

#### Batch Detect Objects
```http
POST /batch-detect
Content-Type: multipart/form-data
X-API-Key: your-api-key

Parameters:
- files: Multiple image files (required)
- confidence: Float between 0-1 (optional, default: 0.5)
```

**Response:**
```json
{
  "batch_results": [
    {
      "filename": "image1.jpg",
      "request_id": "req_123",
      "total_detections": 5,
      "processing_time_ms": 120.0,
      "detections": [...]
    },
    {
      "filename": "image2.jpg",
      "error": "File too large"
    }
  ]
}
```

## 🔒 Configuration

### Environment Variables (.env file)

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# YOLO Model
YOLO_MODEL=yolov8n.pt  # Options: yolov8n, yolov8s, yolov8m, yolov8l, yolov8x
CONFIDENCE_THRESHOLD=0.5

# API Security
API_KEY=your-secret-key-change-in-production
CORS_ORIGINS=*

# Upload Settings
MAX_UPLOAD_SIZE=10485760  # 10MB in bytes
UPLOAD_DIR=uploads

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

### YOLO Models

Available models (faster → more accurate):

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| yolov8n | Small | Fastest | Good |
| yolov8s | Smaller | Fast | Better |
| yolov8m | Medium | Medium | Very Good |
| yolov8l | Large | Slow | Excellent |
| yolov8x | Extra Large | Slowest | Best |

## 📱 Android App Usage

### Features

1. **Home Screen**
   - "Pick Image": Select from gallery
   - "Take Photo": Capture with camera
   - Recent detection history

2. **Detection Results**
   - Real-time visualization with bounding boxes
   - Confidence scores for each detection
   - Processing time metrics
   - Save results locally

3. **Settings**
   - Configure server URL
   - Set API key
   - Adjust confidence threshold
   - View model information

### Permissions

The app requires:
- **Camera**: To capture photos
- **Storage**: To read/write images
- **Internet**: To communicate with backend

## 🧪 Testing

### Backend Testing

#### Using cURL
```bash
# Single image detection
curl -X POST "http://localhost:8000/api/v1/detect" \
  -H "X-API-Key: your-api-key" \
  -F "file=@path/to/image.jpg" \
  -F "confidence=0.5"

# Health check
curl http://localhost:8000/api/v1/health

# Get info
curl http://localhost:8000/api/v1/info
```

#### Using Python
```python
import requests
from pathlib import Path

API_URL = "http://localhost:8000/api/v1"
API_KEY = "your-api-key"

# Single image
files = {'file': open('image.jpg', 'rb')}
headers = {'X-API-Key': API_KEY}
response = requests.post(
    f"{API_URL}/detect",
    files=files,
    params={'confidence': 0.5},
    headers=headers
)
print(response.json())

# Batch images
files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb'))
]
response = requests.post(
    f"{API_URL}/batch-detect",
    files=files,
    headers=headers
)
print(response.json())
```

#### Using Python Requests Library
```python
import requests
from pathlib import Path

def test_detection():
    api_url = "http://localhost:8000/api/v1"
    api_key = "your-api-key"
    
    # Test health
    health = requests.get(f"{api_url}/health").json()
    print(f"Health: {health['status']}")
    
    # Test detection
    with open('sample_image.jpg', 'rb') as f:
        files = {'file': f}
        headers = {'X-API-Key': api_key}
        response = requests.post(
            f"{api_url}/detect",
            files=files,
            headers=headers
        )
        result = response.json()
        print(f"Detections: {result['total_detections']}")
        print(f"Processing time: {result['processing_time_ms']:.2f}ms")

if __name__ == "__main__":
    test_detection()
```

### Interactive API Testing

Visit Swagger UI at `http://localhost:8000/api/docs` to test all endpoints interactively.

## 📊 Performance

### Metrics (yolov8n on CPU)

| Metric | Value |
|--------|-------|
| Processing Time | 100-200ms per image |
| Memory Usage | ~500MB |
| Throughput | ~5-10 images/second |

### Optimization Tips

1. **Use smaller model** (yolov8n) for speed
2. **Adjust confidence threshold** to reduce detections
3. **Enable GPU** support if available
4. **Use image compression** before upload

## 🐛 Troubleshooting

### Backend Issues

**ModuleNotFoundError: No module named 'backend'**
```bash
# Ensure you're in the project root directory
cd /path/to/SWV
python -m uvicorn backend.main:app --reload
```

**YOLO model download fails**
```bash
# Manually download model
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

**Port 8000 already in use**
```bash
# Use different port
python -m uvicorn backend.main:app --port 8001
```

### Android Issues

**Cannot connect to backend**
- Verify server URL in AppConfig.kt
- Check firewall settings
- Ensure API key is correct
- Test with `curl` first

**Camera not working**
- Check camera permissions in app settings
- Ensure `android:name="android.permission.CAMERA"` is in manifest

## 📚 Project Structure

```
SWV/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration management
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── detection.py         # YOLO detection logic
│   ├── routes/
│   │   ├── __init__.py
│   │   └── detection.py         # API endpoints
│   ├── __init__.py
│   └── main.py                  # FastAPI application
├── android/
│   ├── src/main/
│   │   ├── AndroidManifest.xml
│   │   ├── java/com/swv/app/
│   │   │   ├── api/
│   │   │   │   └── DetectionApi.kt
│   │   │   ├── models/
│   │   │   │   └── Models.kt
│   │   │   ├── repository/
│   │   │   │   └── DetectionRepository.kt
│   │   │   └── ui/
│   │   │       ├── MainActivity.kt
│   │   │       ├── DetectionActivity.kt
│   │   │       └── CameraActivity.kt
│   │   └── res/
│   │       └── values/
│   │           └── strings.xml
│   ├── build.gradle
│   └── gradle/wrapper/
├── .env.example                 # Example configuration
├── .env                         # Local configuration (git ignored)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
└── README.md                    # This file
```

## 🚀 Deployment

### Cloud Deployment (AWS, GCP, Azure)

1. **Prepare Docker image**
   ```bash
   docker build -t your-registry/swv-api:1.0.0 .
   docker push your-registry/swv-api:1.0.0
   ```

2. **Deploy to Kubernetes**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

3. **Set environment variables in cloud platform**

### Local Network Deployment

1. **Get your machine IP**
   ```bash
   # Windows
   ipconfig
   
   # macOS/Linux
   ifconfig
   ```

2. **Update Android app configuration**
   ```kotlin
   const val API_BASE_URL = "http://192.168.x.x:8000/"
   ```

3. **Run backend**
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions:
1. Check the Troubleshooting section
2. Review existing GitHub issues
3. Open a new issue with detailed information

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics) - Object detection
- [Android Developers](https://developer.android.com/) - Android platform

---

**Version**: 1.0.0  
**Last Updated**: January 2024  
**Status**: Production Ready ✅
