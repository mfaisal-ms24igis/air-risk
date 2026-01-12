"""
Management command to fetch recent OpenAQ readings for active stations.

This command fetches the latest air quality data from OpenAQ API and stores
it in the PollutantReading table. It's designed for daily operational use.

Usage:
    python manage.py fetch_recent_readings
    python manage.py fetch_recent_readings --days 7
    python manage.py fetch_recent_readings --station-id 3089895
"""

import logging
from datetime import date, timedelta
from typing import Optional

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from air_quality.models import AirQualityStation, PollutantReading
from air_quality.services import get_openaq_client
from air_quality.constants import Pollutant


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch recent air quality readings from OpenAQ API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days to fetch (default: 7)",
        )
        parser.add_argument(
            "--station-id",
            type=int,
            help="Fetch for specific station only (OpenAQ location ID)",
        )
        parser.add_argument(
            "--parameters",
            type=str,
            nargs="+",
            default=["pm25", "pm10", "no2", "so2", "co", "o3"],
            help="Parameters to fetch (default: all pollutants)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=60,
            help="Maximum number of stations to process (default: 60)",
        )

    def handle(self, *args, **options):
        days = options["days"]
        station_id = options.get("station_id")
        parameters = options["parameters"]
        limit = options["limit"]

        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        self.stdout.write(
            f"\nFetching readings from {start_date} to {end_date}"
            f"\nParameters: {', '.join(parameters)}\n"
        )

        # Get stations to process
        if station_id:
            stations = AirQualityStation.objects.filter(
                openaq_location_id=station_id
            )
            if not stations.exists():
                self.stdout.write(
                    self.style.ERROR(f"Station {station_id} not found")
                )
                return
        else:
            # Get active stations with priority
            stations = AirQualityStation.objects.filter(
                is_active=True
            ).order_by("priority", "-total_readings")[:limit]

        total_stations = stations.count()
        if total_stations == 0:
            self.stdout.write(
                self.style.ERROR("No stations found. Run sync_stations first.")
            )
            return

        self.stdout.write(f"Processing {total_stations} stations\n")

        # Get OpenAQ client
        client = get_openaq_client()

        total_readings = 0
        stations_with_data = 0

        for i, station in enumerate(stations, 1):
            self.stdout.write(
                f"[{i}/{total_stations}] {station.name} (ID: {station.openaq_location_id})...",
                ending=""
            )

            try:
                # Fetch readings for this station
                readings = self._fetch_station_readings(
                    client, station, start_date, end_date, parameters
                )

                if readings:
                    count = self._save_readings(station, readings)
                    total_readings += count
                    stations_with_data += 1
                    self.stdout.write(self.style.SUCCESS(f" {count} readings"))

                    # Update station's last_reading_at
                    latest = max(r["timestamp"] for r in readings)
                    station.last_reading_at = latest
                    station.total_readings = (
                        station.total_readings + count
                        if station.total_readings else count
                    )
                    station.save(update_fields=["last_reading_at", "total_readings"])
                else:
                    self.stdout.write(" No data")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f" Error: {e}"))
                logger.exception(f"Error fetching readings for station {station.pk}")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nFetch complete!"
                f"\nTotal readings saved: {total_readings:,}"
                f"\nStations with data: {stations_with_data}/{total_stations}"
                f"\nDate range: {start_date} to {end_date}"
            )
        )

    def _fetch_station_readings(
        self,
        client,
        station: AirQualityStation,
        start_date: date,
        end_date: date,
        parameters: list[str],
    ) -> list[dict]:
        """
        Fetch readings for a single station from OpenAQ API.
        """
        try:
            # Use OpenAQ v3 API to get measurements via locations.sensors
            # Get sensors for this location
            sensors_response = client.client.locations.sensors(
                station.openaq_location_id
            )

            sensor_ids = []
            for sensor in sensors_response.results:
                # parameter is a dict with 'name' key
                param_data = sensor.parameter
                if isinstance(param_data, dict):
                    param_name = param_data.get('name', '').lower()
                else:
                    param_name = getattr(param_data, 'name', '').lower()
                
                # Match parameter names (handle pm2.5 -> pm25)
                param_normalized = param_name.replace(".", "")
                if param_normalized in parameters or param_name in parameters:
                    sensor_ids.append(sensor.id)

            if not sensor_ids:
                return []

            # Fetch measurements for each sensor
            readings = []
            for sensor_id in sensor_ids:
                try:
                    measurements = client.client.measurements.list(
                        sensors_id=sensor_id,
                        datetime_from=f"{start_date.isoformat()}T00:00:00Z",
                        datetime_to=f"{end_date.isoformat()}T23:59:59Z",
                        limit=1000
                    )

                    for m in measurements.results:
                        # Handle parameter as object with name attribute
                        param = getattr(m.parameter, 'name', '').upper()
                        unit = getattr(m.parameter, 'units', 'µg/m³')
                        
                        if param == "PM2.5":
                            param = "PM25"

                        # Datetime is in period.datetime_from.utc
                        try:
                            timestamp = m.period.datetime_from.utc
                            if isinstance(timestamp, str):
                                from datetime import datetime as dt
                                timestamp = dt.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except Exception:
                            continue

                        if timestamp and m.value is not None:
                            readings.append({
                                "timestamp": timestamp,
                                "parameter": param,
                                "value": m.value,
                                "unit": unit or "µg/m³",
                            })
                except Exception as sensor_error:
                    logger.debug(f"Error fetching sensor {sensor_id}: {sensor_error}")
                    continue

            return readings

        except Exception as e:
            logger.warning(f"Error fetching from OpenAQ API: {e}")
            return []

    def _save_readings(
        self,
        station: AirQualityStation,
        readings: list[dict],
    ) -> int:
        """
        Save readings to database.
        """
        readings_to_create = []
        seen = set()

        for reading in readings:
            timestamp = reading["timestamp"]
            parameter = reading["parameter"]
            value = reading["value"]
            unit = reading.get("unit", "µg/m³")

            # Skip invalid values
            if value is None or value < 0:
                continue

            # Skip duplicates within batch
            key = (station.pk, timestamp, parameter)
            if key in seen:
                continue
            seen.add(key)

            # Normalize parameter name
            try:
                pollutant = Pollutant.from_string(parameter)
                if pollutant:
                    parameter = pollutant.value
            except Exception:
                pass

            readings_to_create.append(
                PollutantReading(
                    station=station,
                    timestamp=timestamp,
                    parameter=parameter,
                    value=value,
                    unit=unit,
                    value_normalized=value,  # Assume µg/m³ for now
                    unit_normalized="µg/m³",
                    is_valid=True,
                )
            )

        # Bulk create with ignore_conflicts for duplicates
        if readings_to_create:
            with transaction.atomic():
                PollutantReading.objects.bulk_create(
                    readings_to_create,
                    ignore_conflicts=True,
                    batch_size=1000
                )

        return len(readings_to_create)
