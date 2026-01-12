"""
OpenAQ API client for ground station data.
Fetches air quality readings from ground monitoring stations.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Generator

from openaq import OpenAQ
from django.conf import settings
from django.utils import timezone

from ..models import AirQualityStation, PollutantReading

logger = logging.getLogger(__name__)


class OpenAQError(Exception):
    """OpenAQ API error."""

    pass


class OpenAQClient:
    """
    Client for OpenAQ API v3 using official library.
    Fetches ground station data for Pakistan.
    """

    def __init__(self):
        self.client = OpenAQ(api_key=settings.OPENAQ_API_KEY)

    def fetch_pakistan_stations(self) -> list[dict]:
        """
        Fetch all air quality stations in Pakistan.

        Returns:
            List of station dictionaries
        """
        logger.info("Fetching Pakistan stations from OpenAQ")

        try:
            locations_response = self.client.locations.list(iso="PK", limit=1000)

            # Convert to our expected format
            stations = []
            for location in locations_response.results:
                station_dict = {
                    "id": location.id,
                    "name": location.name,
                    "locality": location.locality,
                    "timezone": location.timezone,
                    "country": location.country.code,
                    "coordinates": {
                        "latitude": location.coordinates.latitude,
                        "longitude": location.coordinates.longitude
                    },
                    "parameters": [sensor.parameter.name for sensor in location.sensors],
                    "sensors": [
                        {
                            "id": sensor.id,
                            "parameter": sensor.parameter.name,
                            "units": sensor.parameter.units
                        }
                        for sensor in location.sensors
                    ]
                }
                stations.append(station_dict)

            logger.info(f"Found {len(stations)} stations in Pakistan")
            return stations

        except Exception as e:
            logger.error(f"Error fetching Pakistan stations: {e}")
            raise OpenAQError(f"Failed to fetch stations: {e}")

    def sync_stations(self) -> tuple[int, int]:
        """
        Sync ground stations from OpenAQ to database.

        Returns:
            Tuple of (created_count, updated_count)
        """
        from django.contrib.gis.geos import Point

        stations_data = self.fetch_pakistan_stations()
        
        # Sort stations by number of available pollutant parameters (descending)
        # to prioritize stations with more data
        def count_pollutant_params(station):
            params = station.get("parameters", [])
            pollutant_count = 0
            for param in params:
                if isinstance(param, dict):
                    param_name = param.get("parameter", "").upper()
                else:
                    param_name = str(param).upper()
                if param_name in ["NO2", "SO2", "PM25", "PM2.5", "CO", "O3"]:
                    pollutant_count += 1
            return pollutant_count
        
        # Remove artificial limit - sync all available stations
        # stations_data.sort(key=count_pollutant_params, reverse=True)
        # top_stations = stations_data[:30]
        
        logger.info(f"Processing all {len(stations_data)} stations")
        
        created = 0
        updated = 0

        for station_data in stations_data:
            location_id = station_data.get("id")
            if not location_id:
                continue

            # Extract coordinates
            coordinates = station_data.get("coordinates", {})
            lat = coordinates.get("latitude")
            lon = coordinates.get("longitude")

            if not lat or not lon:
                continue

            # Extract available parameters
            parameters = []
            for param in station_data.get("parameters", []):
                # Handle both dict and string parameter formats
                if isinstance(param, dict):
                    param_name = param.get("parameter", "").upper()
                else:
                    param_name = str(param).upper()
                
                if param_name in ["NO2", "SO2", "PM25", "CO", "O3"]:
                    parameters.append(param_name)
                elif param_name == "PM2.5":
                    parameters.append("PM25")

            # Create or update station
            station, is_created = AirQualityStation.objects.update_or_create(
                openaq_location_id=location_id,
                defaults={
                    "openaq_id": str(location_id),
                    "name": station_data.get("name", f"Station {location_id}"),
                    "latitude": lat,
                    "longitude": lon,
                    "city": station_data.get("city", ""),
                    "country": "PK",
                    "available_parameters": parameters,
                    "is_active": True,
                    "last_reading_at": timezone.now(),
                },
            )

            if is_created:
                created += 1
            else:
                updated += 1

        logger.info(f"Synced stations: {created} created, {updated} updated")
        return created, updated

    def fetch_readings(
        self,
        start_date: date,
        end_date: date,
        station_ids: list[int] = None,
        parameters: list[str] = None,
    ) -> list[dict]:
        """
        Fetch air quality readings for a date range using bulk country query.

        Args:
            start_date: Start of date range
            end_date: End of date range
            station_ids: Optional list of OpenAQ location IDs
            parameters: Optional list of parameters to fetch

        Returns:
            List of reading dictionaries
        """
        logger.info(f"Fetching readings from {start_date} to {end_date} for Pakistan")

        readings = []
        location_cache = {}  # Cache location details to avoid repeated queries

        try:
            # Get locations first to build cache
            locations_response = self.client.locations.list(iso="PK", limit=1000)
            for loc in locations_response.results:
                location_cache[loc.id] = {
                    "name": loc.name,
                    "latitude": loc.coordinates.latitude,
                    "longitude": loc.coordinates.longitude
                }

            # Filter locations if specific IDs requested
            target_locations = [loc for loc in locations_response.results 
                              if not station_ids or loc.id in station_ids]
            
            # Set up parameter filter if specified
            if parameters:
                param_filter = [p.upper() for p in parameters]
            else:
                param_filter = None
            
            logger.info(f"Fetching measurements for {len(target_locations)} locations")
            
            # OpenAQ v3 requires sensor IDs to fetch measurements
            # Get all sensors from our target locations
            sensor_ids = []
            for loc in target_locations:
                try:
                    # Fetch sensors for this location
                    sensors_response = self.client.sensors.list(locations_id=loc.id, limit=100)
                    for sensor in sensors_response.results:
                        # Filter by parameter if specified
                        if param_filter and sensor.parameter.name.upper() not in param_filter:
                            continue
                        sensor_ids.append(sensor.id)
                except Exception as sensor_error:
                    logger.warning(f"Failed to fetch sensors for location {loc.id}: {sensor_error}")
                    continue
            
            if not sensor_ids:
                logger.warning("No sensors found for target locations")
                return []
            
            logger.info(f"Found {len(sensor_ids)} sensors across {len(target_locations)} locations")
            
            # Fetch measurements by sensor IDs and date range
            measurement_params = {
                "sensors_id": sensor_ids,
                "datetime_from": f"{start_date.isoformat()}T00:00:00Z",
                "datetime_to": f"{(end_date + timedelta(days=1)).isoformat()}T00:00:00Z",
                "limit": 10000  # Get more results per page
            }

            # Fetch measurements (will get global results, filter by Pakistan locations)
            try:
                measurements_response = self.client.measurements.list(**measurement_params)
            except Exception as api_error:
                # If the API call fails, log and return empty (graceful degradation)
                logger.warning(f"OpenAQ API error: {api_error}. Returning empty results.")
                return []

            # Filter and convert to our expected format
            pakistan_location_ids = {loc.id for loc in target_locations}
            
            for measurement in measurements_response.results:
                # Get location info from cache
                loc_id = measurement.location_id if hasattr(measurement, 'location_id') else None
                
                # Skip if not a Pakistan location
                if loc_id not in pakistan_location_ids:
                    continue
                
                # Skip if parameter filter specified and doesn't match
                if param_filter and measurement.parameter.name.upper() not in param_filter:
                    continue
                
                loc_info = location_cache.get(loc_id, {})

                reading_dict = {
                    "location": loc_info.get("name", "Unknown"),
                    "coordinates": {
                        "latitude": loc_info.get("latitude"),
                        "longitude": loc_info.get("longitude")
                    },
                    "date": {
                        "utc": measurement.period.datetime_from.utc
                    },
                    "parameter": measurement.parameter.name,
                    "value": measurement.value,
                    "unit": measurement.parameter.units,
                    "location_id": loc_id,
                    "sensor_id": measurement.sensors_id if hasattr(measurement, 'sensors_id') else None
                }
                readings.append(reading_dict)

        except Exception as e:
            logger.error(f"Error fetching readings: {e}")
            raise OpenAQError(f"Failed to fetch readings: {e}")

        logger.info(f"Fetched {len(readings)} readings for Pakistan")
        return readings

    def sync_readings(
        self,
        start_date: date,
        end_date: date = None,
    ) -> int:
        """
        Sync readings from OpenAQ to database for active stations only.

        Args:
            start_date: Start of date range
            end_date: End of date range (defaults to start_date)

        Returns:
            Number of readings synced
        """
        from air_quality.models import AirQualityStation
        
        if end_date is None:
            end_date = start_date

        # Get only active station IDs from our database
        active_station_ids = list(
            AirQualityStation.objects.filter(is_active=True)
            .values_list('openaq_location_id', flat=True)
        )
        
        logger.info(f"Fetching readings for {len(active_station_ids)} active stations")

        # Map OpenAQ parameter names to our field names
        param_map = {
            "no2": "no2",
            "so2": "so2",
            "pm25": "pm25",
            "pm2.5": "pm25",
            "co": "co",
            "o3": "o3",
        }

        readings_data = self.fetch_readings(
            start_date, 
            end_date, 
            station_ids=active_station_ids,  # Only fetch for active stations
            parameters=["no2", "so2", "pm25", "co", "o3"]
        )

        # Group readings by station and timestamp
        grouped = {}
        for reading in readings_data:
            location_id = reading.get("location", {}).get("id")
            if not location_id:
                continue

            timestamp = reading.get("date", {}).get("utc")
            if not timestamp:
                continue

            # Parse timestamp
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue

            key = (str(location_id), dt)
            if key not in grouped:
                grouped[key] = {
                    "openaq_id": str(location_id),
                    "timestamp": dt,
                    "values": {},
                    "raw_data": [],
                }

            # Add value
            param = reading.get("parameter", "").lower()
            field = param_map.get(param)
            if field:
                value = reading.get("value")
                if value is not None:
                    grouped[key]["values"][field] = value

            grouped[key]["raw_data"].append(reading)

        # Bulk create/update readings
        created_count = 0

        for (openaq_id, timestamp), data in grouped.items():
            try:
                station = AirQualityStation.objects.get(openaq_location_id=int(openaq_id))
            except AirQualityStation.DoesNotExist:
                continue

            # Create individual readings for each parameter
            # The new model stores one row per parameter (normalized)
            for param, value in data["values"].items():
                if value is None:
                    continue
                    
                # Map field name back to Pollutant enum if needed
                # (param_map keys are already close to Pollutant values)
                pollutant_code = param.upper()
                if pollutant_code == "PM2.5":
                    pollutant_code = "PM25"
                
                # Find the unit for this parameter from raw data
                unit = "unknown"
                for raw in data["raw_data"]:
                    if raw.get("parameter") == param or (param == "pm25" and raw.get("parameter") == "pm2.5"):
                        unit = raw.get("unit", "unknown")
                        break

                PollutantReading.objects.update_or_create(
                    station=station,
                    timestamp=timestamp,
                    parameter=pollutant_code,
                    defaults={
                        "value": value,
                        "unit": unit,
                        "is_valid": True,
                    },
                )
                created_count += 1
            
            # Legacy code removed - we don't use GroundReading anymore
            """
            reading, created = GroundReading.objects.update_or_create(
                station=station,
                timestamp=timestamp,
                defaults={
                    "no2": data["values"].get("no2"),
                    "so2": data["values"].get("so2"),
                    "pm25": data["values"].get("pm25"),
                    "co": data["values"].get("co"),
                    "o3": data["values"].get("o3"),
                    "raw_data": data["raw_data"],
                },
            )

            if created:
                created_count += 1
            """

        logger.info(f"Synced {created_count} new readings")
        return created_count

    def backfill_historical(self, days: int = 180) -> int:
        """
        Backfill historical readings for the past N days.

        Args:
            days: Number of days to backfill

        Returns:
            Total readings synced
        """
        logger.info(f"Backfilling {days} days of historical data")

        total = 0
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Process in weekly chunks to avoid API limits
        chunk_start = start_date
        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=7), end_date)

            try:
                count = self.sync_readings(chunk_start, chunk_end)
                total += count
                logger.info(
                    f"Backfilled {chunk_start} to {chunk_end}: {count} readings"
                )
            except OpenAQError as e:
                logger.error(f"Backfill error for {chunk_start} to {chunk_end}: {e}")

            chunk_start = chunk_end + timedelta(days=1)

        logger.info(f"Backfill complete: {total} total readings")
        return total


# Singleton instance
openaq_client = OpenAQClient()


def get_openaq_client():
    """Get the OpenAQ client instance."""
    return openaq_client
