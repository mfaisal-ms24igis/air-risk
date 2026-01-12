# Services module for air quality data processing
# NOTE: Use lazy loading to avoid circular imports and early Django initialization

from .cdse import CDSEClient, CDSEAuthError, CDSEDownloadError
from .openaq import OpenAQClient, OpenAQError
from .geoserver import GeoServerClient, GeoServerError
from .raster import (
    RasterManager,
    WorldPopReader,
    RasterError,
    ensure_cog,
    reproject_raster,
    read_raster_window,
    read_raster_at_points,
    get_raster_stats,
)
from .unit_converter import (
    UnitConverter,
    UnitConversionError,
    get_unit_converter,
)

# GEE Services - Lazy imports to avoid authentication on module load
# These are imported only when explicitly requested to prevent early GEE init
def get_gee_auth():
    """Get the GEE authentication manager (lazy import)."""
    from .gee_auth import get_gee_auth as _get_gee_auth
    return _get_gee_auth()

def get_tropomi_service():
    """Get the TROPOMI service singleton (lazy import)."""
    from .gee_tropomi import get_tropomi_service as _get_tropomi
    return _get_tropomi()

def get_modis_aod_service():
    """Get the MODIS AOD service singleton (lazy import)."""
    from .gee_modis import get_modis_aod_service as _get_modis
    return _get_modis()

def get_satellite_manager():
    """Get the satellite data manager singleton (lazy import)."""
    from .gee_manager import get_satellite_manager as _get_manager
    return _get_manager()

def initialize_gee(**kwargs):
    """Initialize Google Earth Engine (lazy import)."""
    from .gee_auth import initialize_gee as _init_gee
    return _init_gee(**kwargs)

# Alias for backwards compatibility
CDSEError = CDSEDownloadError

# Lazy-loaded singleton instances (initialized on first access)
_cdse_client = None
_openaq_client = None
_geoserver_client = None
_raster_manager = None
_worldpop_reader = None


def get_cdse_client() -> CDSEClient:
    """Get or create the CDSE client singleton."""
    global _cdse_client
    if _cdse_client is None:
        _cdse_client = CDSEClient()
    return _cdse_client


def get_openaq_client() -> OpenAQClient:
    """Get or create the OpenAQ client singleton."""
    global _openaq_client
    if _openaq_client is None:
        _openaq_client = OpenAQClient()
    return _openaq_client


def get_geoserver_client() -> GeoServerClient:
    """Get or create the GeoServer client singleton."""
    global _geoserver_client
    if _geoserver_client is None:
        _geoserver_client = GeoServerClient()
    return _geoserver_client


def get_raster_manager() -> RasterManager:
    """Get or create the raster manager singleton."""
    global _raster_manager
    if _raster_manager is None:
        _raster_manager = RasterManager()
    return _raster_manager


def get_worldpop_reader() -> WorldPopReader:
    """Get or create the WorldPop reader singleton."""
    global _worldpop_reader
    if _worldpop_reader is None:
        _worldpop_reader = WorldPopReader()
    return _worldpop_reader


# Property-based accessors for backwards compatibility
class _LazyClient:
    """Lazy-loading proxy for client singletons."""

    @property
    def cdse_client(self):
        return get_cdse_client()

    @property
    def openaq_client(self):
        return get_openaq_client()

    @property
    def geoserver_client(self):
        return get_geoserver_client()

    @property
    def raster_manager(self):
        return get_raster_manager()

    @property
    def worldpop_reader(self):
        return get_worldpop_reader()


_lazy = _LazyClient()


# For backwards compatibility - expose lazy accessors via module __getattr__
# This allows: `from air_quality.services import raster_manager` to work
# The actual value is resolved lazily when the attribute is accessed
def __getattr__(name: str):
    """Lazy module-level attribute access for backwards compatibility."""
    if name == "cdse_client":
        return get_cdse_client()
    elif name == "openaq_client":
        return get_openaq_client()
    elif name == "geoserver_client":
        return get_geoserver_client()
    elif name == "raster_manager":
        return get_raster_manager()
    elif name == "worldpop_reader":
        return get_worldpop_reader()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # CDSE
    "get_cdse_client",
    "CDSEClient",
    "CDSEError",
    "CDSEAuthError",
    "CDSEDownloadError",
    # OpenAQ
    "get_openaq_client",
    "OpenAQClient",
    "OpenAQError",
    # GeoServer
    "get_geoserver_client",
    "GeoServerClient",
    "GeoServerError",
    # Raster utilities
    "get_raster_manager",
    "get_worldpop_reader",
    "RasterManager",
    "WorldPopReader",
    "RasterError",
    "ensure_cog",
    "reproject_raster",
    "read_raster_window",
    "read_raster_at_points",
    "get_raster_stats",
    # Unit converter
    "get_unit_converter",
    "UnitConverter",
    "UnitConversionError",
    # GEE Services
    "get_gee_auth",
    "get_tropomi_service",
    "get_modis_aod_service",
    "get_satellite_manager",
    "initialize_gee",
]
