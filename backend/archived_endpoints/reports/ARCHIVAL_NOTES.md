# Archived: Reports App URL Configuration
## Date Archived: December 15, 2025
## Status: PARTIALLY ARCHIVED - App restored, URLs removed
## Reason for Archival: General report endpoints redundant, but Report model needed

## Overview
The general reports endpoints (`/api/v1/reports/reports/`) were identified as redundant
during API cleanup as they returned 404/empty responses. However, the Report model
and related functionality are still needed for location-based reports in the exposure app.

## What Was Archived
- URL routing: `/api/v1/reports/` include removed from main URLs
- Endpoint access: General reports ViewSet no longer accessible
- API documentation: General reports endpoints removed

## What Was Preserved
- **Report Model**: Still used by exposure app for location-based reports
- **Report Generation**: PDF generation services preserved
- **Async Tasks**: Background report generation preserved
- **Database Tables**: All migrations and data preserved
- **Dependencies**: All imports from exposure app still work

## Active Report Functionality (Preserved)
- **Location-based Reports**: `/api/v1/exposure/reports/location/` (create_location_report)
- **Report Status**: `/api/v1/exposure/reports/<id>/` (get_report_status)
- **User Reports List**: `/api/v1/exposure/reports/` (list_user_reports)

## Restoration
If general reports endpoints are needed:
1. Re-add URL include in `air_risk/urls.py`
2. Update API documentation
3. Test endpoints functionality

## Cleanup Verification
- Endpoints tested: `/api/v1/reports/reports/` (removed from routing)
- Location reports: `/api/v1/exposure/reports/*` (preserved and functional)
- No data loss: Report model and tables preserved
- Dependencies: Exposure app imports still work