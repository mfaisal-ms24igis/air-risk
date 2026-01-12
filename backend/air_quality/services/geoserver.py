"""
GeoServer REST API client for managing ImageMosaic stores.
Handles publishing corrected rasters and managing TIME dimension.
"""

import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# GeoServer configuration
GEOSERVER_URL = settings.GEOSERVER_URL
GEOSERVER_USER = settings.GEOSERVER_ADMIN_USER
GEOSERVER_PASSWORD = settings.GEOSERVER_ADMIN_PASSWORD
GEOSERVER_WORKSPACE = settings.GEOSERVER_WORKSPACE


class GeoServerError(Exception):
    """GeoServer API error."""

    pass


class GeoServerClient:
    """
    Client for GeoServer REST API.
    Manages ImageMosaic stores with TIME dimension for corrected rasters.
    """

    def __init__(self):
        self.base_url = f"{GEOSERVER_URL}/rest"
        self.workspace = GEOSERVER_WORKSPACE
        self.session = requests.Session()
        self.session.auth = (GEOSERVER_USER, GEOSERVER_PASSWORD)
        self.session.headers.update(
            {
                "Accept": "application/json",
            }
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        json_data: dict = None,
        xml_data: str = None,
        files: dict = None,
        expected_codes: tuple = (200, 201, 202),
    ) -> Optional[dict]:
        """Make a request to GeoServer REST API."""
        url = f"{self.base_url}/{endpoint}"

        headers = {}
        if xml_data:
            headers["Content-Type"] = "application/xml"
        elif json_data:
            headers["Content-Type"] = "application/json"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=xml_data,
                files=files,
                headers=headers,
                timeout=120,
            )

            if response.status_code not in expected_codes:
                logger.error(
                    f"GeoServer error: {response.status_code} - {response.text}"
                )
                raise GeoServerError(
                    f"Request failed: {response.status_code} - {response.text}"
                )

            if response.content and "application/json" in response.headers.get(
                "Content-Type", ""
            ):
                return response.json()
            return None

        except requests.RequestException as e:
            logger.error(f"GeoServer connection error: {e}")
            raise GeoServerError(f"Connection failed: {e}")

    # ==================== Workspace Management ====================

    def workspace_exists(self) -> bool:
        """Check if the workspace exists."""
        try:
            self._make_request("GET", f"workspaces/{self.workspace}")
            return True
        except GeoServerError:
            return False

    def create_workspace(self) -> bool:
        """Create the workspace if it doesn't exist."""
        if self.workspace_exists():
            logger.info(f"Workspace {self.workspace} already exists")
            return False

        data = {"workspace": {"name": self.workspace}}

        self._make_request("POST", "workspaces", json_data=data)
        logger.info(f"Created workspace: {self.workspace}")
        return True

    # ==================== ImageMosaic Store Management ====================

    def store_exists(self, store_name: str) -> bool:
        """Check if a coverage store exists."""
        try:
            self._make_request(
                "GET", f"workspaces/{self.workspace}/coveragestores/{store_name}"
            )
            return True
        except GeoServerError:
            return False

    def create_imagemosaic_store(
        self, store_name: str, mosaic_path: str, description: str = None
    ) -> bool:
        """
        Create an ImageMosaic coverage store.

        Args:
            store_name: Name of the store
            mosaic_path: Path to the mosaic directory (on GeoServer server)
            description: Optional description

        Returns:
            True if created, False if already exists
        """
        if self.store_exists(store_name):
            logger.info(f"Store {store_name} already exists")
            return False

        # Create store via XML for ImageMosaic
        xml_data = f"""
        <coverageStore>
            <name>{store_name}</name>
            <type>ImageMosaic</type>
            <enabled>true</enabled>
            <workspace>
                <name>{self.workspace}</name>
            </workspace>
            <url>file:{mosaic_path}</url>
            <description>{description or store_name}</description>
        </coverageStore>
        """

        self._make_request(
            "POST", f"workspaces/{self.workspace}/coveragestores", xml_data=xml_data
        )
        logger.info(f"Created ImageMosaic store: {store_name}")
        return True

    def configure_time_dimension(self, store_name: str, coverage_name: str) -> None:
        """
        Configure TIME dimension for an ImageMosaic coverage.

        Args:
            store_name: Coverage store name
            coverage_name: Coverage/layer name
        """
        # Enable TIME dimension via metadata
        xml_data = f"""
        <coverage>
            <name>{coverage_name}</name>
            <metadata>
                <entry key="time">
                    <dimensionInfo>
                        <enabled>true</enabled>
                        <presentation>LIST</presentation>
                        <units>ISO8601</units>
                        <defaultValue>
                            <strategy>NEAREST</strategy>
                            <referenceValue>CURRENT</referenceValue>
                        </defaultValue>
                    </dimensionInfo>
                </entry>
            </metadata>
        </coverage>
        """

        self._make_request(
            "PUT",
            f"workspaces/{self.workspace}/coveragestores/{store_name}/coverages/{coverage_name}",
            xml_data=xml_data,
        )
        logger.info(f"Configured TIME dimension for {coverage_name}")

    def add_granule(
        self, store_name: str, coverage_name: str, granule_path: str
    ) -> None:
        """
        Add a new granule (raster file) to an ImageMosaic store.

        Args:
            store_name: Coverage store name
            coverage_name: Coverage name
            granule_path: Path to the raster file
        """
        # Harvest the granule
        self._make_request(
            "POST",
            f"workspaces/{self.workspace}/coveragestores/{store_name}/external.imagemosaic",
            params={"recalculate": "nativebbox,latlonbbox"},
            xml_data=f"file:{granule_path}",
            expected_codes=(200, 201, 202, 204),
        )
        logger.info(f"Added granule to {store_name}: {granule_path}")

    def list_granules(
        self, store_name: str, coverage_name: str, limit: int = 100
    ) -> list[dict]:
        """
        List granules in an ImageMosaic store.

        Args:
            store_name: Coverage store name
            coverage_name: Coverage name
            limit: Maximum number of granules to return

        Returns:
            List of granule metadata
        """
        result = self._make_request(
            "GET",
            f"workspaces/{self.workspace}/coveragestores/{store_name}/coverages/{coverage_name}/index/granules",
            params={"limit": limit},
        )

        if result and "features" in result:
            return result["features"]
        return []

    def delete_old_granules(
        self, store_name: str, coverage_name: str, keep_days: int = 90
    ) -> int:
        """
        Delete granules older than a specified number of days.

        Args:
            store_name: Coverage store name
            coverage_name: Coverage name
            keep_days: Number of days to keep

        Returns:
            Number of granules deleted
        """
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Get granules older than cutoff
        granules = self.list_granules(store_name, coverage_name, limit=1000)
        deleted = 0

        for granule in granules:
            props = granule.get("properties", {})
            time_value = props.get("time")

            if time_value and time_value < cutoff_str:
                granule_id = granule.get("id")
                if granule_id:
                    try:
                        self._make_request(
                            "DELETE",
                            f"workspaces/{self.workspace}/coveragestores/{store_name}/coverages/{coverage_name}/index/granules/{granule_id}",
                            expected_codes=(200, 204),
                        )
                        deleted += 1
                    except GeoServerError:
                        pass

        logger.info(f"Deleted {deleted} old granules from {store_name}")
        return deleted

    # ==================== Style Management ====================

    def style_exists(self, style_name: str) -> bool:
        """Check if a style exists."""
        try:
            self._make_request("GET", f"styles/{style_name}")
            return True
        except GeoServerError:
            return False

    def create_sld_style(self, style_name: str, sld_content: str) -> bool:
        """
        Create or update an SLD style.

        Args:
            style_name: Name of the style
            sld_content: SLD XML content

        Returns:
            True if created, False if updated
        """
        if self.style_exists(style_name):
            # Update existing style
            self._make_request(
                "PUT",
                f"styles/{style_name}",
                xml_data=sld_content,
                expected_codes=(200, 201, 204),
            )
            logger.info(f"Updated style: {style_name}")
            return False

        # Create new style
        self._make_request(
            "POST", "styles", params={"name": style_name}, xml_data=sld_content
        )
        logger.info(f"Created style: {style_name}")
        return True

    def set_layer_default_style(self, layer_name: str, style_name: str) -> None:
        """
        Set the default style for a layer.

        Args:
            layer_name: Layer name
            style_name: Style name
        """
        xml_data = f"""
        <layer>
            <defaultStyle>
                <name>{style_name}</name>
            </defaultStyle>
        </layer>
        """

        self._make_request(
            "PUT", f"layers/{self.workspace}:{layer_name}", xml_data=xml_data
        )
        logger.info(f"Set default style for {layer_name}: {style_name}")

    # ==================== GeoWebCache Management ====================

    def seed_layer(
        self,
        layer_name: str,
        min_zoom: int = 0,
        max_zoom: int = 14,
        grid_set: str = "EPSG:4326",
    ) -> None:
        """
        Seed tiles for a layer using GeoWebCache.

        Args:
            layer_name: Full layer name (workspace:layername)
            min_zoom: Minimum zoom level
            max_zoom: Maximum zoom level
            grid_set: Grid set name
        """
        full_layer = f"{self.workspace}:{layer_name}"

        xml_data = f"""
        <seedRequest>
            <name>{full_layer}</name>
            <gridSetId>{grid_set}</gridSetId>
            <zoomStart>{min_zoom}</zoomStart>
            <zoomStop>{max_zoom}</zoomStop>
            <type>seed</type>
            <threadCount>4</threadCount>
        </seedRequest>
        """

        # GWC endpoint
        url = f"{GEOSERVER_URL}/gwc/rest/seed/{full_layer}.xml"

        try:
            response = self.session.post(
                url,
                data=xml_data,
                headers={"Content-Type": "application/xml"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"Started seeding: {full_layer}")
        except requests.RequestException as e:
            logger.error(f"GWC seed error: {e}")

    def truncate_layer_cache(self, layer_name: str) -> None:
        """
        Truncate the tile cache for a layer.

        Args:
            layer_name: Layer name
        """
        full_layer = f"{self.workspace}:{layer_name}"

        xml_data = f"""
        <truncateRequest>
            <name>{full_layer}</name>
        </truncateRequest>
        """

        url = f"{GEOSERVER_URL}/gwc/rest/masstruncate"

        try:
            response = self.session.post(
                url,
                data=xml_data,
                headers={"Content-Type": "application/xml"},
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f"Truncated cache for: {full_layer}")
        except requests.RequestException as e:
            logger.error(f"GWC truncate error: {e}")

    # ==================== Setup Helpers ====================

    def setup_pollutant_store(self, pollutant: str, mosaic_base_path: str) -> None:
        """
        Set up a complete ImageMosaic store for a pollutant.

        Args:
            pollutant: Pollutant code (NO2, SO2, etc.)
            mosaic_base_path: Base path for mosaic directories
        """
        store_name = f"{pollutant.lower()}_corrected"
        coverage_name = store_name
        mosaic_path = f"{mosaic_base_path}/{store_name}"

        # Create store
        self.create_imagemosaic_store(
            store_name=store_name,
            mosaic_path=mosaic_path,
            description=f"Bias-corrected {pollutant} concentration",
        )

        # Configure TIME dimension
        self.configure_time_dimension(store_name, coverage_name)

        logger.info(f"Setup complete for {pollutant} store")

    def setup_all_stores(self, mosaic_base_path: str) -> None:
        """
        Set up ImageMosaic stores for all pollutants.

        Args:
            mosaic_base_path: Base path for mosaic directories
        """
        from ..constants import Pollutant

        # Ensure workspace exists
        self.create_workspace()

        for pollutant in Pollutant:
            self.setup_pollutant_store(pollutant.value, mosaic_base_path)

        logger.info("Setup complete for all pollutant stores")


# Singleton instance
geoserver_client = GeoServerClient()
