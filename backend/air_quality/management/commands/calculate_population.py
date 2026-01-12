#!/usr/bin/env python
"""
Management command to calculate population totals for districts and provinces
using WorldPop raster data via zonal statistics.
"""

import json
import logging
from pathlib import Path

import rasterstats
from django.core.management.base import BaseCommand
from django.conf import settings

from air_quality.models import District, Province

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Calculate population totals for districts and provinces using WorldPop data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--worldpop-path",
            type=str,
            help="Path to WorldPop TIFF file (default: from settings)",
        )
        parser.add_argument(
            "--districts-only",
            action="store_true",
            help="Only update districts",
        )
        parser.add_argument(
            "--provinces-only",
            action="store_true",
            help="Only update provinces",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving",
        )

    def handle(self, *args, **options):
        worldpop_path = options.get("worldpop_path")
        districts_only = options.get("districts_only")
        provinces_only = options.get("provinces_only")
        dry_run = options.get("dry_run")

        if worldpop_path:
            worldpop_path = Path(worldpop_path)
        else:
            worldpop_path = Path(settings.WORLDPOP_DATA_PATH) / "pak_pop_2025_CN_1km_R2025A_UA_v1.tif"

        if not worldpop_path.exists():
            self.stderr.write(
                self.style.ERROR(f"WorldPop file not found: {worldpop_path}")
            )
            return

        self.stdout.write(f"Using WorldPop file: {worldpop_path}")

        # Process districts
        if not provinces_only:
            self._process_districts(worldpop_path, dry_run)

        # Process provinces
        if not districts_only:
            self._process_provinces(worldpop_path, dry_run)

    def _process_districts(self, worldpop_path: Path, dry_run: bool):
        """Calculate population for districts."""
        self.stdout.write("\n📊 Processing districts...")

        districts = District.objects.filter(geometry__isnull=False)
        if not districts.exists():
            self.stdout.write(self.style.WARNING("No districts with geometry found"))
            return

        self.stdout.write(f"Found {districts.count()} districts with geometry")

        updated = 0
        errors = 0

        for district in districts:
            try:
                # Calculate zonal statistics
                stats = rasterstats.zonal_stats(
                    json.loads(district.geometry.geojson),
                    str(worldpop_path),
                    stats=['sum'],
                    nodata=-99999.0
                )

                if stats and len(stats) > 0:
                    population = stats[0]['sum']
                    if population and population > 0:
                        if dry_run:
                            self.stdout.write(
                                f"  Would update {district.name}: {population:,.0f} people"
                            )
                        else:
                            district.population = population
                            district.save(update_fields=['population'])
                            self.stdout.write(
                                f"  ✓ {district.name}: {population:,.0f} people"
                            )
                        updated += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ {district.name}: No population data")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ {district.name}: No stats calculated")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {district.name}: {e}")
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Districts: {updated} updated, {errors} errors"
            )
        )

    def _process_provinces(self, worldpop_path: Path, dry_run: bool):
        """Calculate population for provinces."""
        self.stdout.write("\n🏛️ Processing provinces...")

        provinces = Province.objects.filter(geometry__isnull=False)
        if not provinces.exists():
            self.stdout.write(self.style.WARNING("No provinces with geometry found"))
            return

        self.stdout.write(f"Found {provinces.count()} provinces with geometry")

        updated = 0
        errors = 0

        for province in provinces:
            try:
                # Calculate zonal statistics
                stats = rasterstats.zonal_stats(
                    json.loads(province.geometry.geojson),
                    str(worldpop_path),
                    stats=['sum'],
                    nodata=-99999.0
                )

                if stats and len(stats) > 0:
                    population = stats[0]['sum']
                    if population and population > 0:
                        if dry_run:
                            self.stdout.write(
                                f"  Would update {province.name}: {population:,.0f} people"
                            )
                        else:
                            province.population = population
                            province.save(update_fields=['population'])
                            self.stdout.write(
                                f"  ✓ {province.name}: {population:,.0f} people"
                            )
                        updated += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ {province.name}: No population data")
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ {province.name}: No stats calculated")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {province.name}: {e}")
                )
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Provinces: {updated} updated, {errors} errors"
            )
        )