"""
Management command to fetch satellite data for ground stations.

Retrieves TROPOMI and MODIS data for active air quality stations
and stores the results for correlation analysis.
"""

import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import F

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch satellite data (NO2, AOD) for active ground monitoring stations"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to fetch (default: 30)',
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD). Overrides --days.',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--parameters',
            type=str,
            nargs='+',
            default=['NO2', 'AOD'],
            help='Parameters to retrieve (default: NO2 AOD)',
        )
        parser.add_argument(
            '--station',
            type=int,
            action='append',
            help='Specific station ID(s) to fetch. Can be repeated.',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            default=True,
            help='Only fetch for active stations (default: True)',
        )
        parser.add_argument(
            '--all-stations',
            action='store_true',
            help='Fetch for all stations, not just active ones',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of stations to process',
        )
        parser.add_argument(
            '--buffer-m',
            type=int,
            default=5000,
            help='Buffer radius in meters around station (default: 5000)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fetched without actually fetching',
        )
        parser.add_argument(
            '--output-csv',
            type=str,
            help='Export results to CSV file',
        )

    def handle(self, *args, **options):
        from air_quality.models import AirQualityStation
        from air_quality.services import get_satellite_manager
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Satellite Data Fetch for Ground Stations"))
        self.stdout.write("=" * 60 + "\n")
        
        # Determine date range
        if options['end_date']:
            end_date = date.fromisoformat(options['end_date'])
        else:
            end_date = date.today()
        
        if options['start_date']:
            start_date = date.fromisoformat(options['start_date'])
        else:
            start_date = end_date - timedelta(days=options['days'])
        
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        self.stdout.write(f"Parameters: {', '.join(options['parameters'])}")
        self.stdout.write(f"Buffer radius: {options['buffer_m']}m")
        
        # Get stations
        stations_qs = AirQualityStation.objects.all()
        
        if options['station']:
            stations_qs = stations_qs.filter(openaq_location_id__in=options['station'])
        elif not options['all_stations']:
            stations_qs = stations_qs.filter(is_active=True)
        
        stations_qs = stations_qs.order_by('priority', 'name')
        
        if options['limit']:
            stations_qs = stations_qs[:options['limit']]
        
        stations = list(stations_qs.values(
            'id', 'name', 'openaq_location_id', 'latitude', 'longitude'
        ))
        
        self.stdout.write(f"Stations to process: {len(stations)}")
        
        if not stations:
            self.stdout.write(self.style.WARNING("No stations found matching criteria"))
            return
        
        # Dry run - just show stations
        if options['dry_run']:
            self.stdout.write("\n" + "-" * 60)
            self.stdout.write("Stations that would be processed (dry run):")
            for i, s in enumerate(stations[:20], 1):
                self.stdout.write(
                    f"  {i}. {s['name']} (ID: {s['openaq_location_id']}) "
                    f"@ ({s['latitude']:.4f}, {s['longitude']:.4f})"
                )
            if len(stations) > 20:
                self.stdout.write(f"  ... and {len(stations) - 20} more")
            return
        
        # Initialize satellite manager
        self.stdout.write("\nInitializing GEE...")
        try:
            manager = get_satellite_manager()
            manager.initialize()
            self.stdout.write(self.style.SUCCESS("✓ GEE initialized"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ GEE initialization failed: {e}"))
            return
        
        # Fetch data for each station
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("Fetching satellite data...")
        
        results = []
        success_count = 0
        error_count = 0
        
        for i, station in enumerate(stations, 1):
            station_name = station['name'][:30]
            self.stdout.write(
                f"\n[{i}/{len(stations)}] {station_name} "
                f"(ID: {station['openaq_location_id']})"
            )
            
            try:
                sat_result = manager.get_air_quality_data(
                    lat=station['latitude'],
                    lon=station['longitude'],
                    start_date=start_date,
                    end_date=end_date,
                    parameters=options['parameters'],
                    buffer_m=options['buffer_m'],
                    parallel=True,
                )
                
                # Extract key values
                result_row = {
                    'station_id': station['openaq_location_id'],
                    'station_name': station['name'],
                    'lat': station['latitude'],
                    'lon': station['longitude'],
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                }
                
                # Add NO2 if available
                if sat_result.no2 and sat_result.no2.mean_value is not None:
                    result_row['no2_mean'] = sat_result.no2.mean_value
                    result_row['no2_images'] = sat_result.no2.image_count
                    self.stdout.write(
                        f"  NO2: {sat_result.no2.mean_value:.2e} mol/m² "
                        f"({sat_result.no2.image_count} images)"
                    )
                
                # Add AOD if available
                if sat_result.aod and sat_result.aod.aod_055 is not None:
                    result_row['aod_055'] = sat_result.aod.aod_055
                    result_row['estimated_pm25'] = sat_result.aod.estimated_pm25
                    result_row['aod_images'] = sat_result.aod.image_count
                    self.stdout.write(
                        f"  AOD: {sat_result.aod.aod_055:.3f} "
                        f"(PM2.5 est: {sat_result.aod.estimated_pm25:.1f} µg/m³)"
                    )
                
                # Add other parameters
                if sat_result.so2 and sat_result.so2.mean_value is not None:
                    result_row['so2_mean'] = sat_result.so2.mean_value
                
                if sat_result.co and sat_result.co.mean_value is not None:
                    result_row['co_mean'] = sat_result.co.mean_value
                
                if sat_result.o3 and sat_result.o3.mean_value is not None:
                    result_row['o3_mean'] = sat_result.o3.mean_value
                
                result_row['query_time_ms'] = sat_result.query_time_ms
                results.append(result_row)
                
                success_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                error_count += 1
                results.append({
                    'station_id': station['openaq_location_id'],
                    'station_name': station['name'],
                    'error': str(e),
                })
        
        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        self.stdout.write(f"  Stations processed: {len(stations)}")
        self.stdout.write(self.style.SUCCESS(f"  Successful: {success_count}"))
        if error_count:
            self.stdout.write(self.style.ERROR(f"  Errors: {error_count}"))
        
        # Export to CSV
        if options['output_csv'] and results:
            self._export_csv(results, options['output_csv'])
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Satellite data fetch complete!"))
    
    def _export_csv(self, results, filepath):
        """Export results to CSV file."""
        import csv
        
        # Get all unique keys
        all_keys = set()
        for r in results:
            all_keys.update(r.keys())
        
        fieldnames = sorted(all_keys)
        
        # Move important fields to front
        priority_fields = [
            'station_id', 'station_name', 'lat', 'lon',
            'start_date', 'end_date', 'no2_mean', 'aod_055', 'estimated_pm25'
        ]
        fieldnames = [f for f in priority_fields if f in fieldnames] + \
                     [f for f in fieldnames if f not in priority_fields]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ Results exported to: {filepath}"))
