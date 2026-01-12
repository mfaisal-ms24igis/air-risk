"""
Management command to ingest OpenAQ bulk data into the database.

This command reads gzipped CSV files from the openaq_bulk_data directory,
normalizes units, validates data, and bulk inserts into the PollutantReading table.

Usage:
    python manage.py ingest_openaq
    python manage.py ingest_openaq --station-ids 8664 8088 --limit 10
    python manage.py ingest_openaq --active-only --batch-size 5000

Prerequisites:
    1. Run analyze_openaq_data first to understand data quality
    2. Run sync_stations to create station records
    3. Run makemigrations && migrate for new models
"""

import csv
import gzip
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from air_quality.models import (
    AirQualityStation,
    PollutantReading,
    DataIngestionLog,
)
from air_quality.constants import (
    Pollutant,
    UnitType,
    POLLUTANT_VALUE_RANGES,
)
from air_quality.services.unit_converter import (
    UnitConverter,
    UnitConversionError,
    get_unit_converter,
)


logger = logging.getLogger(__name__)


class OpenAQIngester:
    """
    Ingests OpenAQ bulk CSV data into the database.
    
    Features:
    - Reads gzipped CSV files
    - Normalizes units to standard (µg/m³)
    - Validates values and coordinates
    - Bulk creates readings for performance
    - Logs errors for debugging
    """

    def __init__(
        self,
        data_dir: Path,
        error_log_path: Path,
        batch_size: int = 5000,
    ) -> None:
        """
        Initialize the ingester.
        
        Args:
            data_dir: Path to openaq_bulk_data directory.
            error_log_path: Path to write error log.
            batch_size: Number of records per bulk_create batch.
        """
        self.data_dir = data_dir
        self.error_log_path = error_log_path
        self.batch_size = batch_size
        
        self.converter = get_unit_converter()
        
        # Statistics
        self.files_processed = 0
        self.rows_total = 0
        self.rows_created = 0
        self.rows_skipped = 0
        self.rows_invalid = 0
        self.rows_duplicate = 0
        
        # Station cache
        self._station_cache: Dict[int, AirQualityStation] = {}
        
        # Error log handle
        self._error_file = None
        
        # Track seen records to detect duplicates within batch
        self._seen_in_batch: Set[tuple] = set()

    def ingest(
        self,
        station_ids: Optional[List[int]] = None,
        active_only: bool = False,
        limit: Optional[int] = None,
    ) -> DataIngestionLog:
        """
        Run the ingestion process.
        
        Args:
            station_ids: Specific station IDs to process (None = all).
            active_only: Only process active stations.
            limit: Maximum number of stations to process.
            
        Returns:
            DataIngestionLog record with statistics.
        """
        # Create ingestion log
        log = DataIngestionLog.objects.create(
            source_type="openaq_bulk",
            source_path=str(self.data_dir),
            status=DataIngestionLog.IngestionStatus.RUNNING,
            command_args={
                "station_ids": station_ids,
                "active_only": active_only,
                "limit": limit,
                "batch_size": self.batch_size,
            },
        )
        
        # Open error log
        self._error_file = open(self.error_log_path, "w", encoding="utf-8")
        self._write_error_header()
        
        try:
            # Build station cache
            self._build_station_cache(station_ids, active_only)
            
            if not self._station_cache:
                self._log_error("No stations found matching criteria")
                log.error_summary = "No stations found"
                log.status = DataIngestionLog.IngestionStatus.FAILED
                log.save()
                return log
            
            # Get stations to process
            stations_to_process = list(self._station_cache.values())
            if limit:
                stations_to_process = stations_to_process[:limit]
            
            logger.info(f"Processing {len(stations_to_process)} stations")
            log.stations_processed = len(stations_to_process)
            
            # Process each station
            for i, station in enumerate(stations_to_process, 1):
                logger.info(
                    f"[{i}/{len(stations_to_process)}] Processing station: "
                    f"{station.name} (ID: {station.openaq_location_id})"
                )
                self._process_station(station)
            
            # Update log with final stats
            log.files_processed = self.files_processed
            log.records_total = self.rows_total
            log.records_created = self.rows_created
            log.records_skipped = self.rows_skipped
            log.records_invalid = self.rows_invalid
            log.error_count = self.rows_invalid + self.rows_duplicate
            log.error_log_path = str(self.error_log_path)
            log.error_summary = (
                f"Skipped: {self.rows_skipped}, "
                f"Invalid: {self.rows_invalid}, "
                f"Duplicates: {self.rows_duplicate}"
            )
            log.mark_completed()
            
        except Exception as e:
            logger.exception("Ingestion failed")
            log.status = DataIngestionLog.IngestionStatus.FAILED
            log.error_summary = str(e)
            log.save()
            raise
            
        finally:
            if self._error_file:
                self._error_file.write(
                    f"\n\nTotal errors: {self.rows_invalid + self.rows_duplicate}\n"
                )
                self._error_file.close()
                self._error_file = None
        
        return log

    def _build_station_cache(
        self,
        station_ids: Optional[List[int]],
        active_only: bool,
    ) -> None:
        """Build cache of station records for quick lookup."""
        queryset = AirQualityStation.objects.all()
        
        if station_ids:
            queryset = queryset.filter(openaq_location_id__in=station_ids)
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        for station in queryset:
            self._station_cache[station.openaq_location_id] = station
        
        logger.info(f"Cached {len(self._station_cache)} stations")

    def _process_station(self, station: AirQualityStation) -> None:
        """
        Process all data files for a station.
        
        Args:
            station: Station record to process.
        """
        location_id = station.openaq_location_id
        station_dir = self.data_dir / f"location_{location_id}"
        
        if not station_dir.exists():
            logger.warning(f"No data directory for station {location_id}")
            return
        
        # Find all CSV.GZ files
        csv_files = list(station_dir.rglob("*.csv.gz"))
        
        if not csv_files:
            logger.warning(f"No CSV files for station {location_id}")
            return
        
        logger.info(f"  Found {len(csv_files)} files")
        
        # Collect readings for bulk insert
        readings_batch: List[PollutantReading] = []
        self._seen_in_batch.clear()
        
        for csv_path in csv_files:
            self.files_processed += 1
            readings = self._process_file(csv_path, station)
            readings_batch.extend(readings)
            
            # Bulk insert when batch is full
            if len(readings_batch) >= self.batch_size:
                self._bulk_insert(readings_batch)
                readings_batch.clear()
                self._seen_in_batch.clear()
        
        # Insert remaining readings
        if readings_batch:
            self._bulk_insert(readings_batch)
        
        # Update station stats
        station.total_readings = PollutantReading.objects.filter(station=station).count()
        last_reading = PollutantReading.objects.filter(station=station).order_by("-timestamp").first()
        if last_reading:
            station.last_reading_at = last_reading.timestamp
        station.save(update_fields=["total_readings", "last_reading_at"])

    def _process_file(
        self,
        csv_path: Path,
        station: AirQualityStation,
    ) -> List[PollutantReading]:
        """
        Process a single CSV.GZ file.
        
        Args:
            csv_path: Path to gzipped CSV file.
            station: Station record.
            
        Returns:
            List of PollutantReading objects (not yet saved).
        """
        readings = []
        
        try:
            with gzip.open(csv_path, "rt", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    self.rows_total += 1
                    
                    reading = self._process_row(row, station, csv_path.name)
                    if reading:
                        readings.append(reading)
                        
        except Exception as e:
            self._log_error(f"Failed to read {csv_path}: {e}")
        
        return readings

    def _process_row(
        self,
        row: Dict[str, str],
        station: AirQualityStation,
        source_file: str,
    ) -> Optional[PollutantReading]:
        """
        Process a single CSV row.
        
        Args:
            row: CSV row dictionary.
            station: Station record.
            source_file: Source filename for error reporting.
            
        Returns:
            PollutantReading object or None if invalid.
        """
        # Extract fields
        parameter = row.get("parameter", "").strip().lower()
        value_str = row.get("value", "").strip()
        unit = row.get("unit", "").strip()
        timestamp_str = row.get("datetime", row.get("datetime_utc", "")).strip()
        
        # Skip if missing required fields
        if not all([parameter, value_str, timestamp_str]):
            self.rows_skipped += 1
            return None
        
        # Parse pollutant
        pollutant = Pollutant.from_string(parameter)
        if pollutant is None:
            # Skip non-pollutant parameters (temperature, humidity, etc.)
            self.rows_skipped += 1
            return None
        
        # Parse timestamp
        try:
            # Handle various ISO formats
            timestamp_str = timestamp_str.replace("Z", "+00:00")
            if "+" not in timestamp_str and "-" not in timestamp_str[-6:]:
                timestamp_str += "+00:00"
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError as e:
            self._log_error(f"Invalid timestamp '{timestamp_str}' in {source_file}: {e}")
            self.rows_invalid += 1
            return None
        
        # Parse value
        try:
            value = float(value_str)
        except ValueError:
            self._log_error(f"Invalid value '{value_str}' in {source_file}")
            self.rows_invalid += 1
            return None
        
        # Check for duplicates within this batch
        record_key = (station.id, timestamp.isoformat(), pollutant.value)
        if record_key in self._seen_in_batch:
            self.rows_duplicate += 1
            return None
        self._seen_in_batch.add(record_key)
        
        # Parse unit
        unit_type = UnitType.from_string(unit)
        if unit_type is None:
            # Use default unit for pollutant
            unit_type = UnitType.UG_M3
            self._log_error(
                f"Unknown unit '{unit}' for {parameter} in {source_file}, "
                f"assuming {unit_type.value}"
            )
        
        # Normalize value
        value_normalized = None
        unit_normalized = ""
        validation_flags = []
        
        try:
            value_normalized, norm_unit = self.converter.normalize_to_standard(
                value, unit, parameter
            )
            unit_normalized = norm_unit.value
        except UnitConversionError as e:
            self._log_error(f"Unit conversion failed for {parameter}: {e}")
            validation_flags.append("conversion_failed")
        
        # Validate value range
        is_valid = True
        
        if value < 0:
            validation_flags.append("negative_value")
            is_valid = False
        
        if pollutant in POLLUTANT_VALUE_RANGES:
            min_val, max_val = POLLUTANT_VALUE_RANGES[pollutant]
            check_val = value_normalized if value_normalized is not None else value
            if check_val < min_val or check_val > max_val:
                validation_flags.append("out_of_range")
                # Still valid, just flagged
        
        # Create reading object (not saved yet)
        reading = PollutantReading(
            station=station,
            timestamp=timestamp,
            parameter=pollutant.value,
            value=value,
            unit=unit_type.value,
            value_normalized=value_normalized,
            unit_normalized=unit_normalized,
            is_valid=is_valid,
            validation_flags=validation_flags if validation_flags else [],
            raw_data={
                "source_file": source_file,
                "original_unit": unit,
            },
        )
        
        return reading

    def _bulk_insert(self, readings: List[PollutantReading]) -> None:
        """
        Bulk insert readings, ignoring duplicates.
        
        Args:
            readings: List of PollutantReading objects.
        """
        if not readings:
            return
        
        try:
            created = PollutantReading.objects.bulk_create(
                readings,
                ignore_conflicts=True,
                batch_size=self.batch_size,
            )
            
            # bulk_create with ignore_conflicts doesn't return count on all DBs
            # so we count what we tried to insert
            self.rows_created += len(readings)
            
        except Exception as e:
            self._log_error(f"Bulk insert failed: {e}")
            # Try individual inserts as fallback
            for reading in readings:
                try:
                    reading.save()
                    self.rows_created += 1
                except Exception:
                    self.rows_duplicate += 1

    def _write_error_header(self) -> None:
        """Write header to error log file."""
        if self._error_file:
            self._error_file.write("OpenAQ Ingestion Error Log\n")
            self._error_file.write(f"Generated: {datetime.now().isoformat()}\n")
            self._error_file.write(f"Data directory: {self.data_dir}\n")
            self._error_file.write("=" * 80 + "\n\n")

    def _log_error(self, message: str) -> None:
        """Write error message to log file."""
        if self._error_file:
            self._error_file.write(f"{datetime.now().isoformat()} | {message}\n")


class Command(BaseCommand):
    """
    Django management command to ingest OpenAQ bulk data.
    
    Usage:
        python manage.py ingest_openaq
        python manage.py ingest_openaq --active-only
        python manage.py ingest_openaq --station-ids 8664 8088
        python manage.py ingest_openaq --limit 10 --batch-size 1000
    """
    
    help = "Ingest OpenAQ bulk data from CSV.GZ files into PollutantReading table"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--data-dir",
            type=str,
            default="openaq_bulk_data",
            help="Path to OpenAQ bulk data directory (default: openaq_bulk_data/)",
        )
        parser.add_argument(
            "--error-log",
            type=str,
            default="data_errors.log",
            help="Path to error log file (default: data_errors.log)",
        )
        parser.add_argument(
            "--station-ids",
            type=int,
            nargs="+",
            help="Specific station IDs to process",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            help="Only process active stations",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of stations to process",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5000,
            help="Records per bulk insert batch (default: 5000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options) -> None:
        data_dir = Path(options["data_dir"])
        error_log = Path(options["error_log"])
        station_ids = options.get("station_ids")
        active_only = options["active_only"]
        limit = options.get("limit")
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]
        
        if not data_dir.exists():
            self.stderr.write(
                self.style.ERROR(f"Data directory not found: {data_dir}")
            )
            return
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== OpenAQ Data Ingestion ===\n"))
        self.stdout.write(f"Data directory: {data_dir}")
        self.stdout.write(f"Error log: {error_log}")
        self.stdout.write(f"Batch size: {batch_size}")
        
        if station_ids:
            self.stdout.write(f"Station IDs: {station_ids}")
        if active_only:
            self.stdout.write("Mode: Active stations only")
        if limit:
            self.stdout.write(f"Limit: {limit} stations")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN MODE]"))
            self._dry_run(data_dir, station_ids, active_only, limit)
            return
        
        # Check prerequisites
        station_count = AirQualityStation.objects.count()
        if station_count == 0:
            self.stderr.write(
                self.style.ERROR(
                    "No stations in database. Run 'python manage.py sync_stations' first."
                )
            )
            return
        
        self.stdout.write(f"\nStations in database: {station_count}")
        
        if active_only:
            active_count = AirQualityStation.objects.filter(is_active=True).count()
            self.stdout.write(f"Active stations: {active_count}")
        
        self.stdout.write("\nStarting ingestion...\n")
        
        # Run ingestion
        ingester = OpenAQIngester(data_dir, error_log, batch_size)
        
        try:
            log = ingester.ingest(
                station_ids=station_ids,
                active_only=active_only,
                limit=limit,
            )
            
            # Print results
            self._print_results(log)
            
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\nIngestion failed: {e}"))
            raise

    def _dry_run(
        self,
        data_dir: Path,
        station_ids: Optional[List[int]],
        active_only: bool,
        limit: Optional[int],
    ) -> None:
        """Show what would be processed in dry run mode."""
        # Get stations
        queryset = AirQualityStation.objects.all()
        
        if station_ids:
            queryset = queryset.filter(openaq_location_id__in=station_ids)
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        stations = list(queryset)
        if limit:
            stations = stations[:limit]
        
        self.stdout.write(f"\nWould process {len(stations)} stations:")
        
        total_files = 0
        for station in stations[:10]:  # Show first 10
            station_dir = data_dir / f"location_{station.openaq_location_id}"
            if station_dir.exists():
                file_count = len(list(station_dir.rglob("*.csv.gz")))
                total_files += file_count
                self.stdout.write(
                    f"  {station.name} (ID: {station.openaq_location_id}): {file_count} files"
                )
        
        if len(stations) > 10:
            self.stdout.write(f"  ... and {len(stations) - 10} more stations")
            # Count remaining files
            for station in stations[10:]:
                station_dir = data_dir / f"location_{station.openaq_location_id}"
                if station_dir.exists():
                    total_files += len(list(station_dir.rglob("*.csv.gz")))
        
        self.stdout.write(f"\nTotal files to process: {total_files}")

    def _print_results(self, log: DataIngestionLog) -> None:
        """Print ingestion results summary."""
        self.stdout.write(self.style.MIGRATE_LABEL("\n📊 Ingestion Results:"))
        self.stdout.write(f"  Status: {log.status}")
        self.stdout.write(f"  Duration: {log.duration_seconds:.1f} seconds")
        self.stdout.write(f"  Stations processed: {log.stations_processed}")
        self.stdout.write(f"  Files processed: {log.files_processed}")
        self.stdout.write(f"  Total rows: {log.records_total:,}")
        self.stdout.write(f"  Records created: {log.records_created:,}")
        self.stdout.write(f"  Records skipped: {log.records_skipped:,}")
        self.stdout.write(f"  Records invalid: {log.records_invalid:,}")
        
        if log.error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"  Errors: {log.error_count:,}")
            )
            self.stdout.write(f"  Error log: {log.error_log_path}")
        
        self.stdout.write(f"\n  Success rate: {log.success_rate:.1f}%")
        
        if log.status == DataIngestionLog.IngestionStatus.COMPLETED:
            self.stdout.write(self.style.SUCCESS("\n✓ Ingestion completed successfully!"))
        elif log.status == DataIngestionLog.IngestionStatus.PARTIAL:
            self.stdout.write(
                self.style.WARNING("\n⚠ Ingestion completed with some errors")
            )
        else:
            self.stdout.write(self.style.ERROR("\n✗ Ingestion failed"))
