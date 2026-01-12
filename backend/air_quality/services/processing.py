from django.db.models import Avg
from air_quality.models import GroundReading, Pollutant
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .base_service import DataProcessor


class DataProcessingService(DataProcessor):
    """
    Service for processing air quality data.
    """

    def __init__(self):
        super().__init__()

    def process(self, data: Any) -> Any:
        """Process data - placeholder."""
        return data

    def calculate_daily_averages(self, pollutant_code: str, days_back: int = 7) -> List[Dict]:
        """
        Calculate daily averages for a pollutant over the last N days.

        Args:
            pollutant_code: Pollutant code (e.g., 'PM25')
            days_back: Number of days to look back

        Returns:
            List of dicts with date and avg_value
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Map pollutant code to field name
        field_map = {
            'PM25': 'pm25',
            'NO2': 'no2',
            'SO2': 'so2',
            'CO': 'co',
            'O3': 'o3'
        }
        field = field_map.get(pollutant_code.upper())
        if not field:
            return []

        readings = GroundReading.objects.filter(
            timestamp__range=(start_date, end_date)
        ).exclude(**{f"{field}__isnull": True}).values('timestamp__date').annotate(
            avg_value=Avg(field)
        ).order_by('timestamp__date')

        return list(readings)

    def get_pollutant_summary(self, pollutant_code: str, days_back: int = 30) -> Dict:
        """
        Get summary statistics for a pollutant.

        Returns:
            Dict with min, max, avg, count
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Map pollutant code to field name
        field_map = {
            'PM25': 'pm25',
            'NO2': 'no2',
            'SO2': 'so2',
            'CO': 'co',
            'O3': 'o3'
        }
        field = field_map.get(pollutant_code.upper())
        if not field:
            return {"min": None, "max": None, "avg": None, "count": 0}

        readings = GroundReading.objects.filter(
            timestamp__range=(start_date, end_date)
        ).exclude(**{f"{field}__isnull": True})

        if not readings:
            return {"min": None, "max": None, "avg": None, "count": 0}

        values = readings.values_list(field, flat=True)
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values)
        }


# Singleton instance
data_processing_service = DataProcessingService()


def get_data_processing_service():
    """Get the data processing service instance."""
    return data_processing_service