# 🚀 Quick Start Guide

## Get Running in 5 Minutes

### Backend (Python)

**Step 1: Setup**
```bash
cd SWV
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

**Step 2: Install**
```bash
pip install -r requirements.txt
```

**Step 3: Run**
```bash
python -m uvicorn backend.main:app --reload
```

**Step 4: Test**
- Open browser: `http://localhost:8000/api/docs`
- Try uploading an image!

---

### Android

**Step 1: Open**
- Open Android Studio
- File → Open → Select `android/` folder

**Step 2: Configure**
Edit `android/src/main/java/com/swv/app/config/AppConfig.kt`:
```kotlin
const val API_BASE_URL = "http://YOUR_IP:8000/"
```

**Step 3: Build & Run**
- Connect Android device or start emulator
- Click Run button or press `Shift + F10`

---

### Docker

**One Command Deploy**
```bash
docker-compose up
```

API ready at `http://localhost:8000`

---

## 🧪 Test Detection

```bash
# Using cURL
curl -X POST "http://localhost:8000/api/v1/detect" \
  -H "X-API-Key: your-secret-key-change-in-production" \
  -F "file=@image.jpg"

# Using Python
python test_detection.py
```

---

## 📚 Full Documentation

See **README.md** for complete setup and configuration details.
