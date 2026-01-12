"""
Django-Q tasks for bias correction.
Handles model training and raster correction.
"""

import logging
from datetime import date, timedelta
from pathlib import Path

from django.utils import timezone
from django.conf import settings

from .models import CorrectionModel, CalibrationPoint, CorrectionRun
from .methods import GWRCorrector, LinearCorrector
from .methods.base import prepare_training_data
from air_quality.constants import Pollutant
from air_quality.models import PollutantRaster
from air_quality.services import (
    get_raster_manager,
    ensure_cog,
)

logger = logging.getLogger(__name__)

# Threshold for using GWR vs Linear
GWR_MIN_STATIONS = 10


def train_correction_model(pollutant: str, training_days: int = 180) -> dict:
    """
    Train a new correction model for a pollutant.

    Uses GWR if sufficient stations, otherwise falls back to linear.

    Args:
        pollutant: Pollutant code
        training_days: Number of days of historical data to use

    Returns:
        Dictionary with training results
    """

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=training_days)

    logger.info(
        f"Training correction model for {pollutant} ({start_date} to {end_date})"
    )

    # Create model record
    model_record = CorrectionModel.objects.create(
        pollutant=pollutant,
        training_start_date=start_date,
        training_end_date=end_date,
        status="TRAINING",
    )

    try:
        # Prepare training data
        X, y, coords, station_ids = prepare_training_data(
            pollutant, start_date, end_date, min_stations=3
        )

        n_stations = len(set(station_ids))
        n_samples = len(X)

        model_record.training_samples = n_samples
        model_record.training_stations = n_stations
        model_record.save()

        logger.info(f"Training data: {n_samples} samples from {n_stations} stations")

        # Choose model type based on number of stations
        if n_stations >= GWR_MIN_STATIONS:
            logger.info("Using GWR correction")
            corrector = GWRCorrector(pollutant)
            model_type = "GWR"
        else:
            logger.info(f"Using Linear correction (only {n_stations} stations)")
            corrector = LinearCorrector(pollutant)
            model_type = "LINEAR"

        # Fit model
        corrector.fit(X, y, coords)

        # Cross-validate
        cv_metrics = corrector.cross_validate(X, y, coords, n_folds=min(5, n_stations))

        # Save model to file
        model_dir = Path(settings.RASTER_STORAGE_PATH) / "models"
        model_path = model_dir / f"{pollutant.lower()}_{model_record.id}.pkl"
        corrector.save(model_path)

        # Update model record
        model_record.model_type = model_type
        model_record.model_file = str(model_path)
        model_record.r_squared = corrector.metrics.get("r_squared")
        model_record.rmse = corrector.metrics.get("rmse")
        model_record.mae = corrector.metrics.get("mae")
        model_record.bias = corrector.metrics.get("bias")
        model_record.cv_r_squared = cv_metrics.get("cv_r_squared")
        model_record.cv_rmse = cv_metrics.get("cv_rmse")

        if model_type == "GWR":
            model_record.bandwidth = corrector.metrics.get("bandwidth")
            model_record.kernel = corrector.kernel
            model_record.local_r_squared_min = corrector.metrics.get(
                "local_r_squared_min"
            )
            model_record.local_r_squared_max = corrector.metrics.get(
                "local_r_squared_max"
            )
            model_record.local_r_squared_mean = corrector.metrics.get(
                "local_r_squared_mean"
            )

        model_record.status = "ACTIVE"
        model_record.is_active = True
        model_record.save()

        # Store calibration points
        y_pred = corrector.predict(X, coords)
        for i in range(len(X)):
            CalibrationPoint.objects.create(
                correction_model=model_record,
                station_id=station_ids[i],
                date=end_date,  # Simplified - actual dates would be stored
                ground_value=float(y[i]),
                satellite_value=float(X[i]),
                corrected_value=float(y_pred[i]),
                residual=float(y[i] - y_pred[i]),
            )

        logger.info(f"Model trained successfully: {model_record}")

        return {
            "status": "success",
            "model_id": model_record.id,
            "model_type": model_type,
            "pollutant": pollutant,
            "n_samples": n_samples,
            "n_stations": n_stations,
            "r_squared": model_record.r_squared,
            "rmse": model_record.rmse,
            "cv_r_squared": model_record.cv_r_squared,
        }

    except Exception as exc:
        model_record.status = "FAILED"
        model_record.notes = str(exc)
        model_record.save()

        logger.error(f"Model training failed: {exc}")
        raise self.retry(exc=exc)


def apply_correction(
    pollutant: str, target_date: str, model_id: int = None
) -> dict:
    """
    Apply bias correction to a raster.

    Args:
        pollutant: Pollutant code
        target_date: ISO date string
        model_id: Specific model to use (defaults to active model)

    Returns:
        Dictionary with correction results
    """
    dt = date.fromisoformat(target_date)

    # Get raster
    try:
        raster = PollutantRaster.objects.get(pollutant=pollutant, date=dt)
    except PollutantRaster.DoesNotExist:
        return {
            "status": "error",
            "error": f"No raster found for {pollutant} on {target_date}",
        }

    if not raster.raw_file or not Path(raster.raw_file).exists():
        return {"status": "error", "error": "Raw raster file not found"}

    # Get correction model
    if model_id:
        model_record = CorrectionModel.objects.get(pk=model_id)
    else:
        model_record = CorrectionModel.get_active_model(pollutant)

    if not model_record:
        return {
            "status": "error",
            "error": f"No active correction model for {pollutant}",
        }

    # Create correction run record
    run = CorrectionRun.objects.create(
        correction_model=model_record,
        raster=raster,
        status="RUNNING",
        started_at=timezone.now(),
    )

    try:
        # Load model
        if model_record.model_type == "GWR":
            corrector = GWRCorrector(pollutant)
        else:
            corrector = LinearCorrector(pollutant)

        corrector.load(Path(model_record.model_file))

        # Prepare paths
        raster_manager = get_raster_manager()
        input_path = Path(raster.raw_file)
        output_path = raster_manager.get_corrected_path(pollutant, dt)

        # Apply correction
        logger.info(f"Applying correction: {input_path} -> {output_path}")
        corrector.correct_raster(input_path, output_path)

        # Convert to COG
        cog_path = ensure_cog(output_path)

        # Get statistics
        from air_quality.services import get_raster_stats

        stats = get_raster_stats(cog_path)

        # Update run record
        run.status = "SUCCESS"
        run.completed_at = timezone.now()
        run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
        run.output_file = str(cog_path)
        run.stats = stats
        run.save()

        # Update raster record
        raster.corrected_file = str(cog_path)
        raster.stats = stats
        raster.save()

        logger.info(f"Correction applied successfully: {run}")

        return {
            "status": "success",
            "run_id": run.id,
            "output_file": str(cog_path),
            "stats": stats,
            "duration": run.duration_seconds,
        }

    except Exception as exc:
        run.status = "FAILED"
        run.completed_at = timezone.now()
        run.error_message = str(exc)
        run.save()

        logger.error(f"Correction failed: {exc}")
        raise self.retry(exc=exc)


def run_daily_correction_pipeline(target_date: str = None) -> dict:
    """
    Run the daily correction pipeline for all pollutants.

    Steps:
    1. Apply correction to each pollutant's raster
    2. Copy to ImageMosaic directory
    3. Update GeoServer

    Args:
        target_date: ISO date string (defaults to yesterday)
    """
    if target_date is None:
        target_date = (date.today() - timedelta(days=1)).isoformat()

    logger.info(f"Running daily correction pipeline for {target_date}")

    results = {}

    for pollutant in Pollutant:
        p = pollutant.value

        try:
            # Apply correction
            correction_result = apply_correction.apply(args=[p, target_date]).get()

            if correction_result.get("status") == "success":
                # Copy to mosaic and update GeoServer
                from air_quality.tasks import update_geoserver_mosaic

                geoserver_result = update_geoserver_mosaic.apply(
                    args=[p, target_date]
                ).get()

                results[p] = {
                    "correction": correction_result,
                    "geoserver": geoserver_result,
                }
            else:
                results[p] = {
                    "correction": correction_result,
                    "geoserver": {"status": "skipped"},
                }

        except Exception as e:
            results[p] = {"status": "error", "error": str(e)}

    return {"date": target_date, "results": results}


def retrain_all_models(training_days: int = 180) -> dict:
    """
    Retrain correction models for all pollutants.
    Should be run weekly to incorporate new ground data.

    Args:
        training_days: Number of days of data to use
    """
    logger.info("Retraining all correction models")

    results = {}

    for pollutant in Pollutant:
        try:
            result = train_correction_model.apply(
                args=[pollutant.value, training_days]
            ).get()
            results[pollutant.value] = result
        except Exception as e:
            results[pollutant.value] = {"status": "error", "error": str(e)}

    return {"training_days": training_days, "results": results}


def evaluate_model_performance(pollutant: str, evaluation_days: int = 30) -> dict:
    """
    Evaluate current model performance on recent data.

    Args:
        pollutant: Pollutant code
        evaluation_days: Number of recent days to evaluate
    """
    from air_quality.models import GroundStation, GroundReading
    from air_quality.services import read_raster_at_points
    import numpy as np

    model_record = CorrectionModel.get_active_model(pollutant)
    if not model_record:
        return {"status": "error", "error": "No active model"}

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=evaluation_days)

    # Load model
    if model_record.model_type == "GWR":
        corrector = GWRCorrector(pollutant)
    else:
        corrector = LinearCorrector(pollutant)
    corrector.load(Path(model_record.model_file))

    # Collect evaluation data from corrected rasters
    actual_values = []
    predicted_values = []

    rasters = PollutantRaster.objects.filter(
        pollutant=pollutant,
        date__gte=start_date,
        date__lte=end_date,
    ).exclude(corrected_file="")

    stations = GroundStation.objects.filter(
        is_active=True, available_parameters__contains=[pollutant]
    )

    for raster in rasters:
        corrected_path = Path(raster.corrected_file)
        if not corrected_path.exists():
            continue

        station_coords = []
        for station in stations:
            if station.location:
                station_coords.append((station.location.x, station.location.y))

        if not station_coords:
            continue

        # Read corrected values
        corrected_values = read_raster_at_points(corrected_path, station_coords)

        # Get ground readings
        field_name = pollutant.lower()
        for i, station in enumerate(stations):
            if station.location is None:
                continue

            corrected = corrected_values[i]
            if corrected is None:
                continue

            reading = GroundReading.objects.filter(
                station=station, timestamp__date=raster.date
            ).first()

            if reading:
                actual = getattr(reading, field_name, None)
                if actual is not None:
                    actual_values.append(actual)
                    predicted_values.append(corrected)

    if len(actual_values) < 5:
        return {"status": "insufficient_data", "n_samples": len(actual_values)}

    # Calculate metrics
    actual = np.array(actual_values)
    predicted = np.array(predicted_values)
    metrics = corrector.calculate_metrics(actual, predicted)

    return {
        "status": "success",
        "model_id": model_record.id,
        "evaluation_period": f"{start_date} to {end_date}",
        "n_samples": len(actual_values),
        "metrics": metrics,
    }
