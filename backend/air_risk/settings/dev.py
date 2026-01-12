"""
Development settings for air_risk project.
"""

from .base import INSTALLED_APPS, LOGGING, MIDDLEWARE  # noqa: F401
from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]

# Debug toolbar
INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Debug toolbar settings
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

# Email backend for development (console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Logging - more verbose in development
LOGGING["loggers"]["air_quality"]["level"] = "DEBUG"
LOGGING["loggers"]["correction"]["level"] = "DEBUG"
LOGGING["loggers"]["exposure"]["level"] = "DEBUG"
