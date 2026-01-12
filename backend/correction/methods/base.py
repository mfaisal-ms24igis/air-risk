"""
Base class for bias correction methods.
"""

import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Tuple
import pickle

import numpy as np
import rasterio

from air_quality.services import read_raster_at_points

logger = logging.getLogger(__name__)


class BaseCorrector(ABC):
    """
    Abstract base class for bias correction methods.
    """

    def __init__(self, pollutant: str):
        self.pollutant = pollutant
        self.model = None
        self.is_fitted = False
        self.metrics = {}

    @abstractmethod
    def fit(
        self, X: np.ndarray, y: np.ndarray, coords: np.ndarray, **kwargs
    ) -> "BaseCorrector":
        """
        Fit the correction model.

        Args:
            X: Satellite values (n_samples,)
            y: Ground truth values (n_samples,)
            coords: Coordinates array (n_samples, 2) as [lon, lat]
            **kwargs: Additional model-specific parameters

        Returns:
            Self for method chaining
        """
        pass

    @abstractmethod
    def predict(self, X: np.ndarray, coords: np.ndarray) -> np.ndarray:
        """
        Predict corrected values.

        Args:
            X: Satellite values (n_samples,)
            coords: Coordinates array (n_samples, 2) as [lon, lat]

        Returns:
            Corrected values array
        """
        pass

    def correct_raster(self, input_path: Path, output_path: Path) -> Path:
        """
        Apply correction to a full raster.

        Args:
            input_path: Path to input raster
            output_path: Path for corrected output

        Returns:
            Path to corrected raster
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")

        with rasterio.open(input_path) as src:
            profile = src.profile.copy()
            data = src.read(1)
            nodata = src.nodata
            transform = src.transform

            # Create coordinate grids
            rows, cols = np.indices(data.shape)
            xs, ys = rasterio.transform.xy(transform, rows.flatten(), cols.flatten())
            coords = np.column_stack([xs, ys])

            # Flatten data
            flat_data = data.flatten()

            # Create mask for valid data
            if nodata is not None:
                valid_mask = flat_data != nodata
            else:
                valid_mask = ~np.isnan(flat_data)

            # Apply correction only to valid pixels
            corrected_flat = flat_data.copy()

            if np.sum(valid_mask) > 0:
                valid_data = flat_data[valid_mask]
                valid_coords = coords[valid_mask]

                corrected_values = self.predict(valid_data, valid_coords)
                corrected_flat[valid_mask] = corrected_values

            # Reshape back to raster dimensions
            corrected_data = corrected_flat.reshape(data.shape)

            # Write output
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(corrected_data.astype(profile["dtype"]), 1)

        logger.info(f"Corrected raster saved: {output_path}")
        return output_path

    def save(self, filepath: Path) -> None:
        """Save the fitted model to a file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "pollutant": self.pollutant,
                    "model": self.model,
                    "is_fitted": self.is_fitted,
                    "metrics": self.metrics,
                },
                f,
            )
        logger.info(f"Model saved: {filepath}")

    def load(self, filepath: Path) -> "BaseCorrector":
        """Load a fitted model from a file."""
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        self.pollutant = data["pollutant"]
        self.model = data["model"]
        self.is_fitted = data["is_fitted"]
        self.metrics = data["metrics"]

        logger.info(f"Model loaded: {filepath}")
        return self

    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """Calculate performance metrics."""
        # Remove NaN values
        mask = ~(np.isnan(y_true) | np.isnan(y_pred))
        y_true = y_true[mask]
        y_pred = y_pred[mask]

        if len(y_true) == 0:
            return {}

        residuals = y_true - y_pred
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

        metrics = {
            "r_squared": 1 - (ss_res / ss_tot) if ss_tot > 0 else 0,
            "rmse": np.sqrt(np.mean(residuals**2)),
            "mae": np.mean(np.abs(residuals)),
            "bias": np.mean(residuals),
            "n_samples": len(y_true),
        }

        return metrics

    def cross_validate(
        self, X: np.ndarray, y: np.ndarray, coords: np.ndarray, n_folds: int = 5
    ) -> dict:
        """
        Perform k-fold cross-validation.

        Args:
            X: Satellite values
            y: Ground truth values
            coords: Coordinates array
            n_folds: Number of folds

        Returns:
            Dictionary of CV metrics
        """
        from sklearn.model_selection import KFold

        kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

        cv_metrics = {
            "r_squared": [],
            "rmse": [],
            "mae": [],
        }

        for train_idx, test_idx in kf.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            coords_train, coords_test = coords[train_idx], coords[test_idx]

            # Create a new instance for this fold
            fold_model = self.__class__(self.pollutant)
            fold_model.fit(X_train, y_train, coords_train)

            y_pred = fold_model.predict(X_test, coords_test)
            metrics = self.calculate_metrics(y_test, y_pred)

            for key in cv_metrics:
                if key in metrics:
                    cv_metrics[key].append(metrics[key])

        return {
            "cv_r_squared": np.mean(cv_metrics["r_squared"]),
            "cv_rmse": np.mean(cv_metrics["rmse"]),
            "cv_r_squared_std": np.std(cv_metrics["r_squared"]),
            "cv_rmse_std": np.std(cv_metrics["rmse"]),
        }


def prepare_training_data(
    pollutant: str, start_date: date, end_date: date, min_stations: int = 5
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """
    Prepare training data by matching ground readings with satellite values.

    Args:
        pollutant: Pollutant code
        start_date: Start of training period
        end_date: End of training period
        min_stations: Minimum number of stations required

    Returns:
        Tuple of (X, y, coords, station_ids)
    """
    from air_quality.models import GroundStation, GroundReading, PollutantRaster

    field_name = pollutant.lower()

    # Get all stations with data for this pollutant
    stations = GroundStation.objects.filter(
        is_active=True, available_parameters__contains=[pollutant]
    )

    if stations.count() < min_stations:
        raise ValueError(f"Insufficient stations ({stations.count()} < {min_stations})")

    X_list = []
    y_list = []
    coords_list = []
    station_ids = []

    # Get all dates with raster data
    rasters = PollutantRaster.objects.filter(
        pollutant=pollutant,
        date__gte=start_date,
        date__lte=end_date,
    ).exclude(raw_file="")

    for raster in rasters:
        raster_path = Path(raster.raw_file)
        if not raster_path.exists():
            continue

        # Get station coordinates
        station_coords = []
        station_objs = []

        for station in stations:
            if station.location:
                station_coords.append((station.location.x, station.location.y))
                station_objs.append(station)

        if not station_coords:
            continue

        # Read satellite values at station locations
        satellite_values = read_raster_at_points(raster_path, station_coords)

        # Get ground readings for this date
        for i, station in enumerate(station_objs):
            sat_value = satellite_values[i]
            if sat_value is None:
                continue

            # Get ground reading for this station and date
            reading = GroundReading.objects.filter(
                station=station,
                timestamp__date=raster.date,
            ).first()

            if reading is None:
                continue

            ground_value = getattr(reading, field_name, None)
            if ground_value is None:
                continue

            X_list.append(sat_value)
            y_list.append(ground_value)
            coords_list.append(station_coords[i])
            station_ids.append(station.id)

    if len(X_list) < min_stations:
        raise ValueError(f"Insufficient training samples ({len(X_list)})")

    return (np.array(X_list), np.array(y_list), np.array(coords_list), station_ids)
