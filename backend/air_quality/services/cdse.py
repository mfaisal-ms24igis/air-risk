"""
CDSE (Copernicus Data Space Ecosystem) API client for Sentinel-5P data.
Handles OAuth2 authentication and raster download using OData API.
"""

import logging
import zipfile
import tempfile
from datetime import datetime, date
from pathlib import Path

import requests
import xarray as xr
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from django.conf import settings
from django.core.cache import cache

from ..constants import Pollutant, CDSE_BAND_NAMES
from .cdse_auth import get_cdse_token

logger = logging.getLogger(__name__)

# CDSE API endpoints
CATALOG_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"


class CDSEAuthError(Exception):
    """CDSE authentication error."""

    pass


class CDSEDownloadError(Exception):
    """CDSE data download error."""

    pass


class CDSEClient:
    """
    Client for Copernicus Data Space Ecosystem API.
    Handles Sentinel-5P data downloads using OAuth2.
    """

    def __init__(self):
        pass

    def _get_access_token(self) -> str:
        """
        Get OAuth2 access token using the auth service.
        """
        return get_cdse_token()

    def _make_authenticated_request(
        self, method: str, url: str, **kwargs
    ) -> requests.Response:
        """Make an authenticated request to CDSE API."""
        token = self._get_access_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        response = requests.request(
            method, url, headers=headers, timeout=kwargs.pop("timeout", 120), **kwargs
        )

        # Handle token expiration
        if response.status_code == 401:
            # Clear cache and retry once
            cache.delete("cdse_oauth_access_token")
            cache.delete("cdse_oauth_expires_at")
            token = self._get_access_token()
            headers["Authorization"] = f"Bearer {token}"
            response = requests.request(
                method, url, headers=headers, timeout=120, **kwargs
            )

        return response

    def download_raster(
        self,
        pollutant: Pollutant,
        target_date: date,
        output_path: Path,
        bbox: list = None,
        resolution: int = 1000,  # meters
    ) -> Path:
        """
        Download Sentinel-5P raster for Pakistan using OData API.

        Args:
            pollutant: The pollutant to download
            target_date: The date to download data for
            output_path: Path to save the output file
            bbox: Bounding box [min_lon, min_lat, max_lon, max_lat]
            resolution: Spatial resolution in meters

        Returns:
            Path to the downloaded file
        """
        if bbox is None:
            bbox = settings.PAKISTAN_BBOX

        band_name = CDSE_BAND_NAMES.get(pollutant)
        if not band_name:
            raise CDSEDownloadError(f"Unknown pollutant: {pollutant}")

        logger.info(f"Downloading {pollutant.value} raster for {target_date}")

        # Find available products for the date
        products = self._find_s5p_products(pollutant, target_date)
        if not products:
            raise CDSEDownloadError(f"No {pollutant.value} products found for {target_date}")

        # Download and process the first available product
        product = products[0]  # Use the most recent
        logger.info(f"Processing product: {product['Name']}")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download the product (NetCDF file directly)
                product_id = product['Id']
                download_url = f"{DOWNLOAD_URL}({product_id})/$value"

                nc_path = Path(temp_dir) / f"product_{product_id}.nc"

                with open(nc_path, "wb") as f:
                    response = self._make_authenticated_request(
                        "GET", download_url, stream=True, timeout=600
                    )

                    if response.status_code != 200:
                        error_msg = response.text[:500]
                        logger.error(f"Download failed: {response.status_code} - {error_msg}")
                        raise CDSEDownloadError(f"Download failed: {response.status_code}")

                    # Download with progress indication
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                logger.debug(f"Download progress: {progress:.1f}%")

                    logger.info(f"Downloaded {downloaded} bytes")

                    # Process the NetCDF file directly
                    processed_path = self._process_netcdf_to_tiff(
                        nc_path, band_name, output_path, bbox, resolution
                    )

            logger.info(f"Successfully processed {pollutant.value} to {processed_path}")
            return processed_path

        except requests.RequestException as e:
            logger.error(f"CDSE request failed: {e}")
            raise CDSEDownloadError(f"Request failed: {e}")

    def _build_evalscript(self, band_name: str) -> str:
        """Build evalscript for Sentinel-5P data retrieval."""
        return f"""
//VERSION=3
function setup() {{
    return {{
        input: ["{band_name}", "dataMask"],
        output: {{
            bands: 1,
            sampleType: "FLOAT32"
        }}
    }};
}}

function evaluatePixel(sample) {{
    if (sample.dataMask == 0) {{
        return [-9999];
    }}
    return [sample.{band_name}];
}}
"""

    def _find_s5p_products(self, pollutant: Pollutant, target_date: date) -> list:
        """Find available Sentinel-5P products for a given date and pollutant."""
        # Map pollutant to S5P product type
        product_types = {
            Pollutant.NO2: "S5P_OFFL_L2__NO2",
            Pollutant.SO2: "S5P_OFFL_L2__SO2",
            Pollutant.CO: "S5P_OFFL_L2__CO",
            Pollutant.O3: "S5P_OFFL_L2__O3",
            Pollutant.PM25: "S5P_OFFL_L2__AER_AI",
        }

        product_type = product_types.get(pollutant)
        if not product_type:
            return []

        # Query for products from target_date 00:00 to next_day 00:00
        start_date = f"{target_date}T00:00:00.000Z"
        end_date = f"{target_date}T23:59:59.999Z"

        params = {
            "$filter": f"Collection/Name eq 'SENTINEL-5P' and startswith(Name,'{product_type}') and ContentDate/Start gt {start_date} and ContentDate/Start lt {end_date}",
            "$orderby": "ContentDate/Start desc",
            "$top": "10"  # Get up to 10 products
        }

        try:
            response = self._make_authenticated_request("GET", CATALOG_URL, params=params)

            if response.status_code != 200:
                logger.warning(f"Catalog query failed: {response.status_code}")
                return []

            data = response.json()
            return data.get("value", [])

        except Exception as e:
            logger.error(f"Catalog query error: {e}")
            return []

    def _process_netcdf_to_tiff(
        self, nc_path: Path, band_name: str, output_path: Path, bbox: list, resolution: int
    ) -> Path:
        """Process NetCDF file to extract band data and save as GeoTIFF."""
        try:
            # Open the NetCDF file
            with xr.open_dataset(nc_path) as ds:
                logger.info(f"NetCDF variables: {list(ds.data_vars)}")

                # Find the data variable (it might have a different name)
                data_var = None
                for var_name in ds.data_vars:
                    if band_name.lower() in var_name.lower() or var_name == band_name:
                        data_var = var_name
                        break

                if data_var is None:
                    # Try common Sentinel-5P variable names
                    possible_names = [band_name, f"{band_name}_column_number_density",
                                    f"tropospheric_{band_name}", f"{band_name.lower()}_tropo"]
                    for name in possible_names:
                        if name in ds.data_vars:
                            data_var = name
                            break

                if data_var is None:
                    available_vars = list(ds.data_vars.keys())
                    raise CDSEDownloadError(f"Could not find {band_name} variable. Available: {available_vars}")

                logger.info(f"Using variable: {data_var}")

                # Extract the data
                data = ds[data_var].values
                lat = ds['latitude'].values if 'latitude' in ds else ds['lat'].values
                lon = ds['longitude'].values if 'longitude' in ds else ds['lon'].values

                # Handle different data shapes
                if data.ndim == 3:
                    # Time, lat, lon - take the first time slice
                    data = data[0]
                elif data.ndim == 2:
                    # lat, lon - use as is
                    pass
                else:
                    raise CDSEDownloadError(f"Unexpected data dimensions: {data.shape}")

                # Create coordinate grids
                lon_grid, lat_grid = np.meshgrid(lon, lat)

                # Clip to bounding box
                mask = (lon_grid >= bbox[0]) & (lon_grid <= bbox[2]) & \
                       (lat_grid >= bbox[1]) & (lat_grid <= bbox[3])

                if not np.any(mask):
                    raise CDSEDownloadError("No data found within bounding box")

                # Get bounds of valid data
                valid_indices = np.where(mask)
                min_row, max_row = valid_indices[0].min(), valid_indices[0].max()
                min_col, max_col = valid_indices[1].min(), valid_indices[1].max()

                # Extract valid data
                data_clipped = data[min_row:max_row+1, min_col:max_col+1]
                lat_clipped = lat_grid[min_row:max_row+1, min_col:max_col+1]
                lon_clipped = lon_grid[min_row:max_row+1, min_col:max_col+1]

                # Replace fill values with NaN
                fill_value = ds[data_var].attrs.get('_FillValue', -9999)
                data_clipped = np.where(data_clipped == fill_value, np.nan, data_clipped)

                # Calculate output dimensions
                height, width = data_clipped.shape
                out_width = int(width * (lon[1] - lon[0]) * 111000 / resolution) if width > 1 else width
                out_height = int(height * (lat[1] - lat[0]) * 111000 / resolution) if height > 1 else height

                # Resample if needed
                if out_width != width or out_height != height:
                    from scipy.ndimage import zoom
                    zoom_factors = (out_height / height, out_width / width)
                    data_clipped = zoom(data_clipped, zoom_factors, order=1)  # Linear interpolation
                    height, width = data_clipped.shape

                # Create transform
                transform = from_bounds(
                    lon_clipped.min(), lat_clipped.min(),
                    lon_clipped.max(), lat_clipped.max(),
                    width, height
                )

                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

                # Write GeoTIFF
                with rasterio.open(
                    output_path,
                    'w',
                    driver='GTiff',
                    height=height,
                    width=width,
                    count=1,
                    dtype=data_clipped.dtype,
                    crs='EPSG:4326',
                    transform=transform,
                    nodata=np.nan
                ) as dst:
                    dst.write(data_clipped, 1)

                logger.info(f"Created GeoTIFF: {output_path} ({width}x{height})")
                return output_path

        except Exception as e:
            logger.error(f"NetCDF processing error: {e}")
            raise CDSEDownloadError(f"Failed to process NetCDF: {e}")

    def get_available_dates(
        self, pollutant: Pollutant, start_date: date, end_date: date, bbox: list = None
    ) -> list[date]:
        """
        Query catalog for available data dates using OData API.

        Args:
            pollutant: The pollutant to check
            start_date: Start of date range
            end_date: End of date range
            bbox: Bounding box

        Returns:
            List of dates with available data
        """
        if bbox is None:
            bbox = settings.PAKISTAN_BBOX

        # Map pollutant to S5P product type
        product_types = {
            Pollutant.NO2: "S5P_OFFL_L2__NO2",
            Pollutant.SO2: "S5P_OFFL_L2__SO2",
            Pollutant.CO: "S5P_OFFL_L2__CO",
            Pollutant.O3: "S5P_OFFL_L2__O3",
            Pollutant.PM25: "S5P_OFFL_L2__AER_AI",
        }

        product_type = product_types.get(pollutant)
        if not product_type:
            return []

        # Query for products in date range
        start_str = f"{start_date}T00:00:00.000Z"
        end_str = f"{end_date}T23:59:59.999Z"

        params = {
            "$filter": f"Collection/Name eq 'SENTINEL-5P' and startswith(Name,'{product_type}') and ContentDate/Start gt {start_str} and ContentDate/Start lt {end_str}",
            "$orderby": "ContentDate/Start",
            "$top": "1000"  # Get up to 1000 products
        }

        try:
            response = self._make_authenticated_request("GET", CATALOG_URL, params=params)

            if response.status_code != 200:
                logger.warning(f"Catalog query failed: {response.status_code}")
                return []

            data = response.json()
            dates = set()

            for product in data.get("value", []):
                datetime_str = product.get("ContentDate", {}).get("Start", "")
                if datetime_str:
                    # Parse ISO format datetime
                    dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                    dates.add(dt.date())

            return sorted(dates)

        except Exception as e:
            logger.error(f"Catalog query error: {e}")
            return []


# Singleton instance
cdse_client = CDSEClient()
