# Archived: AQI Monitor App
## Date Archived: December 15, 2025
## Reason for Archival: Duplicate functionality with main air_quality app

## Overview
The aqi_monitor app was a separate Django app that provided risk assessment endpoints.
However, these endpoints were duplicates of the risk endpoints in the main air_quality app.

## Duplicate Endpoints
- `/api/v1/aqi-monitor/risk/tiles/` → `/api/v1/air-quality/risk/tiles/`
- `/api/v1/aqi-monitor/risk/status/` → `/api/v1/air-quality/risk/status/`
- `/api/v1/aqi-monitor/risk/check/` → `/api/v1/air-quality/risk/check/`

## Files Archived
- `apps/aqi_monitor/__init__.py`
- `apps/aqi_monitor/admin.py`
- `apps/aqi_monitor/apps.py`
- `apps/aqi_monitor/models.py`
- `apps/aqi_monitor/urls.py`
- `apps/aqi_monitor/views.py`
- `apps/aqi_monitor/__pycache__/`

## Migration Notes
- All functionality preserved in `air_quality/api/risk_views.py`
- No data migration required (app had no models)
- URL routing updated in `air_risk/urls.py` to remove aqi-monitor inclusion

## Restoration
If needed, the app can be restored by:
1. Moving files back to `apps/aqi_monitor/`
2. Re-adding the URL include in `air_risk/urls.py`
3. Updating any imports if necessary