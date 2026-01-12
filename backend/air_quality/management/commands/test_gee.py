"""
Management command to test GEE connection and retrieve sample data.
"""

import logging
from datetime import date, timedelta
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test Google Earth Engine connection and retrieve sample satellite data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Only test connection, do not retrieve data',
        )
        parser.add_argument(
            '--lat',
            type=float,
            default=31.5204,
            help='Latitude for test query (default: Lahore)',
        )
        parser.add_argument(
            '--lon',
            type=float,
            default=74.3587,
            help='Longitude for test query (default: Lahore)',
        )
        parser.add_argument(
            '--city',
            type=str,
            choices=['karachi', 'lahore', 'islamabad', 'peshawar', 'quetta', 'multan', 'faisalabad'],
            help='Predefined city to query',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to query (default: 30)',
        )
        parser.add_argument(
            '--parameters',
            type=str,
            nargs='+',
            default=['NO2', 'AOD'],
            help='Parameters to retrieve (default: NO2 AOD)',
        )

    def handle(self, *args, **options):
        from air_quality.services import (
            get_gee_auth,
            get_satellite_manager,
        )
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Google Earth Engine Connection Test"))
        self.stdout.write("=" * 60 + "\n")
        
        # Step 1: Initialize GEE
        self.stdout.write("Initializing GEE authentication...")
        try:
            gee_auth = get_gee_auth()
            gee_auth.initialize()
            self.stdout.write(self.style.SUCCESS(
                f"✓ GEE initialized (project: {gee_auth.project_id})"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ GEE initialization failed: {e}"))
            return
        
        # Step 2: Test connection
        self.stdout.write("\nTesting GEE connection...")
        test_result = gee_auth.test_connection()
        
        if test_result['connected']:
            self.stdout.write(self.style.SUCCESS(
                f"✓ Connection successful (test image: {test_result.get('test_image', 'N/A')})"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"✗ Connection failed: {test_result.get('error', 'Unknown error')}"
            ))
            return
        
        if options['test_only']:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("Test complete!"))
            return
        
        # Step 3: Get satellite data
        self.stdout.write("\n" + "-" * 60)
        self.stdout.write("Retrieving satellite data...")
        
        manager = get_satellite_manager()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=options['days'])
        
        self.stdout.write(f"  Date range: {start_date} to {end_date}")
        self.stdout.write(f"  Parameters: {', '.join(options['parameters'])}")
        
        try:
            if options['city']:
                self.stdout.write(f"  Location: {options['city'].title()}")
                result = manager.get_city_air_quality(
                    city=options['city'],
                    start_date=start_date,
                    end_date=end_date,
                    parameters=options['parameters'],
                )
            else:
                self.stdout.write(f"  Location: ({options['lat']}, {options['lon']})")
                result = manager.get_air_quality_data(
                    lat=options['lat'],
                    lon=options['lon'],
                    start_date=start_date,
                    end_date=end_date,
                    parameters=options['parameters'],
                )
            
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Query completed in {result.query_time_ms:.0f}ms"
            ))
            
            # Display results
            self.stdout.write("\n" + "-" * 60)
            self.stdout.write(self.style.MIGRATE_HEADING("Results:"))
            
            # NO2
            if result.no2:
                self._print_tropomi_result("NO2", result.no2)
            
            # SO2
            if result.so2:
                self._print_tropomi_result("SO2", result.so2)
            
            # CO
            if result.co:
                self._print_tropomi_result("CO", result.co)
            
            # O3
            if result.o3:
                self._print_tropomi_result("O3", result.o3)
            
            # Aerosol Index
            if result.aerosol_index:
                self._print_tropomi_result("Aerosol Index", result.aerosol_index)
            
            # AOD / PM2.5
            if result.aod:
                self._print_aod_result(result.aod)
            
            # Summary
            self.stdout.write("\n" + "-" * 60)
            self.stdout.write(f"Sources queried: {', '.join(result.sources_queried)}")
            self.stdout.write(f"Sources successful: {', '.join(result.sources_successful)}")
            
            if result.errors:
                self.stdout.write(self.style.WARNING(f"Errors: {result.errors}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Data retrieval failed: {e}"))
            logger.exception("Error retrieving satellite data")
            return
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("GEE test complete!"))
        self.stdout.write("=" * 60)
    
    def _print_tropomi_result(self, name, result):
        """Print TROPOMI result in formatted output."""
        if result.error:
            self.stdout.write(f"\n  {name}: {self.style.WARNING(result.error)}")
            return
        
        self.stdout.write(f"\n  {self.style.MIGRATE_LABEL(name)}:")
        self.stdout.write(f"    Images: {result.image_count}")
        
        if result.mean_value is not None:
            # Format scientific notation for small values
            if abs(result.mean_value) < 0.001:
                self.stdout.write(f"    Mean: {result.mean_value:.2e} {result.unit}")
            else:
                self.stdout.write(f"    Mean: {result.mean_value:.4f} {result.unit}")
        
        if result.min_value is not None and result.max_value is not None:
            if abs(result.min_value) < 0.001:
                self.stdout.write(f"    Range: {result.min_value:.2e} - {result.max_value:.2e}")
            else:
                self.stdout.write(f"    Range: {result.min_value:.4f} - {result.max_value:.4f}")
        
        if result.pixel_count:
            self.stdout.write(f"    Pixels: {int(result.pixel_count):,}")
    
    def _print_aod_result(self, result):
        """Print AOD result in formatted output."""
        if result.error:
            self.stdout.write(f"\n  AOD: {self.style.WARNING(result.error)}")
            return
        
        self.stdout.write(f"\n  {self.style.MIGRATE_LABEL('MODIS AOD')}:")
        self.stdout.write(f"    Images: {result.image_count}")
        
        if result.aod_055 is not None:
            self.stdout.write(f"    AOD (550nm): {result.aod_055:.3f}")
        
        if result.aod_047 is not None:
            self.stdout.write(f"    AOD (470nm): {result.aod_047:.3f}")
        
        if result.min_aod is not None and result.max_aod is not None:
            self.stdout.write(f"    Range: {result.min_aod:.3f} - {result.max_aod:.3f}")
        
        if result.estimated_pm25 is not None:
            self.stdout.write(self.style.SUCCESS(
                f"    Estimated PM2.5: {result.estimated_pm25:.1f} µg/m³"
            ))
        
        if result.pixel_count:
            self.stdout.write(f"    Pixels: {int(result.pixel_count):,}")
