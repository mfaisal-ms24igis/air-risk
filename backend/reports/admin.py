"""
Admin configuration for reports app.
"""

from django.contrib import admin
from .models import Report, ReportSubscription, ReportTemplate


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "report_type",
        "user",
        "status",
        "format",
        "start_date",
        "end_date",
        "created_at",
    ]
    list_filter = ["report_type", "status", "format", "created_at"]
    search_fields = ["title", "user__email"]
    raw_id_fields = ["user", "district"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "file_size",
    ]

    fieldsets = (
        ("Basic", {"fields": ("user", "title", "report_type", "format")}),
        (
            "Parameters",
            {
                "fields": (
                    "pollutants",
                    "start_date",
                    "end_date",
                    "district",
                    "province",
                )
            },
        ),
        ("Status", {"fields": ("status", "error_message")}),
        ("File", {"fields": ("file_path", "file_size", "expires_at")}),
        (
            "Timing",
            {
                "fields": ("started_at", "completed_at", "created_at", "updated_at"),
                "classes": ["collapse"],
            },
        ),
    )


@admin.register(ReportSubscription)
class ReportSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "name",
        "frequency",
        "report_type",
        "is_active",
        "last_sent_at",
        "send_count",
    ]
    list_filter = ["frequency", "report_type", "is_active"]
    search_fields = ["user__email", "name"]
    raw_id_fields = ["user", "district"]
    readonly_fields = ["last_sent_at", "send_count", "created_at", "updated_at"]


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "report_type",
        "page_size",
        "orientation",
        "is_active",
        "updated_at",
    ]
    list_filter = ["report_type", "is_active"]
    search_fields = ["name"]
