# Archived: Reports App
## Date Archived: December 15, 2025
## Reason for Archival: Redundant general report management system

## Overview
The reports app was a comprehensive report management system with templates, subscriptions,
and PDF generation capabilities. However, it was identified as redundant during API cleanup.

## Duplicate/Redundant Functionality
- **General Report Management**: The reports app provided generic report creation/management
- **PDF Generation**: Overlapped with location-based reports in exposure app
- **Template System**: Not actively used or maintained
- **Subscription System**: No active subscriptions or usage

## Active Report Functionality (Preserved)
- **Location-based Reports**: `/api/v1/exposure/reports/location/` (create_location_report)
- **Report Status**: `/api/v1/exposure/reports/<id>/` (get_report_status)
- **User Reports List**: `/api/v1/exposure/reports/` (list_user_reports)

## Files Archived
- `reports/__init__.py`
- `reports/admin.py`
- `reports/apps.py`
- `reports/models.py` (Report, ReportSubscription, ReportTemplate)
- `reports/urls.py`
- `reports/api/urls.py`
- `reports/api/views.py`
- `reports/api/serializers.py`
- `reports/services/`
- `reports/tasks.py`
- `reports/migrations/`
- `reports/__pycache__/`

## Database Impact
- **Models Removed**: Report, ReportSubscription, ReportTemplate
- **Migrations**: 4 migration files archived (0001-0004)
- **Data**: Any existing report data should be considered obsolete

## Migration Notes
- All active report functionality preserved in `exposure/api/`
- No URL routing conflicts (different endpoint paths)
- Report generation logic can be migrated if needed in future

## Restoration
If the general reports system is needed:
1. Restore files from `archived_endpoints/reports/`
2. Re-run migrations
3. Re-add URL include in `air_risk/urls.py`
4. Update any dependencies

## Cleanup Verification
- Endpoints tested: `/api/v1/reports/reports/` (was 404/empty)
- No active usage detected in codebase
- Comprehensive API test confirmed redundancy