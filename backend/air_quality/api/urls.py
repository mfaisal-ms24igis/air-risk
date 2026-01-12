"""
URL routes for air quality API.

Geographic and reference data endpoints.

=============================================================================
ENDPOINT REFERENCE
=============================================================================

Districts:
    GET /api/v1/air-quality/districts/
        - List all districts with geometry (GeoJSON)
    GET /api/v1/air-quality/districts/{id}/
        - Single district detail
    GET /api/v1/air-quality/districts/{id}/geojson/
        - Single district as GeoJSON

Provinces:
    GET /api/v1/air-quality/provinces/
        - List all provinces
    GET /api/v1/air-quality/provinces/{id}/
        - Province detail with district list

Stations:
    GET /api/v1/air-quality/stations/
        - Ground monitoring stations
    GET /api/v1/air-quality/stations/{id}/
        - Single station detail with latest readings
    GET /api/v1/air-quality/stations/geojson/
        - All stations as GeoJSON
    GET /api/v1/air-quality/stations/nearby/?lat=31.5&lon=74.3&radius=50
        - Find stations near a point
    GET /api/v1/air-quality/stations/latest/?parameter=PM25
        - Latest readings from all stations
    GET /api/v1/air-quality/stations/{id}/readings/?days=7
        - Recent readings for a station
    GET /api/v1/air-quality/stations/{id}/timeseries/?parameter=PM25&interval=daily
        - Time series data for charts

WMS Layers (Sentinel-5P via GeoServer):
    GET /api/v1/air-quality/wms/layers/
        - All Sentinel-5P pollutant layer configurations
    GET /api/v1/air-quality/wms/layers/?pollutant=NO2&date=2025-12-01
        - Filtered by pollutant and date
    GET /api/v1/air-quality/wms/timeseries/?pollutant=NO2
        - Available time steps for a pollutant

GEE Tiles (Sentinel-5P via Google Earth Engine):
    GET /api/v1/air-quality/gee/layers/
        - All available GEE Sentinel-5P layer configurations
    GET /api/v1/air-quality/gee/tiles/?pollutant=NO2&date=2025-01-15
        - Get GEE tile URL for specific pollutant and date
    GET /api/v1/air-quality/gee/dates/?pollutant=NO2
        - Query available dates in GEE for a pollutant

Reference:
    GET /api/v1/air-quality/legend/
        - AQI color legend and health messages
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DistrictViewSet,
    ProvinceViewSet,
    GroundStationViewSet,
    AQILegendView,
    GEESentinel5PLayersView,
    GEESentinel5PTilesView,
    GEESentinel5PDatesView,
    GEESentinel5PValueView,
)
from .views_gee_proxy import GEETileProxyView
from .risk_views import get_risk_tiles, get_risk_status, trigger_manual_check
from .spatial_views import (
    districts_list,
    district_detail,
    district_tiles,
    stations_nearby,
)

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================
router = DefaultRouter()
router.register(r"districts", DistrictViewSet, basename="district")
router.register(r"provinces", ProvinceViewSet, basename="province")
router.register(r"stations", GroundStationViewSet, basename="station")

# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    
    # AQI legend with colors and health messages
    path("legend/", AQILegendView.as_view(), name="aqi-legend"),
    
    # Sentinel-5P GEE tile endpoints (Google Earth Engine)
    path("gee/layers/", GEESentinel5PLayersView.as_view(), name="gee-layers"),
    path("gee/tiles/", GEESentinel5PTilesView.as_view(), name="gee-tiles"),
    path("gee/dates/", GEESentinel5PDatesView.as_view(), name="gee-dates"),
    path("gee/value/", GEESentinel5PValueView.as_view(), name="gee-value"),
    # Accept both template strings and actual coordinates
    path("gee/proxy/<str:map_id>/<str:z>/<str:x>/<str:y>", GEETileProxyView.as_view(), name="gee-proxy"),
    
    # Dynamic Risk Endpoints (NEW - Hybrid Local + GEE Data Fusion)
    path("risk/tiles/", get_risk_tiles, name="risk-tiles"),
    path("risk/status/", get_risk_status, name="risk-status"),
    path("risk/check/", trigger_manual_check, name="risk-manual-check"),
    
    # Tiered Spatial Endpoints (BASIC/PREMIUM access control)
    path("spatial/districts/", districts_list, name="spatial-districts-list"),
    path("spatial/districts/<int:district_id>/", district_detail, name="spatial-district-detail"),
    path("spatial/districts/<int:district_id>/tiles/", district_tiles, name="spatial-district-tiles"),
    path("spatial/stations/nearby/", stations_nearby, name="spatial-stations-nearby"),
]
