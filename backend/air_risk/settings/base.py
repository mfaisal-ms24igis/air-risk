"""
Base Django settings for air_risk project.
Common settings shared across all environments.
"""

import os
from pathlib import Path
from datetime import timedelta

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Environment variables
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

# Read .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# Optional GDAL / GEOS / PROJ library paths
# These are typically only needed on Windows development environments.
# When running inside containers, system packages provide the libraries.
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH", default=None)
PROJ_LIBRARY_PATH = env("PROJ_LIBRARY_PATH", default=None)

# Data directories
DATA_DIR = BASE_DIR / "data"
RASTER_DIR = DATA_DIR / "rasters"
GROUND_DATA_DIR = DATA_DIR / "ground"

# Ensure directories exist
RASTER_DIR.mkdir(parents=True, exist_ok=True)
GROUND_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Processing settings
OPENAQ_API_URL = "https://api.openaq.org/v3"
CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"
PROCESSING_TIMEOUT = 300  # seconds

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

# Validate SECRET_KEY in production
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("django-insecure")):
    import sys
    print(
        "\n" + "="*70 + "\n"
        "🔴 CRITICAL SECURITY ERROR\n"
        "SECRET_KEY is insecure! Production requires:\n"
        "  - At least 50 characters\n"
        "  - Random, unique value\n"
        "  - Never commit to version control\n"
        "Generate new key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'\n"
        + "="*70
    )
    sys.exit(1)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # JWT token blacklist
    "corsheaders",
    "django_filters",
    "django_q",  # Django-Q for background tasks
    "drf_yasg",
]

LOCAL_APPS = [
    # New service-oriented modules
    "apps.core",           # Shared utilities and base classes
    
    # Legacy apps (gradual migration in progress)
    "users",
    "air_quality",         # Models still used during transition
    "correction",
    "exposure",
    "reports",  # Required for location-based reports
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "air_risk.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "air_risk.wsgi.application"

# Database - PostGIS
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("POSTGRES_DB", default="air_risk"),
        "USER": env("POSTGRES_USER", default="air_risk_user"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="air_risk_pass"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
}

# Custom User Model
AUTH_USER_MODEL = "users.CustomUser"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    # Custom exception handler for standardized error responses
    "EXCEPTION_HANDLER": "air_risk.exceptions.custom_exception_handler",
    # Tier-based rate limiting
    "DEFAULT_THROTTLE_CLASSES": [
        "air_risk.throttling.TieredUserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Base scope (overridden by TieredUserRateThrottle per tier)
        "user": "60/minute",
        # Feature-specific throttles
        "premium_feature": "10/hour",
        "geometry": "30/hour",
    },
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=24),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# CORS Settings
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# DJANGO-Q CONFIGURATION (PostgreSQL ORM Broker - No Redis Required)
# =============================================================================
# Django-Q uses PostgreSQL as the task broker, eliminating Redis dependency
# Simpler architecture than Celery while meeting all requirements

Q_CLUSTER = {
    'name': 'air_risk_tasks',
    'workers': 4,
    'recycle': 500,
    'timeout': 600,  # 10 minutes
    'retry': 720,  # 12 minutes
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',  # Use Django ORM (PostgreSQL) as broker
    'sync': False,  # Run tasks asynchronously
    'poll': 10,  # Poll for new tasks every 10 seconds
    'save_limit': 250,  # Keep last 250 successful tasks
    'ack_failures': True,
    'max_attempts': 3,
    'catch_up': True,  # Run missed scheduled tasks
}

# Cache Configuration
# Use LocMemCache for local development without Redis
# Switch to RedisCache when Redis is available
REDIS_URL = env("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    # Fallback to local memory cache (no Redis required)
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# Email Configuration
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@airrisk.pk")

# GeoServer Configuration
GEOSERVER_URL = env("GEOSERVER_URL", default="http://geoserver:8080/geoserver")
GEOSERVER_ADMIN_USER = env("GEOSERVER_ADMIN_USER", default="admin")
GEOSERVER_ADMIN_PASSWORD = env("GEOSERVER_ADMIN_PASSWORD", default="geoserver")
GEOSERVER_WORKSPACE = env("GEOSERVER_WORKSPACE", default="air_risk")

# CDSE (Copernicus Data Space Ecosystem) Configuration
CDSE = {
    "CLIENT_ID": "cdse-public",
    "TOKEN_URL": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
    "API_BASE": "https://catalogue.dataspace.copernicus.eu/odata/v1",
    "USERNAME": env("CDSE_USERNAME"),
    "PASSWORD": env("CDSE_PASSWORD"),
}

# Legacy CDSE settings (for backward compatibility)
CDSE_CLIENT_ID = env("CDSE_CLIENT_ID", default="")
CDSE_CLIENT_SECRET = env("CDSE_CLIENT_SECRET", default="")
CDSE_TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CDSE_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
CDSE_CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0"

# OpenAQ Configuration
OPENAQ_API_KEY = env("OPENAQ_API_KEY", default="")
OPENAQ_API_URL = "https://api.openaq.org/v3"

# Data Paths
RASTER_DATA_PATH = Path(
    env("RASTER_DATA_PATH", default=str(BASE_DIR / "data" / "rasters"))
)
WORLDPOP_DATA_PATH = Path(
    env("WORLDPOP_DATA_PATH", default=str(BASE_DIR / "data" / "worldpop"))
)
DISTRICTS_DATA_PATH = Path(
    env("DISTRICTS_DATA_PATH", default=str(BASE_DIR / "data" / "districts"))
)

# Ensure data directories exist
for path in [RASTER_DATA_PATH, WORLDPOP_DATA_PATH, DISTRICTS_DATA_PATH]:
    path.mkdir(parents=True, exist_ok=True)

# Air Quality Configuration
POLLUTANTS = ["NO2", "SO2", "PM25", "CO", "O3"]
RASTER_RETENTION_DAYS = 90
GWR_STATION_THRESHOLD = 10  # Minimum stations for GWR, else fallback to linear

# Pakistan bounding box (for CDSE queries)
PAKISTAN_BBOX = [60.87, 23.69, 77.84, 37.08]  # [min_lon, min_lat, max_lon, max_lat]

# AQI Thresholds (US EPA standard)
AQI_BREAKPOINTS = {
    "NO2": {  # ppb
        "good": (0, 53),
        "moderate": (54, 100),
        "unhealthy_sensitive": (101, 360),
        "unhealthy": (361, 649),
        "very_unhealthy": (650, 1249),
        "hazardous": (1250, float("inf")),
    },
    "SO2": {  # ppb
        "good": (0, 35),
        "moderate": (36, 75),
        "unhealthy_sensitive": (76, 185),
        "unhealthy": (186, 304),
        "very_unhealthy": (305, 604),
        "hazardous": (605, float("inf")),
    },
    "PM25": {  # µg/m³
        "good": (0, 12),
        "moderate": (12.1, 35.4),
        "unhealthy_sensitive": (35.5, 55.4),
        "unhealthy": (55.5, 150.4),
        "very_unhealthy": (150.5, 250.4),
        "hazardous": (250.5, float("inf")),
    },
    "CO": {  # ppm
        "good": (0, 4.4),
        "moderate": (4.5, 9.4),
        "unhealthy_sensitive": (9.5, 12.4),
        "unhealthy": (12.5, 15.4),
        "very_unhealthy": (15.5, 30.4),
        "hazardous": (30.5, float("inf")),
    },
    "O3": {  # ppb
        "good": (0, 54),
        "moderate": (55, 70),
        "unhealthy_sensitive": (71, 85),
        "unhealthy": (86, 105),
        "very_unhealthy": (106, 200),
        "hazardous": (201, float("inf")),
    },
}

AQI_COLORS = {
    "good": "#00E400",
    "moderate": "#FFFF00",
    "unhealthy_sensitive": "#FF7E00",
    "unhealthy": "#FF0000",
    "very_unhealthy": "#8F3F97",
    "hazardous": "#7E0023",
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # New service-oriented modules
        "apps.core": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.aqi_monitor": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Legacy apps (still in use during migration)
        "air_quality": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "correction": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "exposure": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django_q": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# DJANGO-Q CONFIGURATION (PostgreSQL ORM Broker - No Redis)
# =============================================================================

Q_CLUSTER = {
    'name': 'air_risk_tasks',
    'workers': 4,
    'recycle': 500,
    'timeout': 600,  # 10 minutes
    'retry': 720,  # 12 minutes
    'queue_limit': 50,
    'bulk': 10,
    'orm': 'default',  # Use Django ORM (PostgreSQL) as broker
    'sync': False,  # Run tasks asynchronously (not synchronously)
    'poll': 10,  # Poll for new tasks every 10 seconds
    'save_limit': 250,  # Keep last 250 successful tasks
    'ack_failures': True,
    'max_attempts': 3,
    'attempt_count': 1,
    
    # Completely disable Redis-based features
    'redis': None,  # Explicitly disable Redis
    'monitor': None,  # Disable monitoring
    'sentry': None,  # Disable Sentry integration
}

# AI Service Settings
AI_API_BASE_URL = env("AI_API_BASE_URL", default="http://localhost:1234")
AI_MODEL = env("AI_MODEL", default="mistralai/mistral-7b-instruct-v0.3")
AI_API_TIMEOUT = env.int("AI_API_TIMEOUT", default=30)
