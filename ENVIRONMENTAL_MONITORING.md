# SWV v2.0 - Environmental Monitoring & Air Quality Analysis

**Versione**: 2.0.0 - Environmental Monitoring Edition  
**Status**: ✅ Production Ready

## 🌍 Cosa è SWV Environmental?

SWV è una **piattaforma completa di monitoraggio ambientale** che utilizza:

- 📸 **Computer Vision (YOLO v8)** - Analizza il fumo dalle foto/video
- 🌡️ **Dati Ambientali** - Integra meteo e qualità dell'aria
- 📍 **Geolocalizzazione** - Incrocia i dati geografici dell'utente
- 📊 **Report Dettagliati** - Genera analisi complete con raccomandazioni sanitarie
- 🤖 **Correlazione Inquinanti** - Stima i livelli di PM2.5, PM10, NO2, O3, SO2, CO

## 🚀 Caratteristiche Principali

### Backend (Python/FastAPI)
✅ **Analisi del Fumo**
- Rileva percentuale di copertura del fumo
- Categorizza livelli (Excellent, Good, Moderate, Poor, Hazardous)
- Analizza densità nelle diverse regioni dell'immagine
- Calcola opacità complessiva
- Rileva clusters di particolato

✅ **Stima Inquinanti**
- PM2.5 (Particulate Matter fino a 2.5µm)
- PM10 (Particulate Matter fino a 10µm)  
- NO2 (Nitrogen Dioxide)
- O3 (Ozone)
- SO2 (Sulfur Dioxide)
- CO (Carbon Monoxide)

✅ **Dati Geografici**
- Reverse geocoding da coordinate GPS
- Integrazione con Open-Meteo (meteo gratuita)
- Supporto WAQI per dati AQI esterni (opzionale)
- Distanza e analisi regionale

✅ **Report Completi**
- HTML visualizzabile nel browser
- JSON strutturato
- Sommari testuali
- Raccomandazioni per la salute

### Android App
🎯 Fotocamera e Galleria
📍 GPS e Geolocalizzazione
📊 Visualizzazione Report
🗺️ Mappa con heatmap inquinamento
⚙️ Configurazione server

## 📡 API Endpoints

### Analisi Smoke

#### 1. Analisi Completa
```http
POST /api/v1/analyze-smoke

Query Parameters:
- latitude (required): GPS latitude (-90 a 90)
- longitude (required): GPS longitude (-180 a 180)
- accuracy (optional): GPS accuracy in meters
- confidence (optional): Detection confidence (0-1)
- include_weather (optional): Include weather data (true/false)

Body:
- file: Image file
```

**Response**: EnvironmentalReport completo con:
- Analisi fumo
- Stima inquinanti
- Dati geografici
- Raccomandazioni sanitarie

#### 2. Report HTML
```http
POST /api/v1/analyze-smoke/html

Response: HTML formattato per visualizzazione nel browser
```

#### 3. Sommario Rapido
```http
POST /api/v1/analyze-smoke/summary

Response: JSON compatto con info essenziali
```

#### 4. Guida AQI
```http
GET /api/v1/aqi-reference

Response: Soglie AQI, unità, effetti sulla salute
```

#### 5. Info Inquinante
```http
GET /api/v1/pollution-info?pollutant=PM2.5

Response: Dettagli su fonti, effetti, descrizione
```

## 🎨 Modelli di Dati

### SmokeAnalysis
```python
{
  "smoke_percentage": 45.2,           # 0-100%
  "smoke_level": "moderate",           # excellent, good, moderate, poor, hazardous
  "density_distribution": {
    "top_left": 12.3,
    "top_center": 45.6,
    # ... 9 regioni
  },
  "dominant_color": [128, 100, 90],    # RGB
  "particles_detected": 152,
  "opacity": 0.35                      # 0-1
}
```

### AirQualitySummary
```python
{
  "aqi_value": 125,                    # 0-500
  "primary_pollutant": "PM2.5",
  "health_recommendation": "...",
  "affected_groups": ["Children", "Elderly", "People with respiratory disease"]
}
```

### PollutantReading
```python
{
  "pollutant_type": "PM2.5",
  "value": 45.3,
  "unit": "µg/m³",
  "aqi_index": 125,
  "risk_level": "moderate_high"
}
```

### EnvironmentalReport
Contiene tutto:
- Report ID unico
- Timestamp
- Geolocalizzazione
- Analisi fumo
- Letture inquinanti
- Dati ambientali (temperature, umidità, vento)
- Raccomandazioni sanitarie

## 🏃 Quick Start

### Backend

```bash
# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run
python -m uvicorn backend.main:app --reload

# Test
python test_environmental.py image.jpg 41.9028 12.4964
```

### API Test

```bash
# Analisi completa
curl -X POST "http://localhost:8000/api/v1/analyze-smoke" \
  -H "X-API-Key: your-secret-key" \
  -F "file=@photo.jpg" \
  -F "latitude=41.9028" \
  -F "longitude=12.4964"

# HTML Report
curl -X POST "http://localhost:8000/api/v1/analyze-smoke/html" \
  ... > report.html
```

## 📊 Interpretazione AQI

| AQI | Range | Interpretazione | Effetti Sanitari |
|-----|-------|-----------------|------------------|
| 0-50 | Green | Excellent | Nessuno |
| 51-100 | Yellow | Good | Nessuno per popolazione generale |
| 101-150 | Orange | Moderate | Sensibili a rischio |
| 151-200 | Red | Poor | Pubblico generale colpito |
| 201-300 | Purple | Very Unhealthy | Evitare attività esterna |
| 300+ | Maroon | Hazardous | Emergenza sanitaria |

## 🔐 Configurazione

### .env Essenziale
```bash
API_KEY=your-secret-key
WAQI_TOKEN=your-token  # Opzionale: https://aqicn.org/
```

### Modelli YOLO Disponibili
- yolov8n (veloce, accuratezza base)
- yolov8s (velocità media)
- yolov8m (equilibrato)
- yolov8l (lento, alta accuratezza)
- yolov8x (molto lento, massima accuratezza)

## 🌐 Integrazione API Esterne

### Open-Meteo (Gratuito - Meteo)
- Temperatura
- Umidità
- Velocità vento
- Visibilità
- **NO API KEY REQUIRED**

### WAQI (Opzionale - AQI)
- Dati AQI da stazioni locali
- Richiede account gratuito
- Token da: https://aqicn.org/data-platform/

## 🔧 Struttura Backend

```
backend/
├── config/
│   └── settings.py          # Configurazione centralizzata
├── models/
│   └── schemas.py           # Modelli Pydantic (100+ linee di schemi)
├── services/
│   ├── detection.py         # YOLO + image processing
│   ├── air_quality.py       # Smoke + Pollutant analysis
│   ├── geolocation.py       # GPS + Weather integration
│   └── report_generator.py  # Report creation + HTML export
├── routes/
│   ├── detection.py         # Endpoint object detection
│   └── environmental.py     # Endpoint environmental monitoring
└── main.py                  # FastAPI app
```

## 📱 Android Integration

### Permessi Richiesti
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
```

### Flusso App
1. User scatta foto o seleziona da galleria
2. Richiedi permessi GPS
3. Invia a `/api/v1/analyze-smoke` con coordinate
4. Ricevi EnvironmentalReport completo
5. Visualizza in HTML o custom UI

## 🚀 Deployment

### Docker
```bash
docker-compose up
# API disponibile su http://localhost:8000
```

### Cloud (AWS/GCP/Azure)
Vedi `DEPLOYMENT.md` per guide complete

## 📚 Documentazione

- **README.md** - Setup completo + troubleshooting
- **API_EXAMPLES.md** - Esempi in cURL, Python, JavaScript
- **DEPLOYMENT.md** - Guide per cloud deployment
- **API Docs** - http://localhost:8000/api/docs (Swagger interattivo)

## ⚠️ Limitazioni Attuali

- Analisi fumo da CV, non da sensori professionali
- Correlazioni inquinanti stimate, non misurate
- Dipende da Open-Meteo per meteo (free, accesso gratuito)
- WAQI token opzionale (meno dati senza token)

## 🎯 Roadmap Futura

- [ ] Database SQLAlchemy per archiviare report storici
- [ ] Map heatmap con OpenStreetMap
- [ ] Trend analysis temporale
- [ ] Video frame-by-frame analysis
- [ ] Machine learning per previsioni AQI
- [ ] Notifiche real-time per soglie AQI
- [ ] Export PDF report
- [ ] Integrazione sensori IoT

## 📞 Support

Per problemi o domande:
1. Consulta `README.md`
2. Prova `test_environmental.py`
3. Accedi a http://localhost:8000/api/docs per testare live
4. Apri issue su GitHub

---

**Created**: January 2024  
**Version**: 2.0.0  
**Mode**: Environmental Monitoring  
**Status**: Production Ready ✅
