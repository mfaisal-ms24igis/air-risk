"""
Population data service.

Provides access to WorldPop population grid data with spatial queries,
resampling, and zonal statistics capabilities.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List
from functools import lru_cache

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.mask import mask as raster_mask
from rasterio.transform import from_bounds
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon

logger = logging.getLogger(__name__)


@dataclass
class PopulationStats:
    """Population statistics for a region."""
    total_population: float
    population_density: float  # people per km²
    area_km2: float
    pixel_count: int
    min_population: float
    max_population: float
    mean_population: float


@dataclass
class PopulationGrid:
    """Population grid data with metadata."""
    data: np.ndarray
    transform: rasterio.transform.Affine
    crs: str
    bounds: Tuple[float, float, float, float]  # (minx, miny, maxx, maxy)
    resolution: float  # in meters
    nodata: float


class PopulationService:
    """
    Service for population data operations.
    
    Uses WorldPop 1km resolution population grid for Pakistan.
    Supports:
    - Extracting population for geometry
    - Resampling to match other grids
    - Zonal statistics for districts/provinces
    """
    
    def __init__(self, population_path: Optional[str] = None):
        """
        Initialize population service.
        
        Args:
            population_path: Path to population raster. Defaults to settings.
        """
        if population_path:
            self.population_path = Path(population_path)
        else:
            self.population_path = Path(settings.BASE_DIR) / "data" / "worldpop" / "pak_pop_2025_CN_1km_R2025A_UA_v1.tif"
        
        self._dataset = None
        self._metadata = None
        
    def _open_dataset(self) -> rasterio.DatasetReader:
        """Open population raster dataset."""
        if self._dataset is None or self._dataset.closed:
            if not self.population_path.exists():
                raise FileNotFoundError(
                    f"Population raster not found: {self.population_path}"
                )
            self._dataset = rasterio.open(self.population_path)
        return self._dataset
    
    def close(self):
        """Close dataset connection."""
        if self._dataset is not None and not self._dataset.closed:
            self._dataset.close()
            self._dataset = None
    
    @property
    def metadata(self) -> dict:
        """Get raster metadata."""
        if self._metadata is None:
            ds = self._open_dataset()
            self._metadata = {
                "crs": str(ds.crs),
                "bounds": ds.bounds,
                "width": ds.width,
                "height": ds.height,
                "transform": ds.transform,
                "resolution": ds.res[0],  # Assuming square pixels
                "nodata": ds.nodata or -99999,
            }
        return self._metadata
    
    def get_population_for_geometry(
        self,
        geometry: GEOSGeometry,
        crop: bool = True
    ) -> PopulationGrid:
        """
        Extract population grid for a geometry.
        
        Args:
            geometry: Django GEOSGeometry (Polygon or MultiPolygon)
            crop: If True, crop to geometry extent
            
        Returns:
            PopulationGrid with data and metadata
        """
        ds = self._open_dataset()
        
        # Convert to GeoJSON-like dict for rasterio
        if isinstance(geometry, (Polygon, MultiPolygon)):
            geom_json = self._geos_to_geojson(geometry)
        else:
            raise ValueError(f"Unsupported geometry type: {type(geometry)}")
        
        try:
            out_image, out_transform = raster_mask(
                ds,
                [geom_json],
                crop=crop,
                filled=True,
                nodata=ds.nodata or -99999
            )
            
            # Get first band
            data = out_image[0]
            
            # Calculate bounds from transform and shape
            height, width = data.shape
            bounds = rasterio.transform.array_bounds(height, width, out_transform)
            
            return PopulationGrid(
                data=data,
                transform=out_transform,
                crs=str(ds.crs),
                bounds=bounds,
                resolution=ds.res[0],
                nodata=ds.nodata or -99999
            )
            
        except Exception as e:
            logger.error(f"Error extracting population for geometry: {e}")
            raise
    
    def get_population_for_bbox(
        self,
        minx: float,
        miny: float,
        maxx: float,
        maxy: float
    ) -> PopulationGrid:
        """
        Extract population grid for a bounding box.
        
        Args:
            minx, miny, maxx, maxy: Bounding box coordinates (WGS84)
            
        Returns:
            PopulationGrid with data and metadata
        """
        ds = self._open_dataset()
        
        # Create window from bounds
        window = rasterio.windows.from_bounds(
            minx, miny, maxx, maxy,
            transform=ds.transform
        )
        
        # Round to integer pixels
        window = window.round_offsets().round_lengths()
        
        try:
            data = ds.read(1, window=window)
            transform = rasterio.windows.transform(window, ds.transform)
            
            return PopulationGrid(
                data=data,
                transform=transform,
                crs=str(ds.crs),
                bounds=(minx, miny, maxx, maxy),
                resolution=ds.res[0],
                nodata=ds.nodata or -99999
            )
            
        except Exception as e:
            logger.error(f"Error extracting population for bbox: {e}")
            raise
    
    def get_population_at_point(
        self,
        longitude: float,
        latitude: float
    ) -> float:
        """
        Get population at a specific point.
        
        Args:
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            
        Returns:
            Population value at point
        """
        ds = self._open_dataset()
        
        try:
            # Sample at point
            values = list(ds.sample([(longitude, latitude)]))[0]
            value = values[0]
            
            # Check for nodata
            if value == ds.nodata or value < 0:
                return 0.0
            
            return float(value)
            
        except Exception as e:
            logger.warning(f"Error getting population at ({longitude}, {latitude}): {e}")
            return 0.0
    
    def calculate_stats(
        self,
        geometry: GEOSGeometry
    ) -> PopulationStats:
        """
        Calculate population statistics for a geometry.
        
        Args:
            geometry: Django GEOSGeometry
            
        Returns:
            PopulationStats with summary statistics
        """
        grid = self.get_population_for_geometry(geometry)
        
        # Mask nodata
        data = np.ma.masked_equal(grid.data, grid.nodata)
        data = np.ma.masked_less(data, 0)  # Negative values are nodata
        
        # Calculate stats
        total_pop = float(np.sum(data))
        pixel_count = int(np.count_nonzero(~data.mask))
        
        # Area calculation (assuming ~1km resolution at equator)
        # WorldPop uses decimal degrees, approximately 0.00833 degrees = 1km
        pixel_area_km2 = (grid.resolution ** 2) * 111.32 ** 2 / 10000  # Approximate
        area_km2 = pixel_count * pixel_area_km2
        
        return PopulationStats(
            total_population=total_pop,
            population_density=total_pop / area_km2 if area_km2 > 0 else 0,
            area_km2=area_km2,
            pixel_count=pixel_count,
            min_population=float(np.min(data)) if pixel_count > 0 else 0,
            max_population=float(np.max(data)) if pixel_count > 0 else 0,
            mean_population=float(np.mean(data)) if pixel_count > 0 else 0
        )
    
    def resample_to_match(
        self,
        grid: PopulationGrid,
        target_transform: rasterio.transform.Affine,
        target_shape: Tuple[int, int],
        target_crs: str = "EPSG:4326",
        resampling: Resampling = Resampling.bilinear
    ) -> np.ndarray:
        """
        Resample population grid to match another grid.
        
        Args:
            grid: Source population grid
            target_transform: Target affine transform
            target_shape: Target (height, width)
            target_crs: Target CRS
            resampling: Resampling method
            
        Returns:
            Resampled population array
        """
        # Prepare output array
        destination = np.zeros(target_shape, dtype=grid.data.dtype)
        
        # Reproject
        reproject(
            source=grid.data,
            destination=destination,
            src_transform=grid.transform,
            src_crs=grid.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=resampling,
            src_nodata=grid.nodata,
            dst_nodata=grid.nodata
        )
        
        return destination
    
    def _geos_to_geojson(self, geometry: GEOSGeometry) -> dict:
        """Convert Django GEOSGeometry to GeoJSON-like dict."""
        return {
            "type": geometry.geom_type,
            "coordinates": geometry.coords if geometry.geom_type != "MultiPolygon" 
                          else list(geometry.coords)
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Singleton instance
_population_service: Optional[PopulationService] = None


def get_population_service() -> PopulationService:
    """Get or create singleton population service."""
    global _population_service
    if _population_service is None:
        _population_service = PopulationService()
    return _population_service
