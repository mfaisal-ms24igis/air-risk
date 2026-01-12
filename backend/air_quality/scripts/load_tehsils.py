#!/usr/bin/env python
"""
Script to load Pakistan tehsil boundaries from the provided GeoPackage file.
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
from django.db import connection


def create_tehsil_table_if_not_exists():
    """Create the tehsil table if it doesn't exist."""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'air_quality_tehsil'
            );
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            print("Creating air_quality_tehsil table...")
            cursor.execute("""
                CREATE TABLE air_quality_tehsil (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    district_id INTEGER REFERENCES air_quality_district(id),
                    province VARCHAR(100) NOT NULL,
                    geometry GEOMETRY(MULTIPOLYGON, 4326),
                    centroid GEOMETRY(POINT, 4326),
                    population BIGINT,
                    area_km2 DOUBLE PRECISION,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            # Create indexes
            cursor.execute("""
                CREATE INDEX air_quality_tehsil_geometry_id
                ON air_quality_tehsil USING GIST (geometry);
            """)
            cursor.execute("""
                CREATE INDEX air_quality_tehsil_district_id_idx
                ON air_quality_tehsil (district_id);
            """)
            cursor.execute("""
                CREATE INDEX air_quality_tehsil_province_idx
                ON air_quality_tehsil (province);
            """)
            cursor.execute("""
                CREATE UNIQUE INDEX air_quality_tehsil_name_district_idx
                ON air_quality_tehsil (name, district_id);
            """)
            print("✓ Created tehsil table and indexes")


def load_pakistan_tehsils():
    """
    Load Pakistan tehsil boundaries from the provided GeoPackage file.
    """
    print("Loading Pakistan tehsil boundaries from provided GeoPackage file...")

    # Create table if it doesn't exist
    create_tehsil_table_if_not_exists()

    # The user has provided PAK_TEHSIL.gpkg with actual PBS boundaries
    source_file = Path(__file__).parent.parent.parent / "data" / "districts" / "PAK_TEHSIL.gpkg"

    if not source_file.exists():
        print(f"✗ Tehsil boundaries file not found: {source_file}")
        print("Please ensure PAK_TEHSIL.gpkg is in the data/districts/ directory")
        return None

    print(f"✓ Found tehsil boundaries file: {source_file}")

    try:
        import geopandas as gpd

        # Read the GeoPackage
        gdf = gpd.read_file(source_file)

        print(f"✓ Loaded {len(gdf)} tehsils from GeoPackage")
        print("Columns:", list(gdf.columns))

        # Ensure the correct CRS (EPSG:4326 for WGS84)
        if gdf.crs is None:
            print("⚠ No CRS found, assuming EPSG:4326 (WGS84)")
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs != "EPSG:4326":
            print(f"⚠ Converting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")

        # Show sample data
        print("\nSample tehsil data:")
        print(gdf[['PROVINCE', 'DISTRICT', 'TEHSIL']].head())

        # Get district mapping for foreign keys
        district_map = {}
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, name, province FROM air_quality_district")
            for row in cursor.fetchall():
                district_id, district_name, province = row
                key = f"{district_name}|{province}"
                district_map[key] = district_id

        print(f"✓ Found {len(district_map)} districts in database")

        # Load tehsils into database
        loaded = 0
        skipped = 0
        errors = 0

        for _, row in gdf.iterrows():
            try:
                # Get tehsil info
                tehsil_name = str(row.get('TEHSIL', '')).strip()
                district_name = str(row.get('DISTRICT', '')).strip()
                province_name = str(row.get('PROVINCE', '')).strip()

                if not tehsil_name or not district_name or not province_name:
                    print(f"⚠ Skipping row {row.name}: missing name/district/province")
                    skipped += 1
                    continue

                # Find district ID
                district_key = f"{district_name}|{province_name}"
                district_id = district_map.get(district_key)

                if not district_id:
                    print(f"⚠ Skipping {tehsil_name}: district '{district_name}' in '{province_name}' not found")
                    skipped += 1
                    continue

                # Convert geometry
                geom = row.geometry
                if geom is None:
                    print(f"⚠ Skipping {tehsil_name}: no geometry")
                    skipped += 1
                    continue

                from shapely import wkt
                geom_wkt = geom.wkt

                # Create GEOS geometry
                from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
                geos_geom = GEOSGeometry(geom_wkt, srid=4326)

                # Ensure MultiPolygon
                if geos_geom.geom_type == 'Polygon':
                    geos_geom = MultiPolygon([geos_geom])

                # Insert or update tehsil using raw SQL
                with connection.cursor() as cursor:
                    # Check if tehsil exists
                    cursor.execute(
                        "SELECT id FROM air_quality_tehsil WHERE name = %s AND district_id = %s",
                        [tehsil_name, district_id]
                    )
                    existing = cursor.fetchone()

                    if existing:
                        # Update
                        cursor.execute("""
                            UPDATE air_quality_tehsil
                            SET geometry = ST_GeomFromText(%s, 4326),
                                province = %s,
                                updated_at = NOW()
                            WHERE name = %s AND district_id = %s
                        """, [geos_geom.wkt, province_name, tehsil_name, district_id])
                        print(f"✓ Updated tehsil: {tehsil_name} ({district_name})")
                        loaded += 1
                    else:
                        # Insert
                        cursor.execute("""
                            INSERT INTO air_quality_tehsil (name, district_id, province, geometry, created_at, updated_at)
                            VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326), NOW(), NOW())
                        """, [tehsil_name, district_id, province_name, geos_geom.wkt])
                        print(f"✓ Created tehsil: {tehsil_name} ({district_name})")
                        loaded += 1

            except Exception as e:
                print(f"✗ Error processing tehsil {row.name}: {e}")
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
    print("Loading Pakistan tehsil boundaries from GeoPackage...")

    try:
        result = load_pakistan_tehsils()
        if result is not None:
            print(f"\n✓ Successfully loaded {result} tehsils")
        else:
            print("\n✗ Failed to load tehsils")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)