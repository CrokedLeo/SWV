# SWV - Smart Vision Environmental Monitoring v2.0

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)](https://fastapi.tiangolo.com/)
[![Android](https://img.shields.io/badge/Android-24+-brightgreen)](https://www.android.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-blue)](https://github.com)

**Piattaforma completa di monitoraggio ambientale** che combina Computer Vision, Geolocalizzazione e Dati Ambientali per analizzare il fumo e stimare i livelli di inquinanti, generando report dettagliati con raccomandazioni sanitarie.

> **New in v2.0**: 🌍 Environmental Monitoring, 💨 Smoke Analysis, 📊 Pollutant Estimation, 📍 Geolocation Integration, 🏥 Health Recommendations

## 🌍 Che cos'è SWV v2.0?

SWV è un'applicazione **production-ready** che permette agli utenti di:

1. 📸 **Fotografare il fumo/inquinamento atmosferico**
2. 💨 **Analizzare la percentuale e il livello di fumo** usando Computer Vision
3. 🔬 **Stimare i livelli di inquinanti** (PM2.5, PM10, NO2, O3, SO2, CO)
4. 📍 **Incrociare i dati geografici** dell'utente con meteo e qualità dell'aria
5. 📊 **Ricevere report dettagliati** con raccomandazioni sanitarie
6. 🗺️ **Visualizzare mappe di inquinamento** per regione

## ✨ Caratteristiche Principali

### Backend (FastAPI + Python)

#### Analisi del Fumo
- ✅ Rileva **percentuale di copertura fumo** (0-100%)
- ✅ Categorizza in **5 livelli** (Excellent, Good, Moderate, Poor, Hazardous)
- ✅ Analizza **distribuzione densità** nelle diverse regioni dell'immagine
- ✅ Calcola **opacità complessiva** dell'aria
- ✅ Rileva **clusters di particolato**
- ✅ Identifica **colore dominante** del fumo/inquinamento

#### Stima Inquinanti
Correlazione automatica tra livelli di fumo e concentrazioni di:
- **PM2.5** - Particulate Matter fino a 2.5 micrometri (polmoni)
- **PM10** - Particulate Matter fino a 10 micrometri
- **NO2** - Nitrogen Dioxide (automobili, industria)
- **O3** - Ozone (smog fotochimico)
- **SO2** - Sulfur Dioxide (centrali elettriche, industria)
- **CO** - Carbon Monoxide (combustione incompleta)

#### Geolocalizzazione & Dati Ambientali
- 📍 **Reverse Geocoding** - Indirizzo da coordinate GPS
- 🌡️ **Meteo** - Integrazione con Open-Meteo API (gratuita)
- 🌐 **AQI Esterno** - Supporto WAQI per dati di qualità dell'aria locali
- 📊 **Correlazione Dati** - Incrocia fumo con meteo e inquinamento regionale

#### Report Completi
- 📄 **HTML** - Visualizzabile nel browser con grafici
- 📋 **JSON** - Strutturato per integrazione con client
- 📱 **Sommario Testo** - Quick summary per app mobile
- 🏥 **Raccomandazioni Sanitarie** - Personalizzate per AQI

#### API Endpoints
- `POST /api/v1/analyze-smoke` - Analisi completa
- `POST /api/v1/analyze-smoke/html` - Report HTML
- `POST /api/v1/analyze-smoke/summary` - Sommario rapido
- `GET /api/v1/aqi-reference` - Guida AQI
- `GET /api/v1/pollution-info` - Info inquinanti
- `GET /api/v1/health` - Health check
- `GET /api/v1/info` - Info applicazione

### Android App

- 🎥 **Cattura Foto** - Con camera dell'app
- 📷 **Seleziona Galleria** - Da foto già scattate
- 📹 **Video Support** - Frame-by-frame analysis (roadmap)
- 📍 **GPS Integration** - Localizzazione automatica
- 📊 **Report Viewer** - Visualizzazione report completi
- 🗺️ **Mappa Heatmap** - Visualizza inquinamento per zona (roadmap)
- ⚙️ **Configurazione** - Server URL, API Key, Threshold
- 💾 **Cache Risultati** - Salva offline i report
- 📱 **Material Design 3** - Modern UI

## 📋 Requisiti

### Backend
- Python 3.11+
- pip
- 2GB+ RAM
- 500MB disk (ONNX model - auto-downloaded on first use)
- Internet (per API esterne)

### Android
- Android Studio 2021.1+
- Android SDK 24+
- Java 11+
- Kotlin 1.9+

### Generale
- Docker (opzionale)
- API Key WAQI (opzionale, per AQI esterno)

## 🚀 Setup Rapido (5 minuti)

### Backend

```bash
# 1. Clone e navigate
cd SWV

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dipendenze
pip install -r requirements.txt

# 4. Run
python -m uvicorn backend.main:app --reload

# 5. Test
python test_environmental.py sample_image.jpg 41.9028 12.4964
```

API disponibile su: **http://localhost:8000**
- Docs Swagger: **http://localhost:8000/api/docs**
- Redoc: **http://localhost:8000/api/redoc**

### Docker

```bash
# Build & Run con un comando
docker-compose up

# API disponibile su http://localhost:8000
```

### Android

```bash
# 1. Apri in Android Studio
File → Open → Select 'android/' folder

# 2. Configura server
Edit: android/src/main/java/com/swv/app/config/AppConfig.kt
const val API_BASE_URL = "http://YOUR_SERVER_IP:8000/"

# 3. Build & Run
Shift + F10 (o click Run)
```

## 📡 API Reference

### Analisi Fumo & Ambiente

#### POST `/api/v1/analyze-smoke`

**Analisi completa con report JSON**

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-smoke" \
  -H "X-API-Key: your-secret-key" \
  -F "file=@photo.jpg" \
  -F "latitude=41.9028" \
  -F "longitude=12.4964" \
  -F "accuracy=10" \
  -F "confidence=0.5" \
  -F "include_weather=true"
```

**Query Parameters:**
| Param | Type | Required | Default | Descrizione |
|-------|------|----------|---------|-------------|
| latitude | float | ✅ | - | GPS latitude (-90 a 90) |
| longitude | float | ✅ | - | GPS longitude (-180 a 180) |
| accuracy | float | ❌ | null | GPS accuracy in meters |
| confidence | float | ❌ | 0.5 | Detection confidence (0-1) |
| include_weather | bool | ❌ | true | Include meteo & AQI |

**Response Example:**
```json
{
  "report_id": "RPT_A1B2C3D4",
  "timestamp": "2024-01-15T10:30:00Z",
  "location": {
    "latitude": 41.9028,
    "longitude": 12.4964,
    "address": "Via della Conciliazione, Rome, Italy",
    "city": "Rome",
    "region": "Lazio",
    "country": "Italy",
    "accuracy_meters": 10
  },
  "smoke_analysis": {
    "smoke_percentage": 45.2,
    "smoke_level": "moderate",
    "density_distribution": {...},
    "dominant_color": [128, 100, 90],
    "particles_detected": 152,
    "opacity": 0.35
  },
  "air_quality_summary": {
    "aqi_value": 125,
    "primary_pollutant": "PM2.5",
    "health_recommendation": "Air quality is unhealthy for sensitive groups",
    "affected_groups": ["Children", "Elderly", "People with respiratory disease"]
  },
  "pollutant_readings": [
    {
      "pollutant_type": "PM2.5",
      "value": 45.3,
      "unit": "µg/m³",
      "aqi_index": 125,
      "risk_level": "moderate_high"
    },
    ...
  ],
  "environmental_data": {
    "temperature": 18.5,
    "humidity": 65,
    "wind_speed": 3.2,
    "visibility": 8000
  },
  "recommendations": [
    "Members of sensitive groups should limit outdoor exposure",
    "Wear N95/KN95 masks if going outside"
  ]
}
```

#### POST `/api/v1/analyze-smoke/html`

**Report in formato HTML visualizzabile**

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-smoke/html" \
  -H "X-API-Key: your-secret-key" \
  -F "file=@photo.jpg" \
  -F "latitude=41.9028" \
  -F "longitude=12.4964" \
  > report.html
```

#### POST `/api/v1/analyze-smoke/summary`

**Sommario rapido per mobile**

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-smoke/summary" \
  -H "X-API-Key: your-secret-key" \
  -F "file=@photo.jpg" \
  -F "latitude=41.9028" \
  -F "longitude=12.4964"
```

**Response:**
```json
{
  "report_id": "RPT_A1B2C3D4",
  "timestamp": "2024-01-15T10:30:00Z",
  "aqi": 125,
  "smoke_percent": 45.2,
  "location": {
    "city": "Rome",
    "region": "Lazio",
    "country": "Italy"
  },
  "summary": "...",
  "recommendation": "Air quality is unhealthy for sensitive groups"
}
```

#### GET `/api/v1/aqi-reference`

**Guida completa AQI (offline-friendly)**

```bash
curl http://localhost:8000/api/v1/aqi-reference
```

Returns: AQI ranges, pollutant units, health effects

#### GET `/api/v1/pollution-info?pollutant=PM2.5`

**Info dettagliata su un inquinante**

```bash
curl "http://localhost:8000/api/v1/pollution-info?pollutant=PM2.5" \
  -H "X-API-Key: your-secret-key"
```

## 🔑 Interpretazione dei Dati

### Air Quality Index (AQI)

| AQI | Range | Livello | Colore | Effetti Sanitari |
|-----|-------|---------|--------|------------------|
| 0-50 | Excellent | ✅ | 🟢 Green | Nessuno |
| 51-100 | Good | ✅ | 🟡 Yellow | Nessuno, general pop. |
| 101-150 | Moderate | ⚠️ | 🟠 Orange | Sensibili a rischio |
| 151-200 | Poor | ❌ | 🔴 Red | Pop. generale colpita |
| 201-300 | Very Unhealthy | 🚨 | 🟣 Purple | Evitare attività esterna |
| 300+ | Hazardous | 🚨 | 🟤 Maroon | Emergenza sanitaria |

### Livelli di Fumo

| Percentage | Livello | Implicazioni |
|-----------|---------|--------------|
| 0-20% | Excellent | Assenza di visibilità disturbata |
| 20-40% | Good | Leggero offuscamento |
| 40-60% | Moderate | Moderato offuscamento |
| 60-80% | Poor | Significativa riduzione visibilità |
| 80-100% | Hazardous | Visibilità gravemente compromessa |

## 🛠️ Configurazione

### .env Essenziale

```bash
# Server
HOST=0.0.0.0
PORT=8000

# API Security
API_KEY=your-secret-key-change-in-production

# YOLO Model (ONNX format)
# Auto-downloaded on first request if not present
YOLO_MODEL=yolov8n.onnx

# External APIs (Optional)
WAQI_TOKEN=  # Get from: https://aqicn.org/data-platform/token/
```

### Modelli YOLO Disponibili (ONNX Format)

| Modello | Size | Speed | Accuracy | CPU RAM |
|---------|------|-------|----------|---------|
| yolov8n | 12MB | ⚡⚡⚡⚡ | Good | Low |
| yolov8s | 23MB | ⚡⚡⚡ | Better | Low-Med |
| yolov8m | 50MB | ⚡⚡ | Very Good | Med |
| yolov8l | 94MB | ⚡ | Excellent | Med-High |
| yolov8x | 161MB | ⚡ | Best | High |

> **Nota:** Il modello viene scaricato automaticamente al primo avvio.  
> Per usare un modello diverso, scarica il file `.onnx` corrispondente e imposta `YOLO_MODEL` nel `.env`.

## 📚 Documenti Aggiuntivi

- **ENVIRONMENTAL_MONITORING.md** - Guida completa modalità v2.0
- **API_EXAMPLES.md** - Esempi cURL, Python, JavaScript
- **DEPLOYMENT.md** - Guide cloud (AWS, GCP, Azure, Heroku)
- **QUICKSTART.md** - Setup rapido 5 minuti
- **API Docs** - http://localhost:8000/api/docs (interactive)

## 🔒 Sicurezza

- ✅ API Key authentication su tutti gli endpoint
- ✅ File upload validation (size, type)
- ✅ CORS configurabile
- ✅ Rate limiting ready (implementare via nginx/cloudflare)
- ✅ SSL/TLS support (tramite reverse proxy)
- ✅ No sensitive data in logs

## 🚀 Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
curl http://localhost:8000/api/docs
```

### Cloud (AWS EC2)

```bash
# Full guide in DEPLOYMENT.md
aws ec2 run-instances --image-id ami-xxx
# ... configure & deploy
```

### Heroku

```bash
heroku create swv-api
git push heroku main
```

## 📊 Performance

### Benchmark (yolov8n.onnx on CPU)

| Metrica | Valore |
|---------|--------|
| Time per Image | 100-200ms |
| Memory Usage | ~500MB |
| Throughput | ~5-10 img/sec |
| YOLO Load Time | ~2s (first call) |

## 🐛 Troubleshooting

### Server non parte
```bash
# Verifica Python 3.11+
python --version

# Verifica dipendenze
pip install -r requirements.txt

# Check porta
netstat -ano | findstr :8000
```

### Analisi lenta
- Usa modello più piccolo (yolov8n.onnx)
- Riduci dimensione immagine
- Usa GPU se disponibile

### Errore "ModuleNotFoundError"
```bash
# Assicurati di essere nella dir giusta
cd /path/to/SWV

# Run da project root
python -m uvicorn backend.main:app --reload
```

## 📱 App Android

### Features Roadmap

- [x] Camera capture
- [x] Geolocation
- [ ] Live preview analysis
- [ ] Video support
- [ ] Map heatmap
- [ ] Local caching
- [ ] Offline mode
- [ ] Report sharing

### Compilare APK

```bash
cd android

# Debug
./gradlew assembleDebug

# Release
./gradlew assembleRelease -PreleaseBuild
```

## 📈 Statistiche API

- **v1.0** - Object Detection (2024-01)
- **v2.0** - Environmental Monitoring (2024-01)
- **Endpoints**: 8+
- **Pollutants**: 6
- **AQI Levels**: 6
- **Countries**: Global

## 📄 Licenza

MIT License - vedi [LICENSE](LICENSE)

## 🤝 Contributing

Contribuzioni benvenute! Vedi [CONTRIBUTING.md](CONTRIBUTING.md)

## 📞 Support

- 📖 **Docs**: README.md, ENVIRONMENTAL_MONITORING.md
- 🧪 **Test**: `python test_environmental.py`
- 🌐 **API Docs**: http://localhost:8000/api/docs
- 🐛 **Issues**: GitHub Issues
- 💬 **Discussion**: GitHub Discussions

---

**Version**: 2.0.0 - Environmental Monitoring  
**Status**: ✅ Production Ready  
**Last Updated**: January 2024  

Built with ❤️ using FastAPI, Python, and Computer Vision
