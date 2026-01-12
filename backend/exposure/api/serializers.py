"""
Serializers for exposure API.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from ..models import DistrictExposure, Hotspot, ProvinceExposure, NationalExposure


class DistrictExposureSerializer(serializers.ModelSerializer):
    """Serializer for district exposure."""

    district_name = serializers.CharField(source="district.name", read_only=True)
    province = serializers.CharField(source="district.province", read_only=True)
    pop_at_risk = serializers.IntegerField(read_only=True)
    percent_at_risk = serializers.FloatField(read_only=True)
    
    # Computed fields to return unified AQI values (prefer satellite over legacy)
    aqi = serializers.SerializerMethodField(help_text="Combined AQI value")
    pm25 = serializers.SerializerMethodField(help_text="PM2.5 concentration µg/m³")
    
    def get_aqi(self, obj):
        """Return AQI preferring satellite-derived mean_aqi over legacy aqi_mean."""
        return obj.mean_aqi or obj.aqi_mean
    
    def get_pm25(self, obj):
        """Return PM2.5 preferring satellite-derived mean_pm25 over legacy concentration_mean."""
        return obj.mean_pm25 or obj.concentration_mean

    class Meta:
        model = DistrictExposure
        fields = [
            "id",
            "district",
            "district_name",
            "province",
            "pollutant",
            "date",
            "total_population",
            # Unified computed fields
            "aqi",
            "pm25",
            # Legacy raster-based fields
            "concentration_mean",
            "concentration_min",
            "concentration_max",
            "aqi_mean",
            "aqi_max",
            # Satellite-derived fields (new)
            "mean_pm25",
            "max_pm25",
            "mean_aqi",
            "max_aqi",
            # Exposure metrics
            "exposure_index",
            "rank",
            "data_source",
            # Population by AQI category
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "pop_at_risk",
            "percent_at_risk",
        ]


class DistrictExposureMapSerializer(serializers.ModelSerializer):
    """Lightweight serializer for map display."""

    district_name = serializers.CharField(source="district.name", read_only=True)
    aqi = serializers.SerializerMethodField(help_text="Combined AQI value")
    pm25 = serializers.SerializerMethodField(help_text="PM2.5 concentration")
    
    def get_aqi(self, obj):
        """Return AQI preferring satellite-derived mean_aqi over legacy aqi_mean."""
        return obj.mean_aqi or obj.aqi_mean
    
    def get_pm25(self, obj):
        """Return PM2.5 preferring satellite-derived mean_pm25 over legacy concentration_mean."""
        return obj.mean_pm25 or obj.concentration_mean

    class Meta:
        model = DistrictExposure
        fields = [
            "district",
            "district_name",
            "aqi",
            "pm25",
            "mean_aqi",
            "mean_pm25",
            "exposure_index",
            "rank",
        ]


class HotspotSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for hotspots."""

    affected_district_names = serializers.SerializerMethodField()

    class Meta:
        model = Hotspot
        geo_field = "centroid"
        fields = [
            "id",
            "pollutant",
            "date",
            "severity",
            "concentration_mean",
            "concentration_max",
            "aqi_mean",
            "affected_population",
            "area_sq_km",
            "persistence_days",
            "affected_district_names",
        ]

    def get_affected_district_names(self, obj):
        return list(obj.affected_districts.values_list("name", flat=True))


class HotspotListSerializer(serializers.ModelSerializer):
    """Lightweight hotspot serializer."""

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = Hotspot
        fields = [
            "id",
            "pollutant",
            "date",
            "latitude",
            "longitude",
            "severity",
            "aqi_mean",
            "affected_population",
            "persistence_days",
        ]

    def get_latitude(self, obj):
        return obj.centroid.y if obj.centroid else None

    def get_longitude(self, obj):
        return obj.centroid.x if obj.centroid else None


class ProvinceExposureSerializer(serializers.ModelSerializer):
    """Serializer for province exposure."""

    class Meta:
        model = ProvinceExposure
        fields = [
            "id",
            "province",
            "pollutant",
            "date",
            "total_population",
            "concentration_mean",
            "aqi_mean",
            "exposure_index",
            "rank",
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "n_districts",
        ]


class NationalExposureSerializer(serializers.ModelSerializer):
    """Serializer for national exposure summary."""

    worst_district_name = serializers.CharField(
        source="worst_district.name", read_only=True
    )

    class Meta:
        model = NationalExposure
        fields = [
            "id",
            "pollutant",
            "date",
            "total_population",
            "concentration_mean",
            "concentration_max",
            "aqi_mean",
            "exposure_index",
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "n_hotspots",
            "worst_district",
            "worst_district_name",
        ]


class ExposureRankingSerializer(serializers.Serializer):
    """Serializer for exposure rankings."""

    rank = serializers.IntegerField()
    district_id = serializers.IntegerField()
    district_name = serializers.CharField()
    province = serializers.CharField()
    exposure_index = serializers.FloatField()
    aqi_mean = serializers.FloatField()
    pop_at_risk = serializers.IntegerField()


class ExposureTimeSeriesSerializer(serializers.Serializer):
    """Serializer for exposure time series."""

    date = serializers.DateField()
    concentration_mean = serializers.FloatField(allow_null=True)
    aqi_mean = serializers.FloatField(allow_null=True)
    exposure_index = serializers.FloatField(allow_null=True)
    pop_at_risk = serializers.IntegerField(allow_null=True)


class PopulationBreakdownSerializer(serializers.Serializer):
    """Serializer for population breakdown by AQI category."""

    category = serializers.CharField()
    population = serializers.IntegerField()
    percentage = serializers.FloatField()
    color = serializers.CharField()
