"""
Admin configuration for users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, GISModelAdmin):
    """
    Admin interface for CustomUser model with GIS support.
    """

    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "has_location_display",
        "preferred_district",
        "report_frequency",
        "is_active",
        "date_joined",
    ]

    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified",
        "report_frequency",
        "date_joined",
    ]

    search_fields = ["username", "email", "first_name", "last_name"]

    ordering = ["-date_joined"]

    fieldsets = UserAdmin.fieldsets + (
        (
            "Location",
            {
                "fields": ("home_location", "preferred_district"),
                "classes": ("collapse",),
            },
        ),
        (
            "Preferences",
            {
                "fields": (
                    "email_verified",
                    "email_preferences",
                    "report_frequency",
                    "tracked_pollutants",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Additional Info",
            {
                "fields": ("email", "first_name", "last_name"),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def has_location_display(self, obj):
        if obj.has_location:
            return format_html(
                '<span style="color: green;">✓</span> ({:.4f}, {:.4f})',
                obj.home_location.x,
                obj.home_location.y,
            )
        return format_html('<span style="color: gray;">—</span>')

    has_location_display.short_description = "Location"
    has_location_display.admin_order_field = "home_location"
