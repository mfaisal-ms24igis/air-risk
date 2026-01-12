#!/usr/bin/env python3
"""
Test the enhanced GIS-based professional narrative generation.
"""

import os
import sys

# Setup path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Direct import without Django setup to avoid GDAL issues in test
from reports.services.ai_insights import generate_professional_narrative


def test_gis_narrative():
    """Test the enhanced narrative with spatial analysis."""
    
    print("=" * 80)
    print("TESTING GIS-BASED PROFESSIONAL NARRATIVE")
    print("=" * 80)
    
    # Mock comprehensive context data
    context_data = {
        "location": {
            "lat": 31.5204,
            "lng": 74.3587,
            "radius_km": 5.0,
            "district": {
                "name": "Lahore",
                "province": "Punjab",
                "population": 11126285,
                "area_km2": 1772
            }
        },
        "start_date": "2025-12-01",
        "end_date": "2025-12-15",
        "ground_trends": {
            "PM25": {
                "mean": 89.5,
                "max": 156.2,
                "min": 42.3,
                "p95": 145.8
            },
            "PM10": {
                "mean": 165.3,
                "max": 289.4,
                "min": 78.9,
                "p95": 267.1
            },
            "NO2": {
                "mean": 67.8,
                "max": 124.5,
                "min": 32.1,
                "p95": 112.3
            },
            "SO2": {
                "mean": 15.4,
                "max": 34.2,
                "min": 5.6,
                "p95": 29.8
            },
            "CO": {
                "mean": 1.8,
                "max": 3.2,
                "min": 0.9,
                "p95": 2.9
            }
        },
        "gee_data": {
            "no2": {
                "mean": 1.45e-4,
                "max": 2.1e-4,
                "unit": "mol/m²"
            },
            "so2": {
                "mean": 6.2e-5,
                "max": 9.8e-5,
                "unit": "mol/m²"
            },
            "co": {
                "mean": 0.032,
                "max": 0.048,
                "unit": "mol/m²"
            }
        },
        "stations": {
            "count": 4,
            "nearest": {
                "name": "Mall Road Station",
                "distance_km": 2.3
            }
        },
        "historical_baseline": {
            "pm25": 75.2  # Baseline for comparison
        },
        "temporal_patterns": {
            "hourly": {},
            "daily": {}
        }
    }
    
    print("\n📊 Testing with Context Data:")
    print(f"   Location: {context_data['location']['district']['name']}")
    print(f"   PM2.5 Mean: {context_data['ground_trends']['PM25']['mean']:.1f} µg/m³")
    print(f"   NO2 Mean: {context_data['ground_trends']['NO2']['mean']:.1f} µg/m³")
    print(f"   Satellite NO2: {context_data['gee_data']['no2']['mean']:.2e} mol/m²")
    print(f"   Stations: {context_data['stations']['count']}")
    
    print("\n🤖 Generating Professional Narrative...")
    narrative = generate_professional_narrative(context_data)
    
    print("\n" + "=" * 80)
    print("GENERATED PROFESSIONAL NARRATIVE")
    print("=" * 80)
    
    # Display Executive Summary
    if narrative.get("executive_summary"):
        print("\n📋 EXECUTIVE SUMMARY:")
        print("-" * 80)
        print(narrative["executive_summary"])
    
    # Display Geographic Analysis
    if narrative.get("geographic_analysis"):
        print("\n🗺️  GEOGRAPHIC ANALYSIS:")
        print("-" * 80)
        print(narrative["geographic_analysis"])
    
    # Display Source Identification
    if narrative.get("source_identification"):
        print("\n🏭 POLLUTION SOURCE IDENTIFICATION:")
        print("-" * 80)
        print(narrative["source_identification"])
    
    # Display Trend Narrative
    if narrative.get("trend_narrative"):
        print("\n📈 TEMPORAL TREND ANALYSIS:")
        print("-" * 80)
        print(narrative["trend_narrative"])
    
    # Display Forecast & Advisory
    if narrative.get("forecast_advisory"):
        print("\n🔮 48-HOUR FORECAST & ADVISORY:")
        print("-" * 80)
        print(narrative["forecast_advisory"])
    
    # Display Recommendations
    if narrative.get("recommendations"):
        print("\n💡 POLICY & HEALTH RECOMMENDATIONS:")
        print("-" * 80)
        for i, rec in enumerate(narrative["recommendations"], 1):
            print(f"   {i}. {rec}")
    
    print("\n" + "=" * 80)
    print("✅ GIS-BASED NARRATIVE GENERATION TEST COMPLETED")
    print("=" * 80)
    
    # Show what's included
    sections_included = [k for k in narrative.keys() if narrative.get(k)]
    print(f"\n📦 Sections Generated: {', '.join(sections_included)}")
    
    return narrative


if __name__ == "__main__":
    test_gis_narrative()
