"""
Satellite-based exposure calculation service.

Combines Google Earth Engine satellite data with population grids
to calculate exposure metrics without needing ground station data.

IMPORTANT: Satellite Data Conversion Notes
==========================================
TROPOMI provides COLUMN DENSITY (mol/m²) - the total amount of gas in a 
vertical column of atmosphere - NOT surface concentration.

Converting column density to surface concentration requires:
1. Boundary layer height (PBL) - varies by location, time, weather
2. Vertical distribution profile of the gas
3. Temperature and pressure profiles

The conversion factors used here are empirically derived from research
comparing TROPOMI data with ground station measurements. They represent
"typical" conditions and have uncertainties of ±30-50%.

References:
- Lamsal et al. (2021): NO2 column to surface conversion
- de Foy et al. (2016): CO column interpretation
- Theys et al. (2019): SO2 column to surface
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, Polygon, Point

from air_quality.constants import calculate_aqi, AQICategory, Pollutant
from air_quality.services.gee_manager import SatelliteDataManager, SatelliteDataResult
from .population import PopulationService, get_population_service

logger = logging.getLogger(__name__)


# =============================================================================
# TROPOMI COLUMN DENSITY TO SURFACE CONCENTRATION CONVERSION
# =============================================================================
# These conversion factors are empirically derived from validation studies
# comparing TROPOMI satellite data with ground-based measurements.
#
# Key assumptions:
# - Planetary Boundary Layer (PBL) height: ~1000-1500m (typical for South Asia)
# - Well-mixed conditions within the boundary layer
# - Conversion factors calibrated for urban/suburban environments
# =============================================================================

def convert_no2_column_to_surface(column_mol_m2: float, pbl_height_m: float = 1000) -> float:
    """
    Convert TROPOMI NO2 tropospheric column density to surface concentration.
    
    TROPOMI NO2 tropospheric column is in mol/m² (typically 0.5-10 × 10⁻⁵ mol/m²)
    
    Conversion approach:
    1. Column density represents total molecules in vertical column
    2. Assume most NO2 is in the boundary layer (valid for tropospheric column)
    3. Convert to surface concentration assuming well-mixed boundary layer
    
    Empirical validation factor ~0.4-0.6 accounts for vertical profile
    (surface concentrations are typically higher than column-averaged)
    
    Args:
        column_mol_m2: NO2 tropospheric column density in mol/m²
        pbl_height_m: Planetary boundary layer height in meters
        
    Returns:
        Surface NO2 concentration in ppb
    """
    # NO2 molecular weight: 46.01 g/mol
    # Avogadro's number: 6.022e23 molecules/mol
    # Standard conditions: T=298K, P=101325 Pa
    
    # Convert mol/m² to molecules/cm²
    molecules_cm2 = column_mol_m2 * 6.022e23 / 1e4  # 1e4 for m² to cm²
    
    # Typical TROPOMI NO2 values: 1e15 to 1e16 molecules/cm² (polluted urban)
    # Clean areas: 1e14 to 1e15 molecules/cm²
    
    # Convert to surface mixing ratio using empirical factor
    # Based on Lamsal et al. (2021) validation studies
    # Factor accounts for: 
    # - Actual vertical profile (surface enhancement)
    # - Boundary layer variability
    # - Diurnal variation (TROPOMI overpass ~13:30 local time)
    
    # Empirical conversion: 1e15 molec/cm² ≈ 2-5 ppb surface (typical urban)
    surface_ppb = (molecules_cm2 / 1e15) * 3.5  # Calibrated factor
    
    # Sanity check: cap at reasonable maximum
    return min(max(surface_ppb, 0), 500)  # NO2 rarely exceeds 500 ppb


def convert_so2_column_to_surface(column_mol_m2: float, pbl_height_m: float = 1000) -> float:
    """
    Convert TROPOMI SO2 total column density to surface concentration.
    
    SO2 column density includes both boundary layer and free troposphere.
    For background areas, most SO2 is in free troposphere (volcanic, transported).
    For polluted areas, boundary layer contribution dominates.
    
    Args:
        column_mol_m2: SO2 column density in mol/m²
        pbl_height_m: Planetary boundary layer height in meters
        
    Returns:
        Surface SO2 concentration in ppb
    """
    # Convert mol/m² to Dobson Units for reference
    # 1 DU = 2.69e16 molecules/cm² = 4.46e-5 mol/m²
    
    # SO2 molecular weight: 64.07 g/mol
    molecules_cm2 = column_mol_m2 * 6.022e23 / 1e4
    
    # Typical TROPOMI SO2 values:
    # - Background: 0.5-1 DU (volcanic influence)  
    # - Polluted urban: 1-5 DU
    # - Industrial hotspots: 5-20 DU
    
    # Empirical conversion based on de Foy et al. and Theys et al.
    # 1 DU SO2 ≈ 5-15 ppb surface (highly variable)
    dobson_units = molecules_cm2 / 2.69e16
    surface_ppb = dobson_units * 8.0  # Calibrated for urban environments
    
    return min(max(surface_ppb, 0), 500)


def convert_co_column_to_surface(column_mol_m2: float, pbl_height_m: float = 1000) -> float:
    """
    Convert TROPOMI CO total column density to surface concentration.
    
    CO has a long atmospheric lifetime (~2 months) and is well-mixed in troposphere.
    TROPOMI CO column is in mol/m² (typically 0.01-0.05 mol/m²)
    
    Important: CO column includes entire troposphere, not just boundary layer.
    Only ~10-20% of column CO is in the boundary layer.
    
    Args:
        column_mol_m2: CO column density in mol/m²
        pbl_height_m: Planetary boundary layer height in meters
        
    Returns:
        Surface CO concentration in ppm
    """
    # CO molecular weight: 28.01 g/mol
    # Typical TROPOMI CO column: 0.015-0.04 mol/m² (1.5-4 × 10¹⁸ molec/cm²)
    
    # Background CO: ~0.018 mol/m² (~100 ppb surface)
    # Polluted urban: 0.025-0.04 mol/m² (~200-500 ppb surface)
    # Fire/industrial: >0.05 mol/m² (~1000+ ppb surface)
    
    # Empirical conversion: based on MOPITT/TROPOMI validation
    # Factor accounts for vertical profile and boundary layer fraction
    
    # Convert to surface mixing ratio
    # 0.018 mol/m² (background) → ~0.1 ppm (100 ppb)
    # Scaling factor: ~5.5 ppm per mol/m²
    surface_ppm = column_mol_m2 * 5.5
    
    # Sanity check: typical surface CO is 0.05-2 ppm
    # Even heavily polluted cities rarely exceed 10 ppm
    return min(max(surface_ppm, 0), 50)


def convert_o3_column_to_surface(column_mol_m2: float) -> float:
    """
    Convert TROPOMI O3 total column to surface concentration estimate.
    
    IMPORTANT: O3 total column is dominated by stratospheric O3 (~90%).
    Tropospheric O3 is only ~10% of total column.
    This conversion is highly uncertain for surface O3.
    
    For better surface O3 estimates, use TROPOMI tropospheric O3 product
    or ground station data.
    
    Args:
        column_mol_m2: O3 column density in mol/m²
        
    Returns:
        Surface O3 concentration in ppb (HIGHLY UNCERTAIN)
    """
    # Total O3 column: typically 250-400 DU (dominated by stratosphere)
    # Tropospheric O3: typically 25-50 DU
    
    # Convert to Dobson Units
    # 1 DU = 2.69e16 molecules/cm² = 4.46e-5 mol/m²
    dobson_units = column_mol_m2 / 4.46e-5
    
    # Estimate tropospheric fraction (~10% of total)
    tropo_du = dobson_units * 0.10
    
    # Convert tropospheric column to surface (very rough)
    # 30 DU tropospheric O3 ≈ 50 ppb surface (typical)
    surface_ppb = (tropo_du / 30) * 50
    
    return min(max(surface_ppb, 0), 300)


@dataclass
class ExposureMetrics:
    """Exposure calculation results."""
    # Basic metrics
    total_population: float
    exposed_population: float  # Population in areas with data
    mean_exposure_index: float
    max_exposure_index: float
    
    # Population by AQI category
    pop_good: int = 0  # AQI 0-50
    pop_moderate: int = 0  # AQI 51-100
    pop_usg: int = 0  # Unhealthy for Sensitive Groups, AQI 101-150
    pop_unhealthy: int = 0  # AQI 151-200
    pop_very_unhealthy: int = 0  # AQI 201-300
    pop_hazardous: int = 0  # AQI > 300
    
    # Pollutant data
    mean_pm25: Optional[float] = None
    mean_no2: Optional[float] = None
    mean_aod: Optional[float] = None
    estimated_pm25_from_aod: Optional[float] = None
    
    # Combined AQI (worst of all pollutants)
    combined_aqi: Optional[float] = None
    aqi_category: Optional[str] = None
    dominant_pollutant: Optional[str] = None
    
    # Data quality
    data_coverage: float = 0.0  # Fraction of area with satellite data
    data_source: str = "satellite"
    observation_date: Optional[date] = None
    
    # Detailed breakdown (optional)
    pollutant_aqi: Dict[str, float] = field(default_factory=dict)


@dataclass
class PixelExposure:
    """Exposure data for a single pixel/point."""
    longitude: float
    latitude: float
    population: float
    pm25: Optional[float]
    aqi: float
    exposure_index: float
    category: AQICategory


class SatelliteExposureService:
    """
    Calculate exposure using satellite data.
    
    Integrates:
    - MODIS AOD → PM2.5 estimates
    - TROPOMI NO2, SO2, CO, O3
    - WorldPop population grid
    
    Provides exposure metrics at various scales:
    - Point (station location)
    - Bounding box (city/region)
    - Polygon (district/province)
    """
    
    # Reference population for exposure index normalization
    REFERENCE_POPULATION = 200.0  # people per km²
    
    # PM2.5 from AOD conversion factors (from gee_modis.py)
    PM25_COEFFICIENTS = {
        "slope": 45.0,
        "intercept": 15.0,
        "seasonal_factors": {
            "winter": 1.3,  # Dec-Feb: higher PM2.5 due to inversions
            "spring": 1.0,  # Mar-May: baseline
            "summer": 0.9,  # Jun-Aug: monsoon, lower PM2.5
            "fall": 1.2,    # Sep-Nov: crop burning
        }
    }
    
    def __init__(
        self,
        satellite_manager: Optional[SatelliteDataManager] = None,
        population_service: Optional[PopulationService] = None
    ):
        """
        Initialize satellite exposure service.
        
        Args:
            satellite_manager: GEE satellite data manager
            population_service: WorldPop population service
        """
        self._satellite_manager = satellite_manager
        self._population_service = population_service
    
    @property
    def satellite_manager(self) -> SatelliteDataManager:
        """Get or create satellite data manager."""
        if self._satellite_manager is None:
            self._satellite_manager = SatelliteDataManager()
        return self._satellite_manager
    
    @property
    def population_service(self) -> PopulationService:
        """Get or create population service."""
        if self._population_service is None:
            self._population_service = get_population_service()
        return self._population_service
    
    def calculate_exposure_for_bbox(
        self,
        minx: float,
        miny: float,
        maxx: float,
        maxy: float,
        target_date: Optional[date] = None,
        days_back: int = 7
    ) -> ExposureMetrics:
        """
        Calculate exposure for a bounding box.
        
        Args:
            minx, miny, maxx, maxy: Bounding box coordinates (WGS84)
            target_date: Target date for satellite data
            days_back: Number of days to look back for data
            
        Returns:
            ExposureMetrics with exposure statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        start_date = target_date - timedelta(days=days_back)
        
        # Get satellite data - bbox must be dict with west, south, east, north
        bbox_dict = {'west': minx, 'south': miny, 'east': maxx, 'north': maxy}
        satellite_data = self.satellite_manager.get_air_quality_data(
            bbox=bbox_dict,
            start_date=start_date,
            end_date=target_date,
            weighted=True
        )
        
        # Get population data
        pop_grid = self.population_service.get_population_for_bbox(
            minx, miny, maxx, maxy
        )
        
        return self._calculate_exposure_from_data(
            satellite_data=satellite_data,
            pop_grid=pop_grid,
            observation_date=target_date
        )
    
    def calculate_exposure_for_geometry(
        self,
        geometry: GEOSGeometry,
        target_date: Optional[date] = None,
        days_back: int = 7
    ) -> ExposureMetrics:
        """
        Calculate exposure for a geometry (district, province).
        
        Args:
            geometry: Django GEOSGeometry (Polygon or MultiPolygon)
            target_date: Target date for satellite data
            days_back: Number of days to look back for data
            
        Returns:
            ExposureMetrics with exposure statistics
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        start_date = target_date - timedelta(days=days_back)
        
        # Get bounding box from geometry - convert tuple to dict
        extent = geometry.extent  # (xmin, ymin, xmax, ymax)
        bbox_dict = {'west': extent[0], 'south': extent[1], 'east': extent[2], 'north': extent[3]}
        
        # Get satellite data for bbox
        satellite_data = self.satellite_manager.get_air_quality_data(
            bbox=bbox_dict,
            start_date=start_date,
            end_date=target_date,
            weighted=True
        )
        
        # Get population data clipped to geometry
        pop_grid = self.population_service.get_population_for_geometry(geometry)
        
        return self._calculate_exposure_from_data(
            satellite_data=satellite_data,
            pop_grid=pop_grid,
            observation_date=target_date
        )
    
    def calculate_exposure_at_point(
        self,
        longitude: float,
        latitude: float,
        buffer_km: float = 5.0,
        target_date: Optional[date] = None,
        days_back: int = 7
    ) -> ExposureMetrics:
        """
        Calculate exposure at a point (e.g., station location).
        
        Uses a buffer around the point to get satellite data.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            buffer_km: Buffer radius in kilometers
            target_date: Target date
            days_back: Days to look back
            
        Returns:
            ExposureMetrics for the location
        """
        # Convert km to degrees (approximate)
        buffer_deg = buffer_km / 111.0
        
        # Create bbox
        minx = longitude - buffer_deg
        maxx = longitude + buffer_deg
        miny = latitude - buffer_deg
        maxy = latitude + buffer_deg
        
        return self.calculate_exposure_for_bbox(
            minx, miny, maxx, maxy,
            target_date=target_date,
            days_back=days_back
        )
    
    def calculate_exposure_for_city(
        self,
        city_name: str,
        target_date: Optional[date] = None,
        days_back: int = 7
    ) -> ExposureMetrics:
        """
        Calculate exposure for a predefined city.
        
        Args:
            city_name: City name (must be in CITY_BBOXES)
            target_date: Target date
            days_back: Days to look back
            
        Returns:
            ExposureMetrics for the city
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        start_date = target_date - timedelta(days=days_back)
        
        # Use satellite manager's city method
        satellite_data = self.satellite_manager.get_city_air_quality(
            city=city_name,
            start_date=start_date,
            end_date=target_date,
            weighted=True
        )
        
        # Get population for city bbox
        from air_quality.services.gee_constants import CITY_BBOXES
        
        if city_name.lower() not in CITY_BBOXES:
            raise ValueError(f"Unknown city: {city_name}. Available: {list(CITY_BBOXES.keys())}")
        
        bbox_dict = CITY_BBOXES[city_name.lower()]
        bbox = (bbox_dict["west"], bbox_dict["south"], bbox_dict["east"], bbox_dict["north"])
        pop_grid = self.population_service.get_population_for_bbox(*bbox)
        
        return self._calculate_exposure_from_data(
            satellite_data=satellite_data,
            pop_grid=pop_grid,
            observation_date=target_date
        )
    
    def _calculate_exposure_from_data(
        self,
        satellite_data: SatelliteDataResult,
        pop_grid,
        observation_date: date
    ) -> ExposureMetrics:
        """
        Calculate exposure metrics from satellite and population data.
        
        This is the core calculation engine.
        """
        # Get population array
        pop_data = pop_grid.data.copy()
        nodata_mask = (pop_data == pop_grid.nodata) | (pop_data < 0)
        pop_data[nodata_mask] = 0
        
        total_population = float(np.sum(pop_data))
        
        # Extract pollutant values (prefer population-weighted mean if available)
        pm25 = None
        
        # Helper to get best available value
        def get_val(res):
            if not res: return None
            return res.weighted_mean_value if res.weighted_mean_value is not None else res.mean_value

        no2_column = get_val(satellite_data.no2)
        so2_column = get_val(satellite_data.so2)
        co_column = get_val(satellite_data.co)
        o3_column = get_val(satellite_data.o3)
        aod = satellite_data.aod.aod_055 if satellite_data.aod else None
        
        # Estimate PM2.5 from AOD if available
        if satellite_data.aod and satellite_data.aod.estimated_pm25:
            pm25 = satellite_data.aod.estimated_pm25
        
        # =========================================================================
        # CONVERT SATELLITE COLUMN DENSITIES TO SURFACE CONCENTRATIONS
        # Using empirically-derived conversion factors from validation studies
        # =========================================================================
        
        # Store converted surface concentrations for reporting
        surface_concentrations = {}
        
        # Calculate AQI for each pollutant using proper conversions
        pollutant_aqi = {}
        
        # PM2.5 from AOD (already in µg/m³)
        if pm25 is not None:
            surface_concentrations["PM25"] = {"value": pm25, "unit": "µg/m³"}
            pollutant_aqi["PM25"] = calculate_aqi(Pollutant.PM25, pm25)
            logger.debug(f"PM2.5: {pm25:.1f} µg/m³ → AQI {pollutant_aqi['PM25']}")
        
        # NO2: Convert column (mol/m²) to surface (ppb)
        if no2_column is not None:
            no2_ppb = convert_no2_column_to_surface(no2_column)
            surface_concentrations["NO2"] = {
                "column_mol_m2": no2_column, 
                "surface_ppb": no2_ppb,
                "unit": "ppb"
            }
            pollutant_aqi["NO2"] = calculate_aqi(Pollutant.NO2, no2_ppb)
            logger.debug(f"NO2: {no2_column:.2e} mol/m² → {no2_ppb:.1f} ppb → AQI {pollutant_aqi['NO2']}")
        
        # SO2: Convert column (mol/m²) to surface (ppb)
        if so2_column is not None:
            so2_ppb = convert_so2_column_to_surface(so2_column)
            surface_concentrations["SO2"] = {
                "column_mol_m2": so2_column,
                "surface_ppb": so2_ppb, 
                "unit": "ppb"
            }
            pollutant_aqi["SO2"] = calculate_aqi(Pollutant.SO2, so2_ppb)
            logger.debug(f"SO2: {so2_column:.2e} mol/m² → {so2_ppb:.1f} ppb → AQI {pollutant_aqi['SO2']}")
        
        # CO: Convert column (mol/m²) to surface (ppm)
        if co_column is not None:
            co_ppm = convert_co_column_to_surface(co_column)
            surface_concentrations["CO"] = {
                "column_mol_m2": co_column,
                "surface_ppm": co_ppm,
                "unit": "ppm"
            }
            pollutant_aqi["CO"] = calculate_aqi(Pollutant.CO, co_ppm)
            logger.debug(f"CO: {co_column:.4f} mol/m² → {co_ppm:.2f} ppm → AQI {pollutant_aqi['CO']}")
        
        # O3: Convert column (mol/m²) to surface (ppb) - HIGHLY UNCERTAIN
        # NOTE: Total O3 column is dominated by stratosphere, not useful for surface AQI
        # We skip O3 AQI from satellite data unless tropospheric O3 product is used
        if o3_column is not None:
            # Don't use total column O3 for surface AQI - too uncertain
            surface_concentrations["O3"] = {
                "column_mol_m2": o3_column,
                "note": "Total column O3 not suitable for surface AQI"
            }
            # Optionally calculate if user wants rough estimate
            # o3_ppb = convert_o3_column_to_surface(o3_column)
            # pollutant_aqi["O3"] = calculate_aqi(Pollutant.O3, o3_ppb)
        
        # Log conversion summary
        logger.info(f"Satellite AQI breakdown: {pollutant_aqi}")
        
        # Determine combined AQI (worst of all pollutants)
        combined_aqi = None
        dominant_pollutant = None
        aqi_category_name = None
        
        if pollutant_aqi:
            combined_aqi = max(pollutant_aqi.values())
            dominant_pollutant = max(pollutant_aqi, key=pollutant_aqi.get)
            aqi_category_name = self._get_category_from_aqi(combined_aqi)
        
        # Calculate population by AQI category
        # For satellite data, we apply uniform AQI to entire region
        # (spatial variation would require gridded satellite data)
        pop_by_category = self._categorize_population_uniform(
            total_population=total_population,
            aqi=combined_aqi
        )
        
        # Calculate exposure index
        exposure_index = self._calculate_exposure_index(
            aqi=combined_aqi or 0,
            population=total_population
        )
        
        # Data coverage (based on satellite data availability)
        data_coverage = 1.0 if satellite_data.has_data else 0.0
        
        return ExposureMetrics(
            total_population=total_population,
            exposed_population=total_population if satellite_data.has_data else 0,
            mean_exposure_index=exposure_index,
            max_exposure_index=exposure_index,  # Same for uniform AQI
            
            pop_good=pop_by_category.get("pop_good", 0),
            pop_moderate=pop_by_category.get("pop_moderate", 0),
            pop_usg=pop_by_category.get("pop_usg", 0),
            pop_unhealthy=pop_by_category.get("pop_unhealthy", 0),
            pop_very_unhealthy=pop_by_category.get("pop_very_unhealthy", 0),
            pop_hazardous=pop_by_category.get("pop_hazardous", 0),
            
            mean_pm25=pm25,
            mean_no2=surface_concentrations.get("NO2", {}).get("surface_ppb"),
            mean_aod=aod,
            estimated_pm25_from_aod=pm25,
            
            combined_aqi=combined_aqi,
            aqi_category=aqi_category_name,
            dominant_pollutant=dominant_pollutant,
            
            data_coverage=data_coverage,
            data_source="satellite",
            observation_date=observation_date,
            pollutant_aqi=pollutant_aqi
        )
    
    def _categorize_population_uniform(
        self,
        total_population: float,
        aqi: Optional[float]
    ) -> Dict[str, int]:
        """
        Categorize population when AQI is uniform across region.
        
        All population goes into one category based on the AQI.
        """
        categories = {
            "pop_good": 0,
            "pop_moderate": 0,
            "pop_usg": 0,
            "pop_unhealthy": 0,
            "pop_very_unhealthy": 0,
            "pop_hazardous": 0,
        }
        
        if aqi is None or total_population <= 0:
            return categories
        
        pop_int = int(total_population)
        
        if aqi <= 50:
            categories["pop_good"] = pop_int
        elif aqi <= 100:
            categories["pop_moderate"] = pop_int
        elif aqi <= 150:
            categories["pop_usg"] = pop_int
        elif aqi <= 200:
            categories["pop_unhealthy"] = pop_int
        elif aqi <= 300:
            categories["pop_very_unhealthy"] = pop_int
        else:
            categories["pop_hazardous"] = pop_int
        
        return categories
    
    def _get_category_from_aqi(self, aqi: float) -> str:
        """Get AQI category name from AQI value."""
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif aqi <= 200:
            return "Unhealthy"
        elif aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"
    
    def _calculate_exposure_index(
        self,
        aqi: float,
        population: float
    ) -> float:
        """
        Calculate exposure index.
        
        Index = AQI × population_weight
        Normalized to 0-500 scale.
        """
        if aqi <= 0 or population <= 0:
            return 0.0
        
        # Population weight (normalized to reference)
        pop_weight = min(population / (self.REFERENCE_POPULATION * 100), 5.0)
        
        # Exposure index
        index = aqi * (0.5 + 0.5 * pop_weight)
        
        return min(index, 500.0)
    
    def batch_calculate_exposure(
        self,
        geometries: List[Tuple[str, GEOSGeometry]],
        target_date: Optional[date] = None,
        days_back: int = 7,
        max_workers: int = 4
    ) -> Dict[str, ExposureMetrics]:
        """
        Calculate exposure for multiple geometries in parallel.
        
        Args:
            geometries: List of (name, geometry) tuples
            target_date: Target date
            days_back: Days to look back
            max_workers: Maximum parallel workers
            
        Returns:
            Dictionary mapping names to ExposureMetrics
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.calculate_exposure_for_geometry,
                    geom,
                    target_date,
                    days_back
                ): name
                for name, geom in geometries
            }
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception as e:
                    logger.error(f"Error calculating exposure for {name}: {e}")
                    results[name] = None
        
        return results


# Convenience function
def calculate_satellite_exposure(
    bbox: Optional[Tuple[float, float, float, float]] = None,
    geometry: Optional[GEOSGeometry] = None,
    city: Optional[str] = None,
    point: Optional[Tuple[float, float]] = None,
    target_date: Optional[date] = None,
    days_back: int = 7
) -> ExposureMetrics:
    """
    Convenience function for satellite exposure calculation.
    
    Provide one of: bbox, geometry, city, or point.
    """
    service = SatelliteExposureService()
    
    if city:
        return service.calculate_exposure_for_city(city, target_date, days_back)
    elif bbox:
        return service.calculate_exposure_for_bbox(*bbox, target_date, days_back)
    elif geometry:
        return service.calculate_exposure_for_geometry(geometry, target_date, days_back)
    elif point:
        return service.calculate_exposure_at_point(*point, target_date=target_date, days_back=days_back)
    else:
        raise ValueError("Must provide bbox, geometry, city, or point")
