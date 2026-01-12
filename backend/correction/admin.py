"""
Admin configuration for correction app.
"""

from django.contrib import admin
from .models import CorrectionModel, CalibrationPoint, CorrectionRun


@admin.register(CorrectionModel)
class CorrectionModelAdmin(admin.ModelAdmin):
    list_display = [
        "pollutant",
        "model_type",
        "status",
        "is_active",
        "training_samples",
        "training_stations",
        "r_squared",
        "rmse",
        "created_at",
    ]
    list_filter = ["pollutant", "model_type", "status", "is_active"]
    search_fields = ["pollutant", "notes"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "r_squared",
        "rmse",
        "mae",
        "bias",
        "cv_r_squared",
        "cv_rmse",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("pollutant", "model_type", "status", "is_active")},
        ),
        (
            "Training Parameters",
            {
                "fields": (
                    "training_start_date",
                    "training_end_date",
                    "training_samples",
                    "training_stations",
                    "bandwidth",
                    "kernel",
                )
            },
        ),
        ("Model Storage", {"fields": ("model_file",)}),
        (
            "Performance Metrics",
            {
                "fields": (
                    "r_squared",
                    "rmse",
                    "mae",
                    "bias",
                    "cv_r_squared",
                    "cv_rmse",
                )
            },
        ),
        (
            "Spatial Metrics (GWR)",
            {
                "fields": (
                    "local_r_squared_min",
                    "local_r_squared_max",
                    "local_r_squared_mean",
                ),
                "classes": ["collapse"],
            },
        ),
        ("Metadata", {"fields": ("notes", "created_at", "updated_at")}),
    )

    actions = ["activate_model", "archive_model"]

    @admin.action(description="Activate selected models")
    def activate_model(self, request, queryset):
        for model in queryset:
            model.is_active = True
            model.status = "ACTIVE"
            model.save()

    @admin.action(description="Archive selected models")
    def archive_model(self, request, queryset):
        queryset.update(status="ARCHIVED", is_active=False)


@admin.register(CalibrationPoint)
class CalibrationPointAdmin(admin.ModelAdmin):
    list_display = [
        "station",
        "date",
        "ground_value",
        "satellite_value",
        "corrected_value",
        "residual",
    ]
    list_filter = ["correction_model__pollutant", "date"]
    search_fields = ["station__name"]
    raw_id_fields = ["correction_model", "station"]


@admin.register(CorrectionRun)
class CorrectionRunAdmin(admin.ModelAdmin):
    list_display = [
        "raster",
        "correction_model",
        "status",
        "started_at",
        "completed_at",
        "duration_seconds",
    ]
    list_filter = ["status", "correction_model__pollutant"]
    search_fields = ["raster__pollutant"]
    raw_id_fields = ["correction_model", "raster"]
    readonly_fields = [
        "created_at",
        "started_at",
        "completed_at",
        "duration_seconds",
        "stats",
    ]
