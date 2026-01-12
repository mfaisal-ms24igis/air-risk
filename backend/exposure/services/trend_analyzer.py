"""
Trend analysis service for location-based air quality assessment.

Analyzes temporal trends in pollutant concentrations using:
- OpenAQ ground station readings (30-day max history)
- GEE Sentinel-5P satellite data
- District exposure data for historical trends
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D, Distance
from django.contrib.gis.db.models.functions import Distance as DistanceFunc
from django.db.models import Avg, Max, Min, Q
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

from air_quality.models import AirQualityStation, PollutantReading, District
from exposure.models import DistrictExposure
from air_quality.constants import Pollutant


class TrendAnalyzer:
    """
    Analyzes air quality trends for a specific location and time range.
    """
    
    def __init__(
        self,
        lat: float,
        lng: float,
        radius_km: float = 5.0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Initialize trend analyzer for a location.
        
        Args:
            lat: Latitude in decimal degrees
            lng: Longitude in decimal degrees
            radius_km: Search radius in kilometers (default: 5km)
            start_date: Start of analysis period (default: 30 days ago)
            end_date: End of analysis period (default: now)
        """
        self.location = Point(lng, lat, srid=4326)
        self.lat = lat
        self.lng = lng
        self.radius_km = radius_km
        
        # Set time range (max 30 days)
        self.end_date = end_date or timezone.now()
        self.start_date = start_date or (self.end_date - timedelta(days=30))
        
        # Enforce 30-day limit
        if (self.end_date - self.start_date).days > 30:
            self.start_date = self.end_date - timedelta(days=30)
    
    def get_district_info(self) -> Optional[Dict]:
        """
        Get district information for the location coordinates.
        
        Returns:
            District info dict or None if not found
        """
        try:
            from django.contrib.gis.db.models.functions import Distance as DistanceFunc
            
            # Find district containing this point
            district = District.objects.filter(
                geometry__contains=self.location
            ).first()
            
            if district:
                return {
                    "name": district.name,
                    "province": district.province,
                    "population": district.population,
                    "area_km2": district.area_km2,
                }
        except Exception as e:
            logger.warning(f"Could not determine district for location {self.lat}, {self.lng}: {e}")
        
        return None
    
    def get_nearby_stations(self) -> List[AirQualityStation]:
        """
        Find ground monitoring stations within radius that have recent data.
        
        Prioritizes stations with data in the analysis time range, then falls back
        to closest stations if no data is available.
        
        Returns:
            List of AirQualityStation objects sorted by distance
        """
        from air_quality.models import PollutantReading
        
        # First, try to find stations with data in our time range
        stations_with_data = AirQualityStation.objects.filter(
            is_active=True,
            location__distance_lte=(self.location, D(km=self.radius_km)),
            readings__timestamp__gte=self.start_date,
            readings__timestamp__lte=self.end_date,
            readings__is_valid=True
        ).annotate(distance=DistanceFunc('location', self.location)).order_by("distance").distinct()[:10]
        
        if stations_with_data:
            return list(stations_with_data)
        
        # Fallback: find closest stations (even without data)
        return list(
            AirQualityStation.objects.filter(
                is_active=True,
                location__distance_lte=(self.location, D(km=self.radius_km))
            )
            .annotate(distance=DistanceFunc('location', self.location))
            .order_by("distance")[:10]
        )
    
    def get_ground_trends(self) -> Dict[str, Dict]:
        """
        Analyze ground station reading trends.
        
        Returns:
            Dictionary mapping pollutant codes to trend statistics:
            {
                "PM25": {
                    "mean": 45.2,
                    "min": 12.1,
                    "max": 98.5,
                    "p95": 85.3,
                    "samples": 720,
                    "stations": 3
                },
                ...
            }
        """
        stations = self.get_nearby_stations()
        station_ids = [s.id for s in stations]
        
        if not station_ids:
            return {}
        
        # Query readings within date range for all pollutants
        readings = PollutantReading.objects.filter(
            station_id__in=station_ids,
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date,
            is_valid=True,
        )
        
        if not readings.exists():
            return {}
        
        trends = {}
        
        # Group by parameter and calculate statistics
        for pollutant_code in ['PM25', 'NO2', 'SO2', 'CO', 'O3']:
            pollutant_readings = readings.filter(parameter=pollutant_code)
            
            if not pollutant_readings.exists():
                continue
            
            # Calculate statistics
            stats = pollutant_readings.aggregate(
                mean=Avg('value_normalized'),
                min_value=Min('value_normalized'),
                max_value=Max('value_normalized'),
            )
            
            # Calculate percentiles (approximate using database)
            values = list(pollutant_readings.values_list('value_normalized', flat=True))
            values = [v for v in values if v is not None]  # Filter out None
            values.sort()
            
            if not values:
                continue
            
            p95_index = int(len(values) * 0.95)
            p95 = values[p95_index] if values else None
            
            trends[pollutant_code] = {
                "mean": round(stats["mean"], 2) if stats["mean"] else None,
                "min": round(stats["min_value"], 2) if stats["min_value"] else None,
                "max": round(stats["max_value"], 2) if stats["max_value"] else None,
                "p95": round(p95, 2) if p95 else None,
                "samples": len(values),
                "stations": pollutant_readings.values("station").distinct().count(),
            }
        
        return trends
    
    def get_exposure_trends(self) -> Dict[str, Dict]:
        """
        Analyze district exposure trends from satellite data.
        Uses DistrictExposure model for historical exposure data.
        
        Returns:
            Dictionary mapping pollutant codes to exposure statistics
        """
        # Find district containing the location
        location_point = Point(self.lng, self.lat, srid=4326)
        
        try:
            district = District.objects.filter(
                geometry__contains=location_point
            ).first()
            
            if not district:
                return {
                    "note": "Location not within any district boundary"
                }
            
            # Query district exposures within date range
            exposures = DistrictExposure.objects.filter(
                district=district,
                date__gte=self.start_date.date(),
                date__lte=self.end_date.date(),
                pollutant__isnull=False  # Exclude combined satellite data
            ).values('pollutant').annotate(
                avg_exposed=Avg('population_exposed'),
                max_exposed=Max('population_exposed'),
                avg_mean_conc=Avg('mean_concentration')
            )
            
            trends = {}
            for exp in exposures:
                pollutant = exp['pollutant']
                trends[pollutant] = {
                    'avg_exposed_population': exp['avg_exposed'] or 0,
                    'max_exposed_population': exp['max_exposed'] or 0,
                    'avg_concentration': exp['avg_mean_conc'] or 0,
                    'district': district.name
                }
            
            return trends
            
        except Exception as e:
            return {
                "error": f"Failed to analyze exposure trends: {str(e)}"
            }
    
    def get_gee_data(self) -> Dict:
        """
        Get Google Earth Engine satellite data for the location.
        
        Returns:
            Dictionary with satellite-derived air quality data:
            {
                "no2": {"mean": 0.00015, "max": 0.00025, "unit": "mol/m²"},
                "so2": {"mean": 0.00002, "max": 0.00005, "unit": "mol/m²"},
                "co": {"mean": 0.02, "max": 0.04, "unit": "mol/m²"},
                "o3": {"mean": 0.12, "max": 0.15, "unit": "mol/m²"},
                "estimated_pm25": 45.2,
                "air_quality_index": 85,
                "tile_urls": {
                    "NO2": "https://earthengine.googleapis.com/v1alpha/projects/earthengine-legacy/maps/...",
                    "SO2": "...",
                }
            }
        """
        try:
            from air_quality.services.gee_manager import get_satellite_manager
            
            manager = get_satellite_manager()
            
            # Get satellite data for the location and date range
            result = manager.get_air_quality_data(
                lat=self.lat,
                lon=self.lng,
                start_date=self.start_date.date(),
                end_date=self.end_date.date(),
                parameters=["NO2", "SO2", "CO", "O3"],
                buffer_m=int(self.radius_km * 1000),  # Convert km to meters
            )
            
            gee_data = {}
            
            # Extract pollutant data
            if result.no2:
                gee_data["no2"] = {
                    "mean": result.no2.mean_value,
                    "max": result.no2.max_value,
                    "unit": result.no2.unit
                }
            
            if result.so2:
                gee_data["so2"] = {
                    "mean": result.so2.mean_value,
                    "max": result.so2.max_value,
                    "unit": result.so2.unit
                }
            
            if result.co:
                gee_data["co"] = {
                    "mean": result.co.mean_value,
                    "max": result.co.max_value,
                    "unit": result.co.unit
                }
            
            if result.o3:
                gee_data["o3"] = {
                    "mean": result.o3.mean_value,
                    "max": result.o3.max_value,
                    "unit": result.o3.unit
                }
            
            # Add derived metrics
            if result.estimated_pm25:
                gee_data["estimated_pm25"] = result.estimated_pm25
            
            if result.air_quality_index:
                gee_data["air_quality_index"] = result.air_quality_index
            
            # Generate tile URLs for maps
            tile_urls = self._generate_gee_tile_urls()
            gee_data["tile_urls"] = tile_urls
            
            return gee_data
            
        except Exception as e:
            logger.warning(f"Failed to get GEE data: {e}")
            return {
                "error": f"Could not retrieve satellite data: {str(e)}"
            }
    
    def _generate_gee_tile_urls(self) -> Dict[str, str]:
        """
        Generate GEE tile URLs for map visualization.
        
        Returns:
            Dictionary mapping pollutant codes to tile URLs
        """
        try:
            from air_quality.services.gee_tiles import get_gee_tile_service
            
            service = get_gee_tile_service()
            tile_urls = {}
            
            # Generate tiles for recent date (last available)
            recent_date = self.end_date.date()
            
            for pollutant in ["NO2", "SO2", "CO", "O3"]:
                try:
                    tile_result = service.get_tile_url(
                        pollutant=pollutant,
                        target_date=recent_date,
                        bbox={
                            "west": self.lng - 0.1,
                            "east": self.lng + 0.1,
                            "south": self.lat - 0.1,
                            "north": self.lat + 0.1
                        }
                    )
                    if tile_result.get("success") and "tiles" in tile_result:
                        tile_urls[pollutant] = tile_result["tiles"]["url_template"]
                except Exception as e:
                    logger.debug(f"Could not generate {pollutant} tiles: {e}")
            
            return tile_urls
            
        except Exception as e:
            logger.warning(f"Failed to generate GEE tile URLs: {e}")
            return {}
    
    def get_temporal_patterns(self) -> Dict:
        """
        Analyze temporal patterns in air quality data.
        
        Returns:
            Dictionary with temporal analysis results
        """
        # Simple implementation - can be enhanced later
        return {
            "note": "Temporal pattern analysis not yet implemented",
            "daily_cycles": {},
            "seasonal_trends": {},
        }
    
    def generate_summary(self) -> Dict:
        """
        Generate comprehensive trend analysis summary.
        
        Returns:
            Complete analysis including:
            - Location and time range
            - Nearby stations
            - Ground reading trends
            - Satellite exposure trends
            - GEE satellite data
            - Temporal patterns
            - Health risk assessment
        """
        stations = self.get_nearby_stations()
        ground_trends = self.get_ground_trends()
        gee_data = self.get_gee_data()
        district_info = self.get_district_info()
        
        return {
            "location": {
                "lat": self.lat,
                "lng": self.lng,
                "radius_km": self.radius_km,
                "district": district_info,
            },
            "time_range": {
                "start": self.start_date.isoformat(),
                "end": self.end_date.isoformat(),
                "days": (self.end_date - self.start_date).days,
            },
            "stations": {
                "count": len(stations),
                "nearest": {
                    "name": stations[0].name,
                    "distance_km": round(stations[0].distance.km, 2),
                } if stations else None,
            },
            "ground_trends": ground_trends,
            "gee_data": gee_data,
            "exposure_trends": self.get_exposure_trends(),
            "temporal_patterns": self.get_temporal_patterns(),
        }


def calculate_health_risk(pollutant_stats: Dict[str, Dict]) -> str:
    """
    Assess overall health risk based on pollutant statistics.
    
    Args:
        pollutant_stats: Dictionary from get_ground_trends()
    
    Returns:
        Risk level: "low", "moderate", "high", "very_high"
    """
    # Simple heuristic: Check if any pollutant mean exceeds unhealthy threshold
    # TODO: Implement proper AQI-based risk assessment
    
    pm25 = pollutant_stats.get("PM25", {}).get("mean", 0)
    
    if pm25 > 55:
        return "high"
    elif pm25 > 35:
        return "moderate"
    else:
        return "low"
