"""
Models for reports and subscriptions.
"""

from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings



class Report(models.Model):
    """
    Generated report record.
    """

    REPORT_TYPE_CHOICES = [
        ("DAILY", "Daily Summary"),
        ("WEEKLY", "Weekly Summary"),
        ("MONTHLY", "Monthly Summary"),
        ("DISTRICT", "District Detail"),
        ("LOCATION", "Location-Based Trend Analysis"),
        ("CUSTOM", "Custom Report"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("GENERATING", "Generating"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    FORMAT_CHOICES = [
        ("PDF", "PDF"),
        ("HTML", "HTML"),
        ("JSON", "JSON"),
    ]

    # User who requested the report (optional for automated reports)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )

    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default="DAILY",
    )

    title = models.CharField(max_length=200)

    # Report parameters
    pollutants = ArrayField(
        models.CharField(max_length=10),
        default=list,
        help_text="Pollutants included in report",
    )

    start_date = models.DateField()
    end_date = models.DateField()

    # Geographic scope
    district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )

    province = models.CharField(max_length=100, blank=True)

    # Location-based report parameters (for LOCATION type)
    location = models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Center point for location-based analysis",
    )

    radius_km = models.FloatField(
        null=True,
        blank=True,
        help_text="Search radius in kilometers for location-based reports",
    )

    # AI enhancement flag
    include_ai_insights = models.BooleanField(
        default=False,
        help_text="Include AI-generated health recommendations (premium feature)",
    )

    # Generation status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default="PDF",
    )

    # File storage
    file_path = models.CharField(
        max_length=500, blank=True, help_text="Path to generated report file"
    )

    file_size = models.BigIntegerField(
        null=True, blank=True, help_text="File size in bytes"
    )

    # Generation timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Django-Q task tracking
    task_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Django-Q task ID for async report generation"
    )

    # Error tracking
    error_message = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Expiration
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When the report file will be deleted"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.created_at.date()})"

    @property
    def is_ready(self) -> bool:
        return self.status == "COMPLETED" and self.file_path


class ReportSubscription(models.Model):
    """
    Subscription for automated report delivery.
    """

    FREQUENCY_CHOICES = [
        ("DAILY", "Daily"),
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_subscriptions",
    )

    name = models.CharField(max_length=100)

    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        default="DAILY",
    )

    # What to include
    report_type = models.CharField(
        max_length=20,
        choices=Report.REPORT_TYPE_CHOICES,
        default="DAILY",
    )

    pollutants = ArrayField(
        models.CharField(max_length=10),
        default=list,
    )

    # Geographic scope (use user's location if not specified)
    district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    province = models.CharField(max_length=100, blank=True)

    include_national = models.BooleanField(
        default=True, help_text="Include national summary"
    )

    # Delivery
    email_enabled = models.BooleanField(default=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Tracking
    last_sent_at = models.DateTimeField(null=True, blank=True)
    send_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.frequency} {self.report_type}"


class ReportTemplate(models.Model):
    """
    HTML template for report generation.
    """

    name = models.CharField(max_length=100, unique=True)

    report_type = models.CharField(
        max_length=20,
        choices=Report.REPORT_TYPE_CHOICES,
    )

    # Template content
    html_template = models.TextField(help_text="Jinja2/Django template for report body")

    css_styles = models.TextField(blank=True, help_text="CSS styles for PDF rendering")

    # Header/footer
    header_template = models.TextField(blank=True)
    footer_template = models.TextField(blank=True)

    # Page settings
    page_size = models.CharField(
        max_length=10, default="A4", help_text="PDF page size (A4, Letter, etc.)"
    )

    orientation = models.CharField(
        max_length=10,
        default="portrait",
        choices=[("portrait", "Portrait"), ("landscape", "Landscape")],
    )

    # Status
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["report_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.report_type})"
