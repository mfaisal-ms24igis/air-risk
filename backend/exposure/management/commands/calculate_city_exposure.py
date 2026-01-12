"""
Management command to calculate satellite-based exposure for cities.

Usage:
    python manage.py calculate_city_exposure lahore
    python manage.py calculate_city_exposure --all
    python manage.py calculate_city_exposure karachi --date 2024-01-15
"""

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from air_quality.services.gee_constants import CITY_BBOXES
from exposure.services.satellite_exposure import SatelliteExposureService


class Command(BaseCommand):
    help = "Calculate satellite-based air quality exposure for cities"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "city",
            nargs="?",
            type=str,
            help="City name (lahore, karachi, islamabad, etc.) or 'all'"
        )
        
        parser.add_argument(
            "--all",
            action="store_true",
            help="Calculate for all predefined cities"
        )
        
        parser.add_argument(
            "--date",
            type=str,
            help="Target date (YYYY-MM-DD). Defaults to yesterday."
        )
        
        parser.add_argument(
            "--days-back",
            type=int,
            default=7,
            help="Number of days to look back for satellite data"
        )
        
        parser.add_argument(
            "--list-cities",
            action="store_true",
            help="List available cities"
        )
    
    def handle(self, *args, **options):
        # List cities
        if options["list_cities"]:
            self.stdout.write("Available cities:")
            for city in sorted(CITY_BBOXES.keys()):
                bbox = CITY_BBOXES[city]
                self.stdout.write(
                    f"  {city}: ({bbox['west']:.2f}, {bbox['south']:.2f}, "
                    f"{bbox['east']:.2f}, {bbox['north']:.2f})"
                )
            return
        
        # Parse date
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
        else:
            target_date = date.today() - timedelta(days=1)
        
        days_back = options["days_back"]
        
        # Determine cities to process
        if options["all"]:
            cities = list(CITY_BBOXES.keys())
        elif options["city"]:
            city = options["city"].lower()
            if city not in CITY_BBOXES:
                raise CommandError(
                    f"Unknown city: {city}. Available: {', '.join(CITY_BBOXES.keys())}"
                )
            cities = [city]
        else:
            raise CommandError("Specify a city name or use --all. Use --list-cities to see available cities.")
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\nCalculating exposure for {len(cities)} cities on {target_date}"
            )
        )
        self.stdout.write(f"Looking back {days_back} days for satellite data\n")
        
        # Initialize service
        service = SatelliteExposureService()
        
        results = []
        for city in cities:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(self.style.HTTP_INFO(f"Processing: {city.title()}"))
            self.stdout.write('='*60)
            
            try:
                exposure = service.calculate_exposure_for_city(
                    city_name=city,
                    target_date=target_date,
                    days_back=days_back
                )
                
                results.append((city, exposure))
                self._print_exposure(city, exposure)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {city}: {e}")
                )
                continue
        
        # Summary
        self._print_summary(results)
    
    def _print_exposure(self, city: str, exposure):
        """Print exposure metrics for a city."""
        self.stdout.write(f"\n{city.title()} Exposure Metrics:")
        self.stdout.write("-" * 40)
        
        # Population
        self.stdout.write(f"Total Population: {exposure.total_population:,.0f}")
        self.stdout.write(f"Exposed Population: {exposure.exposed_population:,.0f}")
        
        # Air Quality
        if exposure.combined_aqi:
            self.stdout.write(
                f"Combined AQI: {exposure.combined_aqi:.1f} ({exposure.aqi_category})"
            )
            self.stdout.write(f"Dominant Pollutant: {exposure.dominant_pollutant}")
        
        if exposure.mean_pm25:
            self.stdout.write(f"PM2.5 (estimated): {exposure.mean_pm25:.1f} µg/m³")
        
        if exposure.mean_no2:
            self.stdout.write(f"NO2: {exposure.mean_no2:.2e} mol/m²")
        
        if exposure.mean_aod:
            self.stdout.write(f"AOD: {exposure.mean_aod:.3f}")
        
        # Exposure Index
        self.stdout.write(f"Exposure Index: {exposure.mean_exposure_index:.1f}")
        
        # Population by AQI
        self.stdout.write("\nPopulation by AQI Category:")
        categories = [
            ("Good (0-50)", exposure.pop_good),
            ("Moderate (51-100)", exposure.pop_moderate),
            ("USG (101-150)", exposure.pop_usg),
            ("Unhealthy (151-200)", exposure.pop_unhealthy),
            ("Very Unhealthy (201-300)", exposure.pop_very_unhealthy),
            ("Hazardous (>300)", exposure.pop_hazardous),
        ]
        
        for name, pop in categories:
            if pop > 0:
                pct = pop / exposure.total_population * 100 if exposure.total_population > 0 else 0
                self.stdout.write(f"  {name}: {pop:,} ({pct:.1f}%)")
        
        # Data quality
        self.stdout.write(f"\nData Coverage: {exposure.data_coverage:.1%}")
        self.stdout.write(f"Data Source: {exposure.data_source}")
    
    def _print_summary(self, results):
        """Print summary of all results."""
        if not results:
            self.stdout.write(self.style.WARNING("\nNo results to summarize."))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write('='*60)
        
        # Sort by AQI (worst first)
        sorted_results = sorted(
            results,
            key=lambda x: x[1].combined_aqi or 0,
            reverse=True
        )
        
        self.stdout.write("\nCities ranked by AQI (worst to best):")
        self.stdout.write("-" * 50)
        self.stdout.write(f"{'City':<15} {'AQI':>8} {'PM2.5':>10} {'Pop (M)':>10}")
        self.stdout.write("-" * 50)
        
        for city, exp in sorted_results:
            aqi_str = f"{exp.combined_aqi:.0f}" if exp.combined_aqi else "N/A"
            pm25_str = f"{exp.mean_pm25:.1f}" if exp.mean_pm25 else "N/A"
            pop_str = f"{exp.total_population/1e6:.2f}"
            self.stdout.write(f"{city.title():<15} {aqi_str:>8} {pm25_str:>10} {pop_str:>10}")
        
        # Total population
        total_pop = sum(exp.total_population for _, exp in results)
        self.stdout.write("-" * 50)
        self.stdout.write(f"{'Total':<15} {'-':>8} {'-':>10} {total_pop/1e6:.2f}")
        
        self.stdout.write(
            self.style.SUCCESS(f"\nProcessed {len(results)} cities successfully.")
        )
