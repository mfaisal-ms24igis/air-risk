"""
Population exposure calculators.
Implements pixel-level exposure calculation using WorldPop grid.
"""

import logging
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from rasterio.mask import mask as raster_mask
from django.conf import settings
from django.contrib.gis.geos import MultiPolygon

from air_quality.constants import calculate_aqi
from air_quality.models import District
from air_quality.services import get_raster_manager

logger = logging.getLogger(__name__)


def calculate_exposure_index(
    concentration: float, population: float, pollutant: str
) -> float:
    """
    Calculate exposure index for a pixel.

    Index = AQI × (population / reference_population)
    Normalized to 0-500 scale.

    Args:
        concentration: Pollutant concentration
        population: Population at pixel
        pollutant: Pollutant code

    Returns:
        Exposure index (0-500)
    """
    if concentration <= 0 or population <= 0:
        return 0.0

    aqi = calculate_aqi(pollutant, concentration)

    # Reference population for normalization (average Pakistan pixel ~200 people/km²)
    ref_pop = 200.0

    # Population weight (capped at 5x reference)
    pop_weight = min(population / ref_pop, 5.0)

    # Exposure index
    index = aqi * (0.5 + 0.5 * pop_weight)

    return min(index, 500.0)


def categorize_population_by_aqi(aqi_array: np.ndarray, pop_array: np.ndarray) -> dict:
    """
    Categorize population by AQI levels.

    Args:
        aqi_array: 2D array of AQI values
        pop_array: 2D array of population values

    Returns:
        Dictionary with population counts per category
    """
    # Flatten arrays
    aqi_flat = aqi_array.flatten()
    pop_flat = pop_array.flatten()

    # Remove nodata
    valid = ~(np.isnan(aqi_flat) | np.isnan(pop_flat))
    aqi_valid = aqi_flat[valid]
    pop_valid = pop_flat[valid]

    # Categorize
    categories = {
        "pop_good": 0,  # 0-50
        "pop_moderate": 0,  # 51-100
        "pop_usg": 0,  # 101-150
        "pop_unhealthy": 0,  # 151-200
        "pop_very_unhealthy": 0,  # 201-300
        "pop_hazardous": 0,  # >300
    }

    if len(aqi_valid) == 0:
        return categories

    categories["pop_good"] = int(np.sum(pop_valid[aqi_valid <= 50]))
    categories["pop_moderate"] = int(
        np.sum(pop_valid[(aqi_valid > 50) & (aqi_valid <= 100)])
    )
    categories["pop_usg"] = int(
        np.sum(pop_valid[(aqi_valid > 100) & (aqi_valid <= 150)])
    )
    categories["pop_unhealthy"] = int(
        np.sum(pop_valid[(aqi_valid > 150) & (aqi_valid <= 200)])
    )
    categories["pop_very_unhealthy"] = int(
        np.sum(pop_valid[(aqi_valid > 200) & (aqi_valid <= 300)])
    )
    categories["pop_hazardous"] = int(np.sum(pop_valid[aqi_valid > 300]))

    return categories


def calculate_district_exposure(
    district: District,
    pollutant: str,
    target_date: date,
    corrected_raster_path: Path = None,
    worldpop_path: Path = None,
) -> dict:
    """
    Calculate exposure statistics for a district.

    Uses pixel-level calculation:
    1. Mask both rasters to district boundary
    2. Calculate AQI at each pixel
    3. Weight by population

    Args:
        district: District model instance
        pollutant: Pollutant code
        target_date: Date of analysis
        corrected_raster_path: Path to corrected pollutant raster
        worldpop_path: Path to WorldPop population grid

    Returns:
        Dictionary with exposure statistics
    """
    if corrected_raster_path is None:
        raster_manager = get_raster_manager()
        corrected_raster_path = raster_manager.get_corrected_path(
            pollutant, target_date
        )

    if worldpop_path is None:
        worldpop_path = Path(settings.WORLDPOP_PATH)

    if not corrected_raster_path.exists():
        raise FileNotFoundError(f"Corrected raster not found: {corrected_raster_path}")

    if not worldpop_path.exists():
        raise FileNotFoundError(f"WorldPop grid not found: {worldpop_path}")

    # Get district geometry as GeoJSON
    import json

    geom = district.geometry
    if isinstance(geom, MultiPolygon):
        geom_geojson = json.loads(geom.json)
    else:
        geom_geojson = json.loads(geom.json)

    # Read and mask pollutant raster
    with rasterio.open(corrected_raster_path) as poll_src:
        poll_masked, poll_transform = raster_mask(
            poll_src, [geom_geojson], crop=True, nodata=np.nan
        )
        poll_data = poll_masked[0]  # First band

    # Read and mask population raster
    with rasterio.open(worldpop_path) as pop_src:
        # Need to handle different resolutions - resample if needed
        pop_masked, pop_transform = raster_mask(
            pop_src, [geom_geojson], crop=True, nodata=np.nan
        )
        pop_data = pop_masked[0]

    # Resample population to match pollutant resolution if needed
    if poll_data.shape != pop_data.shape:
        from scipy.ndimage import zoom

        zoom_factors = (
            poll_data.shape[0] / pop_data.shape[0],
            poll_data.shape[1] / pop_data.shape[1],
        )
        pop_data = zoom(pop_data, zoom_factors, order=1)

    # Create valid data mask
    valid_mask = ~(np.isnan(poll_data) | np.isnan(pop_data))

    if not np.any(valid_mask):
        logger.warning(f"No valid data for district {district.name}")
        return None

    poll_valid = poll_data[valid_mask]
    pop_valid = pop_data[valid_mask]

    # Calculate AQI for each pixel
    aqi_valid = np.array([calculate_aqi(pollutant, c) for c in poll_valid])

    # Calculate exposure indices
    exposure_valid = np.array(
        [
            calculate_exposure_index(c, p, pollutant)
            for c, p in zip(poll_valid, pop_valid)
        ]
    )

    # Total population
    total_pop = int(np.sum(pop_valid))

    # Population-weighted statistics
    if total_pop > 0:
        conc_mean = float(np.average(poll_valid, weights=pop_valid))
        aqi_mean = float(np.average(aqi_valid, weights=pop_valid))
        exposure_mean = float(np.average(exposure_valid, weights=pop_valid))
    else:
        conc_mean = float(np.mean(poll_valid))
        aqi_mean = float(np.mean(aqi_valid))
        exposure_mean = float(np.mean(exposure_valid))

    # Categorize population by AQI
    pop_categories = categorize_population_by_aqi(
        aqi_valid.reshape(-1, 1), pop_valid.reshape(-1, 1)
    )

    return {
        "district_id": district.id,
        "district_name": district.name,
        "pollutant": pollutant,
        "date": target_date,
        "total_population": total_pop,
        "concentration_mean": conc_mean,
        "concentration_min": float(np.min(poll_valid)),
        "concentration_max": float(np.max(poll_valid)),
        "concentration_std": float(np.std(poll_valid)),
        "aqi_mean": aqi_mean,
        "aqi_max": int(np.max(aqi_valid)),
        "exposure_index": exposure_mean,
        **pop_categories,
    }


def identify_hotspots(
    pollutant: str,
    target_date: date,
    aqi_threshold: int = 150,
    min_area_pixels: int = 10,
    corrected_raster_path: Path = None,
    worldpop_path: Path = None,
) -> list[dict]:
    """
    Identify pollution hotspots from spatial clustering.

    Args:
        pollutant: Pollutant code
        target_date: Date of analysis
        aqi_threshold: Minimum AQI for hotspot inclusion
        min_area_pixels: Minimum cluster size
        corrected_raster_path: Path to raster
        worldpop_path: Path to population grid

    Returns:
        List of hotspot dictionaries
    """
    from scipy import ndimage

    if corrected_raster_path is None:
        raster_manager = get_raster_manager()
        corrected_raster_path = raster_manager.get_corrected_path(
            pollutant, target_date
        )

    if worldpop_path is None:
        worldpop_path = Path(settings.WORLDPOP_PATH)

    # Read pollutant raster
    with rasterio.open(corrected_raster_path) as src:
        poll_data = src.read(1)
        transform = src.transform
        _ = src.crs  # Available for future use
        nodata = src.nodata

    # Read population raster
    with rasterio.open(worldpop_path) as src:
        pop_data = src.read(1)

    # Resample if needed
    if poll_data.shape != pop_data.shape:
        from scipy.ndimage import zoom

        zoom_factors = (
            poll_data.shape[0] / pop_data.shape[0],
            poll_data.shape[1] / pop_data.shape[1],
        )
        pop_data = zoom(pop_data, zoom_factors, order=1)

    # Calculate AQI grid
    valid_mask = ~np.isnan(poll_data)
    if nodata is not None:
        valid_mask = valid_mask & (poll_data != nodata)

    aqi_grid = np.full_like(poll_data, np.nan)
    aqi_grid[valid_mask] = np.array(
        [calculate_aqi(pollutant, c) for c in poll_data[valid_mask]]
    )

    # Threshold to find high AQI areas
    high_aqi_mask = aqi_grid >= aqi_threshold

    # Label connected components
    labeled, num_features = ndimage.label(high_aqi_mask)

    hotspots = []

    for label_id in range(1, num_features + 1):
        cluster_mask = labeled == label_id
        n_pixels = np.sum(cluster_mask)

        if n_pixels < min_area_pixels:
            continue

        # Get cluster statistics
        cluster_poll = poll_data[cluster_mask]
        cluster_aqi = aqi_grid[cluster_mask]
        cluster_pop = pop_data[cluster_mask]

        # Calculate centroid
        rows, cols = np.where(cluster_mask)
        center_row = int(np.mean(rows))
        center_col = int(np.mean(cols))
        center_x, center_y = rasterio.transform.xy(transform, center_row, center_col)

        # Estimate area (pixels × pixel area)
        pixel_area_km2 = abs(transform.a * transform.e) / 1e6  # Convert m² to km²
        area_km2 = n_pixels * pixel_area_km2

        # Determine severity
        mean_aqi = np.mean(cluster_aqi)
        if mean_aqi >= 300:
            severity = "CRITICAL"
        elif mean_aqi >= 200:
            severity = "SEVERE"
        elif mean_aqi >= 150:
            severity = "HIGH"
        else:
            severity = "MODERATE"

        # Affected population
        affected_pop = int(np.sum(cluster_pop[~np.isnan(cluster_pop)]))

        hotspots.append(
            {
                "pollutant": pollutant,
                "date": target_date,
                "centroid_lon": center_x,
                "centroid_lat": center_y,
                "area_sq_km": area_km2,
                "severity": severity,
                "concentration_mean": float(np.mean(cluster_poll)),
                "concentration_max": float(np.max(cluster_poll)),
                "aqi_mean": int(mean_aqi),
                "affected_population": affected_pop,
            }
        )

    # Sort by affected population
    hotspots.sort(key=lambda x: x["affected_population"], reverse=True)

    logger.info(f"Identified {len(hotspots)} hotspots for {pollutant} on {target_date}")
    return hotspots


def calculate_national_summary(pollutant: str, target_date: date) -> dict:
    """
    Calculate national-level exposure summary.

    Args:
        pollutant: Pollutant code
        target_date: Date of analysis

    Returns:
        Dictionary with national statistics
    """
    from .models import DistrictExposure, Hotspot
    from django.db.models import Sum, Avg, Max

    # Aggregate from district exposures
    district_agg = DistrictExposure.objects.filter(
        pollutant=pollutant, date=target_date
    ).aggregate(
        total_pop=Sum("total_population"),
        mean_conc=Avg("concentration_mean"),
        max_conc=Max("concentration_max"),
        mean_aqi=Avg("aqi_mean"),
        mean_exposure=Avg("exposure_index"),
        pop_good=Sum("pop_good"),
        pop_moderate=Sum("pop_moderate"),
        pop_usg=Sum("pop_usg"),
        pop_unhealthy=Sum("pop_unhealthy"),
        pop_very_unhealthy=Sum("pop_very_unhealthy"),
        pop_hazardous=Sum("pop_hazardous"),
    )

    # Count hotspots
    n_hotspots = Hotspot.objects.filter(pollutant=pollutant, date=target_date).count()

    # Find worst district
    worst = DistrictExposure.objects.filter(
        pollutant=pollutant, date=target_date, rank=1
    ).first()

    return {
        "pollutant": pollutant,
        "date": target_date,
        "total_population": district_agg["total_pop"] or 0,
        "concentration_mean": district_agg["mean_conc"],
        "concentration_max": district_agg["max_conc"],
        "aqi_mean": district_agg["mean_aqi"],
        "exposure_index": district_agg["mean_exposure"],
        "pop_good": district_agg["pop_good"] or 0,
        "pop_moderate": district_agg["pop_moderate"] or 0,
        "pop_usg": district_agg["pop_usg"] or 0,
        "pop_unhealthy": district_agg["pop_unhealthy"] or 0,
        "pop_very_unhealthy": district_agg["pop_very_unhealthy"] or 0,
        "pop_hazardous": district_agg["pop_hazardous"] or 0,
        "n_hotspots": n_hotspots,
        "worst_district_id": worst.district_id if worst else None,
    }
