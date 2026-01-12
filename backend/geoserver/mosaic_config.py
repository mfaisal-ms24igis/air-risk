"""
ImageMosaic configuration templates for time-enabled raster stores.
"""

import os
from typing import Optional


def get_indexer_properties(time_attribute: str = "ingestion") -> str:
    """
    Generate indexer.properties for ImageMosaic with TIME dimension.

    Args:
        time_attribute: Name of the time attribute

    Returns:
        Properties file content
    """
    return f"""# ImageMosaic Indexer Configuration
# Enables TIME dimension for WMS requests

# Time attribute settings
TimeAttribute={time_attribute}
Schema=*the_geom:Polygon,location:String,{time_attribute}:java.util.Date

# Property collectors for extracting time from filename
PropertyCollectors=TimestampFileNameExtractorSPI[{time_attribute}](yyyyMMdd)

# Coverage name pattern
Name=.*

# Absolute paths in index
AbsolutePath=true

# Recursive directory scan
Recursive=true

# Wildcards for file matching
Wildcard=*.tif,*.tiff

# Caching
Caching=true
"""


def get_timeregex_properties() -> str:
    """
    Generate timeregex.properties for extracting date from filenames.

    Expected filename format: {pollutant}_{YYYYMMDD}.tif
    Example: NO2_20240115.tif

    Returns:
        Properties file content
    """
    return """# Time regex for extracting date from filename
# Matches 8-digit date in format YYYYMMDD after underscore

regex=.*_([0-9]{8}).*
"""


def get_datastore_properties(
    host: str = "db",
    port: int = 5432,
    database: str = "air_quality",
    schema: str = "public",
    user: str = "postgres",
    password: str = "postgres",
) -> str:
    """
    Generate datastore.properties for PostGIS-backed ImageMosaic index.

    Args:
        host: Database host
        port: Database port
        database: Database name
        schema: Database schema
        user: Database user
        password: Database password

    Returns:
        Properties file content
    """
    return f"""# PostGIS datastore configuration for ImageMosaic index
# Stores granule footprints and time information in PostgreSQL

SPI=org.geotools.data.postgis.PostgisNGDataStoreFactory
host={host}
port={port}
database={database}
schema={schema}
user={user}
passwd={password}

# Connection pool settings
max\ connections=10
min\ connections=1
Connection\ timeout=20
validate\ connections=true
Estimated\ extends=false
Loose\ bbox=true
Expose\ primary\ keys=true

# Enable prepared statements for better performance
preparedStatements=true
"""


def get_coverage_properties(
    name: str,
    srs: str = "EPSG:4326",
    suggested_tile_size: str = "512,512",
) -> str:
    """
    Generate coverage-specific properties.

    Args:
        name: Coverage name
        srs: Coordinate reference system
        suggested_tile_size: Tile size for requests

    Returns:
        Properties file content
    """
    return f"""# Coverage configuration for {name}

# Coordinate reference system
Crs=EPSG:4326
DefaultCrs={srs}

# Tile settings
SuggestedTileSize={suggested_tile_size}

# Background value (transparent)
BackgroundValues=-9999

# Input/Output transparency
InputTransparentColor=
OutputTransparentColor=

# Allow multiple dimensions
AllowMultithreading=true

# Maximum allowed tiles
MaxAllowedTiles=1000000
"""


def get_elevation_properties() -> str:
    """
    Generate elevation.properties if elevation dimension is needed.

    Returns:
        Properties file content
    """
    return """# Elevation domain configuration
# Only needed if multiple vertical levels exist

regex=.*_([0-9]+)m.*
"""


def generate_mosaic_config(
    store_name: str,
    pollutant: str,
    base_path: str,
    db_config: Optional[dict] = None,
) -> dict:
    """
    Generate all configuration files for an ImageMosaic store.

    Args:
        store_name: GeoServer store name
        pollutant: Pollutant code (NO2, SO2, etc.)
        base_path: Base path for raster files
        db_config: Optional database configuration

    Returns:
        Dictionary of filename -> content
    """
    if db_config is None:
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "db"),
            "port": int(os.getenv("POSTGRES_PORT", 5432)),
            "database": os.getenv("POSTGRES_DB", "air_quality"),
            "schema": "public",
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        }

    configs = {
        "indexer.properties": get_indexer_properties(),
        "timeregex.properties": get_timeregex_properties(),
        "datastore.properties": get_datastore_properties(**db_config),
        f"{pollutant.lower()}.properties": get_coverage_properties(pollutant),
    }

    return configs


# WMS Layer configuration template
WMS_LAYER_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<layer>
    <name>{layer_name}</name>
    <type>RASTER</type>
    <defaultStyle>
        <name>{style_name}</name>
    </defaultStyle>
    <resource class="coverage">
        <name>{layer_name}</name>
        <nativeCRS>EPSG:4326</nativeCRS>
        <srs>EPSG:4326</srs>
        <nativeBoundingBox>
            <minx>60.0</minx>
            <maxx>78.0</maxx>
            <miny>23.0</miny>
            <maxy>37.5</maxy>
            <crs>EPSG:4326</crs>
        </nativeBoundingBox>
        <metadata>
            <entry key="time">
                <dimensionInfo>
                    <enabled>true</enabled>
                    <presentation>CONTINUOUS_INTERVAL</presentation>
                    <units>ISO8601</units>
                    <defaultValue>
                        <strategy>MAXIMUM</strategy>
                    </defaultValue>
                </dimensionInfo>
            </entry>
        </metadata>
    </resource>
</layer>"""


def get_wms_layer_config(layer_name: str, style_name: str) -> str:
    """
    Generate WMS layer configuration with TIME dimension.

    Args:
        layer_name: GeoServer layer name
        style_name: Default style name

    Returns:
        XML configuration string
    """
    return WMS_LAYER_CONFIG.format(
        layer_name=layer_name,
        style_name=style_name,
    )
