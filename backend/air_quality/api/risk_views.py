"""
API views for Dynamic Pixel-Wise Air Quality Risk.

Endpoints:
- GET /api/risk/tiles/ - Get GEE tile URL for risk visualization
- GET /api/risk/status/ - Get Sentinel-5P update status
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.core.serializers import serialize
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import PollutantReading, AirQualityStation, SystemStatus
from ..services.gee_risk import get_risk_service, RiskCalculationError

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_risk_tiles(request):
    """
    Get GEE tile URL and legend for dynamic risk visualization.
    
    Query Parameters:
    - days: How many days of OpenAQ data to include (default: 7)
    - sentinel_days_back: How far to look for Sentinel-5P images (default: 30)
    - pollutant: Which pollutant to use (default: pm25)
    
    Process:
    1. Query local PostGIS for recent OpenAQ PM2.5 readings
    2. Serialize to GeoJSON
    3. Call GEE risk calculation service
    4. Return tile URL + legend
    
    Returns:
        {
            "success": true,
            "tile_url": "https://earthengine.googleapis.com/v1/...",
            "map_id": "...",
            "token": "...",
            "legend": {
                "title": "Population Exposure Risk",
                "stops": [...],
                ...
            },
            "metadata": {
                "sentinel5p_date": "2024-12-10",
                "openaq_points": 150,
                ...
            }
        }
    """
    try:
        # Parse query parameters
        days = int(request.GET.get('days', 7))
        sentinel_days_back = int(request.GET.get('sentinel_days_back', 30))
        pollutant = request.GET.get('pollutant', 'pm25')
        
        logger.info(
            f"Risk tiles requested: days={days}, "
            f"sentinel_days_back={sentinel_days_back}, pollutant={pollutant}"
        )
        
        # 1. Query local OpenAQ PM2.5 readings from PostGIS
        cutoff_date = timezone.now() - timedelta(days=days)
        
        readings = PollutantReading.objects.filter(
            parameter=pollutant.upper(),
            timestamp__gte=cutoff_date,
            value__isnull=False,
            station__is_active=True  # Only active stations
        ).select_related('station').order_by('-timestamp')
        
        if not readings.exists():
            return Response({
                'success': False,
                'error': f'No {pollutant.upper()} readings found in last {days} days',
                'message': 'Try increasing the "days" parameter or check if stations are active'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 2. Build GeoJSON FeatureCollection
        # Get most recent reading per station to avoid duplicates
        station_latest = {}
        for reading in readings:
            station_id = reading.station_id
            if station_id not in station_latest:
                station_latest[station_id] = reading
        
        geojson_features = []
        for reading in station_latest.values():
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        reading.station.longitude,
                        reading.station.latitude
                    ]
                },
                'properties': {
                    'pm25': float(reading.normalized_value),  # Use normalized value
                    'station_id': reading.station.openaq_location_id,
                    'station_name': reading.station.name,
                    'timestamp': reading.timestamp.isoformat(),
                    'unit': reading.unit,
                }
            }
            geojson_features.append(feature)
        
        openaq_geojson = {
            'type': 'FeatureCollection',
            'features': geojson_features
        }
        
        logger.info(f"Created GeoJSON with {len(geojson_features)} features")
        
        # 3. Call GEE risk calculation service
        risk_service = get_risk_service()
        result = risk_service.calculate_risk_index(
            openaq_geojson=openaq_geojson,
            days_back=sentinel_days_back
        )
        
        # 4. Return response
        return Response({
            'success': True,
            'tile_url': result['tile_url'],
            'map_id': result['map_id'],
            'token': result['token'],
            'legend': result['legend'],
            'metadata': result['metadata'],
            'request_params': {
                'days': days,
                'sentinel_days_back': sentinel_days_back,
                'pollutant': pollutant,
            }
        })
        
    except RiskCalculationError as e:
        logger.error(f"Risk calculation error: {e}")
        return Response({
            'success': False,
            'error': str(e),
            'error_type': 'GEE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_risk_tiles: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e),
            'error_type': 'SERVER_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_risk_status(request):
    """
    Get the current Sentinel-5P update status.
    
    Frontend can poll this endpoint to know when new data is available
    and trigger a tile refresh.
    
    Returns:
        {
            "success": true,
            "status": {
                "image_date": "2024-12-10",
                "last_check": "2024-12-11T08:30:00Z",
                "is_new": false,
                "check_interval_hours": 6
            },
            "is_healthy": true,
            "last_changed": "2024-12-10T14:30:00Z"
        }
    """
    try:
        # Get Sentinel-5P status
        status_obj = SystemStatus.objects.filter(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2
        ).first()
        
        if not status_obj:
            return Response({
                'success': True,
                'status': None,
                'message': 'No status available yet. Background task may not have run.'
            })
        
        return Response({
            'success': True,
            'status': status_obj.value,
            'is_healthy': status_obj.is_healthy,
            'last_checked': status_obj.last_checked.isoformat(),
            'last_changed': status_obj.last_changed.isoformat(),
            'error_message': status_obj.error_message if not status_obj.is_healthy else None
        })
        
    except Exception as e:
        logger.error(f"Error getting risk status: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # Change to appropriate permission in production
def trigger_manual_check(request):
    """
    Manually trigger a Sentinel-5P update check.
    
    Useful for testing or forcing an immediate check.
    
    Returns:
        Task result from check_sentinel5p_updates()
    """
    try:
        from ..tasks import check_sentinel5p_updates
        
        result = check_sentinel5p_updates()
        
        return Response({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Error triggering manual check: {e}", exc_info=True)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
