"""
Sentinel-5P TROPOMI Service for air quality pollutant retrieval.

Provides access to NO2, SO2, CO, O3, and Aerosol Index data from
the TROPOMI instrument on the Sentinel-5P satellite via Google Earth Engine.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass

import ee

from .gee_auth import ensure_gee_initialized, get_gee_auth
from .gee_constants import (
    SatelliteCollection,
    S5P_NO2_BANDS,
    S5P_SO2_BANDS,
    S5P_CO_BANDS,
    S5P_O3_BANDS,
    S5P_AER_AI_BANDS,
    QUALITY_PRESETS,
    QualityFilter,
    PAKISTAN_BBOX,
    DEFAULT_RESOLUTION,
    SATELLITE_UNIT_CONVERSIONS,
    ReducerType,
)

logger = logging.getLogger(__name__)


@dataclass
class S5PResult:
    """Result container for Sentinel-5P data retrieval."""
    parameter: str
    start_date: str
    end_date: str
    geometry: Dict
    mean_value: Optional[float] = None
    median_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    stddev_value: Optional[float] = None
    pixel_count: Optional[int] = None
    unit: str = "mol/m²"
    quality_filter: str = "moderate"
    image_count: int = 0
    error: Optional[str] = None
    weighted_mean_value: Optional[float] = None
    total_population: Optional[float] = None


class TROPOMIService:
    """
    Service for retrieving Sentinel-5P TROPOMI air quality data.
    
    Supports:
    - NO2 (Nitrogen Dioxide) - tropospheric column
    - SO2 (Sulfur Dioxide) - total column
    - CO (Carbon Monoxide) - total column
    - O3 (Ozone) - total column
    - Aerosol Index (UV absorbing aerosols)
    
    Usage:
        service = TROPOMIService()
        
        # Get NO2 for a point
        result = service.get_no2_at_point(
            lat=31.5204,
            lon=74.3587,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        # Get NO2 for a region
        result = service.get_no2_for_region(
            bbox={'west': 74.0, 'south': 31.0, 'east': 75.0, 'north': 32.0},
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
    """
    
    # Map parameter names to collections and bands
    PARAMETER_CONFIG = {
        'NO2': {
            'collection': SatelliteCollection.S5P_NO2_OFFL,
            'bands': S5P_NO2_BANDS,
            'primary_band': 'tropospheric_NO2_column_number_density',
            'qa_band': None,  # No QA band in current collection
            'cloud_band': 'cloud_fraction',
        },
        'SO2': {
            'collection': SatelliteCollection.S5P_SO2_OFFL,
            'bands': S5P_SO2_BANDS,
            'primary_band': 'SO2_column_number_density',
            'qa_band': None,
            'cloud_band': None,
        },
        'CO': {
            'collection': SatelliteCollection.S5P_CO_OFFL,
            'bands': S5P_CO_BANDS,
            'primary_band': 'CO_column_number_density',
            'qa_band': None,
            'cloud_band': None,
        },
        'O3': {
            'collection': SatelliteCollection.S5P_O3_OFFL,
            'bands': S5P_O3_BANDS,
            'primary_band': 'O3_column_number_density',
            'qa_band': None,
            'cloud_band': None,
        },
        'AER_AI': {
            'collection': SatelliteCollection.S5P_AER_AI,
            'bands': S5P_AER_AI_BANDS,
            'primary_band': 'absorbing_aerosol_index',
            'qa_band': None,
            'cloud_band': None,
        },
    }
    
    def __init__(self):
        """Initialize the TROPOMI service."""
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure GEE is initialized."""
        if not self._initialized:
            gee_auth = get_gee_auth()
            if not gee_auth.is_initialized:
                gee_auth.initialize()
            self._initialized = True
    
    def _create_geometry(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        buffer_m: int = 5000,
    ) -> ee.Geometry:
        """
        Create an Earth Engine geometry from point or bbox.
        
        Args:
            lat: Latitude for point geometry.
            lon: Longitude for point geometry.
            bbox: Bounding box dict with west, south, east, north.
            buffer_m: Buffer distance in meters for point geometries.
            
        Returns:
            ee.Geometry object.
        """
        if bbox:
            return ee.Geometry.Rectangle([
                bbox['west'], bbox['south'],
                bbox['east'], bbox['north']
            ])
        elif lat is not None and lon is not None:
            point = ee.Geometry.Point([lon, lat])
            return point.buffer(buffer_m)
        else:
            # Default to Pakistan bbox
            return ee.Geometry.Rectangle([
                PAKISTAN_BBOX['west'], PAKISTAN_BBOX['south'],
                PAKISTAN_BBOX['east'], PAKISTAN_BBOX['north']
            ])
    
    def _get_date_range(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime],
    ) -> Tuple[str, str]:
        """Convert dates to string format for GEE."""
        if isinstance(start_date, (date, datetime)):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, (date, datetime)):
            end_date = end_date.strftime('%Y-%m-%d')
        return start_date, end_date
    
    def _apply_quality_filter(
        self,
        image: ee.Image,
        config: Dict,
        quality: QualityFilter,
    ) -> ee.Image:
        """
        Apply quality and cloud filtering to an image.
        
        Args:
            image: Input ee.Image.
            config: Parameter configuration dict.
            quality: Quality filter settings.
            
        Returns:
            Filtered ee.Image.
        """
        qa_band = config.get('qa_band')
        cloud_band = config.get('cloud_band')
        
        # Start with the image
        filtered = image
        
        # Apply QA filter
        if qa_band and quality.min_qa > 0:
            qa_mask = image.select(qa_band).gte(quality.min_qa)
            filtered = filtered.updateMask(qa_mask)
        
        # Apply cloud filter
        if cloud_band and quality.max_cloud < 1:
            cloud_mask = image.select(cloud_band).lte(quality.max_cloud)
            filtered = filtered.updateMask(cloud_mask)
        
        return filtered
    
    def _get_collection(
        self,
        parameter: str,
        start_date: str,
        end_date: str,
        geometry: ee.Geometry,
        quality_preset: str = 'moderate',
    ) -> Tuple[ee.ImageCollection, Dict, QualityFilter]:
        """
        Get filtered image collection for a parameter.
        
        Args:
            parameter: Pollutant name (NO2, SO2, CO, O3, AER_AI).
            start_date: Start date string.
            end_date: End date string.
            geometry: Region of interest.
            quality_preset: Quality filter preset name.
            
        Returns:
            Tuple of (filtered collection, config, quality filter).
        """
        config = self.PARAMETER_CONFIG.get(parameter.upper())
        if not config:
            raise ValueError(f"Unknown parameter: {parameter}")
        
        quality = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS['moderate'])
        
        # Get collection
        collection = ee.ImageCollection(config['collection'].value)
        
        # Filter by date and bounds
        collection = collection.filterDate(start_date, end_date)
        collection = collection.filterBounds(geometry)
        
        # Apply quality filter to each image
        def apply_qa(img):
            return self._apply_quality_filter(img, config, quality)
        
        filtered = collection.map(apply_qa)
        
        return filtered, config, quality
    
    def get_pollutant_data(
        self,
        parameter: str,
        start_date: Union[str, date],
        end_date: Union[str, date],
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        buffer_m: int = 5000,
        quality_preset: str = 'moderate',
        reducer: ReducerType = ReducerType.MEAN,
        weighted: bool = False,
    ) -> S5PResult:
        """
        Get pollutant data for a location or region.
        
        Args:
            parameter: Pollutant name (NO2, SO2, CO, O3, AER_AI).
            start_date: Start date for data retrieval.
            end_date: End date for data retrieval.
            lat: Latitude (for point queries).
            lon: Longitude (for point queries).
            bbox: Bounding box dict (for region queries).
            buffer_m: Buffer radius in meters for point queries.
            quality_preset: Quality filter preset.
            reducer: Aggregation method for compositing.
            weighted: Calculate population-weighted mean (regions only).
            
        Returns:
            S5PResult with statistics.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        geometry = self._create_geometry(lat, lon, bbox, buffer_m)
        
        result = S5PResult(
            parameter=parameter.upper(),
            start_date=start_str,
            end_date=end_str,
            geometry={'lat': lat, 'lon': lon, 'bbox': bbox},
            quality_filter=quality_preset,
        )
        
        try:
            collection, config, quality = self._get_collection(
                parameter, start_str, end_str, geometry, quality_preset
            )
            
            # Get image count
            result.image_count = collection.size().getInfo()
            
            if result.image_count == 0:
                result.error = "No images found for the specified parameters"
                return result
            
            # Get the primary band
            primary_band = config['primary_band']
            
            # Create composite based on reducer
            if reducer == ReducerType.MEAN:
                composite = collection.select(primary_band).mean()
            elif reducer == ReducerType.MEDIAN:
                composite = collection.select(primary_band).median()
            elif reducer == ReducerType.MAX:
                composite = collection.select(primary_band).max()
            elif reducer == ReducerType.MIN:
                composite = collection.select(primary_band).min()
            else:
                composite = collection.select(primary_band).mean()
            
            # Calculate statistics over the region
            stats = composite.reduceRegion(
                reducer=ee.Reducer.mean()
                    .combine(ee.Reducer.median(), sharedInputs=True)
                    .combine(ee.Reducer.minMax(), sharedInputs=True)
                    .combine(ee.Reducer.stdDev(), sharedInputs=True)
                    .combine(ee.Reducer.count(), sharedInputs=True),
                geometry=geometry,
                scale=DEFAULT_RESOLUTION['s5p'],
                maxPixels=1e9,
            )
            
            stats_dict = stats.getInfo()
            
            # Extract values
            result.mean_value = stats_dict.get(f'{primary_band}_mean')
            result.median_value = stats_dict.get(f'{primary_band}_median')
            result.min_value = stats_dict.get(f'{primary_band}_min')
            result.max_value = stats_dict.get(f'{primary_band}_max')
            result.stddev_value = stats_dict.get(f'{primary_band}_stdDev')
            result.pixel_count = stats_dict.get(f'{primary_band}_count')
            
            # Calculate weighted mean if requested and applicable (regions only)
            if weighted and bbox:
                try:
                    weighted_data = self.get_population_weighted_mean(
                        parameter, start_date, end_date, geometry, quality_preset
                    )
                    result.weighted_mean_value = weighted_data.get('weighted_mean')
                    result.total_population = weighted_data.get('total_population')
                except Exception as e:
                    logger.warning(f"Failed to calculate weighted mean: {e}")
            
            # Set unit
            band_config = config['bands'].get('tropospheric') or config['bands'].get('total')
            if band_config:
                result.unit = band_config.unit
            
        except Exception as e:
            logger.error(f"Error retrieving {parameter} data: {e}")
            result.error = str(e)
        
        return result
    
    def get_no2_at_point(
        self,
        lat: float,
        lon: float,
        start_date: Union[str, date],
        end_date: Union[str, date],
        buffer_m: int = 5000,
        quality_preset: str = 'moderate',
    ) -> S5PResult:
        """
        Get NO2 data at a specific point.
        
        Args:
            lat: Latitude.
            lon: Longitude.
            start_date: Start date.
            end_date: End date.
            buffer_m: Buffer radius in meters.
            quality_preset: Quality filter preset.
            
        Returns:
            S5PResult with NO2 statistics.
        """
        return self.get_pollutant_data(
            parameter='NO2',
            start_date=start_date,
            end_date=end_date,
            lat=lat,
            lon=lon,
            buffer_m=buffer_m,
            quality_preset=quality_preset,
        )
    
    def get_no2_for_region(
        self,
        bbox: Dict[str, float],
        start_date: Union[str, date],
        end_date: Union[str, date],
        quality_preset: str = 'moderate',
    ) -> S5PResult:
        """
        Get NO2 data for a bounding box region.
        
        Args:
            bbox: Dict with west, south, east, north.
            start_date: Start date.
            end_date: End date.
            quality_preset: Quality filter preset.
            
        Returns:
            S5PResult with NO2 statistics.
        """
        return self.get_pollutant_data(
            parameter='NO2',
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
            quality_preset=quality_preset,
        )
    
    def get_time_series(
        self,
        parameter: str,
        lat: float,
        lon: float,
        start_date: Union[str, date],
        end_date: Union[str, date],
        interval_days: int = 1,
        buffer_m: int = 5000,
        quality_preset: str = 'moderate',
    ) -> List[Dict]:
        """
        Get time series of pollutant values at a point.
        
        Args:
            parameter: Pollutant name.
            lat: Latitude.
            lon: Longitude.
            start_date: Start date.
            end_date: End date.
            interval_days: Days between samples.
            buffer_m: Buffer radius in meters.
            quality_preset: Quality filter preset.
            
        Returns:
            List of dicts with date and value.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        geometry = self._create_geometry(lat=lat, lon=lon, buffer_m=buffer_m)
        
        config = self.PARAMETER_CONFIG.get(parameter.upper())
        if not config:
            raise ValueError(f"Unknown parameter: {parameter}")
        
        quality = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS['moderate'])
        primary_band = config['primary_band']
        
        # Get collection
        collection = ee.ImageCollection(config['collection'].value)
        collection = collection.filterDate(start_str, end_str)
        collection = collection.filterBounds(geometry)
        
        # Apply quality filter
        def apply_qa(img):
            return self._apply_quality_filter(img, config, quality)
        
        collection = collection.map(apply_qa)
        
        # Extract values for each image
        def extract_value(img):
            value = img.select(primary_band).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=DEFAULT_RESOLUTION['s5p'],
            ).get(primary_band)
            
            return ee.Feature(None, {
                'date': img.date().format('YYYY-MM-dd'),
                'value': value,
                'system_time': img.get('system:time_start'),
            })
        
        features = collection.map(extract_value)
        
        try:
            result = features.getInfo()
            
            time_series = []
            for feature in result.get('features', []):
                props = feature.get('properties', {})
                if props.get('value') is not None:
                    time_series.append({
                        'date': props.get('date'),
                        'value': props.get('value'),
                        'parameter': parameter.upper(),
                        'unit': config['bands'].get('tropospheric', 
                               config['bands'].get('total')).unit,
                    })
            
            # Sort by date
            time_series.sort(key=lambda x: x['date'])
            
            return time_series
            
        except Exception as e:
            logger.error(f"Error getting time series: {e}")
            return []
    
    def export_composite(
        self,
        parameter: str,
        start_date: Union[str, date],
        end_date: Union[str, date],
        bbox: Optional[Dict[str, float]] = None,
        quality_preset: str = 'moderate',
        output_name: str = None,
        scale: int = 1000,
    ) -> Dict:
        """
        Export a composite image to Google Drive.
        
        Args:
            parameter: Pollutant name.
            start_date: Start date.
            end_date: End date.
            bbox: Region bounding box.
            quality_preset: Quality filter preset.
            output_name: Output file name.
            scale: Export resolution in meters.
            
        Returns:
            Dict with task information.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        geometry = self._create_geometry(bbox=bbox or PAKISTAN_BBOX)
        
        collection, config, _ = self._get_collection(
            parameter, start_str, end_str, geometry, quality_preset
        )
        
        primary_band = config['primary_band']
        composite = collection.select(primary_band).mean()
        
        # Generate output name
        if not output_name:
            output_name = f"{parameter}_{start_str}_{end_str}_composite"
        
        # Create export task
        task = ee.batch.Export.image.toDrive(
            image=composite,
            description=output_name,
            folder='GEE_Exports',
            fileNamePrefix=output_name,
            region=geometry,
            scale=scale,
            crs='EPSG:4326',
            maxPixels=1e10,
        )
        
        task.start()
        
        return {
            'task_id': task.id,
            'status': task.status(),
            'description': output_name,
            'parameter': parameter,
            'start_date': start_str,
            'end_date': end_str,
        }


    def get_population_weighted_mean(
        self,
        parameter: str,
        start_date: Union[str, date],
        end_date: Union[str, date],
        geometry: ee.Geometry,
        quality_preset: str = 'moderate',
    ) -> Dict[str, float]:
        """
        Calculate population-weighted mean for a region.
        
        Formula: Sum(Pixel_Value * Pixel_Pop) / Sum(Pixel_Pop)
        
        Args:
            parameter: Pollutant name.
            start_date: Start date.
            end_date: End date.
            geometry: Region of interest.
            quality_preset: Quality filter preset.
            
        Returns:
            Dict with 'weighted_mean', 'simple_mean', 'total_population'.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        
        # 1. Get Pollutant Image
        collection, config, quality = self._get_collection(
            parameter, start_str, end_str, geometry, quality_preset
        )
        primary_band = config['primary_band']
        pollutant_img = collection.select(primary_band).mean()
        
        # 2. Get Population Image
        # Use 2020 data as it's the most complete global dataset in WorldPop
        # Or use the closest available year to end_date
        pop_collection = ee.ImageCollection(SatelliteCollection.WORLDPOP.value)
        pop_img = pop_collection.filterDate('2020-01-01', '2021-01-01').mean()
        
        # 3. Calculate Weighted Image
        # Multiply pollutant by population
        weighted_img = pollutant_img.multiply(pop_img)
        
        # 4. Reduce Region
        # We need three stats: Sum(Weighted), Sum(Pop), Mean(Pollutant)
        
        # Combine reducers for efficiency
        reducer = ee.Reducer.sum().combine(
            reducer2=ee.Reducer.mean(), sharedInputs=False
        )
        
        # Calculate stats for weighted image (Sum)
        weighted_stats = weighted_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=DEFAULT_RESOLUTION['s5p'],
            maxPixels=1e9,
        )
        
        # Calculate stats for population (Sum)
        pop_stats = pop_img.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=DEFAULT_RESOLUTION['s5p'],
            maxPixels=1e9,
        )
        
        # Calculate simple mean for comparison
        simple_stats = pollutant_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=DEFAULT_RESOLUTION['s5p'],
            maxPixels=1e9,
        )
        
        # Execute info retrieval
        weighted_val = weighted_stats.get(primary_band).getInfo()
        total_pop = pop_stats.get('population').getInfo()
        simple_mean = simple_stats.get(primary_band).getInfo()
        
        if total_pop and total_pop > 0:
            weighted_mean = weighted_val / total_pop
        else:
            weighted_mean = None
            
        # Debug unit retrieval
        band_conf = config['bands'].get('tropospheric') or config['bands'].get('total')
        if band_conf is None:
            logger.error(f"Band config missing for {parameter}. Bands: {config['bands'].keys()}")
            unit = "unknown"
        else:
            unit = band_conf.unit
            
        return {
            'weighted_mean': weighted_mean,
            'simple_mean': simple_mean,
            'total_population': total_pop,
            'unit': unit
        }

# Singleton accessor
_tropomi_service: Optional[TROPOMIService] = None


def get_tropomi_service() -> TROPOMIService:
    """Get the TROPOMI service singleton."""
    global _tropomi_service
    if _tropomi_service is None:
        _tropomi_service = TROPOMIService()
    return _tropomi_service
