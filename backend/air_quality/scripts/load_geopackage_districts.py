#!/usr/bin/env python
"""
Script to load Pakistan district boundaries from the provided GeoPackage file.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "air_risk.settings.dev")

import django
django.setup()

from django.core.management import execute_from_command_line


def load_pakistan_districts():
    """
    Load Pakistan district boundaries from the provided GeoPackage file.
    """
    print("Loading Pakistan district boundaries from provided GeoPackage file...")

    # The user has provided PAK_DISTRICT.gpkg with actual PBS boundaries
    source_file = Path(__file__).parent.parent.parent / "data" / "districts" / "PAK_DISTRICT.gpkg"

    if not source_file.exists():
        print(f"✗ District boundaries file not found: {source_file}")
        print("Please ensure PAK_DISTRICT.gpkg is in the data/districts/ directory")
        return None

    print(f"✓ Found district boundaries file: {source_file}")

    # Convert to GeoJSON for processing
    output_dir = Path(__file__).parent.parent.parent / "data" / "districts"
    output_file = output_dir / "pakistan_districts.geojson"

    try:
        import geopandas as gpd

        # Read the GeoPackage
        gdf = gpd.read_file(source_file)

        print(f"✓ Loaded {len(gdf)} districts from GeoPackage")
        print("Columns:", list(gdf.columns))
        print("CRS:", gdf.crs)

        # Ensure the correct CRS (EPSG:4326 for WGS84)
        if gdf.crs is None:
            print("⚠ No CRS found, assuming EPSG:4326 (WGS84)")
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs != "EPSG:4326":
            print(f"⚠ Converting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")

        # Show sample data
        print("\nSample district data:")
        print(gdf.head())

        # Convert to GeoJSON
        gdf.to_file(output_file, driver='GeoJSON')

        print(f"✓ Converted to GeoJSON: {output_file}")
        return str(output_file)

    except ImportError:
        print("✗ geopandas not available. Install with: pip install geopandas")
        return None
    except Exception as e:
        print(f"✗ Error processing GeoPackage: {e}")
        return None


if __name__ == "__main__":
    print("Loading Pakistan district boundaries from GeoPackage...")

    try:
        geojson_file = load_pakistan_districts()
        if geojson_file:
            print(f"\n✓ District boundaries converted to: {geojson_file}")

            # Now load them into the database
            print("\nLoading districts into database...")
            execute_from_command_line([
                "manage.py",
                "load_districts",
                geojson_file,
                "--clear"
            ])
        else:
            print("\n✗ Failed to load district boundaries")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)