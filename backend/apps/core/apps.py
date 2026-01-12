"""
Core Django App Configuration
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core shared utilities app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core Utilities'
