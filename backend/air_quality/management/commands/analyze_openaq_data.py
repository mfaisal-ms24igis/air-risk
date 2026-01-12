"""
Management command to analyze OpenAQ bulk data files for quality issues.

This command scans all CSV.GZ files in the openaq_bulk_data directory and:
- Detects unit inconsistencies per parameter
- Flags invalid coordinates
- Identifies duplicate station+timestamp+parameter combinations
- Ranks stations by data richness for prioritization

Run before ingestion to understand data quality:
    python manage.py analyze_openaq_data

Outputs:
- Console summary of findings
- data_errors.log with detailed issues
- station_ranking.csv with stations ranked by data value
"""

import csv
import gzip
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand

from air_quality.constants import (
    Pollutant,
    COORDINATE_BOUNDS,
    GLOBAL_COORDINATE_BOUNDS,
)


logger = logging.getLogger(__name__)


class DataAnalyzer:
    """
    Analyzes OpenAQ bulk data files for quality issues.
    
    Collects statistics on:
    - Parameter/unit combinations found
    - Coordinate validity
    - Duplicate records
    - Station data richness
    """

    def __init__(self, data_dir: Path, error_log_path: Path) -> None:
        """
        Initialize the analyzer.
        
        Args:
            data_dir: Path to openaq_bulk_data directory.
            error_log_path: Path to write detailed error log.
        """
        self.data_dir = data_dir
        self.error_log_path = error_log_path
        
        # Statistics collectors
        self.files_scanned: int = 0
        self.total_rows: int = 0
        self.error_rows: int = 0
        
        # Parameter/unit tracking
        self.parameter_units: Dict[str, Set[str]] = defaultdict(set)
        self.parameter_counts: Dict[str, int] = defaultdict(int)
        
        # Coordinate issues
        self.invalid_coordinates: List[Dict[str, Any]] = []
        self.out_of_pakistan_coordinates: List[Dict[str, Any]] = []
        
        # Duplicate tracking (station_id -> set of (timestamp, parameter))
        self.seen_records: Dict[int, Set[Tuple[str, str]]] = defaultdict(set)
        self.duplicate_count: int = 0
        
        # Station statistics
        self.station_stats: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {
                "file_count": 0,
                "row_count": 0,
                "parameters": set(),
                "units": set(),
                "date_range": [None, None],
                "errors": 0,
            }
        )
        
        # Value range tracking
        self.value_ranges: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"min": float("inf"), "max": float("-inf")}
        )
        
        # Error log file handle
        self._error_file = None

    def analyze(self) -> Dict[str, Any]:
        """
        Run the full analysis on all CSV.GZ files.
        
        Returns:
            Dictionary with analysis results.
        """
        # Open error log
        self._error_file = open(self.error_log_path, "w", encoding="utf-8")
        self._error_file.write(f"OpenAQ Data Analysis Error Log\n")
        self._error_file.write(f"Generated: {datetime.now().isoformat()}\n")
        self._error_file.write(f"Data directory: {self.data_dir}\n")
        self._error_file.write("=" * 80 + "\n\n")
        
        try:
            # Find all CSV.GZ files
            csv_files = list(self.data_dir.rglob("*.csv.gz"))
            total_files = len(csv_files)
            
            logger.info(f"Found {total_files} CSV.GZ files to analyze")
            
            for i, csv_path in enumerate(csv_files, 1):
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{total_files} files ({i/total_files*100:.1f}%)")
                
                self._analyze_file(csv_path)
            
            # Close error log
            self._error_file.write(f"\n\nTotal errors logged: {self.error_rows}\n")
            
        finally:
            if self._error_file:
                self._error_file.close()
                self._error_file = None
        
        return self._compile_results()

    def _analyze_file(self, csv_path: Path) -> None:
        """
        Analyze a single CSV.GZ file.
        
        Args:
            csv_path: Path to the gzipped CSV file.
        """
        self.files_scanned += 1
        
        # Extract location ID from path (e.g., location_8664/year_2024/...)
        try:
            parts = csv_path.parts
            location_part = [p for p in parts if p.startswith("location_")]
            if location_part:
                location_id = int(location_part[0].replace("location_", ""))
            else:
                location_id = 0
        except (ValueError, IndexError):
            location_id = 0
        
        self.station_stats[location_id]["file_count"] += 1
        
        try:
            with gzip.open(csv_path, "rt", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    self.total_rows += 1
                    self._analyze_row(row, location_id, csv_path)
                    
        except Exception as e:
            self._log_error(f"Failed to read file {csv_path}: {e}")
            self.station_stats[location_id]["errors"] += 1

    def _analyze_row(
        self,
        row: Dict[str, str],
        location_id: int,
        source_file: Path,
    ) -> None:
        """
        Analyze a single data row.
        
        Args:
            row: Dictionary from CSV reader.
            location_id: OpenAQ location ID.
            source_file: Source file path for error reporting.
        """
        self.station_stats[location_id]["row_count"] += 1
        
        # Get key fields
        parameter = row.get("parameter", "").lower().strip()
        unit = row.get("unit", "").strip()
        value_str = row.get("value", "")
        timestamp = row.get("datetime", row.get("datetime_utc", ""))
        lat_str = row.get("lat", row.get("latitude", ""))
        lon_str = row.get("lon", row.get("longitude", ""))
        
        # Track parameter/unit combinations
        if parameter:
            self.parameter_units[parameter].add(unit)
            self.parameter_counts[parameter] += 1
            self.station_stats[location_id]["parameters"].add(parameter)
            self.station_stats[location_id]["units"].add(unit)
        
        # Track value ranges
        try:
            value = float(value_str)
            if parameter:
                self.value_ranges[parameter]["min"] = min(
                    self.value_ranges[parameter]["min"], value
                )
                self.value_ranges[parameter]["max"] = max(
                    self.value_ranges[parameter]["max"], value
                )
            
            # Check for suspicious values
            if value < 0:
                self._log_error(
                    f"Negative value: {parameter}={value} in {source_file.name}"
                )
                self.error_rows += 1
                
        except (ValueError, TypeError):
            if value_str:
                self._log_error(
                    f"Invalid value '{value_str}' for {parameter} in {source_file.name}"
                )
                self.error_rows += 1
        
        # Track date range
        if timestamp:
            try:
                # Parse ISO format timestamp
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                date_str = dt.date().isoformat()
                
                stats = self.station_stats[location_id]
                if stats["date_range"][0] is None or date_str < stats["date_range"][0]:
                    stats["date_range"][0] = date_str
                if stats["date_range"][1] is None or date_str > stats["date_range"][1]:
                    stats["date_range"][1] = date_str
                    
            except (ValueError, TypeError):
                pass
        
        # Check for duplicates
        if timestamp and parameter:
            record_key = (timestamp, parameter)
            if record_key in self.seen_records[location_id]:
                self.duplicate_count += 1
            else:
                self.seen_records[location_id].add(record_key)
        
        # Validate coordinates
        try:
            lat = float(lat_str) if lat_str else None
            lon = float(lon_str) if lon_str else None
            
            if lat is not None and lon is not None:
                # Check global bounds
                lat_min, lat_max = GLOBAL_COORDINATE_BOUNDS["latitude"]
                lon_min, lon_max = GLOBAL_COORDINATE_BOUNDS["longitude"]
                
                if not (lat_min <= lat <= lat_max) or not (lon_min <= lon <= lon_max):
                    self.invalid_coordinates.append({
                        "location_id": location_id,
                        "lat": lat,
                        "lon": lon,
                        "file": source_file.name,
                    })
                    self._log_error(
                        f"Invalid coordinates ({lat}, {lon}) for location {location_id}"
                    )
                    self.error_rows += 1
                else:
                    # Check Pakistan bounds
                    pk_lat_min, pk_lat_max = COORDINATE_BOUNDS["latitude"]
                    pk_lon_min, pk_lon_max = COORDINATE_BOUNDS["longitude"]
                    
                    if not (pk_lat_min <= lat <= pk_lat_max) or not (pk_lon_min <= lon <= pk_lon_max):
                        self.out_of_pakistan_coordinates.append({
                            "location_id": location_id,
                            "lat": lat,
                            "lon": lon,
                        })
                        
        except (ValueError, TypeError):
            if lat_str or lon_str:
                self._log_error(
                    f"Invalid coordinate format: lat='{lat_str}', lon='{lon_str}' "
                    f"for location {location_id}"
                )
                self.error_rows += 1

    def _log_error(self, message: str) -> None:
        """Write error message to log file."""
        if self._error_file:
            self._error_file.write(f"{datetime.now().isoformat()} | {message}\n")

    def _compile_results(self) -> Dict[str, Any]:
        """
        Compile analysis results into a summary dictionary.
        
        Returns:
            Dictionary with all analysis results.
        """
        # Rank stations by data richness
        station_rankings = []
        for location_id, stats in self.station_stats.items():
            if location_id == 0:
                continue
                
            # Calculate richness score
            # Weight: row_count (40%), parameter diversity (30%), date range (30%)
            row_score = min(stats["row_count"] / 10000, 1.0) * 40
            param_score = min(len(stats["parameters"]) / 5, 1.0) * 30
            
            date_score = 0
            if stats["date_range"][0] and stats["date_range"][1]:
                try:
                    start = datetime.fromisoformat(stats["date_range"][0])
                    end = datetime.fromisoformat(stats["date_range"][1])
                    days = (end - start).days
                    date_score = min(days / 365, 1.0) * 30
                except ValueError:
                    pass
            
            richness_score = row_score + param_score + date_score
            
            station_rankings.append({
                "location_id": location_id,
                "richness_score": round(richness_score, 2),
                "row_count": stats["row_count"],
                "file_count": stats["file_count"],
                "parameters": sorted(stats["parameters"]),
                "parameter_count": len(stats["parameters"]),
                "date_start": stats["date_range"][0],
                "date_end": stats["date_range"][1],
                "errors": stats["errors"],
            })
        
        # Sort by richness score descending
        station_rankings.sort(key=lambda x: x["richness_score"], reverse=True)
        
        # Identify unit inconsistencies
        unit_issues = {}
        for param, units in self.parameter_units.items():
            if len(units) > 1:
                unit_issues[param] = list(units)
        
        return {
            "summary": {
                "files_scanned": self.files_scanned,
                "total_rows": self.total_rows,
                "error_rows": self.error_rows,
                "unique_stations": len(self.station_stats) - (1 if 0 in self.station_stats else 0),
                "duplicate_records": self.duplicate_count,
                "invalid_coordinates": len(self.invalid_coordinates),
                "out_of_pakistan": len(self.out_of_pakistan_coordinates),
            },
            "parameters": {
                param: {
                    "count": self.parameter_counts[param],
                    "units": list(units),
                    "value_range": {
                        "min": self.value_ranges[param]["min"],
                        "max": self.value_ranges[param]["max"],
                    } if param in self.value_ranges else None,
                }
                for param, units in self.parameter_units.items()
            },
            "unit_inconsistencies": unit_issues,
            "station_rankings": station_rankings,
            "top_60_stations": [s["location_id"] for s in station_rankings[:60]],
            "coordinate_issues": {
                "invalid": self.invalid_coordinates[:10],  # First 10
                "out_of_pakistan": len(self.out_of_pakistan_coordinates),
            },
        }


class Command(BaseCommand):
    """
    Django management command to analyze OpenAQ bulk data.
    
    Usage:
        python manage.py analyze_openaq_data
        python manage.py analyze_openaq_data --data-dir /path/to/data
        python manage.py analyze_openaq_data --output-csv station_ranking.csv
    """
    
    help = "Analyze OpenAQ bulk data files for quality issues and station ranking"

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
            "--output-csv",
            type=str,
            default="station_ranking.csv",
            help="Path to station ranking CSV (default: station_ranking.csv)",
        )
        parser.add_argument(
            "--top-n",
            type=int,
            default=60,
            help="Number of top stations to highlight (default: 60)",
        )

    def handle(self, *args, **options) -> None:
        data_dir = Path(options["data_dir"])
        error_log_path = Path(options["error_log"])
        output_csv = Path(options["output_csv"])
        top_n = options["top_n"]
        
        if not data_dir.exists():
            self.stderr.write(
                self.style.ERROR(f"Data directory not found: {data_dir}")
            )
            return
        
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== OpenAQ Data Analysis ===\n"))
        self.stdout.write(f"Data directory: {data_dir}")
        self.stdout.write(f"Error log: {error_log_path}")
        self.stdout.write(f"Output CSV: {output_csv}\n")
        
        # Run analysis
        analyzer = DataAnalyzer(data_dir, error_log_path)
        
        self.stdout.write("Scanning files...\n")
        results = analyzer.analyze()
        
        # Print summary
        self._print_summary(results, top_n)
        
        # Write station ranking CSV
        self._write_ranking_csv(results["station_rankings"], output_csv)
        
        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Analysis complete!")
        )
        self.stdout.write(f"  Error log: {error_log_path}")
        self.stdout.write(f"  Station rankings: {output_csv}")

    def _print_summary(self, results: Dict[str, Any], top_n: int) -> None:
        """Print analysis summary to console."""
        summary = results["summary"]
        
        self.stdout.write(self.style.MIGRATE_LABEL("\n📊 Summary:"))
        self.stdout.write(f"  Files scanned: {summary['files_scanned']:,}")
        self.stdout.write(f"  Total rows: {summary['total_rows']:,}")
        self.stdout.write(f"  Error rows: {summary['error_rows']:,}")
        self.stdout.write(f"  Unique stations: {summary['unique_stations']}")
        self.stdout.write(f"  Duplicate records: {summary['duplicate_records']:,}")
        
        self.stdout.write(self.style.MIGRATE_LABEL("\n📍 Coordinate Issues:"))
        self.stdout.write(f"  Invalid coordinates: {summary['invalid_coordinates']}")
        self.stdout.write(f"  Outside Pakistan bounds: {summary['out_of_pakistan']}")
        
        self.stdout.write(self.style.MIGRATE_LABEL("\n🔬 Parameters Found:"))
        for param, info in sorted(results["parameters"].items()):
            units_str = ", ".join(info["units"])
            range_str = ""
            if info["value_range"]:
                range_str = f" [{info['value_range']['min']:.2f} - {info['value_range']['max']:.2f}]"
            self.stdout.write(
                f"  {param}: {info['count']:,} readings | Units: {units_str}{range_str}"
            )
        
        # Unit inconsistencies
        if results["unit_inconsistencies"]:
            self.stdout.write(
                self.style.WARNING("\n⚠️  Unit Inconsistencies Detected:")
            )
            for param, units in results["unit_inconsistencies"].items():
                self.stdout.write(f"  {param}: {', '.join(units)}")
        else:
            self.stdout.write(
                self.style.SUCCESS("\n✓ No unit inconsistencies detected")
            )
        
        # Top stations
        self.stdout.write(self.style.MIGRATE_LABEL(f"\n🏆 Top {top_n} Stations by Data Richness:"))
        for i, station in enumerate(results["station_rankings"][:top_n], 1):
            params = ", ".join(station["parameters"][:3])
            if len(station["parameters"]) > 3:
                params += f" +{len(station['parameters'])-3} more"
            self.stdout.write(
                f"  {i:2}. Location {station['location_id']:>8} | "
                f"Score: {station['richness_score']:5.1f} | "
                f"Rows: {station['row_count']:>8,} | "
                f"Params: {params}"
            )

    def _write_ranking_csv(
        self,
        rankings: List[Dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Write station rankings to CSV file."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "rank",
                    "location_id",
                    "richness_score",
                    "row_count",
                    "file_count",
                    "parameter_count",
                    "parameters",
                    "date_start",
                    "date_end",
                    "errors",
                    "recommended_priority",
                ],
            )
            writer.writeheader()
            
            for i, station in enumerate(rankings, 1):
                # Assign recommended priority based on rank
                if i <= 10:
                    priority = 1  # Critical
                elif i <= 30:
                    priority = 2  # High
                elif i <= 60:
                    priority = 3  # Medium
                elif i <= 100:
                    priority = 4  # Low
                else:
                    priority = 5  # Minimal
                
                writer.writerow({
                    "rank": i,
                    "location_id": station["location_id"],
                    "richness_score": station["richness_score"],
                    "row_count": station["row_count"],
                    "file_count": station["file_count"],
                    "parameter_count": station["parameter_count"],
                    "parameters": "|".join(station["parameters"]),
                    "date_start": station["date_start"] or "",
                    "date_end": station["date_end"] or "",
                    "errors": station["errors"],
                    "recommended_priority": priority,
                })
