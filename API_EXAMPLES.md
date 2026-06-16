# API Usage Examples

## cURL Examples

### Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/health"
```

### Get Info
```bash
curl -X GET "http://localhost:8000/api/v1/info"
```

### Single Image Detection
```bash
curl -X POST "http://localhost:8000/api/v1/detect" \
  -H "X-API-Key: your-secret-key-change-in-production" \
  -F "file=@/path/to/image.jpg" \
  -F "confidence=0.5"
```

### Batch Detection
```bash
curl -X POST "http://localhost:8000/api/v1/batch-detect" \
  -H "X-API-Key: your-secret-key-change-in-production" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "confidence=0.5"
```

## Python Examples

### Basic Detection
```python
import requests

api_url = "http://localhost:8000/api/v1"
api_key = "your-secret-key-change-in-production"

# Upload and detect
with open("image.jpg", "rb") as f:
    files = {"file": f}
    headers = {"X-API-Key": api_key}
    
    response = requests.post(
        f"{api_url}/detect",
        files=files,
        headers=headers,
        params={"confidence": 0.5}
    )
    
    result = response.json()
    print(f"Detected {result['total_detections']} objects")
    
    for detection in result['detections']:
        print(f"  - {detection['class_name']}: {detection['confidence']:.2%}")
```

### Batch Processing
```python
import requests
import os
from pathlib import Path

api_url = "http://localhost:8000/api/v1"
api_key = "your-secret-key-change-in-production"

# Get all images from directory
image_dir = "images/"
image_files = [("files", open(f"{image_dir}/{f}", "rb")) 
               for f in os.listdir(image_dir) if f.endswith((".jpg", ".png"))]

headers = {"X-API-Key": api_key}

response = requests.post(
    f"{api_url}/batch-detect",
    files=image_files,
    headers=headers
)

results = response.json()["batch_results"]

for result in results:
    print(f"{result['filename']}: {result['total_detections']} objects")
```

### With Error Handling
```python
import requests
from requests.exceptions import RequestException, Timeout

def detect_with_retry(image_path, max_retries=3):
    api_url = "http://localhost:8000/api/v1"
    api_key = "your-secret-key-change-in-production"
    
    for attempt in range(max_retries):
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                headers = {"X-API-Key": api_key}
                
                response = requests.post(
                    f"{api_url}/detect",
                    files=files,
                    headers=headers,
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
                
        except Timeout:
            print(f"Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt == max_retries - 1:
                raise
        except RequestException as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
    
    return None

# Usage
try:
    result = detect_with_retry("image.jpg")
    print(result)
except Exception as e:
    print(f"Detection failed: {e}")
```

### Advanced: Saving Results
```python
import requests
import json
from datetime import datetime

def detect_and_save(image_path, output_dir="results"):
    api_url = "http://localhost:8000/api/v1"
    api_key = "your-secret-key-change-in-production"
    
    with open(image_path, "rb") as f:
        files = {"file": f}
        headers = {"X-API-Key": api_key}
        
        response = requests.post(
            f"{api_url}/detect",
            files=files,
            headers=headers
        )
        
        result = response.json()
        
        # Save JSON result
        timestamp = datetime.now().isoformat()
        filename = image_path.split("/")[-1].split(".")[0]
        output_file = f"{output_dir}/{filename}_{timestamp}.json"
        
        with open(output_file, "w") as out:
            json.dump(result, out, indent=2)
        
        print(f"Results saved to: {output_file}")
        return result

# Usage
detect_and_save("image.jpg")
```

## JavaScript/Fetch Examples

### Basic Detection
```javascript
const API_URL = "http://localhost:8000/api/v1";
const API_KEY = "your-secret-key-change-in-production";

async function detectObjects(imageFile) {
    const formData = new FormData();
    formData.append("file", imageFile);
    formData.append("confidence", 0.5);
    
    try {
        const response = await fetch(`${API_URL}/detect`, {
            method: "POST",
            headers: {
                "X-API-Key": API_KEY
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log(`Detected ${result.total_detections} objects`);
        
        result.detections.forEach(detection => {
            console.log(`- ${detection.class_name}: ${(detection.confidence * 100).toFixed(1)}%`);
        });
        
        return result;
    } catch (error) {
        console.error("Detection failed:", error);
    }
}

// Usage
const fileInput = document.getElementById("imageInput");
fileInput.addEventListener("change", (e) => {
    detectObjects(e.target.files[0]);
});
```

### Drawing Bounding Boxes
```javascript
function drawDetections(imageElement, detections) {
    const canvas = document.createElement("canvas");
    canvas.width = imageElement.width;
    canvas.height = imageElement.height;
    
    const ctx = canvas.getContext("2d");
    ctx.drawImage(imageElement, 0, 0);
    
    // Set drawing properties
    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    ctx.font = "16px Arial";
    ctx.fillStyle = "red";
    
    // Draw each detection
    detections.forEach(detection => {
        // Draw bounding box
        ctx.strokeRect(
            detection.x_min,
            detection.y_min,
            detection.x_max - detection.x_min,
            detection.y_max - detection.y_min
        );
        
        // Draw label
        const label = `${detection.class_name} ${(detection.confidence * 100).toFixed(1)}%`;
        ctx.fillText(label, detection.x_min, detection.y_min - 5);
    });
    
    return canvas;
}
```

## Node.js Examples

### Using Axios
```javascript
const axios = require("axios");
const FormData = require("form-data");
const fs = require("fs");

const API_URL = "http://localhost:8000/api/v1";
const API_KEY = "your-secret-key-change-in-production";

async function detectObjects(imagePath) {
    const form = new FormData();
    form.append("file", fs.createReadStream(imagePath));
    form.append("confidence", 0.5);
    
    try {
        const response = await axios.post(
            `${API_URL}/detect`,
            form,
            {
                headers: {
                    ...form.getHeaders(),
                    "X-API-Key": API_KEY
                }
            }
        );
        
        console.log(`Detections: ${response.data.total_detections}`);
        response.data.detections.forEach(det => {
            console.log(`  - ${det.class_name}: ${(det.confidence * 100).toFixed(1)}%`);
        });
        
        return response.data;
    } catch (error) {
        console.error("Detection failed:", error.message);
    }
}

// Usage
detectObjects("image.jpg");
```

## Response Format

All endpoints return JSON with consistent structure:

```json
{
  "request_id": "uuid",
  "timestamp": "ISO8601",
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
    }
  ]
}
```

## Error Responses

### 400 - Bad Request
```json
{
  "detail": "File type not allowed. Allowed: jpg, jpeg, png, gif, bmp, webp"
}
```

### 401 - Unauthorized
```json
{
  "detail": "Invalid API key"
}
```

### 413 - Payload Too Large
```json
{
  "detail": "File too large. Maximum size: 10.0MB"
}
```

### 500 - Server Error
```json
{
  "detail": "Detection failed: [error message]"
}
```

---

For more examples, check the test files or open an issue!
