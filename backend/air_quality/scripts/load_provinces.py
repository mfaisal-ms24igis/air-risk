#!/usr/bin/env python
"""
Script to load Pakistan province boundaries from the provided GeoPackage file.
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

import pandas as pd
from air_quality.models import Province
from django.db import connection


def create_province_table_if_not_exists():
    """Create the province table if it doesn't exist."""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'air_quality_province'
            );
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            print("Creating air_quality_province table...")
            cursor.execute("""
                CREATE TABLE air_quality_province (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    geometry GEOMETRY(MULTIPOLYGON, 4326),
                    centroid GEOMETRY(POINT, 4326),
                    population BIGINT,
                    area_km2 DOUBLE PRECISION,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            # Create spatial index
            cursor.execute("""
                CREATE INDEX air_quality_province_geometry_id
                ON air_quality_province USING GIST (geometry);
            """)
            print("✓ Created province table and indexes")


def load_pakistan_provinces():
    """
    Load Pakistan province boundaries from the provided GeoPackage file.
    """
    print("Loading Pakistan province boundaries from provided GeoPackage file...")

    # Create table if it doesn't exist
    create_province_table_if_not_exists()

    # The user has provided PAK_PROVINCE.gpkg with actual PBS boundaries
    source_file = Path(__file__).parent.parent.parent / "data" / "districts" / "PAK_PROVINCE.gpkg"

    if not source_file.exists():
        print(f"✗ Province boundaries file not found: {source_file}")
        print("Please ensure PAK_PROVINCE.gpkg is in the data/districts/ directory")
        return None

    print(f"✓ Found province boundaries file: {source_file}")

    try:
        import geopandas as gpd

        # Read the GeoPackage
        gdf = gpd.read_file(source_file)

        print(f"✓ Loaded {len(gdf)} provinces from GeoPackage")
        print("Columns:", list(gdf.columns))

        # Ensure the correct CRS (EPSG:4326 for WGS84)
        if gdf.crs is None:
            print("⚠ No CRS found, assuming EPSG:4326 (WGS84)")
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs != "EPSG:4326":
            print(f"⚠ Converting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")

        # Show sample data
        print("\nSample province data:")
        print(gdf.head())

        # Load provinces into database
        loaded = 0
        skipped = 0
        errors = 0

        for _, row in gdf.iterrows():
            try:
                # Get province name - try different column names
                province_name = None
                for col in ['PROVINCE', 'NAME', 'province', 'name', 'ADM1_EN']:
                    if col in gdf.columns and pd.notna(row[col]):
                        province_name = str(row[col]).strip()
                        break

                if not province_name:
                    print(f"⚠ Skipping row {row.name}: no province name found")
                    skipped += 1
                    continue

                # Convert geometry to WKT
                geom = row.geometry
                if geom is None:
                    print(f"⚠ Skipping {province_name}: no geometry")
                    skipped += 1
                    continue

                from shapely import wkt
                geom_wkt = geom.wkt

                # Create GEOS geometry
                from django.contrib.gis.geos import GEOSGeometry
                geos_geom = GEOSGeometry(geom_wkt, srid=4326)

                # Ensure MultiPolygon
                from django.contrib.gis.geos import MultiPolygon
                if geos_geom.geom_type == 'Polygon':
                    geos_geom = MultiPolygon([geos_geom])

                # Insert or update province using raw SQL
                with connection.cursor() as cursor:
                    # Check if province exists
                    cursor.execute(
                        "SELECT id FROM air_quality_province WHERE name = %s",
                        [province_name]
                    )
                    existing = cursor.fetchone()

                    if existing:
                        # Update
                        cursor.execute("""
                            UPDATE air_quality_province
                            SET geometry = ST_GeomFromText(%s, 4326),
                                updated_at = NOW()
                            WHERE name = %s
                        """, [geos_geom.wkt, province_name])
                        print(f"✓ Updated province: {province_name}")
                        loaded += 1
                    else:
                        # Insert
                        cursor.execute("""
                            INSERT INTO air_quality_province (name, geometry, created_at, updated_at)
                            VALUES (%s, ST_GeomFromText(%s, 4326), NOW(), NOW())
                        """, [province_name, geos_geom.wkt])
                        print(f"✓ Created province: {province_name}")
                        loaded += 1

            except Exception as e:
                print(f"✗ Error processing province {row.name}: {e}")
                errors += 1
                continue

        print(f"\n✓ Completed: {loaded} loaded, {skipped} skipped, {errors} errors")
        return loaded

    except ImportError:
        print("✗ geopandas not available. Install with: pip install geopandas")
        return None
    except Exception as e:
        print(f"✗ Error processing GeoPackage: {e}")
        return None


if __name__ == "__main__":
    print("Loading Pakistan province boundaries from GeoPackage...")

    try:
        result = load_pakistan_provinces()
        if result:
            print(f"\n✓ Successfully loaded {result} provinces")
        else:
            print("\n✗ Failed to load provinces")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)