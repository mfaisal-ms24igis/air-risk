# Backend Implementation Complete - Tiered Air Quality Dashboard

**Date**: December 11, 2025  
**Status**: ✅ Backend 100% Complete | ⏭️ Frontend Pending  
**Technology Stack**: Django 5.x + DRF + PostGIS + Django-Q + LM Studio

---

## 📊 Implementation Summary

### Phase 1: User Subscription Tiers ✅

**Objective**: Implement BASIC/PREMIUM user tiers with JWT integration

**Files Modified/Created**:
- `users/models.py` - Added subscription tier fields
- `users/permissions.py` - NEW: DRF permission classes
- `users/serializers.py` - Updated JWT payload with tier info

**Key Features**:
- ✅ SubscriptionTier choices (BASIC, PREMIUM)
- ✅ `premium_until` expiry tracking
- ✅ `is_premium` property with timezone-aware validation
- ✅ `tier` property returns active tier after expiry check
- ✅ JWT tokens include `tier` and `is_premium` in user payload
- ✅ IsPremiumUser and IsBasicOrPremiumUser permission classes

**Migration**: `users/migrations/0002_customuser_premium_until_and_more.py`

---

### Phase 2: Tiered Spatial API Endpoints ✅

**Objective**: Create map data APIs with tiered access control

**Files Created**:
- `air_quality/api/spatial_views.py` (261 lines)
- `air_quality/constants.py` - Updated with POLLUTANT_LAYERS

**Endpoints Implemented**:

| Endpoint | Method | Auth | Tier | Description |
|----------|--------|------|------|-------------|
| `/api/v1/air-quality/spatial/districts/` | GET | Required | All | List districts (basic: simplified geometry) |
| `/api/v1/air-quality/spatial/districts/{id}/` | GET | Required | All | District details (premium: +bounds, stations, pollutants) |
| `/api/v1/air-quality/spatial/districts/{id}/tiles/` | GET | Required | **PREMIUM** | GCS signed URLs for raster tiles |
| `/api/v1/air-quality/spatial/stations/nearby/` | GET | Required | All | Location search (basic: 10 limit, premium: 50) |

**Tier Differentiation**:
- **BASIC**: Simplified GeoJSON (100m tolerance), 10 station limit, no tile access
- **PREMIUM**: Full geometry, 50 station limit, pollutant data, GCS tile URLs

**Pollutant Layers** (6 total):
- NO2, PM2.5, PM10, SO2, CO, O3
- Each with AQI breakpoints, color schemes, health impacts

---

### Phase 3: Location-Based Trend Analysis ✅

**Objective**: Analyze 30-day air quality trends for any location in Pakistan

**Files Created**:
- `exposure/services/trend_analyzer.py` (254 lines)

**TrendAnalyzer Class**:

```python
analyzer = TrendAnalyzer(
    lat=31.5204,
    lng=74.3587,
    radius_km=5.0,
    start_date=datetime(2025, 11, 11),
    end_date=datetime(2025, 12, 11)
)

summary = analyzer.generate_summary()
```

**Features**:
- ✅ `get_nearby_stations()` - Find ground stations within radius
- ✅ `get_ground_trends()` - Statistical analysis (mean, min, max, p95)
- ✅ `calculate_health_risk()` - AQI-based risk categorization
- ✅ `generate_summary()` - Comprehensive trend report

**Output Structure**:
```json
{
  "location": {"lat": 31.5204, "lng": 74.3587, "radius_km": 5.0},
  "date_range": {"start": "2025-11-11", "end": "2025-12-11"},
  "stations_found": 3,
  "ground_trends": {
    "PM2.5": {"mean": 85.5, "min": 42.0, "max": 165.0, "p95": 148.0, "trend": "increasing"},
    "NO2": {"mean": 42.3, "trend": "stable"}
  },
  "health_risk": {"level": "unhealthy", "message": "..."}
}
```

---

### Phase 4: Async Report Generation ✅

**Objective**: Premium users get async PDF generation with Django-Q

**Files Modified/Created**:
- `reports/models.py` - Added location fields
- `reports/tasks.py` - Appended Django-Q tasks (148 lines)
- `reports/management/commands/setup_schedules.py` - NEW: Django-Q cron setup

**Report Model Updates**:
- ✅ Added `LOCATION` report type
- ✅ `location` PointField (srid=4326) for analysis center
- ✅ `radius_km` FloatField for search radius
- ✅ `include_ai_insights` BooleanField for AI enhancement

**Tasks Created**:

1. **`generate_location_report_async(report_id)`**:
   - Creates TrendAnalyzer instance
   - Calls AI insights service if `include_ai_insights=True`
   - Generates PDF with ReportLab
   - Saves to `media/reports/{user_id}/location_{report_id}.pdf`
   - Sets expiry: +30 days for premium, +7 days for basic

2. **`cleanup_expired_reports_async()`**:
   - Scheduled via Django-Q cron (daily at 2 AM)
   - Deletes report files past `expires_at`
   - Cleanup command: `python manage.py setup_schedules`

**Migration**: `reports/migrations/0003_report_include_ai_insights_report_location_and_more.py`

---

### Phase 5: LM Studio AI Insights ✅

**Objective**: Generate AI-powered health recommendations using local inference

**Files Created**:
- `reports/services/ai_insights.py` (313 lines)
- `backend/LM_STUDIO_SETUP.md` - Comprehensive documentation

**AI Integration Architecture**:

```
User Request → Django View → TrendAnalyzer → ai_insights.py → LM Studio (localhost:1234)
                                                    ↓
                                                Fallback (if offline)
```

**Main Functions**:

1. **`generate_health_recommendations(pollutant_data, location, user_context)`**:
   - POSTs to `http://localhost:1234/v1/chat/completions`
   - OpenAI-compatible API (drop-in replacement)
   - Timeout: 30s (configurable)
   - Model: Auto-detected or manual via `LM_STUDIO_MODEL` env var

2. **`_build_health_prompt(pollutant_data, location, user_context)`**:
   - Constructs structured prompt:
     ```
     You are a public health expert analyzing air quality for Lahore.
     
     Current levels:
     - PM2.5: 85.5 µg/m³ (AQI: 165, increasing)
     - NO2: 42.3 µg/m³ (AQI: 95, stable)
     
     Provide:
     1. Health impact summary
     2. 3-5 actionable recommendations
     3. Risk level
     4. Vulnerable groups
     ```

3. **`_parse_ai_response(response_text)`**:
   - Extracts: `summary`, `recommendations`, `risk_level`, `sensitive_groups`
   - Handles malformed AI output gracefully

4. **`test_lm_studio_connection()`**:
   - Health check: GET `http://localhost:1234/v1/models`
   - Returns available models and connection status

**Fallback System**:
- ✅ **FALLBACK_RECOMMENDATIONS** dict with rule-based advice
- ✅ `get_fallback_recommendations(aqi_level)` for offline mode
- ✅ Triggers on: connection timeout, server down, model error

**Environment Variables**:
```bash
LM_STUDIO_URL=http://localhost:1234/v1  # Default
LM_STUDIO_MODEL=auto  # Auto-detect loaded model
LM_STUDIO_TIMEOUT=30  # Request timeout (seconds)
LM_STUDIO_TEMPERATURE=0.7  # Response creativity
```

**Recommended Models**:
- **Production**: Mistral-7B-Instruct-v0.3 (Q4_K_M, 4.1 GB, 6 GB VRAM)
- **Development**: Phi-3-Mini-4K (Q4_K_M, 2.4 GB, 4 GB VRAM)
- **Testing**: TinyLlama-1.1B (Q4, 0.6 GB, 2 GB VRAM)

---

### Phase 6: Location Report API Endpoints ✅

**Objective**: Create RESTful endpoints for location-based report workflow

**Files Modified**:
- `exposure/api/views.py` - Added 312 lines (3 endpoints)
- `exposure/api/urls.py` - Added report routes

**Endpoints Implemented**:

#### 1. **Create Location Report**
```http
POST /api/v1/exposure/reports/location/
Authorization: Bearer <jwt_token>

{
  "lat": 31.5204,
  "lng": 74.3587,
  "radius_km": 5.0,
  "start_date": "2025-11-11",
  "end_date": "2025-12-11",
  "include_ai": true  // Premium only
}
```

**BASIC User Response** (synchronous):
```json
{
  "report_id": 123,
  "status": "completed",
  "download_url": "/media/reports/1/location_123.pdf",
  "file_size_kb": 145.6,
  "tier": "BASIC"
}
```

**PREMIUM User Response** (async):
```json
{
  "report_id": 124,
  "status": "processing",
  "poll_url": "/api/v1/exposure/reports/124/",
  "estimated_time_seconds": 30,
  "tier": "PREMIUM",
  "include_ai": true
}
```

**Validation**:
- ✅ Pakistan bounds check (60.87-77.84°E, 23.69-37.08°N)
- ✅ Max radius: 50 km
- ✅ Max date range: 30 days
- ✅ AI insights require `is_premium=True`

**Tier Differences**:
- **BASIC**: Immediate PDF, 7-day expiry, no AI, simplified data
- **PREMIUM**: Async task queue, 30-day expiry, AI insights, full data

---

#### 2. **Get Report Status**
```http
GET /api/v1/exposure/reports/{report_id}/
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "report_id": 124,
  "status": "completed",
  "download_url": "/media/reports/1/location_124.pdf",
  "file_size_kb": 245.6,
  "created_at": "2025-12-11T10:30:00Z",
  "completed_at": "2025-12-11T10:30:25Z",
  "expires_at": "2026-01-10T10:30:25Z"
}
```

**Status Values**:
- `pending` - Report created, not yet processing
- `processing` - Django-Q task running
- `completed` - PDF ready for download
- `failed` - Error during generation (see `error` field)

---

#### 3. **List User Reports**
```http
GET /api/v1/exposure/reports/?status=completed&limit=20
Authorization: Bearer <jwt_token>
```

**Response**:
```json
{
  "count": 5,
  "tier": "PREMIUM",
  "reports": [
    {
      "id": 124,
      "type": "LOCATION",
      "title": "Location Report (31.5204, 74.3587)",
      "status": "completed",
      "created_at": "2025-12-11T10:30:00Z",
      "download_url": "/media/reports/1/location_124.pdf",
      "file_size_kb": 245.6
    }
  ]
}
```

**Query Parameters**:
- `status`: Filter by status (completed, processing, failed)
- `limit`: Max results (1-100, default: 20)

---

## 🗄️ Database Schema Updates

### Users Table
```sql
ALTER TABLE users_customuser ADD COLUMN subscription_tier VARCHAR(10) DEFAULT 'BASIC';
ALTER TABLE users_customuser ADD COLUMN premium_until TIMESTAMP NULL;
```

### Reports Table
```sql
ALTER TABLE reports_report ADD COLUMN report_type VARCHAR(20);
ALTER TABLE reports_report ADD COLUMN location GEOMETRY(Point, 4326);
ALTER TABLE reports_report ADD COLUMN radius_km FLOAT;
ALTER TABLE reports_report ADD COLUMN include_ai_insights BOOLEAN DEFAULT FALSE;
```

**Run Migrations**:
```bash
python manage.py migrate users
python manage.py migrate reports
```

---

## 🚀 Deployment Checklist

### 1. Environment Variables

Update `backend/.env`:
```bash
# LM Studio
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=auto
LM_STUDIO_TIMEOUT=30

# Django-Q
DJANGO_Q_WORKERS=2
DJANGO_Q_TIMEOUT=90
DJANGO_Q_RETRY=120
```

### 2. Apply Migrations
```bash
cd backend
python manage.py migrate users
python manage.py migrate reports
```

### 3. Setup Django-Q Schedules
```bash
python manage.py setup_schedules
```

Output:
```
✅ Created schedule: cleanup_expired_reports (daily at 2 AM)
```

### 4. Start Django-Q Cluster
```bash
python manage.py qcluster
```

Expected:
```
[Q] INFO Q Cluster django-dev starting.
[Q] INFO Process-1 ready for work at 12345
```

### 5. Start LM Studio (Optional)

See `LM_STUDIO_SETUP.md` for detailed instructions.

**Quick Start**:
1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. Download Mistral-7B-Instruct (Q4_K_M)
3. Go to Local Server tab → Start Server (port 1234)
4. Test: `curl http://localhost:1234/v1/models`

---

## 🧪 Testing

### Test Tiered Access

**BASIC User**:
```bash
# Login
curl -X POST http://localhost:8000/api/v1/users/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "basic_user", "password": "pass123"}'

# Extract token
export TOKEN="eyJ0eXAi..."

# Test district listing (should return simplified geometry)
curl http://localhost:8000/api/v1/air-quality/spatial/districts/ \
  -H "Authorization: Bearer $TOKEN"

# Test tile access (should fail with 403)
curl http://localhost:8000/api/v1/air-quality/spatial/districts/1/tiles/ \
  -H "Authorization: Bearer $TOKEN"
```

**PREMIUM User**:
```bash
# Test tile access (should succeed)
curl http://localhost:8000/api/v1/air-quality/spatial/districts/1/tiles/ \
  -H "Authorization: Bearer $PREMIUM_TOKEN"
```

---

### Test Report Generation

**Create Report**:
```bash
curl -X POST http://localhost:8000/api/v1/exposure/reports/location/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 31.5204,
    "lng": 74.3587,
    "radius_km": 5.0,
    "start_date": "2025-11-11",
    "end_date": "2025-12-11",
    "include_ai": true
  }'
```

**Poll Status**:
```bash
curl http://localhost:8000/api/v1/exposure/reports/124/ \
  -H "Authorization: Bearer $TOKEN"
```

**List Reports**:
```bash
curl http://localhost:8000/api/v1/exposure/reports/?status=completed \
  -H "Authorization: Bearer $TOKEN"
```

---

### Test LM Studio Integration

**Shell Test**:
```bash
python manage.py shell
```

```python
from reports.services.ai_insights import test_lm_studio_connection

# Check connection
result = test_lm_studio_connection()
print(result['status'])  # Should print 'connected'

# Generate recommendations
from reports.services.ai_insights import generate_health_recommendations

pollutant_data = {
    'PM2.5': {'current': 85.5, 'trend': 'increasing', 'aqi': 165}
}

result = generate_health_recommendations(
    pollutant_data=pollutant_data,
    location="Lahore, Pakistan"
)

print(result['summary'])
```

---

## 📁 Files Created/Modified Summary

### New Files (9 total)

1. **users/permissions.py** (32 lines)
   - IsPremiumUser, IsBasicOrPremiumUser permission classes

2. **air_quality/api/spatial_views.py** (261 lines)
   - Tiered spatial endpoints for districts and stations

3. **exposure/services/trend_analyzer.py** (254 lines)
   - Location-based 30-day trend analysis service

4. **reports/services/ai_insights.py** (313 lines)
   - LM Studio integration with fallback system

5. **reports/management/commands/setup_schedules.py** (48 lines)
   - Django-Q schedule initialization

6. **backend/LM_STUDIO_SETUP.md** (500+ lines)
   - Comprehensive LM Studio documentation

7. **exposure/api/views.py** - Added 312 lines
   - Location report endpoints (create, status, list)

### Modified Files (7 total)

1. **users/models.py**
   - Added `subscription_tier`, `premium_until`, `is_premium`, `tier`

2. **users/serializers.py**
   - Updated JWT payload, UserProfileSerializer

3. **air_quality/constants.py**
   - Added POLLUTANT_LAYERS (6 pollutants)

4. **air_quality/api/urls.py**
   - Added spatial routes

5. **reports/models.py**
   - Added location fields, LOCATION report type

6. **reports/tasks.py**
   - Appended Django-Q tasks (148 lines)

7. **exposure/api/urls.py**
   - Added report routes

### Migrations (2 total)

1. `users/migrations/0002_customuser_premium_until_and_more.py`
2. `reports/migrations/0003_report_include_ai_insights_report_location_and_more.py`

---

## 🎯 Next Steps (Frontend)

### 1. Zustand State Management

Create stores:
- `frontend/src/store/authStore.ts` - User, tier, login, logout
- `frontend/src/store/mapStore.ts` - Selected district, active layers
- `frontend/src/store/reportStore.ts` - Report list, generation state

### 2. MapLibre Components

Create components:
- `frontend/src/components/Map/BasicMap.tsx` - Simplified for BASIC users
- `frontend/src/components/Map/PremiumMap.tsx` - Full features + tile layers
- `frontend/src/components/Map/TierToggle.tsx` - Show tier-locked features

### 3. Report Generation UI

Create components:
- `frontend/src/components/Reports/ReportGenerator.tsx` - Form + polling
- `frontend/src/components/Reports/ReportHistory.tsx` - List past reports
- `frontend/src/components/Reports/DownloadButton.tsx` - PDF download

### 4. Documentation

- API reference for frontend developers
- Zustand store usage guide
- MapLibre integration examples

---

## ✅ Backend Completion Status

| Phase | Status | Files | Lines | Tests |
|-------|--------|-------|-------|-------|
| User Tiers | ✅ Complete | 3 | 150 | Pending |
| Spatial APIs | ✅ Complete | 2 | 261 | Pending |
| Trend Analysis | ✅ Complete | 1 | 254 | Pending |
| Async Reports | ✅ Complete | 3 | 200 | Pending |
| LM Studio | ✅ Complete | 2 | 813 | Pending |
| API Endpoints | ✅ Complete | 2 | 312 | Pending |

**Total**: 13 files created/modified, ~2000 lines of code

---

## 🔗 API Endpoint Reference

### Authentication
- `POST /api/v1/users/token/` - Login (get JWT)
- `POST /api/v1/users/token/refresh/` - Refresh JWT

### Spatial Data (Tiered)
- `GET /api/v1/air-quality/spatial/districts/` - List districts
- `GET /api/v1/air-quality/spatial/districts/{id}/` - District details
- `GET /api/v1/air-quality/spatial/districts/{id}/tiles/` - Raster tiles (PREMIUM)
- `GET /api/v1/air-quality/spatial/stations/nearby/?lat=X&lng=Y` - Nearby stations

### Location Reports
- `POST /api/v1/exposure/reports/location/` - Create report
- `GET /api/v1/exposure/reports/{id}/` - Report status
- `GET /api/v1/exposure/reports/` - List user reports

### Exposure Data
- `GET /api/v1/exposure/dashboard/` - National summary
- `GET /api/v1/exposure/districts/` - District exposure
- `GET /api/v1/exposure/provinces/` - Province exposure
- `GET /api/v1/exposure/hotspots/` - Top polluted areas

---

**Implementation Date**: December 11, 2025  
**Backend Status**: ✅ 100% Complete  
**Frontend Status**: ⏭️ Pending  
**Next Milestone**: Frontend implementation (Zustand + MapLibre + Reports UI)
