"""
AQI Monitor Django App Configuration
"""
from django.apps import AppConfig


class AqiMonitorConfig(AppConfig):
    """Configuration for the AQI Monitor service app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.aqi_monitor'
    verbose_name = 'AQI Monitor Service'
    
    def ready(self):
        """Import signals and perform startup tasks."""
        # Import signals if needed
        # from . import signals  # noqa
        pass
