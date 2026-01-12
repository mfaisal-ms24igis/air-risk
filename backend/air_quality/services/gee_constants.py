"""
Satellite data constants for Google Earth Engine integration.

Defines collection IDs, band names, quality flags, and processing parameters
for various satellite datasets used in air quality monitoring.
"""

from enum import Enum
from typing import Dict, List, Any, NamedTuple


# =============================================================================
# GEE COLLECTION IDENTIFIERS
# =============================================================================

class SatelliteCollection(str, Enum):
    """
    Google Earth Engine collection identifiers for air quality datasets.
    """
    
    # Sentinel-5P TROPOMI (Tropospheric Monitoring Instrument)
    S5P_NO2_OFFL = "COPERNICUS/S5P/OFFL/L3_NO2"
    S5P_NO2_NRTI = "COPERNICUS/S5P/NRTI/L3_NO2"
    S5P_SO2_OFFL = "COPERNICUS/S5P/OFFL/L3_SO2"
    S5P_CO_OFFL = "COPERNICUS/S5P/OFFL/L3_CO"
    S5P_O3_OFFL = "COPERNICUS/S5P/OFFL/L3_O3"
    S5P_HCHO_OFFL = "COPERNICUS/S5P/OFFL/L3_HCHO"
    S5P_AER_AI = "COPERNICUS/S5P/OFFL/L3_AER_AI"
    S5P_CH4_OFFL = "COPERNICUS/S5P/OFFL/L3_CH4"
    S5P_CLOUD = "COPERNICUS/S5P/OFFL/L3_CLOUD"
    
    # MODIS (Moderate Resolution Imaging Spectroradiometer)
    MODIS_AOD_TERRA = "MODIS/061/MOD04_L2"  # Terra
    MODIS_AOD_AQUA = "MODIS/061/MYD04_L2"   # Aqua
    MODIS_MAIAC = "MODIS/061/MCD19A2_GRANULES"  # MAIAC AOD
    
    # Sentinel-2 (for land/urban masking)
    S2_SR = "COPERNICUS/S2_SR_HARMONIZED"
    
    # ERA5 Reanalysis (meteorology)
    ERA5_HOURLY = "ECMWF/ERA5/HOURLY"
    ERA5_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
    
    # Land Cover
    ESA_WORLDCOVER = "ESA/WorldCover/v200"
    MODIS_LAND_COVER = "MODIS/061/MCD12Q1"
    
    # Population
    WORLDPOP = "WorldPop/GP/100m/pop"


# =============================================================================
# BAND CONFIGURATIONS
# =============================================================================

class BandConfig(NamedTuple):
    """Configuration for a satellite band."""
    name: str
    description: str
    unit: str
    scale_factor: float = 1.0
    valid_range: tuple = (None, None)
    fill_value: float = None


# Sentinel-5P NO2 bands
S5P_NO2_BANDS: Dict[str, BandConfig] = {
    "tropospheric": BandConfig(
        name="tropospheric_NO2_column_number_density",
        description="Tropospheric NO2 column density",
        unit="mol/m²",
        scale_factor=1.0,
        valid_range=(0, 0.001),
    ),
    "stratospheric": BandConfig(
        name="stratospheric_NO2_column_number_density",
        description="Stratospheric NO2 column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "total": BandConfig(
        name="NO2_column_number_density",
        description="Total NO2 column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "qa": BandConfig(
        name="qa_value",
        description="Quality assurance value (0-1)",
        unit="",
        valid_range=(0, 1),
    ),
    "cloud_fraction": BandConfig(
        name="cloud_fraction",
        description="Effective cloud fraction",
        unit="",
        valid_range=(0, 1),
    ),
}

# Sentinel-5P SO2 bands
S5P_SO2_BANDS: Dict[str, BandConfig] = {
    "total": BandConfig(
        name="SO2_column_number_density",
        description="Total SO2 column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "pbl": BandConfig(
        name="SO2_column_number_density_amf",
        description="SO2 column with AMF correction",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "qa": BandConfig(
        name="qa_value",
        description="Quality assurance value",
        unit="",
        valid_range=(0, 1),
    ),
}

# Sentinel-5P CO bands
S5P_CO_BANDS: Dict[str, BandConfig] = {
    "total": BandConfig(
        name="CO_column_number_density",
        description="Total CO column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "h2o": BandConfig(
        name="H2O_column_number_density",
        description="Water vapor column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "qa": BandConfig(
        name="qa_value",
        description="Quality assurance value",
        unit="",
        valid_range=(0, 1),
    ),
}

# Sentinel-5P O3 bands
S5P_O3_BANDS: Dict[str, BandConfig] = {
    "total": BandConfig(
        name="O3_column_number_density",
        description="Total O3 column density",
        unit="mol/m²",
        scale_factor=1.0,
    ),
    "qa": BandConfig(
        name="qa_value",
        description="Quality assurance value",
        unit="",
        valid_range=(0, 1),
    ),
}

# Sentinel-5P Aerosol Index bands
S5P_AER_AI_BANDS: Dict[str, BandConfig] = {
    "absorbing_ai_340_380": BandConfig(
        name="absorbing_aerosol_index",
        description="UV Aerosol Index (340/380nm)",
        unit="",
        scale_factor=1.0,
    ),
    "qa": BandConfig(
        name="qa_value",
        description="Quality assurance value",
        unit="",
        valid_range=(0, 1),
    ),
}

# MODIS MAIAC AOD bands
MODIS_MAIAC_BANDS: Dict[str, BandConfig] = {
    "aod_047": BandConfig(
        name="Optical_Depth_047",
        description="AOD at 0.47 µm (Blue)",
        unit="",
        scale_factor=0.001,
        valid_range=(0, 5),
    ),
    "aod_055": BandConfig(
        name="Optical_Depth_055",
        description="AOD at 0.55 µm (Green)",
        unit="",
        scale_factor=0.001,
        valid_range=(0, 5),
    ),
    "qa": BandConfig(
        name="AOD_QA",
        description="AOD Quality Assurance",
        unit="",
    ),
}


# =============================================================================
# QUALITY FILTERS
# =============================================================================

class QualityFilter(NamedTuple):
    """Quality filter configuration."""
    min_qa: float
    max_cloud: float
    description: str


# Quality filter presets
QUALITY_PRESETS: Dict[str, QualityFilter] = {
    "strict": QualityFilter(
        min_qa=0.75,
        max_cloud=0.3,
        description="High quality only (>75% QA, <30% cloud)",
    ),
    "moderate": QualityFilter(
        min_qa=0.5,
        max_cloud=0.5,
        description="Moderate quality (>50% QA, <50% cloud)",
    ),
    "relaxed": QualityFilter(
        min_qa=0.3,
        max_cloud=0.7,
        description="Relaxed quality (>30% QA, <70% cloud)",
    ),
    "all": QualityFilter(
        min_qa=0.0,
        max_cloud=1.0,
        description="No quality filter applied",
    ),
}


# =============================================================================
# SPATIAL CONFIGURATIONS
# =============================================================================

# Pakistan administrative boundary
PAKISTAN_BBOX: Dict[str, float] = {
    "west": 60.87,
    "south": 23.63,
    "east": 77.84,
    "north": 37.08,
}

# Major city bounding boxes (for focused analysis)
CITY_BBOXES: Dict[str, Dict[str, float]] = {
    "karachi": {"west": 66.80, "south": 24.75, "east": 67.50, "north": 25.10},
    "lahore": {"west": 74.15, "south": 31.35, "east": 74.55, "north": 31.70},
    "islamabad": {"west": 72.75, "south": 33.55, "east": 73.30, "north": 33.85},
    "peshawar": {"west": 71.45, "south": 33.90, "east": 71.70, "north": 34.15},
    "quetta": {"west": 66.85, "south": 30.10, "east": 67.10, "north": 30.35},
    "multan": {"west": 71.35, "south": 30.05, "east": 71.65, "north": 30.35},
    "faisalabad": {"west": 73.00, "south": 31.30, "east": 73.30, "north": 31.55},
}

# Default spatial resolution (meters)
DEFAULT_RESOLUTION: Dict[str, int] = {
    "s5p": 1113,        # ~1km at equator (Sentinel-5P native)
    "modis": 1000,      # 1km MODIS
    "maiac": 1000,      # 1km MAIAC
    "sentinel2": 10,    # 10m Sentinel-2
    "export": 1000,     # Default export resolution
}


# =============================================================================
# TEMPORAL CONFIGURATIONS
# =============================================================================

# Data availability start dates
DATA_AVAILABILITY: Dict[str, str] = {
    "S5P_NO2": "2018-06-28",
    "S5P_SO2": "2018-12-05",
    "S5P_CO": "2018-06-28",
    "S5P_O3": "2018-06-28",
    "S5P_AER_AI": "2018-07-04",
    "MODIS_MAIAC": "2000-02-24",
    "ERA5": "1979-01-01",
}

# Typical overpass times (local) for Pakistan
OVERPASS_TIMES: Dict[str, str] = {
    "sentinel5p": "13:30",  # Afternoon orbit
    "terra": "10:30",       # Morning
    "aqua": "13:30",        # Afternoon
}


# =============================================================================
# UNIT CONVERSIONS
# =============================================================================

# Conversion factors from satellite units to standard units
SATELLITE_UNIT_CONVERSIONS: Dict[str, Dict[str, float]] = {
    "NO2": {
        # mol/m² to µg/m³ (assuming 1km boundary layer)
        # NO2 molecular weight: 46.01 g/mol
        # Factor: (mol/m²) * (46.01 g/mol) * (1e6 µg/g) / (1e3 m) = 46.01e3 µg/m³
        "mol_m2_to_ug_m3": 46010.0,
        # mol/m² to molecules/cm²
        "mol_m2_to_molec_cm2": 6.022e19,
    },
    "SO2": {
        # SO2 molecular weight: 64.07 g/mol
        "mol_m2_to_ug_m3": 64070.0,
        "mol_m2_to_molec_cm2": 6.022e19,
    },
    "CO": {
        # CO molecular weight: 28.01 g/mol
        "mol_m2_to_ug_m3": 28010.0,
        "mol_m2_to_molec_cm2": 6.022e19,
    },
    "O3": {
        # O3 molecular weight: 48.00 g/mol
        "mol_m2_to_ug_m3": 48000.0,
        "mol_m2_to_DU": 2241.0,  # Dobson Units
    },
}


# =============================================================================
# REDUCER CONFIGURATIONS
# =============================================================================

class ReducerType(str, Enum):
    """Types of spatial/temporal reducers."""
    MEAN = "mean"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"
    SUM = "sum"
    STDDEV = "stdDev"
    PERCENTILE = "percentile"


# Default aggregation methods by product
DEFAULT_REDUCERS: Dict[str, ReducerType] = {
    "NO2": ReducerType.MEAN,
    "SO2": ReducerType.MEAN,
    "CO": ReducerType.MEAN,
    "O3": ReducerType.MEAN,
    "AOD": ReducerType.MEAN,
    "AER_AI": ReducerType.MEDIAN,
}


# =============================================================================
# EXPORT CONFIGURATIONS
# =============================================================================

# GEE export settings
EXPORT_CONFIG: Dict[str, Any] = {
    "max_pixels": 1e10,
    "file_format": "GeoTIFF",
    "crs": "EPSG:4326",
    "default_scale": 1000,
    "cloud_optimized": True,
}

# GCS bucket for exports (if using cloud storage)
GCS_BUCKET: str = "air-quality-gee-exports"
