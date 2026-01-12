"""API views for exposure data.

This module provides REST endpoints for air quality exposure statistics
at district, province, and national levels.

All responses follow the standard structure:
{
    "status": "success" | "error",
    "data": { ... },
    "message": "Human readable message"
}
"""

from datetime import date, timedelta
from typing import Dict, List, Any, Optional

from django.db.models import F, Count, Sum, Avg
from django_q.tasks import async_task, result
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters import rest_framework as filters

from air_quality.constants import Pollutant, AQI_COLORS
from air_quality.api.utils import APIResponse, deprecated
from air_quality.models import District
from ..models import DistrictExposure, Hotspot, ProvinceExposure, NationalExposure
from ..services.gee_exposure import get_gee_exposure_service, GEEExposureResult
from .serializers import (
    DistrictExposureSerializer,
    DistrictExposureMapSerializer,
    HotspotSerializer,
    HotspotListSerializer,
    ProvinceExposureSerializer,
    NationalExposureSerializer,
    ExposureRankingSerializer,
    ExposureTimeSeriesSerializer,
)


# =============================================================================
# FILTERS
# =============================================================================

class DistrictExposureFilter(filters.FilterSet):
    """
    Filter for district exposure queries.
    
    Attributes:
        pollutant: Filter by pollutant type (case-insensitive)
        province: Filter by province name
        start_date: Filter exposures from this date
        end_date: Filter exposures until this date
        min_rank: Filter by minimum rank (1=worst)
    """
    pollutant = filters.CharFilter(lookup_expr="iexact")
    province = filters.CharFilter(field_name="district__province", lookup_expr="iexact")
    start_date = filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="date", lookup_expr="lte")
    min_rank = filters.NumberFilter(field_name="rank", lookup_expr="lte")

    class Meta:
        model = DistrictExposure
        fields = ["pollutant", "district", "date"]


class HotspotFilter(filters.FilterSet):
    """
    Filter for pollution hotspot queries.
    
    Attributes:
        pollutant: Filter by pollutant type
        severity: Filter by severity level
        start_date: Filter hotspots from this date
        end_date: Filter hotspots until this date
        min_population: Filter by minimum affected population
    """
    pollutant = filters.CharFilter(lookup_expr="iexact")
    severity = filters.CharFilter(lookup_expr="iexact")
    start_date = filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = filters.DateFilter(field_name="date", lookup_expr="lte")
    min_population = filters.NumberFilter(
        field_name="affected_population", lookup_expr="gte"
    )

    class Meta:
        model = Hotspot
        fields = ["pollutant", "severity", "date"]


# =============================================================================
# VIEWSETS
# =============================================================================

class DistrictExposureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    District-level exposure data.
    
    Provides PM2.5, AQI, and population exposure statistics for all 154 districts.
    
    **Filters:**
    - `province`: Filter by province name (e.g., PUNJAB, SINDH)
    - `date`: Filter by date (YYYY-MM-DD)
    - `min_aqi`: Minimum AQI threshold
    - `max_aqi`: Maximum AQI threshold
    """

    queryset = DistrictExposure.objects.select_related("district").all()
    permission_classes = [AllowAny]
    filterset_class = DistrictExposureFilter

    def get_serializer_class(self):
        """
        Get appropriate serializer based on action.
        
        Returns:
            Serializer class for the current action
        """
        if self.action == "map_data":
            return DistrictExposureMapSerializer
        return DistrictExposureSerializer

    def get_queryset(self):
        """
        Get filtered queryset ordered by date and rank.
        
        Returns:
            QuerySet: Ordered district exposure queryset
        """
        queryset = super().get_queryset()
        return queryset.order_by("-date", "rank")

    def list(self, request, *args, **kwargs):
        """
        List district exposures with standardized response.
        
        Returns:
            APIResponse: Paginated list of district exposures
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return APIResponse.success(
                data=serializer.data,
                message=f"Retrieved {len(serializer.data)} district exposures"
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} district exposures"
        )

    @action(detail=False, methods=["get"])
    def latest(self, request) -> Response:
        """
        Get latest exposure data for all districts.

        Query Parameters:
            pollutant (str): Filter by pollutant (default: PM25)
            
        Returns:
            APIResponse: Latest district exposures
        """
        pollutant = request.query_params.get("pollutant", "PM25")

        latest = (
            DistrictExposure.objects.filter(pollutant=pollutant.upper())
            .order_by("-date")
            .first()
        )

        if not latest:
            return APIResponse.error(
                message="No exposure data available",
                status_code=status.HTTP_404_NOT_FOUND
            )

        exposures = (
            DistrictExposure.objects.filter(
                pollutant=pollutant.upper(), date=latest.date
            )
            .select_related("district")
            .order_by("rank")
        )

        serializer = DistrictExposureSerializer(exposures, many=True)
        return APIResponse.success(
            data={
                "date": str(latest.date),
                "pollutant": pollutant.upper(),
                "count": exposures.count(),
                "results": serializer.data,
            },
            message=f"Retrieved latest {pollutant} exposure for {exposures.count()} districts"
        )

    @action(detail=False, methods=["get"])
    def timeseries(self, request) -> Response:
        """
        Get exposure time series for a district.

        Query Parameters:
            district (int): District ID (required)
            pollutant (str): Pollutant code
            days (int): Number of days (default 30)
            
        Returns:
            APIResponse: Time series data for the district
        """
        district_id = request.query_params.get("district")
        pollutant = request.query_params.get("pollutant", "PM25")
        days = int(request.query_params.get("days", 30))

        if not district_id:
            return APIResponse.error(
                message="district parameter required",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        exposures = DistrictExposure.objects.filter(
            district_id=district_id,
            pollutant=pollutant.upper(),
            date__gte=start_date,
            date__lte=end_date,
        ).order_by("date")

        data: List[Dict[str, Any]] = []
        for exp in exposures:
            data.append({
                "date": str(exp.date),
                "concentration_mean": exp.concentration_mean,
                "aqi_mean": exp.aqi_mean,
                "exposure_index": exp.exposure_index,
                "pop_at_risk": exp.pop_at_risk,
            })

        return APIResponse.success(
            data={
                "district_id": int(district_id),
                "pollutant": pollutant.upper(),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "timeseries": data,
            },
            message=f"Retrieved {len(data)} data points for district {district_id}"
        )


class HotspotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for pollution hotspots.

    Returns hotspot data including GeoJSON for map display.
    """

    queryset = Hotspot.objects.all()
    permission_classes = [AllowAny]
    filterset_class = HotspotFilter

    def get_serializer_class(self):
        """Get serializer based on action."""
        if self.action == "list":
            return HotspotListSerializer
        return HotspotSerializer

    def get_queryset(self):
        """Get ordered queryset."""
        queryset = super().get_queryset()
        return queryset.order_by("-date", "-affected_population")

    def list(self, request, *args, **kwargs):
        """List hotspots with standardized response."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return APIResponse.success(
                data=serializer.data,
                message=f"Retrieved {len(serializer.data)} hotspots"
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} hotspots"
        )

    @action(detail=False, methods=["get"])
    def geojson(self, request) -> Response:
        """
        Get hotspots as GeoJSON FeatureCollection.
        
        Query Parameters:
            pollutant (str): Filter by pollutant
            date (str): Target date
        """
        pollutant = request.query_params.get("pollutant", "PM25")
        target_date = request.query_params.get("date")

        if target_date:
            dt = date.fromisoformat(target_date)
        else:
            latest = (
                Hotspot.objects.filter(pollutant=pollutant.upper())
                .order_by("-date")
                .first()
            )
            dt = latest.date if latest else date.today() - timedelta(days=1)

        hotspots = Hotspot.objects.filter(
            pollutant=pollutant.upper(), date=dt
        ).prefetch_related("affected_districts")

        serializer = HotspotSerializer(hotspots, many=True)
        
        return APIResponse.geojson(
            features=serializer.data,
            message=f"Retrieved {len(serializer.data)} hotspots",
            properties={"date": str(dt), "pollutant": pollutant.upper()}
        )

    @action(detail=False, methods=["get"])
    def summary(self, request) -> Response:
        """
        Get hotspot summary statistics.
        
        Query Parameters:
            pollutant (str): Pollutant code
            days (int): Number of days (default 7)
        """
        pollutant = request.query_params.get("pollutant", "PM25")
        days = int(request.query_params.get("days", 7))

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        summary = Hotspot.objects.filter(
            pollutant=pollutant.upper(), 
            date__gte=start_date, 
            date__lte=end_date
        ).aggregate(
            total_hotspots=Count("id"),
            total_affected_pop=Sum("affected_population"),
            avg_aqi=Avg("aqi_mean"),
            critical_count=Count("id", filter=F("severity") == "CRITICAL"),
            severe_count=Count("id", filter=F("severity") == "SEVERE"),
        )

        return APIResponse.success(
            data={
                "pollutant": pollutant.upper(),
                "period": f"{start_date} to {end_date}",
                **summary,
            },
            message="Hotspot summary retrieved"
        )


class ProvinceExposureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Province-level aggregated exposure data.
    
    Provides population-weighted AQI and exposure statistics aggregated at province level.
    Data includes rankings by air quality severity.
    """

    queryset = ProvinceExposure.objects.all()
    serializer_class = ProvinceExposureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Get filtered and ordered queryset."""
        queryset = super().get_queryset()
        # Handle swagger schema generation (no request object)
        if getattr(self, 'swagger_fake_view', False) or not self.request:
            return queryset.order_by("-date", "rank")
        pollutant = self.request.query_params.get("pollutant")
        if pollutant:
            queryset = queryset.filter(pollutant=pollutant.upper())
        return queryset.order_by("-date", "rank")

    def list(self, request, *args, **kwargs):
        """List province exposures with standardized response."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} province exposures"
        )

    @action(detail=False, methods=["get"])
    def latest(self, request) -> Response:
        """
        Get latest province exposures.
        
        Query Parameters:
            pollutant (str): Pollutant code (default: PM25)
        """
        pollutant = request.query_params.get("pollutant", "PM25")

        latest = (
            ProvinceExposure.objects.filter(pollutant=pollutant.upper())
            .order_by("-date")
            .first()
        )

        if not latest:
            return APIResponse.error(
                message="No province exposure data available",
                status_code=status.HTTP_404_NOT_FOUND
            )

        exposures = ProvinceExposure.objects.filter(
            pollutant=pollutant.upper(), date=latest.date
        ).order_by("rank")

        serializer = ProvinceExposureSerializer(exposures, many=True)
        return APIResponse.success(
            data={
                "date": str(latest.date),
                "pollutant": pollutant.upper(),
                "results": serializer.data,
            },
            message=f"Retrieved latest {pollutant} exposure for {exposures.count()} provinces"
        )


class NationalExposureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    National-level exposure summary.
    
    Provides aggregate statistics for all of Pakistan including:
    - Population-weighted AQI and PM2.5
    - Population breakdown by AQI category
    - Worst affected districts
    """

    queryset = NationalExposure.objects.all()
    serializer_class = NationalExposureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Get filtered and ordered queryset."""
        queryset = super().get_queryset()
        # Handle swagger schema generation (no request object)
        if getattr(self, 'swagger_fake_view', False) or not self.request:
            return queryset.order_by("-date")
        pollutant = self.request.query_params.get("pollutant")
        if pollutant:
            queryset = queryset.filter(pollutant=pollutant.upper())
        return queryset.order_by("-date")

    def list(self, request, *args, **kwargs):
        """List national exposures with standardized response."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message=f"Retrieved {len(serializer.data)} national exposure records"
        )

    @action(detail=False, methods=["get"])
    def latest(self, request) -> Response:
        """
        Get latest national exposure for all pollutants.
        
        Returns:
            APIResponse: Latest national exposure for each pollutant
        """
        results: Dict[str, Any] = {}

        for pollutant in Pollutant:
            latest = (
                NationalExposure.objects.filter(pollutant=pollutant.value)
                .order_by("-date")
                .first()
            )

            if latest:
                results[pollutant.value] = NationalExposureSerializer(latest).data

        return APIResponse.success(
            data=results,
            message=f"Retrieved latest national exposure for {len(results)} pollutants"
        )

    @action(detail=False, methods=["get"])
    def population_breakdown(self, request) -> Response:
        """
        Get population breakdown by AQI category.
        
        Query Parameters:
            pollutant (str): Pollutant code (default: PM25)
            date (str): Target date
        """
        pollutant = request.query_params.get("pollutant", "PM25")
        target_date = request.query_params.get("date")

        if target_date:
            dt = date.fromisoformat(target_date)
        else:
            latest = (
                NationalExposure.objects.filter(pollutant=pollutant.upper())
                .order_by("-date")
                .first()
            )
            dt = latest.date if latest else None

        if not dt:
            return APIResponse.error(
                message="No national exposure data available",
                status_code=status.HTTP_404_NOT_FOUND
            )

        national = NationalExposure.objects.filter(
            pollutant=pollutant.upper(), date=dt
        ).first()

        if not national:
            return APIResponse.error(
                message="No data for specified date",
                status_code=status.HTTP_404_NOT_FOUND
            )

        total = national.total_population
        categories = [
            ("Good", national.pop_good, AQI_COLORS.get("Good", "#00E400")),
            ("Moderate", national.pop_moderate, AQI_COLORS.get("Moderate", "#FFFF00")),
            ("USG", national.pop_usg, AQI_COLORS.get("USG", "#FF7E00")),
            ("Unhealthy", national.pop_unhealthy, AQI_COLORS.get("Unhealthy", "#FF0000")),
            ("Very Unhealthy", national.pop_very_unhealthy, AQI_COLORS.get("Very Unhealthy", "#8F3F97")),
            ("Hazardous", national.pop_hazardous, AQI_COLORS.get("Hazardous", "#7E0023")),
        ]

        breakdown: List[Dict[str, Any]] = []
        for cat, pop, color in categories:
            breakdown.append({
                "category": cat,
                "population": pop,
                "percentage": round((pop / total * 100), 1) if total > 0 else 0,
                "color": color,
            })

        return APIResponse.success(
            data={
                "date": str(dt),
                "pollutant": pollutant.upper(),
                "total_population": total,
                "breakdown": breakdown,
            },
            message="Population breakdown retrieved"
        )


# =============================================================================
# GEE-BASED EXPOSURE CALCULATION
# =============================================================================

from rest_framework.views import APIView


class CalculateGEEExposureView(APIView):
    """
    Calculate pixel-wise exposure using Google Earth Engine.
    
    All calculations are performed server-side on GEE. Returns tile URLs
    for visualization and summary statistics without downloading raster data.
    
    **POST /api/v1/exposure/calculate-gee/**
    
    Request body:
    ```json
    {
        "scope": "district" | "province" | "national",
        "district_ids": [1, 2, 3],  // Optional: specific district IDs
        "province": "Punjab",        // Optional: all districts in province
        "target_date": "2024-01-15", // Optional: defaults to today
        "days_back": 7,              // Optional: days to average (default: 7)
        "save_results": true         // Optional: save to database (default: false)
    }
    ```
    
    Response:
    ```json
    {
        "status": "success",
        "data": {
            "results": [
                {
                    "district_id": 1,
                    "district_name": "Lahore",
                    "exposure_tile_url": "https://earthengine.googleapis.com/...",
                    "aqi_tile_url": "https://earthengine.googleapis.com/...",
                    "statistics": {
                        "total_population": 11126285,
                        "mean_exposure_index": 234.5,
                        "max_exposure_index": 456.7,
                        "mean_aqi": 178.3,
                        "max_aqi": 285.0,
                        "population_breakdown": {
                            "good": 0,
                            "moderate": 1200000,
                            "unhealthy_sensitive": 4500000,
                            "unhealthy": 5426285,
                            "very_unhealthy": 0,
                            "hazardous": 0
                        }
                    }
                }
            ],
            "calculation_date": "2024-01-15",
            "data_source": "gee_gridded"
        },
        "message": "Calculated exposure for 1 district(s)"
    }
    ```
    """
    permission_classes = [AllowAny]
    
    def post(self, request) -> Response:
        """Calculate GEE-based exposure for districts, provinces, or nationally."""
        # Parse request parameters
        scope = request.data.get('scope', 'district')
        district_ids = request.data.get('district_ids', [])
        province = request.data.get('province')
        target_date_str = request.data.get('target_date')
        days_back = int(request.data.get('days_back', 7))
        save_results = request.data.get('save_results', False)
        async_mode = request.data.get('async', False)
        
        # Parse target date
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                return APIResponse.error(
                    message="Invalid date format. Use YYYY-MM-DD",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = date.today()
        
        # Get districts based on scope
        districts = []
        
        if scope == 'district' and district_ids:
            districts = District.objects.filter(id__in=district_ids)
        elif scope == 'province' and province:
            districts = District.objects.filter(province__iexact=province)
        elif scope == 'national':
            districts = District.objects.all()
        else:
            return APIResponse.error(
                message="Invalid scope or missing parameters. Provide district_ids, province, or scope='national'",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        if not districts.exists():
            return APIResponse.error(
                message="No districts found matching criteria",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # For large batches (province/national), use async mode by default
        if (scope in ['province', 'national']) and districts.count() > 5 and not async_mode:
            async_mode = True
        
        # Handle async mode for large batches
        if async_mode:
            from ..tasks import calculate_gee_exposure_batch
            
            # Submit async task
            task_id = async_task(
                calculate_gee_exposure_batch,
                district_ids=[d.id for d in districts] if district_ids else None,
                province=province,
                target_date=target_date.isoformat(),
                days_back=days_back,
                save_to_db=save_results,
                task_name=f"GEE Exposure Calculation - {scope} - {target_date.isoformat()}",
            )
            
            return APIResponse.success(
                data={
                    'task_id': task_id,
                    'status': 'processing',
                    'scope': scope,
                    'district_count': districts.count(),
                    'calculation_date': target_date.isoformat(),
                    'message': 'Task submitted. Use task_id to check status at /api/v1/exposure/calculate-gee/status/?task_id={task_id}',
                },
                message=f"Async calculation started for {districts.count()} district(s)"
            )
        
        # Synchronous mode - calculate exposure for each district
        gee_service = get_gee_exposure_service()
        results = []
        
        for district in districts:
            try:
                # Calculate exposure on GEE
                gee_result: GEEExposureResult = gee_service.calculate_exposure_for_geometry(
                    geometry=district.geometry,
                    target_date=target_date,
                    days_back=days_back,
                )
                
                # Format result
                district_result = {
                    'district_id': district.id,
                    'district_name': district.name,
                    'province': district.province,
                    'exposure_tile_url': gee_result.exposure_tile_url,
                    'aqi_tile_url': gee_result.aqi_tile_url,
                    'map_id': gee_result.map_id,
                    'token': gee_result.token,
                    'statistics': {
                        'total_population': gee_result.total_population,
                        'mean_exposure_index': gee_result.mean_exposure_index,
                        'max_exposure_index': gee_result.max_exposure_index,
                        'mean_aqi': gee_result.mean_aqi,
                        'max_aqi': gee_result.max_aqi,
                        'population_breakdown': {
                            'good': gee_result.pop_good,
                            'moderate': gee_result.pop_moderate,
                            'unhealthy_sensitive': gee_result.pop_unhealthy_sensitive,
                            'unhealthy': gee_result.pop_unhealthy,
                            'very_unhealthy': gee_result.pop_very_unhealthy,
                            'hazardous': gee_result.pop_hazardous,
                        },
                        'pollutants': {
                            'pm25': gee_result.mean_pm25,
                            'no2': gee_result.mean_no2,
                            'so2': gee_result.mean_so2,
                            'co': gee_result.mean_co,
                        },
                        'dominant_pollutant': gee_result.dominant_pollutant,
                    },
                    'errors': gee_result.errors if gee_result.errors else [],
                }
                
                # Save to database if requested
                if save_results and not gee_result.errors:
                    DistrictExposure.objects.update_or_create(
                        district=district,
                        date=target_date,
                        pollutant='PM25',  # Primary pollutant
                        defaults={
                            'concentration_mean': gee_result.mean_pm25 or 0,
                            'aqi_mean': gee_result.mean_aqi,
                            'aqi_max': int(gee_result.max_aqi),
                            'exposure_index': gee_result.mean_exposure_index,
                            'total_population': gee_result.total_population,
                            'pop_good': gee_result.pop_good,
                            'pop_moderate': gee_result.pop_moderate,
                            'pop_usg': gee_result.pop_unhealthy_sensitive,
                            'pop_unhealthy': gee_result.pop_unhealthy,
                            'pop_very_unhealthy': gee_result.pop_very_unhealthy,
                            'pop_hazardous': gee_result.pop_hazardous,
                            'data_source': 'gee_gridded',
                            'mean_pm25': gee_result.mean_pm25,
                        }
                    )
                
                results.append(district_result)
                
            except Exception as e:
                results.append({
                    'district_id': district.id,
                    'district_name': district.name,
                    'error': str(e),
                })
        
        return APIResponse.success(
            data={
                'results': results,
                'calculation_date': target_date.isoformat(),
                'days_averaged': days_back,
                'data_source': 'gee_gridded',
                'saved_to_database': save_results,
            },
            message=f"Calculated exposure for {len(results)} district(s)"
        )
    
    def get(self, request) -> Response:
        """
        Check status of async GEE exposure calculation task.
        
        Query Parameters:
            task_id (str): Task ID from POST request
            
        Returns:
            Task status and results if complete
        """
        task_id = request.query_params.get('task_id')
        
        if not task_id:
            return APIResponse.error(
                message="task_id parameter is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Try to get task result
            task_result = result(task_id, wait=0)  # Don't wait, return immediately
            
            if task_result is None:
                # Task is still running or doesn't exist
                return APIResponse.success(
                    data={
                        'task_id': task_id,
                        'status': 'processing',
                        'message': 'Task is still processing. Check again in a few moments.',
                    },
                    message="Task in progress"
                )
            else:
                # Task is complete
                return APIResponse.success(
                    data={
                        'task_id': task_id,
                        'status': 'completed',
                        'results': task_result,
                    },
                    message="Task completed successfully"
                )
                
        except Exception as e:
            return APIResponse.error(
                message=f"Error checking task status: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
