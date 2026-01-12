"""
Management command to calculate district-level exposure.

Usage:
    python manage.py calculate_district_exposure
    python manage.py calculate_district_exposure --province punjab
    python manage.py calculate_district_exposure --date 2024-01-15 --aggregate
"""

from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from air_quality.models import District
from exposure.services.district_exposure import (
    DistrictExposureService,
    calculate_district_exposures,
    aggregate_to_province_and_national,
)


class Command(BaseCommand):
    help = "Calculate exposure for districts using satellite and ground data"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--province",
            type=str,
            help="Filter by province name"
        )
        
        parser.add_argument(
            "--district",
            type=str,
            help="Calculate for a specific district"
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
            "--no-ground",
            action="store_true",
            help="Don't include ground station data"
        )
        
        parser.add_argument(
            "--aggregate",
            action="store_true",
            help="Aggregate to province and national level after district calculation"
        )
        
        parser.add_argument(
            "--aggregate-only",
            action="store_true",
            help="Only aggregate existing district data (skip district calculation)"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't save results to database"
        )
        
        parser.add_argument(
            "--list-districts",
            action="store_true",
            help="List available districts"
        )
    
    def handle(self, *args, **options):
        # List districts
        if options["list_districts"]:
            return self._list_districts(options.get("province"))
        
        # Parse date
        if options["date"]:
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                raise CommandError(f"Invalid date format: {options['date']}. Use YYYY-MM-DD.")
        else:
            target_date = date.today() - timedelta(days=1)
        
        days_back = options["days_back"]
        save = not options["dry_run"]
        include_ground = not options["no_ground"]
        
        # Aggregate only
        if options["aggregate_only"]:
            return self._aggregate_only(target_date, save)
        
        # Initialize service
        service = DistrictExposureService()
        
        # Single district
        if options["district"]:
            return self._calculate_single_district(
                service=service,
                district_name=options["district"],
                target_date=target_date,
                days_back=days_back,
                include_ground=include_ground,
                save=save
            )
        
        # All districts or by province
        self._calculate_all_districts(
            service=service,
            province=options.get("province"),
            target_date=target_date,
            days_back=days_back,
            include_ground=include_ground,
            save=save,
            aggregate=options["aggregate"]
        )
    
    def _list_districts(self, province=None):
        """List available districts."""
        districts = District.objects.filter(geometry__isnull=False)
        
        if province:
            districts = districts.filter(province__iexact=province)
        
        districts = districts.order_by("province", "name")
        
        self.stdout.write(f"\nDistricts with geometry: {districts.count()}")
        
        current_province = None
        for district in districts:
            if district.province != current_province:
                current_province = district.province
                self.stdout.write(f"\n{current_province}:")
            self.stdout.write(f"  - {district.name}")
    
    def _calculate_single_district(
        self,
        service,
        district_name,
        target_date,
        days_back,
        include_ground,
        save
    ):
        """Calculate exposure for a single district."""
        try:
            district = District.objects.get(
                name__iexact=district_name,
                geometry__isnull=False
            )
        except District.DoesNotExist:
            raise CommandError(
                f"District not found: {district_name}. "
                "Use --list-districts to see available districts."
            )
        except District.MultipleObjectsReturned:
            raise CommandError(
                f"Multiple districts match '{district_name}'. "
                "Please be more specific."
            )
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\nCalculating exposure for {district.name}, {district.province}"
            )
        )
        self.stdout.write(f"Date: {target_date}")
        self.stdout.write(f"Days back: {days_back}")
        self.stdout.write(f"Include ground data: {include_ground}")
        self.stdout.write(f"Save to database: {save}\n")
        
        try:
            result = service.calculate_district_exposure(
                district=district,
                target_date=target_date,
                days_back=days_back,
                include_ground_data=include_ground,
                save=save
            )
            
            self._print_district_result(result)
            
        except Exception as e:
            raise CommandError(f"Error calculating exposure: {e}")
    
    def _calculate_all_districts(
        self,
        service,
        province,
        target_date,
        days_back,
        include_ground,
        save,
        aggregate
    ):
        """Calculate exposure for all districts."""
        districts = District.objects.filter(geometry__isnull=False)
        
        if province:
            districts = districts.filter(province__iexact=province)
        
        count = districts.count()
        
        if count == 0:
            raise CommandError("No districts found with geometry.")
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\nCalculating exposure for {count} districts"
            )
        )
        self.stdout.write(f"Date: {target_date}")
        self.stdout.write(f"Province filter: {province or 'All'}")
        self.stdout.write(f"Days back: {days_back}")
        self.stdout.write(f"Include ground data: {include_ground}")
        self.stdout.write(f"Save to database: {save}\n")
        
        results = service.calculate_all_districts(
            province=province,
            target_date=target_date,
            days_back=days_back,
            include_ground_data=include_ground,
            save=save
        )
        
        # Summary
        self._print_summary(results)
        
        # Aggregate if requested
        if aggregate and save:
            self.stdout.write("\n" + "="*60)
            self.stdout.write(self.style.HTTP_INFO("Aggregating to province and national level..."))
            
            agg_results = aggregate_to_province_and_national(target_date, save=True)
            
            self.stdout.write("\nProvince Aggregations:")
            for prov, result in agg_results["provinces"].items():
                if result:
                    self.stdout.write(
                        f"  {prov}: AQI={result.mean_aqi:.1f}, "
                        f"Pop={result.total_population:,.0f}"
                    )
            
            if agg_results["national"]:
                nat = agg_results["national"]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nNational: AQI={nat.mean_aqi:.1f}, "
                        f"Pop={nat.total_population:,.0f}, "
                        f"Districts={nat.district_count}"
                    )
                )
    
    def _aggregate_only(self, target_date, save):
        """Only aggregate existing district data."""
        self.stdout.write(
            self.style.HTTP_INFO(
                f"\nAggregating existing district data for {target_date}"
            )
        )
        
        agg_results = aggregate_to_province_and_national(target_date, save=save)
        
        self.stdout.write("\nProvince Aggregations:")
        for prov, result in agg_results["provinces"].items():
            if result:
                self.stdout.write(
                    f"  {prov}: AQI={result.mean_aqi:.1f}, "
                    f"Pop={result.total_population:,.0f}, "
                    f"Districts={result.district_count}"
                )
        
        if agg_results["national"]:
            nat = agg_results["national"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nNational: AQI={nat.mean_aqi:.1f}, "
                    f"Pop={nat.total_population:,.0f}, "
                    f"Districts={nat.district_count}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("\nNo national aggregation created.")
            )
    
    def _print_district_result(self, result):
        """Print exposure result for a district."""
        exp = result.exposure
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"{result.district.name}, {result.district.province}")
        self.stdout.write('='*50)
        
        self.stdout.write(f"Total Population: {exp.total_population:,.0f}")
        
        if exp.combined_aqi:
            self.stdout.write(
                f"Combined AQI: {exp.combined_aqi:.1f} ({exp.aqi_category})"
            )
            self.stdout.write(f"Dominant Pollutant: {exp.dominant_pollutant}")
        
        if exp.mean_pm25:
            self.stdout.write(f"PM2.5: {exp.mean_pm25:.1f} µg/m³")
        
        self.stdout.write(f"Exposure Index: {exp.mean_exposure_index:.1f}")
        self.stdout.write(f"Data Source: {result.data_source}")
        
        if result.ground_data:
            self.stdout.write(
                f"Ground Stations: {result.ground_data['station_count']}"
            )
            self.stdout.write(
                f"Ground PM2.5: {result.ground_data['pm25_mean']:.1f} µg/m³"
            )
        
        if result.fused_pm25:
            self.stdout.write(f"Fused PM2.5: {result.fused_pm25:.1f} µg/m³")
    
    def _print_summary(self, results):
        """Print summary of all district results."""
        if not results:
            self.stdout.write(self.style.WARNING("\nNo results."))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write('='*60)
        
        # Count by data source
        sources = {}
        for r in results:
            src = r.data_source
            sources[src] = sources.get(src, 0) + 1
        
        self.stdout.write(f"Total districts processed: {len(results)}")
        self.stdout.write("By data source:")
        for src, count in sorted(sources.items()):
            self.stdout.write(f"  {src}: {count}")
        
        # Top 10 worst AQI
        sorted_results = sorted(
            [r for r in results if r.exposure.combined_aqi],
            key=lambda x: x.exposure.combined_aqi,
            reverse=True
        )[:10]
        
        if sorted_results:
            self.stdout.write("\nTop 10 Worst AQI Districts:")
            self.stdout.write("-" * 50)
            
            for r in sorted_results:
                pm25_str = f"{r.exposure.mean_pm25:.1f}" if r.exposure.mean_pm25 else 'N/A'
                self.stdout.write(
                    f"  {r.district.name}: AQI={r.exposure.combined_aqi:.0f}, "
                    f"PM2.5={pm25_str}"
                )
        
        # Total population
        total_pop = sum(r.exposure.total_population for r in results)
        self.stdout.write(f"\nTotal population covered: {total_pop:,.0f}")
