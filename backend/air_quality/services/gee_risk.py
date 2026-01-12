"""
Dynamic Pixel-Wise Air Quality Risk Service

HYBRID DATA FUSION:
- Local PostGIS data: OpenAQ PM2.5 readings (passed as GeoJSON)
- Cloud GEE data: Sentinel-5P NO2 + WorldPop Population

Performs bias correction and calculates population exposure risk.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any, List
import ee

from .gee_auth import initialize_gee

logger = logging.getLogger(__name__)


class RiskCalculationError(Exception):
    """Raised when risk calculation fails."""
    pass


class DynamicRiskService:
    """
    Service for calculating dynamic pixel-wise air quality risk.
    
    HYBRID APPROACH:
    - Accepts GeoJSON of local OpenAQ PM2.5 readings
    - Fetches Sentinel-5P NO2 from GEE (latest available)
    - Fetches WorldPop population from GEE
    - Performs data fusion and returns visualization tiles
    
    Returns:
    - GEE tile URL for visualization
    - Legend configuration with min/max values
    """
    
    # Color palette: Green -> Yellow -> Red -> Purple
    RISK_PALETTE = [
        '#00FF00',  # Green (low risk)
        '#7FFF00',  # Chartreuse
        '#FFFF00',  # Yellow (moderate risk)
        '#FFA500',  # Orange
        '#FF0000',  # Red (high risk)
        '#8B0000',  # Dark Red
        '#800080',  # Purple (extreme risk)
        '#4B0082',  # Indigo
    ]
    
    # Pakistan bounding box
    PAKISTAN_BBOX = {
        'min_lon': 60.87,
        'min_lat': 23.69,
        'max_lon': 77.84,
        'max_lat': 37.08,
    }
    
    def __init__(self):
        """Initialize the risk service and authenticate with GEE."""
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize Google Earth Engine."""
        if self._initialized:
            return True
            
        try:
            initialize_gee()
            self._initialized = True
            logger.info("DynamicRiskService initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize GEE: {e}")
            raise RiskCalculationError(f"GEE initialization failed: {e}")
    
    def get_latest_sentinel5p_no2(
        self,
        days_back: int = 30
    ) -> Tuple[ee.Image, str]:
        """
        Fetch the latest available Sentinel-5P NO2 image.
        
        Args:
            days_back: How many days to look back for data (default: 30)
            
        Returns:
            Tuple of (ee.Image, date_string)
            
        Raises:
            RiskCalculationError: If no data is available
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Define date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Pakistan region
            region = ee.Geometry.Rectangle([
                self.PAKISTAN_BBOX['min_lon'],
                self.PAKISTAN_BBOX['min_lat'],
                self.PAKISTAN_BBOX['max_lon'],
                self.PAKISTAN_BBOX['max_lat'],
            ])
            
            # Sentinel-5P NO2 collection
            collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2') \
                .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                .filterBounds(region) \
                .select('NO2_column_number_density')
            
            # Get the most recent image
            image_list = collection.sort('system:time_start', False).limit(1)
            
            # Check if we have data
            size = image_list.size().getInfo()
            if size == 0:
                raise RiskCalculationError(
                    f"No Sentinel-5P NO2 data available in the last {days_back} days"
                )
            
            # Get the image and its date
            latest_image = ee.Image(image_list.first())
            timestamp = latest_image.get('system:time_start').getInfo()
            image_date = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
            
            logger.info(f"Retrieved Sentinel-5P NO2 image from {image_date}")
            
            return latest_image, image_date
            
        except Exception as e:
            logger.error(f"Error fetching Sentinel-5P data: {e}")
            raise RiskCalculationError(f"Failed to fetch Sentinel-5P data: {e}")
    
    def geojson_to_ee_featurecollection(
        self,
        geojson_dict: Dict[str, Any],
        property_name: str = 'pm25'
    ) -> ee.FeatureCollection:
        """
        Convert GeoJSON dictionary (from local PostGIS) to ee.FeatureCollection.
        
        Args:
            geojson_dict: GeoJSON FeatureCollection dict from Django serializer
            property_name: Property to extract from features (default: 'pm25')
            
        Returns:
            ee.FeatureCollection ready for GEE processing
            
        Raises:
            RiskCalculationError: If GeoJSON is invalid or empty
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # Validate GeoJSON structure
            if geojson_dict.get('type') != 'FeatureCollection':
                raise ValueError("GeoJSON must be a FeatureCollection")
            
            features = geojson_dict.get('features', [])
            if not features:
                raise ValueError("GeoJSON FeatureCollection is empty")
            
            # Convert to EE features
            ee_features = []
            for feature in features:
                # Extract geometry
                geom_type = feature['geometry']['type']
                coords = feature['geometry']['coordinates']
                
                if geom_type == 'Point':
                    ee_geom = ee.Geometry.Point(coords)
                else:
                    raise ValueError(f"Unsupported geometry type: {geom_type}")
                
                # Extract properties
                props = feature.get('properties', {})
                
                # Ensure required property exists
                if property_name not in props:
                    logger.warning(
                        f"Feature missing '{property_name}' property, skipping"
                    )
                    continue
                
                # Create EE feature
                ee_feature = ee.Feature(ee_geom, {
                    property_name: float(props[property_name]),
                    # Include other useful properties
                    'station_id': props.get('station_id'),
                    'timestamp': props.get('timestamp'),
                })
                ee_features.append(ee_feature)
            
            if not ee_features:
                raise ValueError(
                    f"No valid features with '{property_name}' property found"
                )
            
            collection = ee.FeatureCollection(ee_features)
            logger.info(
                f"Converted {len(ee_features)} local OpenAQ points to "
                f"ee.FeatureCollection"
            )
            
            return collection
            
        except Exception as e:
            logger.error(f"Error converting GeoJSON to EE: {e}")
            raise RiskCalculationError(f"Failed to convert GeoJSON: {e}")
    
    def get_worldpop_data(self, year: int = 2020) -> ee.Image:
        """
        Fetch WorldPop Global Project Population Data.
        
        Args:
            year: Year for population data (default: 2020)
            
        Returns:
            ee.Image with population counts per pixel
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # WorldPop population count
            worldpop = ee.ImageCollection('WorldPop/GP/100m/pop') \
                .filter(ee.Filter.eq('country', 'PAK')) \
                .filter(ee.Filter.eq('year', year)) \
                .first() \
                .select('population')
            
            logger.info(f"Retrieved WorldPop data for {year}")
            
            return worldpop
            
        except Exception as e:
            logger.error(f"Error fetching WorldPop data: {e}")
            raise RiskCalculationError(f"Failed to fetch WorldPop data: {e}")
    
    def calculate_risk_index(
        self,
        openaq_geojson: Dict[str, Any],
        days_back: int = 30,
        pop_year: int = 2020
    ) -> Dict[str, Any]:
        """
        Calculate pixel-wise population exposure risk.
        
        HYBRID DATA FUSION:
        1. Convert local OpenAQ GeoJSON to ee.FeatureCollection
        2. Fetch latest Sentinel-5P NO2 from GEE
        3. Interpolate OpenAQ PM2.5 to create bias correction surface
        4. Fuse satellite + ground data
        5. Multiply by normalized WorldPop to get risk index
        
        Args:
            openaq_geojson: GeoJSON dict with local OpenAQ PM2.5 readings
                           Must have 'pm25' property in each feature
            days_back: Days to look back for Sentinel-5P data (default: 30)
            pop_year: Year for WorldPop data (default: 2020)
            
        Returns:
            Dictionary with:
            - tile_url: GEE tile URL template
            - map_id: GEE map ID
            - token: GEE token
            - legend: Legend configuration with min/max and colors
            - metadata: Additional metadata (date, sources, etc.)
            
        Raises:
            RiskCalculationError: If calculation fails
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # 1. Convert local OpenAQ GeoJSON to ee.FeatureCollection
            openaq_fc = self.geojson_to_ee_featurecollection(
                openaq_geojson,
                property_name='pm25'
            )
            
            # 2. Fetch Sentinel-5P NO2 (latest from GEE Cloud)
            no2_image, no2_date = self.get_latest_sentinel5p_no2(days_back)
            
            # 3. Fetch WorldPop from GEE Cloud
            population = self.get_worldpop_data(pop_year)
            
            # 4. Create PM2.5 bias correction surface from local OpenAQ points
            pm25_surface = self._interpolate_point_data(
                openaq_fc,
                property_name='pm25',
                scale=5000  # 5km interpolation scale
            )
            
            # 5. Fuse satellite NO2 with ground PM2.5
            # Convert NO2 to approximate PM2.5 equivalent using empirical factor
            no2_to_pm25_factor = 1e6 * 46.0055 / 6.022e23 * 1e4  # mol/m² to µg/m³
            
            satellite_pm25 = no2_image.multiply(no2_to_pm25_factor)
            
            # Weighted fusion: 70% ground data, 30% satellite
            # (Ground data is more accurate but sparse)
            fused_pm25 = pm25_surface.multiply(0.7).add(satellite_pm25.multiply(0.3))
            
            # 6. Normalize population (0-1 scale)
            region = ee.Geometry.Rectangle([
                self.PAKISTAN_BBOX['min_lon'],
                self.PAKISTAN_BBOX['min_lat'],
                self.PAKISTAN_BBOX['max_lon'],
                self.PAKISTAN_BBOX['max_lat'],
            ])
            
            pop_stats = population.reduceRegion(
                reducer=ee.Reducer.minMax(),
                geometry=region,
                scale=1000,
                maxPixels=1e9
            )
            
            pop_min = ee.Number(pop_stats.get('population_min'))
            pop_max = ee.Number(pop_stats.get('population_max'))
            
            normalized_population = population.subtract(pop_min) \
                .divide(pop_max.subtract(pop_min))
            
            # 7. Calculate risk index: PM2.5 × normalized population
            risk_index = fused_pm25.multiply(normalized_population)
            
            # 8. Get statistics for legend
            risk_stats = risk_index.reduceRegion(
                reducer=ee.Reducer.percentile([0, 25, 50, 75, 95, 100]),
                geometry=region,
                scale=1000,
                maxPixels=1e9,
                bestEffort=True
            )
            
            # Use 0th and 95th percentile for better visualization
            risk_min = risk_stats.get('constant_p0').getInfo() or 0
            risk_max = risk_stats.get('constant_p95').getInfo() or 100
            
            # Ensure we have valid values
            if risk_max <= risk_min:
                risk_max = risk_min + 50
            
            # 9. Apply visualization
            vis_params = {
                'min': risk_min,
                'max': risk_max,
                'palette': self.RISK_PALETTE,
            }
            
            # Get map ID for tiles
            map_id_dict = risk_index.getMapId(vis_params)
            
            # 10. Build legend
            legend = self._build_legend(risk_min, risk_max)
            
            # 11. Return complete result
            result = {
                'tile_url': map_id_dict['tile_fetcher'].url_format,
                'map_id': map_id_dict['mapid'],
                'token': map_id_dict['token'],
                'legend': legend,
                'metadata': {
                    'sentinel5p_date': no2_date,
                    'openaq_points': len(openaq_geojson.get('features', [])),
                    'worldpop_year': pop_year,
                    'risk_min': float(risk_min),
                    'risk_max': float(risk_max),
                    'bbox': self.PAKISTAN_BBOX,
                    'fusion_method': 'weighted_average',
                    'fusion_weights': {'ground': 0.7, 'satellite': 0.3},
                    'generated_at': datetime.now().isoformat(),
                }
            }
            
            logger.info(
                f"Risk calculation successful. "
                f"Range: {risk_min:.2f} - {risk_max:.2f}, "
                f"OpenAQ points: {len(openaq_geojson.get('features', []))}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Risk calculation failed: {e}", exc_info=True)
            raise RiskCalculationError(f"Risk calculation failed: {e}")
    
    def _interpolate_point_data(
        self,
        point_fc: ee.FeatureCollection,
        property_name: str,
        scale: float = 5000
    ) -> ee.Image:
        """
        Interpolate point data using Inverse Distance Weighting (IDW).
        
        Args:
            point_fc: FeatureCollection with point features
            property_name: Property to interpolate
            scale: Interpolation scale in meters
            
        Returns:
            ee.Image with interpolated values
        """
        # Get region bounds
        region = ee.Geometry.Rectangle([
            self.PAKISTAN_BBOX['min_lon'],
            self.PAKISTAN_BBOX['min_lat'],
            self.PAKISTAN_BBOX['max_lon'],
            self.PAKISTAN_BBOX['max_lat'],
        ])
        
        # Create a grid of coordinates
        lon_lat = ee.Image.pixelLonLat()
        
        # For each point, calculate distance-weighted contribution
        def process_point(feature):
            point = feature.geometry()
            value = ee.Number(feature.get(property_name))
            
            # Calculate distance from each pixel to this point
            distance = lon_lat.subtract(ee.Image.constant([
                point.coordinates().get(0),
                point.coordinates().get(1)
            ])).pow(2).reduce(ee.Reducer.sum()).sqrt()
            
            # IDW weight: 1 / (distance + buffer)^2
            # Add buffer to avoid division by zero
            weight = distance.add(0.001).pow(-2)
            
            # Weighted value
            weighted_value = weight.multiply(value)
            
            return ee.Image.cat([weighted_value, weight])
        
        # Process all points
        weighted_images = point_fc.map(process_point)
        
        # Sum all weighted values and weights
        summed = weighted_images.reduce(ee.Reducer.sum())
        
        # Final interpolated surface: sum(weighted_values) / sum(weights)
        interpolated = summed.select(0).divide(summed.select(1))
        
        return interpolated.clip(region)
    
    def _build_legend(
        self,
        min_value: float,
        max_value: float
    ) -> Dict[str, Any]:
        """
        Build legend configuration for the risk index.
        
        Args:
            min_value: Minimum risk value
            max_value: Maximum risk value
            
        Returns:
            Legend dictionary with stops and labels
        """
        # Create 8 stops matching the palette
        num_stops = len(self.RISK_PALETTE)
        value_range = max_value - min_value
        step = value_range / (num_stops - 1)
        
        stops = []
        for i, color in enumerate(self.RISK_PALETTE):
            value = min_value + (step * i)
            stops.append({
                'value': round(value, 2),
                'color': color,
                'label': self._get_risk_label(i, num_stops)
            })
        
        return {
            'title': 'Population Exposure Risk',
            'subtitle': 'NO2 × PM2.5 × Population Density',
            'unit': 'Risk Index',
            'stops': stops,
            'min': round(min_value, 2),
            'max': round(max_value, 2),
        }
    
    def _get_risk_label(self, index: int, total: int) -> str:
        """Get human-readable label for risk level."""
        labels = [
            'Very Low',
            'Low',
            'Moderate',
            'Elevated',
            'High',
            'Very High',
            'Severe',
            'Extreme'
        ]
        return labels[index] if index < len(labels) else f'Level {index + 1}'


# Singleton instance
_risk_service: Optional[DynamicRiskService] = None


def get_risk_service() -> DynamicRiskService:
    """Get or create the singleton risk service instance."""
    global _risk_service
    
    if _risk_service is None:
        _risk_service = DynamicRiskService()
        _risk_service.initialize()
    
    return _risk_service
