"""
Management command to link air quality stations to their districts.

Uses PostGIS spatial queries to find which district polygon contains each station point.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.db import transaction

from air_quality.models import AirQualityStation, District


class Command(BaseCommand):
    help = "Link air quality stations to districts based on their coordinates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-link all stations, even those already assigned",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(self.style.NOTICE("Linking stations to districts..."))

        # Get stations to process
        if force:
            stations = AirQualityStation.objects.all()
            self.stdout.write(f"Processing all {stations.count()} stations (force mode)")
        else:
            stations = AirQualityStation.objects.filter(district__isnull=True)
            self.stdout.write(f"Processing {stations.count()} unlinked stations")

        linked_count = 0
        not_found_count = 0
        errors = []

        with transaction.atomic():
            for station in stations:
                try:
                    # Create point from station coordinates
                    if station.location:
                        point = station.location
                    else:
                        point = Point(station.longitude, station.latitude, srid=4326)

                    # Find district that contains this point
                    district = District.objects.filter(
                        geometry__contains=point
                    ).first()

                    if district:
                        if not dry_run:
                            station.district = district
                            # Also update location if not set
                            if not station.location:
                                station.location = point
                            station.save(update_fields=["district", "location"])
                        
                        linked_count += 1
                        self.stdout.write(
                            f"  ✓ {station.name} → {district.name}, {district.province}"
                        )
                    else:
                        not_found_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ✗ {station.name} ({station.latitude}, {station.longitude}) "
                                f"- No district found"
                            )
                        )

                except Exception as e:
                    errors.append((station.name, str(e)))
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ {station.name} - Error: {e}")
                    )

            if dry_run:
                # Rollback in dry-run mode
                transaction.set_rollback(True)

        # Summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        
        self.stdout.write(f"Linked: {linked_count}")
        self.stdout.write(f"Not found: {not_found_count}")
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))

        self.stdout.write(self.style.SUCCESS("Done!"))
