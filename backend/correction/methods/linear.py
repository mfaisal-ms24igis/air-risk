"""
Linear regression bias correction.
Fallback method when GWR cannot be applied (insufficient stations).
"""

import logging

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

from .base import BaseCorrector

logger = logging.getLogger(__name__)


class LinearCorrector(BaseCorrector):
    """
    Global linear regression corrector.

    Fits a single linear model across all locations.
    Used as fallback when there aren't enough ground stations for GWR.
    """

    def __init__(self, pollutant: str, use_ridge: bool = False, alpha: float = 1.0):
        """
        Initialize linear corrector.

        Args:
            pollutant: Pollutant code
            use_ridge: If True, use Ridge regression with regularization
            alpha: Ridge regularization parameter
        """
        super().__init__(pollutant)
        self.use_ridge = use_ridge
        self.alpha = alpha
        self.scaler = None
        self.intercept = None
        self.slope = None

    def fit(
        self, X: np.ndarray, y: np.ndarray, coords: np.ndarray = None, **kwargs
    ) -> "LinearCorrector":
        """
        Fit linear regression model.

        Args:
            X: Satellite values (n_samples,)
            y: Ground truth values (n_samples,)
            coords: Coordinates (not used, for API compatibility)

        Returns:
            Self for method chaining
        """
        X = X.reshape(-1, 1) if X.ndim == 1 else X

        # Remove NaN values
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X_clean = X[mask]
        y_clean = y[mask]

        if len(y_clean) < 3:
            raise ValueError(
                f"Insufficient samples for linear regression: {len(y_clean)}"
            )

        # Optional scaling
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_clean)

        # Fit model
        if self.use_ridge:
            self.model = Ridge(alpha=self.alpha)
        else:
            self.model = LinearRegression()

        self.model.fit(X_scaled, y_clean)

        # Store coefficients (in original scale)
        self.intercept = self.model.intercept_
        self.slope = self.model.coef_[0] / self.scaler.scale_[0]

        # Calculate metrics
        y_pred = self.model.predict(X_scaled)
        self.metrics = self.calculate_metrics(y_clean, y_pred)
        self.metrics["intercept"] = float(self.intercept)
        self.metrics["slope"] = float(self.slope)

        logger.info(
            f"Linear model fitted: R²={self.metrics['r_squared']:.4f}, "
            f"y = {self.intercept:.4f} + {self.slope:.4f}x"
        )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray, coords: np.ndarray = None) -> np.ndarray:
        """
        Predict corrected values using linear model.

        Args:
            X: Satellite values (n_samples,)
            coords: Coordinates (not used)

        Returns:
            Corrected values array
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")

        X = X.reshape(-1, 1) if X.ndim == 1 else X

        # Handle NaN values
        result = np.full(len(X), np.nan)
        valid_mask = ~np.isnan(X).any(axis=1)

        if np.any(valid_mask):
            X_valid = X[valid_mask]
            X_scaled = self.scaler.transform(X_valid)
            y_pred = self.model.predict(X_scaled)

            # Ensure non-negative values
            y_pred = np.maximum(y_pred, 0)
            result[valid_mask] = y_pred

        return result

    def get_equation(self) -> str:
        """Get the regression equation as a string."""
        if not self.is_fitted:
            return "Model not fitted"

        sign = "+" if self.slope >= 0 else ""
        return f"y = {self.intercept:.4f} {sign}{self.slope:.4f}x"


class RobustLinearCorrector(BaseCorrector):
    """
    Robust linear regression using RANSAC.
    Handles outliers better than standard OLS.
    """

    def __init__(
        self, pollutant: str, min_samples: float = 0.5, residual_threshold: float = None
    ):
        """
        Initialize robust linear corrector.

        Args:
            pollutant: Pollutant code
            min_samples: Minimum fraction of samples for RANSAC
            residual_threshold: Threshold for inlier classification
        """
        super().__init__(pollutant)
        self.min_samples = min_samples
        self.residual_threshold = residual_threshold
        self.scaler = None

    def fit(
        self, X: np.ndarray, y: np.ndarray, coords: np.ndarray = None, **kwargs
    ) -> "RobustLinearCorrector":
        """
        Fit RANSAC linear model.
        """
        from sklearn.linear_model import RANSACRegressor

        X = X.reshape(-1, 1) if X.ndim == 1 else X

        # Remove NaN values
        mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X_clean = X[mask]
        y_clean = y[mask]

        if len(y_clean) < 5:
            raise ValueError(f"Insufficient samples for RANSAC: {len(y_clean)}")

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_clean)

        # Fit RANSAC model
        self.model = RANSACRegressor(
            min_samples=self.min_samples,
            residual_threshold=self.residual_threshold,
            random_state=42,
        )
        self.model.fit(X_scaled, y_clean)

        # Calculate metrics on inliers
        inlier_mask = self.model.inlier_mask_
        y_pred = self.model.predict(X_scaled)

        self.metrics = self.calculate_metrics(y_clean, y_pred)
        self.metrics["n_inliers"] = int(np.sum(inlier_mask))
        self.metrics["inlier_ratio"] = float(np.mean(inlier_mask))

        logger.info(
            f"RANSAC fitted: R²={self.metrics['r_squared']:.4f}, "
            f"inliers={self.metrics['inlier_ratio'] * 100:.1f}%"
        )

        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray, coords: np.ndarray = None) -> np.ndarray:
        """Predict corrected values."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")

        X = X.reshape(-1, 1) if X.ndim == 1 else X

        result = np.full(len(X), np.nan)
        valid_mask = ~np.isnan(X).any(axis=1)

        if np.any(valid_mask):
            X_valid = X[valid_mask]
            X_scaled = self.scaler.transform(X_valid)
            y_pred = self.model.predict(X_scaled)
            y_pred = np.maximum(y_pred, 0)
            result[valid_mask] = y_pred

        return result
