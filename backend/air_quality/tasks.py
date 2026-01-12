"""
Tasks for air quality data ingestion and processing using Django-Q.
"""

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from django.utils import timezone

from .models import PollutantRaster, GroundStation, SystemStatus
from .constants import Pollutant
from .services import (
    get_cdse_client,
    get_openaq_client,
    get_geoserver_client,
    get_raster_manager,
    ensure_cog,
)
from .services.gee_risk import get_risk_service, RiskCalculationError

logger = logging.getLogger(__name__)


# ==================== Django-Q Tasks ====================


def check_sentinel5p_updates() -> Dict[str, Any]:
    """
    Check for new Sentinel-5P NO2 images (runs every 6 hours via Django-Q).
    
    This task:
    1. Queries GEE for the latest Sentinel-5P NO2 image
    2. Compares it with the last known image date in SystemStatus
    3. If a new image is available, updates the SystemStatus model
    4. Frontend can poll SystemStatus to know when to refresh tiles
    
    Returns:
        Dict with task result and metadata
    """
    task_start = timezone.now()
    logger.info("Starting Sentinel-5P update check...")
    
    try:
        # Get the risk service (initializes GEE)
        risk_service = get_risk_service()
        
        # Fetch latest Sentinel-5P NO2 image
        latest_image, latest_date = risk_service.get_latest_sentinel5p_no2(
            days_back=30
        )
        
        # Get or create the status entry
        status = SystemStatus.get_or_create_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            default_value={'image_date': None, 'last_check': None}
        )
        
        # Check if this is a new image
        old_date = status.value.get('image_date')
        is_new = (old_date is None) or (latest_date != old_date)
        
        # Update the status
        status_value = {
            'image_date': latest_date,
            'last_check': task_start.isoformat(),
            'is_new': is_new,
            'check_interval_hours': 6,
        }
        
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value=status_value,
            is_healthy=True,
            error_message=""
        )
        
        result = {
            'success': True,
            'latest_date': latest_date,
            'previous_date': old_date,
            'is_new_image': is_new,
            'checked_at': task_start.isoformat(),
            'message': (
                f"New image available: {latest_date}" if is_new
                else f"No new image (latest: {latest_date})"
            )
        }
        
        if is_new:
            logger.info(
                f"✓ New Sentinel-5P image detected: {latest_date} "
                f"(previous: {old_date})"
            )
        else:
            logger.info(f"No new Sentinel-5P image (latest: {latest_date})")
        
        return result
        
    except RiskCalculationError as e:
        error_msg = f"GEE error: {str(e)}"
        logger.error(f"Failed to check Sentinel-5P updates: {error_msg}")
        
        # Update status as unhealthy
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value={
                'last_check': task_start.isoformat(),
                'error': error_msg,
            },
            is_healthy=False,
            error_message=error_msg
        )
        
        return {
            'success': False,
            'error': error_msg,
            'checked_at': task_start.isoformat(),
        }
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"Failed to check Sentinel-5P updates: {error_msg}", exc_info=True)
        
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value={
                'last_check': task_start.isoformat(),
                'error': error_msg,
            },
            is_healthy=False,
            error_message=error_msg
        )
        
        return {
            'success': False,
            'error': error_msg,
            'checked_at': task_start.isoformat(),
        }


def manual_trigger_risk_calculation(
    openaq_geojson: Dict[str, Any],
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Manually trigger a risk calculation (for testing or on-demand use).
    
    Args:
        openaq_geojson: GeoJSON dict with local OpenAQ data
        days_back: How many days back to search for Sentinel-5P data
        
    Returns:
        Risk calculation result dictionary
    """
    logger.info("Manual risk calculation triggered")
    
    try:
        risk_service = get_risk_service()
        result = risk_service.calculate_risk_index(
            openaq_geojson=openaq_geojson,
            days_back=days_back
        )
        
        # Update system status
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.RISK_CALCULATION,
            value={
                'last_run': timezone.now().isoformat(),
                'sentinel5p_date': result['metadata']['sentinel5p_date'],
                'openaq_points': result['metadata']['openaq_points'],
            },
            is_healthy=True
        )
        
        logger.info("Manual risk calculation completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Manual risk calculation failed: {e}", exc_info=True)
        
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.RISK_CALCULATION,
            value={
                'last_run': timezone.now().isoformat(),
                'error': str(e),
            },
            is_healthy=False,
            error_message=str(e)
        )
        
        raise


# ==================== OpenAQ Tasks (Legacy Celery) ====================


def sync_ground_stations() -> dict:
    """
    Sync ground station metadata from OpenAQ.
    Should be run periodically to discover new stations.
    """
    try:
        openaq_client = get_openaq_client()
        created, updated = openaq_client.sync_stations()

        return {
            "status": "success",
            "created": created,
            "updated": updated,
            "total": GroundStation.objects.count(),
        }

    except Exception as exc:
        logger.error(f"Failed to sync ground stations: {exc}")
        raise


def fetch_ground_readings(target_date: str = None) -> dict:
    """
    Fetch ground readings from OpenAQ for a specific date.

    Args:
        target_date: ISO date string (defaults to yesterday)
    """
    if target_date:
        dt = date.fromisoformat(target_date)
    else:
        dt = date.today() - timedelta(days=1)

    try:
        openaq_client = get_openaq_client()
        count = openaq_client.sync_readings(dt)

        return {
            "status": "success",
            "date": dt.isoformat(),
            "readings_synced": count,
        }

    except Exception as exc:
        logger.error(f"Failed to fetch ground readings: {exc}")
        raise


def backfill_historical_readings(days: int = 180) -> dict:
    """
    Backfill historical readings from OpenAQ.
    Should be run once during initial setup.

    Args:
        days: Number of days to backfill
    """
    try:
        openaq_client = get_openaq_client()
        count = openaq_client.backfill_historical(days)

        return {
            "status": "success",
            "days": days,
            "total_readings": count,
        }

    except Exception as exc:
        logger.error(f"Failed to backfill historical data: {exc}")
        raise


# ==================== CDSE/Sentinel-5P Tasks ====================


def download_pollutant_raster(pollutant: str, target_date: str = None) -> dict:
    """
    Download satellite raster for a single pollutant.

    Args:
        pollutant: Pollutant code (NO2, SO2, PM25, CO, O3)
        target_date: ISO date string (defaults to yesterday)
    """
    if target_date:
        dt = date.fromisoformat(target_date)
    else:
        dt = date.today() - timedelta(days=1)

    # Get clients
    raster_manager = get_raster_manager()
    cdse_client = get_cdse_client()

    # Convert pollutant to enum for CDSE
    pollutant_enum = Pollutant(pollutant)

    # Get output path
    output_path = raster_manager.get_raw_path(pollutant, dt)

    # Check if already exists
    if output_path.exists():
        logger.info(f"Raster already exists: {output_path}")

        # Ensure record in database
        raster, created = PollutantRaster.objects.get_or_create(
            pollutant=pollutant,
            date=dt,
            defaults={
                "raw_file": str(output_path),
                "source": "CDSE",
            },
        )

        return {
            "status": "exists",
            "pollutant": pollutant,
            "date": dt.isoformat(),
            "path": str(output_path),
        }

    try:
        # Download from CDSE
        result_path = cdse_client.download_raster(
            pollutant=pollutant_enum, target_date=dt, output_path=output_path
        )

        # Convert to COG
        cog_path = ensure_cog(result_path)

        # Create database record
        raster = PollutantRaster.objects.create(
            pollutant=pollutant,
            date=dt,
            raw_file=str(cog_path),
            source="CDSE",
        )

        logger.info(f"Downloaded raster: {pollutant} for {dt}")

        return {
            "status": "success",
            "pollutant": pollutant,
            "date": dt.isoformat(),
            "path": str(cog_path),
            "raster_id": raster.id,
        }

    except Exception as exc:
        logger.error(f"Failed to download {pollutant} raster: {exc}")
        raise


def download_all_pollutants(target_date: str = None) -> dict:
    """
    Download satellite rasters for all pollutants.

    Args:
        target_date: ISO date string (defaults to yesterday)
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    results = {}

    for pollutant in Pollutant:
        try:
            result = download_pollutant_raster(pollutant.value, target_date)
            results[pollutant.value] = result
        except Exception as e:
            results[pollutant.value] = {"status": "error", "error": str(e)}

    return {
        "date": target_date,
        "results": results,
    }


def check_data_availability(target_date: str = None) -> dict:
    """
    Check CDSE data availability for a date.

    Args:
        target_date: ISO date string
    """
    if target_date:
        dt = date.fromisoformat(target_date)
    else:
        dt = date.today() - timedelta(days=1)

    cdse_client = get_cdse_client()
    availability = {}

    for pollutant in Pollutant:
        try:
            dates = cdse_client.get_available_dates(
                pollutant.value, dt - timedelta(days=7), dt
            )
            availability[pollutant.value] = {
                "available": dt in dates,
                "recent_dates": [d.isoformat() for d in dates[-5:]],
            }
        except Exception as e:
            availability[pollutant.value] = {"available": False, "error": str(e)}

    return {
        "date": dt.isoformat(),
        "availability": availability,
    }


# ==================== Pipeline Orchestration ====================


def run_daily_ingestion_pipeline(target_date: str = None) -> dict:
    """
    Run the complete daily data ingestion pipeline.

    Pipeline steps:
    1. Sync ground stations
    2. Fetch ground readings
    3. Download satellite rasters
    4. Trigger bias correction (via correction app)

    Args:
        target_date: ISO date string (defaults to yesterday)
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info(f"Starting daily ingestion pipeline for {target_date}")

    results = {
        "date": target_date,
        "steps": {},
    }

    # Step 1: Sync ground stations
    try:
        station_result = sync_ground_stations.apply()
        results["steps"]["stations"] = station_result.get()
    except Exception as e:
        results["steps"]["stations"] = {"status": "error", "error": str(e)}

    # Step 2: Fetch ground readings
    try:
        readings_result = fetch_ground_readings.apply(args=[target_date])
        results["steps"]["readings"] = readings_result.get()
    except Exception as e:
        results["steps"]["readings"] = {"status": "error", "error": str(e)}

    # Step 3: Download satellite rasters
    try:
        rasters_result = download_all_pollutants.apply(args=[target_date])
        results["steps"]["rasters"] = rasters_result.get()
    except Exception as e:
        results["steps"]["rasters"] = {"status": "error", "error": str(e)}

    # Step 4: Trigger bias correction (deferred to correction app)
    # This will be called from correction.tasks.run_daily_correction_pipeline
    try:
        from correction.tasks import run_daily_correction_pipeline

        correction_result = run_daily_correction_pipeline.apply(args=[target_date])
        results["steps"]["correction"] = correction_result.get()
    except ImportError:
        results["steps"]["correction"] = {
            "status": "skipped",
            "reason": "correction app not installed",
        }
    except Exception as e:
        results["steps"]["correction"] = {"status": "error", "error": str(e)}

    logger.info(f"Daily pipeline complete for {target_date}")
    return results


def cleanup_old_rasters(keep_days: int = 90) -> dict:
    """
    Clean up raw rasters older than specified days.
    Corrected rasters in ImageMosaic are managed separately.

    Args:
        keep_days: Number of days to keep
    """
    from datetime import datetime, timedelta

    cutoff = date.today() - timedelta(days=keep_days)
    raster_manager = get_raster_manager()

    deleted_count = 0
    deleted_size = 0

    for pollutant in Pollutant:
        raw_dir = raster_manager.base_path / "raw" / pollutant.value.lower()
        if not raw_dir.exists():
            continue

        for raster_path in raw_dir.glob("*.tif"):
            try:
                # Extract date from filename
                parts = raster_path.stem.split("_")
                date_str = parts[-1]
                raster_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if raster_date < cutoff:
                    size = raster_path.stat().st_size
                    raster_path.unlink()
                    deleted_count += 1
                    deleted_size += size

            except (ValueError, IndexError):
                continue

    # Also cleanup database records
    PollutantRaster.objects.filter(
        date__lt=cutoff, corrected_file__isnull=True
    ).delete()

    logger.info(
        f"Cleaned up {deleted_count} old rasters ({deleted_size / 1024 / 1024:.1f} MB)"
    )

    return {
        "status": "success",
        "deleted_count": deleted_count,
        "deleted_size_mb": round(deleted_size / 1024 / 1024, 1),
        "cutoff_date": cutoff.isoformat(),
    }


# ==================== GeoServer Tasks ====================


def update_geoserver_mosaic(pollutant: str, target_date: str) -> dict:
    """
    Update GeoServer ImageMosaic with new corrected raster.

    Args:
        pollutant: Pollutant code
        target_date: ISO date string
    """
    dt = date.fromisoformat(target_date)
    raster_manager = get_raster_manager()
    geoserver_client = get_geoserver_client()

    # Get raster DB record and corrected raster path
    try:
        raster = PollutantRaster.objects.get(pollutant=pollutant, date=dt)
    except PollutantRaster.DoesNotExist:
        return {
            "status": "error",
            "error": f"No raster record found for {pollutant} on {target_date}",
        }

    # Prefer the corrected_file field (COG path) if available
    corrected_path = None
    if raster.corrected_file:
        corrected_path = Path(raster.corrected_file)
    else:
        corrected_path = raster_manager.get_corrected_path(pollutant, dt)

    if not corrected_path.exists():
        return {
            "status": "error",
            "error": f"Corrected raster not found: {corrected_path}",
        }

    try:
        # Copy to mosaic directory
        mosaic_path = raster_manager.copy_to_mosaic(pollutant, dt, corrected_path)

        # Add granule to GeoServer
        store_name = f"{pollutant.lower()}_corrected"
        geoserver_client.add_granule(
            store_name=store_name,
            coverage_name=store_name,
            granule_path=str(mosaic_path),
        )

        # Truncate tile cache for fresh tiles
        geoserver_client.truncate_layer_cache(store_name)

        return {
            "status": "success",
            "pollutant": pollutant,
            "date": target_date,
            "mosaic_path": str(mosaic_path),
        }

    except Exception as e:
        logger.error(f"Failed to update GeoServer mosaic: {e}")
        return {"status": "error", "error": str(e)}


def setup_geoserver_stores() -> dict:
    """
    Initialize GeoServer workspace and ImageMosaic stores.
    Should be run once during initial setup.
    """
    try:
        raster_manager = get_raster_manager()
        geoserver_client = get_geoserver_client()

        mosaic_base = str(raster_manager.base_path / "mosaics")

        # Ensure directories exist
        raster_manager.ensure_directories()

        # Setup all stores
        geoserver_client.setup_all_stores(mosaic_base)

        return {
            "status": "success",
            "workspace": geoserver_client.workspace,
            "mosaic_base": mosaic_base,
        }

    except Exception as e:
        logger.error(f"Failed to setup GeoServer: {e}")
        return {"status": "error", "error": str(e)}


def cleanup_geoserver_granules(keep_days: int = 90) -> dict:
    """
    Remove old granules from GeoServer ImageMosaic stores.

    Args:
        keep_days: Number of days to keep
    """
    geoserver_client = get_geoserver_client()
    results = {}

    for pollutant in Pollutant:
        store_name = f"{pollutant.value.lower()}_corrected"

        try:
            deleted = geoserver_client.delete_old_granules(
                store_name=store_name, coverage_name=store_name, keep_days=keep_days
            )
            results[pollutant.value] = {"status": "success", "deleted": deleted}
        except Exception as e:
            results[pollutant.value] = {"status": "error", "error": str(e)}

    return {"keep_days": keep_days, "results": results}
