"""
Models for bias correction.
Stores trained correction models and calibration history.
"""

from django.db import models
from django.core.validators import MinValueValidator

from air_quality.constants import Pollutant


class CorrectionModel(models.Model):
    """
    Trained bias correction model for a pollutant.
    Stores model coefficients and performance metrics.
    """

    MODEL_TYPE_CHOICES = [
        ("GWR", "Geographically Weighted Regression"),
        ("LINEAR", "Linear Regression"),
        ("ENSEMBLE", "Ensemble"),
    ]

    STATUS_CHOICES = [
        ("TRAINING", "Training"),
        ("ACTIVE", "Active"),
        ("ARCHIVED", "Archived"),
        ("FAILED", "Failed"),
    ]

    pollutant = models.CharField(
        max_length=10,
        choices=[(p.value, p.value) for p in Pollutant],
        db_index=True,
    )

    model_type = models.CharField(
        max_length=20,
        choices=MODEL_TYPE_CHOICES,
        default="GWR",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="TRAINING",
    )

    # Training parameters
    training_start_date = models.DateField(
        help_text="Start date of training data period"
    )
    training_end_date = models.DateField(help_text="End date of training data period")
    training_samples = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of training samples used",
    )
    training_stations = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of ground stations used",
    )

    # GWR specific parameters
    bandwidth = models.FloatField(
        null=True, blank=True, help_text="GWR bandwidth parameter (adaptive or fixed)"
    )
    kernel = models.CharField(
        max_length=20, default="bisquare", help_text="GWR kernel function"
    )

    # Model file storage
    model_file = models.CharField(
        max_length=500, blank=True, help_text="Path to serialized model file"
    )

    # Performance metrics
    r_squared = models.FloatField(
        null=True, blank=True, help_text="Coefficient of determination (R²)"
    )
    rmse = models.FloatField(null=True, blank=True, help_text="Root Mean Square Error")
    mae = models.FloatField(null=True, blank=True, help_text="Mean Absolute Error")
    bias = models.FloatField(null=True, blank=True, help_text="Mean Bias")

    # Cross-validation metrics
    cv_r_squared = models.FloatField(
        null=True, blank=True, help_text="Cross-validation R²"
    )
    cv_rmse = models.FloatField(
        null=True, blank=True, help_text="Cross-validation RMSE"
    )

    # Spatial metrics
    local_r_squared_min = models.FloatField(
        null=True, blank=True, help_text="Minimum local R² (GWR only)"
    )
    local_r_squared_max = models.FloatField(
        null=True, blank=True, help_text="Maximum local R² (GWR only)"
    )
    local_r_squared_mean = models.FloatField(
        null=True, blank=True, help_text="Mean local R² (GWR only)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Is this the currently active model for the pollutant?
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the active model for predictions",
    )

    # Additional metadata
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pollutant", "status"]),
            models.Index(fields=["pollutant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.pollutant} {self.model_type} ({self.created_at.date()})"

    def save(self, *args, **kwargs):
        # Ensure only one active model per pollutant
        if self.is_active:
            CorrectionModel.objects.filter(
                pollutant=self.pollutant, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_model(cls, pollutant: str) -> "CorrectionModel":
        """Get the currently active model for a pollutant."""
        return cls.objects.filter(
            pollutant=pollutant, is_active=True, status="ACTIVE"
        ).first()


class CalibrationPoint(models.Model):
    """
    Individual calibration data point.
    Links ground readings to satellite values for training.
    """

    correction_model = models.ForeignKey(
        CorrectionModel,
        on_delete=models.CASCADE,
        related_name="calibration_points",
    )

    station = models.ForeignKey(
        "air_quality.GroundStation",
        on_delete=models.CASCADE,
        related_name="calibration_points",
    )

    date = models.DateField(db_index=True)

    # Values
    ground_value = models.FloatField(help_text="Ground station measurement")
    satellite_value = models.FloatField(
        help_text="Satellite-derived value at station location"
    )
    corrected_value = models.FloatField(
        null=True, blank=True, help_text="Model-predicted corrected value"
    )

    # Residual analysis
    residual = models.FloatField(
        null=True, blank=True, help_text="Prediction residual (ground - corrected)"
    )

    # GWR local coefficients
    local_intercept = models.FloatField(
        null=True, blank=True, help_text="Local intercept coefficient"
    )
    local_slope = models.FloatField(
        null=True, blank=True, help_text="Local slope coefficient"
    )
    local_r_squared = models.FloatField(null=True, blank=True, help_text="Local R²")

    class Meta:
        unique_together = ["correction_model", "station", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["correction_model", "date"]),
        ]

    def __str__(self):
        return f"{self.station.name} - {self.date}"


class CorrectionRun(models.Model):
    """
    Record of a correction run applying a model to a raster.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("RUNNING", "Running"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    correction_model = models.ForeignKey(
        CorrectionModel,
        on_delete=models.CASCADE,
        related_name="correction_runs",
    )

    raster = models.ForeignKey(
        "air_quality.PollutantRaster",
        on_delete=models.CASCADE,
        related_name="correction_runs",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    # Execution details
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Output
    output_file = models.CharField(
        max_length=500, blank=True, help_text="Path to corrected raster file"
    )

    # Error handling
    error_message = models.TextField(blank=True)

    # Statistics of corrected raster
    stats = models.JSONField(
        default=dict,
        blank=True,
        help_text="Statistics of corrected raster (min, max, mean, etc.)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["correction_model", "raster"]

    def __str__(self):
        return f"{self.raster} - {self.status}"
