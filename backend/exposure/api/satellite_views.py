"""
API views for satellite-based exposure data.

Provides standardized endpoints for:
- Real-time satellite exposure calculations
- City-level exposure metrics
- Dashboard summaries with AQI breakdowns
- Station exposure with ground-satellite fusion
- GeoJSON exports for mapping

All responses follow the standard structure:
{
    "status": "success" | "error",
    "data": <GeoJSON FeatureCollection | Dict>,
    "message": <string>
}
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

from django.db.models import Avg, Sum, Max, Min, Count, F
from django.shortcuts import get_object_or_404
from rest_framework import views, status
from rest_framework.permissions import AllowAny

from air_quality.models import District, AirQualityStation
from air_quality.services.gee_constants import CITY_BBOXES
from air_quality.api.utils import (
    APIResponse, 
    deprecated, 
    FileHygiene,
    get_aqi_color,
    get_aqi_category,
    geometry_to_geojson,
)
from exposure.models import DistrictExposure, ProvinceExposure, NationalExposure
from exposure.services import SatelliteExposureService, DistrictExposureService
from .satellite_serializers import (
    SatelliteExposureSerializer,
    DistrictExposureSatelliteSerializer,
    ProvinceExposureSatelliteSerializer,
    NationalExposureSatelliteSerializer,
)


# =============================================================================
# AQI REFERENCE DATA
# =============================================================================

AQI_INFO: Dict[str, Dict[str, str]] = {
    "Good": {
        "range": "0-50",
        "color": "#00E400",
        "message": "Air quality is satisfactory"
    },
    "Moderate": {
        "range": "51-100",
        "color": "#FFFF00",
        "message": "Acceptable; moderate health concern for sensitive people"
    },
    "Unhealthy for Sensitive Groups": {
        "range": "101-150",
        "color": "#FF7E00",
        "message": "Members of sensitive groups may experience health effects"
    },
    "Unhealthy": {
        "range": "151-200",
        "color": "#FF0000",
        "message": "Everyone may begin to experience health effects"
    },
    "Very Unhealthy": {
        "range": "201-300",
        "color": "#8F3F97",
        "message": "Health alert: everyone may experience serious effects"
    },
    "Hazardous": {
        "range": ">300",
        "color": "#7E0023",
        "message": "Health emergency: entire population affected"
    },
}


# =============================================================================
# SATELLITE EXPOSURE ENDPOINTS
# =============================================================================

class SatelliteExposureView(views.APIView):
    """
    Calculate real-time satellite exposure for any location.
    
    Supports multiple query modes:
    - Point location (lat, lon)
    - Bounding box (minx, miny, maxx, maxy)
    - Predefined city name
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Calculate satellite-based exposure for a location.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            city (str): Predefined city name (lahore, karachi, etc.)
            lat (float): Latitude for point-based query
            lon (float): Longitude for point-based query
            minx (float): Western boundary for bbox query
            miny (float): Southern boundary for bbox query
            maxx (float): Eastern boundary for bbox query
            maxy (float): Northern boundary for bbox query
            date (str): Target date in YYYY-MM-DD format
            days_back (int): Days to look back for satellite data (default: 7)
            
        Returns:
            APIResponse: Standardized response with exposure metrics
        """
        # Extract query parameters
        city = request.query_params.get("city")
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        minx = request.query_params.get("minx")
        date_str = request.query_params.get("date")
        days_back = int(request.query_params.get("days_back", 7))
        
        # Parse target date
        target_date = self._parse_date(date_str)
        if isinstance(target_date, APIResponse):
            return target_date  # Return error response
        
        service = SatelliteExposureService()
        
        try:
            if city:
                exposure = service.calculate_exposure_for_city(
                    city_name=city,
                    target_date=target_date,
                    days_back=days_back
                )
                location_info = {"type": "city", "name": city}
            elif lat and lon:
                exposure = service.calculate_exposure_at_point(
                    longitude=float(lon),
                    latitude=float(lat),
                    target_date=target_date,
                    days_back=days_back
                )
                location_info = {"type": "point", "lat": float(lat), "lon": float(lon)}
            elif minx:
                bbox = self._parse_bbox(request.query_params)
                if isinstance(bbox, APIResponse):
                    return bbox
                exposure = service.calculate_exposure_for_bbox(
                    *bbox,
                    target_date=target_date,
                    days_back=days_back
                )
                location_info = {"type": "bbox", "bounds": bbox}
            else:
                return APIResponse.error(
                    message="Provide city, lat/lon, or bbox parameters",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = SatelliteExposureSerializer(exposure)
            return APIResponse.success(
                data={
                    "target_date": str(target_date),
                    "days_back": days_back,
                    "location": location_info,
                    "exposure": serializer.data,
                },
                message="Satellite exposure calculated successfully"
            )
            
        except ValueError as e:
            return APIResponse.error(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return APIResponse.error(
                message=f"Failed to calculate exposure: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _parse_date(self, date_str: Optional[str]) -> date:
        """
        Parse date string or return yesterday's date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            date: Parsed date or yesterday
        """
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        return date.today() - timedelta(days=1)
    
    def _parse_bbox(self, params: Dict) -> Tuple[float, float, float, float]:
        """
        Parse bounding box from query parameters.
        
        Args:
            params: Query parameters dict
            
        Returns:
            Tuple of (minx, miny, maxx, maxy)
        """
        try:
            return (
                float(params.get("minx")),
                float(params.get("miny")),
                float(params.get("maxx")),
                float(params.get("maxy")),
            )
        except (TypeError, ValueError):
            return APIResponse.error(
                message="Invalid bbox parameters. Provide minx, miny, maxx, maxy as floats.",
                status_code=status.HTTP_400_BAD_REQUEST
            )


class CityExposureView(views.APIView):
    """
    Get exposure metrics for predefined Pakistani cities.
    
    Provides satellite-derived PM2.5, AQI, and population exposure
    for major urban centers.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get exposure for one or all predefined cities.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            city (str): Specific city name (optional, returns all if omitted)
            date (str): Target date in YYYY-MM-DD format
            days_back (int): Days to look back for satellite data (default: 7)
            
        Returns:
            APIResponse: Standardized response with city exposure data
        """
        city = request.query_params.get("city")
        date_str = request.query_params.get("date")
        days_back = int(request.query_params.get("days_back", 7))
        
        # Parse date
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = date.today() - timedelta(days=1)
        
        service = SatelliteExposureService()
        
        # Determine cities to process
        cities = [city.lower()] if city else list(CITY_BBOXES.keys())
        
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        
        for city_name in cities:
            if city_name not in CITY_BBOXES:
                errors.append({
                    "city": city_name,
                    "error": f"Unknown city. Available: {list(CITY_BBOXES.keys())}"
                })
                continue
                
            try:
                exposure = service.calculate_exposure_for_city(
                    city_name=city_name,
                    target_date=target_date,
                    days_back=days_back
                )
                results.append({
                    "city": city_name,
                    "display_name": city_name.title(),
                    "exposure": SatelliteExposureSerializer(exposure).data
                })
            except Exception as e:
                errors.append({"city": city_name, "error": str(e)})
        
        return APIResponse.success(
            data={
                "date": str(target_date),
                "days_back": days_back,
                "cities": results,
                "errors": errors if errors else None,
                "available_cities": list(CITY_BBOXES.keys()),
            },
            message=f"Retrieved exposure for {len(results)} cities"
        )


class AvailableCitiesView(views.APIView):
    """
    List available cities for exposure calculation.
    
    Returns city names and bounding boxes for all predefined
    Pakistani urban centers.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get list of available cities with bounding boxes.
        
        Args:
            request: DRF Request object
            
        Returns:
            APIResponse: List of cities with bbox coordinates
        """
        cities: List[Dict[str, Any]] = []
        for name, bbox in CITY_BBOXES.items():
            cities.append({
                "name": name,
                "display_name": name.title(),
                "bbox": {
                    "west": bbox["west"],
                    "south": bbox["south"],
                    "east": bbox["east"],
                    "north": bbox["north"],
                }
            })
        
        return APIResponse.success(
            data={"cities": cities, "count": len(cities)},
            message="Available cities retrieved"
        )


# =============================================================================
# DASHBOARD ENDPOINTS
# =============================================================================

class DashboardView(views.APIView):
    """
    Dashboard summary endpoint providing key exposure metrics.
    
    Returns national, provincial, and district-level summaries
    with AQI breakdowns for frontend dashboard display.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get dashboard summary data.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            date (str): Target date in YYYY-MM-DD format
            
        Returns:
            APIResponse: Dashboard summary with national, province, and district data
        """
        date_str = request.query_params.get("date")
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            latest = DistrictExposure.objects.order_by("-date").first()
            target_date = latest.date if latest else date.today() - timedelta(days=1)
        
        # Get national summary
        national = NationalExposure.objects.filter(date=target_date).first()
        
        # Get province summaries
        provinces = ProvinceExposure.objects.filter(
            date=target_date
        ).order_by("-mean_aqi")
        
        # Get worst districts (top 10)
        districts = DistrictExposure.objects.filter(
            date=target_date
        ).select_related("district").order_by("-mean_aqi")[:10]
        
        # Get data source breakdown
        source_counts = DistrictExposure.objects.filter(
            date=target_date
        ).values("data_source").annotate(count=Count("id"))
        data_sources = {s["data_source"]: s["count"] for s in source_counts}
        
        # Build response
        response_data: Dict[str, Any] = {
            "date": str(target_date),
            "national": None,
            "provinces": [],
            "worst_districts": [],
            "data_sources": data_sources,
            "aqi_breakdown": [],
        }
        
        if national:
            response_data["national"] = NationalExposureSatelliteSerializer(national).data
            response_data["aqi_breakdown"] = self._get_aqi_breakdown(national)
        
        response_data["provinces"] = ProvinceExposureSatelliteSerializer(
            provinces, many=True
        ).data
        
        response_data["worst_districts"] = DistrictExposureSatelliteSerializer(
            districts, many=True
        ).data
        
        return APIResponse.success(
            data=response_data,
            message="Dashboard data retrieved successfully"
        )
    
    def _get_aqi_breakdown(self, national: NationalExposure) -> List[Dict[str, Any]]:
        """
        Calculate AQI category breakdown with percentages.
        
        Args:
            national: NationalExposure model instance
            
        Returns:
            List of dicts with category info and population data
        """
        total = national.total_population
        if total == 0:
            return []
        
        categories = [
            ("Good", national.pop_good),
            ("Moderate", national.pop_moderate),
            ("Unhealthy for Sensitive Groups", national.pop_usg),
            ("Unhealthy", national.pop_unhealthy),
            ("Very Unhealthy", national.pop_very_unhealthy),
            ("Hazardous", national.pop_hazardous),
        ]
        
        breakdown: List[Dict[str, Any]] = []
        for cat, pop in categories:
            info = AQI_INFO.get(cat, {})
            breakdown.append({
                "category": cat,
                "aqi_range": info.get("range", ""),
                "population": pop,
                "percentage": round(pop / total * 100, 1) if total > 0 else 0,
                "color": info.get("color", "#999"),
                "health_message": info.get("message", ""),
            })
        
        return breakdown


# =============================================================================
# TREND AND TIMESERIES ENDPOINTS
# =============================================================================

class ExposureTrendView(views.APIView):
    """
    Get exposure trends over time for any administrative level.
    
    Supports district, province, or national-level trend analysis.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get exposure trend data over time.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            district (int): District ID for district-level trend
            province (str): Province name for province-level trend
            days (int): Number of days to look back (default: 30)
            
        Returns:
            APIResponse: Trend data with daily metrics
        """
        district_id = request.query_params.get("district")
        province = request.query_params.get("province")
        days = int(request.query_params.get("days", 30))
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        trend: List[Dict[str, Any]] = []
        level = "national"
        
        if district_id:
            level = "district"
            trend = self._get_district_trend(int(district_id), start_date, end_date)
        elif province:
            level = "province"
            trend = self._get_province_trend(province, start_date, end_date)
        else:
            trend = self._get_national_trend(start_date, end_date)
        
        return APIResponse.success(
            data={
                "level": level,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "data_points": len(trend),
                "trend": trend,
            },
            message=f"Retrieved {level} exposure trend"
        )
    
    def _get_district_trend(
        self, 
        district_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get trend data for a district."""
        exposures = DistrictExposure.objects.filter(
            district_id=district_id,
            date__gte=start_date,
            date__lte=end_date
        ).order_by("date")
        
        return [{
            "date": str(exp.date),
            "mean_aqi": exp.mean_aqi,
            "mean_pm25": exp.mean_pm25,
            "exposure_index": exp.exposure_index,
            "pop_at_risk": exp.pop_at_risk,
        } for exp in exposures]
    
    def _get_province_trend(
        self, 
        province: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get trend data for a province."""
        exposures = ProvinceExposure.objects.filter(
            province__iexact=province,
            date__gte=start_date,
            date__lte=end_date
        ).order_by("date")
        
        return [{
            "date": str(exp.date),
            "mean_aqi": exp.mean_aqi,
            "mean_pm25": exp.mean_pm25,
            "exposure_index": exp.exposure_index,
            "pop_at_risk": (
                exp.pop_usg + exp.pop_unhealthy + 
                exp.pop_very_unhealthy + exp.pop_hazardous
            ),
        } for exp in exposures]
    
    def _get_national_trend(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get trend data for national level."""
        exposures = NationalExposure.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).order_by("date")
        
        return [{
            "date": str(exp.date),
            "mean_aqi": exp.mean_aqi,
            "mean_pm25": exp.mean_pm25,
            "exposure_index": exp.exposure_index,
            "pop_at_risk": (
                exp.pop_usg + exp.pop_unhealthy + 
                exp.pop_very_unhealthy + exp.pop_hazardous
            ),
        } for exp in exposures]


# =============================================================================
# STATION EXPOSURE ENDPOINT
# =============================================================================

class StationExposureView(views.APIView):
    """
    Get satellite exposure at ground monitoring station locations.
    
    Useful for comparing satellite estimates with ground truth.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get satellite exposure at station locations.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            station (int): Specific station ID (optional)
            active_only (bool): Only include active stations (default: true)
            date (str): Target date in YYYY-MM-DD format
            days_back (int): Days to look back for satellite data (default: 7)
            limit (int): Maximum stations to process (default: 50)
            
        Returns:
            APIResponse: Station exposure data with satellite metrics
        """
        station_id = request.query_params.get("station")
        active_only = request.query_params.get("active_only", "true").lower() == "true"
        date_str = request.query_params.get("date")
        days_back = int(request.query_params.get("days_back", 7))
        limit = int(request.query_params.get("limit", 50))
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = date.today() - timedelta(days=1)
        
        # Get stations
        stations = AirQualityStation.objects.all()
        if active_only:
            stations = stations.filter(is_active=True)
        if station_id:
            stations = stations.filter(id=station_id)
        
        service = SatelliteExposureService()
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        
        for station in stations[:limit]:
            if not station.location:
                continue
                
            try:
                exposure = service.calculate_exposure_at_point(
                    longitude=station.location.x,
                    latitude=station.location.y,
                    buffer_km=5.0,
                    target_date=target_date,
                    days_back=days_back
                )
                
                results.append({
                    "station_id": station.id,
                    "station_name": station.name or f"Station {station.openaq_id}",
                    "latitude": station.location.y,
                    "longitude": station.location.x,
                    "satellite_pm25": exposure.mean_pm25,
                    "satellite_aqi": exposure.combined_aqi,
                    "satellite_aod": exposure.mean_aod,
                    "population": exposure.total_population,
                    "exposure_index": exposure.mean_exposure_index,
                    "aqi_category": exposure.aqi_category,
                })
            except Exception as e:
                errors.append({
                    "station_id": station.id,
                    "station_name": station.name,
                    "error": str(e),
                })
        
        return APIResponse.success(
            data={
                "date": str(target_date),
                "station_count": len(results),
                "stations": results,
                "errors": errors if errors else None,
            },
            message=f"Retrieved satellite exposure for {len(results)} stations"
        )


# =============================================================================
# GEOJSON EXPORT ENDPOINTS
# =============================================================================

class DistrictExposureGeoJSONView(views.APIView):
    """
    Export district exposure as GeoJSON FeatureCollection.
    
    Optimized for web mapping applications with choropleth styling.
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request) -> APIResponse:
        """
        Get district exposure as GeoJSON.
        
        Args:
            request: DRF Request object
            
        Query Parameters:
            date (str): Target date in YYYY-MM-DD format
            province (str): Filter by province name
            
        Returns:
            APIResponse: GeoJSON FeatureCollection with district exposure
        """
        date_str = request.query_params.get("date")
        province = request.query_params.get("province")
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            latest = DistrictExposure.objects.order_by("-date").first()
            target_date = latest.date if latest else date.today() - timedelta(days=1)
        
        exposures = DistrictExposure.objects.filter(
            date=target_date
        ).select_related("district")
        
        if province:
            exposures = exposures.filter(district__province__iexact=province)
        
        features: List[Dict[str, Any]] = []
        for exp in exposures:
            if not exp.district or not exp.district.geometry:
                continue
                
            feature = {
                "type": "Feature",
                "id": exp.id,
                "properties": {
                    "district_id": exp.district.id,
                    "district_name": exp.district.name,
                    "province": exp.district.province,
                    "date": str(exp.date),
                    "total_population": exp.total_population,
                    "mean_pm25": exp.mean_pm25,
                    "mean_aqi": exp.mean_aqi,
                    "exposure_index": exp.exposure_index,
                    "pop_good": exp.pop_good,
                    "pop_moderate": exp.pop_moderate,
                    "pop_usg": exp.pop_usg,
                    "pop_unhealthy": exp.pop_unhealthy,
                    "pop_very_unhealthy": exp.pop_very_unhealthy,
                    "pop_hazardous": exp.pop_hazardous,
                    "pop_at_risk": exp.pop_at_risk,
                    "data_source": exp.data_source,
                    "aqi_color": get_aqi_color(exp.mean_aqi),
                    "aqi_category": get_aqi_category(exp.mean_aqi),
                },
                "geometry": geometry_to_geojson(exp.district.geometry),
            }
            features.append(feature)
        
        return APIResponse.geojson(
            features=features,
            message=f"Retrieved {len(features)} district exposure features",
            properties={
                "date": str(target_date),
                "province_filter": province,
                "feature_count": len(features),
            }
        )


# =============================================================================
# DEPRECATED ENDPOINTS (marked for removal)
# =============================================================================

# Note: The following endpoints from the legacy views.py are deprecated
# and should be migrated to the new satellite-based endpoints:
#
# - /api/v1/exposure/districts/map_data/ -> Use /api/v1/exposure/geojson/districts/
# - /api/v1/exposure/districts/rankings/ -> Use /api/v1/exposure/dashboard/
# - /api/v1/exposure/hotspots/geojson/ -> Maintained for hotspot visualization
