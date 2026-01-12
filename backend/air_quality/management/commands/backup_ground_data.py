"""
Management command to backup existing GroundStation and GroundReading data.

Run this BEFORE any migration that modifies these models:
    python manage.py backup_ground_data

Creates a timestamped backup directory with JSON exports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from django.db.models import Count

from air_quality.models import GroundStation, GroundReading

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Export current GroundStation and GroundReading data to JSON backup files.
    
    Creates a timestamped directory with:
    - ground_stations.json: All station records with geometry
    - ground_readings.json: All reading records (chunked if large)
    - backup_metadata.json: Record counts and backup timestamp
    """
    
    help = "Backup GroundStation and GroundReading tables to JSON files"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--output-dir",
            type=str,
            default="backups",
            help="Base directory for backups (default: backups/)",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=10000,
            help="Number of readings per chunk file (default: 10000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be backed up without writing files",
        )

    def handle(self, *args, **options) -> None:
        output_dir = options["output_dir"]
        chunk_size = options["chunk_size"]
        dry_run = options["dry_run"]

        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = Path(output_dir) / f"ground_data_{timestamp}"

        # Gather statistics
        station_count = GroundStation.objects.count()
        reading_count = GroundReading.objects.count()
        
        # Station statistics
        stations_by_status = GroundStation.objects.values("is_active").annotate(
            count=Count("id")
        )
        active_count = sum(
            s["count"] for s in stations_by_status if s["is_active"]
        )
        inactive_count = sum(
            s["count"] for s in stations_by_status if not s["is_active"]
        )

        # Reading statistics by pollutant
        reading_stats = self._get_reading_stats()

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Ground Data Backup ===\n"))
        self.stdout.write(f"Backup directory: {backup_path}")
        self.stdout.write(f"Timestamp: {timestamp}\n")
        
        self.stdout.write(self.style.MIGRATE_LABEL("Stations:"))
        self.stdout.write(f"  Total: {station_count}")
        self.stdout.write(f"  Active: {active_count}")
        self.stdout.write(f"  Inactive: {inactive_count}\n")
        
        self.stdout.write(self.style.MIGRATE_LABEL("Readings:"))
        self.stdout.write(f"  Total: {reading_count}")
        for pollutant, count in reading_stats.items():
            self.stdout.write(f"  {pollutant}: {count}")
        self.stdout.write("")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No files written.\n"))
            return

        if station_count == 0 and reading_count == 0:
            self.stdout.write(
                self.style.WARNING("No data to backup. Tables are empty.")
            )
            return

        # Create backup directory
        backup_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"Created backup directory: {backup_path}\n")

        # Export stations
        self._export_stations(backup_path)
        
        # Export readings in chunks
        self._export_readings(backup_path, chunk_size)
        
        # Write metadata
        metadata = self._write_metadata(
            backup_path,
            timestamp,
            station_count,
            reading_count,
            reading_stats,
            chunk_size,
        )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Backup complete: {backup_path}")
        )
        self.stdout.write(f"  Metadata: {backup_path / 'backup_metadata.json'}")

    def _get_reading_stats(self) -> dict[str, int]:
        """Get reading counts by pollutant type."""
        stats = {}
        pollutants = ["no2", "so2", "pm25", "co", "o3"]
        
        for pollutant in pollutants:
            # Count non-null values for each pollutant field
            filter_kwargs = {f"{pollutant}__isnull": False}
            count = GroundReading.objects.filter(**filter_kwargs).count()
            if count > 0:
                stats[pollutant.upper()] = count
        
        return stats

    def _export_stations(self, backup_path: Path) -> None:
        """Export all GroundStation records to JSON."""
        self.stdout.write("Exporting stations...", ending=" ")
        
        stations = GroundStation.objects.all()
        
        # Custom serialization to handle geometry
        station_data = []
        for station in stations:
            station_data.append({
                "id": station.id,
                "openaq_id": station.openaq_id,
                "openaq_location_id": station.openaq_location_id,
                "name": station.name,
                "location": {
                    "type": "Point",
                    "coordinates": [station.location.x, station.location.y]
                } if station.location else None,
                "district_id": station.district_id,
                "city": station.city,
                "country": station.country,
                "available_parameters": station.available_parameters,
                "is_active": station.is_active,
                "last_updated": station.last_updated.isoformat() if station.last_updated else None,
                "created_at": station.created_at.isoformat() if station.created_at else None,
                "updated_at": station.updated_at.isoformat() if station.updated_at else None,
            })
        
        output_file = backup_path / "ground_stations.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(station_data, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(self.style.SUCCESS(f"✓ {len(station_data)} stations"))

    def _export_readings(self, backup_path: Path, chunk_size: int) -> None:
        """Export GroundReading records to JSON, chunked for large datasets."""
        total_readings = GroundReading.objects.count()
        
        if total_readings == 0:
            self.stdout.write("No readings to export.")
            return
        
        self.stdout.write(f"Exporting {total_readings} readings...")
        
        # Process in chunks to avoid memory issues
        chunk_num = 0
        exported = 0
        
        readings_qs = GroundReading.objects.select_related("station").order_by("id")
        
        while exported < total_readings:
            chunk = readings_qs[exported:exported + chunk_size]
            chunk_data = []
            
            for reading in chunk:
                chunk_data.append({
                    "id": reading.id,
                    "station_id": reading.station_id,
                    "station_openaq_id": reading.station.openaq_id if reading.station else None,
                    "timestamp": reading.timestamp.isoformat() if reading.timestamp else None,
                    "no2": reading.no2,
                    "so2": reading.so2,
                    "pm25": reading.pm25,
                    "co": reading.co,
                    "o3": reading.o3,
                    "raw_data": reading.raw_data,
                    "created_at": reading.created_at.isoformat() if reading.created_at else None,
                })
            
            # Write chunk file
            chunk_file = backup_path / f"ground_readings_{chunk_num:04d}.json"
            with open(chunk_file, "w", encoding="utf-8") as f:
                json.dump(chunk_data, f, indent=2, ensure_ascii=False)
            
            exported += len(chunk_data)
            chunk_num += 1
            
            self.stdout.write(
                f"  Chunk {chunk_num}: {len(chunk_data)} readings "
                f"({exported}/{total_readings})"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f"✓ Exported {exported} readings in {chunk_num} chunks")
        )

    def _write_metadata(
        self,
        backup_path: Path,
        timestamp: str,
        station_count: int,
        reading_count: int,
        reading_stats: dict[str, int],
        chunk_size: int,
    ) -> dict[str, Any]:
        """Write backup metadata file."""
        metadata = {
            "backup_timestamp": timestamp,
            "backup_created_at": datetime.now().isoformat(),
            "django_app": "air_quality",
            "models_backed_up": ["GroundStation", "GroundReading"],
            "statistics": {
                "station_count": station_count,
                "reading_count": reading_count,
                "readings_by_pollutant": reading_stats,
            },
            "settings": {
                "chunk_size": chunk_size,
            },
            "files": {
                "stations": "ground_stations.json",
                "readings_pattern": "ground_readings_*.json",
            },
            "restore_notes": [
                "This backup was created before schema migration.",
                "Station geometry is stored as GeoJSON Point.",
                "Readings are chunked into multiple files for large datasets.",
                "To restore, use a custom management command or Django shell.",
            ],
        }
        
        metadata_file = backup_path / "backup_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        return metadata
