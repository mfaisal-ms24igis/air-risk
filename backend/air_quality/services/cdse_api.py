"""
CDSE API Client for Sentinel-5P data.
Uses OAuth2 authentication for search and download operations.
"""

import requests
from django.conf import settings
from .cdse_auth import get_cdse_token

CDSE = settings.CDSE


def cdse_headers():
    """Get headers with OAuth2 Bearer token."""
    token = get_cdse_token()
    return {"Authorization": f"Bearer {token}"}


def search_s5p_products(filter_query, top=50, skip=0):
    """
    Uses OAuth2 Bearer token to query Sentinel-5P metadata.
    filter_query must be a valid OData filter string.
    """
    base = CDSE["API_BASE"]
    url = (
        f"{base}/Products?"
        f"$filter={filter_query}&$top={top}&$skip={skip}"
    )

    r = requests.get(url, headers=cdse_headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def download_s5p_product(product_id, file_path):
    """
    Uses token-based OAuth2 authentication to download Sentinel-5P product zip.
    """
    base = "https://download.dataspace.copernicus.eu/odata/v1"
    # Don't URL encode the parentheses - OData requires them as-is
    url = f"{base}/Products({product_id})/$value"

    with requests.get(url, headers=cdse_headers(), stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=16 * 1024 * 1024):
                if chunk:
                    f.write(chunk)

    return file_path