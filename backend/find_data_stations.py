import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.base')
django.setup()

from air_quality.models import PollutantReading, AirQualityStation
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance as DistanceFunc

# Find stations that have readings in the last 30 days
start_date = timezone.make_aware(datetime.now() - timedelta(days=30))
end_date = timezone.make_aware(datetime.now())

stations_with_data = PollutantReading.objects.filter(
    timestamp__gte=start_date,
    timestamp__lte=end_date,
    is_valid=True
).values('station').distinct()

print(f'Stations with data in last 30 days: {len(stations_with_data)}')

# Get details of first few stations with data
for i, station_data in enumerate(stations_with_data[:5]):
    station_id = station_data['station']
    station = AirQualityStation.objects.get(id=station_id)
    readings_count = PollutantReading.objects.filter(
        station_id=station_id,
        timestamp__gte=start_date,
        timestamp__lte=end_date,
        is_valid=True
    ).count()

    print(f'{i+1}. {station.name} (ID: {station.id}) - {readings_count} readings')
    print(f'   Location: {station.latitude:.4f}, {station.longitude:.4f}')

# Check if any stations with data are near Lahore
lahore_point = Point(74.3587, 31.5204, srid=4326)  # Note: lng, lat for Point
nearby_stations = AirQualityStation.objects.filter(
    location__distance_lte=(lahore_point, D(km=50))
).annotate(distance=DistanceFunc('location', lahore_point)).order_by('distance')[:10]

print(f'\nStations within 50km of Lahore:')
for station in nearby_stations:
    has_data = PollutantReading.objects.filter(
        station_id=station.id,
        timestamp__gte=start_date,
        timestamp__lte=end_date,
        is_valid=True
    ).exists()
    data_status = "HAS DATA" if has_data else "no data"
    print(f'  {station.name} ({station.distance.km:.1f} km) - {data_status}')