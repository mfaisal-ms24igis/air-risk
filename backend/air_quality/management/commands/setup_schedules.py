"""
Management command to setup Django-Q scheduled tasks.
Replaces Celery Beat schedule configuration.
"""

from django.core.management.base import BaseCommand
from django_q.models import Schedule


class Command(BaseCommand):
    help = 'Setup Django-Q scheduled tasks for background processing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('Setting up Django-Q Scheduled Tasks'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))

        # Clear existing schedules (optional - comment out to preserve manual schedules)
        # Schedule.objects.all().delete()
        # self.stdout.write('Cleared existing schedules')

        schedules = [
            {
                'name': 'Daily Ingestion Pipeline',
                'func': 'air_quality.tasks.run_daily_ingestion_pipeline',
                'schedule_type': Schedule.CRON,
                'cron': '0 6 * * *',  # Daily at 06:00 UTC
                'repeats': -1,  # Repeat indefinitely
            },
            {
                'name': 'Weekly Model Retraining',
                'func': 'correction.tasks.retrain_all_models',
                'schedule_type': Schedule.CRON,
                'cron': '0 2 * * 0',  # Sunday at 02:00 UTC
                'repeats': -1,
            },
            {
                'name': 'Daily Scheduled Reports',
                'func': 'reports.tasks.generate_scheduled_reports',
                'schedule_type': Schedule.CRON,
                'cron': '0 8 * * *',  # Daily at 08:00 UTC
                'repeats': -1,
            },
            {
                'name': 'Hourly Raster Cleanup',
                'func': 'air_quality.tasks.cleanup_old_rasters',
                'schedule_type': Schedule.CRON,
                'cron': '30 * * * *',  # Every hour at :30
                'repeats': -1,
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for schedule_data in schedules:
            name = schedule_data['name']
            
            # Check if schedule already exists
            existing = Schedule.objects.filter(name=name).first()
            
            if existing:
                # Update existing schedule
                for key, value in schedule_data.items():
                    setattr(existing, key, value)
                existing.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  ↻ Updated: {name}')
                )
            else:
                # Create new schedule
                Schedule.objects.create(**schedule_data)
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {name}')
                )

        self.stdout.write('\n' + '='*70)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary:\n'
                f'  Created: {created_count}\n'
                f'  Updated: {updated_count}\n'
                f'  Total:   {created_count + updated_count}'
            )
        )
        self.stdout.write('='*70 + '\n')

        # Display all active schedules
        self.stdout.write(self.style.WARNING('\nActive Schedules:'))
        self.stdout.write('-'*70)
        
        for schedule in Schedule.objects.all().order_by('name'):
            status = '✓ Active' if schedule.next_run else '✗ Disabled'
            self.stdout.write(
                f'  {schedule.name:30s} {schedule.cron:15s} {status}'
            )
        
        self.stdout.write('-'*70 + '\n')
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Django-Q schedules configured successfully!\n'
                '\nNext steps:\n'
                '  1. Start Django-Q cluster: python manage.py qcluster\n'
                '  2. Or use Docker: docker-compose up -d qcluster\n'
                '  3. Monitor tasks: Django Admin → Django Q → Successful/Failed tasks\n'
            )
        )
