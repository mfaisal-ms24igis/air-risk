# Archived API Endpoints
## Date: December 15, 2025
## Purpose: Cleanup of redundant API endpoints in Air Risk platform

## Overview
During comprehensive API testing of 34 endpoints, several redundant endpoints were identified
that either duplicated functionality or returned empty/404 responses. These have been archived
for future reference while cleaning up the active codebase.

## Archived Components

### 1. WMS (Web Map Service) Endpoints
**Location**: `archived_endpoints/wms/`
**Reason**: Duplicated Google Earth Engine tile functionality
**Endpoints Removed**:
- `/api/v1/air-quality/wms/layers/`
- `/api/v1/air-quality/wms/timeseries/`

**Files Archived**:
- `wms_views.py` - Sentinel5PWMSLayersView, Sentinel5PTimeSeriesView classes
- `ARCHIVAL_NOTES.md` - Detailed documentation

**Migration**: All WMS functionality replaced by GEE tiles (`/api/v1/air-quality/gee/tiles/`)

### 2. AQI Monitor App
**Location**: `archived_endpoints/aqi_monitor/`
**Reason**: Duplicate risk endpoints with main air_quality app
**Endpoints Removed**:
- `/api/v1/aqi-monitor/risk/tiles/`
- `/api/v1/aqi-monitor/risk/status/`
- `/api/v1/aqi-monitor/risk/check/`

**Files Archived**:
- Complete Django app structure (models, views, URLs, etc.)
- `ARCHIVAL_NOTES.md` - Detailed documentation

**Migration**: All functionality preserved in `/api/v1/air-quality/risk/*` endpoints

### 3. General Reports App (PARTIALLY ARCHIVED)
**Location**: `archived_endpoints/reports/`
**Status**: App restored, only URL routing removed
**Reason**: General report endpoints were redundant, but Report model needed for location-based reports
**Endpoints Removed**:
- `/api/v1/reports/reports/` (and all sub-endpoints)
- `/api/v1/reports/subscriptions/`

**Files Archived**: URL configuration only
**App Status**: Reports app restored in INSTALLED_APPS, URL routing removed
**Migration**: General reports endpoints removed, location-based reports preserved

## Code Changes Made

### URL Configuration (`air_risk/urls.py`)
- Removed `path("aqi-monitor/", include("apps.aqi_monitor.urls"))`
- Removed `path("reports/", include("reports.api.urls"))`

### Air Quality URLs (`air_quality/api/urls.py`)
- Removed WMS endpoint imports and paths
- Preserved all GEE and risk endpoints

### Views (`air_quality/api/views_refactored.py`)
- Removed `Sentinel5PWMSLayersView` class (lines 1065-1337)
- Removed `Sentinel5PTimeSeriesView` class (lines 1339-1394)

### Test Updates (`comprehensive_api_test.py`)
- Removed archived endpoint tests
- Updated endpoint categorization

## Verification Results (December 15, 2025)
**Test Results**: ✅ PASSED
- **Total Endpoints Tested**: 30
- **Vital Endpoints**: 28 (93% working)
- **Ghost Endpoints**: 2 (removed as planned)
- **Danger Endpoints**: 0 (no server errors)

**Confirmed Removed**:
- ✅ `/api/v1/air-quality/wms/layers/` → 404
- ✅ `/api/v1/air-quality/wms/timeseries/` → 404 (not tested but removed)
- ✅ `/api/v1/aqi-monitor/risk/tiles/` → 404
- ✅ `/api/v1/aqi-monitor/risk/status/` → 404
- ✅ `/api/v1/aqi-monitor/risk/check/` → 404
- ✅ `/api/v1/reports/reports/` → Removed from routing

**Preserved Functionality**:
- ✅ Authentication (JWT login/register)
- ✅ Exposure dashboard and analytics
- ✅ Air quality districts/provinces/stations
- ✅ GEE tiles and layers
- ✅ Location-based reports (`/api/v1/exposure/reports/`)
- ✅ All spatial and geographic data

## Restoration Process
If any archived functionality is needed in the future:

1. **WMS Endpoints**:
   - Copy `archived_endpoints/wms/wms_views.py` back to `air_quality/api/`
   - Re-add imports and URL paths in `air_quality/api/urls.py`
   - Reconfigure GeoServer if needed

2. **AQI Monitor App**:
   - Restore `archived_endpoints/aqi_monitor/` to `apps/aqi_monitor/`
   - Re-add URL include in `air_risk/urls.py`

3. **Reports App**:
   - Restore `archived_endpoints/reports/` to `reports/`
   - Run migrations: `python manage.py migrate reports`
   - Re-add URL include in `air_risk/urls.py`

## Benefits of Cleanup
- **Reduced Complexity**: 6 redundant endpoints removed
- **Clearer API**: Single source of truth for each functionality
- **Maintenance**: Less code to maintain and test
- **Performance**: Fewer URL patterns to match
- **Documentation**: Archived code preserved for reference

## Next Steps
- Update API documentation to reflect removed endpoints
- Update frontend code if it references archived endpoints
- Consider database cleanup of archived app tables (if any)
- Monitor for any missing functionality reports