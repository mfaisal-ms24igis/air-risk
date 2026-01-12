"""
Admin configuration for exposure app.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import DistrictExposure, Hotspot, ProvinceExposure, NationalExposure


@admin.register(DistrictExposure)
class DistrictExposureAdmin(admin.ModelAdmin):
    list_display = [
        "district",
        "pollutant",
        "date",
        "total_population",
        "concentration_mean",
        "aqi_mean",
        "exposure_index",
        "rank",
    ]
    list_filter = ["pollutant", "date", "district__province"]
    search_fields = ["district__name"]
    raw_id_fields = ["district"]
    date_hierarchy = "date"
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Basic", {"fields": ("district", "pollutant", "date")}),
        ("Population", {"fields": ("total_population",)}),
        (
            "Concentration",
            {
                "fields": (
                    "concentration_mean",
                    "concentration_min",
                    "concentration_max",
                    "concentration_std",
                )
            },
        ),
        ("AQI", {"fields": ("aqi_mean", "aqi_max")}),
        (
            "Population by Category",
            {
                "fields": (
                    "pop_good",
                    "pop_moderate",
                    "pop_usg",
                    "pop_unhealthy",
                    "pop_very_unhealthy",
                    "pop_hazardous",
                ),
                "classes": ["collapse"],
            },
        ),
        ("Scores", {"fields": ("exposure_index", "rank")}),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )


@admin.register(Hotspot)
class HotspotAdmin(GISModelAdmin):
    list_display = [
        "id",
        "pollutant",
        "date",
        "severity",
        "concentration_mean",
        "aqi_mean",
        "affected_population",
        "persistence_days",
    ]
    list_filter = ["pollutant", "severity", "date"]
    date_hierarchy = "date"
    readonly_fields = ["created_at"]
    filter_horizontal = ["affected_districts"]

    fieldsets = (
        ("Basic", {"fields": ("pollutant", "date", "severity")}),
        ("Location", {"fields": ("centroid", "geometry", "area_sq_km")}),
        (
            "Statistics",
            {
                "fields": (
                    "concentration_mean",
                    "concentration_max",
                    "aqi_mean",
                    "affected_population",
                )
            },
        ),
        ("Persistence", {"fields": ("persistence_days",)}),
        ("Affected Areas", {"fields": ("affected_districts",)}),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ["collapse"],
            },
        ),
    )


@admin.register(ProvinceExposure)
class ProvinceExposureAdmin(admin.ModelAdmin):
    list_display = [
        "province",
        "pollutant",
        "date",
        "total_population",
        "concentration_mean",
        "aqi_mean",
        "exposure_index",
        "rank",
    ]
    list_filter = ["pollutant", "date", "province"]
    date_hierarchy = "date"
    readonly_fields = ["created_at"]


@admin.register(NationalExposure)
class NationalExposureAdmin(admin.ModelAdmin):
    list_display = [
        "pollutant",
        "date",
        "total_population",
        "concentration_mean",
        "aqi_mean",
        "n_hotspots",
        "worst_district",
    ]
    list_filter = ["pollutant", "date"]
    date_hierarchy = "date"
    raw_id_fields = ["worst_district"]
    readonly_fields = ["created_at"]
