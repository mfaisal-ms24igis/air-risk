"""
Custom User model with location and preferences for air quality reporting.
"""

from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Extended user model with location and air quality preferences.
    """

    class SubscriptionTier(models.TextChoices):
        BASIC = "BASIC", "Basic"
        PREMIUM = "PREMIUM", "Premium"

    class ReportFrequency(models.TextChoices):
        NONE = "NONE", "No scheduled reports"
        DAILY = "DAILY", "Daily"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    # Subscription tier
    subscription_tier = models.CharField(
        max_length=10,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.BASIC,
        help_text="User subscription tier (BASIC or PREMIUM)",
    )

    premium_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Premium subscription expiry date (null for lifetime/basic)",
    )

    # Location fields
    home_location = models.PointField(
        null=True,
        blank=True,
        srid=4326,
        help_text="User home location for personalized exposure data",
    )

    preferred_district = models.ForeignKey(
        "air_quality.District",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_users",
        help_text="Preferred district for reports and alerts",
    )

    # Notification preferences
    email_verified = models.BooleanField(default=False)

    email_preferences = models.JSONField(
        default=dict, blank=True, help_text="Email notification preferences"
    )

    report_frequency = models.CharField(
        max_length=10,
        choices=ReportFrequency.choices,
        default=ReportFrequency.NONE,
        help_text="Frequency of scheduled exposure reports",
    )

    # Pollutants to track
    tracked_pollutants = models.JSONField(
        default=list,
        blank=True,
        help_text="List of pollutants to track: NO2, SO2, PM25, CO, O3",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email or self.username

    def save(self, *args, **kwargs):
        # Set default tracked pollutants if empty
        if not self.tracked_pollutants:
            self.tracked_pollutants = ["NO2", "PM25", "O3"]

        # Set default email preferences if empty
        if not self.email_preferences:
            self.email_preferences = {
                "exposure_alerts": True,
                "weekly_summary": True,
                "report_ready": True,
            }

        super().save(*args, **kwargs)

    def set_location(self, longitude: float, latitude: float):
        """Set user location from coordinates."""
        self.home_location = Point(longitude, latitude, srid=4326)
        self.save(update_fields=["home_location", "updated_at"])

    @property
    def location_coordinates(self):
        """Return location as (longitude, latitude) tuple."""
        if self.home_location:
            return (self.home_location.x, self.home_location.y)
        return None

    @property
    def has_location(self):
        """Check if user has set a location."""
        return self.home_location is not None

    @property
    def wants_daily_reports(self):
        return self.report_frequency == self.ReportFrequency.DAILY

    @property
    def wants_weekly_reports(self):
        return self.report_frequency == self.ReportFrequency.WEEKLY

    @property
    def wants_monthly_reports(self):
        return self.report_frequency == self.ReportFrequency.MONTHLY

    @property
    def is_premium(self):
        """Check if user has active premium subscription."""
        if self.subscription_tier == self.SubscriptionTier.BASIC:
            return False
        if self.subscription_tier == self.SubscriptionTier.PREMIUM:
            # Check expiry if set
            if self.premium_until is None:
                return True  # Lifetime premium
            return timezone.now() < self.premium_until
        return False

    @property
    def tier(self):
        """Return current active tier (checks expiry)."""
        return (
            self.SubscriptionTier.PREMIUM
            if self.is_premium
            else self.SubscriptionTier.BASIC
        )
