"""
MODIS Aerosol Optical Depth (AOD) Service.

Provides access to MODIS MAIAC AOD data for PM2.5 estimation via Google Earth Engine.
AOD is strongly correlated with surface PM2.5 concentrations and serves as a proxy
when ground monitoring is unavailable.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass

import ee

from .gee_auth import ensure_gee_initialized, get_gee_auth
from .gee_constants import (
    SatelliteCollection,
    MODIS_MAIAC_BANDS,
    PAKISTAN_BBOX,
    DEFAULT_RESOLUTION,
    ReducerType,
)

logger = logging.getLogger(__name__)


@dataclass
class AODResult:
    """Result container for MODIS AOD data retrieval."""
    start_date: str
    end_date: str
    geometry: Dict
    aod_047: Optional[float] = None  # Blue band AOD
    aod_055: Optional[float] = None  # Green band AOD (primary for PM2.5)
    min_aod: Optional[float] = None
    max_aod: Optional[float] = None
    stddev_aod: Optional[float] = None
    pixel_count: Optional[int] = None
    estimated_pm25: Optional[float] = None  # Estimated PM2.5 in µg/m³
    image_count: int = 0
    error: Optional[str] = None


class MODISAODService:
    """
    Service for retrieving MODIS MAIAC AOD data for PM2.5 estimation.
    
    MAIAC (Multi-Angle Implementation of Atmospheric Correction) provides
    high-quality AOD at 1km resolution, which can be converted to surface
    PM2.5 concentrations using empirical relationships.
    
    Usage:
        service = MODISAODService()
        
        # Get AOD at a point
        result = service.get_aod_at_point(
            lat=31.5204,
            lon=74.3587,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        # Get estimated PM2.5
        pm25 = result.estimated_pm25
    """
    
    # PM2.5 estimation coefficients (calibrated for South Asia/IGP region)
    # Based on studies: Kumar et al. (2017), Sharma et al. (2019), Mhawish et al. (2020)
    # Lahore/IGP region has higher AOD-PM2.5 relationship due to:
    # - High secondary aerosol formation
    # - Agricultural burning (Oct-Nov)
    # - Thermal inversions (Dec-Feb)
    # - Industrial emissions
    PM25_COEFFICIENTS = {
        'slope': 180.0,       # µg/m³ per AOD unit (IGP studies: 150-250)
        'intercept': 25.0,    # Background PM2.5 (higher for urban Indo-Gangetic Plain)
        'seasonal_factor': {
            'winter': 1.8,    # Oct-Feb (severe inversions, crop burning, AQI 300-500)
            'summer': 1.0,    # Mar-Jun (pre-monsoon dust)
            'monsoon': 0.6,   # Jul-Sep (washout effect)
        },
        'humidity_factor': 0.85,  # Adjustment for hygroscopic growth
        # Regional adjustment for extreme pollution events
        'extreme_event_threshold': 200.0,  # PM2.5 threshold for extreme events
    }
    
    def __init__(self):
        """Initialize the MODIS AOD service."""
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
        """Create an Earth Engine geometry from point or bbox."""
        if bbox:
            return ee.Geometry.Rectangle([
                bbox['west'], bbox['south'],
                bbox['east'], bbox['north']
            ])
        elif lat is not None and lon is not None:
            point = ee.Geometry.Point([lon, lat])
            return point.buffer(buffer_m)
        else:
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
    
    def _get_seasonal_factor(self, date_str: str) -> float:
        """Get seasonal adjustment factor for PM2.5 estimation."""
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            month = dt.month
            
            if month in [10, 11, 12, 1, 2]:
                return self.PM25_COEFFICIENTS['seasonal_factor']['winter']
            elif month in [7, 8, 9]:
                return self.PM25_COEFFICIENTS['seasonal_factor']['monsoon']
            else:
                return self.PM25_COEFFICIENTS['seasonal_factor']['summer']
        except:
            return 1.0
    
    def _estimate_pm25(self, aod: float, date_str: str) -> float:
        """
        Estimate surface PM2.5 from AOD using calibrated empirical relationship.
        
        Formula: PM2.5 = (slope × AOD + intercept) × seasonal_factor
        
        Coefficients calibrated for Indo-Gangetic Plain (IGP) conditions:
        - slope: 180 µg/m³ per AOD (based on Kumar et al. 2017, Mhawish et al. 2020)
        - intercept: 25 µg/m³ (urban IGP background)
        - seasonal factors account for:
            * Winter inversions (Oct-Feb): 1.8x
            * Pre-monsoon dust (Mar-Jun): 1.0x
            * Monsoon washout (Jul-Sep): 0.6x
        
        For AOD = 0.58 in winter: (180 × 0.58 + 25) × 1.8 = 233 µg/m³
        This maps to AQI ~283, consistent with Lahore's typical winter AQI.
        
        Note: For production use, consider ML models with:
        - Planetary Boundary Layer Height (PBLH)
        - Relative Humidity (RH)
        - Wind speed and direction
        - Ground station calibration
        """
        if aod is None or aod < 0:
            return None
        
        seasonal = self._get_seasonal_factor(date_str)
        
        pm25 = (
            self.PM25_COEFFICIENTS['slope'] * aod +
            self.PM25_COEFFICIENTS['intercept']
        ) * seasonal
        
        return max(0, pm25)  # PM2.5 can't be negative
    
    def _apply_qa_filter(self, image: ee.Image) -> ee.Image:
        """
        Apply quality filtering to MAIAC AOD.
        
        MAIAC QA flags:
        - Bit 0-2: Adjacency mask (0=clear)
        - Bit 3-4: Cloud mask (0=clear)
        - Bit 5-7: QA for AOD
        """
        # Select AOD bands and apply scale factor
        aod_055 = image.select('Optical_Depth_055').multiply(0.001)
        aod_047 = image.select('Optical_Depth_047').multiply(0.001)
        
        # Basic QA: filter negative and extreme values
        valid_mask = aod_055.gte(0).And(aod_055.lte(5))
        
        # Create output image with valid data only
        return image.addBands(
            aod_055.updateMask(valid_mask).rename('AOD_055_scaled')
        ).addBands(
            aod_047.updateMask(valid_mask).rename('AOD_047_scaled')
        )
    
    def get_aod_data(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        buffer_m: int = 5000,
        estimate_pm25: bool = True,
    ) -> AODResult:
        """
        Get MODIS MAIAC AOD data for a location or region.
        
        Args:
            start_date: Start date for data retrieval.
            end_date: End date for data retrieval.
            lat: Latitude (for point queries).
            lon: Longitude (for point queries).
            bbox: Bounding box dict (for region queries).
            buffer_m: Buffer radius in meters for point queries.
            estimate_pm25: Whether to estimate PM2.5 from AOD.
            
        Returns:
            AODResult with statistics and optional PM2.5 estimate.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        geometry = self._create_geometry(lat, lon, bbox, buffer_m)
        
        result = AODResult(
            start_date=start_str,
            end_date=end_str,
            geometry={'lat': lat, 'lon': lon, 'bbox': bbox},
        )
        
        try:
            # Get MAIAC collection
            collection = ee.ImageCollection(SatelliteCollection.MODIS_MAIAC.value)
            collection = collection.filterDate(start_str, end_str)
            collection = collection.filterBounds(geometry)
            
            # Apply QA filter
            collection = collection.map(self._apply_qa_filter)
            
            # Get image count
            result.image_count = collection.size().getInfo()
            
            if result.image_count == 0:
                result.error = "No MODIS MAIAC images found for the specified parameters"
                return result
            
            # Create mean composite
            composite = collection.select(['AOD_055_scaled', 'AOD_047_scaled']).mean()
            
            # Calculate statistics
            stats = composite.reduceRegion(
                reducer=ee.Reducer.mean()
                    .combine(ee.Reducer.minMax(), sharedInputs=True)
                    .combine(ee.Reducer.stdDev(), sharedInputs=True)
                    .combine(ee.Reducer.count(), sharedInputs=True),
                geometry=geometry,
                scale=DEFAULT_RESOLUTION['maiac'],
                maxPixels=1e9,
            )
            
            stats_dict = stats.getInfo()
            
            # Extract AOD values
            result.aod_055 = stats_dict.get('AOD_055_scaled_mean')
            result.aod_047 = stats_dict.get('AOD_047_scaled_mean')
            result.min_aod = stats_dict.get('AOD_055_scaled_min')
            result.max_aod = stats_dict.get('AOD_055_scaled_max')
            result.stddev_aod = stats_dict.get('AOD_055_scaled_stdDev')
            result.pixel_count = stats_dict.get('AOD_055_scaled_count')
            
            # Estimate PM2.5
            if estimate_pm25 and result.aod_055 is not None:
                result.estimated_pm25 = self._estimate_pm25(result.aod_055, start_str)
            
        except Exception as e:
            logger.error(f"Error retrieving AOD data: {e}")
            result.error = str(e)
        
        return result
    
    def get_aod_at_point(
        self,
        lat: float,
        lon: float,
        start_date: Union[str, date],
        end_date: Union[str, date],
        buffer_m: int = 5000,
    ) -> AODResult:
        """
        Get AOD data at a specific point.
        
        Args:
            lat: Latitude.
            lon: Longitude.
            start_date: Start date.
            end_date: End date.
            buffer_m: Buffer radius in meters.
            
        Returns:
            AODResult with AOD statistics and PM2.5 estimate.
        """
        return self.get_aod_data(
            start_date=start_date,
            end_date=end_date,
            lat=lat,
            lon=lon,
            buffer_m=buffer_m,
        )
    
    def get_aod_for_region(
        self,
        bbox: Dict[str, float],
        start_date: Union[str, date],
        end_date: Union[str, date],
    ) -> AODResult:
        """
        Get AOD data for a bounding box region.
        
        Args:
            bbox: Dict with west, south, east, north.
            start_date: Start date.
            end_date: End date.
            
        Returns:
            AODResult with regional AOD statistics.
        """
        return self.get_aod_data(
            start_date=start_date,
            end_date=end_date,
            bbox=bbox,
        )
    
    def get_time_series(
        self,
        lat: float,
        lon: float,
        start_date: Union[str, date],
        end_date: Union[str, date],
        buffer_m: int = 5000,
    ) -> List[Dict]:
        """
        Get time series of AOD values at a point.
        
        Args:
            lat: Latitude.
            lon: Longitude.
            start_date: Start date.
            end_date: End date.
            buffer_m: Buffer radius in meters.
            
        Returns:
            List of dicts with date, AOD, and estimated PM2.5.
        """
        self._ensure_initialized()
        
        start_str, end_str = self._get_date_range(start_date, end_date)
        geometry = self._create_geometry(lat=lat, lon=lon, buffer_m=buffer_m)
        
        # Get collection
        collection = ee.ImageCollection(SatelliteCollection.MODIS_MAIAC.value)
        collection = collection.filterDate(start_str, end_str)
        collection = collection.filterBounds(geometry)
        collection = collection.map(self._apply_qa_filter)
        
        # Extract values for each image
        def extract_value(img):
            aod_055 = img.select('AOD_055_scaled').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=DEFAULT_RESOLUTION['maiac'],
            ).get('AOD_055_scaled')
            
            aod_047 = img.select('AOD_047_scaled').reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=DEFAULT_RESOLUTION['maiac'],
            ).get('AOD_047_scaled')
            
            return ee.Feature(None, {
                'date': img.date().format('YYYY-MM-dd'),
                'aod_055': aod_055,
                'aod_047': aod_047,
                'system_time': img.get('system:time_start'),
            })
        
        features = collection.map(extract_value)
        
        try:
            result = features.getInfo()
            
            time_series = []
            for feature in result.get('features', []):
                props = feature.get('properties', {})
                aod = props.get('aod_055')
                date_str = props.get('date')
                
                if aod is not None:
                    entry = {
                        'date': date_str,
                        'aod_055': aod,
                        'aod_047': props.get('aod_047'),
                    }
                    
                    # Add PM2.5 estimate
                    pm25 = self._estimate_pm25(aod, date_str)
                    if pm25 is not None:
                        entry['estimated_pm25'] = pm25
                    
                    time_series.append(entry)
            
            # Sort by date
            time_series.sort(key=lambda x: x['date'])
            
            return time_series
            
        except Exception as e:
            logger.error(f"Error getting AOD time series: {e}")
            return []
    
    def calibrate_pm25_model(
        self,
        ground_stations: List[Dict],
        start_date: Union[str, date],
        end_date: Union[str, date],
    ) -> Dict:
        """
        Calibrate PM2.5 estimation model using ground truth data.
        
        This method compares satellite AOD with ground PM2.5 measurements
        to derive location-specific regression coefficients.
        
        Args:
            ground_stations: List of dicts with lat, lon, pm25 measurements.
            start_date: Calibration period start.
            end_date: Calibration period end.
            
        Returns:
            Dict with calibration statistics and updated coefficients.
        """
        self._ensure_initialized()
        
        # This is a placeholder for a full calibration implementation
        # In production, this would:
        # 1. Extract AOD at each ground station
        # 2. Match with concurrent PM2.5 measurements
        # 3. Perform linear regression
        # 4. Calculate R², RMSE, bias
        # 5. Return calibrated coefficients
        
        logger.warning("PM2.5 model calibration not fully implemented")
        
        return {
            'status': 'not_implemented',
            'current_coefficients': self.PM25_COEFFICIENTS,
            'message': 'Full calibration requires ground truth data integration',
        }


# Singleton accessor
_modis_aod_service: Optional[MODISAODService] = None


def get_modis_aod_service() -> MODISAODService:
    """Get the MODIS AOD service singleton."""
    global _modis_aod_service
    if _modis_aod_service is None:
        _modis_aod_service = MODISAODService()
    return _modis_aod_service
