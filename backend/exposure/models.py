"""
Models for population exposure analysis.
Stores district-level exposure statistics and hotspots.
"""

from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator, MaxValueValidator


# Data source choices for exposure calculations
DATA_SOURCE_CHOICES = [
    ("satellite", "Satellite Only"),
    ("ground", "Ground Only"),
    ("fused", "Ground-Satellite Fusion"),
    ("raster", "Corrected Raster"),
]


class DistrictExposure(models.Model):
    """
    Daily population exposure statistics for a district.
    Calculated from WorldPop population grid × air quality data.
    
    Supports multiple data sources:
    - satellite: MODIS AOD + TROPOMI
    - ground: Ground station measurements
    - fused: Combined satellite + ground
    - raster: Corrected raster products
    """

    district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.CASCADE,
        related_name="exposures",
    )

    pollutant = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
        help_text="Pollutant type (null for combined satellite data)"
    )

    date = models.DateField(db_index=True)

    # Population statistics
    total_population = models.BigIntegerField(
        default=0, help_text="Total population in district"
    )

    # Concentration statistics (µg/m³) - legacy fields for raster-based
    concentration_mean = models.FloatField(
        null=True, blank=True, help_text="Population-weighted mean concentration"
    )
    concentration_min = models.FloatField(null=True, blank=True)
    concentration_max = models.FloatField(null=True, blank=True)
    concentration_std = models.FloatField(null=True, blank=True)

    # PM2.5 specific fields (for satellite/fusion)
    mean_pm25 = models.FloatField(
        null=True, blank=True, help_text="Mean PM2.5 concentration (µg/m³)"
    )
    max_pm25 = models.FloatField(
        null=True, blank=True, help_text="Maximum PM2.5 concentration"
    )

    # AQI statistics (legacy for raster-based)
    aqi_mean = models.FloatField(
        null=True, blank=True, help_text="Population-weighted mean AQI"
    )
    aqi_max = models.IntegerField(null=True, blank=True)

    # Combined AQI fields (for satellite/fusion)
    mean_aqi = models.FloatField(
        null=True, blank=True, help_text="Combined AQI (worst of all pollutants)"
    )
    max_aqi = models.FloatField(
        null=True, blank=True, help_text="Maximum AQI in district"
    )

    # Population exposed by AQI category
    pop_good = models.BigIntegerField(
        default=0, help_text="Population in Good AQI (0-50)"
    )
    pop_moderate = models.BigIntegerField(
        default=0, help_text="Population in Moderate AQI (51-100)"
    )
    pop_usg = models.BigIntegerField(
        default=0, help_text="Population in USG AQI (101-150)"
    )
    pop_unhealthy = models.BigIntegerField(
        default=0, help_text="Population in Unhealthy AQI (151-200)"
    )
    pop_very_unhealthy = models.BigIntegerField(
        default=0, help_text="Population in Very Unhealthy AQI (201-300)"
    )
    pop_hazardous = models.BigIntegerField(
        default=0, help_text="Population in Hazardous AQI (>300)"
    )

    # Exposure index (composite score)
    exposure_index = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        help_text="Exposure index (0-500)",
    )

    # District ranking for this day
    rank = models.IntegerField(
        null=True, blank=True, help_text="Rank among all districts (1=worst)"
    )

    # Data source tracking
    data_source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="satellite",
        help_text="Data source for this calculation"
    )
    station_count = models.IntegerField(
        default=0,
        help_text="Number of ground stations in district"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Allow both pollutant-specific and combined records
        ordering = ["-date", "rank"]
        indexes = [
            models.Index(fields=["pollutant", "date"]),
            models.Index(fields=["date", "rank"]),
            models.Index(fields=["district", "date"]),
            models.Index(fields=["data_source", "date"]),
        ]

    def __str__(self):
        pollutant = self.pollutant or "Combined"
        return f"{self.district.name} - {pollutant} - {self.date}"

    @property
    def pop_at_risk(self) -> int:
        """Population exposed to unhealthy levels (AQI > 100)."""
        return (
            self.pop_usg
            + self.pop_unhealthy
            + self.pop_very_unhealthy
            + self.pop_hazardous
        )

    @property
    def percent_at_risk(self) -> float:
        """Percentage of population at risk."""
        if self.total_population == 0:
            return 0.0
        return (self.pop_at_risk / self.total_population) * 100


class Hotspot(models.Model):
    """
    Geographic hotspot of high air pollution exposure.
    Identified from spatial clustering of high-risk areas.
    """

    SEVERITY_CHOICES = [
        ("MODERATE", "Moderate"),
        ("HIGH", "High"),
        ("SEVERE", "Severe"),
        ("CRITICAL", "Critical"),
    ]

    pollutant = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
        help_text="Pollutant type (null for combined)"
    )

    date = models.DateField(db_index=True)

    # Location
    centroid = gis_models.PointField(srid=4326, help_text="Hotspot centroid")

    # Affected area (convex hull of hotspot pixels)
    geometry = gis_models.PolygonField(
        srid=4326, null=True, blank=True, help_text="Hotspot boundary"
    )

    area_sq_km = models.FloatField(
        null=True, blank=True, help_text="Hotspot area in km²"
    )

    # Severity
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="MODERATE",
    )

    # Statistics
    concentration_mean = models.FloatField(help_text="Mean concentration in hotspot")
    concentration_max = models.FloatField(help_text="Maximum concentration")
    aqi_mean = models.IntegerField(help_text="Mean AQI in hotspot")

    # Affected population
    affected_population = models.BigIntegerField(
        default=0, help_text="Estimated population in hotspot area"
    )

    # Affected districts
    affected_districts = models.ManyToManyField(
        "air_quality.District",
        related_name="hotspots",
        blank=True,
    )

    # Persistence (how many consecutive days)
    persistence_days = models.IntegerField(
        default=1, help_text="Number of consecutive days as hotspot"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-severity", "-affected_population"]
        indexes = [
            models.Index(fields=["pollutant", "date"]),
            models.Index(fields=["date", "severity"]),
        ]

    def __str__(self):
        return f"{self.pollutant} Hotspot ({self.severity}) - {self.date}"


class ProvinceExposure(models.Model):
    """
    Province-level aggregated exposure statistics.
    Derived from district exposures.
    """

    province = models.CharField(max_length=100, db_index=True)

    pollutant = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
        help_text="Pollutant type (null for combined)"
    )

    date = models.DateField(db_index=True)

    # Aggregated statistics
    total_population = models.BigIntegerField(default=0)
    concentration_mean = models.FloatField(null=True, blank=True)
    aqi_mean = models.FloatField(null=True, blank=True)
    exposure_index = models.FloatField(null=True, blank=True)

    # New fields for satellite-based calculation
    mean_pm25 = models.FloatField(
        null=True, blank=True, help_text="Population-weighted mean PM2.5"
    )
    mean_aqi = models.FloatField(null=True, blank=True)
    max_aqi = models.FloatField(null=True, blank=True)

    # Population by category
    pop_good = models.BigIntegerField(default=0)
    pop_moderate = models.BigIntegerField(default=0)
    pop_usg = models.BigIntegerField(default=0)
    pop_unhealthy = models.BigIntegerField(default=0)
    pop_very_unhealthy = models.BigIntegerField(default=0)
    pop_hazardous = models.BigIntegerField(default=0)

    # Number of districts
    n_districts = models.IntegerField(default=0)
    district_count = models.IntegerField(default=0, help_text="Number of districts with data")

    # Worst district
    worst_district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worst_province_days",
        help_text="District with highest AQI"
    )

    # Ranking
    rank = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "rank"]
        indexes = [
            models.Index(fields=["pollutant", "date"]),
            models.Index(fields=["province", "date"]),
        ]

    def __str__(self):
        pollutant = self.pollutant or "Combined"
        return f"{self.province} - {pollutant} - {self.date}"


class NationalExposure(models.Model):
    """
    National-level exposure summary.
    Daily summary across all of Pakistan.
    """

    pollutant = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        db_index=True,
        help_text="Pollutant type (null for combined)"
    )

    date = models.DateField(db_index=True)

    # National statistics
    total_population = models.BigIntegerField(default=0)
    concentration_mean = models.FloatField(null=True, blank=True)
    concentration_max = models.FloatField(null=True, blank=True)
    aqi_mean = models.FloatField(null=True, blank=True)
    exposure_index = models.FloatField(null=True, blank=True)

    # New fields for satellite-based calculation
    mean_pm25 = models.FloatField(
        null=True, blank=True, help_text="National population-weighted mean PM2.5"
    )
    mean_aqi = models.FloatField(null=True, blank=True)
    max_aqi = models.FloatField(null=True, blank=True)

    # Population by category
    pop_good = models.BigIntegerField(default=0)
    pop_moderate = models.BigIntegerField(default=0)
    pop_usg = models.BigIntegerField(default=0)
    pop_unhealthy = models.BigIntegerField(default=0)
    pop_very_unhealthy = models.BigIntegerField(default=0)
    pop_hazardous = models.BigIntegerField(default=0)

    # Hotspot count
    n_hotspots = models.IntegerField(default=0)

    # Province and district counts
    province_count = models.IntegerField(default=0, help_text="Number of provinces with data")
    district_count = models.IntegerField(default=0, help_text="Number of districts with data")

    # Most affected district
    worst_district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worst_exposure_days",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        pollutant = self.pollutant or "Combined"
        return f"Pakistan - {pollutant} - {self.date}"
