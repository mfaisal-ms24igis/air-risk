"""
Serializers for air quality API.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from ..models import District, GroundStation, GroundReading, PollutantRaster, Province
from ..constants import AQI_COLORS


class DistrictSerializer(GeoFeatureModelSerializer):
    """Serializer for District model with GeoJSON output."""

    class Meta:
        model = District
        geo_field = "geometry"
        fields = [
            "id",
            "name",
            "province",
            "population",
            "area_km2",
        ]


class DistrictListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for district listing (no geometry)."""

    class Meta:
        model = District
        fields = [
            "id",
            "name",
            "province",
            "population",
            "area_km2",
        ]


class ProvinceSerializer(GeoFeatureModelSerializer):
    """Serializer for Province model with GeoJSON output."""

    class Meta:
        model = Province
        geo_field = "geometry"
        fields = [
            "id",
            "name",
            "population",
            "area_km2",
        ]


class ProvinceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for province listing (no geometry)."""

    class Meta:
        model = Province
        fields = [
            "id",
            "name",
            "population",
            "area_km2",
        ]


class GroundStationSerializer(GeoFeatureModelSerializer):
    """Serializer for GroundStation model with GeoJSON output."""

    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = GroundStation
        geo_field = "location"
        fields = [
            "id",
            "openaq_id",
            "name",
            "city",
            "country",
            "district",
            "district_name",
            "available_parameters",
            "is_active",
            "last_updated",
        ]


class GroundStationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for station listing."""

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    district_name = serializers.CharField(source="district.name", read_only=True)

    class Meta:
        model = GroundStation
        fields = [
            "id",
            "openaq_id",
            "name",
            "city",
            "latitude",
            "longitude",
            "district_name",
            "available_parameters",
            "is_active",
        ]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None


class GroundReadingSerializer(serializers.ModelSerializer):
    """Serializer for ground readings."""

    station_name = serializers.CharField(source="station.name", read_only=True)

    class Meta:
        model = GroundReading
        fields = [
            "id",
            "station",
            "station_name",
            "timestamp",
            "no2",
            "so2",
            "pm25",
            "co",
            "o3",
        ]


class GroundReadingDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for ground readings with calculated AQI."""

    station = GroundStationListSerializer(read_only=True)
    aqi_values = serializers.SerializerMethodField()

    class Meta:
        model = GroundReading
        fields = [
            "id",
            "station",
            "timestamp",
            "no2",
            "so2",
            "pm25",
            "co",
            "o3",
            "aqi_values",
            "raw_data",
        ]

    def get_aqi_values(self, obj):
        """Calculate AQI for each pollutant."""
        from ..constants import calculate_aqi

        result = {}
        for pollutant in ["no2", "so2", "pm25", "co", "o3"]:
            value = getattr(obj, pollutant)
            if value is not None:
                aqi = calculate_aqi(pollutant.upper(), value)
                result[pollutant] = {
                    "concentration": value,
                    "aqi": aqi,
                    "category": get_aqi_category(aqi),
                    "color": get_aqi_color(aqi),
                }
        return result


class PollutantRasterSerializer(serializers.ModelSerializer):
    """Serializer for pollutant raster metadata."""

    has_raw = serializers.SerializerMethodField()
    has_corrected = serializers.SerializerMethodField()
    wms_url = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = PollutantRaster
        fields = [
            "id",
            "pollutant",
            "date",
            "status",
            "has_raw",
            "has_corrected",
            "wms_url",
            "stats",
            "created_at",
        ]

    def get_has_raw(self, obj):
        return bool(obj.raw_path)

    def get_has_corrected(self, obj):
        return bool(obj.corrected_path)

    def get_wms_url(self, obj):
        if obj.is_processed:
            from django.conf import settings

            return (
                f"{settings.GEOSERVER_URL}/{settings.GEOSERVER_WORKSPACE}/wms?"
                f"service=WMS&version=1.1.1&request=GetMap"
                f"&layers={settings.GEOSERVER_WORKSPACE}:{obj.pollutant.lower()}_corrected"
                f"&time={obj.date.isoformat()}"
            )
        return None

    def get_stats(self, obj):
        """Return statistics for the raster."""
        if obj.min_value is not None and obj.max_value is not None and obj.mean_value is not None:
            return {
                "min": obj.min_value,
                "max": obj.max_value,
                "mean": obj.mean_value,
            }
        return None


class AQIBreakpointSerializer(serializers.Serializer):
    """Serializer for AQI breakpoint information."""

    pollutant = serializers.CharField()
    breakpoints = serializers.ListField()


class TimeSeriesPointSerializer(serializers.Serializer):
    """Serializer for time series data points."""

    timestamp = serializers.DateTimeField()
    value = serializers.FloatField(allow_null=True)
    aqi = serializers.IntegerField(allow_null=True)


class TimeSeriesSerializer(serializers.Serializer):
    """Serializer for time series response."""

    station_id = serializers.IntegerField(required=False)
    district_id = serializers.IntegerField(required=False)
    pollutant = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    data = TimeSeriesPointSerializer(many=True)


class PointValueSerializer(serializers.Serializer):
    """Serializer for point value query response."""

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    pollutant = serializers.CharField()
    date = serializers.DateField()
    concentration = serializers.FloatField(allow_null=True)
    aqi = serializers.IntegerField(allow_null=True)
    category = serializers.CharField(allow_null=True)
    color = serializers.CharField(allow_null=True)
    is_corrected = serializers.BooleanField()


class DataAvailabilitySerializer(serializers.Serializer):
    """Serializer for data availability response."""

    pollutant = serializers.CharField()
    available_dates = serializers.ListField(child=serializers.DateField())
    latest_date = serializers.DateField(allow_null=True)
    total_count = serializers.IntegerField()


# ==================== Helper Functions ====================


def get_aqi_category(aqi: int) -> str:
    """Get AQI category from AQI value."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def get_aqi_color(aqi: int) -> str:
    """Get AQI color from AQI value."""
    if aqi <= 50:
        return AQI_COLORS[0]
    elif aqi <= 100:
        return AQI_COLORS[1]
    elif aqi <= 150:
        return AQI_COLORS[2]
    elif aqi <= 200:
        return AQI_COLORS[3]
    elif aqi <= 300:
        return AQI_COLORS[4]
    else:
        return AQI_COLORS[5]
