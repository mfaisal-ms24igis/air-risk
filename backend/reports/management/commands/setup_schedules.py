"""
Management command to set up Django-Q scheduled tasks.

Usage:
    python manage.py setup_schedules
"""

from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = "Set up Django-Q scheduled tasks for report cleanup and maintenance"

    def handle(self, *args, **options):
        self.stdout.write("Setting up Django-Q schedules...")

        # Cleanup expired reports - Daily at 2 AM
        cleanup_schedule, created = Schedule.objects.update_or_create(
            name="cleanup_expired_reports",
            defaults={
                "func": "reports.tasks.cleanup_expired_reports_async",
                "schedule_type": Schedule.CRON,
                "cron": "0 2 * * *",  # Every day at 2 AM
                "repeats": -1,  # Repeat indefinitely
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    "✅ Created schedule: cleanup_expired_reports (daily at 2 AM)"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Updated existing schedule: cleanup_expired_reports"
                )
            )

        self.stdout.write(
            self.style.SUCCESS("\n✅ All schedules configured successfully!")
        )
        self.stdout.write("\nActive schedules:")
        self.stdout.write(f"  - {cleanup_schedule.name}: {cleanup_schedule.cron}")
