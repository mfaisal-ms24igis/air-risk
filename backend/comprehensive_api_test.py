"""
Comprehensive API endpoint testing script.
Tests all endpoints from the manifest, categorizing them as Vital, Ghost, or Danger.
"""

import requests
import json
import time
from typing import Dict, Optional, List, Tuple

BASE_URL = "http://127.0.0.1:8000/api/v1"

class APIEndpointTester:
    def __init__(self):
        self.basic_token: Optional[str] = None
        self.premium_token: Optional[str] = None
        self.session = requests.Session()
        self.session.timeout = 30

        # Categorize endpoints
        self.vital_endpoints = []
        self.ghost_endpoints = []
        self.danger_endpoints = []

    def print_section(self, title: str):
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)

    def print_test(self, endpoint: str, method: str, status_code: int, response_type: str, details: str = ""):
        status_icon = "✅" if status_code < 400 else "❌" if status_code >= 500 else "⚠️"
        print(f"{status_icon} {method} {endpoint} → {status_code} ({response_type})")
        if details:
            print(f"   {details}")

    def categorize_endpoint(self, endpoint: str, status_code: int, response_data: any):
        """Categorize endpoint based on response"""
        if status_code >= 500:
            self.danger_endpoints.append(endpoint)
        elif status_code == 404 or (status_code == 200 and self._is_empty_response(response_data)):
            self.ghost_endpoints.append(endpoint)
        else:
            self.vital_endpoints.append(endpoint)

    def _is_empty_response(self, data) -> bool:
        """Check if response is effectively empty"""
        if data is None:
            return True
        if isinstance(data, (list, dict)) and len(data) == 0:
            return True
        if isinstance(data, dict):
            # Check for empty results
            if 'results' in data and len(data['results']) == 0:
                return True
            if 'count' in data and data['count'] == 0:
                return True
        return False

    def make_request(self, endpoint: str, method: str = "GET", data: Dict = None,
                    headers: Dict = None, auth_token: str = None) -> Tuple[int, str, any]:
        """Make HTTP request and return status, content-type, and parsed data"""
        url = f"{BASE_URL}{endpoint}"
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"

        try:
            if method == "GET":
                response = self.session.get(url, headers=request_headers)
            elif method == "POST":
                request_headers["Content-Type"] = "application/json"
                response = self.session.post(url, json=data, headers=request_headers)
            else:
                return 0, "unknown", None

            status_code = response.status_code
            content_type = response.headers.get('content-type', 'unknown')

            # Try to parse JSON
            try:
                if 'application/json' in content_type:
                    response_data = response.json()
                else:
                    response_data = response.text
            except:
                response_data = response.text

            return status_code, content_type, response_data

        except requests.exceptions.RequestException as e:
            return 0, "error", str(e)

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        self.print_section("AUTHENTICATION ENDPOINTS")

        endpoints = [
            ("/auth/login/", "POST", {"username": "basic_test", "password": "testpass123"}),
            ("/auth/register/", "POST", {"username": "test_user", "email": "test@example.com", "password": "testpass123"}),
        ]

        for endpoint, method, data in endpoints:
            status, content_type, response_data = self.make_request(endpoint, method, data)
            self.print_test(endpoint, method, status, content_type.split(';')[0])

            if endpoint == "/auth/login/" and status == 200 and isinstance(response_data, dict):
                self.basic_token = response_data.get('access')
                # Try premium login
                status2, _, response_data2 = self.make_request("/auth/login/", "POST",
                    {"username": "premium_test", "password": "testpass123"})
                if status2 == 200 and isinstance(response_data2, dict):
                    self.premium_token = response_data2.get('access')

            self.categorize_endpoint(endpoint, status, response_data)

    def test_public_endpoints(self):
        """Test public endpoints that don't require auth"""
        self.print_section("PUBLIC ENDPOINTS")

        endpoints = [
            "/exposure/dashboard/",
            "/exposure/districts/",
            "/exposure/hotspots/",
            "/exposure/geojson/districts/",
            "/air-quality/districts/",
            "/air-quality/provinces/",
            "/air-quality/stations/",
            "/air-quality/legend/",
            "/air-quality/gee/layers/",
            "/air-quality/wms/layers/",
        ]

        for endpoint in endpoints:
            status, content_type, response_data = self.make_request(endpoint)
            response_type = content_type.split(';')[0] if isinstance(content_type, str) else "unknown"
            self.print_test(endpoint, "GET", status, response_type)

            # Add details for data endpoints
            if status == 200 and isinstance(response_data, dict):
                if 'results' in response_data:
                    count = len(response_data['results'])
                    print(f"   Returned {count} items")
                elif 'count' in response_data:
                    print(f"   Count: {response_data['count']}")

            self.categorize_endpoint(endpoint, status, response_data)

    def test_protected_endpoints(self):
        """Test endpoints that require authentication"""
        self.print_section("PROTECTED ENDPOINTS")

        if not self.basic_token:
            print("⚠️  Skipping protected endpoints - no auth token")
            return

        endpoints = [
            ("/auth/profile/", "GET", None, "basic"),
            ("/exposure/reports/location/", "POST", {
                "lat": 31.5204, "lng": 74.3587, "radius_km": 10.0, "include_ai_insights": False
            }, "basic"),
            ("/exposure/reports/", "GET", None, "basic"),
        ]

        if self.premium_token:
            endpoints.extend([
                ("/auth/profile/", "GET", None, "premium"),
                ("/exposure/reports/location/", "POST", {
                    "lat": 31.5204, "lng": 74.3587, "radius_km": 15.0, "include_ai_insights": True
                }, "premium"),
                ("/exposure/reports/", "GET", None, "premium"),
                ("/air-quality/spatial/districts/", "GET", None, "premium"),
                ("/air-quality/spatial/stations/nearby/", "GET", None, "premium"),
            ])

        for endpoint, method, data, tier in endpoints:
            token = self.basic_token if tier == "basic" else self.premium_token
            status, content_type, response_data = self.make_request(endpoint, method, data, auth_token=token)
            response_type = content_type.split(';')[0] if isinstance(content_type, str) else "unknown"
            self.print_test(f"{endpoint} ({tier})", method, status, response_type)

            if status == 200 and isinstance(response_data, dict):
                if 'results' in response_data:
                    count = len(response_data['results'])
                    print(f"   Returned {count} items")
                elif 'id' in response_data:
                    print(f"   Created resource ID: {response_data['id']}")

            self.categorize_endpoint(endpoint, status, response_data)

    def test_special_endpoints(self):
        """Test special or potentially problematic endpoints"""
        self.print_section("SPECIAL ENDPOINTS")

        endpoints = [
            "/air-quality/gee/tiles/",  # Requires parameters
            "/air-quality/gee/dates/",  # Requires parameters
            "/air-quality/stations/nearby/",  # Requires lat/lng
            "/air-quality/risk/tiles/",  # New risk endpoints
            "/air-quality/risk/status/",
            "/air-quality/risk/check/",
        ]

        for endpoint in endpoints:
            status, content_type, response_data = self.make_request(endpoint)
            response_type = content_type.split(';')[0] if isinstance(content_type, str) else "unknown"
            self.print_test(endpoint, "GET", status, response_type)

            if status == 400 and isinstance(response_data, dict):
                print(f"   Validation error: {response_data}")

            self.categorize_endpoint(endpoint, status, response_data)

    def test_with_parameters(self):
        """Test endpoints with required parameters"""
        self.print_section("PARAMETERIZED ENDPOINTS")

        # Test with parameters
        param_endpoints = [
            ("/air-quality/stations/nearby/?lat=31.5&lng=74.3&radius=50", "stations nearby"),
            ("/air-quality/gee/tiles/?pollutant=NO2&date=2025-12-01", "GEE tiles"),
            ("/air-quality/gee/dates/?pollutant=NO2", "GEE dates"),
            ("/exposure/districts/?province=PUNJAB", "districts by province"),
        ]

        for endpoint, description in param_endpoints:
            status, content_type, response_data = self.make_request(endpoint)
            response_type = content_type.split(';')[0] if isinstance(content_type, str) else "unknown"
            self.print_test(f"{endpoint} ({description})", "GET", status, response_type)

            if status == 200 and isinstance(response_data, dict):
                if 'results' in response_data:
                    count = len(response_data['results'])
                    print(f"   Returned {count} items")

            self.categorize_endpoint(endpoint, status, response_data)

    def print_summary(self):
        """Print final categorization summary"""
        self.print_section("ENDPOINT CATEGORIZATION SUMMARY")

        print(f"🟢 VITAL ENDPOINTS ({len(self.vital_endpoints)}): Core functionality working")
        for ep in self.vital_endpoints[:10]:  # Show first 10
            print(f"   ✅ {ep}")
        if len(self.vital_endpoints) > 10:
            print(f"   ... and {len(self.vital_endpoints) - 10} more")

        print(f"\n👻 GHOST ENDPOINTS ({len(self.ghost_endpoints)}): Empty/404 responses")
        for ep in self.ghost_endpoints:
            print(f"   ⚠️  {ep}")

        print(f"\n🔴 DANGER ENDPOINTS ({len(self.danger_endpoints)}): Server errors")
        for ep in self.danger_endpoints:
            print(f"   ❌ {ep}")

        print(f"\n📊 SUMMARY:")
        print(f"   Total endpoints tested: {len(self.vital_endpoints + self.ghost_endpoints + self.danger_endpoints)}")
        print(f"   Safe to remove: {len(self.ghost_endpoints)} ghost endpoints")

    def run_all_tests(self):
        """Run comprehensive endpoint testing"""
        print("=" * 80)
        print("AIR RISK API ENDPOINT COMPREHENSIVE TESTING")
        print("Server: http://127.0.0.1:8000/")
        print("=" * 80)

        # Test in order of dependency
        self.test_auth_endpoints()
        self.test_public_endpoints()
        self.test_protected_endpoints()
        self.test_special_endpoints()
        self.test_with_parameters()

        self.print_summary()

        print("\n" + "=" * 80)
        print("TESTING COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    tester = APIEndpointTester()
    tester.run_all_tests()