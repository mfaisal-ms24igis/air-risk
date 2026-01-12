"""
Unit conversion service for air quality measurements.

Handles conversion between different measurement units used by OpenAQ,
satellite data (Sentinel-5P), and standard reporting formats.

Example usage:
    from air_quality.services.unit_converter import UnitConverter
    
    converter = UnitConverter()
    
    # Convert ppb to µg/m³ for NO2
    ug_value = converter.convert(50.0, UnitType.PPB, UnitType.UG_M3, Pollutant.NO2)
    
    # Normalize a reading to standard units
    normalized, unit = converter.normalize_to_standard(50.0, "ppb", "NO2")
"""

import logging
from typing import Tuple, Optional

from air_quality.constants import (
    Pollutant,
    UnitType,
    STANDARD_UNITS,
    MOLECULAR_WEIGHTS,
    UNIT_CONVERSION_FACTORS,
    MOLAR_VOLUME_L,
)
from air_quality.services.base_service import BaseService


class UnitConversionError(Exception):
    """Raised when unit conversion fails."""
    pass


class UnitConverter(BaseService):
    """
    Service for converting air quality measurement units.
    
    Handles conversions between:
    - Mass concentration: µg/m³, mg/m³, ng/m³
    - Volume concentration: ppm, ppb, ppmv
    - Column density: mol/m², molecules/cm², DU
    - Particle counts: particles/cm³, #/cm³
    
    Gas conversions (ppm/ppb ↔ µg/m³) require molecular weight and use
    standard temperature (25°C) and pressure (1 atm).
    
    Attributes:
        molar_volume: Molar volume at STP in liters (24.45 L/mol at 25°C, 1 atm)
    """

    def __init__(self) -> None:
        """Initialize the unit converter service."""
        super().__init__(logger_name="UnitConverter")
        self.molar_volume = MOLAR_VOLUME_L

    def convert(
        self,
        value: float,
        from_unit: UnitType,
        to_unit: UnitType,
        pollutant: Optional[Pollutant] = None,
    ) -> float:
        """
        Convert a value from one unit to another.
        
        Args:
            value: The measurement value to convert.
            from_unit: Source unit type.
            to_unit: Target unit type.
            pollutant: Pollutant type (required for gas conversions).
            
        Returns:
            Converted value in target units.
            
        Raises:
            UnitConversionError: If conversion is not supported or pollutant
                is required but not provided.
        """
        # Same unit - no conversion needed
        if from_unit == to_unit:
            return value
        
        # Check for direct conversion factor
        conversion_key = (from_unit, to_unit)
        if conversion_key in UNIT_CONVERSION_FACTORS:
            factor = UNIT_CONVERSION_FACTORS[conversion_key]
            
            if factor is not None:
                # Direct conversion with constant factor
                return value * factor
            else:
                # Requires molecular weight (gas conversion)
                if pollutant is None:
                    raise UnitConversionError(
                        f"Pollutant required for {from_unit.value} → {to_unit.value} conversion"
                    )
                return self._convert_gas_units(value, from_unit, to_unit, pollutant)
        
        # Try reverse conversion
        reverse_key = (to_unit, from_unit)
        if reverse_key in UNIT_CONVERSION_FACTORS:
            factor = UNIT_CONVERSION_FACTORS[reverse_key]
            
            if factor is not None:
                return value / factor
            else:
                if pollutant is None:
                    raise UnitConversionError(
                        f"Pollutant required for {from_unit.value} → {to_unit.value} conversion"
                    )
                return self._convert_gas_units(value, from_unit, to_unit, pollutant)
        
        # Try two-step conversion through µg/m³
        if from_unit != UnitType.UG_M3 and to_unit != UnitType.UG_M3:
            try:
                # Convert to µg/m³ first
                intermediate = self.convert(value, from_unit, UnitType.UG_M3, pollutant)
                # Then convert to target unit
                return self.convert(intermediate, UnitType.UG_M3, to_unit, pollutant)
            except UnitConversionError:
                pass  # Fall through to error
        
        raise UnitConversionError(
            f"No conversion path from {from_unit.value} to {to_unit.value}"
        )

    def _convert_gas_units(
        self,
        value: float,
        from_unit: UnitType,
        to_unit: UnitType,
        pollutant: Pollutant,
    ) -> float:
        """
        Convert gas concentrations between volume and mass units.
        
        Uses the ideal gas law at standard conditions:
        - Temperature: 25°C (298.15 K)
        - Pressure: 1 atm (101.325 kPa)
        - Molar volume: 24.45 L/mol
        
        Conversion formulas:
        - ppb → µg/m³: value * (MW / molar_volume)
        - µg/m³ → ppb: value * (molar_volume / MW)
        - ppm → µg/m³: value * (MW / molar_volume) * 1000
        - µg/m³ → ppm: value * (molar_volume / MW) / 1000
        
        Args:
            value: Measurement value.
            from_unit: Source unit.
            to_unit: Target unit.
            pollutant: Gas pollutant (NO2, SO2, CO, O3).
            
        Returns:
            Converted value.
            
        Raises:
            UnitConversionError: If pollutant has no molecular weight defined.
        """
        if pollutant not in MOLECULAR_WEIGHTS:
            raise UnitConversionError(
                f"No molecular weight defined for {pollutant.value}. "
                f"Gas conversion only supported for: {list(MOLECULAR_WEIGHTS.keys())}"
            )
        
        mw = MOLECULAR_WEIGHTS[pollutant]
        
        # PPB → µg/m³
        if from_unit == UnitType.PPB and to_unit == UnitType.UG_M3:
            return value * (mw / self.molar_volume)
        
        # µg/m³ → PPB
        if from_unit == UnitType.UG_M3 and to_unit == UnitType.PPB:
            return value * (self.molar_volume / mw)
        
        # PPM → µg/m³
        if from_unit == UnitType.PPM and to_unit == UnitType.UG_M3:
            return value * (mw / self.molar_volume) * 1000
        
        # µg/m³ → PPM
        if from_unit == UnitType.UG_M3 and to_unit == UnitType.PPM:
            return value * (self.molar_volume / mw) / 1000
        
        # PPB → PPM
        if from_unit == UnitType.PPB and to_unit == UnitType.PPM:
            return value / 1000
        
        # PPM → PPB
        if from_unit == UnitType.PPM and to_unit == UnitType.PPB:
            return value * 1000
        
        raise UnitConversionError(
            f"Gas conversion not implemented: {from_unit.value} → {to_unit.value}"
        )

    def normalize_to_standard(
        self,
        value: float,
        unit: str,
        parameter: str,
    ) -> Tuple[float, UnitType]:
        """
        Normalize a measurement to standard units for its pollutant type.
        
        This is the primary method for data ingestion - it takes raw values
        from OpenAQ (which may have varying units) and converts to the
        standard unit for that pollutant (typically µg/m³).
        
        Args:
            value: Raw measurement value.
            unit: Unit string from data source (e.g., "ppb", "ug/m3").
            parameter: Pollutant parameter string (e.g., "pm25", "NO2").
            
        Returns:
            Tuple of (normalized_value, standard_unit).
            
        Raises:
            UnitConversionError: If unit or parameter is not recognized.
        """
        # Parse unit string
        source_unit = UnitType.from_string(unit)
        if source_unit is None:
            raise UnitConversionError(f"Unrecognized unit: {unit}")
        
        # Parse pollutant
        pollutant = Pollutant.from_string(parameter)
        if pollutant is None:
            raise UnitConversionError(f"Unrecognized parameter: {parameter}")
        
        # Get standard unit for this pollutant
        if pollutant not in STANDARD_UNITS:
            # Default to µg/m³ for unknown pollutants
            target_unit = UnitType.UG_M3
        else:
            target_unit = STANDARD_UNITS[pollutant]
        
        # Convert
        try:
            normalized_value = self.convert(value, source_unit, target_unit, pollutant)
            return (normalized_value, target_unit)
        except UnitConversionError as e:
            self.log_warning(
                f"Could not normalize {parameter}={value} {unit}: {e}"
            )
            # Return original value with source unit if conversion fails
            return (value, source_unit)

    def is_conversion_supported(
        self,
        from_unit: UnitType,
        to_unit: UnitType,
        pollutant: Optional[Pollutant] = None,
    ) -> bool:
        """
        Check if a conversion is supported.
        
        Args:
            from_unit: Source unit.
            to_unit: Target unit.
            pollutant: Pollutant (required for gas conversions).
            
        Returns:
            True if conversion is supported.
        """
        if from_unit == to_unit:
            return True
        
        # Check direct conversion
        if (from_unit, to_unit) in UNIT_CONVERSION_FACTORS:
            factor = UNIT_CONVERSION_FACTORS[(from_unit, to_unit)]
            if factor is not None:
                return True
            # Gas conversion - check if pollutant has MW
            return pollutant is not None and pollutant in MOLECULAR_WEIGHTS
        
        # Check reverse conversion
        if (to_unit, from_unit) in UNIT_CONVERSION_FACTORS:
            factor = UNIT_CONVERSION_FACTORS[(to_unit, from_unit)]
            if factor is not None:
                return True
            return pollutant is not None and pollutant in MOLECULAR_WEIGHTS
        
        return False

    def get_conversion_factor(
        self,
        from_unit: UnitType,
        to_unit: UnitType,
        pollutant: Optional[Pollutant] = None,
    ) -> Optional[float]:
        """
        Get the conversion factor between units.
        
        For gas conversions, this calculates the factor based on molecular weight.
        
        Args:
            from_unit: Source unit.
            to_unit: Target unit.
            pollutant: Pollutant (required for gas conversions).
            
        Returns:
            Conversion factor, or None if not supported.
        """
        if from_unit == to_unit:
            return 1.0
        
        # Check direct conversion
        key = (from_unit, to_unit)
        if key in UNIT_CONVERSION_FACTORS:
            factor = UNIT_CONVERSION_FACTORS[key]
            if factor is not None:
                return factor
            
            # Calculate gas conversion factor
            if pollutant and pollutant in MOLECULAR_WEIGHTS:
                mw = MOLECULAR_WEIGHTS[pollutant]
                
                if from_unit == UnitType.PPB and to_unit == UnitType.UG_M3:
                    return mw / self.molar_volume
                if from_unit == UnitType.PPM and to_unit == UnitType.UG_M3:
                    return (mw / self.molar_volume) * 1000
                if from_unit == UnitType.UG_M3 and to_unit == UnitType.PPB:
                    return self.molar_volume / mw
                if from_unit == UnitType.UG_M3 and to_unit == UnitType.PPM:
                    return (self.molar_volume / mw) / 1000
        
        return None


# Module-level singleton instance
_unit_converter: Optional[UnitConverter] = None


def get_unit_converter() -> UnitConverter:
    """
    Get the singleton UnitConverter instance.
    
    Returns:
        Shared UnitConverter instance.
    """
    global _unit_converter
    if _unit_converter is None:
        _unit_converter = UnitConverter()
    return _unit_converter
