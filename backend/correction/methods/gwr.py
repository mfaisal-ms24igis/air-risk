"""
Geographically Weighted Regression (GWR) bias correction.
Uses mgwr library for spatially-varying coefficients.
"""

import logging

import numpy as np
from scipy.spatial.distance import cdist

from .base import BaseCorrector

logger = logging.getLogger(__name__)

# Minimum samples required for GWR
GWR_MIN_SAMPLES = 10


class GWRCorrector(BaseCorrector):
    """
    Geographically Weighted Regression corrector.

    Fits a local regression model where coefficients vary spatially.
    Useful when the relationship between satellite and ground values
    varies across different locations.
    """

    def __init__(
        self,
        pollutant: str,
        kernel: str = "bisquare",
        fixed: bool = False,
        constant: bool = True,
    ):
        """
        Initialize GWR corrector.

        Args:
            pollutant: Pollutant code
            kernel: Kernel function ('gaussian', 'bisquare', 'exponential')
            fixed: If True, use fixed bandwidth; if False, use adaptive
            constant: If True, include intercept term
        """
        super().__init__(pollutant)
        self.kernel = kernel
        self.fixed = fixed
        self.constant = constant
        self.bandwidth = None
        self.coords_train = None
        self.X_train = None
        self.y_train = None
        self.local_params = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        coords: np.ndarray,
        bandwidth: float = None,
        **kwargs,
    ) -> "GWRCorrector":
        """
        Fit GWR model.

        Args:
            X: Satellite values (n_samples,)
            y: Ground truth values (n_samples,)
            coords: Coordinates array (n_samples, 2) as [lon, lat]
            bandwidth: Fixed bandwidth value (optional, otherwise optimized)

        Returns:
            Self for method chaining
        """
        n_samples = len(X)

        if n_samples < GWR_MIN_SAMPLES:
            raise ValueError(
                f"GWR requires at least {GWR_MIN_SAMPLES} samples, got {n_samples}"
            )

        # Store training data for prediction
        self.coords_train = coords
        self.X_train = X.reshape(-1, 1) if X.ndim == 1 else X
        self.y_train = y

        try:
            # Try using mgwr library
            from mgwr.gwr import GWR
            from mgwr.sel_bw import Sel_BW
            import libpysal  # noqa: F401 - required for mgwr internals

            # Prepare design matrix
            if self.constant:
                X_design = np.column_stack([np.ones(n_samples), self.X_train])
            else:
                X_design = self.X_train

            # Select optimal bandwidth if not provided
            if bandwidth is None:
                logger.info("Selecting optimal bandwidth...")
                selector = Sel_BW(
                    coords, y, X_design, kernel=self.kernel, fixed=self.fixed
                )
                self.bandwidth = selector.search(criterion="AICc")
                logger.info(f"Optimal bandwidth: {self.bandwidth}")
            else:
                self.bandwidth = bandwidth

            # Fit GWR model
            logger.info("Fitting GWR model...")
            self.model = GWR(
                coords,
                y,
                X_design,
                bw=self.bandwidth,
                kernel=self.kernel,
                fixed=self.fixed,
            ).fit()

            # Store local parameters
            self.local_params = self.model.params

            # Calculate metrics
            y_pred = self.model.predy.flatten()
            self.metrics = self.calculate_metrics(y, y_pred)
            self.metrics["bandwidth"] = self.bandwidth

            # Local R² statistics
            if hasattr(self.model, "localR2"):
                local_r2 = self.model.localR2
                self.metrics["local_r_squared_min"] = float(np.min(local_r2))
                self.metrics["local_r_squared_max"] = float(np.max(local_r2))
                self.metrics["local_r_squared_mean"] = float(np.mean(local_r2))

            logger.info(
                f"GWR fitted: R²={self.metrics['r_squared']:.4f}, RMSE={self.metrics['rmse']:.4f}"
            )

        except ImportError:
            logger.warning("mgwr not available, falling back to custom implementation")
            self._fit_custom(X, y, coords, bandwidth)

        self.is_fitted = True
        return self

    def _fit_custom(
        self, X: np.ndarray, y: np.ndarray, coords: np.ndarray, bandwidth: float = None
    ):
        """
        Custom GWR implementation when mgwr is not available.
        Uses weighted least squares with spatial kernel.
        """
        n_samples = len(X)

        # Calculate pairwise distances
        distances = cdist(coords, coords)

        # Determine bandwidth using rule of thumb if not provided
        if bandwidth is None:
            # Use median distance as starting point
            self.bandwidth = np.median(distances) * 0.5
        else:
            self.bandwidth = bandwidth

        # Calculate kernel weights
        weights = self._kernel_weights(distances, self.bandwidth)

        # Fit local models at each point
        self.local_params = np.zeros((n_samples, 2))  # [intercept, slope]
        y_pred = np.zeros(n_samples)

        X_with_intercept = np.column_stack([np.ones(n_samples), X])

        for i in range(n_samples):
            W = np.diag(weights[i])

            # Weighted least squares: (X'WX)^-1 X'Wy
            XtW = X_with_intercept.T @ W
            try:
                beta = np.linalg.solve(XtW @ X_with_intercept, XtW @ y)
            except np.linalg.LinAlgError:
                # Fallback to pseudo-inverse
                beta = np.linalg.lstsq(XtW @ X_with_intercept, XtW @ y, rcond=None)[0]

            self.local_params[i] = beta
            y_pred[i] = X_with_intercept[i] @ beta

        self.metrics = self.calculate_metrics(y, y_pred)
        self.metrics["bandwidth"] = self.bandwidth
        self.model = "custom"

        logger.info(f"Custom GWR fitted: R²={self.metrics['r_squared']:.4f}")

    def _kernel_weights(self, distances: np.ndarray, bandwidth: float) -> np.ndarray:
        """Calculate kernel weights from distances."""
        u = distances / bandwidth

        if self.kernel == "gaussian":
            weights = np.exp(-0.5 * u**2)
        elif self.kernel == "bisquare":
            weights = np.where(u < 1, (1 - u**2) ** 2, 0)
        elif self.kernel == "exponential":
            weights = np.exp(-u)
        else:
            raise ValueError(f"Unknown kernel: {self.kernel}")

        return weights

    def predict(self, X: np.ndarray, coords: np.ndarray) -> np.ndarray:
        """
        Predict corrected values using GWR.

        For new locations, interpolates local parameters from
        nearest training points.

        Args:
            X: Satellite values (n_samples,)
            coords: Coordinates array (n_samples, 2)

        Returns:
            Corrected values array
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")

        n_samples = len(X)
        y_pred = np.zeros(n_samples)

        # Calculate distances to training points
        distances = cdist(coords, self.coords_train)
        weights = self._kernel_weights(distances, self.bandwidth)

        for i in range(n_samples):
            # Weighted average of local parameters
            w = weights[i]
            w_sum = np.sum(w)

            if w_sum > 0:
                # Interpolate local parameters
                local_intercept = np.sum(w * self.local_params[:, 0]) / w_sum
                local_slope = np.sum(w * self.local_params[:, 1]) / w_sum
            else:
                # Use global average
                local_intercept = np.mean(self.local_params[:, 0])
                local_slope = np.mean(self.local_params[:, 1])

            y_pred[i] = local_intercept + local_slope * X[i]

        # Ensure non-negative values for concentrations
        y_pred = np.maximum(y_pred, 0)

        return y_pred

    def get_local_coefficients(self) -> dict:
        """Get local coefficient statistics."""
        if self.local_params is None:
            return {}

        return {
            "intercept": {
                "min": float(np.min(self.local_params[:, 0])),
                "max": float(np.max(self.local_params[:, 0])),
                "mean": float(np.mean(self.local_params[:, 0])),
                "std": float(np.std(self.local_params[:, 0])),
            },
            "slope": {
                "min": float(np.min(self.local_params[:, 1])),
                "max": float(np.max(self.local_params[:, 1])),
                "mean": float(np.mean(self.local_params[:, 1])),
                "std": float(np.std(self.local_params[:, 1])),
            },
        }
