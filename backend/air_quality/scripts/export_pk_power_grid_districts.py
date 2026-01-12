#!/usr/bin/env python
"""
Script to export district data from PK_POWER_GRID database and import into Django.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "air_risk.settings.dev")

import django
django.setup()

from django.core.management import execute_from_command_line
import pandas as pd
from sqlalchemy import create_engine


def export_districts_from_pk_power_grid():
    """
    Export district data from PK_POWER_GRID database.
    Supports PostgreSQL, MySQL, SQLite, and SQL Server.
    """
    print("Exporting districts from PK_POWER_GRID database...")

    # Database connection parameters - you'll need to provide these
    db_configs = {
        'postgresql': {
            'host': input("PostgreSQL Host (default: localhost): ") or 'localhost',
            'port': input("PostgreSQL Port (default: 5432): ") or '5432',
            'database': input("Database name (default: PK_POWER_GRID): ") or 'PK_POWER_GRID',
            'user': input("Username: "),
            'password': input("Password: "),
            'connection_string': None
        },
        'mysql': {
            'host': input("MySQL Host (default: localhost): ") or 'localhost',
            'port': input("MySQL Port (default: 3306): ") or '3306',
            'database': input("Database name (default: PK_POWER_GRID): ") or 'PK_POWER_GRID',
            'user': input("Username: "),
            'password': input("Password: "),
            'connection_string': None
        },
        'sqlite': {
            'database': input("SQLite file path: "),
            'connection_string': None
        },
        'mssql': {
            'server': input("SQL Server (default: localhost): ") or 'localhost',
            'database': input("Database name (default: PK_POWER_GRID): ") or 'PK_POWER_GRID',
            'user': input("Username: "),
            'password': input("Password: "),
            'connection_string': None
        }
    }

    # Choose database type
    print("\nAvailable database types:")
    for i, db_type in enumerate(db_configs.keys(), 1):
        print(f"{i}. {db_type.upper()}")

    while True:
        try:
            choice = int(input("\nSelect database type (1-4): ")) - 1
            if 0 <= choice < len(db_configs):
                db_type = list(db_configs.keys())[choice]
                break
            else:
                print("Invalid choice. Please select 1-4.")
        except ValueError:
            print("Please enter a number.")

    config = db_configs[db_type]

    # Build connection string
    if db_type == 'postgresql':
        config['connection_string'] = (
            f"postgresql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    elif db_type == 'mysql':
        config['connection_string'] = (
            f"mysql+pymysql://{config['user']}:{config['password']}@"
            f"{config['host']}:{config['port']}/{config['database']}"
        )
    elif db_type == 'sqlite':
        config['connection_string'] = f"sqlite:///{config['database']}"
    elif db_type == 'mssql':
        config['connection_string'] = (
            f"mssql+pyodbc://{config['user']}:{config['password']}@"
            f"{config['server']}/{config['database']}?driver=ODBC+Driver+17+for+SQL+Server"
        )

    try:
        # Connect to database
        print(f"\nConnecting to {db_type.upper()} database...")
        engine = pd.io.sql.create_engine(config['connection_string'])

        # Try different possible table names for districts
        possible_tables = [
            'districts', 'pakistan_districts', 'admin_districts',
            'pk_districts', 'district', 'pak_districts'
        ]

        districts_df = None
        table_found = None

        # Get available tables first
        if db_type == 'sqlite':
            tables_query = "SELECT name FROM sqlite_master WHERE type='table';"
        else:
            tables_query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """

        try:
            tables_df = pd.read_sql(tables_query, engine)
            available_tables = tables_df.iloc[:, 0].tolist()
            print(f"Available tables: {available_tables}")

            # Look for district-related tables
            district_tables = [t for t in available_tables if 'district' in t.lower()]
            if district_tables:
                print(f"Found district tables: {district_tables}")
                table_found = district_tables[0]  # Use first match
            else:
                print("No district tables found. Please specify table name manually.")
                table_found = input("Enter the exact table name containing districts: ")

        except Exception as e:
            print(f"Could not query table list: {e}")
            table_found = input("Enter the exact table name containing districts: ")

        if not table_found:
            print("No table specified. Exiting.")
            return None

        # Query the districts table
        print(f"\nReading data from table: {table_found}")
        query = f"SELECT * FROM {table_found} LIMIT 1000"  # Limit for safety
        districts_df = pd.read_sql(query, engine)

        print(f"Found {len(districts_df)} records")
        print("Columns:", list(districts_df.columns))

        # Show sample data
        print("\nSample data:")
        print(districts_df.head())

        # Ask user to map columns
        print("\nPlease map the columns to Django District model fields:")
        print("Required fields: name, province, geometry")
        print("Optional fields: code, population, area_km2")

        column_mapping = {}

        # Try to auto-map common column names
        possible_name_cols = [c for c in districts_df.columns if 'name' in c.lower() or c.lower() in ['district', 'district_name']]
        possible_province_cols = [c for c in districts_df.columns if 'province' in c.lower() or 'prov' in c.lower()]
        possible_geom_cols = [c for c in districts_df.columns if 'geom' in c.lower() or 'shape' in c.lower() or 'wkt' in c.lower()]
        possible_code_cols = [c for c in districts_df.columns if 'code' in c.lower() or 'id' in c.lower()]

        # Auto-map if possible
        if possible_name_cols:
            column_mapping['name'] = possible_name_cols[0]
            print(f"Auto-mapped 'name' to column: {possible_name_cols[0]}")
        else:
            column_mapping['name'] = input("Column for district name: ")

        if possible_province_cols:
            column_mapping['province'] = possible_province_cols[0]
            print(f"Auto-mapped 'province' to column: {possible_province_cols[0]}")
        else:
            column_mapping['province'] = input("Column for province: ")

        if possible_geom_cols:
            column_mapping['geometry'] = possible_geom_cols[0]
            print(f"Auto-mapped 'geometry' to column: {possible_geom_cols[0]}")
        else:
            column_mapping['geometry'] = input("Column for geometry (WKT or GeoJSON): ")

        # Optional mappings
        if possible_code_cols:
            use_code = input(f"Use column '{possible_code_cols[0]}' for district code? (y/n): ").lower() == 'y'
            if use_code:
                column_mapping['code'] = possible_code_cols[0]

        # Create GeoJSON
        features = []
        for _, row in districts_df.iterrows():
            try:
                # Handle geometry conversion
                geom_data = row[column_mapping['geometry']]

                # Convert WKT to GeoJSON if needed
                if isinstance(geom_data, str) and geom_data.startswith('POLYGON') or geom_data.startswith('MULTIPOLYGON'):
                    # This is WKT - we'd need shapely to convert, but for now assume GeoJSON
                    print("Warning: WKT geometry detected. Please ensure geometry is in GeoJSON format.")
                    continue
                elif isinstance(geom_data, dict):
                    # Already GeoJSON
                    geometry = geom_data
                else:
                    print(f"Unsupported geometry format for row {row.name}")
                    continue

                feature = {
                    "type": "Feature",
                    "properties": {
                        "NAME": str(row[column_mapping['name']]),
                        "PROVINCE": str(row[column_mapping['province']]),
                    },
                    "geometry": geometry
                }

                if 'code' in column_mapping:
                    feature["properties"]["CODE"] = str(row[column_mapping['code']])

                features.append(feature)

            except Exception as e:
                print(f"Error processing row {row.name}: {e}")
                continue

        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }

        # Save to file
        output_dir = Path(__file__).parent.parent.parent / "data" / "districts"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "pk_power_grid_districts.geojson"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Exported {len(features)} districts to: {output_file}")
        return str(output_file)

    except Exception as e:
        print(f"✗ Error exporting districts: {e}")
        return None


if __name__ == "__main__":
    print("PK_POWER_GRID District Export Tool")
    print("=" * 40)

    exported_file = export_districts_from_pk_power_grid()

    if exported_file:
        print(f"\n✓ Successfully exported districts to: {exported_file}")

        # Ask if user wants to import into Django
        import_now = input("\nImport districts into Django database now? (y/n): ").lower() == 'y'

        if import_now:
            print("\nLoading districts into Django database...")
            execute_from_command_line([
                "manage.py",
                "load_districts",
                exported_file,
                "--name-field", "NAME",
                "--province-field", "PROVINCE",
                "--clear"
            ])
    else:
        print("\n✗ Export failed.")