"""
Management command to aggregate district exposure data into province and national summaries.

Usage:
    python manage.py aggregate_exposure                    # Aggregate latest date
    python manage.py aggregate_exposure --date 2025-12-04  # Specific date
    python manage.py aggregate_exposure --all              # All available dates
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Avg, Max, Min, Count, F

from exposure.models import DistrictExposure, ProvinceExposure, NationalExposure


class Command(BaseCommand):
    help = "Aggregate district exposure data into province and national summaries"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Target date (YYYY-MM-DD). Defaults to latest available.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all available dates",
        )

    def handle(self, *args, **options):
        target_date = options.get("date")
        process_all = options.get("all")

        if process_all:
            # Get all unique dates
            dates = DistrictExposure.objects.values_list("date", flat=True).distinct()
            for dt in dates:
                self.process_date(dt)
        elif target_date:
            dt = date.fromisoformat(target_date)
            self.process_date(dt)
        else:
            # Get latest date
            latest = DistrictExposure.objects.order_by("-date").first()
            if latest:
                self.process_date(latest.date)
            else:
                self.stderr.write(self.style.ERROR("No district exposure data found"))
                return

    def process_date(self, target_date: date):
        """Process aggregation for a specific date."""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Processing date: {target_date}")
        self.stdout.write('='*60)

        # 1. Calculate district rankings
        self.calculate_district_rankings(target_date)

        # 2. Aggregate to province level
        self.aggregate_provinces(target_date)

        # 3. Aggregate to national level
        self.aggregate_national(target_date)

        self.stdout.write(self.style.SUCCESS(f"✓ Completed aggregation for {target_date}"))

    def calculate_district_rankings(self, target_date: date):
        """Calculate district rankings based on mean AQI (worst = rank 1)."""
        self.stdout.write("\n📊 Calculating district rankings...")

        districts = DistrictExposure.objects.filter(
            date=target_date
        ).order_by("-mean_aqi")  # Highest AQI = worst = rank 1

        with transaction.atomic():
            for rank, district in enumerate(districts, start=1):
                district.rank = rank
                district.save(update_fields=["rank"])

        self.stdout.write(self.style.SUCCESS(f"   ✓ Ranked {districts.count()} districts"))

    def aggregate_provinces(self, target_date: date):
        """Aggregate district data into province summaries."""
        self.stdout.write("\n🏛️  Aggregating province exposures...")

        # Get unique provinces from district data
        provinces = DistrictExposure.objects.filter(
            date=target_date
        ).values_list("district__province", flat=True).distinct()

        province_count = 0
        for province in provinces:
            district_exposures = DistrictExposure.objects.filter(
                date=target_date,
                district__province=province
            ).select_related("district")

            if not district_exposures.exists():
                continue

            # Calculate aggregations
            agg = district_exposures.aggregate(
                total_pop=Sum("total_population"),
                pop_good_sum=Sum("pop_good"),
                pop_moderate_sum=Sum("pop_moderate"),
                pop_usg_sum=Sum("pop_usg"),
                pop_unhealthy_sum=Sum("pop_unhealthy"),
                pop_very_unhealthy_sum=Sum("pop_very_unhealthy"),
                pop_hazardous_sum=Sum("pop_hazardous"),
                max_aqi_val=Max("mean_aqi"),
                district_count=Count("id"),
            )

            # Population-weighted mean AQI
            total_pop = agg["total_pop"] or 0
            if total_pop > 0:
                weighted_aqi_sum = sum(
                    (exp.mean_aqi or 0) * exp.total_population
                    for exp in district_exposures
                )
                weighted_pm25_sum = sum(
                    (exp.mean_pm25 or 0) * exp.total_population
                    for exp in district_exposures
                )
                pop_weighted_aqi = weighted_aqi_sum / total_pop
                pop_weighted_pm25 = weighted_pm25_sum / total_pop
            else:
                pop_weighted_aqi = 0
                pop_weighted_pm25 = 0

            # Find worst district
            worst = district_exposures.order_by("-mean_aqi").first()

            # Calculate exposure index (pop-weighted AQI capped at 500)
            exposure_index = min(pop_weighted_aqi * 3, 500)

            # Create or update province exposure
            province_exp, created = ProvinceExposure.objects.update_or_create(
                province=province,
                date=target_date,
                pollutant=None,  # Combined satellite data
                defaults={
                    "total_population": total_pop,
                    "mean_pm25": round(pop_weighted_pm25, 2),
                    "mean_aqi": round(pop_weighted_aqi, 1),
                    "max_aqi": agg["max_aqi_val"],
                    "exposure_index": round(exposure_index, 1),
                    "pop_good": agg["pop_good_sum"] or 0,
                    "pop_moderate": agg["pop_moderate_sum"] or 0,
                    "pop_usg": agg["pop_usg_sum"] or 0,
                    "pop_unhealthy": agg["pop_unhealthy_sum"] or 0,
                    "pop_very_unhealthy": agg["pop_very_unhealthy_sum"] or 0,
                    "pop_hazardous": agg["pop_hazardous_sum"] or 0,
                    "district_count": agg["district_count"],
                    "n_districts": agg["district_count"],
                    "worst_district": worst.district if worst else None,
                }
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                f"   {action}: {province} - AQI {pop_weighted_aqi:.1f}, "
                f"{agg['district_count']} districts, {total_pop:,} pop"
            )
            province_count += 1

        # Calculate province rankings
        self.calculate_province_rankings(target_date)

        self.stdout.write(self.style.SUCCESS(f"   ✓ Processed {province_count} provinces"))

    def calculate_province_rankings(self, target_date: date):
        """Rank provinces by mean AQI."""
        provinces = ProvinceExposure.objects.filter(
            date=target_date,
            pollutant__isnull=True
        ).order_by("-mean_aqi")

        with transaction.atomic():
            for rank, prov in enumerate(provinces, start=1):
                prov.rank = rank
                prov.save(update_fields=["rank"])

    def aggregate_national(self, target_date: date):
        """Aggregate all district data into national summary."""
        self.stdout.write("\n🇵🇰 Aggregating national exposure...")

        district_exposures = DistrictExposure.objects.filter(date=target_date)

        if not district_exposures.exists():
            self.stderr.write("   No district data for national aggregation")
            return

        # Calculate aggregations
        agg = district_exposures.aggregate(
            total_pop=Sum("total_population"),
            pop_good_sum=Sum("pop_good"),
            pop_moderate_sum=Sum("pop_moderate"),
            pop_usg_sum=Sum("pop_usg"),
            pop_unhealthy_sum=Sum("pop_unhealthy"),
            pop_very_unhealthy_sum=Sum("pop_very_unhealthy"),
            pop_hazardous_sum=Sum("pop_hazardous"),
            max_aqi_val=Max("mean_aqi"),
            max_pm25_val=Max("mean_pm25"),
            district_count=Count("id"),
        )

        # Population-weighted means
        total_pop = agg["total_pop"] or 0
        if total_pop > 0:
            weighted_aqi_sum = sum(
                (exp.mean_aqi or 0) * exp.total_population
                for exp in district_exposures
            )
            weighted_pm25_sum = sum(
                (exp.mean_pm25 or 0) * exp.total_population
                for exp in district_exposures
            )
            pop_weighted_aqi = weighted_aqi_sum / total_pop
            pop_weighted_pm25 = weighted_pm25_sum / total_pop
        else:
            pop_weighted_aqi = 0
            pop_weighted_pm25 = 0

        # Count provinces
        province_count = district_exposures.values(
            "district__province"
        ).distinct().count()

        # Find worst district
        worst = district_exposures.order_by("-mean_aqi").first()

        # Calculate exposure index
        exposure_index = min(pop_weighted_aqi * 3, 500)

        # Create or update national exposure
        national_exp, created = NationalExposure.objects.update_or_create(
            date=target_date,
            pollutant=None,  # Combined satellite data
            defaults={
                "total_population": total_pop,
                "mean_pm25": round(pop_weighted_pm25, 2),
                "mean_aqi": round(pop_weighted_aqi, 1),
                "max_aqi": agg["max_aqi_val"],
                "concentration_max": agg["max_pm25_val"],
                "exposure_index": round(exposure_index, 1),
                "pop_good": agg["pop_good_sum"] or 0,
                "pop_moderate": agg["pop_moderate_sum"] or 0,
                "pop_usg": agg["pop_usg_sum"] or 0,
                "pop_unhealthy": agg["pop_unhealthy_sum"] or 0,
                "pop_very_unhealthy": agg["pop_very_unhealthy_sum"] or 0,
                "pop_hazardous": agg["pop_hazardous_sum"] or 0,
                "province_count": province_count,
                "district_count": agg["district_count"],
                "worst_district": worst.district if worst else None,
            }
        )

        action = "Created" if created else "Updated"
        self.stdout.write(f"\n   {action} National Summary:")
        self.stdout.write(f"   • Population: {total_pop:,}")
        self.stdout.write(f"   • Mean PM2.5: {pop_weighted_pm25:.1f} µg/m³")
        self.stdout.write(f"   • Mean AQI: {pop_weighted_aqi:.1f}")
        self.stdout.write(f"   • Max AQI: {agg['max_aqi_val']:.1f}")
        self.stdout.write(f"   • Provinces: {province_count}")
        self.stdout.write(f"   • Districts: {agg['district_count']}")
        if worst:
            self.stdout.write(f"   • Worst District: {worst.district.name} ({worst.mean_aqi:.1f} AQI)")

        # Population breakdown
        self.stdout.write(f"\n   Population by AQI Category:")
        self.stdout.write(f"   • Good (0-50):        {agg['pop_good_sum'] or 0:>12,}")
        self.stdout.write(f"   • Moderate (51-100):  {agg['pop_moderate_sum'] or 0:>12,}")
        self.stdout.write(f"   • USG (101-150):      {agg['pop_usg_sum'] or 0:>12,}")
        self.stdout.write(f"   • Unhealthy (151-200):{agg['pop_unhealthy_sum'] or 0:>12,}")
        self.stdout.write(f"   • Very Unhealthy:     {agg['pop_very_unhealthy_sum'] or 0:>12,}")
        self.stdout.write(f"   • Hazardous (>300):   {agg['pop_hazardous_sum'] or 0:>12,}")

        self.stdout.write(self.style.SUCCESS(f"\n   ✓ National aggregation complete"))
