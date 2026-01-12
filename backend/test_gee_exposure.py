"""
Test script for GEE-based pixel-wise exposure calculation.

Run from backend directory:
    python test_gee_exposure.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.dev')
django.setup()

from datetime import date, timedelta
from air_quality.models import District
from exposure.services.gee_exposure import get_gee_exposure_service


def test_single_district():
    """Test GEE exposure calculation for a single district."""
    print("=" * 80)
    print("TEST: Single District GEE Exposure Calculation")
    print("=" * 80)
    
    # Get Lahore district
    try:
        lahore = District.objects.get(name__iexact='Lahore')
        print(f"\n✓ Found district: {lahore.name} (ID: {lahore.id})")
        print(f"  Province: {lahore.province}")
        print(f"  Population: {lahore.population:,}")
        print(f"  Area: {lahore.area_km2:.2f} km²")
    except District.DoesNotExist:
        print("\n✗ Lahore district not found. Using first district instead.")
        lahore = District.objects.first()
        if not lahore:
            print("\n✗ No districts found in database!")
            return False
        print(f"\n✓ Using district: {lahore.name} (ID: {lahore.id})")
    
    # Calculate exposure
    print("\n" + "-" * 80)
    print("Calculating pixel-wise exposure on Google Earth Engine...")
    print("-" * 80)
    
    gee_service = get_gee_exposure_service()
    # Use a date 7 days ago to ensure data availability
    target_date = date.today() - timedelta(days=7)
    
    try:
        result = gee_service.calculate_exposure_for_geometry(
            geometry=lahore.geometry,
            target_date=target_date,
            days_back=7,
        )
        
        # Print results
        print("\n✓ Calculation successful!")
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        
        print(f"\nDistrict: {lahore.name}")
        print(f"Date: {result.calculation_date}")
        print(f"Data Source: {result.data_source}")
        print(f"Resolution: {result.resolution_meters:.1f} meters")
        
        print(f"\n--- POPULATION STATISTICS ---")
        print(f"Total Population: {result.total_population:,}")
        
        print(f"\n--- AIR QUALITY STATISTICS ---")
        print(f"Mean AQI: {result.mean_aqi:.1f}")
        print(f"Max AQI: {result.max_aqi:.1f}")
        print(f"Dominant Pollutant: {result.dominant_pollutant}")
        
        print(f"\n--- EXPOSURE STATISTICS ---")
        print(f"Mean Exposure Index: {result.mean_exposure_index:.2f}")
        print(f"Max Exposure Index: {result.max_exposure_index:.2f}")
        
        print(f"\n--- POPULATION BY AQI CATEGORY ---")
        total_pop = result.total_population
        categories = [
            ("Good (0-50)", result.pop_good),
            ("Moderate (51-100)", result.pop_moderate),
            ("USG (101-150)", result.pop_unhealthy_sensitive),
            ("Unhealthy (151-200)", result.pop_unhealthy),
            ("Very Unhealthy (201-300)", result.pop_very_unhealthy),
            ("Hazardous (>300)", result.pop_hazardous),
        ]
        
        for category, pop in categories:
            pct = (pop / total_pop * 100) if total_pop > 0 else 0
            print(f"{category:30s}: {pop:10,} ({pct:5.1f}%)")
        
        print(f"\n--- POLLUTANT CONCENTRATIONS ---")
        if result.mean_pm25:
            print(f"PM2.5: {result.mean_pm25:.2f} µg/m³")
        if result.mean_no2:
            print(f"NO2: {result.mean_no2:.2f} ppb")
        if result.mean_so2:
            print(f"SO2: {result.mean_so2:.2f} ppb")
        if result.mean_co:
            print(f"CO: {result.mean_co:.2f} ppm")
        
        print(f"\n--- TILE URLS (for frontend visualization) ---")
        print(f"Exposure Tile: {result.exposure_tile_url[:80]}...")
        print(f"AQI Tile: {result.aqi_tile_url[:80]}...")
        print(f"Map ID: {result.map_id}")
        print(f"Token: {result.token[:20]}...")
        
        if result.errors:
            print(f"\n⚠ WARNINGS:")
            for error in result.errors:
                print(f"  - {error}")
        
        print("\n" + "=" * 80)
        return True
        
    except Exception as e:
        print(f"\n✗ Error calculating exposure: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoint():
    """Test the API endpoint programmatically."""
    print("\n\n" + "=" * 80)
    print("TEST: API Endpoint")
    print("=" * 80)
    
    print("\nTo test the API endpoint, use curl or a REST client:")
    print("\n1. Single District (synchronous):")
    print("   POST http://localhost:8000/api/v1/exposure/calculate-gee/")
    print("   Content-Type: application/json")
    print("   {")
    print('     "scope": "district",')
    print('     "district_ids": [1],')
    print('     "target_date": "2024-12-14",')
    print('     "days_back": 7,')
    print('     "save_results": false')
    print("   }")
    
    print("\n2. Province (async):")
    print("   POST http://localhost:8000/api/v1/exposure/calculate-gee/")
    print("   Content-Type: application/json")
    print("   {")
    print('     "scope": "province",')
    print('     "province": "Punjab",')
    print('     "target_date": "2024-12-14",')
    print('     "async": true,')
    print('     "save_results": true')
    print("   }")
    
    print("\n3. Check Task Status:")
    print("   GET http://localhost:8000/api/v1/exposure/calculate-gee/?task_id=<task_id>")
    
    print("\n" + "=" * 80)


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "  GEE-BASED PIXEL-WISE EXPOSURE CALCULATION TEST SUITE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    success = test_single_district()
    
    test_api_endpoint()
    
    print("\n" + "=" * 80)
    if success:
        print("✓ TEST PASSED")
    else:
        print("✗ TEST FAILED")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
