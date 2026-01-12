"""
URL routes for exposure API.

Primary endpoints for air quality exposure analysis.

=============================================================================
ENDPOINT REFERENCE
=============================================================================

Dashboard (Main Entry Point):
    GET /api/v1/exposure/dashboard/
        Returns: national summary, province rankings, worst districts

District Exposure:
    GET /api/v1/exposure/districts/
    GET /api/v1/exposure/districts/?province=PUNJAB
    GET /api/v1/exposure/districts/{id}/

Province Exposure:  
    GET /api/v1/exposure/provinces/
    GET /api/v1/exposure/provinces/{id}/

National Exposure:
    GET /api/v1/exposure/national/

Hotspots:
    GET /api/v1/exposure/hotspots/

GeoJSON (Maps):
    GET /api/v1/exposure/geojson/districts/
    GET /api/v1/exposure/geojson/districts/?province=PUNJAB

Trends:
    GET /api/v1/exposure/trends/?scope=national&days=30
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    DistrictExposureViewSet,
    HotspotViewSet,
    ProvinceExposureViewSet,
    NationalExposureViewSet,
    CalculateGEEExposureView,
)
from .satellite_views import (
    DashboardView,
    ExposureTrendView,
    DistrictExposureGeoJSONView,
)

# =============================================================================
# ROUTER CONFIGURATION
# =============================================================================
router = DefaultRouter()
router.register(r"districts", DistrictExposureViewSet, basename="district-exposure")
router.register(r"provinces", ProvinceExposureViewSet, basename="province-exposure")
router.register(r"national", NationalExposureViewSet, basename="national-exposure")
router.register(r"hotspots", HotspotViewSet, basename="hotspot")

# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # ViewSet routes
    path("", include(router.urls)),
    
    # Dashboard - Main frontend entry point
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    
    # Time series trends
    path("trends/", ExposureTrendView.as_view(), name="exposure-trends"),
    
    # GeoJSON for map visualization
    path("geojson/districts/", DistrictExposureGeoJSONView.as_view(), name="district-geojson"),
    
    # GEE-based pixel-wise exposure calculation
    path("calculate-gee/", CalculateGEEExposureView.as_view(), name="calculate-gee-exposure"),
]
