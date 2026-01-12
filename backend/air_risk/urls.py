"""
URL configuration for air_risk project.

API v1 Endpoints:
- /api/v1/auth/          - Authentication (JWT login, register, profile)
- /api/v1/air-quality/   - Geographic data (districts, provinces, stations)
- /api/v1/exposure/      - Exposure analytics (dashboard, districts, hotspots)

Documentation:
- /api/docs/             - Swagger UI
- /api/redoc/            - ReDoc
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
                "aqi_monitor": "/api/v1/aqi-monitor/",  # New service-oriented module
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
        
        # Reports
        path("reports/", include("reports.api.urls")),
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

Real-time air quality data, population exposure analysis, and risk assessment 
for all 154 districts across Pakistan.

### Key Features
- **Satellite-derived PM2.5** from MODIS AOD (South Asian calibration)
- **Sentinel-5P Pollutants** (NO2, SO2, CO, O3, HCHO, CH4, Aerosol) via GEE
- **Ground Station Data** from 366 OpenAQ monitoring stations
- **Population exposure** using WorldPop data
- **EPA AQI** with standard breakpoints
- **GeoJSON support** for map visualization

### Primary Endpoints

#### Exposure & Dashboard
| Endpoint | Description |
|----------|-------------|
| `/api/v1/exposure/dashboard/` | Main dashboard with national/province stats |
| `/api/v1/exposure/districts/` | District-level exposure data |
| `/api/v1/exposure/geojson/districts/` | GeoJSON for map visualization |

#### Ground Stations
| Endpoint | Description |
|----------|-------------|
| `/api/v1/air-quality/stations/` | All 366 monitoring stations |
| `/api/v1/air-quality/stations/{id}/` | Station detail with latest readings |
| `/api/v1/air-quality/stations/{id}/timeseries/` | Time series for charts |
| `/api/v1/air-quality/stations/latest/` | Latest readings from all stations |
| `/api/v1/air-quality/stations/nearby/` | Find stations near a point |

#### Sentinel-5P Satellite Tiles (GEE)
| Endpoint | Description |
|----------|-------------|
| `/api/v1/air-quality/gee/layers/` | Available pollutant layers |
| `/api/v1/air-quality/gee/tiles/` | Get tile URL with date selection |
| `/api/v1/air-quality/gee/dates/` | Available dates for pollutant |

#### Geographic Data
| Endpoint | Description |
|----------|-------------|
| `/api/v1/air-quality/districts/` | District boundaries (GeoJSON) |
| `/api/v1/air-quality/provinces/` | Province boundaries |
| `/api/v1/air-quality/legend/` | AQI color legend |

### Authentication
Most endpoints are public. User features require JWT token.

### Map Library Support
GEE tile endpoints include usage examples for **MapLibre GL JS**, Leaflet, and OpenLayers.
""",
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
