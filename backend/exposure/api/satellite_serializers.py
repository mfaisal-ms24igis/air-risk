"""
Serializers for satellite-based exposure API.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from air_quality.models import District, AirQualityStation
from exposure.models import DistrictExposure, ProvinceExposure, NationalExposure


class SatelliteExposureSerializer(serializers.Serializer):
    """Serializer for satellite exposure metrics."""
    
    total_population = serializers.FloatField()
    exposed_population = serializers.FloatField()
    mean_exposure_index = serializers.FloatField()
    max_exposure_index = serializers.FloatField()
    
    # Population by AQI category
    pop_good = serializers.IntegerField()
    pop_moderate = serializers.IntegerField()
    pop_usg = serializers.IntegerField()
    pop_unhealthy = serializers.IntegerField()
    pop_very_unhealthy = serializers.IntegerField()
    pop_hazardous = serializers.IntegerField()
    
    # Pollutant data
    mean_pm25 = serializers.FloatField(allow_null=True)
    mean_no2 = serializers.FloatField(allow_null=True)
    mean_aod = serializers.FloatField(allow_null=True)
    estimated_pm25_from_aod = serializers.FloatField(allow_null=True)
    
    # AQI
    combined_aqi = serializers.FloatField(allow_null=True)
    aqi_category = serializers.CharField(allow_null=True)
    dominant_pollutant = serializers.CharField(allow_null=True)
    
    # Metadata
    data_coverage = serializers.FloatField()
    data_source = serializers.CharField()
    observation_date = serializers.DateField(allow_null=True)


class CityExposureSerializer(serializers.Serializer):
    """Serializer for city-level exposure response."""
    
    city = serializers.CharField()
    exposure = SatelliteExposureSerializer()


class DistrictExposureSatelliteSerializer(serializers.ModelSerializer):
    """Enhanced serializer for satellite-based district exposure."""
    
    district_name = serializers.CharField(source="district.name", read_only=True)
    province = serializers.CharField(source="district.province", read_only=True)
    pop_at_risk = serializers.IntegerField(read_only=True)
    percent_at_risk = serializers.FloatField(read_only=True)
    
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
            "mean_pm25",
            "max_pm25",
            "mean_aqi",
            "max_aqi",
            "exposure_index",
            "rank",
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "pop_at_risk",
            "percent_at_risk",
            "data_source",
            "station_count",
        ]


class DistrictExposureGeoJSONSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for district exposure with geometry."""
    
    district_name = serializers.CharField(source="district.name", read_only=True)
    province = serializers.CharField(source="district.province", read_only=True)
    geometry = serializers.SerializerMethodField()
    pop_at_risk = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = DistrictExposure
        geo_field = "geometry"
        fields = [
            "id",
            "district",
            "district_name",
            "province",
            "date",
            "total_population",
            "mean_pm25",
            "mean_aqi",
            "exposure_index",
            "pop_at_risk",
            "data_source",
        ]
    
    def get_geometry(self, obj):
        """Get geometry from related district."""
        if obj.district and obj.district.boundary:
            return obj.district.boundary
        return None


class ProvinceExposureSatelliteSerializer(serializers.ModelSerializer):
    """Enhanced serializer for satellite-based province exposure."""
    
    worst_district_name = serializers.CharField(
        source="worst_district.name", read_only=True, allow_null=True
    )
    
    class Meta:
        model = ProvinceExposure
        fields = [
            "id",
            "province",
            "pollutant",
            "date",
            "total_population",
            "mean_pm25",
            "mean_aqi",
            "max_aqi",
            "exposure_index",
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "district_count",
            "worst_district",
            "worst_district_name",
        ]


class NationalExposureSatelliteSerializer(serializers.ModelSerializer):
    """Enhanced serializer for satellite-based national exposure."""
    
    worst_district_name = serializers.CharField(
        source="worst_district.name", read_only=True, allow_null=True
    )
    
    class Meta:
        model = NationalExposure
        fields = [
            "id",
            "pollutant",
            "date",
            "total_population",
            "mean_pm25",
            "mean_aqi",
            "max_aqi",
            "exposure_index",
            "pop_good",
            "pop_moderate",
            "pop_usg",
            "pop_unhealthy",
            "pop_very_unhealthy",
            "pop_hazardous",
            "province_count",
            "district_count",
            "worst_district",
            "worst_district_name",
        ]


class DashboardSummarySerializer(serializers.Serializer):
    """Serializer for dashboard summary data."""
    
    date = serializers.DateField()
    
    # National totals
    total_population = serializers.IntegerField()
    total_exposed = serializers.IntegerField()
    
    # AQI metrics
    national_aqi = serializers.FloatField(allow_null=True)
    aqi_category = serializers.CharField(allow_null=True)
    
    # PM2.5
    national_pm25 = serializers.FloatField(allow_null=True)
    
    # Population breakdown
    pop_good = serializers.IntegerField()
    pop_moderate = serializers.IntegerField()
    pop_usg = serializers.IntegerField()
    pop_unhealthy = serializers.IntegerField()
    pop_very_unhealthy = serializers.IntegerField()
    pop_hazardous = serializers.IntegerField()
    
    # Counts
    province_count = serializers.IntegerField()
    district_count = serializers.IntegerField()
    
    # Worst areas
    worst_district = serializers.DictField(allow_null=True)
    worst_province = serializers.DictField(allow_null=True)
    
    # Data source
    data_sources = serializers.DictField()


class ExposureTrendSerializer(serializers.Serializer):
    """Serializer for exposure trends over time."""
    
    date = serializers.DateField()
    mean_aqi = serializers.FloatField(allow_null=True)
    mean_pm25 = serializers.FloatField(allow_null=True)
    exposure_index = serializers.FloatField(allow_null=True)
    pop_at_risk = serializers.IntegerField(allow_null=True)


class StationExposureSerializer(serializers.Serializer):
    """Serializer for station-level exposure."""
    
    station_id = serializers.IntegerField()
    station_name = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    
    # Satellite exposure at location
    satellite_pm25 = serializers.FloatField(allow_null=True)
    satellite_aqi = serializers.FloatField(allow_null=True)
    satellite_aod = serializers.FloatField(allow_null=True)
    
    # Ground measurements (if available)
    ground_pm25 = serializers.FloatField(allow_null=True)
    ground_readings_count = serializers.IntegerField()
    
    # Fused estimate
    fused_pm25 = serializers.FloatField(allow_null=True)
    
    # Population in buffer
    population = serializers.FloatField()
    exposure_index = serializers.FloatField()


class AQIBreakdownSerializer(serializers.Serializer):
    """Serializer for AQI category breakdown."""
    
    category = serializers.CharField()
    aqi_range = serializers.CharField()
    population = serializers.IntegerField()
    percentage = serializers.FloatField()
    color = serializers.CharField()
    health_message = serializers.CharField()
