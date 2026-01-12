"""
GEE Tile Proxy View

Proxies Google Earth Engine tile requests to add authentication.
This allows MapLibre to display GEE tiles without CORS/auth issues.
"""

import logging
import requests
import ee
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from air_quality.services.gee_auth import get_gee_auth

logger = logging.getLogger(__name__)


class GEETileProxyView(APIView):
    """
    Proxy for Google Earth Engine tile requests.
    
    This endpoint proxies tile requests to GEE, adding necessary authentication.
    MapLibre requests tiles through this proxy instead of directly from GEE.
    
    URL Format: /api/v1/air-quality/gee/proxy/{map_id}/{z}/{x}/{y}
    """
    permission_classes = [AllowAny]
    throttle_classes = []  # Disable throttling for tile proxy
    
    @swagger_auto_schema(
        operation_summary="Proxy GEE tile request",
        operation_description="Forward tile request to GEE with authentication",
        tags=["Sentinel-5P GEE Tiles"],
        manual_parameters=[
            openapi.Parameter('map_id', openapi.IN_PATH, description="GEE map ID", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('z', openapi.IN_PATH, description="Zoom level", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('x', openapi.IN_PATH, description="Tile X coordinate", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('y', openapi.IN_PATH, description="Tile Y coordinate", type=openapi.TYPE_INTEGER, required=True),
        ],
    )
    def get(self, request, map_id, z, x, y):
        """
        Proxy a tile request to Google Earth Engine.
        
        Path Parameters:
            map_id (str): GEE map ID from tile URL
            z (str): Zoom level (or {z} template)
            x (str): Tile X coordinate (or {x} template)
            y (str): Tile Y coordinate (or {y} template)
        
        Returns:
            PNG image tile from GEE
        """
        # MapLibre tests URL template with literal {z}/{x}/{y} - return empty tile
        if z in ('{z}', '%7Bz%7D') or x in ('{x}', '%7Bx%7D') or y in ('{y}', '%7By%7D'):
            logger.debug(f"Template test request: {z}/{x}/{y}")
            # Return 1x1 transparent PNG
            import base64
            transparent_png = base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            )
            return HttpResponse(transparent_png, content_type='image/png')
        
        # Ensure GEE is initialized
        gee_auth = get_gee_auth()
        if not gee_auth.is_initialized:
            gee_auth.initialize()
        
        # Construct GEE tile URL
        gee_url = f"https://earthengine-highvolume.googleapis.com/v1/projects/agriprecsion-pakistan/maps/{map_id}/tiles/{z}/{x}/{y}"
        
        try:
            # Get GEE credentials for authorization
            credentials = ee.data.getAssetRoots()[0]  # This ensures we're authenticated
            
            # Get the auth token
            auth_token = None
            try:
                # Try to get the access token from credentials
                if hasattr(ee.data, '_credentials') and ee.data._credentials:
                    if hasattr(ee.data._credentials, 'get_access_token'):
                        token_info = ee.data._credentials.get_access_token()
                        auth_token = token_info.access_token if hasattr(token_info, 'access_token') else token_info
                    elif hasattr(ee.data._credentials, 'token'):
                        auth_token = ee.data._credentials.token
            except Exception as e:
                logger.warning(f"Could not get GEE access token: {e}")
            
            # Build headers
            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            # Forward request to GEE with authentication
            logger.info(f"Requesting GEE tile: {gee_url}")
            response = requests.get(gee_url, headers=headers, timeout=10)
            
            # Log response details
            content_length = len(response.content)
            logger.info(f"GEE response: {response.status_code}, content-length: {content_length}, content-type: {response.headers.get('Content-Type')}")
            
            # Check if tile is likely empty (very small PNG)
            if content_length < 500:
                logger.warning(f"Tile might be empty/transparent: {z}/{x}/{y} - size: {content_length} bytes")
            
            # Return the tile image
            return HttpResponse(
                response.content,
                content_type=response.headers.get('Content-Type', 'image/png'),
                status=response.status_code
            )
            
        except Exception as e:
            logger.error(f"Error proxying GEE tile: {e}")
            return HttpResponse(
                b'',
                content_type='image/png',
                status=500
            )
