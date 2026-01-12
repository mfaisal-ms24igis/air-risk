"""
GEE-based Pixel-wise Exposure Calculation Service.

Calculates air quality exposure entirely on Google Earth Engine servers
using pixel-wise operations. Returns tile URLs for visualization and
summary statistics without downloading raster data.
"""

import logging
import ee
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from django.contrib.gis.geos import GEOSGeometry

from air_quality.services.gee_auth import initialize_gee
from air_quality.constants import Pollutant, AQICategory, AQI_BREAKPOINTS, AQI_INDEX_BREAKPOINTS

logger = logging.getLogger(__name__)


@dataclass
class GEEExposureResult:
    """Result from GEE-based exposure calculation."""
    
    # Tile URLs for visualization
    exposure_tile_url: str
    aqi_tile_url: str
    map_id: str
    token: str
    
    # Summary statistics
    total_population: int
    mean_exposure_index: float
    max_exposure_index: float
    mean_aqi: float
    max_aqi: float
    
    # Population by AQI category
    pop_good: int = 0
    pop_moderate: int = 0
    pop_unhealthy_sensitive: int = 0
    pop_unhealthy: int = 0
    pop_very_unhealthy: int = 0
    pop_hazardous: int = 0
    
    # Pollutant contributions
    mean_pm25: Optional[float] = None
    mean_no2: Optional[float] = None
    mean_so2: Optional[float] = None
    mean_co: Optional[float] = None
    dominant_pollutant: Optional[str] = None
    
    # Metadata
    calculation_date: str = ""
    geometry_bounds: Dict[str, float] = field(default_factory=dict)
    resolution_meters: float = 1113.2
    data_source: str = "gee_gridded"
    errors: List[str] = field(default_factory=list)


class GEEExposureService:
    """
    Service for calculating pixel-wise exposure on Google Earth Engine.
    
    All calculations are performed server-side on GEE using ee.Image operations.
    Only summary statistics and tile URLs are returned to minimize data transfer.
    """
    
    def __init__(self):
        """Initialize the GEE exposure service."""
        self._initialized = False
        initialize_gee()
        self._initialized = True
    
    def calculate_aqi_image(
        self,
        pollutant_image: ee.Image,
        pollutant: Pollutant,
    ) -> ee.Image:
        """
        Calculate AQI pixel-wise on GEE using EPA breakpoints.
        
        Uses cascading .where() conditions to implement piecewise linear
        interpolation formula: Ip = ((IHi - ILo) / (BPHi - BPLo)) * (Cp - BPLo) + ILo
        
        Args:
            pollutant_image: ee.Image with pollutant concentrations in standard units
                - PM2.5: µg/m³
                - NO2: ppb  
                - SO2: ppb
                - CO: ppm
            pollutant: Pollutant enum type
            
        Returns:
            ee.Image with AQI values (0-500)
        """
        breakpoints = AQI_BREAKPOINTS.get(pollutant, {})
        if not breakpoints:
            logger.error(f"No breakpoints defined for {pollutant}")
            return ee.Image.constant(0).rename('AQI')
        
        # Initialize AQI image with zeros
        aqi = ee.Image(0)
        
        # Apply piecewise linear interpolation for each category
        for category in [
            AQICategory.GOOD,
            AQICategory.MODERATE,
            AQICategory.UNHEALTHY_SENSITIVE,
            AQICategory.UNHEALTHY,
            AQICategory.VERY_UNHEALTHY,
            AQICategory.HAZARDOUS,
        ]:
            bp_lo, bp_hi = breakpoints[category]
            i_lo, i_hi = AQI_INDEX_BREAKPOINTS[category]
            
            # Create mask for pixels in this concentration range
            in_range = pollutant_image.gte(bp_lo).And(pollutant_image.lte(bp_hi))
            
            # Calculate AQI for pixels in this range
            # AQI = ((IHi - ILo) / (BPHi - BPLo)) * (C - BPLo) + ILo
            slope = (i_hi - i_lo) / (bp_hi - bp_lo)
            aqi_for_range = pollutant_image.subtract(bp_lo).multiply(slope).add(i_lo)
            
            # Update AQI where mask is true
            aqi = aqi.where(in_range, aqi_for_range)
        
        # Cap values above hazardous range at 500
        hazardous_high = breakpoints[AQICategory.HAZARDOUS][1]
        aqi = aqi.where(pollutant_image.gt(hazardous_high), 500)
        
        return aqi.rename('AQI')
    
    def calculate_combined_aqi_image(
        self,
        pm25_image: Optional[ee.Image] = None,
        no2_image: Optional[ee.Image] = None,
        so2_image: Optional[ee.Image] = None,
        co_image: Optional[ee.Image] = None,
    ) -> Tuple[ee.Image, str]:
        """
        Calculate combined AQI taking maximum across all pollutants.
        
        Args:
            pm25_image: PM2.5 in µg/m³
            no2_image: NO2 in ppb
            so2_image: SO2 in ppb
            co_image: CO in ppm
            
        Returns:
            Tuple of (combined_aqi_image, dominant_pollutant_name)
        """
        aqi_images = []
        pollutant_names = []
        
        if pm25_image is not None:
            aqi_images.append(self.calculate_aqi_image(pm25_image, Pollutant.PM25).rename('AQI_PM25'))
            pollutant_names.append('PM25')
        
        if no2_image is not None:
            aqi_images.append(self.calculate_aqi_image(no2_image, Pollutant.NO2).rename('AQI_NO2'))
            pollutant_names.append('NO2')
        
        if so2_image is not None:
            aqi_images.append(self.calculate_aqi_image(so2_image, Pollutant.SO2).rename('AQI_SO2'))
            pollutant_names.append('SO2')
        
        if co_image is not None:
            aqi_images.append(self.calculate_aqi_image(co_image, Pollutant.CO).rename('AQI_CO'))
            pollutant_names.append('CO')
        
        if not aqi_images:
            logger.warning("No pollutant images provided for combined AQI")
            return ee.Image.constant(0).rename('AQI'), "NONE"
        
        # Stack all AQI images
        aqi_stack = ee.Image.cat(aqi_images)
        
        # Take maximum AQI across all pollutants (pixel-wise)
        combined_aqi = aqi_stack.reduce(ee.Reducer.max()).rename('AQI')
        
        # Determine dominant pollutant (most common worst pollutant)
        # For now, return the first pollutant as dominant (can be enhanced)
        dominant_pollutant = pollutant_names[0] if pollutant_names else "UNKNOWN"
        
        return combined_aqi, dominant_pollutant
    
    def get_worldpop_image(
        self,
        year: int = 2020,
        resolution_meters: float = 1113.2,
    ) -> ee.Image:
        """
        Get WorldPop population data from GEE and aggregate to target resolution.
        
        Args:
            year: Year for population data (2020 is latest)
            resolution_meters: Target resolution in meters (default: 1113.2 for Sentinel-5P)
            
        Returns:
            ee.Image with population counts aggregated to target resolution
        """
        # WorldPop is at 100m resolution for Pakistan
        worldpop = ee.ImageCollection('WorldPop/GP/100m/pop') \
            .filter(ee.Filter.eq('country', 'PAK')) \
            .filter(ee.Filter.eq('year', year)) \
            .first() \
            .select('population')
        
        # Aggregate to satellite resolution using sum reducer
        # This sums all 100m pixels within each target resolution pixel
        aggregated_pop = worldpop.reduceResolution(
            reducer=ee.Reducer.sum(),
            maxPixels=65536
        ).reproject(
            crs='EPSG:4326',
            scale=resolution_meters
        )
        
        return aggregated_pop.rename('population')
    
    def calculate_exposure_image(
        self,
        aqi_image: ee.Image,
        population_image: ee.Image,
    ) -> ee.Image:
        """
        Calculate exposure index pixel-wise on GEE.
        
        Exposure = AQI × log(population + 1)
        
        This weights AQI by population, giving higher exposure scores
        where both pollution and population are high.
        
        Args:
            aqi_image: ee.Image with AQI values
            population_image: ee.Image with population counts
            
        Returns:
            ee.Image with exposure index values
        """
        # Exposure = AQI × log(population + 1)
        # Note: If AQI image has no bands, this will fail in getInfo() later
        # but we handle that in the calling function
        try:
            exposure = aqi_image.multiply(
                population_image.add(1).log()
            )
            return exposure.rename('exposure')
        except Exception as e:
            logger.warning(f"Failed to calculate exposure, returning zero: {e}")
            return ee.Image.constant(0).rename('exposure')
    
    def categorize_population_by_aqi(
        self,
        aqi_image: ee.Image,
        population_image: ee.Image,
        geometry: ee.Geometry,
        scale: float = 1113.2,
    ) -> Dict[str, int]:
        """
        Categorize population by AQI levels using server-side reduction.
        
        Args:
            aqi_image: ee.Image with AQI values
            population_image: ee.Image with population counts
            geometry: ee.Geometry region to analyze
            scale: Pixel scale in meters
            
        Returns:
            Dict with population counts per AQI category
        """
        categories = {
            'good': (0, 50),
            'moderate': (51, 100),
            'unhealthy_sensitive': (101, 150),
            'unhealthy': (151, 200),
            'very_unhealthy': (201, 300),
            'hazardous': (301, 500),
        }
        
        pop_by_category = {}
        
        for category_name, (aqi_min, aqi_max) in categories.items():
            # Mask population where AQI is in this range
            pop_masked = population_image.updateMask(
                aqi_image.gt(aqi_min).And(aqi_image.lte(aqi_max))
            )
            
            # Sum population in this category
            try:
                result = pop_masked.reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=geometry,
                    scale=scale,
                    maxPixels=1e10,
                    bestEffort=True,
                ).getInfo()
                
                pop_by_category[category_name] = int(result.get('population', 0))
            except Exception as e:
                logger.error(f"Error categorizing population for {category_name}: {e}")
                pop_by_category[category_name] = 0
        
        return pop_by_category
    
    def get_exposure_statistics(
        self,
        exposure_image: ee.Image,
        aqi_image: ee.Image,
        population_image: ee.Image,
        geometry: ee.Geometry,
        scale: float = 1113.2,
    ) -> Dict[str, float]:
        """
        Calculate summary statistics for exposure and AQI.
        
        Args:
            exposure_image: ee.Image with exposure values
            aqi_image: ee.Image with AQI values
            population_image: ee.Image with population counts
            geometry: ee.Geometry region to analyze
            scale: Pixel scale in meters
            
        Returns:
            Dict with summary statistics
        """
        try:
            # Calculate statistics for exposure
            exposure_stats = exposure_image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.max(), '', True
                ).combine(
                    ee.Reducer.sum(), '', True
                ),
                geometry=geometry,
                scale=scale,
                maxPixels=1e10,
                bestEffort=True,
            ).getInfo()
            
            # Calculate statistics for AQI
            aqi_stats = aqi_image.reduceRegion(
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.max(), '', True
                ),
                geometry=geometry,
                scale=scale,
                maxPixels=1e10,
                bestEffort=True,
            ).getInfo()
            
            # Calculate total population
            pop_stats = population_image.reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=scale,
                maxPixels=1e10,
                bestEffort=True,
            ).getInfo()
            
            return {
                'mean_exposure': exposure_stats.get('exposure_mean', 0),
                'max_exposure': exposure_stats.get('exposure_max', 0),
                'total_exposure': exposure_stats.get('exposure_sum', 0),
                'mean_aqi': aqi_stats.get('AQI_mean', 0),
                'max_aqi': aqi_stats.get('AQI_max', 0),
                'total_population': pop_stats.get('population', 0),
            }
        except Exception as e:
            logger.error(f"Error calculating exposure statistics: {e}")
            return {
                'mean_exposure': 0,
                'max_exposure': 0,
                'total_exposure': 0,
                'mean_aqi': 0,
                'max_aqi': 0,
                'total_population': 0,
            }
    
    def generate_tile_urls(
        self,
        exposure_image: ee.Image,
        aqi_image: ee.Image,
        max_exposure: float,
        max_aqi: float,
    ) -> Dict[str, Any]:
        """
        Generate tile URLs for visualization.
        
        Args:
            exposure_image: ee.Image with exposure values
            aqi_image: ee.Image with AQI values
            max_exposure: Maximum exposure value for color scaling
            max_aqi: Maximum AQI value for color scaling
            
        Returns:
            Dict with tile URLs and tokens
        """
        # Exposure tile (green to red gradient)
        exposure_vis = {
            'min': 0,
            'max': max_exposure,
            'palette': ['#00FF00', '#FFFF00', '#FFA500', '#FF0000', '#800080', '#400020']
        }
        
        # AQI tile (EPA standard colors)
        aqi_vis = {
            'min': 0,
            'max': 500,
            'palette': ['#00E400', '#FFFF00', '#FF7E00', '#FF0000', '#8F3F97', '#7E0023']
        }
        
        try:
            exposure_map = exposure_image.getMapId(exposure_vis)
            aqi_map = aqi_image.getMapId(aqi_vis)
            
            # Extract map IDs from the tile URLs to create proxied endpoints
            import re
            exposure_tile_url = exposure_map['tile_fetcher'].url_format
            aqi_tile_url = aqi_map['tile_fetcher'].url_format
            
            exposure_match = re.search(r'/maps/([^/]+)/tiles/', exposure_tile_url)
            aqi_match = re.search(r'/maps/([^/]+)/tiles/', aqi_tile_url)
            
            if not exposure_match or not aqi_match:
                raise ValueError("Could not extract map ID from GEE tile URL")
            
            exposure_map_id = exposure_match.group(1)
            aqi_map_id = aqi_match.group(1)
            
            # Create proxied tile URLs through our backend to avoid CORS issues
            try:
                from django.conf import settings
                base_url = getattr(settings, 'SITE_URL', None)
                if not base_url:
                    base_url = 'http://localhost:8000'
            except Exception:
                base_url = 'http://localhost:8000'
            
            proxied_exposure_url = f"{base_url}/api/v1/air-quality/gee/proxy/{exposure_map_id}/{{z}}/{{x}}/{{y}}"
            proxied_aqi_url = f"{base_url}/api/v1/air-quality/gee/proxy/{aqi_map_id}/{{z}}/{{x}}/{{y}}"
            
            logger.info(f"[GEE Exposure] Generated proxied tile URLs")
            logger.info(f"[GEE Exposure] Exposure Map ID: {exposure_map_id}")
            logger.info(f"[GEE Exposure] AQI Map ID: {aqi_map_id}")
            
            return {
                'exposure': {
                    'tile_url': proxied_exposure_url,
                    'map_id': exposure_map_id,
                    'token': exposure_map['token'],
                },
                'aqi': {
                    'tile_url': proxied_aqi_url,
                    'map_id': aqi_map_id,
                    'token': aqi_map['token'],
                }
            }
        except Exception as e:
            logger.error(f"Error generating tile URLs: {e}")
            return {
                'exposure': {'tile_url': '', 'map_id': '', 'token': ''},
                'aqi': {'tile_url': '', 'map_id': '', 'token': ''}
            }
    
    def convert_no2_to_surface(self, no2_column_image: ee.Image) -> ee.Image:
        """
        Convert NO2 column density to surface concentration.
        
        Args:
            no2_column_image: ee.Image with NO2 in mol/m²
            
        Returns:
            ee.Image with NO2 in ppb
        """
        # Conversion: mol/m² to ppb
        # Typical NO2 column: 1e-5 mol/m² ≈ 2.5e15 molecules/cm² ≈ 20-50 ppb surface
        # Conversion factor: mol/m² * 2e6 ≈ ppb (assuming 1km boundary layer)
        conversion_factor = 2e6  # Empirical conversion
        return no2_column_image.multiply(conversion_factor).rename('NO2_ppb')
    
    def convert_so2_to_surface(self, so2_column_image: ee.Image) -> ee.Image:
        """
        Convert SO2 column density to surface concentration.
        
        Args:
            so2_column_image: ee.Image with SO2 in mol/m²
            
        Returns:
            ee.Image with SO2 in ppb
        """
        # Typical SO2 column: 1e-5 mol/m² ≈ 10-30 ppb surface
        conversion_factor = 1.5e6  # Empirical conversion
        return so2_column_image.multiply(conversion_factor).rename('SO2_ppb')
    
    def convert_co_to_surface(self, co_column_image: ee.Image) -> ee.Image:
        """
        Convert CO column density to surface concentration.
        
        Args:
            co_column_image: ee.Image with CO in mol/m²
            
        Returns:
            ee.Image with CO in ppm
        """
        # Typical CO column: 0.02 mol/m² ≈ 200-500 ppb surface ≈ 0.2-0.5 ppm
        # Conversion factor: mol/m² * 20 ≈ ppm
        conversion_factor = 20  # Empirical conversion
        return co_column_image.multiply(conversion_factor).rename('CO_ppm')
    
    def estimate_pm25_from_no2(self, no2_column_image: ee.Image) -> ee.Image:
        """
        Estimate PM2.5 from NO2 column density (Sentinel-5P).
        
        Uses empirical relationship between NO2 and PM2.5 observed in urban areas.
        
        Args:
            no2_column_image: ee.Image with NO2 in mol/m²
            
        Returns:
            ee.Image with PM2.5 in µg/m³
        """
        # Convert NO2 column to surface concentration (ppb)
        no2_surface = self.convert_no2_to_surface(no2_column_image)
        
        # Empirical relationship: PM2.5(µg/m³) ≈ NO2(ppb) × 2.0
        # Based on urban pollution studies showing correlation between traffic-related NO2 and PM2.5
        # Typical: 30 ppb NO2 → 60 µg/m³ PM2.5
        pm25_ugm3 = no2_surface.multiply(2.0)
        
        return pm25_ugm3.rename('PM25_ugm3')
    
    def calculate_exposure_for_geometry(
        self,
        geometry: GEOSGeometry,
        target_date: date,
        days_back: int = 7,
        pop_year: int = 2020,
    ) -> GEEExposureResult:
        """
        Calculate pixel-wise exposure for a geometry entirely on GEE.
        
        This is the main entry point for exposure calculation.
        
        Args:
            geometry: Django GEOSGeometry (district polygon)
            target_date: Date for which to calculate exposure
            days_back: Number of days to average satellite data
            pop_year: Year for population data
            
        Returns:
            GEEExposureResult with tile URLs and summary statistics
        """
        errors = []
        
        # Convert Django geometry to GEE geometry
        geojson = geometry.json
        ee_geometry = ee.Geometry(eval(geojson))
        bounds = geometry.extent  # (xmin, ymin, xmax, ymax)
        
        # Date range for satellite data
        end_date = target_date
        start_date = end_date - timedelta(days=days_back)
        
        try:
            # 1. Get satellite data (Sentinel-5P TROPOMI NO2, SO2, CO)
            no2_collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2') \
                .filterDate(start_date.isoformat(), end_date.isoformat()) \
                .filterBounds(ee_geometry) \
                .select('tropospheric_NO2_column_number_density')
            
            so2_collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_SO2') \
                .filterDate(start_date.isoformat(), end_date.isoformat()) \
                .filterBounds(ee_geometry) \
                .select('SO2_column_number_density')
            
            co_collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_CO') \
                .filterDate(start_date.isoformat(), end_date.isoformat()) \
                .filterBounds(ee_geometry) \
                .select('CO_column_number_density')
            
            # Check if collections have data by checking size
            no2_size = no2_collection.size().getInfo()
            so2_size = so2_collection.size().getInfo()
            co_size = co_collection.size().getInfo()
            
            logger.info(f"[GEE Exposure] Collection sizes: NO2={no2_size}, SO2={so2_size}, CO={co_size}")
            
            # Average over time period (only if data available)
            no2_mean = no2_collection.mean() if no2_size > 0 else None
            so2_mean = so2_collection.mean() if so2_size > 0 else None
            co_mean = co_collection.mean() if co_size > 0 else None
            
            # 2. Convert to surface concentrations (only for available data)
            no2_surface = self.convert_no2_to_surface(no2_mean) if no2_mean is not None else None
            so2_surface = self.convert_so2_to_surface(so2_mean) if so2_mean is not None else None
            co_surface = self.convert_co_to_surface(co_mean) if co_mean is not None else None
            
            # Estimate PM2.5 from NO2 (empirical relationship)
            pm25_surface = self.estimate_pm25_from_no2(no2_mean) if no2_mean is not None else None
            
            # 3. Calculate combined AQI pixel-wise
            combined_aqi, dominant_pollutant = self.calculate_combined_aqi_image(
                pm25_image=pm25_surface,
                no2_image=no2_surface,
                so2_image=so2_surface,
                co_image=co_surface,
            )
            
            # 4. Get population data aggregated to satellite resolution
            population = self.get_worldpop_image(year=pop_year, resolution_meters=1113.2)
            
            # 5. Calculate exposure pixel-wise
            exposure = self.calculate_exposure_image(combined_aqi, population)
            
            # 6. Get summary statistics
            stats = self.get_exposure_statistics(
                exposure,
                combined_aqi,
                population,
                ee_geometry,
                scale=1113.2,
            )
            
            # 7. Categorize population by AQI
            pop_categories = self.categorize_population_by_aqi(
                combined_aqi,
                population,
                ee_geometry,
                scale=1113.2,
            )
            
            # 8. Clip images to geometry for visualization
            exposure_clipped = exposure.clip(ee_geometry)
            aqi_clipped = combined_aqi.clip(ee_geometry)
            
            # 9. Generate tile URLs
            tiles = self.generate_tile_urls(
                exposure_clipped,
                aqi_clipped,
                stats['max_exposure'],
                stats['max_aqi'],
            )
            
            # 10. Calculate mean pollutant values
            pollutant_stats = {}
            for img, name in [
                (pm25_surface, 'pm25'),
                (no2_surface, 'no2'),
                (so2_surface, 'so2'),
                (co_surface, 'co'),
            ]:
                if img is None:
                    pollutant_stats[name] = None
                    continue
                    
                try:
                    result = img.reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=ee_geometry,
                        scale=1113.2,
                        maxPixels=1e10,
                        bestEffort=True,
                    ).getInfo()
                    pollutant_stats[name] = result.get(list(result.keys())[0], None) if result else None
                except Exception as e:
                    logger.warning(f"Failed to calculate mean for {name}: {e}")
                    pollutant_stats[name] = None
            
            # 11. Build result
            return GEEExposureResult(
                exposure_tile_url=tiles['exposure']['tile_url'],
                aqi_tile_url=tiles['aqi']['tile_url'],
                map_id=tiles['exposure']['map_id'],
                token=tiles['exposure']['token'],
                total_population=int(stats['total_population']),
                mean_exposure_index=float(stats['mean_exposure']),
                max_exposure_index=float(stats['max_exposure']),
                mean_aqi=float(stats['mean_aqi']),
                max_aqi=float(stats['max_aqi']),
                pop_good=pop_categories.get('good', 0),
                pop_moderate=pop_categories.get('moderate', 0),
                pop_unhealthy_sensitive=pop_categories.get('unhealthy_sensitive', 0),
                pop_unhealthy=pop_categories.get('unhealthy', 0),
                pop_very_unhealthy=pop_categories.get('very_unhealthy', 0),
                pop_hazardous=pop_categories.get('hazardous', 0),
                mean_pm25=pollutant_stats.get('pm25'),
                mean_no2=pollutant_stats.get('no2'),
                mean_so2=pollutant_stats.get('so2'),
                mean_co=pollutant_stats.get('co'),
                dominant_pollutant=dominant_pollutant,
                calculation_date=target_date.isoformat(),
                geometry_bounds={
                    'west': bounds[0],
                    'south': bounds[1],
                    'east': bounds[2],
                    'north': bounds[3],
                },
                resolution_meters=1113.2,
                data_source="gee_gridded",
                errors=errors,
            )
            
        except Exception as e:
            logger.error(f"Error calculating GEE exposure: {e}")
            errors.append(str(e))
            
            # Return empty result with error
            return GEEExposureResult(
                exposure_tile_url="",
                aqi_tile_url="",
                map_id="",
                token="",
                total_population=0,
                mean_exposure_index=0,
                max_exposure_index=0,
                mean_aqi=0,
                max_aqi=0,
                calculation_date=target_date.isoformat(),
                geometry_bounds={},
                errors=errors,
            )


# Singleton instance
_gee_exposure_service: Optional[GEEExposureService] = None


def get_gee_exposure_service() -> GEEExposureService:
    """Get the GEE exposure service singleton."""
    global _gee_exposure_service
    if _gee_exposure_service is None:
        _gee_exposure_service = GEEExposureService()
    return _gee_exposure_service
