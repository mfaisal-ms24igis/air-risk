"""
Tiered spatial API endpoints for BASIC and PREMIUM users.

Implements access control based on user subscription tier:
- BASIC: District polygons + aggregate AQI only
- PREMIUM: Full pollutant breakdowns, station lists, tile URLs
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.shortcuts import get_object_or_404

from air_quality.models import District, GroundStation
from air_quality.api.serializers import DistrictSerializer
from users.permissions import IsPremiumUser
from air_quality.constants import POLLUTANT_LAYERS


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def districts_list(request):
    """
    List all districts with tiered access.
    
    **BASIC users get:**
    - District name and ID
    - Boundary geometry (simplified)
    - Latest aggregate AQI value only
    
    **PREMIUM users get:**
    - All BASIC features
    - Full geometry (not simplified)
    - Pollutant breakdown
    - Station count
    
    **Query Parameters:**
    - `simplified`: bool (default: auto-detect based on tier)
    """
    is_premium = request.user.is_premium
    simplified = request.GET.get("simplified", "auto")
    
    if simplified == "auto":
        # BASIC users get simplified geometry by default
        simplified = not is_premium
    else:
        simplified = simplified.lower() == "true"
    
    districts = District.objects.all()
    
    # Serialize with tier-appropriate detail
    serializer = DistrictSerializer(
        districts,
        many=True,
        context={
            "request": request,
            "tier": "premium" if is_premium else "basic",
            "simplified": simplified,
        },
    )
    
    return Response({
        "count": districts.count(),
        "tier": request.user.tier,
        "results": serializer.data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def district_detail(request, district_id):
    """
    Get detailed district information with tiered access.
    
    **BASIC users get:**
    - District name, geometry
    - Latest aggregate AQI
    - Province information
    
    **PREMIUM users get:**
    - All BASIC features
    - Pollutant concentrations (NO2, CO, SO2, O3, PM2.5, PM10)
    - Bounding box for map zooming
    - Station list within district
    - Historical trend summary
    
    **Path Parameters:**
    - `district_id`: District ID
    """
    district = get_object_or_404(District, pk=district_id)
    is_premium = request.user.is_premium
    
    # Base response for all users
    response_data = {
        "id": district.id,
        "name": district.name,
        "province": district.province if hasattr(district, 'province') else None,
        "geometry": district.geometry.simplify(0.01) if not is_premium else district.geometry,
        "tier": request.user.tier,
    }
    
    # PREMIUM features
    if is_premium:
        # Bounding box for map zooming
        bounds = district.geometry.extent  # (xmin, ymin, xmax, ymax)
        response_data["bounds"] = {
            "southwest": {"lng": bounds[0], "lat": bounds[1]},
            "northeast": {"lng": bounds[2], "lat": bounds[3]},
        }
        
        # Stations within district
        stations = GroundStation.objects.filter(
            location__within=district.geometry
        ).values("id", "location_id", "name", "latitude", "longitude")
        
        response_data["stations"] = list(stations)
        response_data["station_count"] = len(stations)
        
        # TODO: Add pollutant concentrations from latest exposure snapshot
        # This requires querying ExposureSnapshot model
        response_data["pollutants"] = {
            "note": "Integration with ExposureSnapshot pending"
        }
    
    return Response(response_data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPremiumUser])
def district_tiles(request, district_id):
    """
    Get available pollutant tile URLs for a specific district (PREMIUM ONLY).
    
    Returns GCS-signed URLs for raster tiles clipped to district bounds.
    Tiles are served from Google Cloud Storage with 1-hour expiration.
    
    **Path Parameters:**
    - `district_id`: District ID
    
    **Query Parameters:**
    - `date`: Date in YYYY-MM-DD format (default: latest available)
    - `pollutants`: Comma-separated list (default: all)
    
    **Response:**
    ```json
    {
        "district_id": 123,
        "district_name": "Lahore",
        "date": "2025-12-11",
        "tiles": [
            {
                "pollutant": "NO2",
                "name": "Nitrogen Dioxide",
                "url": "https://storage.googleapis.com/...",
                "expires_at": "2025-12-11T15:00:00Z",
                "legend": {...}
            }
        ]
    }
    ```
    """
    district = get_object_or_404(District, pk=district_id)
    date = request.GET.get("date", None)  # TODO: Get latest date if None
    pollutants_param = request.GET.get("pollutants", None)
    
    # Filter pollutants
    if pollutants_param:
        requested = [p.strip().upper() for p in pollutants_param.split(",")]
        pollutants = [p for p in POLLUTANT_LAYERS if p["code"] in requested]
    else:
        pollutants = POLLUTANT_LAYERS
    
    tiles = []
    
    # TODO: Implement GCS signed URL generation
    # For each pollutant:
    # 1. Check if raster exists in processed_data/{pollutant}/{date}/
    # 2. Generate signed URL with 1-hour expiration
    # 3. Include legend/color scheme from constants
    
    for pollutant in pollutants:
        tiles.append({
            "pollutant": pollutant["code"],
            "name": pollutant["name"],
            "url": f"https://storage.googleapis.com/TODO-implement/{pollutant['code']}",
            "expires_at": "TODO",
            "legend": pollutant.get("legend", {}),
            "status": "pending_implementation",
        })
    
    return Response({
        "district_id": district.id,
        "district_name": district.name,
        "date": date or "latest",
        "bounds": {
            "southwest": {
                "lng": district.geometry.extent[0],
                "lat": district.geometry.extent[1]
            },
            "northeast": {
                "lng": district.geometry.extent[2],
                "lat": district.geometry.extent[3]
            },
        },
        "tiles": tiles,
        "tier": request.user.tier,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stations_nearby(request):
    """
    Find monitoring stations near user location.
    
    **BASIC users:**
    - Max 10 stations
    - Basic info only (name, location, latest AQI)
    
    **PREMIUM users:**
    - Max 50 stations
    - Full info (all pollutants, trends)
    
    **Query Parameters:**
    - `lat`: Latitude (required)
    - `lng`: Longitude (required)
    - `radius_km`: Search radius in km (default: 5, max: 50)
    """
    try:
        lat = float(request.GET.get("lat"))
        lng = float(request.GET.get("lng"))
    except (TypeError, ValueError):
        return Response(
            {"error": "Invalid lat/lng parameters"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    radius_km = min(float(request.GET.get("radius_km", 5)), 50)
    is_premium = request.user.is_premium
    limit = 50 if is_premium else 10
    
    point = Point(lng, lat, srid=4326)
    
    stations = GroundStation.objects.filter(
        location__distance_lte=(point, D(km=radius_km))
    ).distance(point).order_by("distance")[:limit]
    
    results = []
    for station in stations:
        station_data = {
            "id": station.id,
            "location_id": station.location_id,
            "name": station.name,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "distance_km": round(station.distance.km, 2),
        }
        
        # PREMIUM: Add detailed pollutant data
        if is_premium:
            station_data["pollutants"] = "TODO: Latest readings"
        
        results.append(station_data)
    
    return Response({
        "location": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "count": len(results),
        "max_results": limit,
        "tier": request.user.tier,
        "stations": results,
    })
