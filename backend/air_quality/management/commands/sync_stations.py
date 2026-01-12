"""
Management command to sync stations from pakistan_stations.csv.

This command reads the station metadata CSV and creates/updates AirQualityStation
records, ranking stations by data richness and activating the top 60.

Usage:
    python manage.py sync_stations
    python manage.py sync_stations --csv pakistan_stations.csv --activate-top 60
    python manage.py sync_stations --from-ranking station_ranking.csv
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from air_quality.models import AirQualityStation
from air_quality.constants import MAX_ACTIVE_STATIONS


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Sync air quality stations from CSV metadata files.
    
    Reads pakistan_stations.csv (from OpenAQ) and optionally station_ranking.csv
    (from analyze_openaq_data command) to create/update stations and set priorities.
    """
    
    help = "Sync air quality stations from CSV files and activate top stations"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--csv",
            type=str,
            default="pakistan_stations.csv",
            help="Path to station metadata CSV (default: pakistan_stations.csv)",
        )
        parser.add_argument(
            "--from-ranking",
            type=str,
            default="",
            help="Path to station_ranking.csv from analyze_openaq_data (optional)",
        )
        parser.add_argument(
            "--activate-top",
            type=int,
            default=MAX_ACTIVE_STATIONS,
            help=f"Number of top stations to activate (default: {MAX_ACTIVE_STATIONS})",
        )
        parser.add_argument(
            "--deactivate-all",
            action="store_true",
            help="Deactivate all stations before processing",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options) -> None:
        csv_path = Path(options["csv"])
        ranking_path = Path(options["from_ranking"]) if options["from_ranking"] else None
        activate_top = options["activate_top"]
        deactivate_all = options["deactivate_all"]
        dry_run = options["dry_run"]
        
        if not csv_path.exists():
            self.stderr.write(
                self.style.ERROR(f"Station CSV not found: {csv_path}")
            )
            return
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Station Sync ===\n"))
        self.stdout.write(f"Station CSV: {csv_path}")
        if ranking_path:
            self.stdout.write(f"Ranking CSV: {ranking_path}")
        self.stdout.write(f"Activate top: {activate_top}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN MODE]\n"))
        
        # Load ranking data if provided
        rankings = {}
        if ranking_path and ranking_path.exists():
            rankings = self._load_rankings(ranking_path)
            self.stdout.write(f"Loaded rankings for {len(rankings)} stations")
        
        # Load station metadata
        stations = self._load_station_csv(csv_path)
        self.stdout.write(f"Loaded {len(stations)} stations from CSV")
        
        if deactivate_all and not dry_run:
            count = AirQualityStation.objects.update(is_active=False)
            self.stdout.write(f"Deactivated {count} existing stations")
        
        # Process stations
        created = 0
        updated = 0
        errors = 0
        
        # Enrich with rankings and sort
        for station in stations:
            location_id = station["id"]
            if location_id in rankings:
                station["richness_score"] = rankings[location_id]["richness_score"]
                station["recommended_priority"] = rankings[location_id]["priority"]
            else:
                # Default score based on sensors_count
                station["richness_score"] = station.get("sensors_count", 1) * 10
                station["recommended_priority"] = 4  # Low priority
        
        # Sort by richness score (descending)
        stations.sort(key=lambda x: x.get("richness_score", 0), reverse=True)
        
        # Process each station
        with transaction.atomic():
            for i, station_data in enumerate(stations, 1):
                try:
                    if dry_run:
                        self._dry_run_station(station_data, i, activate_top)
                    else:
                        was_created = self._sync_station(station_data, i, activate_top)
                        if was_created:
                            created += 1
                        else:
                            updated += 1
                except Exception as e:
                    errors += 1
                    self.stderr.write(
                        self.style.ERROR(
                            f"Error processing station {station_data.get('id')}: {e}"
                        )
                    )
        
        # Summary
        self.stdout.write(self.style.MIGRATE_LABEL("\n📊 Summary:"))
        if dry_run:
            self.stdout.write(f"  Would create: {len([s for s in stations if not self._station_exists(s['id'])])}")
            self.stdout.write(f"  Would update: {len([s for s in stations if self._station_exists(s['id'])])}")
            self.stdout.write(f"  Would activate: {min(activate_top, len(stations))}")
        else:
            self.stdout.write(f"  Created: {created}")
            self.stdout.write(f"  Updated: {updated}")
            self.stdout.write(f"  Errors: {errors}")
            
            active_count = AirQualityStation.objects.filter(is_active=True).count()
            self.stdout.write(f"  Active stations: {active_count}")
        
        self.stdout.write(self.style.SUCCESS("\n✓ Station sync complete!"))

    def _load_station_csv(self, csv_path: Path) -> List[Dict[str, Any]]:
        """
        Load station metadata from CSV.
        
        Expected columns: id, name, locality, country, latitude, longitude,
                         timezone, sensors_count, parameters
        """
        stations = []
        
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Parse parameters list
                    params_str = row.get("parameters", "")
                    if params_str:
                        parameters = [p.strip() for p in params_str.split(",")]
                    else:
                        parameters = []
                    
                    station = {
                        "id": int(row["id"]),
                        "name": row.get("name", "").strip(),
                        "locality": row.get("locality", "").strip(),
                        "country": row.get("country", "PK").strip(),
                        "latitude": float(row["latitude"]) if row.get("latitude") else None,
                        "longitude": float(row["longitude"]) if row.get("longitude") else None,
                        "timezone": row.get("timezone", "Asia/Karachi").strip(),
                        "sensors_count": int(row.get("sensors_count", 1) or 1),
                        "parameters": parameters,
                    }
                    
                    # Skip stations with invalid coordinates
                    if station["latitude"] is None or station["longitude"] is None:
                        logger.warning(f"Skipping station {station['id']}: missing coordinates")
                        continue
                    
                    stations.append(station)
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row: {e}")
                    continue
        
        return stations

    def _load_rankings(self, ranking_path: Path) -> Dict[int, Dict[str, Any]]:
        """
        Load station rankings from analyze_openaq_data output.
        
        Expected columns: rank, location_id, richness_score, recommended_priority
        """
        rankings = {}
        
        with open(ranking_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    location_id = int(row["location_id"])
                    rankings[location_id] = {
                        "rank": int(row["rank"]),
                        "richness_score": float(row["richness_score"]),
                        "priority": int(row["recommended_priority"]),
                        "row_count": int(row.get("row_count", 0)),
                    }
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid ranking row: {e}")
                    continue
        
        return rankings

    def _station_exists(self, location_id: int) -> bool:
        """Check if station already exists in database."""
        return AirQualityStation.objects.filter(
            openaq_location_id=location_id
        ).exists()

    def _sync_station(
        self,
        station_data: Dict[str, Any],
        rank: int,
        activate_top: int,
    ) -> bool:
        """
        Create or update a station record.
        
        Args:
            station_data: Station metadata dictionary.
            rank: Station rank (1 = highest data richness).
            activate_top: Number of top stations to activate.
            
        Returns:
            True if created, False if updated.
        """
        location_id = station_data["id"]
        
        # Determine if station should be active
        should_activate = rank <= activate_top
        
        # Get priority from ranking or calculate from rank
        if "recommended_priority" in station_data:
            priority = station_data["recommended_priority"]
        elif rank <= 10:
            priority = AirQualityStation.StationPriority.CRITICAL
        elif rank <= 30:
            priority = AirQualityStation.StationPriority.HIGH
        elif rank <= 60:
            priority = AirQualityStation.StationPriority.MEDIUM
        elif rank <= 100:
            priority = AirQualityStation.StationPriority.LOW
        else:
            priority = AirQualityStation.StationPriority.MINIMAL
        
        # Prepare station fields
        defaults = {
            "name": station_data["name"] or f"Station {location_id}",
            "latitude": station_data["latitude"],
            "longitude": station_data["longitude"],
            "locality": station_data.get("locality", ""),
            "country": station_data.get("country", "PK"),
            "timezone": station_data.get("timezone", "Asia/Karachi"),
            "sensors_count": station_data.get("sensors_count", 1),
            "available_parameters": station_data.get("parameters", []),
            "priority": priority,
            "is_active": should_activate,
            "data_source": AirQualityStation.DataSource.OPENAQ,
        }
        
        station, created = AirQualityStation.objects.update_or_create(
            openaq_location_id=location_id,
            defaults=defaults,
        )
        
        status = "🟢" if should_activate else "⚪"
        action = "Created" if created else "Updated"
        
        if rank <= 20 or created:  # Show first 20 and all new stations
            self.stdout.write(
                f"  {status} {action}: {station.name} (ID: {location_id}, "
                f"Priority: {priority}, Rank: {rank})"
            )
        
        return created

    def _dry_run_station(
        self,
        station_data: Dict[str, Any],
        rank: int,
        activate_top: int,
    ) -> None:
        """Show what would be done for a station in dry run mode."""
        location_id = station_data["id"]
        exists = self._station_exists(location_id)
        should_activate = rank <= activate_top
        
        status = "🟢" if should_activate else "⚪"
        action = "Update" if exists else "Create"
        
        if rank <= 20:  # Show first 20
            self.stdout.write(
                f"  {status} Would {action}: {station_data['name']} "
                f"(ID: {location_id}, Rank: {rank})"
            )
