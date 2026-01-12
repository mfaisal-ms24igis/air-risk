#!/usr/bin/env python
"""
Synchronous script to fetch ground data from OpenAQ and store in database.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "air_risk.settings.dev")
django.setup()

from air_quality.services.openaq import get_openaq_client
from air_quality.services.base_service import BaseService
from air_quality.models import GroundReading, GroundStation


class OpenAQDataIngestion(BaseService):
    """
    Class for ingesting OpenAQ data.
    """

    def __init__(self):
        super().__init__()
        self.client = get_openaq_client()

    def fetch_and_store_data(self, city: str = "Lahore", days_back: int = 1,
                           start_date: datetime = None, end_date: datetime = None) -> int:
        """
        Fetch recent air quality data and store in database.

        Args:
            city: City name (currently ignored, fetches Pakistan data)
            days_back: Number of days back to fetch
            start_date: Optional specific start date (for testing)
            end_date: Optional specific end date (for testing)

        Returns:
            Number of new readings stored
        """
        # Calculate date range
        if start_date and end_date:
            # Use provided dates for testing
            start_dt = start_date
            end_dt = end_date
        else:
            # Default: fetch from yesterday back
            end_dt = datetime.now() - timedelta(days=1)
            start_dt = end_dt - timedelta(days=days_back)

        print(f"Fetching OpenAQ data from {start_dt.date()} to {end_dt.date()}")

        # Fetch data
        data = self.client.fetch_readings(
            start_date=start_dt.date(),
            end_date=end_dt.date()
        )

        stored_count = 0
        for measurement in data:
            try:
                stored_count += self._process_measurement(measurement)
            except Exception as e:
                print(f"Error processing measurement: {e}")

        print(f"Stored {stored_count} new readings")
        return stored_count

    def _process_measurement(self, measurement: Dict) -> int:
        """
        Process a single measurement and store if new.

        Returns:
            1 if stored, 0 if already exists
        """
        # Extract data
        location = measurement['location']
        coordinates = measurement['coordinates']
        date_utc = measurement['date']['utc']
        parameter = measurement['parameter']
        value = measurement['value']
        unit = measurement['unit']
        location_id = measurement['location_id']

        # Get or create station
        station, _ = GroundStation.objects.get_or_create(
            openaq_id=str(location_id),
            defaults={
                'name': location,
                'location': f"POINT({coordinates['longitude']} {coordinates['latitude']})"
            }
        )

        # Map parameter to field
        field_map = {
            'no2': 'no2',
            'so2': 'so2',
            'pm25': 'pm25',
            'co': 'co',
            'o3': 'o3'
        }
        field = field_map.get(parameter.lower())
        if not field:
            self.log_warning(f"Unknown parameter: {parameter}")
            return 0

        # Create reading
        reading, created = GroundReading.objects.get_or_create(
            station=station,
            timestamp=date_utc,
            defaults={field: value, 'raw_data': measurement}
        )

        if not created and getattr(reading, field) is None:
            # Update if the field was null
            setattr(reading, field, value)
            reading.save()
            created = True

        return 1 if created else 0


if __name__ == "__main__":
    ingestion = OpenAQDataIngestion()
    ingestion.fetch_and_store_data()