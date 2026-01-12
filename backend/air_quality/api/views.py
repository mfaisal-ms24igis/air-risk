"""
API views for air quality data (Refactored with standardized responses).

This module provides endpoints for:
- District and Province geographic data
- Population raster metadata
- Ground monitoring station data
- AQI legend/reference information

All responses follow the standard structure:
{
    "status": "success" | "error",
    "data": <GeoJSON FeatureCollection | Dict>,
    "message": <string>
}
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

from django.db import models, transaction
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.core.cache import cache
from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django_filters import rest_framework as filters

logger = logging.getLogger(__name__)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from ..models import District, Province, AirQualityStation, PollutantReading
from ..constants import Pollutant, AQI_COLORS
from .utils import APIResponse, deprecated, FileHygiene, get_aqi_color, get_aqi_category
from .serializers import (
    DistrictSerializer,
    DistrictListSerializer,
    ProvinceSerializer,
    ProvinceListSerializer,
)


# =============================================================================
# FILTERS
# =============================================================================

class DistrictFilter(filters.FilterSet):
    """
    Filter for district queries.
    
    Attributes:
        province: Filter by province name (case-insensitive)
        name: Filter by district name (partial match)
    """
    province = filters.CharFilter(lookup_expr="iexact")
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = District
        fields = ["province", "name"]


class StationFilter(filters.FilterSet):
    """
    Filter for ground station queries.
    
    Attributes:
        district: Filter by district ID
        province: Filter by province name
        is_active: Filter by active status
        source: Filter by data source (e.g., openaq)
    """
    district = filters.NumberFilter()
    province = filters.CharFilter(field_name="district__province", lookup_expr="iexact")
    is_active = filters.BooleanFilter()
    source = filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = AirQualityStation
        fields = ["district", "is_active", "source"]


# =============================================================================
# GEOGRAPHIC VIEWSETS (Primary Frontend Endpoints)
# =============================================================================

class DistrictViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Pakistan districts.
    
    Provides district boundaries and metadata for map visualization.
    
    Endpoints:
        GET /api/v1/air-quality/districts/
        GET /api/v1/air-quality/districts/{id}/
        GET /api/v1/air-quality/districts/{id}/geometry/
        GET /api/v1/air-quality/districts/provinces/
    """
    queryset = District.objects.all()
    permission_classes = [AllowAny]
    filterset_class = DistrictFilter

    def get_serializer_class(self):
        """Get serializer based on action."""
        if self.action == "list":
            return DistrictListSerializer
        return DistrictSerializer

    def list(self, request, *args, **kwargs):
        """
        List all districts with standardized response.
        
        Query Parameters:
            province (str): Filter by province name
            name (str): Filter by partial district name
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} districts"
        )

    def retrieve(self, request, *args, **kwargs):
        """Get a single district with full details."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved district: {instance.name}"
        )

    @action(detail=True, methods=["get"])
    def geometry(self, request, pk=None) -> APIResponse:
        """
        Get district geometry as GeoJSON Feature.
        
        Returns:
            APIResponse: GeoJSON Feature with district boundary
        """
        district = self.get_object()
        
        if not district.geometry:
            return APIResponse.error(
                message=f"No geometry data for district {district.name}",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        import json
        feature = {
            "type": "Feature",
            "id": district.pk,
            "geometry": json.loads(district.geometry.geojson),
            "properties": {
                "id": district.pk,
                "name": district.name,
                "province": district.province,
                "population": district.population,
                "area_km2": district.area_km2,
            }
        }
        
        return APIResponse.success(
            data=feature,
            message=f"Retrieved geometry for {district.name}"
        )

    @action(detail=False, methods=["get"])
    def provinces(self, request) -> APIResponse:
        """
        Get list of provinces with district counts.
        
        Returns:
            APIResponse: List of provinces with aggregated statistics
        """
        provinces = (
            District.objects.values("province")
            .annotate(
                district_count=models.Count("id"),
                total_population=models.Sum("population"),
                total_area=models.Sum("area_km2"),
            )
            .order_by("province")
        )

        return APIResponse.success(
            data=list(provinces),
            message=f"Retrieved {len(provinces)} provinces"
        )

    @action(detail=False, methods=["get"])
    def geojson(self, request) -> APIResponse:
        """
        Get all districts as GeoJSON FeatureCollection.
        
        Query Parameters:
            province (str): Filter by province name
        """
        province = request.query_params.get("province")
        
        queryset = self.get_queryset().exclude(geometry__isnull=True)
        if province:
            queryset = queryset.filter(province__iexact=province)
        
        import json
        features = []
        for district in queryset:
            features.append({
                "type": "Feature",
                "id": district.pk,
                "geometry": json.loads(district.geometry.geojson),
                "properties": {
                    "id": district.pk,
                    "name": district.name,
                    "province": district.province,
                    "population": district.population,
                }
            })
        
        return APIResponse.geojson(
            features=features,
            message=f"Retrieved GeoJSON for {len(features)} districts",
            properties={"province_filter": province}
        )


class ProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for Pakistan provinces.
    
    Endpoints:
        GET /api/v1/air-quality/provinces/
        GET /api/v1/air-quality/provinces/{id}/
        GET /api/v1/air-quality/provinces/{id}/geometry/
    """
    queryset = Province.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Get serializer based on action."""
        if self.action == "list":
            return ProvinceListSerializer
        return ProvinceSerializer

    def list(self, request, *args, **kwargs):
        """List all provinces."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} provinces"
        )

    def retrieve(self, request, *args, **kwargs):
        """Get a single province."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved province: {instance.name}"
        )

    @action(detail=True, methods=["get"])
    def geometry(self, request, pk=None) -> APIResponse:
        """Get province geometry as GeoJSON Feature."""
        province = self.get_object()
        
        if not province.boundary:
            return APIResponse.error(
                message=f"No boundary data for province {province.name}",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        import json
        feature = {
            "type": "Feature",
            "id": province.pk,
            "geometry": json.loads(province.boundary.geojson),
            "properties": {
                "id": province.pk,
                "name": province.name,
            }
        }
        
        return APIResponse.success(
            data=feature,
            message=f"Retrieved geometry for {province.name}"
        )

    @action(detail=False, methods=["get"])
    def geojson(self, request) -> APIResponse:
        """
        Get all provinces as GeoJSON FeatureCollection.
        
        Returns:
            GeoJSON FeatureCollection with all province boundaries.
        """
        import json
        
        provinces = Province.objects.exclude(geometry__isnull=True)
        
        features = []
        for province in provinces:
            feature = {
                "type": "Feature",
                "id": province.pk,
                "geometry": json.loads(province.geometry.geojson),
                "properties": {
                    "id": province.pk,
                    "name": province.name,
                    "population": province.population,
                    "area_km2": float(province.area_km2) if province.area_km2 else None,
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }
        
        return APIResponse.success(
            data=geojson,
            message=f"Retrieved GeoJSON for {len(features)} provinces"
        )


# =============================================================================
# POPULATION DATA ENDPOINTS
# =============================================================================

class PopulationRasterView(views.APIView):
    """
    WorldPop population raster metadata.
    
    Endpoint: GET /api/v1/air-quality/population/
    """
    permission_classes = [AllowAny]

    def get(self, request) -> APIResponse:
        """
        Get WorldPop raster metadata.
        
        Returns:
            APIResponse: Raster metadata including bounds, resolution, and statistics
        """
        try:
            import rasterio
        except ImportError:
            return APIResponse.error(
                message="Rasterio not installed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        worldpop_path = Path(settings.WORLDPOP_DATA_PATH) / "pak_pop_2025_CN_1km_R2025A_UA_v1.tif"

        if not worldpop_path.exists():
            return APIResponse.error(
                message="WorldPop raster file not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        try:
            with rasterio.open(str(worldpop_path)) as src:
                metadata: Dict[str, Any] = {
                    "filename": worldpop_path.name,
                    "crs": str(src.crs),
                    "bounds": {
                        "west": src.bounds.left,
                        "south": src.bounds.bottom,
                        "east": src.bounds.right,
                        "north": src.bounds.top,
                    },
                    "dimensions": {
                        "width": src.width,
                        "height": src.height,
                    },
                    "resolution": {
                        "x": src.res[0],
                        "y": src.res[1],
                        "unit": "degrees"
                    },
                    "nodata_value": src.nodata,
                    "data_type": str(src.dtypes[0]),
                    "description": "WorldPop 2025 UN-adjusted population density for Pakistan (1km resolution)",
                    "source": "WorldPop (www.worldpop.org)",
                    "year": 2025,
                    "units": "people per pixel",
                }

                # Calculate statistics (cached)
                cache_key = "worldpop_statistics"
                stats = cache.get(cache_key)
                
                if not stats:
                    data = src.read(1)
                    valid_data = data[data != src.nodata]
                    if len(valid_data) > 0:
                        stats = {
                            "min_population": float(valid_data.min()),
                            "max_population": float(valid_data.max()),
                            "mean_population": float(valid_data.mean()),
                            "total_population": float(valid_data.sum()),
                            "valid_pixels": int(len(valid_data)),
                        }
                        cache.set(cache_key, stats, 3600)  # Cache for 1 hour
                
                if stats:
                    metadata["statistics"] = stats

            return APIResponse.success(
                data=metadata,
                message="WorldPop raster metadata retrieved"
            )

        except Exception as e:
            return APIResponse.error(
                message=f"Failed to read raster: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PopulationDownloadView(views.APIView):
    """
    Download WorldPop raster file.
    
    DEPRECATED: Consider using tile-based access instead for large files.
    
    Endpoint: GET /api/v1/air-quality/population/download/
    """
    permission_classes = [AllowAny]

    @deprecated(
        reason="Large file download - consider using tile-based access",
        removal_version="2.0.0",
        alternative="Tile-based COG access"
    )
    def get(self, request):
        """Download the WorldPop raster file."""
        from django.http import FileResponse

        worldpop_path = Path(settings.WORLDPOP_DATA_PATH) / "pak_pop_2025_CN_1km_R2025A_UA_v1.tif"

        if not worldpop_path.exists():
            return APIResponse.error(
                message="WorldPop raster file not found",
                status_code=status.HTTP_404_NOT_FOUND
            )

        try:
            response = FileResponse(
                open(worldpop_path, 'rb'),
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{worldpop_path.name}"'
            return response

        except Exception as e:
            return APIResponse.error(
                message=f"Failed to serve file: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# =============================================================================
# AQI REFERENCE DATA
# =============================================================================

class AQILegendView(views.APIView):
    """
    AQI color scale and category reference.
    
    Endpoint: GET /api/v1/air-quality/legend/
    """
    permission_classes = [AllowAny]

    def get(self, request) -> APIResponse:
        """
        Get AQI legend with colors and health messages.
        
        Returns:
            APIResponse: AQI categories with colors and health guidance
        """
        legend = [
            {
                "category": "Good",
                "range": {"min": 0, "max": 50},
                "color": "#00E400",
                "description": "Air quality is satisfactory, and air pollution poses little or no risk.",
                "health_message": "None"
            },
            {
                "category": "Moderate",
                "range": {"min": 51, "max": 100},
                "color": "#FFFF00",
                "description": "Air quality is acceptable. However, there may be a risk for some people.",
                "health_message": "Unusually sensitive people should consider reducing prolonged outdoor exertion."
            },
            {
                "category": "Unhealthy for Sensitive Groups",
                "short_name": "USG",
                "range": {"min": 101, "max": 150},
                "color": "#FF7E00",
                "description": "Members of sensitive groups may experience health effects.",
                "health_message": "People with respiratory or heart disease, the elderly, and children should limit prolonged outdoor exertion."
            },
            {
                "category": "Unhealthy",
                "range": {"min": 151, "max": 200},
                "color": "#FF0000",
                "description": "Everyone may begin to experience health effects.",
                "health_message": "People with respiratory or heart disease, the elderly, and children should avoid prolonged outdoor exertion. Everyone else should limit prolonged outdoor exertion."
            },
            {
                "category": "Very Unhealthy",
                "range": {"min": 201, "max": 300},
                "color": "#8F3F97",
                "description": "Health alert: everyone may experience more serious health effects.",
                "health_message": "People with respiratory or heart disease, the elderly, and children should avoid all outdoor exertion. Everyone else should limit outdoor exertion."
            },
            {
                "category": "Hazardous",
                "range": {"min": 301, "max": 500},
                "color": "#7E0023",
                "description": "Health emergency: the entire population is more likely to be affected.",
                "health_message": "Everyone should avoid all outdoor exertion."
            },
        ]

        pollutants = [
            {
                "code": "PM25",
                "name": "PM2.5",
                "full_name": "Fine Particulate Matter",
                "unit": "μg/m³",
                "description": "Particles smaller than 2.5 micrometers in diameter"
            },
            {
                "code": "PM10",
                "name": "PM10",
                "full_name": "Coarse Particulate Matter",
                "unit": "μg/m³",
                "description": "Particles smaller than 10 micrometers in diameter"
            },
            {
                "code": "NO2",
                "name": "NO₂",
                "full_name": "Nitrogen Dioxide",
                "unit": "ppb",
                "description": "Gas produced by combustion, especially from vehicles"
            },
            {
                "code": "SO2",
                "name": "SO₂",
                "full_name": "Sulfur Dioxide",
                "unit": "ppb",
                "description": "Gas produced by burning fossil fuels containing sulfur"
            },
            {
                "code": "O3",
                "name": "O₃",
                "full_name": "Ozone",
                "unit": "ppb",
                "description": "Ground-level ozone formed by photochemical reactions"
            },
            {
                "code": "CO",
                "name": "CO",
                "full_name": "Carbon Monoxide",
                "unit": "ppm",
                "description": "Colorless gas produced by incomplete combustion"
            },
        ]

        return APIResponse.success(
            data={
                "categories": legend,
                "pollutants": pollutants,
                "source": "US EPA Air Quality Index (AQI)",
            },
            message="AQI legend retrieved"
        )


# =============================================================================
# GROUND STATION ENDPOINTS
# =============================================================================

class GroundStationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for ground monitoring stations.
    
    Provides station locations and latest readings for map display.
    
    Endpoints:
        GET /api/v1/air-quality/stations/
        GET /api/v1/air-quality/stations/{id}/
        GET /api/v1/air-quality/stations/geojson/
        GET /api/v1/air-quality/stations/{id}/readings/
    """
    queryset = AirQualityStation.objects.select_related("district").filter(is_active=True)
    serializer_class = None  # We use custom responses, but need this for swagger
    permission_classes = [AllowAny]
    filterset_class = StationFilter

    def get_serializer_class(self):
        """Return None - we use custom APIResponse instead of serializers."""
        if getattr(self, 'swagger_fake_view', False):
            # Return a dummy serializer for swagger schema generation
            from rest_framework import serializers
            class GroundStationDummySerializer(serializers.Serializer):
                class Meta:
                    ref_name = 'GroundStationResponse'
            return GroundStationDummySerializer
        return None

    def list(self, request, *args, **kwargs):
        """List all active stations."""
        queryset = self.filter_queryset(self.get_queryset())
        
        stations_data = []
        for station in queryset:
            stations_data.append({
                "id": station.pk,
                "name": station.name,
                "openaq_location_id": station.openaq_location_id,
                "data_source": station.data_source,
                "district": station.district.name if station.district else None,
                "province": station.district.province if station.district else None,
                "location": {
                    "lat": station.location.y if station.location else station.latitude,
                    "lng": station.location.x if station.location else station.longitude,
                },
                "is_active": station.is_active,
                "available_parameters": station.available_parameters,
            })
        
        return APIResponse.success(
            data=stations_data,
            message=f"Retrieved {len(stations_data)} stations"
        )

    def retrieve(self, request, *args, **kwargs):
        """Get a single station with latest reading. Fetches from OpenAQ if data is missing or stale."""
        station = self.get_object()
        force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
        
        # Get latest readings grouped by parameter
        latest_readings = (
            station.readings
            .order_by('parameter', '-timestamp')
            .distinct('parameter')
        )
        
        # Check if we need to fetch from OpenAQ
        should_fetch = force_refresh or not latest_readings.exists()
        
        # If we have readings, check if they're stale (> 24 hours old)
        if not should_fetch and latest_readings.exists():
            most_recent = latest_readings.first().timestamp
            if timezone.now() - most_recent > timedelta(hours=24):
                should_fetch = True
        
        # Fetch from OpenAQ if needed
        if should_fetch and station.openaq_location_id:
            try:
                self._fetch_and_save_latest_readings(station)
                # Re-query after fetching
                latest_readings = (
                    station.readings
                    .order_by('parameter', '-timestamp')
                    .distinct('parameter')
                )
            except Exception as e:
                logger.error(f"Failed to fetch OpenAQ data for station {station.pk}: {e}")
                # Continue with cached data if available
        
        station_data: Dict[str, Any] = {
            "id": station.pk,
            "name": station.name,
            "data_source": station.data_source,
            "openaq_location_id": station.openaq_location_id,
            "district": {
                "id": station.district.pk,
                "name": station.district.name,
                "province": station.district.province,
            } if station.district else None,
            "location": {
                "lat": station.location.y if station.location else station.latitude,
                "lng": station.location.x if station.location else station.longitude,
            },
            "is_active": station.is_active,
            "available_parameters": station.available_parameters,
            "latest_readings": {},
            "last_updated": None,
            "openaq_checked": should_fetch,  # Indicates if we tried to fetch from OpenAQ
        }
        
        for reading in latest_readings:
            station_data["latest_readings"][reading.parameter] = {
                "timestamp": reading.timestamp.isoformat(),
                "value": reading.value,
                "value_normalized": reading.value_normalized,
                "unit": reading.unit,
            }
            # Track the most recent timestamp
            if station_data["last_updated"] is None or reading.timestamp.isoformat() > station_data["last_updated"]:
                station_data["last_updated"] = reading.timestamp.isoformat()
        
        return APIResponse.success(
            data=station_data,
            message=f"Retrieved station: {station.name}"
        )
    
    def _fetch_and_save_latest_readings(self, station):
        """Fetch latest readings from OpenAQ and save to database. Exact copy of fetch_recent_readings logic."""
        from air_quality.services import get_openaq_client
        from air_quality.models import PollutantReading
        from datetime import datetime as dt
        
        client = get_openaq_client()
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        try:
            # Get sensors for this location
            sensors_response = client.client.locations.sensors(station.openaq_location_id)
            
            if not sensors_response.results:
                logger.info(f"No sensors found for station {station.pk}")
                return
            
            sensor_ids = [sensor.id for sensor in sensors_response.results]
            logger.info(f"Found {len(sensor_ids)} sensors for station {station.pk}")
            
            # Fetch measurements for each sensor
            readings = []
            for sensor_id in sensor_ids:
                try:
                    measurements = client.client.measurements.list(
                        sensors_id=sensor_id,
                        datetime_from=f"{start_date.isoformat()}T00:00:00Z",
                        datetime_to=f"{end_date.isoformat()}T23:59:59Z",
                        limit=1000
                    )

                    for m in measurements.results:
                        # Handle parameter as object with name attribute
                        param = getattr(m.parameter, 'name', '').upper()
                        unit = getattr(m.parameter, 'units', 'µg/m³')
                        
                        if param == "PM2.5":
                            param = "PM25"

                        # Datetime is in period.datetime_from.utc
                        try:
                            timestamp = m.period.datetime_from.utc
                            if isinstance(timestamp, str):
                                timestamp = dt.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except Exception:
                            continue

                        if timestamp and m.value is not None:
                            readings.append({
                                "timestamp": timestamp,
                                "parameter": param,
                                "value": m.value,
                                "unit": unit or "µg/m³",
                            })
                except Exception as sensor_error:
                    logger.debug(f"Error fetching sensor {sensor_id}: {sensor_error}")
                    continue
            
            logger.info(f"Fetched {len(readings)} total readings for station {station.pk}")
            
            # Save readings
            if readings:
                readings_to_create = []
                for reading_data in readings:
                    reading = PollutantReading(
                        station=station,
                        timestamp=reading_data['timestamp'],
                        parameter=reading_data['parameter'],
                        value=reading_data['value'],
                        unit=reading_data['unit'],
                        value_normalized=reading_data['value']
                    )
                    readings_to_create.append(reading)
                
                with transaction.atomic():
                    PollutantReading.objects.bulk_create(
                        readings_to_create,
                        ignore_conflicts=True
                    )
                    logger.info(f"Saved {len(readings_to_create)} readings for station {station.pk}")
                    
                    station.last_reading_at = timezone.now()
                    station.save(update_fields=['last_reading_at'])
            else:
                logger.info(f"No readings fetched from OpenAQ for station {station.pk}")
        
        except Exception as e:
            logger.error(f"Error fetching OpenAQ data: {e}")
            raise

    @action(detail=False, methods=["get"])
    def geojson(self, request) -> APIResponse:
        """
        Get stations as GeoJSON FeatureCollection with latest readings.
        
        Query Parameters:
            has_data (bool): Only include stations with recent data (default: true)
            days (int): Days to look back for readings (default: 30)
        """
        has_data = request.query_params.get("has_data", "true").lower() == "true"
        days = int(request.query_params.get("days", 30))
        
        # Cache key - with graceful fallback if Redis unavailable
        cache_key = f"stations_geojson_{has_data}_{days}"
        try:
            cached = cache.get(cache_key)
            if cached:
                return APIResponse.geojson(
                    features=cached["features"],
                    message="Stations GeoJSON (cached)",
                    properties=cached.get("properties", {})
                )
        except Exception:
            # Redis unavailable, continue without cache
            pass
        
        queryset = self.get_queryset()
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Filter to stations with recent data if requested
        if has_data:
            station_ids = (
                PollutantReading.objects
                .filter(timestamp__gte=cutoff_date)
                .values_list("station_id", flat=True)
                .distinct()
            )
            queryset = queryset.filter(pk__in=station_ids)
        
        # Optimized: Return lightweight GeoJSON (no embedded readings)
        # Data will be fetched on-demand when user clicks a station
        
        features = []
        for station in queryset:
            if not station.location:
                continue
                
            properties: Dict[str, Any] = {
                "id": station.pk,
                "name": station.name,
                "data_source": station.data_source,
                "district": station.district.name if station.district else None,
                "province": station.district.province if station.district else None,
                "is_active": station.is_active,
            }
            
            features.append({
                "type": "Feature",
                "id": station.pk,
                "geometry": {
                    "type": "Point",
                    "coordinates": [station.location.x, station.location.y]
                },
                "properties": properties,
            })
        
        # Cache for 1 hour (static data)
        try:
            cache.set(cache_key, {"features": features, "properties": {"days": days}}, 3600)
        except Exception:
            pass  # Redis unavailable, skip caching
        
        return APIResponse.geojson(
            features=features,
            message=f"Retrieved {len(features)} stations as GeoJSON (Lightweight)",
            properties={"days": days, "has_data_filter": has_data}
        )

    @action(detail=True, methods=["get"])
    def readings(self, request, pk=None) -> APIResponse:
        """
        Get recent readings for a station.
        
        Query Parameters:
            days (int): Days of history (default: 7)
            limit (int): Maximum readings (default: 100)
        """
        station = self.get_object()
        days = int(request.query_params.get("days", 7))
        # Tiered access logic
        is_premium = request.user.groups.filter(name='Premium').exists()
        max_limit = 40 if is_premium else 10
        
        limit = int(request.query_params.get("limit", 100))
        # Enforce tiered limit
        limit = min(limit, max_limit)
        
        start_date = timezone.now() - timedelta(days=days)
        readings = (
            station.readings
            .filter(timestamp__gte=start_date)
            .order_by("-timestamp")[:limit]
        )
        
        readings_data = []
        for r in readings:
            readings_data.append({
                "timestamp": r.timestamp.isoformat(),
                "parameter": r.parameter,
                "value": r.value,
                "value_normalized": r.value_normalized,
                "unit": r.unit,
            })
        
        return APIResponse.success(
            data={
                "station_id": station.pk,
                "station_name": station.name,
                "period": {
                    "start": start_date.isoformat(),
                    "end": timezone.now().isoformat(),
                    "days": days,
                },
                "readings": readings_data,
            },
            message=f"Retrieved {len(readings_data)} readings for {station.name}"
        )

    @action(detail=True, methods=["get"])
    def timeseries(self, request, pk=None) -> APIResponse:
        """
        Get time series data for a station with aggregation support.
        
        Optimized for chart display with configurable aggregation intervals.
        
        Query Parameters:
            parameter (str): Pollutant (pm25, no2, etc.) - required
            start (str): Start date YYYY-MM-DD (default: 30 days ago)
            end (str): End date YYYY-MM-DD (default: today)
            interval (str): Aggregation interval - hourly, daily, weekly (default: daily)
        
        Returns time series data suitable for charting libraries.
        """
        from django.db.models import Avg, Max, Min, Count
        from django.db.models.functions import TruncHour, TruncDay, TruncWeek
        
        station = self.get_object()
        
        # Get parameter
        parameter = request.query_params.get("parameter", "").upper()
        if not parameter:
            return APIResponse.error(
                message="parameter required (e.g., PM25, NO2, CO, SO2, O3)",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse dates
        end_date = request.query_params.get("end")
        start_date = request.query_params.get("start")
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = timezone.make_aware(end_dt.replace(hour=23, minute=59, second=59))
            except ValueError:
                return APIResponse.error(
                    message="Invalid end date. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            end_dt = timezone.now()
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                start_dt = timezone.make_aware(start_dt)
            except ValueError:
                return APIResponse.error(
                    message="Invalid start date. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            start_dt = end_dt - timedelta(days=30)
        
        # Get aggregation interval
        interval = request.query_params.get("interval", "daily").lower()
        
        if interval == "hourly":
            trunc_func = TruncHour("timestamp")
            interval_label = "hour"
        elif interval == "weekly":
            trunc_func = TruncWeek("timestamp")
            interval_label = "week"
        else:  # daily
            trunc_func = TruncDay("timestamp")
            interval_label = "day"
        
        # Query with aggregation
        readings = (
            station.readings
            .filter(
                parameter=parameter,
                timestamp__gte=start_dt,
                timestamp__lte=end_dt,
                is_valid=True,
            )
            .annotate(period=trunc_func)
            .values("period")
            .annotate(
                avg_value=Avg("value_normalized"),
                max_value=Max("value_normalized"),
                min_value=Min("value_normalized"),
                count=Count("id"),
            )
            .order_by("period")
        )
        
        # Format for chart display
        timeseries_data = []
        for r in readings:
            if r["period"] and r["avg_value"] is not None:
                timeseries_data.append({
                    "timestamp": r["period"].isoformat(),
                    "avg": round(r["avg_value"], 2) if r["avg_value"] else None,
                    "max": round(r["max_value"], 2) if r["max_value"] else None,
                    "min": round(r["min_value"], 2) if r["min_value"] else None,
                    "count": r["count"],
                })
        
        # Get unit for the parameter
        unit = "µg/m³"  # Default
        first_reading = station.readings.filter(parameter=parameter).first()
        if first_reading:
            unit = first_reading.unit_normalized or first_reading.unit
        
        return APIResponse.success(
            data={
                "station": {
                    "id": station.pk,
                    "name": station.name,
                    "district": station.district.name if station.district else None,
                },
                "parameter": parameter,
                "unit": unit,
                "interval": interval_label,
                "period": {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                },
                "data_points": len(timeseries_data),
                "timeseries": timeseries_data,
            },
            message=f"Retrieved {len(timeseries_data)} {interval_label}ly data points for {parameter}"
        )

    @action(detail=False, methods=["get"])
    def latest(self, request) -> APIResponse:
        """
        Get latest readings from all stations.
        
        Query Parameters:
            parameter (str): Filter by pollutant (pm25, no2, etc.)
            province (str): Filter by province name
            limit (int): Maximum stations (default: 50)
        
        Returns latest reading for each station, sorted by timestamp.
        """
        parameter = request.query_params.get("parameter", "").upper()
        province = request.query_params.get("province", "").upper()
        limit = int(request.query_params.get("limit", 50))
        
        # Base queryset
        queryset = self.get_queryset()
        
        # Filter by province
        if province:
            queryset = queryset.filter(district__province__iexact=province)
        
        stations_data = []
        for station in queryset[:limit]:
            # Get latest reading for this station
            reading_qs = station.readings.filter(is_valid=True)
            if parameter:
                reading_qs = reading_qs.filter(parameter=parameter)
            
            latest = reading_qs.order_by("-timestamp").first()
            
            if latest:
                stations_data.append({
                    "station_id": station.pk,
                    "station_name": station.name,
                    "district": station.district.name if station.district else None,
                    "province": station.district.province if station.district else None,
                    "location": {
                        "lat": station.latitude,
                        "lng": station.longitude,
                    },
                    "reading": {
                        "timestamp": latest.timestamp.isoformat(),
                        "parameter": latest.parameter,
                        "value": latest.value,
                        "value_normalized": latest.value_normalized,
                        "unit": latest.unit,
                    },
                })
        
        # Sort by timestamp descending
        stations_data.sort(key=lambda x: x["reading"]["timestamp"], reverse=True)
        
        return APIResponse.success(
            data={
                "count": len(stations_data),
                "filter": {
                    "parameter": parameter or "all",
                    "province": province or "all",
                },
                "stations": stations_data,
            },
            message=f"Retrieved latest readings from {len(stations_data)} stations"
        )

    @action(detail=False, methods=["get"])
    def nearby(self, request) -> APIResponse:
        """
        Find stations near a point.
        
        Query Parameters:
            lat (float): Latitude (required)
            lon (float): Longitude (required)
            radius (float): Search radius in km (default: 50)
        """
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        radius_km = float(request.query_params.get("radius", 50))

        if not lat or not lon:
            return APIResponse.error(
                message="lat and lon parameters required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        point = Point(float(lon), float(lat), srid=4326)

        # Filter by distance (radius in meters)
        from django.contrib.gis.db.models.functions import Distance
        
        stations = (
            self.get_queryset()
            .annotate(distance=Distance("location", point))
            .filter(distance__lte=radius_km * 1000)
            .order_by("distance")[:10]
        )

        stations_data = []
        for station in stations:
            stations_data.append({
                "id": station.pk,
                "name": station.name,
                "distance_km": round(station.distance.m / 1000, 2),
                "district": station.district.name if station.district else None,
                "location": {
                    "lat": station.location.y,
                    "lng": station.location.x,
                },
            })

        return APIResponse.success(
            data={
                "center": {"lat": float(lat), "lng": float(lon)},
                "radius_km": radius_km,
                "stations": stations_data,
            },
            message=f"Found {len(stations_data)} stations within {radius_km}km"
        )


# =============================================================================
# =============================================================================
# GOOGLE EARTH ENGINE TILE VIEWS
# =============================================================================
# GOOGLE EARTH ENGINE TILE VIEWS
# =============================================================================

class GEESentinel5PLayersView(views.APIView):
    """
    Get available Sentinel-5P tile layers from Google Earth Engine.
    
    Endpoints:
        GET /api/v1/air-quality/gee/layers/
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Get GEE Sentinel-5P layer configurations",
        operation_description="Returns all available Sentinel-5P pollutant layers with visualization parameters.",
        tags=["Sentinel-5P GEE Tiles"],
    )
    def get(self, request) -> APIResponse:
        """
        Get all available GEE Sentinel-5P tile layer configurations.
        """
        try:
            from ..services.gee_tiles import get_gee_tile_service
            
            service = get_gee_tile_service()
            layers = service.get_all_layers()
            
            return APIResponse.success(
                data={
                    "source": "Google Earth Engine",
                    "satellite": "Sentinel-5P TROPOMI",
                    "layers": layers,
                    "total": len(layers),
                },
                message=f"Retrieved {len(layers)} Sentinel-5P layers from GEE"
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to get GEE layers: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GEESentinel5PTilesView(views.APIView):
    """
    Get GEE tile URL for Sentinel-5P pollutant visualization with date selection.
    
    This endpoint generates tile URLs from Google Earth Engine that can be used
    directly in web mapping libraries like Leaflet or OpenLayers.
    
    Endpoints:
        GET /api/v1/air-quality/gee/tiles/?pollutant=NO2&date=2025-01-15
        GET /api/v1/air-quality/gee/tiles/?pollutant=SO2&date=2025-01-10&composite=3
    """
    permission_classes = [AllowAny]
    
    # Pakistan bounding box
    PAKISTAN_BBOX = {
        'west': 60.0,
        'south': 23.0,
        'east': 78.0,
        'north': 37.5,
    }
    
    @swagger_auto_schema(
        operation_summary="Get GEE tile URL for Sentinel-5P",
        operation_description="Generate tile URL with date selection for MapLibre/Leaflet/OpenLayers.",
        tags=["Sentinel-5P GEE Tiles"],
        manual_parameters=[
            openapi.Parameter('pollutant', openapi.IN_QUERY, description="Pollutant code (NO2, SO2, CO, O3, HCHO, CH4, AER_AI, CLOUD)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('date', openapi.IN_QUERY, description="Date in YYYY-MM-DD format", type=openapi.TYPE_STRING),
            openapi.Parameter('composite', openapi.IN_QUERY, description="Days for composite (1-30)", type=openapi.TYPE_INTEGER),
            openapi.Parameter('bbox', openapi.IN_QUERY, description="Bounding box as west,south,east,north", type=openapi.TYPE_STRING),
        ],
    )
    def get(self, request) -> APIResponse:
        """
        Get GEE tile URL for a specific pollutant and date.
        
        Query Parameters:
            pollutant (str): Required - Pollutant code (NO2, SO2, CO, O3, HCHO, CH4, AER_AI, CLOUD)
            date (str): Date in YYYY-MM-DD format (defaults to yesterday)
            composite (int): Days for composite (1=single day, 3=3-day mean, etc.) default=1
            bbox (str): Optional bounding box as "west,south,east,north"
        
        Returns:
            Tile URL and layer configuration for use in mapping libraries.
        """
        try:
            from ..services.gee_tiles import get_gee_tile_service, S5P_TILE_CONFIGS
            
            # Get and validate pollutant
            pollutant = request.query_params.get("pollutant", "").upper()
            
            if not pollutant:
                return APIResponse.error(
                    message=f"pollutant parameter required. Available: {', '.join(S5P_TILE_CONFIGS.keys())}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if pollutant not in S5P_TILE_CONFIGS:
                return APIResponse.error(
                    message=f"Unknown pollutant: {pollutant}. Available: {', '.join(S5P_TILE_CONFIGS.keys())}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get date parameter (default to yesterday for data availability)
            date_param = request.query_params.get("date")
            if date_param:
                try:
                    target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
                except ValueError:
                    return APIResponse.error(
                        message="Invalid date format. Use YYYY-MM-DD",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Default to yesterday (more likely to have data than today)
                target_date = (datetime.now() - timedelta(days=1)).date()
            
            # Get composite days (default to 7 for better coverage)
            try:
                composite_days = int(request.query_params.get("composite", 7))
                if composite_days < 1 or composite_days > 30:
                    composite_days = 7
            except ValueError:
                composite_days = 7
            
            # Parse optional bbox
            bbox = None
            bbox_param = request.query_params.get("bbox")
            if bbox_param:
                try:
                    parts = [float(x) for x in bbox_param.split(",")]
                    if len(parts) == 4:
                        bbox = {
                            'west': parts[0],
                            'south': parts[1],
                            'east': parts[2],
                            'north': parts[3],
                        }
                except (ValueError, IndexError):
                    pass
            
            # If no bbox provided, use Pakistan bbox
            if not bbox:
                    # Allow clipping to province/district AOI if provided
                    province_param = request.query_params.get('province')
                    district_param = request.query_params.get('district')
                    aoi_geojson = None
                    try:
                        if district_param:
                            district_obj = District.objects.get(pk=int(district_param)) if district_param.isdigit() else District.objects.get(name__iexact=district_param)
                            from django.contrib.gis.geos import mapping
                            aoi_geojson = mapping(district_obj.geometry)
                        elif province_param:
                            province_obj = Province.objects.get(name__iexact=province_param)
                            from django.contrib.gis.geos import mapping
                            aoi_geojson = mapping(province_obj.geometry)
                    except Exception:
                        aoi_geojson = None

                    if aoi_geojson:
                        bbox = None
                    else:
                        bbox = self.PAKISTAN_BBOX
            
            # Get tile URL from GEE
            service = get_gee_tile_service()
            result = service.get_tile_url(
                pollutant=pollutant,
                target_date=target_date,
                days_composite=composite_days,
                bbox=bbox,
                aoi_geojson=aoi_geojson if 'aoi_geojson' in locals() else None,
            )
            
            if not result.get("success"):
                return APIResponse.error(
                    message=result.get("error", "Failed to generate tile URL"),
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return APIResponse.success(
                data=result,
                message=f"Generated GEE tile URL for {pollutant} on {target_date}"
            )
            
        except ImportError as e:
            return APIResponse.error(
                message=f"GEE service not available: {str(e)}",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Error generating tile URL: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GEESentinel5PDatesView(views.APIView):
    """
    Get available dates for Sentinel-5P pollutant data from Google Earth Engine.
    
    Endpoints:
        GET /api/v1/air-quality/gee/dates/?pollutant=NO2
        GET /api/v1/air-quality/gee/dates/?pollutant=NO2&days=60
        GET /api/v1/air-quality/gee/dates/?pollutant=SO2&start=2025-01-01&end=2025-01-31
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Get available dates for Sentinel-5P in GEE",
        operation_description="Query available dates with imagery for a pollutant.",
        tags=["Sentinel-5P GEE Tiles"],
        manual_parameters=[
            openapi.Parameter('pollutant', openapi.IN_QUERY, description="Pollutant code (NO2, SO2, CO, O3, etc.)", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('start', openapi.IN_QUERY, description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('end', openapi.IN_QUERY, description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('days', openapi.IN_QUERY, description="Days back from end date (default: 30)", type=openapi.TYPE_INTEGER),
        ],
    )
    def get(self, request) -> APIResponse:
        """
        Get available dates for a pollutant from GEE.
        
        Query Parameters:
            pollutant (str): Required - Pollutant code (NO2, SO2, CO, O3, etc.)
            start (str): Start date (YYYY-MM-DD) - optional
            end (str): End date (YYYY-MM-DD) - optional, defaults to today
            days (int): Number of days back from end_date (default: 30)
        
        Returns:
            List of available dates with imagery in GEE.
        """
        try:
            from ..services.gee_tiles import get_gee_tile_service, S5P_TILE_CONFIGS
            
            # Get and validate pollutant
            pollutant = request.query_params.get("pollutant", "").upper()
            
            if not pollutant:
                return APIResponse.error(
                    message=f"pollutant parameter required. Available: {', '.join(S5P_TILE_CONFIGS.keys())}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if pollutant not in S5P_TILE_CONFIGS:
                return APIResponse.error(
                    message=f"Unknown pollutant: {pollutant}. Available: {', '.join(S5P_TILE_CONFIGS.keys())}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Parse dates
            start_date = request.query_params.get("start")
            end_date = request.query_params.get("end")
            days = int(request.query_params.get("days", 365))
            
            # Validate start date
            if start_date:
                try:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    return APIResponse.error(
                        message="Invalid start date format. Use YYYY-MM-DD",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate end date
            if end_date:
                try:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    return APIResponse.error(
                        message="Invalid end date format. Use YYYY-MM-DD",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                end_date = date.today()
            
            if start_date and start_date > end_date:
                return APIResponse.error(
                    message="Start date cannot be after end date",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if not start_date:
                start_date = end_date - timedelta(days=days)
            
            service = get_gee_tile_service()
            result = service.get_available_dates(pollutant, start_date, end_date)
            
            if not result.get("success"):
                return APIResponse.error(
                    message=result.get("error", "Unknown error querying GEE dates"),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            dates_list = result.get("available_dates", [])
            # Sort dates descending (latest first)
            dates_list.sort(reverse=True)
            
            latest_date = dates_list[0] if dates_list else None
            
            response_data = {
                "pollutant": pollutant,
                "available_dates": dates_list,
                "latest_date": latest_date,
                "date_range": result.get("date_range"),
                "count": len(dates_list)
            }
            
            return APIResponse.success(
                data=response_data,
                message=f"Found {len(dates_list)} dates with {pollutant} imagery"
            )
            
        except Exception as e:
            return APIResponse.error(
                message=f"Error querying dates: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GEESentinel5PValueView(views.APIView):
        """
        Get value of a GEE pollutant at a single point (lon/lat).
        Endpoint: GET /api/v1/air-quality/gee/value/?pollutant=NO2&date=YYYY-MM-DD&lon=69.3&lat=30.4
        """
        permission_classes = [AllowAny]

        @swagger_auto_schema(
            operation_summary="Get pollutant value at point",
            operation_description="Sample the GEE image at a lat/lon point and return the value",
            tags=["Sentinel-5P GEE Tiles"],
            manual_parameters=[
                openapi.Parameter('pollutant', openapi.IN_QUERY, description="Pollutant code (NO2, SO2, ...)", type=openapi.TYPE_STRING, required=True),
                openapi.Parameter('date', openapi.IN_QUERY, description="Date YYYY-MM-DD", type=openapi.TYPE_STRING, required=True),
                openapi.Parameter('lon', openapi.IN_QUERY, description="Longitude (decimal)", type=openapi.TYPE_NUMBER, required=True),
                openapi.Parameter('lat', openapi.IN_QUERY, description="Latitude (decimal)", type=openapi.TYPE_NUMBER, required=True),
                openapi.Parameter('composite', openapi.IN_QUERY, description="Composite days (optional)", type=openapi.TYPE_INTEGER),
            ],
        )
        def get(self, request) -> APIResponse:
            try:
                from ..services.gee_tiles import get_gee_tile_service
                pollutant = request.query_params.get('pollutant', '').upper()
                date_param = request.query_params.get('date')
                lon = request.query_params.get('lon')
                lat = request.query_params.get('lat')
                composite = int(request.query_params.get('composite', 1))

                if not pollutant or not date_param or lon is None or lat is None:
                    return APIResponse.error(message='pollutant, date, lon, lat are required', status_code=status.HTTP_400_BAD_REQUEST)
                try:
                    lon_f = float(lon)
                    lat_f = float(lat)
                except ValueError:
                    return APIResponse.error(message='lon and lat must be valid numbers', status_code=status.HTTP_400_BAD_REQUEST)

                service = get_gee_tile_service()
                result = service.get_value_at_point(pollutant=pollutant, target_date=date_param, lon=lon_f, lat=lat_f, days_composite=composite)

                if not result.get('success'):
                    return APIResponse.error(message=result.get('error', 'Failed to sample point'), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

                return APIResponse.success(data=result, message=f"Sampled {pollutant} at {lon},{lat} for {date_param}")
            except Exception as e:
                return APIResponse.error(message=f'Error sampling point: {e}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
