"""
Trigger the daily ingestion pipeline via manage.py for debugging/testing.
"""

from django.core.management.base import BaseCommand
from air_quality.tasks import run_daily_ingestion_pipeline


class Command(BaseCommand):
    help = "Trigger the daily ingestion pipeline (download->correct->publish) for testing"

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, help="ISO date (YYYY-MM-DD)", default=None)

    def handle(self, *args, **options):
        target_date = options.get("date")
        self.stdout.write(f"Triggering pipeline for date: {target_date}")
        result = run_daily_ingestion_pipeline.apply(args=[target_date]).get()
        self.stdout.write(self.style.SUCCESS(str(result)))
