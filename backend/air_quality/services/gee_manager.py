"""
Satellite Data Manager - Unified interface for all GEE satellite services.

Provides a single entry point for retrieving air quality data from multiple
satellite sources (TROPOMI, MODIS) and combining them with ground station data.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from .gee_auth import get_gee_auth, initialize_gee, GEEAuthError
from .gee_tropomi import TROPOMIService, S5PResult, get_tropomi_service
from .gee_modis import MODISAODService, AODResult, get_modis_aod_service
from .gee_constants import (
    PAKISTAN_BBOX,
    CITY_BBOXES,
    SatelliteCollection,
    DATA_AVAILABILITY,
)

logger = logging.getLogger(__name__)


@dataclass
class SatelliteDataResult:
    """Combined result from multiple satellite sources."""
    
    # Query parameters
    lat: Optional[float] = None
    lon: Optional[float] = None
    bbox: Optional[Dict[str, float]] = None
    start_date: str = ""
    end_date: str = ""
    
    # TROPOMI results
    no2: Optional[S5PResult] = None
    so2: Optional[S5PResult] = None
    co: Optional[S5PResult] = None
    o3: Optional[S5PResult] = None
    aerosol_index: Optional[S5PResult] = None
    
    # MODIS results
    aod: Optional[AODResult] = None
    
    # Combined metrics
    estimated_pm25: Optional[float] = None
    air_quality_index: Optional[int] = None
    dominant_pollutant: Optional[str] = None
    
    # Metadata
    sources_queried: List[str] = field(default_factory=list)
    sources_successful: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    query_time_ms: float = 0.0
    
    @property
    def has_data(self) -> bool:
        """Check if any satellite data was retrieved."""
        return bool(
            self.no2 or self.so2 or self.co or 
            self.o3 or self.aerosol_index or self.aod
        )


class SatelliteDataManager:
    """
    Unified manager for satellite air quality data.
    
    Combines data from:
    - Sentinel-5P TROPOMI (NO2, SO2, CO, O3, Aerosol Index)
    - MODIS MAIAC (AOD for PM2.5 estimation)
    
    Usage:
        manager = SatelliteDataManager()
        
        # Get all available data for a location
        result = manager.get_air_quality_data(
            lat=31.5204,
            lon=74.3587,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        # Access individual pollutants
        print(f"NO2: {result.no2.mean_value} mol/m²")
        print(f"Estimated PM2.5: {result.estimated_pm25} µg/m³")
    """
    
    def __init__(self):
        """Initialize the satellite data manager."""
        self._tropomi: Optional[TROPOMIService] = None
        self._modis: Optional[MODISAODService] = None
        self._initialized = False
    
    def initialize(self, **kwargs) -> bool:
        """
        Initialize the manager and underlying services.
        
        Args:
            **kwargs: Arguments passed to GEE authentication.
            
        Returns:
            True if initialization successful.
        """
        if self._initialized:
            return True
        
        try:
            initialize_gee(**kwargs)
            self._tropomi = get_tropomi_service()
            self._modis = get_modis_aod_service()
            self._initialized = True
            logger.info("SatelliteDataManager initialized successfully")
            return True
        except GEEAuthError as e:
            logger.error(f"Failed to initialize SatelliteDataManager: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the manager is initialized."""
        if not self._initialized:
            self.initialize()
    
    def get_air_quality_data(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        bbox: Optional[Dict[str, float]] = None,
        start_date: Union[str, date] = None,
        end_date: Union[str, date] = None,
        parameters: List[str] = None,
        buffer_m: int = 5000,
        quality_preset: str = 'moderate',
        parallel: bool = True,
        weighted: bool = False,
    ) -> SatelliteDataResult:
        """
        Get comprehensive air quality data from all satellite sources.
        
        Args:
            lat: Latitude for point query.
            lon: Longitude for point query.
            bbox: Bounding box for region query.
            start_date: Start date (defaults to 30 days ago).
            end_date: End date (defaults to today).
            parameters: List of parameters to retrieve. Options:
                        ['NO2', 'SO2', 'CO', 'O3', 'AER_AI', 'AOD']
                        Defaults to all.
            buffer_m: Buffer radius in meters for point queries.
            quality_preset: Quality filter preset.
            parallel: Whether to query sources in parallel.
            weighted: Calculate population-weighted mean (regions only).
            
        Returns:
            SatelliteDataResult with all retrieved data.
        """
        self._ensure_initialized()
        
        import time
        start_time = time.time()
        
        # Set default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Convert dates to strings
        if isinstance(start_date, (date, datetime)):
            start_str = start_date.strftime('%Y-%m-%d')
        else:
            start_str = start_date
            
        if isinstance(end_date, (date, datetime)):
            end_str = end_date.strftime('%Y-%m-%d')
        else:
            end_str = end_date
        
        # Default parameters
        if parameters is None:
            parameters = ['NO2', 'SO2', 'CO', 'O3', 'AER_AI', 'AOD']
        
        parameters = [p.upper() for p in parameters]
        
        # Initialize result
        result = SatelliteDataResult(
            lat=lat,
            lon=lon,
            bbox=bbox,
            start_date=start_str,
            end_date=end_str,
            sources_queried=parameters.copy(),
        )
        
        # Define query functions
        queries = {}
        
        if 'NO2' in parameters:
            queries['NO2'] = lambda: self._tropomi.get_pollutant_data(
                'NO2', start_str, end_str, lat, lon, bbox, buffer_m, quality_preset, weighted=weighted
            )
        
        if 'SO2' in parameters:
            queries['SO2'] = lambda: self._tropomi.get_pollutant_data(
                'SO2', start_str, end_str, lat, lon, bbox, buffer_m, quality_preset, weighted=weighted
            )
        
        if 'CO' in parameters:
            queries['CO'] = lambda: self._tropomi.get_pollutant_data(
                'CO', start_str, end_str, lat, lon, bbox, buffer_m, quality_preset, weighted=weighted
            )
        
        if 'O3' in parameters:
            queries['O3'] = lambda: self._tropomi.get_pollutant_data(
                'O3', start_str, end_str, lat, lon, bbox, buffer_m, quality_preset, weighted=weighted
            )
        
        if 'AER_AI' in parameters:
            queries['AER_AI'] = lambda: self._tropomi.get_pollutant_data(
                'AER_AI', start_str, end_str, lat, lon, bbox, buffer_m, quality_preset, weighted=weighted
            )
        
        if 'AOD' in parameters:
            queries['AOD'] = lambda: self._modis.get_aod_data(
                start_str, end_str, lat, lon, bbox, buffer_m
            )
        
        # Execute queries
        if parallel and len(queries) > 1:
            results_dict = self._execute_parallel(queries)
        else:
            results_dict = self._execute_sequential(queries)
        
        # Assign results
        if 'NO2' in results_dict:
            result.no2 = results_dict['NO2']
            if result.no2 and not result.no2.error:
                result.sources_successful.append('NO2')
            elif result.no2 and result.no2.error:
                result.errors['NO2'] = result.no2.error
        
        if 'SO2' in results_dict:
            result.so2 = results_dict['SO2']
            if result.so2 and not result.so2.error:
                result.sources_successful.append('SO2')
            elif result.so2 and result.so2.error:
                result.errors['SO2'] = result.so2.error
        
        if 'CO' in results_dict:
            result.co = results_dict['CO']
            if result.co and not result.co.error:
                result.sources_successful.append('CO')
            elif result.co and result.co.error:
                result.errors['CO'] = result.co.error
        
        if 'O3' in results_dict:
            result.o3 = results_dict['O3']
            if result.o3 and not result.o3.error:
                result.sources_successful.append('O3')
            elif result.o3 and result.o3.error:
                result.errors['O3'] = result.o3.error
        
        if 'AER_AI' in results_dict:
            result.aerosol_index = results_dict['AER_AI']
            if result.aerosol_index and not result.aerosol_index.error:
                result.sources_successful.append('AER_AI')
            elif result.aerosol_index and result.aerosol_index.error:
                result.errors['AER_AI'] = result.aerosol_index.error
        
        if 'AOD' in results_dict:
            result.aod = results_dict['AOD']
            if result.aod and not result.aod.error:
                result.sources_successful.append('AOD')
                result.estimated_pm25 = result.aod.estimated_pm25
            elif result.aod and result.aod.error:
                result.errors['AOD'] = result.aod.error
        
        # Calculate query time
        result.query_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _execute_parallel(self, queries: Dict) -> Dict:
        """Execute queries in parallel using ThreadPoolExecutor."""
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
            future_to_key = {
                executor.submit(func): key 
                for key, func in queries.items()
            }
            
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error(f"Error querying {key}: {e}")
                    results[key] = None
        
        return results
    
    def _execute_sequential(self, queries: Dict) -> Dict:
        """Execute queries sequentially."""
        results = {}
        
        for key, func in queries.items():
            try:
                results[key] = func()
            except Exception as e:
                logger.error(f"Error querying {key}: {e}")
                results[key] = None
        
        return results
    
    def get_city_air_quality(
        self,
        city: str,
        start_date: Union[str, date] = None,
        end_date: Union[str, date] = None,
        parameters: List[str] = None,
        weighted: bool = False,
    ) -> SatelliteDataResult:
        """
        Get air quality data for a predefined city.
        
        Args:
            city: City name (karachi, lahore, islamabad, etc.)
            start_date: Start date.
            end_date: End date.
            parameters: List of parameters to retrieve.
            weighted: Calculate population-weighted mean.
            
        Returns:
            SatelliteDataResult for the city region.
        """
        city_lower = city.lower()
        
        if city_lower not in CITY_BBOXES:
            raise ValueError(
                f"Unknown city: {city}. Available: {list(CITY_BBOXES.keys())}"
            )
        
        bbox = CITY_BBOXES[city_lower]
        
        return self.get_air_quality_data(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
            weighted=weighted,
        )
    
    def get_pakistan_air_quality(
        self,
        start_date: Union[str, date] = None,
        end_date: Union[str, date] = None,
        parameters: List[str] = None,
    ) -> SatelliteDataResult:
        """
        Get country-wide air quality data for Pakistan.
        
        Args:
            start_date: Start date.
            end_date: End date.
            parameters: List of parameters to retrieve.
            
        Returns:
            SatelliteDataResult for Pakistan.
        """
        return self.get_air_quality_data(
            bbox=PAKISTAN_BBOX,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
        )
    
    def get_station_satellite_data(
        self,
        stations: List[Dict],
        start_date: Union[str, date],
        end_date: Union[str, date],
        parameters: List[str] = None,
        buffer_m: int = 5000,
    ) -> List[Dict]:
        """
        Get satellite data for multiple ground stations.
        
        Args:
            stations: List of dicts with 'lat', 'lon', 'id' keys.
            start_date: Start date.
            end_date: End date.
            parameters: Parameters to retrieve.
            buffer_m: Buffer radius around each station.
            
        Returns:
            List of dicts with station ID and satellite data.
        """
        self._ensure_initialized()
        
        results = []
        
        for station in stations:
            try:
                sat_data = self.get_air_quality_data(
                    lat=station['lat'],
                    lon=station['lon'],
                    start_date=start_date,
                    end_date=end_date,
                    parameters=parameters,
                    buffer_m=buffer_m,
                    parallel=True,
                )
                
                results.append({
                    'station_id': station.get('id'),
                    'station_name': station.get('name'),
                    'lat': station['lat'],
                    'lon': station['lon'],
                    'satellite_data': sat_data,
                })
                
            except Exception as e:
                logger.error(f"Error getting satellite data for station {station}: {e}")
                results.append({
                    'station_id': station.get('id'),
                    'error': str(e),
                })
        
        return results
    
    def test_connection(self) -> Dict:
        """
        Test the satellite data connection.
        
        Returns:
            Dict with connection test results.
        """
        self._ensure_initialized()
        
        gee_auth = get_gee_auth()
        return gee_auth.test_connection()
    
    def get_available_datasets(self) -> Dict:
        """
        Get information about available satellite datasets.
        
        Returns:
            Dict with dataset information.
        """
        return {
            'tropomi': {
                'parameters': ['NO2', 'SO2', 'CO', 'O3', 'AER_AI'],
                'collection': SatelliteCollection.S5P_NO2_OFFL.value,
                'availability': {
                    param: DATA_AVAILABILITY.get(f'S5P_{param}', 'Unknown')
                    for param in ['NO2', 'SO2', 'CO', 'O3', 'AER_AI']
                },
                'resolution': '1.1 km',
                'temporal': 'Daily',
            },
            'modis_maiac': {
                'parameters': ['AOD'],
                'collection': SatelliteCollection.MODIS_MAIAC.value,
                'availability': DATA_AVAILABILITY.get('MODIS_MAIAC', 'Unknown'),
                'resolution': '1 km',
                'temporal': 'Daily',
            },
        }


# Singleton accessor
_satellite_manager: Optional[SatelliteDataManager] = None


def get_satellite_manager() -> SatelliteDataManager:
    """Get the satellite data manager singleton."""
    global _satellite_manager
    if _satellite_manager is None:
        _satellite_manager = SatelliteDataManager()
    return _satellite_manager
