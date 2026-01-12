"""
Google Earth Engine Integration Service
========================================

Handles all GEE operations for risk map generation, including:
- GeoJSON to Earth Engine FeatureCollection conversion
- Sentinel-5P NO2 data retrieval
- WorldPop population data retrieval
- IDW interpolation of ground station data
- Data fusion and risk index calculation
- Tile URL generation for MapLibre rendering

Author: Principal Software Architect
Date: December 11, 2025
"""

import ee
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from apps.core.base_service import (
    BaseService,
    ServiceResult,
    GeoSpatialServiceMixin
)


logger = logging.getLogger(__name__)


class RiskMapService(BaseService, GeoSpatialServiceMixin):
    """
    Service for generating dynamic air quality risk maps.
    
    Fuses local ground station data (OpenAQ) with cloud satellite
    imagery (Sentinel-5P) and population data (WorldPop) to create
    pixel-wise risk assessments.
    
    Usage:
        service = RiskMapService()
        result = service.generate_risk_map(openaq_geojson)
        
        if result.success:
            tile_url = result.data['tile_url']
            legend = result.data['legend']
    """
    
    # Configuration constants
    DEFAULT_LOOKBACK_DAYS: int = 30
    DEFAULT_POP_YEAR: int = 2020
    IDW_POWER: float = 2.0
    IDW_MAX_DISTANCE: float = 50000  # meters
    
    # Data fusion weights
    GROUND_WEIGHT: float = 0.7
    SATELLITE_WEIGHT: float = 0.3
    
    # Color palette for risk visualization
    RISK_PALETTE: List[str] = [
        '#00FF00',  # 0-50: Good (Green)
        '#FFFF00',  # 50-100: Moderate (Yellow)
        '#FFA500',  # 100-150: Unhealthy for Sensitive (Orange)
        '#FF0000',  # 150-200: Unhealthy (Red)
        '#8B008B',  # 200-300: Very Unhealthy (Purple)
        '#800000',  # 300+: Hazardous (Maroon)
    ]
    
    def _initialize(self) -> None:
        """Initialize Earth Engine authentication."""
        try:
            ee.Initialize()
            self.logger.info("Earth Engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Earth Engine: {e}")
            raise
    
    def generate_risk_map(
        self,
        openaq_geojson: Dict[str, Any],
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        pop_year: int = DEFAULT_POP_YEAR,
        region_bounds: Optional[List[float]] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Generate a risk map from local and cloud data sources.
        
        Args:
            openaq_geojson: GeoJSON FeatureCollection of OpenAQ stations
            lookback_days: Days to look back for Sentinel-5P data
            pop_year: WorldPop data year
            region_bounds: Optional [west, south, east, north] bounds
            
        Returns:
            ServiceResult containing:
                - tile_url: MapLibre-compatible tile URL
                - legend: Legend configuration
                - metadata: Processing information
        """
        try:
            self._log_operation(
                "generate_risk_map",
                stations_count=len(openaq_geojson.get('features', []))
            )
            
            # Validate input
            if not self.validate_geojson(openaq_geojson):
                return ServiceResult.error_result("Invalid GeoJSON structure")
            
            # Step 1: Convert GeoJSON to Earth Engine FeatureCollection
            ground_fc = self._geojson_to_ee_fc(openaq_geojson)
            
            # Step 2: Get latest Sentinel-5P NO2 data
            sentinel_result = self._get_latest_sentinel5p_no2(lookback_days)
            if not sentinel_result.success:
                return sentinel_result
            
            sentinel_image = sentinel_result.data['image']
            sentinel_date = sentinel_result.data['date']
            
            # Step 3: Get WorldPop population data
            population_image = self._get_worldpop_data(pop_year)
            
            # Step 4: Interpolate ground station data using IDW
            ground_pm25_image = self._interpolate_ground_data(
                ground_fc,
                property_name='pm25_value'
            )
            
            # Step 5: Fuse ground and satellite data
            fused_pm25 = self._fuse_ground_satellite(
                ground_pm25_image,
                sentinel_image
            )
            
            # Step 6: Calculate risk index
            risk_index = self._calculate_risk_index(
                fused_pm25,
                population_image
            )
            
            # Step 7: Generate tile URL
            if region_bounds:
                geometry = ee.Geometry.Rectangle(region_bounds)
            else:
                geometry = ground_fc.geometry().bounds()
            
            tile_url = self._generate_tile_url(risk_index, geometry)
            
            # Step 8: Prepare result
            result_data = {
                'tile_url': tile_url,
                'legend': self._generate_legend(),
                'metadata': {
                    'sentinel_date': sentinel_date.isoformat(),
                    'population_year': pop_year,
                    'ground_stations': ground_fc.size().getInfo(),
                    'fusion_weights': {
                        'ground': self.GROUND_WEIGHT,
                        'satellite': self.SATELLITE_WEIGHT
                    },
                    'generated_at': datetime.utcnow().isoformat()
                }
            }
            
            self._log_operation(
                "generate_risk_map_success",
                level='info',
                sentinel_date=sentinel_date.isoformat()
            )
            
            return ServiceResult.success_result(result_data)
            
        except Exception as e:
            return self._handle_error("generate_risk_map", e)
    
    def _geojson_to_ee_fc(
        self,
        geojson: Dict[str, Any]
    ) -> ee.FeatureCollection:
        """
        Convert GeoJSON FeatureCollection to Earth Engine FeatureCollection.
        
        Args:
            geojson: GeoJSON dictionary
            
        Returns:
            ee.FeatureCollection
        """
        features = []
        
        for feature_dict in geojson.get('features', []):
            geometry = feature_dict.get('geometry')
            properties = feature_dict.get('properties', {})
            
            if geometry and geometry.get('type') == 'Point':
                coords = geometry['coordinates']
                point = ee.Geometry.Point(coords)
                ee_feature = ee.Feature(point, properties)
                features.append(ee_feature)
        
        return ee.FeatureCollection(features)
    
    def _get_latest_sentinel5p_no2(
        self,
        lookback_days: int
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Retrieve the latest Sentinel-5P NO2 data.
        
        Args:
            lookback_days: Number of days to search back
            
        Returns:
            ServiceResult containing image and date
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=lookback_days)
            
            collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2') \
                .filterDate(start_date.strftime('%Y-%m-%d'),
                           end_date.strftime('%Y-%m-%d')) \
                .select('tropospheric_NO2_column_number_density')
            
            # Get the most recent image
            latest_image = collection.sort('system:time_start', False).first()
            
            # Check if any images were found
            if latest_image is None:
                return ServiceResult.error_result(
                    f"No Sentinel-5P data found in last {lookback_days} days"
                )
            
            # Get image date
            time_start = latest_image.get('system:time_start')
            image_date = datetime.utcfromtimestamp(
                ee.Number(time_start).divide(1000).getInfo()
            )
            
            return ServiceResult.success_result({
                'image': latest_image,
                'date': image_date
            })
            
        except Exception as e:
            return self._handle_error("get_latest_sentinel5p_no2", e)
    
    def _get_worldpop_data(self, year: int) -> ee.Image:
        """
        Retrieve WorldPop population count data.
        
        Args:
            year: Data year
            
        Returns:
            ee.Image of population density
        """
        return ee.ImageCollection('WorldPop/GP/100m/pop') \
            .filterDate(f'{year}-01-01', f'{year}-12-31') \
            .mosaic()
    
    def _interpolate_ground_data(
        self,
        feature_collection: ee.FeatureCollection,
        property_name: str
    ) -> ee.Image:
        """
        Interpolate point data to raster using Inverse Distance Weighting.
        
        Args:
            feature_collection: Point features with values
            property_name: Property to interpolate
            
        Returns:
            Interpolated ee.Image
        """
        def idw_feature(feature):
            """Create IDW kernel for each feature."""
            point = feature.geometry()
            value = ee.Number(feature.get(property_name))
            
            # Create distance image from this point
            distance = ee.Image().distance(point)
            
            # Calculate weight: 1 / (distance^power)
            weight = distance.pow(self.IDW_POWER).add(1).pow(-1)
            
            # Apply maximum distance threshold
            weight = weight.updateMask(distance.lt(self.IDW_MAX_DISTANCE))
            
            # Weighted value
            weighted_value = weight.multiply(value)
            
            return ee.Image.cat(weighted_value, weight)
        
        # Apply IDW to all features
        idw_images = feature_collection.map(idw_feature)
        
        # Sum all weighted values and weights
        sum_image = idw_images.sum()
        
        # Divide weighted sum by weight sum
        interpolated = sum_image.select(0).divide(sum_image.select(1))
        
        return interpolated.rename(property_name)
    
    def _fuse_ground_satellite(
        self,
        ground_image: ee.Image,
        satellite_image: ee.Image
    ) -> ee.Image:
        """
        Fuse ground station and satellite data.
        
        Uses weighted average: 70% ground + 30% satellite
        
        Args:
            ground_image: Interpolated ground measurements
            satellite_image: Satellite observations
            
        Returns:
            Fused ee.Image
        """
        # Normalize satellite NO2 to approximate PM2.5 scale
        # This is a simplified conversion - adjust based on domain knowledge
        satellite_pm25_approx = satellite_image.multiply(1e6)
        
        # Weighted fusion
        fused = ground_image.multiply(self.GROUND_WEIGHT) \
            .add(satellite_pm25_approx.multiply(self.SATELLITE_WEIGHT))
        
        return fused.rename('fused_pm25')
    
    def _calculate_risk_index(
        self,
        pm25_image: ee.Image,
        population_image: ee.Image
    ) -> ee.Image:
        """
        Calculate risk index from PM2.5 and population.
        
        Risk = PM2.5 * log(population + 1)
        
        Args:
            pm25_image: Fused PM2.5 concentrations
            population_image: Population density
            
        Returns:
            Risk index ee.Image
        """
        # Logarithmic population weighting
        pop_factor = population_image.add(1).log()
        
        # Risk index
        risk = pm25_image.multiply(pop_factor)
        
        return risk.rename('risk_index')
    
    def _generate_tile_url(
        self,
        image: ee.Image,
        geometry: ee.Geometry
    ) -> str:
        """
        Generate MapLibre-compatible tile URL.
        
        Args:
            image: Earth Engine image
            geometry: Region of interest
            
        Returns:
            Tile URL string
        """
        vis_params = {
            'min': 0,
            'max': 300,
            'palette': self.RISK_PALETTE
        }
        
        map_id = image.getMapId(vis_params)
        return map_id['tile_fetcher'].url_format
    
    def _generate_legend(self) -> Dict[str, Any]:
        """
        Generate legend configuration for frontend.
        
        Returns:
            Legend configuration dictionary
        """
        return {
            'title': 'Air Quality Risk Index',
            'type': 'gradient',
            'stops': [
                {'value': 0, 'color': self.RISK_PALETTE[0], 'label': 'Good'},
                {'value': 50, 'color': self.RISK_PALETTE[1], 'label': 'Moderate'},
                {'value': 100, 'color': self.RISK_PALETTE[2], 'label': 'Unhealthy for Sensitive'},
                {'value': 150, 'color': self.RISK_PALETTE[3], 'label': 'Unhealthy'},
                {'value': 200, 'color': self.RISK_PALETTE[4], 'label': 'Very Unhealthy'},
                {'value': 300, 'color': self.RISK_PALETTE[5], 'label': 'Hazardous'},
            ],
            'unit': 'Risk Index'
        }
