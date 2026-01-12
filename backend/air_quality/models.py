"""
Models for air quality data: Districts, Ground Stations, Readings, and Rasters.

This module defines the core data models for the Air Quality Exposure & Risk
Intelligence Platform, including administrative boundaries, monitoring stations,
pollutant readings, and satellite raster metadata.
"""

from datetime import datetime
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from .constants import (
    Pollutant,
    UnitType,
    PROVINCES,
    COORDINATE_BOUNDS,
    GLOBAL_COORDINATE_BOUNDS,
    POLLUTANT_VALUE_RANGES,
)


# =============================================================================
# VALIDATORS
# =============================================================================

def validate_latitude(value: float) -> None:
    """
    Validate latitude is within global bounds.
    
    Args:
        value: Latitude in decimal degrees.
        
    Raises:
        ValidationError: If latitude is outside valid range.
    """
    min_lat, max_lat = GLOBAL_COORDINATE_BOUNDS["latitude"]
    if not (min_lat <= value <= max_lat):
        raise ValidationError(
            f"Latitude must be between {min_lat} and {max_lat}. Got: {value}"
        )


def validate_longitude(value: float) -> None:
    """
    Validate longitude is within global bounds.
    
    Args:
        value: Longitude in decimal degrees.
        
    Raises:
        ValidationError: If longitude is outside valid range.
    """
    min_lon, max_lon = GLOBAL_COORDINATE_BOUNDS["longitude"]
    if not (min_lon <= value <= max_lon):
        raise ValidationError(
            f"Longitude must be between {min_lon} and {max_lon}. Got: {value}"
        )


def validate_pakistan_coordinates(latitude: float, longitude: float) -> bool:
    """
    Check if coordinates are within Pakistan region bounds.
    
    Args:
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        
    Returns:
        True if coordinates are within Pakistan bounds.
    """
    lat_min, lat_max = COORDINATE_BOUNDS["latitude"]
    lon_min, lon_max = COORDINATE_BOUNDS["longitude"]
    return (lat_min <= latitude <= lat_max) and (lon_min <= longitude <= lon_max)


# =============================================================================
# ADMINISTRATIVE BOUNDARY MODELS
# =============================================================================

class District(models.Model):
    """
    Administrative district with geometry for zonal statistics.
    """

    name = models.CharField(max_length=100, db_index=True)
    province = models.CharField(
        max_length=100, choices=[(p, p) for p in PROVINCES], db_index=True
    )

    # PostGIS geometry
    geometry = models.MultiPolygonField(srid=4326)

    # Centroid for hotspot markers (auto-calculated)
    centroid = models.PointField(srid=4326, null=True, blank=True)

    # Cached population from WorldPop
    population = models.BigIntegerField(
        null=True, blank=True, help_text="Total population from WorldPop grid"
    )

    # Area in square kilometers
    area_km2 = models.FloatField(
        null=True, blank=True, help_text="Area in square kilometers"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "District"
        verbose_name_plural = "Districts"
        ordering = ["province", "name"]
        unique_together = ["name", "province"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["province"]),
        ]

    def __str__(self):
        return f"{self.name}, {self.province}"

    def save(self, *args, **kwargs):
        # Auto-calculate centroid
        if self.geometry and not self.centroid:
            self.centroid = self.geometry.centroid

        # Auto-calculate area
        if self.geometry and not self.area_km2:
            # Transform to equal-area projection for accurate area
            geom_transformed = self.geometry.transform(
                32642, clone=True
            )  # UTM 42N for Pakistan
            self.area_km2 = geom_transformed.area / 1_000_000  # m² to km²

        super().save(*args, **kwargs)


class Province(models.Model):
    """
    Administrative province with geometry for zonal statistics.
    """

    name = models.CharField(max_length=100, unique=True, db_index=True)

    # PostGIS geometry
    geometry = models.MultiPolygonField(srid=4326)

    # Centroid for hotspot markers (auto-calculated)
    centroid = models.PointField(srid=4326, null=True, blank=True)

    # Cached population from WorldPop
    population = models.BigIntegerField(
        null=True, blank=True, help_text="Total population from WorldPop grid"
    )

    # Area in square kilometers
    area_km2 = models.FloatField(
        null=True, blank=True, help_text="Area in square kilometers"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Province"
        verbose_name_plural = "Provinces"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-calculate centroid
        if self.geometry and not self.centroid:
            self.centroid = self.geometry.centroid

        # Auto-calculate area
        if self.geometry and not self.area_km2:
            # Transform to equal-area projection for accurate area
            geom_transformed = self.geometry.transform(
                32642, clone=True
            )  # UTM 42N for Pakistan
            self.area_km2 = geom_transformed.area / 1_000_000  # m² to km²

        super().save(*args, **kwargs)


class Tehsil(models.Model):
    """
    Administrative tehsil (sub-district) with geometry for zonal statistics.
    """

    name = models.CharField(max_length=100, db_index=True)
    district = models.ForeignKey(
        District, on_delete=models.CASCADE, related_name="tehsils"
    )
    province = models.CharField(
        max_length=100, choices=[(p, p) for p in PROVINCES], db_index=True
    )

    # PostGIS geometry
    geometry = models.MultiPolygonField(srid=4326)

    # Centroid for hotspot markers (auto-calculated)
    centroid = models.PointField(srid=4326, null=True, blank=True)

    # Cached population from WorldPop
    population = models.BigIntegerField(
        null=True, blank=True, help_text="Total population from WorldPop grid"
    )

    # Area in square kilometers
    area_km2 = models.FloatField(
        null=True, blank=True, help_text="Area in square kilometers"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tehsil"
        verbose_name_plural = "Tehsils"
        ordering = ["province", "district", "name"]
        unique_together = ["name", "district"]

    def __str__(self):
        return f"{self.name}, {self.district.name}"

    def save(self, *args, **kwargs):
        # Auto-calculate centroid
        if self.geometry and not self.centroid:
            self.centroid = self.geometry.centroid

        # Auto-calculate area
        if self.geometry and not self.area_km2:
            # Transform to equal-area projection for accurate area
            geom_transformed = self.geometry.transform(
                32642, clone=True
            )  # UTM 42N for Pakistan
            self.area_km2 = geom_transformed.area / 1_000_000  # m² to km²

        super().save(*args, **kwargs)


# =============================================================================
# AIR QUALITY STATION & READING MODELS (NEW SCHEMA)
# =============================================================================

class AirQualityStation(models.Model):
    """
    Ground-based air quality monitoring station from OpenAQ.
    
    This model replaces the legacy GroundStation with stricter validation,
    explicit priority ranking for API rate limiting, and better data provenance.
    
    Attributes:
        openaq_location_id: Unique identifier from OpenAQ API (primary key for sync).
        name: Human-readable station name.
        location: PostGIS Point geometry (EPSG:4326).
        priority: Station priority for API queries (1=highest, 5=lowest).
        is_active: Whether station is included in regular syncs (max 60 active).
    """

    class StationPriority(models.IntegerChoices):
        """Priority levels for API rate limiting."""
        CRITICAL = 1, "Critical (hourly sync)"
        HIGH = 2, "High (daily sync)"
        MEDIUM = 3, "Medium (weekly sync)"
        LOW = 4, "Low (monthly sync)"
        MINIMAL = 5, "Minimal (on-demand only)"

    class DataSource(models.TextChoices):
        """Source of station data."""
        OPENAQ = "OPENAQ", "OpenAQ API"
        MANUAL = "MANUAL", "Manual Entry"
        GOVERNMENT = "GOV", "Government Agency"
        RESEARCH = "RESEARCH", "Research Institution"

    # OpenAQ identifiers
    openaq_location_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="Unique location ID from OpenAQ API"
    )
    
    # Legacy field for backwards compatibility
    openaq_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Legacy string ID (deprecated, use openaq_location_id)"
    )

    name = models.CharField(max_length=200, db_index=True)
    
    # Location with validation
    latitude = models.FloatField(
        validators=[validate_latitude],
        help_text="Latitude in decimal degrees (WGS84)"
    )
    longitude = models.FloatField(
        validators=[validate_longitude],
        help_text="Longitude in decimal degrees (WGS84)"
    )
    
    # PostGIS geometry (auto-populated from lat/lon)
    location = models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Auto-populated Point geometry"
    )

    # Associated district (for joining with satellite data)
    district = models.ForeignKey(
        "District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="air_quality_stations",
    )

    # Station metadata
    locality = models.CharField(
        max_length=200,
        blank=True,
        help_text="Locality/neighborhood name"
    )
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=50, default="PK")
    timezone = models.CharField(max_length=50, default="Asia/Karachi")
    
    # Data source tracking
    data_source = models.CharField(
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.OPENAQ,
    )

    # Available parameters at this station (e.g., ["pm25", "pm10", "no2"])
    available_parameters = models.JSONField(
        default=list,
        help_text="List of pollutants measured at this station"
    )
    sensors_count = models.IntegerField(
        default=0,
        help_text="Number of sensors at this station"
    )

    # Priority and status for API rate limiting
    priority = models.IntegerField(
        choices=StationPriority.choices,
        default=StationPriority.MEDIUM,
        db_index=True,
        help_text="Priority for API queries (1=highest)"
    )
    is_active = models.BooleanField(
        default=False,  # Default to inactive - must explicitly activate
        db_index=True,
        help_text="Whether station is included in regular syncs"
    )
    
    # Data quality tracking
    last_reading_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of most recent reading"
    )
    total_readings = models.IntegerField(
        default=0,
        help_text="Total number of readings from this station"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Air Quality Station"
        verbose_name_plural = "Air Quality Stations"
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["openaq_location_id"]),
            models.Index(fields=["is_active", "priority"]),
            models.Index(fields=["country"]),
            models.Index(fields=["data_source"]),
        ]

    def __str__(self) -> str:
        status = "🟢" if self.is_active else "⚪"
        return f"{status} {self.name} ({self.openaq_location_id})"

    def clean(self) -> None:
        """Validate station data before save."""
        super().clean()
        
        # Warn if coordinates outside Pakistan (but don't reject)
        if not validate_pakistan_coordinates(self.latitude, self.longitude):
            # Log warning but allow - station might be near border
            pass

    def save(self, *args, **kwargs) -> None:
        """Auto-populate location geometry from lat/lon."""
        from django.contrib.gis.geos import Point
        
        # Create Point geometry from lat/lon
        if self.latitude and self.longitude:
            self.location = Point(self.longitude, self.latitude, srid=4326)
        
        # Sync legacy openaq_id field
        if self.openaq_location_id and not self.openaq_id:
            self.openaq_id = str(self.openaq_location_id)
        
        super().save(*args, **kwargs)

    @property
    def coordinates(self) -> tuple[float, float]:
        """Return (longitude, latitude) tuple for GeoJSON compatibility."""
        return (self.longitude, self.latitude)
    
    @property
    def is_in_pakistan(self) -> bool:
        """Check if station is within Pakistan bounds."""
        return validate_pakistan_coordinates(self.latitude, self.longitude)


class PollutantReading(models.Model):
    """
    Individual air quality reading from a monitoring station.
    
    This model replaces the legacy GroundReading with:
    - Single parameter/value per row (normalized schema)
    - Explicit unit tracking for data provenance
    - Normalized value field for standardized comparisons
    
    The unique constraint on (station, timestamp, parameter) prevents duplicates
    while allowing multiple pollutants at the same timestamp.
    """

    station = models.ForeignKey(
        AirQualityStation,
        on_delete=models.CASCADE,
        related_name="readings"
    )

    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Measurement timestamp (UTC)"
    )

    # Single parameter per row (normalized schema)
    parameter = models.CharField(
        max_length=10,
        choices=Pollutant.choices(),
        db_index=True,
        help_text="Pollutant type (e.g., PM25, NO2)"
    )
    
    # Original value and unit as received
    value = models.FloatField(
        help_text="Measurement value in original units"
    )
    unit = models.CharField(
        max_length=20,
        choices=UnitType.choices(),
        help_text="Original measurement unit"
    )
    
    # Normalized value (converted to standard unit for the pollutant)
    value_normalized = models.FloatField(
        null=True,
        blank=True,
        help_text="Value normalized to standard unit (µg/m³ for most)"
    )
    unit_normalized = models.CharField(
        max_length=20,
        choices=UnitType.choices(),
        blank=True,
        help_text="Standard unit after normalization"
    )

    # Data quality flags
    is_valid = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether reading passed validation checks"
    )
    validation_flags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation issues (e.g., ['out_of_range', 'negative'])"
    )

    # Raw response from source (for debugging)
    raw_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Original data from API/file"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pollutant Reading"
        verbose_name_plural = "Pollutant Readings"
        ordering = ["-timestamp"]
        unique_together = ["station", "timestamp", "parameter"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["parameter"]),
            models.Index(fields=["station", "timestamp"]),
            models.Index(fields=["station", "parameter", "timestamp"]),
            models.Index(fields=["is_valid"]),
        ]

    def __str__(self) -> str:
        return f"{self.station.name} - {self.parameter}: {self.value} {self.unit} @ {self.timestamp}"

    def clean(self) -> None:
        """Validate reading data."""
        super().clean()
        
        flags = []
        
        # Check for negative values
        if self.value < 0:
            flags.append("negative_value")
        
        # Check value range for pollutant
        pollutant = Pollutant.from_string(self.parameter)
        if pollutant and pollutant in POLLUTANT_VALUE_RANGES:
            min_val, max_val = POLLUTANT_VALUE_RANGES[pollutant]
            # Use normalized value if available, else original
            check_val = self.value_normalized if self.value_normalized else self.value
            if check_val < min_val or check_val > max_val:
                flags.append("out_of_range")
        
        if flags:
            self.validation_flags = flags
            self.is_valid = len(flags) == 0 or flags == ["out_of_range"]  # Allow out_of_range but flag it

    def save(self, *args, **kwargs) -> None:
        """Run validation before save."""
        self.full_clean()
        super().save(*args, **kwargs)


class DataIngestionLog(models.Model):
    """
    Log of data ingestion runs for tracking and debugging.
    
    Each run of the ingest_openaq command creates one record to track
    what was processed, how long it took, and any errors encountered.
    """

    class IngestionStatus(models.TextChoices):
        STARTED = "STARTED", "Started"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        PARTIAL = "PARTIAL", "Partial Success"

    # Run identification
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=IngestionStatus.choices,
        default=IngestionStatus.STARTED,
    )
    
    # Source information
    source_type = models.CharField(
        max_length=50,
        default="openaq_bulk",
        help_text="Type of data source (openaq_bulk, openaq_api, manual)"
    )
    source_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to source files or API endpoint"
    )

    # Statistics
    files_processed = models.IntegerField(default=0)
    records_total = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_skipped = models.IntegerField(default=0)
    records_invalid = models.IntegerField(default=0)
    
    # Stations affected
    stations_processed = models.IntegerField(default=0)
    
    # Performance
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text="Total processing time in seconds"
    )

    # Error tracking
    error_count = models.IntegerField(default=0)
    error_log_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Path to detailed error log file"
    )
    error_summary = models.TextField(
        blank=True,
        help_text="Summary of errors encountered"
    )

    # Command arguments (for reproducibility)
    command_args = models.JSONField(
        default=dict,
        help_text="Arguments passed to the ingestion command"
    )

    class Meta:
        verbose_name = "Data Ingestion Log"
        verbose_name_plural = "Data Ingestion Logs"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["started_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["source_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_type} @ {self.started_at} - {self.status}"

    @property
    def success_rate(self) -> float:
        """Calculate percentage of successfully processed records."""
        if self.records_total == 0:
            return 0.0
        return (self.records_created + self.records_updated) / self.records_total * 100

    def mark_completed(self) -> None:
        """Mark ingestion as completed and calculate duration."""
        from django.utils import timezone
        
        self.completed_at = timezone.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        
        if self.error_count > 0 and self.records_created > 0:
            self.status = self.IngestionStatus.PARTIAL
        elif self.error_count > 0:
            self.status = self.IngestionStatus.FAILED
        else:
            self.status = self.IngestionStatus.COMPLETED
        
        self.save()


# =============================================================================
# LEGACY MODELS (KEPT FOR MIGRATION COMPATIBILITY)
# =============================================================================

class GroundStation(models.Model):
    """
    [DEPRECATED] Legacy ground station model.
    
    This model is kept for migration compatibility. New code should use
    AirQualityStation instead. Will be removed in a future migration.
    """

    # OpenAQ identifiers
    openaq_id = models.CharField(max_length=50, unique=True, db_index=True)
    openaq_location_id = models.IntegerField(null=True, blank=True)

    name = models.CharField(max_length=200)

    # Location
    location = models.PointField(srid=4326)

    # Associated district (for joining with satellite data)
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ground_stations",
    )

    # Station metadata
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=50, default="Pakistan")

    # Available parameters at this station
    available_parameters = models.JSONField(
        default=list, help_text="List of pollutants measured at this station"
    )

    # Status
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ground Station (Legacy)"
        verbose_name_plural = "Ground Stations (Legacy)"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.openaq_id})"

    @property
    def coordinates(self):
        """Return (longitude, latitude) tuple."""
        return (self.location.x, self.location.y)


class GroundReading(models.Model):
    """
    [DEPRECATED] Legacy ground reading model.
    
    This model is kept for migration compatibility. New code should use
    PollutantReading instead. Will be removed in a future migration.
    """

    station = models.ForeignKey(
        GroundStation, on_delete=models.CASCADE, related_name="readings"
    )

    timestamp = models.DateTimeField(db_index=True)

    # Pollutant values (nullable - not all stations measure all pollutants)
    no2 = models.FloatField(null=True, blank=True, help_text="NO2 in ppb")
    so2 = models.FloatField(null=True, blank=True, help_text="SO2 in ppb")
    pm25 = models.FloatField(null=True, blank=True, help_text="PM2.5 in µg/m³")
    co = models.FloatField(null=True, blank=True, help_text="CO in ppm")
    o3 = models.FloatField(null=True, blank=True, help_text="O3 in ppb")

    # Raw response from OpenAQ (for debugging)
    raw_data = models.JSONField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ground Reading (Legacy)"
        verbose_name_plural = "Ground Readings (Legacy)"
        ordering = ["-timestamp"]
        unique_together = ["station", "timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["station", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.station.name} - {self.timestamp}"

    def get_value(self, pollutant: Pollutant) -> float | None:
        """Get the value for a specific pollutant."""
        field_map = {
            Pollutant.NO2: self.no2,
            Pollutant.SO2: self.so2,
            Pollutant.PM25: self.pm25,
            Pollutant.CO: self.co,
            Pollutant.O3: self.o3,
        }
        return field_map.get(pollutant)


# =============================================================================
# RASTER MODELS
# =============================================================================

class PollutantRaster(models.Model):
    """
    Metadata for downloaded and processed raster files.
    """

    class ProcessingStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DOWNLOADING = "DOWNLOADING", "Downloading"
        DOWNLOADED = "DOWNLOADED", "Downloaded"
        CORRECTING = "CORRECTING", "Applying Correction"
        CORRECTED = "CORRECTED", "Corrected"
        CALCULATING = "CALCULATING", "Calculating Exposure"
        COMPLETE = "COMPLETE", "Complete"
        FAILED = "FAILED", "Failed"

    date = models.DateField(db_index=True)
    pollutant = models.CharField(
        max_length=10, choices=Pollutant.choices(), db_index=True
    )

    # File paths (relative to RASTER_DATA_PATH)
    raw_path = models.CharField(
        max_length=500, blank=True, help_text="Path to raw downloaded raster"
    )
    corrected_path = models.CharField(
        max_length=500, blank=True, help_text="Path to bias-corrected raster"
    )

    # Processing status
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )

    # Processing metadata
    correction_model_id = models.IntegerField(
        null=True, blank=True, help_text="ID of the correction model used"
    )

    # Statistics (computed after processing)
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    mean_value = models.FloatField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)

    # Timestamps
    downloaded_at = models.DateTimeField(null=True, blank=True)
    corrected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pollutant Raster"
        verbose_name_plural = "Pollutant Rasters"
        ordering = ["-date", "pollutant"]
        unique_together = ["date", "pollutant"]
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["pollutant"]),
            models.Index(fields=["status"]),
            models.Index(fields=["date", "pollutant"]),
        ]

    def __str__(self):
        return f"{self.pollutant} - {self.date} ({self.status})"

    @property
    def is_processed(self):
        return self.status == self.ProcessingStatus.COMPLETE

    @property
    def has_raw(self):
        return bool(self.raw_path)

    @property
    def has_corrected(self):
        return bool(self.corrected_path)


# =============================================================================
# SYSTEM STATUS & METADATA TRACKING
# =============================================================================

class SystemStatus(models.Model):
    """
    Track system-wide status and metadata for background tasks.
    
    Used for:
    - Tracking latest Sentinel-5P image availability
    - Notifying frontend when to refresh tiles
    - Monitoring background task health
    """
    
    class StatusType(models.TextChoices):
        """Type of status being tracked."""
        SENTINEL5P_NO2 = "S5P_NO2", "Sentinel-5P NO2 Latest Image"
        SENTINEL5P_SO2 = "S5P_SO2", "Sentinel-5P SO2 Latest Image"
        RISK_CALCULATION = "RISK_CALC", "Risk Calculation Status"
        DATA_SYNC = "DATA_SYNC", "Data Synchronization"
        SYSTEM_HEALTH = "SYS_HEALTH", "System Health"
    
    # Status identifier (unique key)
    status_type = models.CharField(
        max_length=20,
        choices=StatusType.choices,
        unique=True,
        db_index=True,
        help_text="Type of status being tracked"
    )
    
    # Current value (flexible JSON field)
    value = models.JSONField(
        default=dict,
        help_text="Current status value (e.g., image date, task result)"
    )
    
    # Last check timestamp
    last_checked = models.DateTimeField(
        auto_now=True,
        help_text="When this status was last updated"
    )
    
    # Last change timestamp (only updates when value changes)
    last_changed = models.DateTimeField(
        auto_now_add=True,
        help_text="When the value last changed"
    )
    
    # Is this status currently valid/healthy?
    is_healthy = models.BooleanField(
        default=True,
        help_text="Whether this status indicates a healthy state"
    )
    
    # Error message if unhealthy
    error_message = models.TextField(
        blank=True,
        help_text="Error message if status is unhealthy"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Status"
        verbose_name_plural = "System Statuses"
        ordering = ["status_type"]
    
    def __str__(self):
        return f"{self.get_status_type_display()}: {self.last_checked.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """Update last_changed only if value actually changed."""
        if self.pk:
            try:
                old_instance = SystemStatus.objects.get(pk=self.pk)
                if old_instance.value != self.value:
                    self.last_changed = datetime.now()
            except SystemStatus.DoesNotExist:
                pass
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_status(cls, status_type: str, default_value: dict = None):
        """Get or create a status entry."""
        status, created = cls.objects.get_or_create(
            status_type=status_type,
            defaults={'value': default_value or {}}
        )
        return status
    
    @classmethod
    def update_status(
        cls,
        status_type: str,
        value: dict,
        is_healthy: bool = True,
        error_message: str = ""
    ):
        """Update a status entry."""
        status = cls.get_or_create_status(status_type)
        status.value = value
        status.is_healthy = is_healthy
        status.error_message = error_message
        status.save()
        return status

