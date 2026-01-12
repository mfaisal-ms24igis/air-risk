"""
Management command to backfill historical OpenAQ data for GWR training.
"""

import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction

from air_quality.services import get_openaq_client
from air_quality.models import GroundStation, GroundReading

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Backfill historical OpenAQ readings for Pakistan stations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=2024,
            help="Year to backfill (default: 2024)",
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date (YYYY-MM-DD). Overrides --year.",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="End date (YYYY-MM-DD). Defaults to today or end of year.",
        )
        parser.add_argument(
            "--parameters",
            type=str,
            nargs="+",
            default=["NO2", "SO2", "PM25", "CO", "O3"],
            help="Pollutants to fetch (default: all)",
        )
        parser.add_argument(
            "--batch-days",
            type=int,
            default=7,
            help="Number of days to fetch per batch (default: 7)",
        )
        parser.add_argument(
            "--sync-stations",
            action="store_true",
            help="Sync stations from OpenAQ before backfilling",
        )

    def handle(self, *args, **options):
        client = get_openaq_client()

        # Sync stations if requested
        if options["sync_stations"]:
            self.stdout.write("Syncing stations from OpenAQ...")
            created, updated = client.sync_stations()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Synced {created + updated} stations ({created} created, {updated} updated)"
                )
            )

        # Determine date range
        if options["start_date"]:
            start_date = date.fromisoformat(options["start_date"])
        else:
            year = options["year"]
            start_date = date(year, 1, 1)

        if options["end_date"]:
            end_date = date.fromisoformat(options["end_date"])
        elif options["start_date"]:
            end_date = date.today()
        else:
            year = options["year"]
            end_date = date(year, 12, 31)
            if end_date > date.today():
                end_date = date.today()

        parameters = options["parameters"]
        batch_days = options["batch_days"]

        self.stdout.write(
            f"\nBackfilling data from {start_date} to {end_date}"
            f"\nParameters: {', '.join(parameters)}"
            f"\nBatch size: {batch_days} days\n"
        )

        # Get all active stations
        stations = GroundStation.objects.filter(is_active=True, country="Pakistan")
        total_stations = stations.count()

        if total_stations == 0:
            self.stdout.write(
                self.style.ERROR(
                    "No active stations found. Run with --sync-stations first."
                )
            )
            return

        self.stdout.write(f"Processing {total_stations} stations\n")

        # Process in batches by date range
        current_date = start_date
        total_readings = 0
        total_batches = 0

        while current_date <= end_date:
            batch_end = min(current_date + timedelta(days=batch_days - 1), end_date)
            total_batches += 1

            self.stdout.write(
                f"\n[Batch {total_batches}] Fetching {current_date} to {batch_end}..."
            )

            try:
                # Fetch readings for all stations in this date range
                batch_readings = 0

                for param in parameters:
                    self.stdout.write(f"  Fetching {param}...", ending="")

                    # Get all station OpenAQ IDs
                    station_ids = list(
                        stations.filter(
                            available_parameters__contains=[param]
                        ).values_list("openaq_location_id", flat=True)
                    )

                    if not station_ids:
                        self.stdout.write(" No stations")
                        continue

                    # Fetch readings from OpenAQ
                    readings_data = client.fetch_readings(
                        start_date=current_date,
                        end_date=batch_end,
                        station_ids=station_ids,
                        parameters=[param],
                    )

                    # Bulk create readings
                    if readings_data:
                        count = self._save_readings(readings_data)
                        batch_readings += count
                        self.stdout.write(f" {count} readings")
                    else:
                        self.stdout.write(" 0 readings")

                total_readings += batch_readings
                self.stdout.write(
                    self.style.SUCCESS(f"  Batch total: {batch_readings} readings")
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  Error: {e}"))
                logger.exception(f"Error fetching batch {current_date} to {batch_end}")

            current_date = batch_end + timedelta(days=1)

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nBackfill complete!"
                f"\nTotal readings saved: {total_readings:,}"
                f"\nDate range: {start_date} to {end_date}"
                f"\nStations: {total_stations}"
                f"\nBatches processed: {total_batches}"
            )
        )

    def _save_readings(self, readings_data: list[dict]) -> int:
        """
        Save readings to database in bulk.

        Returns:
            Number of readings saved
        """
        from django.contrib.gis.geos import Point

        readings_to_create = []

        for reading in readings_data:
            # Get station
            station_id = reading.get("location_id")
            try:
                station = GroundStation.objects.get(openaq_location_id=station_id)
            except GroundStation.DoesNotExist:
                continue

            # Parse datetime
            datetime_str = reading.get("datetime_utc")
            if not datetime_str:
                continue

            try:
                reading_time = (
                    datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
                    .astimezone()
                    .replace(tzinfo=None)
                )
            except (ValueError, AttributeError):
                continue

            # Get pollutant and value
            parameter = reading.get("parameter", "").upper()
            if parameter == "PM2.5":
                parameter = "PM25"

            value = reading.get("value")
            if value is None or value < 0:
                continue

            # Create reading object
            readings_to_create.append(
                GroundReading(
                    station=station,
                    pollutant=parameter,
                    value=value,
                    unit=reading.get("unit", "µg/m³"),
                    timestamp=reading_time,
                )
            )

        # Bulk create with ignore_conflicts to skip duplicates
        if readings_to_create:
            with transaction.atomic():
                GroundReading.objects.bulk_create(
                    readings_to_create, ignore_conflicts=True, batch_size=1000
                )

        return len(readings_to_create)
