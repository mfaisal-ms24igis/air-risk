"""
Local Data Service - OpenAQ Data Management
============================================

Handles querying, filtering, and serialization of local OpenAQ
ground station data stored in PostGIS.

This service provides clean abstraction over the database models,
keeping views thin and testable.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.contrib.gis.geos import Point
from django.db.models import QuerySet, Avg, Max
import logging

from apps.core.base_service import BaseService, ServiceResult, GeoSpatialServiceMixin


logger = logging.getLogger(__name__)


class LocalDataService(BaseService, GeoSpatialServiceMixin):
    """
    Service for accessing local OpenAQ ground station data.
    
    Provides methods to:
    - Query recent PM2.5 measurements
    - Filter by geographic region
    - Serialize to GeoJSON for GEE processing
    - Aggregate station statistics
    
    Usage:
        service = LocalDataService()
        result = service.get_recent_pm25_geojson(hours=24)
        
        if result.success:
            geojson = result.data
    """
    
    def get_recent_pm25_geojson(
        self,
        hours: int = 24,
        region_bounds: Optional[List[float]] = None,
        min_stations: int = 3
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Get recent PM2.5 measurements as GeoJSON FeatureCollection.
        
        Args:
            hours: Number of hours to look back
            region_bounds: Optional [west, south, east, north] bounds
            min_stations: Minimum number of stations required
            
        Returns:
            ServiceResult containing GeoJSON FeatureCollection
        """
        try:
            # Import here to avoid circular dependency during app initialization
            from air_quality.models import PollutantReading, AirQualityStation
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Query recent PM2.5 readings
            queryset = PollutantReading.objects.filter(
                pollutant='pm25',
                timestamp__gte=cutoff_time
            ).select_related('station')
            
            # Apply geographic filter if provided
            if region_bounds:
                west, south, east, north = region_bounds
                queryset = queryset.filter(
                    station__location__x__gte=west,
                    station__location__x__lte=east,
                    station__location__y__gte=south,
                    station__location__y__lte=north
                )
            
            # Get latest reading per station
            station_readings = self._get_latest_per_station(queryset)
            
            # Check minimum stations requirement
            if len(station_readings) < min_stations:
                return ServiceResult.error_result(
                    f"Insufficient stations: found {len(station_readings)}, need {min_stations}",
                    stations_found=len(station_readings)
                )
            
            # Convert to GeoJSON
            geojson = self._readings_to_geojson(station_readings)
            
            self._log_operation(
                "get_recent_pm25_geojson_success",
                level='info',
                stations=len(station_readings),
                hours=hours
            )
            
            return ServiceResult.success_result(
                geojson,
                stations_count=len(station_readings),
                time_range_hours=hours
            )
            
        except Exception as e:
            return self._handle_error("get_recent_pm25_geojson", e)
    
    def get_station_statistics(
        self,
        station_id: int,
        days: int = 7
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Get statistical summary for a specific station.
        
        Args:
            station_id: Station database ID
            days: Number of days to analyze
            
        Returns:
            ServiceResult containing statistics
        """
        try:
            from air_quality.models import PollutantReading
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            readings = PollutantReading.objects.filter(
                station_id=station_id,
                pollutant='pm25',
                timestamp__gte=cutoff_time
            )
            
            stats = readings.aggregate(
                avg_pm25=Avg('value'),
                max_pm25=Max('value'),
                count=Count('id')
            )
            
            return ServiceResult.success_result({
                'station_id': station_id,
                'period_days': days,
                'average_pm25': float(stats['avg_pm25'] or 0),
                'max_pm25': float(stats['max_pm25'] or 0),
                'reading_count': stats['count']
            })
            
        except Exception as e:
            return self._handle_error("get_station_statistics", e)
    
    def _get_latest_per_station(
        self,
        queryset: QuerySet
    ) -> List[Dict[str, Any]]:
        """
        Get the latest reading for each station from a queryset.
        
        Args:
            queryset: Filtered PollutantReading queryset
            
        Returns:
            List of dicts with station and reading info
        """
        # Group by station and get latest
        station_readings = {}
        
        for reading in queryset.order_by('station_id', '-timestamp'):
            station_id = reading.station_id
            
            if station_id not in station_readings:
                station_readings[station_id] = {
                    'station': reading.station,
                    'reading': reading,
                    'timestamp': reading.timestamp,
                    'value': reading.value
                }
        
        return list(station_readings.values())
    
    def _readings_to_geojson(
        self,
        station_readings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Convert station readings to GeoJSON FeatureCollection.
        
        Args:
            station_readings: List of station/reading dicts
            
        Returns:
            GeoJSON FeatureCollection
        """
        features = []
        
        for item in station_readings:
            station = item['station']
            reading = item['reading']
            
            # Extract coordinates
            coords = [station.location.x, station.location.y]
            
            # Build feature
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': coords
                },
                'properties': {
                    'station_id': station.id,
                    'station_name': station.name,
                    'pm25_value': float(reading.value),
                    'timestamp': reading.timestamp.isoformat(),
                    'pollutant': reading.pollutant,
                    'unit': reading.unit
                }
            }
            
            features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': features
        }


# Add Count import at the top
from django.db.models import Count  # noqa
