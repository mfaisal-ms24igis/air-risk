"""
Admin configuration for air quality models.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html

from .models import District, GroundStation, GroundReading, PollutantRaster


@admin.register(District)
class DistrictAdmin(GISModelAdmin):
    """Admin for District model with map widget."""

    list_display = [
        "name",
        "province",
        "population_display",
        "area_display",
        "station_count",
        "updated_at",
    ]
    list_filter = ["province"]
    search_fields = ["name", "province"]
    ordering = ["province", "name"]
    readonly_fields = ["centroid", "area_km2", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("name", "province")}),
        (
            "Geometry",
            {
                "fields": ("geometry", "centroid", "area_km2"),
                "classes": ("collapse",),
            },
        ),
        (
            "Demographics",
            {
                "fields": ("population",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def population_display(self, obj):
        if obj.population:
            return f"{obj.population:,}"
        return "—"

    population_display.short_description = "Population"

    def area_display(self, obj):
        if obj.area_km2:
            return f"{obj.area_km2:,.1f} km²"
        return "—"

    area_display.short_description = "Area"

    def station_count(self, obj):
        count = obj.ground_stations.filter(is_active=True).count()
        return count if count > 0 else "—"

    station_count.short_description = "Stations"


@admin.register(GroundStation)
class GroundStationAdmin(GISModelAdmin):
    """Admin for Ground Station model."""

    list_display = [
        "name",
        "openaq_id",
        "city",
        "district",
        "parameters_display",
        "is_active",
        "last_updated",
    ]
    list_filter = ["is_active", "district__province", "city"]
    search_fields = ["name", "openaq_id", "city"]
    ordering = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["district"]

    fieldsets = (
        (None, {"fields": ("name", "openaq_id", "openaq_location_id")}),
        (
            "Location",
            {
                "fields": ("location", "city", "country", "district"),
            },
        ),
        (
            "Parameters",
            {
                "fields": ("available_parameters",),
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "last_updated"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def parameters_display(self, obj):
        if obj.available_parameters:
            return ", ".join(obj.available_parameters)
        return "—"

    parameters_display.short_description = "Parameters"


@admin.register(GroundReading)
class GroundReadingAdmin(admin.ModelAdmin):
    """Admin for Ground Reading model."""

    list_display = [
        "station",
        "timestamp",
        "no2_display",
        "so2_display",
        "pm25_display",
        "co_display",
        "o3_display",
    ]
    list_filter = ["station__district__province", "timestamp"]
    search_fields = ["station__name"]
    ordering = ["-timestamp"]
    readonly_fields = ["created_at"]
    raw_id_fields = ["station"]
    date_hierarchy = "timestamp"

    def no2_display(self, obj):
        return f"{obj.no2:.2f}" if obj.no2 else "—"

    no2_display.short_description = "NO₂"

    def so2_display(self, obj):
        return f"{obj.so2:.2f}" if obj.so2 else "—"

    so2_display.short_description = "SO₂"

    def pm25_display(self, obj):
        return f"{obj.pm25:.1f}" if obj.pm25 else "—"

    pm25_display.short_description = "PM2.5"

    def co_display(self, obj):
        return f"{obj.co:.2f}" if obj.co else "—"

    co_display.short_description = "CO"

    def o3_display(self, obj):
        return f"{obj.o3:.2f}" if obj.o3 else "—"

    o3_display.short_description = "O₃"


@admin.register(PollutantRaster)
class PollutantRasterAdmin(admin.ModelAdmin):
    """Admin for Pollutant Raster model."""

    list_display = [
        "date",
        "pollutant",
        "status_display",
        "has_files",
        "mean_display",
        "updated_at",
    ]
    list_filter = ["pollutant", "status", "date"]
    search_fields = ["date"]
    ordering = ["-date", "pollutant"]
    readonly_fields = [
        "downloaded_at",
        "corrected_at",
        "min_value",
        "max_value",
        "mean_value",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "date"

    fieldsets = (
        (None, {"fields": ("date", "pollutant", "status")}),
        (
            "Files",
            {
                "fields": ("raw_path", "corrected_path"),
            },
        ),
        (
            "Processing",
            {
                "fields": ("correction_model_id", "error_message"),
            },
        ),
        (
            "Statistics",
            {
                "fields": ("min_value", "max_value", "mean_value"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("downloaded_at", "corrected_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_display(self, obj):
        colors = {
            "PENDING": "gray",
            "DOWNLOADING": "blue",
            "DOWNLOADED": "blue",
            "CORRECTING": "orange",
            "CORRECTED": "orange",
            "CALCULATING": "orange",
            "COMPLETE": "green",
            "FAILED": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {};">{}</span>', color, obj.get_status_display()
        )

    status_display.short_description = "Status"

    def has_files(self, obj):
        raw = "✓" if obj.has_raw else "✗"
        corrected = "✓" if obj.has_corrected else "✗"
        return f"Raw: {raw}, Corrected: {corrected}"

    has_files.short_description = "Files"

    def mean_display(self, obj):
        if obj.mean_value:
            return f"{obj.mean_value:.6f}"
        return "—"

    mean_display.short_description = "Mean"
