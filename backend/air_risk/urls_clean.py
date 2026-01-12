"""
Air Quality & Risk API - URL Configuration

This module defines the clean, production-ready API endpoints.
All deprecated endpoints have been removed and the API is organized
into logical groups for frontend consumption.

API VERSION: v1
BASE URL: /api/v1/

=============================================================================
API STRUCTURE OVERVIEW
=============================================================================

1. AUTHENTICATION (Optional for public endpoints)
   /api/v1/auth/login/              POST - JWT token login
   /api/v1/auth/logout/             POST - Logout
   /api/v1/auth/token/refresh/      POST - Refresh JWT token
   /api/v1/auth/register/           POST - User registration
   /api/v1/auth/profile/            GET/PUT - User profile

2. GEOGRAPHIC DATA
   /api/v1/air-quality/districts/   GET - List all districts (GeoJSON)
   /api/v1/air-quality/provinces/   GET - List all provinces
   /api/v1/air-quality/stations/    GET - Ground monitoring stations
   /api/v1/air-quality/legend/      GET - AQI color legend

3. EXPOSURE DATA (Primary Frontend Endpoints)
   /api/v1/exposure/dashboard/      GET - Main dashboard summary
   /api/v1/exposure/districts/      GET - District exposure list
   /api/v1/exposure/provinces/      GET - Province exposure list
   /api/v1/exposure/national/       GET - National exposure
   /api/v1/exposure/hotspots/       GET - Pollution hotspots
   /api/v1/exposure/geojson/districts/  GET - GeoJSON for map
   /api/v1/exposure/trends/         GET - Time series trends

=============================================================================
RESPONSE FORMAT
=============================================================================

All endpoints return standardized JSON:
{
    "status": "success" | "error",
    "data": { ... } | [ ... ],
    "message": "Human readable message"
}

GeoJSON endpoints return:
{
    "status": "success",
    "data": {
        "type": "FeatureCollection",
        "features": [ ... ]
    },
    "message": "..."
}
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for container orchestration."""
    return JsonResponse({"status": "healthy", "version": "1.0.0"})


def api_root(request):
    """API root with available endpoints."""
    return JsonResponse({
        "status": "success",
        "data": {
            "version": "1.0.0",
            "endpoints": {
                "auth": "/api/v1/auth/",
                "air_quality": "/api/v1/air-quality/",
                "exposure": "/api/v1/exposure/",
            },
            "documentation": "/api/docs/",
        },
        "message": "Air Quality & Risk API v1"
    })


urlpatterns = [
    # Health check
    path("health/", health_check, name="health_check"),
    
    # API root
    path("api/v1/", api_root, name="api_root"),
    
    # Admin
    path("admin/", admin.site.urls),
    
    # API v1 endpoints
    path("api/v1/", include([
        # Authentication (JWT)
        path("auth/", include("users.urls")),
        
        # Geographic data & stations
        path("air-quality/", include("air_quality.api.urls")),
        
        # Exposure & analytics
        path("exposure/", include("exposure.api.urls")),
    ])),
]

# API Documentation (Swagger/ReDoc)
try:
    from drf_yasg.views import get_schema_view
    from drf_yasg import openapi
    from rest_framework import permissions

    schema_view = get_schema_view(
        openapi.Info(
            title="Air Quality & Risk API",
            default_version="v1",
            description="""
## Pakistan Air Quality Monitoring & Risk Assessment API

This API provides real-time air quality data, population exposure analysis,
and risk assessment for all 154 districts across Pakistan.

### Key Features:
- **Satellite-derived PM2.5** from MODIS AOD with South Asian calibration
- **Population exposure** calculated using WorldPop data
- **EPA AQI** with standard breakpoints
- **GeoJSON support** for map visualization

### Data Coverage:
- 154 districts across 7 provinces/territories
- ~253 million population coverage
- Daily satellite updates

### Authentication:
Most endpoints are public. User-specific features require JWT authentication.
""",
            terms_of_service="https://airrisk.pk/terms/",
            contact=openapi.Contact(email="api@airrisk.pk"),
            license=openapi.License(name="MIT License"),
        ),
        public=True,
        permission_classes=[permissions.AllowAny],
    )

    urlpatterns += [
        path("api/docs/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    ]
except ImportError:
    pass

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
