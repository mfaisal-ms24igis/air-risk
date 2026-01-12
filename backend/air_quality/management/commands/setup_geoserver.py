"""
Django management command to set up GeoServer workspace, stores, and styles.
"""

import os
import logging

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from air_quality.services.geoserver import GeoServerClient
from geoserver.sld_templates import (
    get_aqi_sld,
    get_concentration_sld,
    get_district_style,
    get_station_style,
    get_hotspot_style,
    POLLUTANT_THRESHOLDS,
)
from geoserver.mosaic_config import generate_mosaic_config


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set up GeoServer workspace, ImageMosaic stores, and styles for air quality layers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace",
            type=str,
            default="air_quality",
            help="GeoServer workspace name (default: air_quality)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing workspace and recreate",
        )
        parser.add_argument(
            "--styles-only",
            action="store_true",
            help="Only update styles, skip stores",
        )
        parser.add_argument(
            "--stores-only",
            action="store_true",
            help="Only create stores, skip styles",
        )

    def handle(self, *args, **options):
        workspace = options["workspace"]
        reset = options["reset"]
        styles_only = options["styles_only"]
        stores_only = options["stores_only"]

        # Initialize GeoServer client
        try:
            client = GeoServerClient()
        except Exception as e:
            raise CommandError(f"Failed to connect to GeoServer: {e}")

        self.stdout.write(f"Setting up GeoServer workspace: {workspace}")

        # Reset workspace if requested
        if reset:
            self._reset_workspace(client, workspace)

        # Create workspace
        self._create_workspace(client, workspace)

        # Create styles
        if not stores_only:
            self._create_styles(client, workspace)

        # Create ImageMosaic stores
        if not styles_only:
            self._create_stores(client, workspace)

        self.stdout.write(
            self.style.SUCCESS(f"GeoServer setup completed for workspace: {workspace}")
        )

    def _reset_workspace(self, client: GeoServerClient, workspace: str):
        """Delete existing workspace."""
        self.stdout.write(f"Resetting workspace: {workspace}")
        try:
            client._make_request(
                "DELETE",
                f"workspaces/{workspace}",
                params={"recurse": "true"},
            )
            self.stdout.write(self.style.WARNING(f"Deleted workspace: {workspace}"))
        except Exception:
            self.stdout.write("Workspace does not exist, skipping reset")

    def _create_workspace(self, client: GeoServerClient, workspace: str):
        """Create GeoServer workspace."""
        self.stdout.write(f"Creating workspace: {workspace}")

        try:
            client.create_workspace(workspace)
            self.stdout.write(self.style.SUCCESS(f"Created workspace: {workspace}"))
        except Exception as e:
            if "already exists" in str(e).lower():
                self.stdout.write(f"Workspace {workspace} already exists")
            else:
                raise CommandError(f"Failed to create workspace: {e}")

    def _create_styles(self, client: GeoServerClient, workspace: str):
        """Create all SLD styles."""
        self.stdout.write("Creating styles...")

        pollutants = ["NO2", "SO2", "CO", "O3", "PM25"]

        # AQI styles for each pollutant
        for pollutant in pollutants:
            style_name = f"{pollutant.lower()}_aqi"
            sld = get_aqi_sld(f"{workspace}:{pollutant.lower()}", pollutant)
            self._upload_style(client, workspace, style_name, sld)

        # Concentration styles
        for pollutant, config in POLLUTANT_THRESHOLDS.items():
            style_name = f"{pollutant.lower()}_concentration"
            sld = get_concentration_sld(
                f"{workspace}:{pollutant.lower()}",
                pollutant,
                config["unit"],
                config["thresholds"],
            )
            self._upload_style(client, workspace, style_name, sld)

        # Vector styles
        vector_styles = [
            ("districts", get_district_style()),
            ("stations", get_station_style()),
            ("hotspots", get_hotspot_style()),
        ]

        for style_name, sld in vector_styles:
            self._upload_style(client, workspace, style_name, sld)

        self.stdout.write(self.style.SUCCESS("All styles created"))

    def _upload_style(
        self, client: GeoServerClient, workspace: str, name: str, sld: str
    ):
        """Upload a single SLD style."""
        try:
            # Check if style exists
            try:
                client._make_request("GET", f"workspaces/{workspace}/styles/{name}")
                # Style exists, update it
                client._make_request(
                    "PUT",
                    f"workspaces/{workspace}/styles/{name}",
                    data=sld,
                    headers={"Content-Type": "application/vnd.ogc.sld+xml"},
                )
                self.stdout.write(f"  Updated style: {name}")
            except Exception:
                # Style doesn't exist, create it
                # First create style entry
                client._make_request(
                    "POST",
                    f"workspaces/{workspace}/styles",
                    data={"style": {"name": name, "filename": f"{name}.sld"}},
                )
                # Then upload SLD content
                client._make_request(
                    "PUT",
                    f"workspaces/{workspace}/styles/{name}",
                    data=sld,
                    headers={"Content-Type": "application/vnd.ogc.sld+xml"},
                )
                self.stdout.write(f"  Created style: {name}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Failed to create style {name}: {e}"))

    def _create_stores(self, client: GeoServerClient, workspace: str):
        """Create ImageMosaic stores for each pollutant."""
        self.stdout.write("Creating ImageMosaic stores...")

        pollutants = ["NO2", "SO2", "CO", "O3", "PM25"]
        raster_dir = str(getattr(settings, "RASTER_DATA_PATH", "/app/data/rasters"))

        for pollutant in pollutants:
            store_name = f"{pollutant.lower()}_corrected"
            store_path = os.path.join(raster_dir, "corrected", pollutant.lower())

            try:
                self._create_mosaic_store(
                    client, workspace, store_name, store_path, pollutant
                )
                self.stdout.write(self.style.SUCCESS(f"  Created store: {store_name}"))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Failed to create store {store_name}: {e}")
                )

        self.stdout.write(self.style.SUCCESS("All stores created"))

    def _create_mosaic_store(
        self,
        client: GeoServerClient,
        workspace: str,
        store_name: str,
        store_path: str,
        pollutant: str,
    ):
        """Create a single ImageMosaic store."""
        # Generate configuration files
        configs = generate_mosaic_config(store_name, pollutant, store_path)

        # Write config files to store directory
        os.makedirs(store_path, exist_ok=True)
        for filename, content in configs.items():
            filepath = os.path.join(store_path, filename)
            with open(filepath, "w") as f:
                f.write(content)

        # Create the ImageMosaic store via REST API
        store_config = {
            "coverageStore": {
                "name": store_name,
                "type": "ImageMosaic",
                "enabled": True,
                "workspace": {"name": workspace},
                "url": f"file:{store_path}",
            }
        }

        try:
            # Try to create store
            client._make_request(
                "POST",
                f"workspaces/{workspace}/coveragestores",
                data=store_config,
            )
        except Exception as e:
            if "already exists" in str(e).lower():
                # Update existing store
                client._make_request(
                    "PUT",
                    f"workspaces/{workspace}/coveragestores/{store_name}",
                    data=store_config,
                )
            else:
                raise

        # Publish coverage from store
        coverage_config = {
            "coverage": {
            "name": store_name,
            "nativeName": store_name,
                "title": f"{pollutant} Air Quality",
                "srs": "EPSG:4326",
                "nativeBoundingBox": {
                    "minx": 60.0,
                    "maxx": 78.0,
                    "miny": 23.0,
                    "maxy": 37.5,
                    "crs": "EPSG:4326",
                },
                "enabled": True,
                "metadata": {
                    "entry": [
                        {
                            "@key": "time",
                            "dimensionInfo": {
                                "enabled": True,
                                "presentation": "CONTINUOUS_INTERVAL",
                                "units": "ISO8601",
                                "defaultValue": {
                                    "strategy": "MAXIMUM",
                                },
                            },
                        },
                    ],
                },
            }
        }

        try:
            client._make_request(
                "POST",
                f"workspaces/{workspace}/coveragestores/{store_name}/coverages",
                data=coverage_config,
            )
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        # Set default style
        style_name = f"{pollutant.lower()}_aqi"
        layer_config = {
            "layer": {
                "defaultStyle": {
                    "name": style_name,
                    "workspace": workspace,
                },
            }
        }

        client._make_request(
            "PUT",
            f"layers/{workspace}:{store_name}",
            data=layer_config,
        )
