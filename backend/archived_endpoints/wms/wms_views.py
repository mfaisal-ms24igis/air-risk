"""
ARCHIVED: Sentinel-5P WMS Views

These views were removed as redundant in favor of GEE-based endpoints.
They provided GeoServer WMS integration for Sentinel-5P data.

Removed on: December 15, 2025
Reason: Overlap with GEE tiles, GeoServer dependency not needed
"""

from datetime import date, datetime, timedelta
from django.conf import settings
from rest_framework import status, views
from rest_framework.permissions import AllowAny

from air_risk.api_response import APIResponse


class Sentinel5PWMSLayersView(views.APIView):
    """
    API endpoint for Sentinel-5P WMS layer configurations.

    Returns WMS URLs for all available Sentinel-5P Level 2 pollutant layers
    with time dimension support for historical data visualization.

    Endpoints:
        GET /api/v1/air-quality/wms/layers/
        GET /api/v1/air-quality/wms/layers/?date=2025-12-01
    """
    permission_classes = [AllowAny]

    # Sentinel-5P Level 2 product definitions
    SENTINEL5P_LAYERS = {
        "NO2": {
            "name": "no2_corrected",
            "title": "Nitrogen Dioxide (NO2)",
            "description": "Tropospheric NO2 column density from Sentinel-5P TROPOMI",
            "unit": "mol/m²",
            "product": "L2__NO2___",
            "style": "no2_style",
            "colormap": "YlOrRd",
        },
        "SO2": {
            "name": "so2_corrected",
            "title": "Sulfur Dioxide (SO2)",
            "description": "SO2 total column from Sentinel-5P TROPOMI",
            "unit": "mol/m²",
            "product": "L2__SO2___",
            "style": "so2_style",
            "colormap": "PuRd",
        },
        "CO": {
            "name": "co_corrected",
            "title": "Carbon Monoxide (CO)",
            "description": "CO total column from Sentinel-5P TROPOMI",
            "unit": "mol/m²",
            "product": "L2__CO____",
            "style": "co_style",
            "colormap": "Greys",
        },
        "O3": {
            "name": "o3_corrected",
            "title": "Ozone (O3)",
            "description": "O3 total column from Sentinel-5P TROPOMI",
            "unit": "mol/m²",
            "product": "L2__O3____",
            "style": "o3_style",
            "colormap": "Blues",
        },
        "HCHO": {
            "name": "hcho_corrected",
            "title": "Formaldehyde (HCHO)",
            "description": "HCHO tropospheric column from Sentinel-5P TROPOMI",
            "unit": "mol/m²",
            "product": "L2__HCHO__",
            "style": "hcho_style",
            "colormap": "Oranges",
        },
        "CH4": {
            "name": "ch4_corrected",
            "title": "Methane (CH4)",
            "description": "CH4 total column from Sentinel-5P TROPOMI",
            "unit": "ppb",
            "product": "L2__CH4___",
            "style": "ch4_style",
            "colormap": "Greens",
        },
        "AER_AI": {
            "name": "aerosol_index_corrected",
            "title": "UV Aerosol Index",
            "description": "Absorbing Aerosol Index from Sentinel-5P TROPOMI",
            "unit": "dimensionless",
            "product": "L2__AER_AI",
            "style": "aerosol_style",
            "colormap": "RdYlBu_r",
        },
        "CLOUD": {
            "name": "cloud_fraction",
            "title": "Cloud Fraction",
            "description": "Effective cloud fraction from Sentinel-5P TROPOMI",
            "unit": "fraction",
            "product": "L2__CLOUD_",
            "style": "cloud_style",
            "colormap": "Greys",
        },
    }

    # Pakistan bounding box
    BBOX = "60,23,78,37.5"

    def get(self, request) -> APIResponse:
        """
        Get WMS layer configurations for all Sentinel-5P pollutants.

        Query Parameters:
            date (str): Target date for TIME dimension (YYYY-MM-DD)
            pollutant (str): Filter to specific pollutant (e.g., NO2, SO2)
            format (str): Output format - png, jpeg, geotiff (default: png)

        Returns:
            List of WMS layer configurations with URLs
        """
        target_date = request.query_params.get("date")
        pollutant_filter = request.query_params.get("pollutant", "").upper()
        output_format = request.query_params.get("format", "png")

        # Validate date
        if target_date:
            try:
                datetime.strptime(target_date, "%Y-%m-%d")
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = date.today().isoformat()

        # Get GeoServer base URL from settings
        geoserver_url = getattr(settings, "GEOSERVER_URL", "http://localhost:8080/geoserver")
        workspace = getattr(settings, "GEOSERVER_WORKSPACE", "air_risk")

        # Format mapping
        format_map = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "geotiff": "image/geotiff",
            "tiff": "image/geotiff",
        }
        mime_format = format_map.get(output_format.lower(), "image/png")

        layers = []

        for code, layer_info in self.SENTINEL5P_LAYERS.items():
            # Filter by pollutant if specified
            if pollutant_filter and code != pollutant_filter:
                continue

            layer_name = f"{workspace}:{layer_info['name']}"

            # Build WMS GetMap URL
            wms_url = (
                f"{geoserver_url}/{workspace}/wms?"
                f"service=WMS&version=1.1.1&request=GetMap"
                f"&layers={layer_name}"
                f"&bbox={self.BBOX}"
                f"&width=800&height=600"
                f"&srs=EPSG:4326"
                f"&format={mime_format}"
                f"&time={target_date}"
            )

            # Build GetCapabilities URL
            capabilities_url = (
                f"{geoserver_url}/{workspace}/wms?"
                f"service=WMS&version=1.1.1&request=GetCapabilities"
            )

            # Build GetFeatureInfo URL template
            feature_info_url = (
                f"{geoserver_url}/{workspace}/wms?"
                f"service=WMS&version=1.1.1&request=GetFeatureInfo"
                f"&layers={layer_name}"
                f"&query_layers={layer_name}"
                f"&info_format=application/json"
                f"&bbox={self.BBOX}"
                f"&width=800&height=600"
                f"&srs=EPSG:4326"
                f"&x={{x}}&y={{y}}"
                f"&time={target_date}"
            )

            layers.append({
                "code": code,
                "name": layer_info["name"],
                "layer": layer_name,
                "title": layer_info["title"],
                "description": layer_info["description"],
                "unit": layer_info["unit"],
                "product": layer_info["product"],
                "colormap": layer_info["colormap"],
                "date": target_date,
                "bbox": {
                    "minx": 60.0,
                    "miny": 23.0,
                    "maxx": 78.0,
                    "maxy": 37.5,
                    "crs": "EPSG:4326",
                },
                "urls": {
                    "wms_getmap": wms_url,
                    "wms_capabilities": capabilities_url,
                    "wms_feature_info": feature_info_url,
                },
                "time_enabled": True,
            })

        # Build WMS base URL for MapLibre
        wms_base = f"{geoserver_url}/{workspace}/wms"

        return APIResponse.success(
            data={
                "geoserver_url": geoserver_url,
                "workspace": workspace,
                "date": target_date,
                "format": mime_format,
                "layers": layers,
                "usage": {
                    "maplibre": {
                        "description": "MapLibre GL JS requires raster-dem or raster sources. For WMS, use a tile URL pattern.",
                        "wms_source_example": f"""
// Add WMS as raster source (requires converting WMS to tiles)
map.addSource('s5p-wms', {{
  type: 'raster',
  tiles: [
    '{wms_base}?service=WMS&version=1.1.1&request=GetMap&layers={workspace}:s5p_no2&bbox={{bbox-epsg-3857}}&width=256&height=256&srs=EPSG:3857&format=image/png&transparent=true&time={target_date}'
  ],
  tileSize: 256
}});
map.addLayer({{
  id: 's5p-layer',
  type: 'raster',
  source: 's5p-wms',
  paint: {{ 'raster-opacity': 0.8 }}
}});""",
                        "recommendation": "For MapLibre, prefer the GEE tiles endpoint (/api/v1/air-quality/gee/tiles/) which provides direct XYZ tile URLs.",
                    },
                    "leaflet": "L.tileLayer.wms(url, {layers: layer_name, format: 'image/png', transparent: true, time: date})",
                    "openlayers": "new ol.layer.Tile({source: new ol.source.TileWMS({url, params: {LAYERS: layer_name, TIME: date}})})",
                },
            },
            message=f"Retrieved {len(layers)} Sentinel-5P WMS layers for {target_date}"
        )


class Sentinel5PTimeSeriesView(views.APIView):
    """
    Get available dates for a Sentinel-5P layer.

    Endpoints:
        GET /api/v1/air-quality/wms/timeseries/?pollutant=NO2
        GET /api/v1/air-quality/wms/timeseries/?pollutant=NO2&start=2025-11-01&end=2025-12-01
    """
    permission_classes = [AllowAny]

    def get(self, request) -> APIResponse:
        """
        Get available time steps for a pollutant layer.

        Query Parameters:
            pollutant (str): Pollutant code (required) - NO2, SO2, CO, O3, etc.
            start (str): Start date (YYYY-MM-DD)
            end (str): End date (YYYY-MM-DD)
            days (int): Number of days back from today (default: 30)
        """
        pollutant = request.query_params.get("pollutant", "").upper()

        if not pollutant:
            return APIResponse.error(
                message="pollutant parameter required (NO2, SO2, CO, O3, etc.)",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if pollutant not in Sentinel5PWMSLayersView.SENTINEL5P_LAYERS:
            return APIResponse.error(
                message=f"Unknown pollutant: {pollutant}. Available: {', '.join(Sentinel5PWMSLayersView.SENTINEL5P_LAYERS.keys())}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Parse date range
        start_date = request.query_params.get("start")
        end_date = request.query_params.get("end")
        days = int(request.query_params.get("days", 30))

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid end date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            end_dt = date.today()

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid start date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            start_dt = end_dt - timedelta(days=days)

        layer_info = Sentinel5PWMSLayersView.SENTINEL5P_LAYERS[pollutant]
        geoserver_url = getattr(settings, "GEOSERVER_URL", "http://localhost:8080/geoserver")
        workspace = getattr(settings, "GEOSERVER_WORKSPACE", "air_risk")

        # Generate date list (in production, this would query GeoServer or database)
        # For now, return expected dates based on Sentinel-5P daily revisit
        available_dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            available_dates.append(current_dt.isoformat())
            current_dt += timedelta(days=1)

        return APIResponse.success(
            data={
                "pollutant": pollutant,
                "layer": layer_info["name"],
                "title": layer_info["title"],
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "available_dates": available_dates,
                "total_dates": len(available_dates),
                "wms_time_format": "ISO8601",
                "example_time_param": f"time={available_dates[-1] if available_dates else ''}",
            },
            message=f"Found {len(available_dates)} available dates for {pollutant}"
        )