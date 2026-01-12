"""
URL routes for exposure API.

Clean, production-ready endpoints for air quality exposure analysis.

=============================================================================
PRIMARY ENDPOINTS (Use these for frontend)
=============================================================================

Dashboard & Summary:
    GET /api/v1/exposure/dashboard/
        - National summary (AQI, PM2.5, population)
        - Province rankings
        - Top 10 worst districts
        - Population breakdown by AQI category

District Exposure:
    GET /api/v1/exposure/districts/
        - List all district exposures
        - Filter: ?province=PUNJAB, ?date=2025-12-04
    
    GET /api/v1/exposure/districts/{id}/
        - Single district detail

Province Exposure:
    GET /api/v1/exposure/provinces/
        - Province-level aggregated data
    
    GET /api/v1/exposure/provinces/{id}/
        - Single province detail

National Exposure:
    GET /api/v1/exposure/national/
        - National-level statistics

GeoJSON (Map Visualization):
    GET /api/v1/exposure/geojson/districts/
        - GeoJSON FeatureCollection for choropleth map
        - Filter: ?province=PUNJAB

Hotspots:
    GET /api/v1/exposure/hotspots/
        - Pollution hotspot clusters

Trends:
    GET /api/v1/exposure/trends/
        - Time series data
        - Params: ?scope=national|province|district&days=30

=============================================================================
RESPONSE FORMAT
=============================================================================

{
    "status": "success" | "error",
    "data": { ... },
    "message": "Human readable message"
}
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views_refactored import (
    DistrictExposureViewSet,
    HotspotViewSet,
    ProvinceExposureViewSet,
    NationalExposureViewSet,
)
from .satellite_views_refactored import (
    DashboardView,
    ExposureTrendView,
    DistrictExposureGeoJSONView,
)

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================
router = DefaultRouter()

# Core exposure endpoints
router.register(r"districts", DistrictExposureViewSet, basename="district-exposure")
router.register(r"provinces", ProvinceExposureViewSet, basename="province-exposure")
router.register(r"national", NationalExposureViewSet, basename="national-exposure")
router.register(r"hotspots", HotspotViewSet, basename="hotspot")

# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # ViewSet routes (list, retrieve, custom actions)
    path("", include(router.urls)),
    
    # ==========================================================================
    # PRIMARY FRONTEND ENDPOINTS
    # ==========================================================================
    
    # Dashboard - Main entry point for frontend
    # GET /api/v1/exposure/dashboard/
    # Returns: national summary, province rankings, worst districts, AQI breakdown
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    
    # Time series trends
    # GET /api/v1/exposure/trends/?scope=national&days=30
    path("trends/", ExposureTrendView.as_view(), name="exposure-trends"),
    
    # ==========================================================================
    # GEOJSON ENDPOINTS (Map Visualization)
    # ==========================================================================
    
    # District exposure as GeoJSON FeatureCollection
    # GET /api/v1/exposure/geojson/districts/?province=PUNJAB
    path("geojson/districts/", DistrictExposureGeoJSONView.as_view(), name="district-geojson"),
]
