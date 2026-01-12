"""
Django management command to load Pakistan district boundaries.
"""

import os
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction

try:
    import fiona

    FIONA_AVAILABLE = True
except ImportError:
    FIONA_AVAILABLE = False

try:
    import geopandas as gpd

    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

from air_quality.models import District


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load Pakistan district boundaries from shapefile or GeoJSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path to shapefile (.shp) or GeoJSON file",
        )
        parser.add_argument(
            "--name-field",
            type=str,
            default="NAME",
            help="Field containing district name (default: NAME)",
        )
        parser.add_argument(
            "--province-field",
            type=str,
            default="PROVINCE",
            help="Field containing province name (default: PROVINCE)",
        )
        parser.add_argument(
            "--code-field",
            type=str,
            default="CODE",
            help="Field containing district code (default: CODE)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing districts before loading",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be loaded without saving",
        )

    def handle(self, *args, **options):
        source = options["source"]
        name_field = options["name_field"]
        province_field = options["province_field"]
        code_field = options["code_field"]
        clear = options["clear"]
        dry_run = options["dry_run"]

        # Check file exists
        if not os.path.exists(source):
            raise CommandError(f"File not found: {source}")

        # Determine file type
        ext = Path(source).suffix.lower()

        if ext == ".shp":
            if not FIONA_AVAILABLE and not GEOPANDAS_AVAILABLE:
                raise CommandError(
                    "fiona or geopandas required for shapefile support. "
                    "Install with: pip install fiona geopandas"
                )
        elif ext == ".gpkg":
            if not GEOPANDAS_AVAILABLE:
                raise CommandError(
                    "geopandas required for GeoPackage support. "
                    "Install with: pip install geopandas"
                )
        elif ext not in [".json", ".geojson"]:
            raise CommandError(f"Unsupported file format: {ext}")

        self.stdout.write(f"Loading districts from: {source}")

        # Load features
        features = self._load_features(source, ext)

        if not features:
            raise CommandError("No features found in file")

        self.stdout.write(f"Found {len(features)} features")

        # Clear existing if requested
        if clear and not dry_run:
            count = District.objects.count()
            District.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing districts"))

        # Load districts
        loaded = 0
        skipped = 0
        errors = 0

        with transaction.atomic():
            for feature in features:
                try:
                    result = self._process_feature(
                        feature,
                        name_field,
                        province_field,
                        code_field,
                        dry_run,
                    )
                    if result:
                        loaded += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f"Error processing feature: {e}")
                    )

        # Summary
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded: {loaded}, Skipped: {skipped}, Errors: {errors}"
            )
        )

    def _load_features(self, source: str, ext: str) -> list:
        """Load features from file."""
        features = []

        if GEOPANDAS_AVAILABLE:
            # Use geopandas for all formats
            gdf = gpd.read_file(source)
            for _, row in gdf.iterrows():
                features.append(
                    {
                        "properties": row.to_dict(),
                        "geometry": row.geometry.__geo_interface__,
                    }
                )
        elif FIONA_AVAILABLE and ext == ".shp":
            # Use fiona for shapefiles
            with fiona.open(source) as src:
                for feature in src:
                    features.append(feature)
        else:
            # Use json for GeoJSON
            import json

            with open(source) as f:
                data = json.load(f)

            if data.get("type") == "FeatureCollection":
                features = data.get("features", [])
            elif data.get("type") == "Feature":
                features = [data]
            else:
                raise CommandError("Invalid GeoJSON format")

        return features

    def _process_feature(
        self,
        feature: dict,
        name_field: str,
        province_field: str,
        code_field: str,
        dry_run: bool,
    ) -> bool:
        """Process a single feature."""
        properties = feature.get("properties", {})
        geometry = feature.get("geometry")

        if not geometry:
            self.stdout.write(self.style.WARNING("  Skipping feature without geometry"))
            return False

        # Get name
        name = properties.get(name_field)
        if not name:
            # Try alternative field names
            for alt in ["name", "NAME", "district", "DISTRICT", "ADM2_EN"]:
                if properties.get(alt):
                    name = properties[alt]
                    break

        if not name:
            self.stdout.write(self.style.WARNING("  Skipping feature without name"))
            return False

        # Get province
        province = properties.get(province_field)
        if not province:
            for alt in ["province", "PROVINCE", "ADM1_EN", "state", "STATE"]:
                if properties.get(alt):
                    province = properties[alt]
                    break

        # Get code
        code = properties.get(code_field)
        if not code:
            for alt in ["code", "CODE", "ADM2_PCODE", "id", "ID"]:
                if properties.get(alt):
                    code = properties[alt]
                    break

        if not code:
            # Generate code from name
            code = name.upper().replace(" ", "_")[:20]

        # Parse geometry
        try:
            import json

            geom_json = json.dumps(geometry)
            geom = GEOSGeometry(geom_json)

            # Fix self-intersections using buffer(0) before type conversion
            if not geom.valid:
                self.stdout.write(self.style.WARNING(f"  Fixing invalid geometry for {name}"))
                geom = geom.buffer(0)

            # Ensure MultiPolygon
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            elif not isinstance(geom, MultiPolygon):
                # Try to fix by buffering
                fixed_geom = geom.buffer(0)
                if isinstance(fixed_geom, Polygon):
                    geom = MultiPolygon([fixed_geom])
                elif isinstance(fixed_geom, MultiPolygon):
                    geom = fixed_geom
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  Skipping {name}: unsupported geometry type {type(geom)}")
                    )
                    return False

            # Ensure valid after conversion
            if not geom.valid:
                geom = geom.buffer(0)
                # Re-check MultiPolygon after buffer
                if isinstance(geom, Polygon):
                    geom = MultiPolygon([geom])

            # Ensure SRID is set to 4326 (WGS84)
            if not geom.srid:
                geom.srid = 4326

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  Error parsing geometry for {name}: {e}")
            )
            return False

        if dry_run:
            self.stdout.write(f"  Would load: {name} ({province or 'Unknown'})")
            return True

        # Create or update district
        district, created = District.objects.update_or_create(
            name=name,
            province=province or "Unknown",
            defaults={
                "geometry": geom,
                "area_km2": geom.transform(32643, clone=True).area / 1_000_000
                if geom
                else 0,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action}: {name}")

        return True
