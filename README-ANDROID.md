# SWV Android App

Environmental monitoring Android application with geolocation integration and report viewer. Connects to the SWV FastAPI backend for smoke detection and air quality analysis.

## Setup Instructions

### Prerequisites
- Android Studio Hedgehog (2023.1.1) or later
- JDK 11 or later
- Android SDK 34
- Gradle 8.2+

### Opening the Project
1. Open Android Studio
2. Select **File → Open** and navigate to `android/` directory
3. Wait for Gradle sync to complete
4. If prompted, install any missing SDK components

### SDK Configuration
Ensure the following SDK versions are installed via **SDK Manager**:
- **Compile SDK**: 34 (Android 14)
- **Min SDK**: 24 (Android 7.0)
- **Target SDK**: 34

## Build Configuration

### Building the APK
```bash
# Debug build
cd android
./gradlew assembleDebug

# Release build
./gradlew assembleRelease
```

The APK will be generated at:
- `app/build/outputs/apk/debug/app-debug.apk`
- `app/build/outputs/apk/release/app-release.apk`

### Running on Device/Emulator
```bash
# Install debug APK on connected device
./gradlew installDebug

# Run directly
./gradlew run
```

## Connecting to Backend

### Configuration
Update the backend URL in `app/src/main/java/com/swv/utils/Constants.kt`:

```kotlin
const val API_BASE_URL = "http://YOUR_SERVER_IP:8000/"
const val API_KEY = "your-secret-key-change-in-production"
```

### Configuration Methods
1. **Hardcoded** in `Constants.kt` (default)
2. **Build config** via `buildConfigField` in `build.gradle.kts`
3. **Runtime** via Settings UI (future feature)

### Backend Requirements
- FastAPI server running on the configured URL
- API key matching the server's `API_KEY` setting
- Network connectivity between device and server

### Development Setup
For local development with an emulator:
```kotlin
// Android emulator localhost alias
const val API_BASE_URL = "http://10.0.2.2:8000/"
```

For physical device on same network:
```kotlin
// Use your computer's local IP address
const val API_BASE_URL = "http://192.168.x.x:8000/"
```

## API Integration

### Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze-smoke` | Full smoke & air quality analysis |
| POST | `/api/v1/analyze-smoke/summary` | Quick analysis summary |
| GET | `/api/v1/reports/history` | Historical reports by location |
| GET | `/api/v1/reports/{id}` | Single report by ID |
| GET | `/api/v1/reports/stats/location` | Aggregated location statistics |
| GET | `/api/v1/aqi-reference` | AQI reference guide |
| GET | `/api/v1/pollution-info` | Pollutant information |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/detect` | Generic object detection |

### Authentication
All endpoints require an API key sent via the `X-API-Key` header. The key is configured in `ApiClient.kt` and automatically added to all requests via an OkHttp interceptor.

### Data Flow
```
Camera/Gallery → Image File → AnalysisService → Retrofit API → Backend
                                                      ↓
                                              EnvironmentalReport
                                                      ↓
                                              CacheManager (local)
                                                      ↓
                                              UI Activities/Fragments
```

## Architecture Overview

### Pattern: MVVM-ish (Model-View-ViewModel inspired)

The app follows an adapted MVVM pattern suitable for Android activities:

### Layers

#### 1. **Data Layer** (`api/`, `service/`)
- **ApiClient** - Singleton Retrofit client with OkHttp interceptor for API key
- **ApiService** - Retrofit interface defining all backend endpoints
- **models/** - Data classes matching Pydantic backend models with Gson `@SerializedName`
- **AnalysisService** - Android Service for background image upload/analysis
- **CacheManager** - SharedPreferences-based local caching of reports
- **LocationService** - FusedLocationProviderClient wrapper for GPS geolocation

#### 2. **UI Layer** (`ui/`)
- **MainActivity** - Navigation hub (Analyze, Dashboard, Reports)
- **CaptureActivity** - Camera (MediaStore) / Gallery (ActivityResultContracts) capture
- **DashboardActivity** - AQI overview with SwipeRefreshLayout, latest report summary
- **MapViewActivity** - Opens Google Maps (app or web) at current location
- **ReportActivity** - RecyclerView list of cached reports
- **ReportAdapter** - RecyclerView.Adapter binding report data to item_report layout
- **ReportFragment** - DialogFragment showing full report details

#### 3. **Utility Layer** (`utils/`)
- **Constants** - API URLs, timeouts, preference keys, AQI ranges
- **PermissionUtils** - Runtime permission handling (Camera, Location, Storage)

### Key Patterns
- **View Binding** for type-safe layout access
- **Coroutines** for async API calls (Dispatchers.IO)
- **SharedPreferences** for SQLite-free caching
- **Serializable** for passing reports between components
- **Service** for background analysis with broadcast intents

### Permissions
- `CAMERA` - Image capture
- `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION` - GPS positioning
- `READ_EXTERNAL_STORAGE` / `READ_MEDIA_IMAGES` - Gallery access
- `INTERNET` - API communication

## Dependencies

| Library | Purpose |
|---------|---------|
| Retrofit2 + Gson | HTTP API calls and JSON parsing |
| OkHttp + Logging | HTTP client with debug logging |
| Google Play Services Location | FusedLocationProviderClient GPS |
| Glide | Image loading and caching |
| CameraX / MediaStore | Camera capture via intent |
| Material Components | Material Design 3 UI |
| Kotlin Coroutines | Async operations |
| AndroidX Lifecycle | ViewModel + LiveData |
| Timber | Logging |
