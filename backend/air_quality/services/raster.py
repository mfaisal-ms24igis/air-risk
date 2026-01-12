"""
Raster utilities for processing and managing GeoTIFF files.
Handles COG optimization, windowed reads, and raster statistics.
"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union, Generator
import shutil

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds
from rasterio.warp import reproject, calculate_default_transform
from django.conf import settings
from django.contrib.gis.geos import Polygon

logger = logging.getLogger(__name__)

# Base paths
RASTER_STORAGE_PATH = Path(settings.RASTER_DATA_PATH)
WORLDPOP_PATH = Path(settings.WORLDPOP_DATA_PATH) / "pak_ppp_2020_1km_UNadj.tif"


class RasterError(Exception):
    """Raster processing error."""

    pass


def ensure_cog(
    input_path: Union[str, Path],
    output_path: Union[str, Path] = None,
    blocksize: int = 256,
) -> Path:
    """
    Convert a GeoTIFF to Cloud-Optimized GeoTIFF (COG).

    Args:
        input_path: Path to input GeoTIFF
        output_path: Path for output COG (defaults to input with .cog.tif suffix)
        blocksize: Tile size for COG

    Returns:
        Path to COG file
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.with_suffix(".cog.tif")
    else:
        output_path = Path(output_path)

    cog_profile = {
        "driver": "GTiff",
        "interleave": "band",
        "tiled": True,
        "blockxsize": blocksize,
        "blockysize": blocksize,
        "compress": "deflate",
        "predictor": 2,
    }

    with rasterio.open(input_path) as src:
        cog_profile.update(
            {
                "count": src.count,
                "dtype": src.dtypes[0],
                "crs": src.crs,
                "transform": src.transform,
                "width": src.width,
                "height": src.height,
                "nodata": src.nodata,
            }
        )

        with rasterio.open(output_path, "w", **cog_profile) as dst:
            for i in range(1, src.count + 1):
                data = src.read(i)
                dst.write(data, i)

            # Build overviews
            dst.build_overviews([2, 4, 8, 16, 32], Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

    logger.info(f"Created COG: {output_path}")
    return output_path


def reproject_raster(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    dst_crs: str = "EPSG:4326",
    resolution: float = None,
) -> Path:
    """
    Reproject a raster to a new CRS.

    Args:
        input_path: Path to input raster
        output_path: Path for output raster
        dst_crs: Target CRS
        resolution: Target resolution (optional)

    Returns:
        Path to reprojected raster
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    with rasterio.open(input_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=resolution
        )

        profile = src.profile.copy()
        profile.update(
            {
                "crs": dst_crs,
                "transform": transform,
                "width": width,
                "height": height,
            }
        )

        with rasterio.open(output_path, "w", **profile) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear,
                )

    logger.info(f"Reprojected raster to {dst_crs}: {output_path}")
    return output_path


def read_raster_window(
    raster_path: Union[str, Path], bounds: tuple, band: int = 1
) -> tuple[np.ndarray, dict]:
    """
    Read a windowed portion of a raster.

    Args:
        raster_path: Path to raster file
        bounds: (minx, miny, maxx, maxy) in raster CRS
        band: Band number to read

    Returns:
        Tuple of (data array, metadata dict)
    """
    with rasterio.open(raster_path) as src:
        window = from_bounds(*bounds, src.transform)
        data = src.read(band, window=window)

        metadata = {
            "transform": src.window_transform(window),
            "crs": src.crs,
            "nodata": src.nodata,
            "bounds": bounds,
            "shape": data.shape,
        }

        return data, metadata


def read_raster_at_points(
    raster_path: Union[str, Path], points: list[tuple], band: int = 1
) -> list[Optional[float]]:
    """
    Read raster values at specific points.

    Args:
        raster_path: Path to raster file
        points: List of (x, y) coordinates in raster CRS
        band: Band number to read

    Returns:
        List of values (None for nodata or out-of-bounds)
    """
    with rasterio.open(raster_path) as src:
        values = list(src.sample(points, indexes=band))

        results = []
        for val in values:
            if val is not None and len(val) > 0:
                v = val[0]
                if src.nodata is not None and v == src.nodata:
                    results.append(None)
                elif np.isnan(v):
                    results.append(None)
                else:
                    results.append(float(v))
            else:
                results.append(None)

        return results


def get_raster_stats(
    raster_path: Union[str, Path], band: int = 1, mask: np.ndarray = None
) -> dict:
    """
    Calculate statistics for a raster band.

    Args:
        raster_path: Path to raster file
        band: Band number
        mask: Optional boolean mask (True = include)

    Returns:
        Dictionary with min, max, mean, std, count
    """
    with rasterio.open(raster_path) as src:
        data = src.read(band)
        nodata = src.nodata

        # Create valid data mask
        if nodata is not None:
            valid = data != nodata
        else:
            valid = ~np.isnan(data)

        if mask is not None:
            valid = valid & mask

        valid_data = data[valid]

        if len(valid_data) == 0:
            return {
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
                "count": 0,
            }

        return {
            "min": float(np.min(valid_data)),
            "max": float(np.max(valid_data)),
            "mean": float(np.mean(valid_data)),
            "std": float(np.std(valid_data)),
            "count": int(len(valid_data)),
        }


def iterate_raster_tiles(
    raster_path: Union[str, Path], tile_size: int = 256, band: int = 1
) -> Generator[tuple[np.ndarray, Window, dict], None, None]:
    """
    Iterate over raster in tiles.

    Args:
        raster_path: Path to raster file
        tile_size: Size of tiles
        band: Band number to read

    Yields:
        Tuple of (data array, window, metadata)
    """
    with rasterio.open(raster_path) as src:
        for ji, window in src.block_windows(band):
            data = src.read(band, window=window)

            metadata = {
                "transform": src.window_transform(window),
                "crs": src.crs,
                "nodata": src.nodata,
                "block_index": ji,
            }

            yield data, window, metadata


class RasterManager:
    """
    Manager for organizing and accessing pollutant rasters.
    """

    def __init__(self, base_path: Path = None):
        self.base_path = base_path or RASTER_STORAGE_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_raw_path(self, pollutant: str, date: date) -> Path:
        """Get path for raw (uncorrected) raster."""
        return (
            self.base_path
            / "raw"
            / pollutant.lower()
            / f"{pollutant.lower()}_{date.isoformat()}.tif"
        )

    def get_corrected_path(self, pollutant: str, date: date) -> Path:
        """Get path for corrected raster."""
        return (
            self.base_path
            / "corrected"
            / pollutant.lower()
            / f"{pollutant.lower()}_corrected_{date.isoformat()}.tif"
        )

    def get_mosaic_path(self, pollutant: str) -> Path:
        """Get path for ImageMosaic directory."""
        return self.base_path / "mosaics" / f"{pollutant.lower()}_corrected"

    def ensure_directories(self) -> None:
        """Create all necessary directories."""
        from ..constants import Pollutant

        for pollutant in Pollutant:
            p = pollutant.value.lower()
            (self.base_path / "raw" / p).mkdir(parents=True, exist_ok=True)
            (self.base_path / "corrected" / p).mkdir(parents=True, exist_ok=True)
            (self.base_path / "mosaics" / f"{p}_corrected").mkdir(
                parents=True, exist_ok=True
            )

    def list_available_dates(
        self, pollutant: str, corrected: bool = False
    ) -> list[date]:
        """List dates with available rasters."""
        if corrected:
            pattern = f"{pollutant.lower()}_corrected_*.tif"
            base = self.base_path / "corrected" / pollutant.lower()
        else:
            pattern = f"{pollutant.lower()}_*.tif"
            base = self.base_path / "raw" / pollutant.lower()

        dates = []
        for path in base.glob(pattern):
            try:
                # Extract date from filename
                parts = path.stem.split("_")
                date_str = parts[-1]  # Last part is date
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                dates.append(d)
            except ValueError:
                continue

        return sorted(dates)

    def save_raster(
        self,
        data: np.ndarray,
        transform,
        crs,
        output_path: Path,
        nodata: float = None,
        dtype: str = "float32",
    ) -> Path:
        """
        Save a numpy array as a GeoTIFF.

        Args:
            data: 2D numpy array
            transform: Affine transform
            crs: Coordinate reference system
            output_path: Output path
            nodata: NoData value
            dtype: Data type

        Returns:
            Path to saved file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        profile = {
            "driver": "GTiff",
            "dtype": dtype,
            "width": data.shape[1],
            "height": data.shape[0],
            "count": 1,
            "crs": crs,
            "transform": transform,
            "nodata": nodata,
            "compress": "deflate",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
        }

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data.astype(dtype), 1)

        logger.info(f"Saved raster: {output_path}")
        return output_path

    def copy_to_mosaic(
        self, pollutant: str, date: date, source_path: Path = None
    ) -> Path:
        """
        Copy a corrected raster to the ImageMosaic directory.

        Args:
            pollutant: Pollutant code
            date: Raster date
            source_path: Source path (defaults to corrected path)

        Returns:
            Path to mosaic file
        """
        if source_path is None:
            source_path = self.get_corrected_path(pollutant, date)

        mosaic_dir = self.get_mosaic_path(pollutant)
        mosaic_dir.mkdir(parents=True, exist_ok=True)

        # Filename format for ImageMosaic TIME dimension
        # Format: {name}_{YYYYMMDD}T000000.tif
        mosaic_filename = (
            f"{pollutant.lower()}_corrected_{date.strftime('%Y%m%d')}T000000.tif"
        )
        mosaic_path = mosaic_dir / mosaic_filename

        shutil.copy2(source_path, mosaic_path)
        logger.info(f"Copied to mosaic: {mosaic_path}")

        return mosaic_path


class WorldPopReader:
    """
    Reader for WorldPop population grid.
    """

    def __init__(self, worldpop_path: Path = None):
        self.worldpop_path = worldpop_path or WORLDPOP_PATH
        self._dataset = None

    @property
    def dataset(self):
        """Lazy load the WorldPop dataset."""
        if self._dataset is None:
            self._dataset = rasterio.open(self.worldpop_path)
        return self._dataset

    def close(self):
        """Close the dataset."""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None

    def get_population_for_bounds(self, bounds: tuple) -> tuple[np.ndarray, dict]:
        """
        Get population grid for a bounding box.

        Args:
            bounds: (minx, miny, maxx, maxy) in EPSG:4326

        Returns:
            Tuple of (population array, metadata)
        """
        return read_raster_window(self.worldpop_path, bounds)

    def get_total_population(self, geometry: Polygon) -> float:
        """
        Calculate total population within a geometry.

        Args:
            geometry: Polygon geometry in EPSG:4326

        Returns:
            Total population
        """
        from rasterio.mask import mask as raster_mask

        with rasterio.open(self.worldpop_path) as src:
            # Convert Django geometry to GeoJSON-like dict
            geom = geometry.json
            import json

            geom_dict = json.loads(geom)

            try:
                masked, _ = raster_mask(src, [geom_dict], crop=True, nodata=np.nan)

                # Sum population, ignoring nodata
                valid = ~np.isnan(masked)
                return float(np.sum(masked[valid]))

            except Exception as e:
                logger.error(f"Error calculating population: {e}")
                return 0.0

    def get_population_at_points(self, points: list[tuple]) -> list[Optional[float]]:
        """
        Get population values at specific points.

        Args:
            points: List of (x, y) coordinates in EPSG:4326

        Returns:
            List of population values
        """
        return read_raster_at_points(self.worldpop_path, points)


# Singleton instances
raster_manager = RasterManager()
worldpop_reader = WorldPopReader()
