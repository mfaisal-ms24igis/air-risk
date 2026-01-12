"""
Django management command to process WorldPop data and populate population fields.
"""

import os
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.contrib.gis.db.models.functions import Transform
from django.db import transaction

try:
    import rasterio
    from rasterio.mask import mask
    from rasterstats import zonal_stats
    import numpy as np
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

from air_quality.models import District, Province
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process WorldPop raster and populate population data for districts and provinces"

    def add_arguments(self, parser):
        parser.add_argument(
            "--worldpop-file",
            type=str,
            default=None,
            help="Path to WorldPop TIFF file (default: auto-detect from WORLDPOP_DATA_PATH)"
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing population data"
        )
        parser.add_argument(
            "--districts-only",
            action="store_true",
            help="Only process districts, skip provinces"
        )
        parser.add_argument(
            "--provinces-only",
            action="store_true",
            help="Only process provinces, skip districts"
        )

    def handle(self, *args, **options):
        if not RASTERIO_AVAILABLE:
            self.stderr.write(
                self.style.ERROR(
                    "rasterio and rasterstats required. Install with: pip install rasterio rasterstats"
                )
            )
            return

        worldpop_file = options["worldpop_file"]
        overwrite = options["overwrite"]
        districts_only = options["districts_only"]
        provinces_only = options["provinces_only"]

        # Find WorldPop file
        if not worldpop_file:
            worldpop_path = Path(settings.WORLDPOP_DATA_PATH)
            tif_files = list(worldpop_path.glob("*.tif"))
            if not tif_files:
                self.stderr.write(
                    self.style.ERROR(f"No TIFF files found in {worldpop_path}")
                )
                return
            worldpop_file = str(tif_files[0])  # Use first TIFF file
            self.stdout.write(f"Using WorldPop file: {worldpop_file}")

        if not os.path.exists(worldpop_file):
            self.stderr.write(
                self.style.ERROR(f"WorldPop file not found: {worldpop_file}")
            )
            return

        # Process districts
        if not provinces_only:
            self.stdout.write("\n🏙️  Processing districts...")
            self._process_geometries(District, worldpop_file, overwrite)

        # Process provinces
        if not districts_only:
            self.stdout.write("\n🏛️  Processing provinces...")
            self._process_geometries(Province, worldpop_file, overwrite)

        self.stdout.write(
            self.style.SUCCESS("\n✅ WorldPop population data processing complete!")
        )

    def _process_geometries(self, model_class, worldpop_file, overwrite):
        """Process population data for a geometry model (District or Province)."""
        queryset = model_class.objects.all()

        if queryset.count() == 0:
            self.stdout.write(f"  No {model_class.__name__.lower()}s found to process")
            return

        processed = 0
        skipped = 0
        errors = 0

        with rasterio.open(worldpop_file) as src:
            self.stdout.write(f"  WorldPop raster CRS: {src.crs}")
            self.stdout.write(f"  WorldPop raster bounds: {src.bounds}")

            for geom_obj in queryset:
                try:
                    # Skip if population already exists and not overwriting
                    if geom_obj.population is not None and not overwrite:
                        self.stdout.write(f"  Skipping {geom_obj}: population already exists")
                        skipped += 1
                        continue

                    # Transform geometry to match raster CRS if needed
                    geom = geom_obj.geometry
                    if geom.srid != 4326:
                        geom = geom.transform(4326, clone=True)

                    # Calculate zonal statistics
                    stats = zonal_stats(
                        geom,
                        worldpop_file,
                        stats=['sum'],
                        nodata=src.nodata
                    )

                    if stats and len(stats) > 0 and stats[0]['sum'] is not None:
                        population = int(stats[0]['sum'])
                        geom_obj.population = population
                        geom_obj.save(update_fields=['population'])

                        self.stdout.write(f"  ✅ {geom_obj}: {population:,} population")
                        processed += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠️  {geom_obj}: no population data")
                        )
                        skipped += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ {geom_obj}: {e}")
                    )
                    errors += 1

        self.stdout.write(
            f"  📊 {model_class.__name__} summary: {processed} processed, {skipped} skipped, {errors} errors"
        )