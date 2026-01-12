"""
Django-Q tasks for exposure calculations.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional

from django.db.models import F

from .models import DistrictExposure, Hotspot, ProvinceExposure, NationalExposure
from .calculators import (
    calculate_district_exposure,
    identify_hotspots,
    calculate_national_summary,
)
from .services.gee_exposure import get_gee_exposure_service, GEEExposureResult
from air_quality.constants import Pollutant
from air_quality.models import District

logger = logging.getLogger(__name__)


def calculate_single_district_exposure(
    district_id: int, pollutant: str, target_date: str
) -> dict:
    """
    Calculate exposure for a single district and pollutant.

    Args:
        district_id: District ID
        pollutant: Pollutant code
        target_date: ISO date string
    """
    dt = date.fromisoformat(target_date)
    district = District.objects.get(pk=district_id)

    try:
        result = calculate_district_exposure(district, pollutant, dt)

        if result is None:
            return {"status": "no_data", "district_id": district_id}

        # Create or update exposure record
        exposure, created = DistrictExposure.objects.update_or_create(
            district=district,
            pollutant=pollutant,
            date=dt,
            defaults={
                "total_population": result["total_population"],
                "concentration_mean": result["concentration_mean"],
                "concentration_min": result["concentration_min"],
                "concentration_max": result["concentration_max"],
                "concentration_std": result["concentration_std"],
                "aqi_mean": result["aqi_mean"],
                "aqi_max": result["aqi_max"],
                "exposure_index": result["exposure_index"],
                "pop_good": result["pop_good"],
                "pop_moderate": result["pop_moderate"],
                "pop_usg": result["pop_usg"],
                "pop_unhealthy": result["pop_unhealthy"],
                "pop_very_unhealthy": result["pop_very_unhealthy"],
                "pop_hazardous": result["pop_hazardous"],
            },
        )

        return {
            "status": "success",
            "district_id": district_id,
            "exposure_id": exposure.id,
            "created": created,
        }

    except Exception as exc:
        logger.error(f"Failed to calculate exposure for district {district_id}: {exc}")
        raise self.retry(exc=exc)


def calculate_all_district_exposures(pollutant: str, target_date: str) -> dict:
    """
    Calculate exposure for all districts for a pollutant.

    Args:
        pollutant: Pollutant code
        target_date: ISO date string
    """
    # Validate date format
    date.fromisoformat(target_date)
    districts = District.objects.all()

    results = {
        "success": 0,
        "failed": 0,
        "no_data": 0,
    }

    for district in districts:
        try:
            result = calculate_single_district_exposure.apply(
                args=[district.id, pollutant, target_date]
            ).get()

            if result.get("status") == "success":
                results["success"] += 1
            elif result.get("status") == "no_data":
                results["no_data"] += 1
            else:
                results["failed"] += 1

        except Exception as e:
            logger.error(f"District {district.id} exposure failed: {e}")
            results["failed"] += 1

    # Update rankings
    update_district_rankings.apply(args=[pollutant, target_date])

    return {
        "pollutant": pollutant,
        "date": target_date,
        "districts_processed": sum(results.values()),
        **results,
    }


def update_district_rankings(pollutant: str, target_date: str) -> dict:
    """
    Update district rankings based on exposure index.

    Args:
        pollutant: Pollutant code
        target_date: ISO date string
    """
    dt = date.fromisoformat(target_date)

    # Get all exposures for this pollutant and date, ordered by exposure index
    exposures = DistrictExposure.objects.filter(
        pollutant=pollutant, date=dt, exposure_index__isnull=False
    ).order_by("-exposure_index")

    # Update ranks (1 = worst)
    for rank, exposure in enumerate(exposures, start=1):
        exposure.rank = rank
        exposure.save(update_fields=["rank"])

    return {
        "pollutant": pollutant,
        "date": target_date,
        "ranked": exposures.count(),
    }


def identify_pollution_hotspots(
    pollutant: str, target_date: str, threshold_aqi: float = 100
) -> dict:
    """
    Identify and store pollution hotspots.

    Args:
        pollutant: Pollutant code
        target_date: ISO date string
        aqi_threshold: Minimum AQI threshold
    """
    from django.contrib.gis.geos import Point

    dt = date.fromisoformat(target_date)

    try:
        hotspots_data = identify_hotspots(
            pollutant=pollutant, target_date=dt, aqi_threshold=aqi_threshold
        )

        # Clear existing hotspots for this date/pollutant
        Hotspot.objects.filter(pollutant=pollutant, date=dt).delete()

        # Create new hotspots
        created = 0
        for hs in hotspots_data:
            hotspot = Hotspot.objects.create(
                pollutant=pollutant,
                date=dt,
                centroid=Point(hs["centroid_lon"], hs["centroid_lat"], srid=4326),
                area_sq_km=hs["area_sq_km"],
                severity=hs["severity"],
                concentration_mean=hs["concentration_mean"],
                concentration_max=hs["concentration_max"],
                aqi_mean=hs["aqi_mean"],
                affected_population=hs["affected_population"],
            )

            # Find affected districts (intersecting with centroid)
            affected = District.objects.filter(geometry__contains=hotspot.centroid)
            hotspot.affected_districts.set(affected)

            created += 1

        # Update persistence (consecutive days)
        update_hotspot_persistence.apply(args=[pollutant, target_date])

        return {
            "status": "success",
            "pollutant": pollutant,
            "date": target_date,
            "hotspots_identified": created,
        }

    except Exception as exc:
        logger.error(f"Failed to identify hotspots: {exc}")
        return {"status": "error", "error": str(exc)}


def update_hotspot_persistence(pollutant: str, target_date: str) -> dict:
    """
    Update hotspot persistence (consecutive days).
    Checks if today's hotspots overlap with yesterday's.
    """
    from django.contrib.gis.measure import D

    dt = date.fromisoformat(target_date)
    yesterday = dt - timedelta(days=1)

    today_hotspots = Hotspot.objects.filter(pollutant=pollutant, date=dt)
    yesterday_hotspots = Hotspot.objects.filter(pollutant=pollutant, date=yesterday)

    updated = 0
    for hs in today_hotspots:
        # Check if any of yesterday's hotspots were nearby
        nearby = yesterday_hotspots.filter(
            centroid__distance_lte=(hs.centroid, D(km=50))
        ).first()

        if nearby:
            hs.persistence_days = nearby.persistence_days + 1
            hs.save(update_fields=["persistence_days"])
            updated += 1

    return {
        "pollutant": pollutant,
        "date": target_date,
        "persistent_hotspots": updated,
    }


def aggregate_province_exposures(pollutant: str, target_date: str) -> dict:
    """
    Aggregate district exposures to province level.
    """
    from django.db.models import Sum, Avg, Count

    dt = date.fromisoformat(target_date)

    # Get province aggregations
    provinces = (
        DistrictExposure.objects.filter(pollutant=pollutant, date=dt)
        .values(province=F("district__province"))
        .annotate(
            total_pop=Sum("total_population"),
            mean_conc=Avg("concentration_mean"),
            mean_aqi=Avg("aqi_mean"),
            mean_exposure=Avg("exposure_index"),
            pop_good=Sum("pop_good"),
            pop_moderate=Sum("pop_moderate"),
            pop_usg=Sum("pop_usg"),
            pop_unhealthy=Sum("pop_unhealthy"),
            pop_very_unhealthy=Sum("pop_very_unhealthy"),
            pop_hazardous=Sum("pop_hazardous"),
            n_districts=Count("id"),
        )
    )

    created = 0
    for prov in provinces:
        ProvinceExposure.objects.update_or_create(
            province=prov["province"],
            pollutant=pollutant,
            date=dt,
            defaults={
                "total_population": prov["total_pop"] or 0,
                "concentration_mean": prov["mean_conc"],
                "aqi_mean": prov["mean_aqi"],
                "exposure_index": prov["mean_exposure"],
                "pop_good": prov["pop_good"] or 0,
                "pop_moderate": prov["pop_moderate"] or 0,
                "pop_usg": prov["pop_usg"] or 0,
                "pop_unhealthy": prov["pop_unhealthy"] or 0,
                "pop_very_unhealthy": prov["pop_very_unhealthy"] or 0,
                "pop_hazardous": prov["pop_hazardous"] or 0,
                "n_districts": prov["n_districts"],
            },
        )
        created += 1

    # Update province rankings
    exposures = ProvinceExposure.objects.filter(pollutant=pollutant, date=dt).order_by(
        "-exposure_index"
    )

    for rank, exp in enumerate(exposures, start=1):
        exp.rank = rank
        exp.save(update_fields=["rank"])

    return {
        "pollutant": pollutant,
        "date": target_date,
        "provinces_aggregated": created,
    }


def calculate_national_exposure(pollutant: str, target_date: str) -> dict:
    """
    Calculate and store national exposure summary.
    """
    dt = date.fromisoformat(target_date)

    summary = calculate_national_summary(pollutant, dt)

    NationalExposure.objects.update_or_create(
        pollutant=pollutant,
        date=dt,
        defaults={
            "total_population": summary["total_population"],
            "concentration_mean": summary["concentration_mean"],
            "concentration_max": summary["concentration_max"],
            "aqi_mean": summary["aqi_mean"],
            "exposure_index": summary["exposure_index"],
            "pop_good": summary["pop_good"],
            "pop_moderate": summary["pop_moderate"],
            "pop_usg": summary["pop_usg"],
            "pop_unhealthy": summary["pop_unhealthy"],
            "pop_very_unhealthy": summary["pop_very_unhealthy"],
            "pop_hazardous": summary["pop_hazardous"],
            "n_hotspots": summary["n_hotspots"],
            "worst_district_id": summary["worst_district_id"],
        },
    )

    return {
        "status": "success",
        "pollutant": pollutant,
        "date": target_date,
    }


def run_daily_exposure_pipeline(target_date: str = None) -> dict:
    """
    Run complete daily exposure pipeline for all pollutants.

    Steps:
    1. Calculate district exposures
    2. Identify hotspots
    3. Aggregate to provinces
    4. Calculate national summary
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info(f"Running exposure pipeline for {target_date}")

    results = {}

    for pollutant in Pollutant:
        p = pollutant.value
        results[p] = {}

        try:
            # Step 1: District exposures
            district_result = calculate_all_district_exposures.apply(
                args=[p, target_date]
            ).get()
            results[p]["districts"] = district_result

            # Step 2: Hotspots
            hotspot_result = identify_pollution_hotspots.apply(
                args=[p, target_date]
            ).get()
            results[p]["hotspots"] = hotspot_result

            # Step 3: Province aggregation
            province_result = aggregate_province_exposures.apply(
                args=[p, target_date]
            ).get()
            results[p]["provinces"] = province_result

            # Step 4: National summary
            national_result = calculate_national_exposure.apply(
                args=[p, target_date]
            ).get()
            results[p]["national"] = national_result

        except Exception as e:
            results[p] = {"status": "error", "error": str(e)}

    return results


# =============================================================================
# GEE-BASED EXPOSURE TASKS
# =============================================================================

def calculate_gee_exposure_single_district(
    district_id: int,
    target_date: str,
    days_back: int = 7,
    save_to_db: bool = True,
) -> Dict:
    """
    Calculate GEE-based pixel-wise exposure for a single district.
    
    Args:
        district_id: District ID
        target_date: ISO date string (YYYY-MM-DD)
        days_back: Number of days to average satellite data
        save_to_db: Whether to save results to database
        
    Returns:
        Dict with status and results
    """
    dt = date.fromisoformat(target_date)
    
    try:
        district = District.objects.get(pk=district_id)
        gee_service = get_gee_exposure_service()
        
        # Calculate exposure on GEE
        result: GEEExposureResult = gee_service.calculate_exposure_for_geometry(
            geometry=district.geometry,
            target_date=dt,
            days_back=days_back,
        )
        
        if result.errors:
            logger.error(f"GEE calculation errors for district {district_id}: {result.errors}")
            return {
                "status": "error",
                "district_id": district_id,
                "district_name": district.name,
                "errors": result.errors,
            }
        
        # Save to database if requested
        if save_to_db:
            exposure, created = DistrictExposure.objects.update_or_create(
                district=district,
                pollutant='PM25',  # Primary pollutant
                date=dt,
                defaults={
                    'concentration_mean': result.mean_pm25 or 0,
                    'aqi_mean': result.mean_aqi,
                    'aqi_max': int(result.max_aqi),
                    'exposure_index': result.mean_exposure_index,
                    'total_population': result.total_population,
                    'pop_good': result.pop_good,
                    'pop_moderate': result.pop_moderate,
                    'pop_usg': result.pop_unhealthy_sensitive,
                    'pop_unhealthy': result.pop_unhealthy,
                    'pop_very_unhealthy': result.pop_very_unhealthy,
                    'pop_hazardous': result.pop_hazardous,
                    'data_source': 'gee_gridded',
                    'mean_pm25': result.mean_pm25,
                }
            )
            
            return {
                "status": "success",
                "district_id": district_id,
                "district_name": district.name,
                "exposure_id": exposure.id,
                "created": created,
                "mean_aqi": result.mean_aqi,
                "total_population": result.total_population,
            }
        else:
            return {
                "status": "success",
                "district_id": district_id,
                "district_name": district.name,
                "mean_aqi": result.mean_aqi,
                "total_population": result.total_population,
                "tile_url": result.exposure_tile_url,
            }
            
    except District.DoesNotExist:
        logger.error(f"District {district_id} not found")
        return {
            "status": "error",
            "district_id": district_id,
            "error": "District not found",
        }
    except Exception as e:
        logger.error(f"Failed to calculate GEE exposure for district {district_id}: {e}")
        return {
            "status": "error",
            "district_id": district_id,
            "error": str(e),
        }


def calculate_gee_exposure_batch(
    district_ids: Optional[List[int]] = None,
    province: Optional[str] = None,
    target_date: str = None,
    days_back: int = 7,
    save_to_db: bool = True,
) -> Dict:
    """
    Calculate GEE-based exposure for multiple districts in batch.
    
    Args:
        district_ids: List of district IDs (optional)
        province: Province name to calculate all districts (optional)
        target_date: ISO date string (defaults to today)
        days_back: Number of days to average satellite data
        save_to_db: Whether to save results to database
        
    Returns:
        Dict with batch results summary
    """
    if target_date is None:
        target_date = date.today().isoformat()
    
    # Determine which districts to process
    if district_ids:
        districts = District.objects.filter(id__in=district_ids)
    elif province:
        districts = District.objects.filter(province__iexact=province)
    else:
        districts = District.objects.all()
    
    if not districts.exists():
        return {
            "status": "error",
            "error": "No districts found matching criteria",
        }
    
    results = {
        "success": [],
        "errors": [],
        "total": districts.count(),
        "date": target_date,
        "data_source": "gee_gridded",
    }
    
    logger.info(f"Starting GEE batch calculation for {results['total']} districts")
    
    # Process each district
    for district in districts:
        result = calculate_gee_exposure_single_district(
            district_id=district.id,
            target_date=target_date,
            days_back=days_back,
            save_to_db=save_to_db,
        )
        
        if result["status"] == "success":
            results["success"].append(result)
        else:
            results["errors"].append(result)
    
    logger.info(
        f"GEE batch calculation complete: "
        f"{len(results['success'])} success, {len(results['errors'])} errors"
    )
    
    return results


def calculate_gee_exposure_national(
    target_date: str = None,
    days_back: int = 7,
    save_to_db: bool = True,
) -> Dict:
    """
    Calculate GEE-based exposure for all districts nationally.
    
    This is a convenience wrapper for calculate_gee_exposure_batch with all districts.
    
    Args:
        target_date: ISO date string (defaults to today)
        days_back: Number of days to average satellite data
        save_to_db: Whether to save results to database
        
    Returns:
        Dict with batch results summary
    """
    return calculate_gee_exposure_batch(
        district_ids=None,
        province=None,
        target_date=target_date,
        days_back=days_back,
        save_to_db=save_to_db,
    )

    return {"date": target_date, "results": results}
