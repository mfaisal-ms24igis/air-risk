import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.base')
django.setup()

from air_quality.models import PollutantReading, AirQualityStation
from django.utils import timezone
from datetime import datetime, timedelta

# Check readings for the stations found
station_ids = [294, 280, 266]  # CERP Office, NPPMCL, Syed Maratib Ali Road
start_date = timezone.make_aware(datetime.now() - timedelta(days=30))
end_date = timezone.make_aware(datetime.now())

print('Checking readings for Lahore stations...')
for station_id in station_ids:
    station = AirQualityStation.objects.get(id=station_id)
    readings_count = PollutantReading.objects.filter(
        station_id=station_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date,
        is_valid=True
    ).count()
    print(f'{station.name} (ID: {station_id}): {readings_count} readings')

# Check what parameters are available
all_readings = PollutantReading.objects.filter(
    station_id__in=station_ids,
    timestamp__gte=start_date,
    timestamp__lte=end_date,
    is_valid=True
).values('parameter').distinct()

print(f'\nAvailable parameters: {[r["parameter"] for r in all_readings]}')

# Check total readings in the system
total_readings = PollutantReading.objects.count()
print(f'\nTotal readings in system: {total_readings}')

# Check date range of readings
if total_readings > 0:
    earliest = PollutantReading.objects.order_by('timestamp').first().timestamp
    latest = PollutantReading.objects.order_by('-timestamp').first().timestamp
    print(f'Date range: {earliest} to {latest}')