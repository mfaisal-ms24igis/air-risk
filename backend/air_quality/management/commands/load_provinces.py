"""
Django management command to load Pakistan province boundaries.
"""

import os
import logging
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False

from air_quality.models import Province


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load Pakistan province boundaries from GeoPackage, shapefile, or GeoJSON"

    def add_arguments(self, parser):
        parser.add_argument(
            "source",
            type=str,
            help="Path to GeoPackage (.gpkg), shapefile (.shp), or GeoJSON file",
        )
        parser.add_argument(
            "--name-field",
            type=str,
            default="PROVINCE",
            help="Field containing province name (default: PROVINCE)",
        )
        parser.add_argument(
            "--population-field",
            type=str,
            default="Population",
            help="Field containing population (default: Population)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing provinces before loading",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be loaded without saving",
        )

    def handle(self, *args, **options):
        source = options["source"]
        name_field = options["name_field"]
        population_field = options["population_field"]
        clear = options["clear"]
        dry_run = options["dry_run"]

        # Check file exists
        if not os.path.exists(source):
            raise CommandError(f"File not found: {source}")

        # Determine file type
        ext = Path(source).suffix.lower()

        if ext in [".shp", ".gpkg"]:
            if not GEOPANDAS_AVAILABLE:
                raise CommandError(
                    "geopandas required for shapefile/GeoPackage support. "
                    "Install with: pip install geopandas"
                )
        elif ext not in [".json", ".geojson"]:
            raise CommandError(f"Unsupported file format: {ext}")

        self.stdout.write(f"Loading provinces from: {source}")

        # Load features
        features = self._load_features(source, ext)

        if not features:
            raise CommandError("No features found in file")

        self.stdout.write(f"Found {len(features)} features")

        # Clear existing if requested
        if clear and not dry_run:
            count = Province.objects.count()
            Province.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing provinces"))

        # Load provinces
        loaded = 0
        skipped = 0
        errors = 0

        with transaction.atomic():
            for feature in features:
                try:
                    result = self._process_feature(
                        feature,
                        name_field,
                        population_field,
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
                features.append({
                    "properties": row.to_dict(),
                    "geometry": row.geometry.__geo_interface__,
                })
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
        population_field: str,
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
            for alt in ["name", "NAME", "province", "PROVINCE", "ADM1_EN"]:
                if properties.get(alt):
                    name = properties[alt]
                    break

        if not name:
            self.stdout.write(self.style.WARNING("  Skipping feature without name"))
            return False

        # Get population
        population = properties.get(population_field)
        if population:
            try:
                population = int(float(population))
            except (ValueError, TypeError):
                population = None

        # Parse geometry
        try:
            import json
            geom_json = json.dumps(geometry)
            geom = GEOSGeometry(geom_json)

            # Ensure MultiPolygon
            if isinstance(geom, Polygon):
                geom = MultiPolygon([geom])
            elif not isinstance(geom, MultiPolygon):
                self.stdout.write(
                    self.style.WARNING(f"  Skipping {name}: unsupported geometry type")
                )
                return False

            # Ensure valid
            if not geom.valid:
                geom = geom.buffer(0)

            # Ensure SRID is set to 4326 (WGS84)
            if not geom.srid:
                geom.srid = 4326

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  Error parsing geometry for {name}: {e}")
            )
            return False

        if dry_run:
            self.stdout.write(f"  Would load: {name} (pop: {population or 'N/A'})")
            return True

        # Calculate area in km²
        try:
            area_km2 = geom.transform(32643, clone=True).area / 1_000_000
        except Exception:
            area_km2 = None

        # Create or update province
        province, created = Province.objects.update_or_create(
            name=name,
            defaults={
                "geometry": geom,
                "population": population,
                "area_km2": area_km2,
            },
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"  {action}: {name}")
        return True
