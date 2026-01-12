"""
District-level exposure calculation service.

Calculates and stores exposure metrics at district level using:
- Satellite data (MODIS, TROPOMI)
- Ground station data (when available)
- Population data (WorldPop)
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any

import numpy as np
from django.db import transaction
from django.db.models import Avg, Sum, Max, Min, Count
from django.contrib.gis.geos import GEOSGeometry

from air_quality.models import District, PollutantReading, AirQualityStation
from air_quality.constants import calculate_aqi, get_aqi_category, AQICategory
from exposure.models import DistrictExposure, ProvinceExposure, NationalExposure, Hotspot
from .satellite_exposure import SatelliteExposureService, ExposureMetrics
from .population import PopulationService, get_population_service

logger = logging.getLogger(__name__)


@dataclass
class DistrictExposureResult:
    """Result of district exposure calculation."""
    district: District
    exposure: ExposureMetrics
    ground_data: Optional[Dict] = None
    satellite_data: Optional[Dict] = None
    fused_pm25: Optional[float] = None
    data_source: str = "satellite"
    created_record: Optional[DistrictExposure] = None


class DistrictExposureService:
    """
    Calculate and manage district-level exposure.
    
    Features:
    - Satellite-based exposure calculation
    - Ground station data integration
    - Ground-satellite data fusion
    - Province and national aggregation
    """
    
    def __init__(
        self,
        satellite_service: Optional[SatelliteExposureService] = None,
        population_service: Optional[PopulationService] = None
    ):
        """
        Initialize district exposure service.
        
        Args:
            satellite_service: Satellite exposure calculator
            population_service: Population data service
        """
        self._satellite_service = satellite_service
        self._population_service = population_service
    
    @property
    def satellite_service(self) -> SatelliteExposureService:
        """Get or create satellite service."""
        if self._satellite_service is None:
            self._satellite_service = SatelliteExposureService()
        return self._satellite_service
    
    @property
    def population_service(self) -> PopulationService:
        """Get or create population service."""
        if self._population_service is None:
            self._population_service = get_population_service()
        return self._population_service
    
    def calculate_district_exposure(
        self,
        district: District,
        target_date: Optional[date] = None,
        days_back: int = 7,
        include_ground_data: bool = True,
        save: bool = True
    ) -> DistrictExposureResult:
        """
        Calculate exposure for a single district.
        
        Args:
            district: District model instance
            target_date: Date for calculation
            days_back: Days to look back for satellite data
            include_ground_data: Whether to include ground station data
            save: Whether to save to database
            
        Returns:
            DistrictExposureResult with all exposure data
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"Calculating exposure for {district.name} on {target_date}")
        
        # Calculate satellite-based exposure
        satellite_exposure = self.satellite_service.calculate_exposure_for_geometry(
            geometry=district.geometry,
            target_date=target_date,
            days_back=days_back
        )
        
        # Get ground station data if requested
        ground_data = None
        if include_ground_data:
            ground_data = self._get_ground_data_for_district(
                district=district,
                target_date=target_date
            )
        
        # Fuse satellite and ground data
        fused_pm25 = None
        data_source = "satellite"
        final_exposure = satellite_exposure
        
        if ground_data and ground_data.get("pm25_mean") is not None:
            fused_pm25 = self._fuse_ground_satellite_pm25(
                ground_pm25=ground_data["pm25_mean"],
                satellite_pm25=satellite_exposure.mean_pm25,
                ground_count=ground_data.get("station_count", 0)
            )
            data_source = "fused" if satellite_exposure.mean_pm25 else "ground"
            
            # Recalculate AQI with fused PM2.5
            if fused_pm25 is not None:
                final_exposure = self._update_exposure_with_fused_pm25(
                    exposure=satellite_exposure,
                    fused_pm25=fused_pm25
                )
        
        # Create result
        # Check if satellite data is available (data_coverage > 0 or any pollutant data)
        has_satellite_data = (
            satellite_exposure.data_coverage > 0 or 
            satellite_exposure.mean_pm25 is not None or
            satellite_exposure.mean_no2 is not None or
            satellite_exposure.mean_aod is not None
        )
        result = DistrictExposureResult(
            district=district,
            exposure=final_exposure,
            ground_data=ground_data,
            satellite_data={
                "pm25": satellite_exposure.mean_pm25,
                "no2": satellite_exposure.mean_no2,
                "aod": satellite_exposure.mean_aod,
            } if has_satellite_data else None,
            fused_pm25=fused_pm25,
            data_source=data_source
        )
        
        # Save to database
        if save:
            result.created_record = self._save_district_exposure(
                district=district,
                exposure=final_exposure,
                target_date=target_date,
                data_source=data_source,
                ground_data=ground_data
            )
        
        return result
    
    def calculate_all_districts(
        self,
        province: Optional[str] = None,
        target_date: Optional[date] = None,
        days_back: int = 7,
        include_ground_data: bool = True,
        save: bool = True
    ) -> List[DistrictExposureResult]:
        """
        Calculate exposure for all districts.
        
        Args:
            province: Filter by province name (optional)
            target_date: Date for calculation
            days_back: Days to look back
            include_ground_data: Include ground station data
            save: Save results to database
            
        Returns:
            List of DistrictExposureResult
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        # Get districts
        districts = District.objects.filter(geometry__isnull=False)
        if province:
            districts = districts.filter(province__iexact=province)
        
        results = []
        total = districts.count()
        
        for idx, district in enumerate(districts, 1):
            logger.info(f"Processing district {idx}/{total}: {district.name}")
            
            try:
                result = self.calculate_district_exposure(
                    district=district,
                    target_date=target_date,
                    days_back=days_back,
                    include_ground_data=include_ground_data,
                    save=save
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error processing {district.name}: {e}")
                continue
        
        return results
    
    def aggregate_province_exposure(
        self,
        province_name: str,
        target_date: Optional[date] = None,
        save: bool = True
    ) -> Optional[ProvinceExposure]:
        """
        Aggregate district exposures to province level.
        
        Args:
            province_name: Province name
            target_date: Date for aggregation
            save: Save to database
            
        Returns:
            ProvinceExposure instance or None
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        # Get district exposures for this province
        district_exposures = DistrictExposure.objects.filter(
            district__province__iexact=province_name,
            date=target_date
        )
        
        if not district_exposures.exists():
            logger.warning(f"No district exposures for {province_name} on {target_date}")
            return None
        
        # Aggregate
        agg = district_exposures.aggregate(
            total_pop=Sum("total_population"),
            total_pop_good=Sum("pop_good"),
            total_pop_moderate=Sum("pop_moderate"),
            total_pop_usg=Sum("pop_usg"),
            total_pop_unhealthy=Sum("pop_unhealthy"),
            total_pop_very_unhealthy=Sum("pop_very_unhealthy"),
            total_pop_hazardous=Sum("pop_hazardous"),
            avg_aqi=Avg("mean_aqi"),
            max_aqi=Max("mean_aqi"),
            avg_exposure=Avg("exposure_index"),
            district_count=Count("id"),
        )
        
        # Find worst district
        worst = district_exposures.order_by("-mean_aqi").first()
        
        # Calculate weighted average PM2.5
        weighted_pm25 = None
        pm25_districts = district_exposures.filter(mean_pm25__isnull=False)
        if pm25_districts.exists():
            total_pop = sum(d.total_population for d in pm25_districts)
            if total_pop > 0:
                weighted_pm25 = sum(
                    d.mean_pm25 * d.total_population for d in pm25_districts
                ) / total_pop
        
        if save:
            province_exposure, created = ProvinceExposure.objects.update_or_create(
                province=province_name,
                date=target_date,
                defaults={
                    "total_population": agg["total_pop"] or 0,
                    "pop_good": agg["total_pop_good"] or 0,
                    "pop_moderate": agg["total_pop_moderate"] or 0,
                    "pop_usg": agg["total_pop_usg"] or 0,
                    "pop_unhealthy": agg["total_pop_unhealthy"] or 0,
                    "pop_very_unhealthy": agg["total_pop_very_unhealthy"] or 0,
                    "pop_hazardous": agg["total_pop_hazardous"] or 0,
                    "mean_aqi": agg["avg_aqi"],
                    "max_aqi": agg["max_aqi"],
                    "mean_pm25": weighted_pm25,
                    "exposure_index": agg["avg_exposure"],
                    "district_count": agg["district_count"],
                    "worst_district": worst.district if worst else None,
                }
            )
            logger.info(f"{'Created' if created else 'Updated'} province exposure for {province_name}")
            return province_exposure
        
        return None
    
    def aggregate_national_exposure(
        self,
        target_date: Optional[date] = None,
        save: bool = True
    ) -> Optional[NationalExposure]:
        """
        Aggregate province exposures to national level.
        
        Args:
            target_date: Date for aggregation
            save: Save to database
            
        Returns:
            NationalExposure instance or None
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)
        
        # Get all district exposures
        district_exposures = DistrictExposure.objects.filter(date=target_date)
        
        if not district_exposures.exists():
            logger.warning(f"No district exposures for {target_date}")
            return None
        
        # Aggregate
        agg = district_exposures.aggregate(
            total_pop=Sum("total_population"),
            total_pop_good=Sum("pop_good"),
            total_pop_moderate=Sum("pop_moderate"),
            total_pop_usg=Sum("pop_usg"),
            total_pop_unhealthy=Sum("pop_unhealthy"),
            total_pop_very_unhealthy=Sum("pop_very_unhealthy"),
            total_pop_hazardous=Sum("pop_hazardous"),
            avg_aqi=Avg("mean_aqi"),
            max_aqi=Max("mean_aqi"),
            avg_exposure=Avg("exposure_index"),
            district_count=Count("id"),
        )
        
        # Province count
        province_count = district_exposures.values("district__province").distinct().count()
        
        # Worst district
        worst = district_exposures.order_by("-mean_aqi").first()
        
        # Weighted PM2.5
        weighted_pm25 = None
        pm25_districts = district_exposures.filter(mean_pm25__isnull=False)
        if pm25_districts.exists():
            total_pop = sum(d.total_population for d in pm25_districts)
            if total_pop > 0:
                weighted_pm25 = sum(
                    d.mean_pm25 * d.total_population for d in pm25_districts
                ) / total_pop
        
        if save:
            national_exposure, created = NationalExposure.objects.update_or_create(
                date=target_date,
                defaults={
                    "total_population": agg["total_pop"] or 0,
                    "pop_good": agg["total_pop_good"] or 0,
                    "pop_moderate": agg["total_pop_moderate"] or 0,
                    "pop_usg": agg["total_pop_usg"] or 0,
                    "pop_unhealthy": agg["total_pop_unhealthy"] or 0,
                    "pop_very_unhealthy": agg["total_pop_very_unhealthy"] or 0,
                    "pop_hazardous": agg["total_pop_hazardous"] or 0,
                    "mean_aqi": agg["avg_aqi"],
                    "max_aqi": agg["max_aqi"],
                    "mean_pm25": weighted_pm25,
                    "exposure_index": agg["avg_exposure"],
                    "province_count": province_count,
                    "district_count": agg["district_count"],
                    "worst_district": worst.district if worst else None,
                }
            )
            logger.info(f"{'Created' if created else 'Updated'} national exposure")
            return national_exposure
        
        return None
    
    def _get_ground_data_for_district(
        self,
        district: District,
        target_date: date
    ) -> Optional[Dict]:
        """
        Get ground station data for a district.
        
        Returns:
            Dictionary with ground measurement stats or None
        """
        # Get stations in district
        stations = AirQualityStation.objects.filter(
            is_active=True,
            location__within=district.geometry
        )
        
        if not stations.exists():
            return None
        
        station_ids = list(stations.values_list("id", flat=True))
        
        # Get readings for target date (parameter field uses PM25 for PM2.5)
        readings = PollutantReading.objects.filter(
            station_id__in=station_ids,
            timestamp__date=target_date,
            parameter="PM25",
            value__isnull=False,
            value__gt=0
        )
        
        if not readings.exists():
            return None
        
        # Calculate stats
        agg = readings.aggregate(
            pm25_mean=Avg("value"),
            pm25_max=Max("value"),
            pm25_min=Min("value"),
            reading_count=Count("id")
        )
        
        return {
            "pm25_mean": agg["pm25_mean"],
            "pm25_max": agg["pm25_max"],
            "pm25_min": agg["pm25_min"],
            "reading_count": agg["reading_count"],
            "station_count": stations.count(),
            "station_ids": station_ids,
        }
    
    def _fuse_ground_satellite_pm25(
        self,
        ground_pm25: float,
        satellite_pm25: Optional[float],
        ground_count: int = 1
    ) -> float:
        """
        Fuse ground and satellite PM2.5 estimates.
        
        Uses weighted average with more weight to ground measurements
        when more stations are available.
        
        Args:
            ground_pm25: Ground measurement PM2.5
            satellite_pm25: Satellite-estimated PM2.5
            ground_count: Number of ground stations
            
        Returns:
            Fused PM2.5 estimate
        """
        if satellite_pm25 is None:
            return ground_pm25
        
        if ground_pm25 is None:
            return satellite_pm25
        
        # Weight ground data more heavily with more stations
        # 1 station = 60% ground, 2+ stations = 70% ground, 5+ = 80%
        if ground_count >= 5:
            ground_weight = 0.8
        elif ground_count >= 2:
            ground_weight = 0.7
        else:
            ground_weight = 0.6
        
        satellite_weight = 1.0 - ground_weight
        
        return ground_pm25 * ground_weight + satellite_pm25 * satellite_weight
    
    def _update_exposure_with_fused_pm25(
        self,
        exposure: ExposureMetrics,
        fused_pm25: float
    ) -> ExposureMetrics:
        """
        Update exposure metrics with fused PM2.5.
        
        Recalculates AQI and population categorization.
        """
        # Calculate new AQI
        new_pm25_aqi = calculate_aqi("PM25", fused_pm25)
        
        # Update pollutant AQI
        new_pollutant_aqi = exposure.pollutant_aqi.copy()
        new_pollutant_aqi["PM25"] = new_pm25_aqi
        
        # Recalculate combined AQI
        new_combined_aqi = max(new_pollutant_aqi.values()) if new_pollutant_aqi else None
        new_dominant = max(new_pollutant_aqi, key=new_pollutant_aqi.get) if new_pollutant_aqi else None
        new_category = get_aqi_category(new_combined_aqi) if new_combined_aqi else None
        
        # Recategorize population
        new_pop_categories = self.satellite_service._categorize_population_uniform(
            total_population=exposure.total_population,
            aqi=new_combined_aqi
        )
        
        # Return updated metrics
        return ExposureMetrics(
            total_population=exposure.total_population,
            exposed_population=exposure.exposed_population,
            mean_exposure_index=exposure.mean_exposure_index,
            max_exposure_index=exposure.max_exposure_index,
            
            pop_good=new_pop_categories["pop_good"],
            pop_moderate=new_pop_categories["pop_moderate"],
            pop_usg=new_pop_categories["pop_usg"],
            pop_unhealthy=new_pop_categories["pop_unhealthy"],
            pop_very_unhealthy=new_pop_categories["pop_very_unhealthy"],
            pop_hazardous=new_pop_categories["pop_hazardous"],
            
            mean_pm25=fused_pm25,
            mean_no2=exposure.mean_no2,
            mean_aod=exposure.mean_aod,
            estimated_pm25_from_aod=exposure.estimated_pm25_from_aod,
            
            combined_aqi=new_combined_aqi,
            aqi_category=new_category.value if new_category else None,
            dominant_pollutant=new_dominant,
            
            data_coverage=exposure.data_coverage,
            data_source="fused",
            observation_date=exposure.observation_date,
            pollutant_aqi=new_pollutant_aqi
        )
    
    def _save_district_exposure(
        self,
        district: District,
        exposure: ExposureMetrics,
        target_date: date,
        data_source: str,
        ground_data: Optional[Dict] = None
    ) -> DistrictExposure:
        """
        Save district exposure to database.
        """
        exposure_record, created = DistrictExposure.objects.update_or_create(
            district=district,
            date=target_date,
            defaults={
                "total_population": int(exposure.total_population),
                "pop_good": exposure.pop_good,
                "pop_moderate": exposure.pop_moderate,
                "pop_usg": exposure.pop_usg,
                "pop_unhealthy": exposure.pop_unhealthy,
                "pop_very_unhealthy": exposure.pop_very_unhealthy,
                "pop_hazardous": exposure.pop_hazardous,
                "mean_aqi": exposure.combined_aqi,
                "max_aqi": exposure.combined_aqi,  # Same for uniform
                "mean_pm25": exposure.mean_pm25,
                "max_pm25": exposure.mean_pm25,
                "exposure_index": exposure.mean_exposure_index,
                "data_source": data_source,
                "station_count": ground_data.get("station_count", 0) if ground_data else 0,
            }
        )
        
        logger.info(
            f"{'Created' if created else 'Updated'} exposure for "
            f"{district.name}: AQI={exposure.combined_aqi:.1f}, "
            f"Pop={exposure.total_population:,.0f}"
        )
        
        return exposure_record


# Convenience functions
def calculate_district_exposures(
    province: Optional[str] = None,
    target_date: Optional[date] = None,
    save: bool = True
) -> List[DistrictExposureResult]:
    """
    Convenience function to calculate all district exposures.
    """
    service = DistrictExposureService()
    return service.calculate_all_districts(
        province=province,
        target_date=target_date,
        save=save
    )


def aggregate_to_province_and_national(
    target_date: Optional[date] = None,
    save: bool = True
) -> Dict[str, Any]:
    """
    Aggregate exposures to province and national level.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)
    
    service = DistrictExposureService()
    
    # Get unique provinces
    provinces = District.objects.values_list("province", flat=True).distinct()
    
    province_results = {}
    for province in provinces:
        if province:
            result = service.aggregate_province_exposure(province, target_date, save)
            province_results[province] = result
    
    national_result = service.aggregate_national_exposure(target_date, save)
    
    return {
        "provinces": province_results,
        "national": national_result,
        "date": target_date,
    }
