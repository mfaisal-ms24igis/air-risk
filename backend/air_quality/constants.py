"""
Constants for air quality data processing.

Includes pollutant definitions, unit types, conversion factors, AQI breakpoints,
and API rate limiting constants.
"""

from enum import Enum
from typing import Dict, Tuple


# =============================================================================
# RATE LIMITING CONSTANTS
# =============================================================================

MAX_STATIONS_PER_MINUTE: int = 60
"""Maximum number of stations to query per minute (OpenAQ API limit)."""

MAX_STATIONS_PER_HOUR: int = 300
"""Maximum number of stations to query per hour (conservative limit)."""

MAX_ACTIVE_STATIONS: int = 60
"""Maximum number of stations to keep active for regular syncing."""


# =============================================================================
# COORDINATE BOUNDS (Pakistan Region)
# =============================================================================

COORDINATE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "latitude": (23.5, 37.5),   # Pakistan's lat range with buffer
    "longitude": (60.5, 77.5),  # Pakistan's lon range with buffer
}
"""Valid coordinate bounds for Pakistan region validation."""

# Global coordinate bounds for general validation
GLOBAL_COORDINATE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "latitude": (-90.0, 90.0),
    "longitude": (-180.0, 180.0),
}


# =============================================================================
# POLLUTANT DEFINITIONS
# =============================================================================

class Pollutant(str, Enum):
    """
    Supported pollutants for air quality monitoring.
    
    These map to both OpenAQ parameters and Sentinel-5P products.
    """

    NO2 = "NO2"
    SO2 = "SO2"
    PM25 = "PM25"
    PM10 = "PM10"
    PM1 = "PM1"
    CO = "CO"
    O3 = "O3"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return choices for Django model fields."""
        return [(p.value, p.name) for p in cls]

    @classmethod
    def values(cls) -> list[str]:
        """Return list of pollutant values."""
        return [p.value for p in cls]
    
    @classmethod
    def from_string(cls, value: str) -> "Pollutant | None":
        """
        Convert string to Pollutant enum, handling common variations.
        
        Args:
            value: String like 'pm25', 'PM2.5', 'pm2.5', etc.
            
        Returns:
            Pollutant enum or None if not recognized.
        """
        if not value:
            return None
        
        # Normalize: uppercase, remove dots and spaces
        normalized = value.upper().replace(".", "").replace(" ", "").replace("_", "")
        
        # Handle common variations
        mapping = {
            "PM25": cls.PM25,
            "PM2.5": cls.PM25,
            "PM10": cls.PM10,
            "PM1": cls.PM1,
            "NO2": cls.NO2,
            "SO2": cls.SO2,
            "CO": cls.CO,
            "O3": cls.O3,
            "OZONE": cls.O3,
        }
        
        return mapping.get(normalized)


# =============================================================================
# UNIT TYPES AND CONVERSIONS
# =============================================================================

class UnitType(str, Enum):
    """
    Measurement units for pollutant concentrations.
    
    OpenAQ data comes in various units that need normalization.
    """
    
    # Mass concentration units
    UG_M3 = "µg/m³"           # Micrograms per cubic meter (standard for PM)
    MG_M3 = "mg/m³"           # Milligrams per cubic meter
    NG_M3 = "ng/m³"           # Nanograms per cubic meter
    
    # Volume concentration units
    PPM = "ppm"               # Parts per million
    PPB = "ppb"               # Parts per billion
    PPMV = "ppmv"             # Parts per million by volume
    
    # Column density units (satellite data)
    MOL_M2 = "mol/m²"         # Moles per square meter
    MOLEC_CM2 = "molecules/cm²"  # Molecules per square centimeter
    DU = "DU"                 # Dobson Units (for O3 column)
    
    # Particle count units
    PARTICLES_CM3 = "particles/cm³"  # Particle count
    COUNT_CM3 = "#/cm³"       # Alternative particle count notation
    
    # Dimensionless
    INDEX = "index"           # For AQI or aerosol index
    UNITLESS = ""             # No unit
    
    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return choices for Django model fields."""
        return [(u.value, u.name) for u in cls]
    
    @classmethod
    def from_string(cls, value: str) -> "UnitType | None":
        """
        Convert string to UnitType enum, handling variations.
        
        Args:
            value: Unit string like 'ug/m3', 'µg/m³', 'ppb', etc.
            
        Returns:
            UnitType enum or None if not recognized.
        """
        if not value:
            return None
        
        # Normalize: lowercase, standardize unicode
        normalized = value.lower().strip()
        normalized = normalized.replace("μ", "µ")  # Greek mu to micro sign
        normalized = normalized.replace("u", "µ").replace("³", "3").replace("²", "2")
        
        mapping = {
            "µg/m3": cls.UG_M3,
            "µg/m³": cls.UG_M3,
            "ug/m3": cls.UG_M3,
            "mg/m3": cls.MG_M3,
            "mg/m³": cls.MG_M3,
            "ng/m3": cls.NG_M3,
            "ng/m³": cls.NG_M3,
            "ppm": cls.PPM,
            "ppb": cls.PPB,
            "ppmv": cls.PPMV,
            "mol/m2": cls.MOL_M2,
            "mol/m²": cls.MOL_M2,
            "molecules/cm2": cls.MOLEC_CM2,
            "molecules/cm²": cls.MOLEC_CM2,
            "du": cls.DU,
            "particles/cm3": cls.PARTICLES_CM3,
            "particles/cm³": cls.PARTICLES_CM3,
            "#/cm3": cls.COUNT_CM3,
            "#/cm³": cls.COUNT_CM3,
            "index": cls.INDEX,
            "": cls.UNITLESS,
        }
        
        return mapping.get(normalized)


# Standard units for each pollutant (normalization targets)
STANDARD_UNITS: Dict[Pollutant, UnitType] = {
    Pollutant.NO2: UnitType.UG_M3,    # Ground: µg/m³, Satellite: mol/m²
    Pollutant.SO2: UnitType.UG_M3,    # Ground: µg/m³, Satellite: mol/m²
    Pollutant.PM25: UnitType.UG_M3,   # Always µg/m³
    Pollutant.PM10: UnitType.UG_M3,   # Always µg/m³
    Pollutant.PM1: UnitType.UG_M3,    # Always µg/m³
    Pollutant.CO: UnitType.UG_M3,     # Ground: µg/m³ or ppm, Satellite: mol/m²
    Pollutant.O3: UnitType.UG_M3,     # Ground: µg/m³ or ppb, Satellite: mol/m² or DU
}

# Molecular weights for gas conversions (g/mol)
MOLECULAR_WEIGHTS: Dict[Pollutant, float] = {
    Pollutant.NO2: 46.0055,
    Pollutant.SO2: 64.066,
    Pollutant.CO: 28.0101,
    Pollutant.O3: 47.9982,
}

# Standard temperature and pressure for gas conversions
STANDARD_TEMPERATURE_K: float = 298.15  # 25°C in Kelvin
STANDARD_PRESSURE_PA: float = 101325.0  # 1 atm in Pascals
MOLAR_VOLUME_L: float = 24.45  # Liters per mole at STP

# Unit conversion factors to standard units (µg/m³)
# Format: (from_unit, to_unit, pollutant) -> factor or None if pollutant-specific
UNIT_CONVERSION_FACTORS: Dict[Tuple[UnitType, UnitType], float | None] = {
    # Mass concentration conversions (pollutant-independent)
    (UnitType.MG_M3, UnitType.UG_M3): 1000.0,
    (UnitType.NG_M3, UnitType.UG_M3): 0.001,
    (UnitType.UG_M3, UnitType.MG_M3): 0.001,
    (UnitType.UG_M3, UnitType.NG_M3): 1000.0,
    
    # PPB/PPM conversions require molecular weight (pollutant-dependent)
    # These are markers - actual conversion uses molecular weight
    (UnitType.PPB, UnitType.UG_M3): None,  # Requires MW
    (UnitType.PPM, UnitType.UG_M3): None,  # Requires MW
    (UnitType.UG_M3, UnitType.PPB): None,  # Requires MW
    (UnitType.UG_M3, UnitType.PPM): None,  # Requires MW
    
    # PPB <-> PPM
    (UnitType.PPB, UnitType.PPM): 0.001,
    (UnitType.PPM, UnitType.PPB): 1000.0,
}


# CDSE (Copernicus Data Space Ecosystem) band names for Sentinel-5P
CDSE_BAND_NAMES = {
    Pollutant.NO2: "tropospheric_NO2_column_number_density",
    Pollutant.SO2: "SO2_column_number_density",
    Pollutant.CO: "CO_column_number_density",
    Pollutant.O3: "O3_column_number_density",
    Pollutant.PM25: "aerosol_index_354_388",  # UV Aerosol Index for PM2.5 proxy
}


# =============================================================================
# AQI CATEGORIES AND BREAKPOINTS (US EPA Standard)
# =============================================================================
# Reference: https://www.airnow.gov/aqi/aqi-basics/
# The AQI is divided into six categories, each corresponding to a different 
# level of health concern.
# =============================================================================

class AQICategory(str, Enum):
    """
    Air Quality Index categories (US EPA Standard).
    
    Category Number | AQI Range | Descriptor
    1               | 0-50      | Good
    2               | 51-100    | Moderate  
    3               | 101-150   | Unhealthy for Sensitive Groups
    4               | 151-200   | Unhealthy
    5               | 201-300   | Very Unhealthy
    6               | 301-500   | Hazardous
    """

    GOOD = "good"
    MODERATE = "moderate"
    UNHEALTHY_SENSITIVE = "unhealthy_sensitive"
    UNHEALTHY = "unhealthy"
    VERY_UNHEALTHY = "very_unhealthy"
    HAZARDOUS = "hazardous"

    @classmethod
    def choices(cls):
        return [(c.value, c.name.replace("_", " ").title()) for c in cls]
    
    @classmethod
    def from_aqi(cls, aqi_value: float) -> "AQICategory":
        """Get the category for a given AQI value."""
        if aqi_value <= 50:
            return cls.GOOD
        elif aqi_value <= 100:
            return cls.MODERATE
        elif aqi_value <= 150:
            return cls.UNHEALTHY_SENSITIVE
        elif aqi_value <= 200:
            return cls.UNHEALTHY
        elif aqi_value <= 300:
            return cls.VERY_UNHEALTHY
        else:
            return cls.HAZARDOUS


# AQI Index Breakpoints (same for all pollutants)
# These are the AQI values that correspond to concentration breakpoints
AQI_INDEX_BREAKPOINTS = {
    AQICategory.GOOD: (0, 50),
    AQICategory.MODERATE: (51, 100),
    AQICategory.UNHEALTHY_SENSITIVE: (101, 150),
    AQICategory.UNHEALTHY: (151, 200),
    AQICategory.VERY_UNHEALTHY: (201, 300),
    AQICategory.HAZARDOUS: (301, 500),
}


# Concentration Breakpoints by Pollutant (US EPA standard)
# These define the concentration ranges for each AQI category
# Formula: Ip = ((IHi - ILo) / (BPHi - BPLo)) * (Cp - BPLo) + ILo
AQI_BREAKPOINTS = {
    Pollutant.NO2: {  # ppb (1-hour average)
        AQICategory.GOOD: (0, 53),
        AQICategory.MODERATE: (54, 100),
        AQICategory.UNHEALTHY_SENSITIVE: (101, 360),
        AQICategory.UNHEALTHY: (361, 649),
        AQICategory.VERY_UNHEALTHY: (650, 1249),
        AQICategory.HAZARDOUS: (1250, 2049),
    },
    Pollutant.SO2: {  # ppb (1-hour average)
        AQICategory.GOOD: (0, 35),
        AQICategory.MODERATE: (36, 75),
        AQICategory.UNHEALTHY_SENSITIVE: (76, 185),
        AQICategory.UNHEALTHY: (186, 304),
        AQICategory.VERY_UNHEALTHY: (305, 604),
        AQICategory.HAZARDOUS: (605, 1004),
    },
    Pollutant.PM25: {  # µg/m³ (24-hour average)
        AQICategory.GOOD: (0.0, 12.0),
        AQICategory.MODERATE: (12.1, 35.4),
        AQICategory.UNHEALTHY_SENSITIVE: (35.5, 55.4),
        AQICategory.UNHEALTHY: (55.5, 150.4),
        AQICategory.VERY_UNHEALTHY: (150.5, 250.4),
        AQICategory.HAZARDOUS: (250.5, 500.4),
    },
    Pollutant.PM10: {  # µg/m³ (24-hour average)
        AQICategory.GOOD: (0, 54),
        AQICategory.MODERATE: (55, 154),
        AQICategory.UNHEALTHY_SENSITIVE: (155, 254),
        AQICategory.UNHEALTHY: (255, 354),
        AQICategory.VERY_UNHEALTHY: (355, 424),
        AQICategory.HAZARDOUS: (425, 604),
    },
    Pollutant.CO: {  # ppm (8-hour average)
        AQICategory.GOOD: (0.0, 4.4),
        AQICategory.MODERATE: (4.5, 9.4),
        AQICategory.UNHEALTHY_SENSITIVE: (9.5, 12.4),
        AQICategory.UNHEALTHY: (12.5, 15.4),
        AQICategory.VERY_UNHEALTHY: (15.5, 30.4),
        AQICategory.HAZARDOUS: (30.5, 50.4),
    },
    Pollutant.O3: {  # ppb (8-hour average)
        AQICategory.GOOD: (0, 54),
        AQICategory.MODERATE: (55, 70),
        AQICategory.UNHEALTHY_SENSITIVE: (71, 85),
        AQICategory.UNHEALTHY: (86, 105),
        AQICategory.VERY_UNHEALTHY: (106, 200),
        AQICategory.HAZARDOUS: (201, 504),
    },
}

# AQI Colors for visualization (US EPA Standard)
# Reference: https://www.airnow.gov/aqi/aqi-basics/
AQI_COLORS = {
    AQICategory.GOOD: "#00E400",           # Green
    AQICategory.MODERATE: "#FFFF00",       # Yellow
    AQICategory.UNHEALTHY_SENSITIVE: "#FF7E00",  # Orange
    AQICategory.UNHEALTHY: "#FF0000",      # Red
    AQICategory.VERY_UNHEALTHY: "#8F3F97", # Purple
    AQICategory.HAZARDOUS: "#7E0023",      # Maroon
}

# AQI Category Descriptors (human-readable)
AQI_DESCRIPTORS = {
    AQICategory.GOOD: "Good",
    AQICategory.MODERATE: "Moderate",
    AQICategory.UNHEALTHY_SENSITIVE: "Unhealthy for Sensitive Groups",
    AQICategory.UNHEALTHY: "Unhealthy",
    AQICategory.VERY_UNHEALTHY: "Very Unhealthy",
    AQICategory.HAZARDOUS: "Hazardous",
}

# Health messages for each AQI category
AQI_HEALTH_MESSAGES = {
    AQICategory.GOOD: "Air quality is satisfactory, and air pollution poses little or no risk.",
    AQICategory.MODERATE: "Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive to air pollution.",
    AQICategory.UNHEALTHY_SENSITIVE: "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
    AQICategory.UNHEALTHY: "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects.",
    AQICategory.VERY_UNHEALTHY: "Health alert: The risk of health effects is increased for everyone.",
    AQICategory.HAZARDOUS: "Health warning of emergency conditions: everyone is more likely to be affected.",
}

# Legacy pollutant units mapping (for satellite data)
# Ground data should use STANDARD_UNITS from above
POLLUTANT_UNITS = {
    Pollutant.NO2: "mol/m²",
    Pollutant.SO2: "mol/m²",
    Pollutant.PM25: "µg/m³",
    Pollutant.PM10: "µg/m³",
    Pollutant.PM1: "µg/m³",
    Pollutant.CO: "mol/m²",
    Pollutant.O3: "mol/m²",
}

# CDSE Sentinel-5P band names (alternative naming)
CDSE_BAND_NAMES_ALT = {
    Pollutant.NO2: "NO2",
    Pollutant.SO2: "SO2",
    Pollutant.CO: "CO",
    Pollutant.O3: "O3",
    # PM2.5 uses Aerosol Index as proxy
    Pollutant.PM25: "AER_AI_340_380",
}


# =============================================================================
# GEOGRAPHIC CONSTANTS
# =============================================================================

# Pakistan provinces
PROVINCES = [
    "Punjab",
    "Sindh",
    "Khyber Pakhtunkhwa",
    "Balochistan",
    "Islamabad Capital Territory",
    "Gilgit-Baltistan",
    "Azad Jammu and Kashmir",
]


# =============================================================================
# VALIDATION CONSTANTS
# =============================================================================

# Valid value ranges for pollutants (sanity checks)
POLLUTANT_VALUE_RANGES: Dict[Pollutant, Tuple[float, float]] = {
    Pollutant.NO2: (0.0, 2000.0),    # µg/m³ - max ~2000 in extreme pollution
    Pollutant.SO2: (0.0, 2000.0),    # µg/m³
    Pollutant.PM25: (0.0, 1000.0),   # µg/m³ - Delhi hits 500+ in winter
    Pollutant.PM10: (0.0, 2000.0),   # µg/m³
    Pollutant.PM1: (0.0, 500.0),     # µg/m³
    Pollutant.CO: (0.0, 100.0),      # mg/m³ or ~50 ppm
    Pollutant.O3: (0.0, 500.0),      # µg/m³
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_aqi(pollutant: Pollutant | str, value: float) -> float:
    """
    Calculate AQI sub-index for a given pollutant concentration using EPA formula.
    
    Formula: Ip = ((IHi - ILo) / (BPHi - BPLo)) * (Cp - BPLo) + ILo
    
    Where:
        Ip = the sub-index for pollutant p
        Cp = the rounded concentration of pollutant p
        BPHi = the concentration breakpoint >= Cp
        BPLo = the concentration breakpoint <= Cp  
        IHi = the AQI value corresponding to BPHi
        ILo = the AQI value corresponding to BPLo
    
    The overall AQI is determined by the highest sub-index value among all 
    measured pollutants.
    
    Args:
        pollutant: The pollutant type (Pollutant enum or string like "PM25")
        value: The concentration value in standard units:
               - PM2.5: µg/m³ (24-hour average)
               - PM10: µg/m³ (24-hour average)
               - NO2: ppb (1-hour average)
               - SO2: ppb (1-hour average)
               - CO: ppm (8-hour average)
               - O3: ppb (8-hour average)
        
    Returns:
        AQI value (0-500)
    
    Reference:
        https://www.airnow.gov/aqi/aqi-basics/
    """
    # Convert string to Pollutant enum if needed
    if isinstance(pollutant, str):
        pollutant = Pollutant.from_string(pollutant)
        if pollutant is None:
            return 0.0
    
    # Get concentration breakpoints for this pollutant
    breakpoints = AQI_BREAKPOINTS.get(pollutant, {})
    if not breakpoints:
        return 0.0
    
    # Handle negative or zero values
    if value < 0:
        return 0.0
    
    # Find the concentration breakpoint range containing the value
    for category, (bp_lo, bp_hi) in breakpoints.items():
        if bp_lo <= value <= bp_hi:
            # Get corresponding AQI index breakpoints
            i_lo, i_hi = AQI_INDEX_BREAKPOINTS[category]
            
            # Apply EPA linear interpolation formula
            # Ip = ((IHi - ILo) / (BPHi - BPLo)) * (Cp - BPLo) + ILo
            aqi = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (value - bp_lo) + i_lo
            return round(aqi, 1)
    
    # If value exceeds the highest breakpoint (Hazardous), cap at 500
    # Check if value is above the highest concentration
    hazardous_range = breakpoints.get(AQICategory.HAZARDOUS)
    if hazardous_range and value > hazardous_range[1]:
        return 500.0
    
    # If value is above the highest category's lower bound
    if hazardous_range and value >= hazardous_range[0]:
        # Extrapolate within hazardous range
        bp_lo, bp_hi = hazardous_range
        i_lo, i_hi = AQI_INDEX_BREAKPOINTS[AQICategory.HAZARDOUS]
        aqi = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (value - bp_lo) + i_lo
        return min(round(aqi, 1), 500.0)
    
    return 500.0


def get_aqi_category(pollutant: Pollutant | str, value: float) -> AQICategory:
    """
    Determine AQI category for a given pollutant concentration.

    Args:
        pollutant: The pollutant type (Pollutant enum or string)
        value: The concentration value in standard units

    Returns:
        AQICategory enum value
    """
    # Convert string to Pollutant enum if needed
    if isinstance(pollutant, str):
        pollutant = Pollutant.from_string(pollutant)
        if pollutant is None:
            return AQICategory.GOOD
    
    breakpoints = AQI_BREAKPOINTS.get(pollutant, {})

    for category, (low, high) in breakpoints.items():
        if low <= value <= high:
            return category

    return AQICategory.HAZARDOUS


def get_category_from_aqi(aqi_value: float) -> AQICategory:
    """
    Get the AQI category directly from an AQI value.
    
    Args:
        aqi_value: The calculated AQI value (0-500)
        
    Returns:
        AQICategory enum value
    """
    return AQICategory.from_aqi(aqi_value)


def get_aqi_color(category: AQICategory) -> str:
    """Get the hex color code for an AQI category."""
    return AQI_COLORS.get(category, "#7E0023")


def get_aqi_descriptor(category: AQICategory) -> str:
    """Get the human-readable descriptor for an AQI category."""
    return AQI_DESCRIPTORS.get(category, "Unknown")


def get_health_message(category: AQICategory) -> str:
    """Get the health advisory message for an AQI category."""
    return AQI_HEALTH_MESSAGES.get(category, "")


# =============================================================================
# POLLUTANT LAYER CONFIGURATIONS (for Frontend Display)
# =============================================================================

POLLUTANT_LAYERS = [
    {
        "code": "NO2",
        "name": "Nitrogen Dioxide",
        "unit": "µg/m³",
        "description": "Traffic and industrial emissions",
        "health_impact": "Respiratory irritation, reduced lung function",
        "color_scheme": "orange-red",
        "legend": {
            "min": 0,
            "max": 200,
            "colors": ["#00ff00", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"],
            "labels": ["Good (0-50)", "Moderate (51-100)", "Unhealthy for Sensitive (101-150)", 
                      "Unhealthy (151-200)", "Very Unhealthy (200+)"]
        }
    },
    {
        "code": "PM25",
        "name": "PM2.5 (Fine Particulate Matter)",
        "unit": "µg/m³",
        "description": "Fine particles from combustion, dust",
        "health_impact": "Cardiovascular and respiratory issues",
        "color_scheme": "purple-blue",
        "legend": {
            "min": 0,
            "max": 250,
            "colors": ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97", "#7e0023"],
            "labels": ["Good (0-12)", "Moderate (12-35)", "Unhealthy for Sensitive (35-55)",
                      "Unhealthy (55-150)", "Very Unhealthy (150-250)", "Hazardous (250+)"]
        }
    },
    {
        "code": "PM10",
        "name": "PM10 (Coarse Particulate Matter)",
        "unit": "µg/m³",
        "description": "Dust, pollen, and mold spores",
        "health_impact": "Respiratory irritation, aggravates asthma",
        "color_scheme": "brown-yellow",
        "legend": {
            "min": 0,
            "max": 350,
            "colors": ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"],
            "labels": ["Good (0-54)", "Moderate (55-154)", "Unhealthy for Sensitive (155-254)",
                      "Unhealthy (255-354)", "Very Unhealthy (355+)"]
        }
    },
    {
        "code": "SO2",
        "name": "Sulfur Dioxide",
        "unit": "µg/m³",
        "description": "Fossil fuel combustion",
        "health_impact": "Respiratory issues, especially for asthmatics",
        "color_scheme": "yellow-green",
        "legend": {
            "min": 0,
            "max": 600,
            "colors": ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"],
            "labels": ["Good (0-35)", "Moderate (36-75)", "Unhealthy for Sensitive (76-185)",
                      "Unhealthy (186-304)", "Very Unhealthy (305+)"]
        }
    },
    {
        "code": "CO",
        "name": "Carbon Monoxide",
        "unit": "µg/m³",
        "description": "Incomplete combustion (vehicles, fires)",
        "health_impact": "Reduces oxygen delivery to organs",
        "color_scheme": "red-pink",
        "legend": {
            "min": 0,
            "max": 50000,
            "colors": ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"],
            "labels": ["Good (0-4400)", "Moderate (4500-9400)", "Unhealthy for Sensitive (9500-12400)",
                      "Unhealthy (12500-15400)", "Very Unhealthy (15500+)"]
        }
    },
    {
        "code": "O3",
        "name": "Ozone",
        "unit": "µg/m³",
        "description": "Secondary pollutant from reactions",
        "health_impact": "Respiratory irritation, chest pain",
        "color_scheme": "cyan-blue",
        "legend": {
            "min": 0,
            "max": 400,
            "colors": ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"],
            "labels": ["Good (0-54)", "Moderate (55-70)", "Unhealthy for Sensitive (71-85)",
                      "Unhealthy (86-105)", "Very Unhealthy (106+)"]
        }
    },
]
"""
Pollutant layer configurations for frontend display.

Each layer includes:
- code: Pollutant identifier
- name: Display name
- unit: Measurement unit
- description: Brief explanation
- health_impact: Health effects
- color_scheme: Visual theme
- legend: Color ramp and AQI breakpoints for visualization
"""

