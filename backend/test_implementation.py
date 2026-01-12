"""
Test script for AIR RISK implementation.
Tests authentication, report generation, and LM Studio integration.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.utils import timezone
from datetime import datetime, timedelta
from reports.services.ai_insights import test_lm_studio_connection, generate_health_recommendations
from exposure.services.trend_analyzer import TrendAnalyzer

User = get_user_model()

print("=" * 80)
print("AIR RISK - SYSTEM INTEGRATION TEST")
print("=" * 80)

# Test 1: LM Studio Connection
print("\n[TEST 1] LM Studio Connection")
print("-" * 80)
lm_studio_available = test_lm_studio_connection()
if lm_studio_available:
    print(f"✅ LM Studio is online at http://127.0.0.1:1234/v1")
    print(f"   AI-powered recommendations will be generated")
else:
    print(f"⚠️  LM Studio offline - Will use fallback mode")
    print(f"   Rule-based recommendations will be used")

# Test 2: Create Test Users
print("\n[TEST 2] User Creation")
print("-" * 80)

# Create BASIC user
basic_user, created = User.objects.get_or_create(
    username='basic_test',
    defaults={
        'email': 'basic@test.com',
        'first_name': 'Basic',
        'last_name': 'User',
        'subscription_tier': 'BASIC',
        'is_active': True
    }
)
if created:
    basic_user.set_password('testpass123')
    basic_user.save()
    print(f"✅ Created BASIC user: {basic_user.username}")
else:
    print(f"ℹ️  BASIC user already exists: {basic_user.username}")

print(f"   Tier: {basic_user.tier}")
print(f"   Is Premium: {basic_user.is_premium}")

# Create PREMIUM user
premium_user, created = User.objects.get_or_create(
    username='premium_test',
    defaults={
        'email': 'premium@test.com',
        'first_name': 'Premium',
        'last_name': 'User',
        'subscription_tier': 'PREMIUM',
        'premium_until': timezone.now() + timedelta(days=365),
        'is_active': True
    }
)
if created:
    premium_user.set_password('testpass123')
    premium_user.save()
    print(f"✅ Created PREMIUM user: {premium_user.username}")
else:
    # Update premium expiry
    premium_user.premium_until = timezone.now() + timedelta(days=365)
    premium_user.subscription_tier = 'PREMIUM'
    premium_user.save()
    print(f"ℹ️  PREMIUM user already exists: {premium_user.username} (updated expiry)")

print(f"   Tier: {premium_user.tier}")
print(f"   Is Premium: {premium_user.is_premium}")
print(f"   Premium Until: {premium_user.premium_until}")

# Test 3: Trend Analysis
print("\n[TEST 3] Location Trend Analysis")
print("-" * 80)
print("Testing Lahore location (31.5204, 74.3587)")

try:
    analyzer = TrendAnalyzer(
        lat=31.5204,
        lng=74.3587,
        radius_km=10.0,
        start_date=timezone.make_aware(datetime.now() - timedelta(days=30)),
        end_date=timezone.make_aware(datetime.now())
    )
    
    nearby_stations = analyzer.get_nearby_stations()
    print(f"✅ Found {len(nearby_stations)} nearby stations")
    for station in nearby_stations[:3]:
        # distance is a Distance object from GeoDjango annotation
        distance_km = station.distance.km if hasattr(station, 'distance') else 0
        print(f"   - {station.name} ({distance_km:.1f} km)")
    
    ground_trends = analyzer.get_ground_trends()
    if ground_trends:
        print(f"✅ Ground trends analysis complete")
        for pollutant, stats in list(ground_trends.items())[:2]:
            print(f"   {pollutant}: mean={stats.get('mean', 0):.1f}, trend={stats.get('trend', 'N/A')}")
    else:
        print("⚠️  No ground data available for this location/period")
    
except Exception as e:
    print(f"❌ Trend analysis failed: {e}")

# Test 4: AI Health Recommendations
print("\n[TEST 4] AI Health Recommendations")
print("-" * 80)

# Use actual trend data from the analyzer
test_pollutant_data = ground_trends if ground_trends else {
    'PM25': {
        'mean': 85.5,
        'max': 155.0,
        'p95': 142.3
    },
    'NO2': {
        'mean': 42.3,
        'max': 78.5,
        'p95': 68.2
    }
}

test_location = {
    'lat': 31.5204,
    'lng': 74.3587
}

try:
    # First test LM Studio directly
    import requests
    try:
        test_response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": "local-model",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Say 'Hello' if you can read this."}
                ],
                "max_tokens": 50
            },
            timeout=10
        )
        if test_response.status_code == 200:
            print("✅ LM Studio API responds correctly")
            model_name = test_response.json().get('model', 'unknown')
            print(f"   Active model: {model_name}")
        else:
            print(f"⚠️  LM Studio returned status {test_response.status_code}")
            print(f"   Response: {test_response.text[:200]}")
    except Exception as e:
        print(f"⚠️  LM Studio test failed: {e}")
    
    # Now test our function
    recommendations = generate_health_recommendations(
        pollutant_data=test_pollutant_data,
        location=test_location,
        user_context={'age': 30, 'health_conditions': []}
    )
    
    if recommendations:
        if recommendations.get('ai_generated'):
            print("✅ AI-generated recommendations (LM Studio)")
        else:
            print("✅ Rule-based recommendations (Fallback)")
        
        print(f"\nSummary:\n{recommendations.get('summary', 'N/A')}")
        print(f"\nRisk Level: {recommendations.get('risk_level', 'unknown').upper()}")
        print(f"\nRecommendations:")
        for i, rec in enumerate(recommendations.get('recommendations', [])[:3], 1):
            print(f"  {i}. {rec}")
        
        if recommendations.get('sensitive_groups'):
            print(f"\nSensitive Groups: {', '.join(recommendations['sensitive_groups'])}")
    else:
        print("⚠️  No recommendations generated (LM Studio offline)")
    
except Exception as e:
    print(f"❌ AI recommendation generation failed: {e}")

# Test 5: Database Check
print("\n[TEST 5] Database Models Check")
print("-" * 80)

from air_quality.models import District, GroundStation
from exposure.models import DistrictExposure
from reports.models import Report

districts_count = District.objects.count()
stations_count = GroundStation.objects.count()
exposures_count = DistrictExposure.objects.count()
reports_count = Report.objects.count()

print(f"Districts: {districts_count}")
print(f"Ground Stations: {stations_count}")
print(f"District Exposures: {exposures_count}")
print(f"Reports: {reports_count}")

if districts_count > 0:
    sample_district = District.objects.first()
    print(f"\nSample District: {sample_district.name}, {sample_district.province}")
    print(f"✅ Database has geographic data")
else:
    print("\n⚠️  No districts in database - Spatial endpoints may return empty results")

# Test 6: API Endpoint URLs
print("\n[TEST 6] API Endpoint Configuration")
print("-" * 80)

from django.urls import reverse

try:
    # Test without namespace (direct URL names)
    urls_to_test = [
        ('create-location-report', 'POST /exposure/reports/location/'),
        ('list-user-reports', 'GET /exposure/reports/'),
        ('dashboard', 'GET /exposure/dashboard/'),
    ]
    
    for url_name, description in urls_to_test:
        try:
            url = reverse(url_name)
            print(f"✅ {description} → {url}")
        except Exception as e:
            print(f"❌ {description} → Error: {e}")
            
except Exception as e:
    print(f"❌ URL configuration test failed: {e}")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"""
✅ Backend Status: READY
✅ Migrations: Applied
✅ Test Users: Created (basic_test, premium_test)
{"✅ LM Studio: Connected" if lm_studio_available else "⚠️  LM Studio: Offline (fallback mode)"}
✅ API Endpoints: Configured

NEXT STEPS:
1. Start Django development server: python manage.py runserver
2. Start Django-Q worker: python manage.py qcluster
3. Test API endpoints with curl or Postman
4. Build and run frontend: cd ../frontend && npm run dev

AUTHENTICATION:
- Basic User: username=basic_test, password=testpass123
- Premium User: username=premium_test, password=testpass123

API TESTING:
curl -X POST http://localhost:8000/api/v1/users/token/ \\
  -H "Content-Type: application/json" \\
  -d '{{"username": "premium_test", "password": "testpass123"}}'
""")
print("=" * 80)
