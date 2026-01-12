"""
Abstract Base Models
====================

Provides reusable abstract models for common patterns across apps.
"""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract model providing automatic timestamp tracking.
    
    Adds created_at and updated_at fields to any model that inherits it.
    """
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class StatusTrackingModel(TimeStampedModel):
    """
    Abstract model for tracking operational status.
    
    Useful for system health checks, data freshness, and monitoring.
    """
    
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        STALE = 'STALE', 'Stale'
    
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True
    )
    
    status_message = models.TextField(blank=True)
    last_check = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        abstract = True
    
    def mark_success(self, message: str = "") -> None:
        """Mark operation as successful."""
        self.status = self.StatusChoices.SUCCESS
        self.status_message = message
        self.last_check = timezone.now()
        self.save(update_fields=['status', 'status_message', 'last_check', 'updated_at'])
    
    def mark_failed(self, message: str) -> None:
        """Mark operation as failed."""
        self.status = self.StatusChoices.FAILED
        self.status_message = message
        self.last_check = timezone.now()
        self.save(update_fields=['status', 'status_message', 'last_check', 'updated_at'])
    
    def mark_processing(self, message: str = "") -> None:
        """Mark operation as in progress."""
        self.status = self.StatusChoices.PROCESSING
        self.status_message = message
        self.last_check = timezone.now()
        self.save(update_fields=['status', 'status_message', 'last_check', 'updated_at'])
