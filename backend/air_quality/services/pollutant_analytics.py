"""
Pollutant Analytics Service

Implements advanced analytical methods for air quality data analysis:
1. Pollutant Concentration Calculation (spatial averaging)
2. Trend Analysis using Linear Regression
3. Seasonal Decomposition Analysis
4. Hotspot Identification using Z-Score Normalization
5. Spatial Interpolation using Inverse Distance Weighting (IDW)

Reference methodology based on GEE-based Sentinel-5P analysis techniques.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum

import numpy as np
from scipy import stats
from django.contrib.gis.geos import Point, Polygon, GEOSGeometry

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConcentrationResult:
    """
    Result of pollutant concentration calculation.
    
    Equation 1: Cp = (1/N) * Σ(Ci)
    Where:
        Cp = mean pollutant concentration
        Ci = concentration value of each pixel i
        N = total number of pixels within the ROI
    """
    pollutant: str
    mean_concentration: float  # Cp
    std_deviation: float       # σ
    min_value: float
    max_value: float
    pixel_count: int           # N
    unit: str
    start_date: date
    end_date: date
    geometry_area_km2: Optional[float] = None


@dataclass
class TrendResult:
    """
    Result of linear regression trend analysis.
    
    Equation 2: y = a + bx + e
    Where:
        y = pollutant concentration
        x = time (months or years)
        a = intercept
        b = slope (rate of change)
        e = error term
    """
    pollutant: str
    slope: float               # b - rate of change
    intercept: float           # a
    r_squared: float           # coefficient of determination
    p_value: float             # statistical significance
    std_error: float           # standard error of slope
    trend_direction: str       # "increasing", "decreasing", or "stable"
    confidence_interval: Tuple[float, float]  # 95% CI for slope
    time_unit: str             # "monthly" or "yearly"
    data_points: int


@dataclass
class SeasonalDecomposition:
    """
    Result of seasonal decomposition analysis.
    
    Equation 3: Yt = Tt + St + et (Additive model)
    Where:
        Yt = observed pollutant value at time t
        Tt = trend component
        St = seasonal component
        et = residual/random noise component
    """
    pollutant: str
    observed: List[float]      # Yt - original time series
    trend: List[float]         # Tt - long-term trend
    seasonal: List[float]      # St - seasonal pattern
    residual: List[float]      # et - noise/unexplained
    period: int                # seasonality period (e.g., 12 for monthly)
    dates: List[date]
    seasonal_strength: float   # how strong is seasonality (0-1)
    trend_strength: float      # how strong is trend (0-1)


@dataclass 
class HotspotResult:
    """
    Result of hotspot identification using Z-score normalization.
    
    Equation 4: Zi = (Ci - μ) / σ
    Where:
        Ci = pollutant concentration of pixel i
        μ = mean pollutant concentration of entire region
        σ = standard deviation of pollutant concentration
        
    Pixels with Z > threshold (e.g., 2) are classified as hotspots.
    """
    pollutant: str
    hotspot_pixels: List[Dict]  # List of {lat, lon, concentration, z_score}
    total_pixels: int
    hotspot_count: int
    hotspot_percentage: float
    mean_concentration: float   # μ
    std_deviation: float        # σ
    z_threshold: float          # threshold used (default 2.0)
    max_z_score: float
    hotspot_centroid: Optional[Tuple[float, float]] = None  # (lat, lon)


@dataclass
class IDWResult:
    """
    Result of Inverse Distance Weighting interpolation.
    
    Equation 5: Ĉ(x) = Σ(wi(x) * Ci) / Σ(wi(x))
    Where:
        Ĉ(x) = estimated concentration at location x
        wi(x) = weight for sample i = 1 / d(x, xi)^p
        d(x, xi) = distance between x and sampled point xi
        p = power parameter (usually 2)
    """
    estimated_value: float      # Ĉ(x)
    location: Tuple[float, float]  # (lat, lon)
    nearby_samples: int
    power_parameter: float      # p (default 2)
    search_radius_km: float
    confidence: float           # based on sample density


# =============================================================================
# POLLUTANT ANALYTICS SERVICE
# =============================================================================

class PollutantAnalyticsService:
    """
    Service for advanced pollutant data analytics.
    
    Implements statistical methods for:
    - Temporal trend analysis
    - Seasonal pattern detection
    - Spatial hotspot identification
    - Interpolation for unsampled locations
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # =========================================================================
    # 1. POLLUTANT CONCENTRATION CALCULATION (Equation 1)
    # =========================================================================
    
    def calculate_mean_concentration(
        self,
        pixel_values: np.ndarray,
        pollutant: str,
        unit: str = "mol/m²",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ConcentrationResult:
        """
        Calculate mean pollutant concentration over a Region of Interest.
        
        Equation 1: Cp = (1/N) * Σ(Ci)
        
        Args:
            pixel_values: Array of concentration values from satellite pixels
            pollutant: Name of the pollutant (NO2, CO, O3, etc.)
            unit: Measurement unit
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            ConcentrationResult with mean, std, min, max, and pixel count
        """
        # Remove invalid values (NaN, negative)
        valid_mask = ~np.isnan(pixel_values) & (pixel_values >= 0)
        valid_values = pixel_values[valid_mask]
        
        if len(valid_values) == 0:
            raise ValueError(f"No valid pixel values for {pollutant}")
        
        # Calculate statistics (Equation 1)
        mean_conc = float(np.mean(valid_values))  # Cp = (1/N) * Σ(Ci)
        std_dev = float(np.std(valid_values))
        
        return ConcentrationResult(
            pollutant=pollutant,
            mean_concentration=mean_conc,
            std_deviation=std_dev,
            min_value=float(np.min(valid_values)),
            max_value=float(np.max(valid_values)),
            pixel_count=len(valid_values),  # N
            unit=unit,
            start_date=start_date or date.today(),
            end_date=end_date or date.today()
        )
    
    # =========================================================================
    # 2. TREND ANALYSIS USING LINEAR REGRESSION (Equation 2)
    # =========================================================================
    
    def analyze_trend(
        self,
        time_series: List[Tuple[date, float]],
        pollutant: str,
        time_unit: str = "monthly"
    ) -> TrendResult:
        """
        Perform linear regression trend analysis on pollutant time series.
        
        Equation 2: y = a + bx + e
        Where:
            y = pollutant concentration
            x = time (converted to numeric)
            a = intercept
            b = slope (rate of change)
            e = error term
        
        A positive slope (b > 0) indicates increasing trend.
        A negative slope (b < 0) indicates decreasing trend.
        
        Args:
            time_series: List of (date, concentration) tuples
            pollutant: Name of the pollutant
            time_unit: "monthly" or "yearly"
            
        Returns:
            TrendResult with slope, intercept, R², p-value, etc.
        """
        if len(time_series) < 3:
            raise ValueError("Need at least 3 data points for trend analysis")
        
        # Sort by date
        sorted_data = sorted(time_series, key=lambda x: x[0])
        
        # Convert dates to numeric (days since first observation)
        base_date = sorted_data[0][0]
        x = np.array([(d[0] - base_date).days for d in sorted_data])
        y = np.array([d[1] for d in sorted_data])
        
        # Perform linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Calculate 95% confidence interval for slope
        n = len(x)
        t_critical = stats.t.ppf(0.975, n - 2)
        ci_margin = t_critical * std_err
        confidence_interval = (slope - ci_margin, slope + ci_margin)
        
        # Determine trend direction
        if p_value < 0.05:  # Statistically significant
            if slope > 0:
                trend_direction = "increasing"
            elif slope < 0:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable (not significant)"
        
        return TrendResult(
            pollutant=pollutant,
            slope=slope,                    # b
            intercept=intercept,            # a
            r_squared=r_value ** 2,
            p_value=p_value,
            std_error=std_err,
            trend_direction=trend_direction,
            confidence_interval=confidence_interval,
            time_unit=time_unit,
            data_points=n
        )
    
    # =========================================================================
    # 3. SEASONAL DECOMPOSITION ANALYSIS (Equation 3)
    # =========================================================================
    
    def decompose_seasonal(
        self,
        time_series: List[Tuple[date, float]],
        pollutant: str,
        period: int = 12  # 12 months for annual seasonality
    ) -> SeasonalDecomposition:
        """
        Perform seasonal decomposition on pollutant time series.
        
        Equation 3: Yt = Tt + St + et (Additive model)
        Where:
            Yt = observed pollutant value at time t
            Tt = trend component (moving average)
            St = seasonal component (average deviation by season)
            et = residual (Yt - Tt - St)
        
        Args:
            time_series: List of (date, concentration) tuples
            pollutant: Name of the pollutant
            period: Seasonality period (12 for monthly data with annual cycle)
            
        Returns:
            SeasonalDecomposition with trend, seasonal, and residual components
        """
        if len(time_series) < period * 2:
            raise ValueError(f"Need at least {period * 2} data points for seasonal decomposition")
        
        # Sort by date
        sorted_data = sorted(time_series, key=lambda x: x[0])
        dates = [d[0] for d in sorted_data]
        observed = np.array([d[1] for d in sorted_data])  # Yt
        
        n = len(observed)
        
        # Step 1: Calculate trend component (Tt) using centered moving average
        trend = np.zeros(n)
        half_period = period // 2
        
        for i in range(half_period, n - half_period):
            if period % 2 == 0:
                # Even period: weighted average
                trend[i] = (0.5 * observed[i - half_period] + 
                           np.sum(observed[i - half_period + 1:i + half_period]) +
                           0.5 * observed[i + half_period]) / period
            else:
                # Odd period: simple average
                trend[i] = np.mean(observed[i - half_period:i + half_period + 1])
        
        # Extend trend to edges using linear extrapolation
        if trend[half_period] != 0:
            for i in range(half_period):
                trend[i] = trend[half_period]
            for i in range(n - half_period, n):
                trend[i] = trend[n - half_period - 1]
        
        # Step 2: Calculate detrended series
        detrended = observed - trend
        
        # Step 3: Calculate seasonal component (St)
        seasonal = np.zeros(n)
        seasonal_indices = np.zeros(period)
        
        for i in range(period):
            # Average of all values at same seasonal position
            seasonal_values = detrended[i::period]
            seasonal_indices[i] = np.nanmean(seasonal_values)
        
        # Normalize seasonal component (should sum to 0 for additive model)
        seasonal_indices -= np.mean(seasonal_indices)
        
        # Apply seasonal pattern to full series
        for i in range(n):
            seasonal[i] = seasonal_indices[i % period]
        
        # Step 4: Calculate residual (et = Yt - Tt - St)
        residual = observed - trend - seasonal
        
        # Calculate strength metrics
        var_residual = np.var(residual)
        var_detrended = np.var(detrended)
        var_deseasonalized = np.var(observed - seasonal)
        
        seasonal_strength = max(0, 1 - var_residual / var_detrended) if var_detrended > 0 else 0
        trend_strength = max(0, 1 - var_residual / var_deseasonalized) if var_deseasonalized > 0 else 0
        
        return SeasonalDecomposition(
            pollutant=pollutant,
            observed=observed.tolist(),
            trend=trend.tolist(),
            seasonal=seasonal.tolist(),
            residual=residual.tolist(),
            period=period,
            dates=dates,
            seasonal_strength=seasonal_strength,
            trend_strength=trend_strength
        )
    
    # =========================================================================
    # 4. HOTSPOT IDENTIFICATION USING Z-SCORE (Equation 4)
    # =========================================================================
    
    def identify_hotspots(
        self,
        pixel_data: List[Dict[str, float]],  # [{lat, lon, concentration}, ...]
        pollutant: str,
        z_threshold: float = 2.0
    ) -> HotspotResult:
        """
        Identify pollution hotspots using Z-score normalization.
        
        Equation 4: Zi = (Ci - μ) / σ
        Where:
            Ci = pollutant concentration of pixel i
            μ = mean pollutant concentration of entire region
            σ = standard deviation of pollutant concentration
            
        Pixels with Z > threshold (default 2.0) are classified as hotspots.
        
        Args:
            pixel_data: List of dicts with lat, lon, concentration
            pollutant: Name of the pollutant
            z_threshold: Z-score threshold for hotspot classification (default 2.0)
            
        Returns:
            HotspotResult with identified hotspots and statistics
        """
        if not pixel_data:
            raise ValueError("No pixel data provided")
        
        # Extract concentrations
        concentrations = np.array([p['concentration'] for p in pixel_data])
        
        # Calculate μ (mean) and σ (standard deviation)
        mu = np.mean(concentrations)
        sigma = np.std(concentrations)
        
        if sigma == 0:
            raise ValueError("Standard deviation is zero - all values are identical")
        
        # Calculate Z-scores for all pixels (Equation 4)
        hotspot_pixels = []
        max_z = float('-inf')
        
        for pixel in pixel_data:
            z_score = (pixel['concentration'] - mu) / sigma  # Zi = (Ci - μ) / σ
            
            if z_score > max_z:
                max_z = z_score
            
            if z_score > z_threshold:
                hotspot_pixels.append({
                    'lat': pixel['lat'],
                    'lon': pixel['lon'],
                    'concentration': pixel['concentration'],
                    'z_score': z_score
                })
        
        # Sort hotspots by Z-score (highest first)
        hotspot_pixels.sort(key=lambda x: x['z_score'], reverse=True)
        
        # Calculate hotspot centroid
        centroid = None
        if hotspot_pixels:
            centroid = (
                np.mean([p['lat'] for p in hotspot_pixels]),
                np.mean([p['lon'] for p in hotspot_pixels])
            )
        
        return HotspotResult(
            pollutant=pollutant,
            hotspot_pixels=hotspot_pixels,
            total_pixels=len(pixel_data),
            hotspot_count=len(hotspot_pixels),
            hotspot_percentage=100 * len(hotspot_pixels) / len(pixel_data),
            mean_concentration=mu,
            std_deviation=sigma,
            z_threshold=z_threshold,
            max_z_score=max_z,
            hotspot_centroid=centroid
        )
    
    # =========================================================================
    # 5. SPATIAL INTERPOLATION USING IDW (Equation 5)
    # =========================================================================
    
    def interpolate_idw(
        self,
        sample_points: List[Dict[str, float]],  # [{lat, lon, concentration}, ...]
        target_location: Tuple[float, float],   # (lat, lon) to estimate
        power: float = 2.0,
        search_radius_km: float = 50.0,
        min_samples: int = 3
    ) -> IDWResult:
        """
        Estimate pollutant concentration at unsampled location using IDW.
        
        Equation 5: Ĉ(x) = Σ(wi(x) * Ci) / Σ(wi(x))
        Where:
            Ĉ(x) = estimated concentration at location x
            wi(x) = weight for sample i = 1 / d(x, xi)^p
            d(x, xi) = distance between x and sampled point xi
            p = power parameter (default 2)
        
        Args:
            sample_points: List of known sample locations with concentrations
            target_location: (lat, lon) tuple for location to estimate
            power: Power parameter p (default 2)
            search_radius_km: Maximum distance to consider samples
            min_samples: Minimum samples required for estimation
            
        Returns:
            IDWResult with estimated value and metadata
        """
        target_lat, target_lon = target_location
        
        # Calculate distances and weights
        weights = []
        values = []
        
        for sample in sample_points:
            # Calculate distance using Haversine formula
            distance_km = self._haversine_distance(
                target_lat, target_lon,
                sample['lat'], sample['lon']
            )
            
            # Only include samples within search radius
            if distance_km <= search_radius_km:
                if distance_km < 0.001:  # Very close - avoid division by zero
                    distance_km = 0.001
                
                # Calculate weight: wi(x) = 1 / d(x, xi)^p
                weight = 1.0 / (distance_km ** power)
                weights.append(weight)
                values.append(sample['concentration'])
        
        if len(weights) < min_samples:
            raise ValueError(
                f"Insufficient samples within {search_radius_km}km. "
                f"Found {len(weights)}, need {min_samples}"
            )
        
        weights = np.array(weights)
        values = np.array(values)
        
        # Apply IDW formula: Ĉ(x) = Σ(wi * Ci) / Σ(wi)
        estimated_value = np.sum(weights * values) / np.sum(weights)
        
        # Calculate confidence based on sample density and distance
        avg_distance = search_radius_km / len(weights) if weights.size > 0 else search_radius_km
        confidence = min(1.0, len(weights) / 10) * (1 - avg_distance / search_radius_km)
        
        return IDWResult(
            estimated_value=estimated_value,
            location=target_location,
            nearby_samples=len(weights),
            power_parameter=power,
            search_radius_km=search_radius_km,
            confidence=max(0, confidence)
        )
    
    def interpolate_grid(
        self,
        sample_points: List[Dict[str, float]],
        bbox: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        resolution: float = 0.01,  # degrees
        power: float = 2.0,
        search_radius_km: float = 50.0
    ) -> np.ndarray:
        """
        Create interpolated grid of pollutant concentrations using IDW.
        
        Args:
            sample_points: List of known samples with lat, lon, concentration
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            resolution: Grid resolution in degrees
            power: IDW power parameter
            search_radius_km: Maximum search radius
            
        Returns:
            2D numpy array of interpolated values
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        
        # Create grid
        lons = np.arange(min_lon, max_lon, resolution)
        lats = np.arange(min_lat, max_lat, resolution)
        
        grid = np.zeros((len(lats), len(lons)))
        
        for i, lat in enumerate(lats):
            for j, lon in enumerate(lons):
                try:
                    result = self.interpolate_idw(
                        sample_points=sample_points,
                        target_location=(lat, lon),
                        power=power,
                        search_radius_km=search_radius_km,
                        min_samples=1
                    )
                    grid[i, j] = result.estimated_value
                except ValueError:
                    grid[i, j] = np.nan
        
        return grid
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth.
        
        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)
            
        Returns:
            Distance in kilometers
        """
        R = 6371  # Earth's radius in km
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = (np.sin(delta_lat / 2) ** 2 + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2)
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_analytics_service() -> PollutantAnalyticsService:
    """Get singleton instance of PollutantAnalyticsService."""
    return PollutantAnalyticsService()


def calculate_aqi_from_concentrations(concentrations: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate AQI from multiple pollutant concentrations.
    
    The overall AQI is determined by the highest sub-index value
    among all measured pollutants.
    
    Args:
        concentrations: Dict mapping pollutant name to concentration value
                       e.g., {"PM25": 35.5, "NO2": 100, "CO": 2.0}
                       
    Returns:
        Dict with overall_aqi, dominant_pollutant, and breakdown
    """
    from air_quality.constants import calculate_aqi, Pollutant, AQICategory
    
    aqi_values = {}
    
    for pollutant_name, concentration in concentrations.items():
        try:
            pollutant = Pollutant.from_string(pollutant_name)
            if pollutant:
                aqi = calculate_aqi(pollutant, concentration)
                aqi_values[pollutant_name] = {
                    'concentration': concentration,
                    'aqi': aqi,
                    'category': AQICategory.from_aqi(aqi).value
                }
        except Exception as e:
            logger.warning(f"Could not calculate AQI for {pollutant_name}: {e}")
    
    if not aqi_values:
        return {
            'overall_aqi': None,
            'dominant_pollutant': None,
            'category': None,
            'breakdown': {}
        }
    
    # Find maximum AQI (dominant pollutant)
    dominant = max(aqi_values.items(), key=lambda x: x[1]['aqi'])
    
    return {
        'overall_aqi': dominant[1]['aqi'],
        'dominant_pollutant': dominant[0],
        'category': dominant[1]['category'],
        'breakdown': aqi_values
    }
