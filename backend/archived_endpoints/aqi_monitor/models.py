"""
AQI Monitor Models - Data Freshness Tracking
=============================================

Lightweight models for tracking data update status.
Actual air quality data models remain in the legacy air_quality app
until full migration is complete.
"""

from django.db import models
from django.utils import timezone
from apps.core.models import StatusTrackingModel


class DataFreshness(StatusTrackingModel):
    """
    Tracks the freshness and availability of external data sources.
    
    Used to monitor:
    - Latest Sentinel-5P imagery availability
    - OpenAQ data sync status
    - WorldPop data versions
    - GEE service health
    """
    
    class DataSourceChoices(models.TextChoices):
        SENTINEL5P_NO2 = 'S5P_NO2', 'Sentinel-5P NO2'
        WORLDPOP = 'WORLDPOP', 'WorldPop Population'
        OPENAQ_LOCAL = 'OPENAQ_LOCAL', 'OpenAQ Local Data'
        GEE_SERVICE = 'GEE_SERVICE', 'Google Earth Engine Service'
        RISK_CALCULATION = 'RISK_CALC', 'Risk Map Calculation'
    
    source = models.CharField(
        max_length=20,
        choices=DataSourceChoices.choices,
        unique=True,
        db_index=True
    )
    
    last_available_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Latest data timestamp available from source"
    )
    
    last_successful_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time data was successfully retrieved"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional source-specific information"
    )
    
    is_healthy = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether the data source is currently operational"
    )
    
    class Meta:
        verbose_name = 'Data Freshness Status'
        verbose_name_plural = 'Data Freshness Statuses'
        ordering = ['-last_check']
    
    def __str__(self) -> str:
        return f"{self.get_source_display()} - {self.status}"
    
    @classmethod
    def get_or_create_source(cls, source: str) -> 'DataFreshness':
        """
        Get or create a data freshness record for a source.
        
        Args:
            source: DataSourceChoices value
            
        Returns:
            DataFreshness instance
        """
        obj, created = cls.objects.get_or_create(
            source=source,
            defaults={
                'status': cls.StatusChoices.PENDING,
                'is_healthy': True
            }
        )
        return obj
    
    def update_availability(
        self,
        available_date: timezone.datetime,
        success: bool = True,
        **metadata
    ) -> None:
        """
        Update data availability information.
        
        Args:
            available_date: Latest data timestamp from source
            success: Whether the check was successful
            **metadata: Additional metadata to store
        """
        self.last_available_date = available_date
        self.last_check = timezone.now()
        
        if success:
            self.last_successful_sync = timezone.now()
            self.mark_success()
            self.is_healthy = True
        else:
            self.is_healthy = False
        
        # Merge metadata
        self.metadata.update(metadata)
        
        self.save(update_fields=[
            'last_available_date',
            'last_check',
            'last_successful_sync',
            'status',
            'status_message',
            'is_healthy',
            'metadata',
            'updated_at'
        ])
    
    def is_stale(self, max_age_hours: int = 24) -> bool:
        """
        Check if data is considered stale.
        
        Args:
            max_age_hours: Maximum acceptable age in hours
            
        Returns:
            True if data is older than max_age_hours
        """
        if not self.last_available_date:
            return True
        
        age = timezone.now() - self.last_available_date
        return age.total_seconds() > (max_age_hours * 3600)
