"""
API Views - Thin HTTP Handlers
===============================

Views are intentionally thin - they only:
1. Parse HTTP requests
2. Call service layer
3. Format HTTP responses

All business logic lives in services/.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .services import RiskMapService, LocalDataService
from .models import DataFreshness

logger = logging.getLogger(__name__)


@swagger_auto_schema(
    method='get',
    operation_description='Get risk map tiles for current air quality data',
    manual_parameters=[
        openapi.Parameter(
            'hours_back',
            openapi.IN_QUERY,
            description='Hours to look back for ground data (default: 24)',
            type=openapi.TYPE_INTEGER,
            default=24
        ),
        openapi.Parameter(
            'lookback_days',
            openapi.IN_QUERY,
            description='Days to look back for Sentinel-5P data (default: 30)',
            type=openapi.TYPE_INTEGER,
            default=30
        ),
    ],
    responses={
        200: openapi.Response(
            description='Risk map tiles generated successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'tile_url': openapi.Schema(type=openapi.TYPE_STRING),
                    'legend': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'metadata': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            )
        ),
        400: 'Invalid request or insufficient data',
        500: 'Server error during risk calculation'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_risk_tiles(request):
    """
    Generate and return risk map tile URL.
    
    This endpoint:
    1. Queries local OpenAQ data from PostGIS
    2. Sends GeoJSON to RiskMapService
    3. Returns MapLibre-compatible tile URL
    
    Query Parameters:
        - hours_back: Hours to look back for ground data (default: 24)
        - lookback_days: Days for Sentinel-5P lookup (default: 30)
    """
    try:
        # Parse query parameters
        hours_back = int(request.GET.get('hours_back', 24))
        lookback_days = int(request.GET.get('lookback_days', 30))
        
        logger.info(
            f"Risk tiles requested: hours_back={hours_back}, "
            f"lookback_days={lookback_days}"
        )
        
        # Step 1: Get local ground data
        local_service = LocalDataService()
        data_result = local_service.get_recent_pm25_geojson(hours=hours_back)
        
        if not data_result.success:
            return Response(
                {
                    'error': data_result.error,
                    'details': 'Failed to retrieve local ground station data'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 2: Generate risk map
        risk_service = RiskMapService()
        risk_result = risk_service.generate_risk_map(
            openaq_geojson=data_result.data,
            lookback_days=lookback_days
        )
        
        if not risk_result.success:
            return Response(
                {
                    'error': risk_result.error,
                    'details': 'Risk map generation failed'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Step 3: Return successful response
        logger.info("Risk tiles generated successfully")
        
        return Response(risk_result.data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Risk tiles error: {e}", exc_info=True)
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='get',
    operation_description='Get data freshness status for all sources',
    responses={
        200: openapi.Response(
            description='Data freshness status',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'sources': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT)
                    ),
                    'overall_health': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                }
            )
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_data_status(request):
    """
    Get status of all data sources.
    
    Returns freshness information for:
    - Sentinel-5P imagery
    - OpenAQ local data
    - WorldPop data
    - GEE service health
    - Last risk calculation
    """
    try:
        sources = DataFreshness.objects.all()
        
        status_data = {
            'sources': [
                {
                    'source': s.get_source_display(),
                    'status': s.status,
                    'is_healthy': s.is_healthy,
                    'last_check': s.last_check.isoformat() if s.last_check else None,
                    'last_available_date': s.last_available_date.isoformat() if s.last_available_date else None,
                    'status_message': s.status_message,
                    'metadata': s.metadata
                }
                for s in sources
            ],
            'overall_health': all(s.is_healthy for s in sources),
            'checked_at': timezone.now().isoformat()
        }
        
        return Response(status_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Data status error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    operation_description='Manually trigger Sentinel-5P data check',
    responses={
        200: 'Check initiated successfully',
        500: 'Server error during check'
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_manual_check(request):
    """
    Manually trigger data freshness check.
    
    Useful for testing or forcing an immediate update check.
    """
    try:
        from django_q.tasks import async_task
        
        # Queue the task
        task_id = async_task(
            'apps.aqi_monitor.tasks.check_sentinel5p_updates',
            hook='apps.aqi_monitor.tasks.on_check_complete'  # Optional callback
        )
        
        logger.info(f"Manual check queued: task_id={task_id}")
        
        return Response(
            {
                'message': 'Data check queued',
                'task_id': task_id
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Manual check error: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to queue check task'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Import timezone at module level
from django.utils import timezone  # noqa
