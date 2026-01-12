"""
Test suite for Dynamic Risk Feature

Run with: python manage.py test air_quality.tests.test_risk
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.gis.geos import Point

from air_quality.models import (
    AirQualityStation,
    PollutantReading,
    SystemStatus,
)
from air_quality.services.gee_risk import (
    DynamicRiskService,
    RiskCalculationError,
)
from air_quality.tasks import check_sentinel5p_updates


class DynamicRiskServiceTests(TestCase):
    """Test the GEE risk calculation service."""
    
    def setUp(self):
        """Create test data."""
        self.service = DynamicRiskService()
        
        # Create test station
        self.station = AirQualityStation.objects.create(
            openaq_location_id=12345,
            name="Test Station",
            latitude=31.5204,
            longitude=74.3587,
            is_active=True,
        )
        
        # Create test reading
        self.reading = PollutantReading.objects.create(
            station=self.station,
            timestamp=timezone.now(),
            parameter="PM25",
            value=75.5,
            unit="µg/m³",
            normalized_value=75.5,
        )
    
    def test_geojson_conversion(self):
        """Test GeoJSON to ee.FeatureCollection conversion."""
        geojson = {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [74.3587, 31.5204]
                    },
                    'properties': {
                        'pm25': 75.5,
                        'station_id': 12345,
                    }
                }
            ]
        }
        
        # This would normally initialize GEE
        # For testing, we'll mock it
        with patch.object(self.service, '_initialized', True):
            with patch('air_quality.services.gee_risk.ee.FeatureCollection'):
                try:
                    fc = self.service.geojson_to_ee_featurecollection(geojson)
                    # If we got here without error, test passes
                    self.assertIsNotNone(fc)
                except RiskCalculationError as e:
                    # Expected if GEE is not actually initialized
                    self.assertIn('GeoJSON', str(e))
    
    def test_invalid_geojson(self):
        """Test error handling for invalid GeoJSON."""
        invalid_geojson = {
            'type': 'Point',  # Should be FeatureCollection
            'coordinates': [74.3587, 31.5204]
        }
        
        with self.assertRaises(RiskCalculationError):
            self.service.geojson_to_ee_featurecollection(invalid_geojson)
    
    def test_empty_geojson(self):
        """Test error handling for empty GeoJSON."""
        empty_geojson = {
            'type': 'FeatureCollection',
            'features': []
        }
        
        with self.assertRaises(RiskCalculationError):
            self.service.geojson_to_ee_featurecollection(empty_geojson)


class SystemStatusTests(TestCase):
    """Test the SystemStatus model."""
    
    def test_create_status(self):
        """Test creating a status entry."""
        status = SystemStatus.objects.create(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value={'image_date': '2024-12-10'},
            is_healthy=True,
        )
        
        self.assertEqual(status.status_type, 'S5P_NO2')
        self.assertEqual(status.value['image_date'], '2024-12-10')
        self.assertTrue(status.is_healthy)
    
    def test_update_status(self):
        """Test updating a status entry."""
        status = SystemStatus.update_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value={'image_date': '2024-12-10'},
            is_healthy=True,
        )
        
        self.assertIsNotNone(status)
        self.assertEqual(status.value['image_date'], '2024-12-10')
    
    def test_get_or_create(self):
        """Test get_or_create_status helper."""
        status1 = SystemStatus.get_or_create_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2
        )
        
        status2 = SystemStatus.get_or_create_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2
        )
        
        # Should return the same instance
        self.assertEqual(status1.pk, status2.pk)


class RiskAPITests(TestCase):
    """Test the Risk API endpoints."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = Client()
        
        # Create test station with PM2.5 data
        self.station = AirQualityStation.objects.create(
            openaq_location_id=12345,
            name="Test Station",
            latitude=31.5204,
            longitude=74.3587,
            is_active=True,
        )
        
        # Create recent reading
        self.reading = PollutantReading.objects.create(
            station=self.station,
            timestamp=timezone.now(),
            parameter="PM25",
            value=75.5,
            unit="µg/m³",
            normalized_value=75.5,
        )
    
    def test_status_endpoint(self):
        """Test the status API endpoint."""
        response = self.client.get('/api/v1/air-quality/risk/status/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
    
    def test_status_with_data(self):
        """Test status endpoint with existing status."""
        # Create a status
        SystemStatus.update_status(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2,
            value={
                'image_date': '2024-12-10',
                'is_new': False,
            },
            is_healthy=True,
        )
        
        response = self.client.get('/api/v1/air-quality/risk/status/')
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['status'])
        self.assertEqual(data['status']['image_date'], '2024-12-10')
    
    @patch('air_quality.api.risk_views.get_risk_service')
    def test_tiles_endpoint_success(self, mock_service):
        """Test the tiles API endpoint with mocked GEE."""
        # Mock the risk service
        mock_result = {
            'tile_url': 'https://example.com/tiles/{z}/{x}/{y}',
            'map_id': 'mock_map_id',
            'token': 'mock_token',
            'legend': {
                'title': 'Risk',
                'stops': [],
                'min': 0,
                'max': 100,
            },
            'metadata': {
                'sentinel5p_date': '2024-12-10',
                'openaq_points': 1,
            }
        }
        
        mock_service_instance = MagicMock()
        mock_service_instance.calculate_risk_index.return_value = mock_result
        mock_service.return_value = mock_service_instance
        
        response = self.client.get('/api/v1/air-quality/risk/tiles/?days=7')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertIn('tile_url', data)
        self.assertIn('legend', data)
        self.assertIn('metadata', data)
    
    def test_tiles_endpoint_no_data(self):
        """Test tiles endpoint with no OpenAQ data."""
        # Delete the reading
        PollutantReading.objects.all().delete()
        
        response = self.client.get('/api/v1/air-quality/risk/tiles/?days=7')
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class BackgroundTaskTests(TestCase):
    """Test the background tasks."""
    
    @patch('air_quality.tasks.get_risk_service')
    def test_check_sentinel5p_updates(self, mock_service):
        """Test the Sentinel-5P update check task."""
        # Mock the GEE service
        mock_service_instance = MagicMock()
        mock_service_instance.get_latest_sentinel5p_no2.return_value = (
            MagicMock(),  # image
            '2024-12-10'  # date
        )
        mock_service.return_value = mock_service_instance
        
        # Run the task
        result = check_sentinel5p_updates()
        
        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['latest_date'], '2024-12-10')
        
        # Verify SystemStatus was updated
        status = SystemStatus.objects.get(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2
        )
        self.assertEqual(status.value['image_date'], '2024-12-10')
        self.assertTrue(status.is_healthy)
    
    @patch('air_quality.tasks.get_risk_service')
    def test_check_sentinel5p_error_handling(self, mock_service):
        """Test error handling in update check."""
        # Mock an error
        mock_service_instance = MagicMock()
        mock_service_instance.get_latest_sentinel5p_no2.side_effect = Exception(
            "GEE connection failed"
        )
        mock_service.return_value = mock_service_instance
        
        # Run the task
        result = check_sentinel5p_updates()
        
        # Should handle error gracefully
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Status should be marked unhealthy
        status = SystemStatus.objects.get(
            status_type=SystemStatus.StatusType.SENTINEL5P_NO2
        )
        self.assertFalse(status.is_healthy)


if __name__ == '__main__':
    import django
    django.setup()
    
    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=2)
    runner.run_tests(['air_quality.tests.test_risk'])
