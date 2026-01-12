"""
GeoServer configuration package.
"""

from .sld_templates import (
    get_aqi_sld,
    get_concentration_sld,
    get_district_style,
    get_station_style,
    get_hotspot_style,
    POLLUTANT_THRESHOLDS,
)
from .mosaic_config import (
    get_indexer_properties,
    get_timeregex_properties,
    get_datastore_properties,
    get_coverage_properties,
    generate_mosaic_config,
    get_wms_layer_config,
)

__all__ = [
    "get_aqi_sld",
    "get_concentration_sld",
    "get_district_style",
    "get_station_style",
    "get_hotspot_style",
    "POLLUTANT_THRESHOLDS",
    "get_indexer_properties",
    "get_timeregex_properties",
    "get_datastore_properties",
    "get_coverage_properties",
    "generate_mosaic_config",
    "get_wms_layer_config",
]
