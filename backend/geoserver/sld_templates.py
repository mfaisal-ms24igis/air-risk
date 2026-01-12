"""
GeoServer SLD (Styled Layer Descriptor) templates for air quality layers.
"""

# AQI color ramp (standard EPA colors)
AQI_COLORS = {
    "good": "#00e400",  # 0-50
    "moderate": "#ffff00",  # 51-100
    "usg": "#ff7e00",  # 101-150 (Unhealthy for Sensitive Groups)
    "unhealthy": "#ff0000",  # 151-200
    "very_unhealthy": "#8f3f97",  # 201-300
    "hazardous": "#7e0023",  # 301+
}


def get_aqi_sld(layer_name: str, pollutant: str) -> str:
    """
    Generate SLD for AQI raster layer.

    Args:
        layer_name: Name of the GeoServer layer
        pollutant: Pollutant code (NO2, SO2, etc.)

    Returns:
        SLD XML string
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>{layer_name}</Name>
        <UserStyle>
            <Name>{pollutant}_aqi_style</Name>
            <Title>{pollutant} Air Quality Index</Title>
            <Abstract>Color ramp for {pollutant} AQI values using EPA standard colors</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <Name>AQI Color Ramp</Name>
                    <RasterSymbolizer>
                        <ColorMap type="ramp">
                            <ColorMapEntry color="{AQI_COLORS["good"]}" quantity="0" label="Good (0)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["good"]}" quantity="50" label="Good (50)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["moderate"]}" quantity="51" label="Moderate (51)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["moderate"]}" quantity="100" label="Moderate (100)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["usg"]}" quantity="101" label="USG (101)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["usg"]}" quantity="150" label="USG (150)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["unhealthy"]}" quantity="151" label="Unhealthy (151)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["unhealthy"]}" quantity="200" label="Unhealthy (200)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["very_unhealthy"]}" quantity="201" label="Very Unhealthy (201)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["very_unhealthy"]}" quantity="300" label="Very Unhealthy (300)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["hazardous"]}" quantity="301" label="Hazardous (301+)" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["hazardous"]}" quantity="500" label="Hazardous (500)" opacity="0.8"/>
                        </ColorMap>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''


def get_concentration_sld(
    layer_name: str, pollutant: str, unit: str, thresholds: dict
) -> str:
    """
    Generate SLD for pollutant concentration raster layer.

    Args:
        layer_name: Name of the GeoServer layer
        pollutant: Pollutant code
        unit: Measurement unit
        thresholds: Dict with 'good', 'moderate', 'unhealthy', 'hazardous' values

    Returns:
        SLD XML string
    """
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>{layer_name}</Name>
        <UserStyle>
            <Name>{pollutant}_concentration_style</Name>
            <Title>{pollutant} Concentration ({unit})</Title>
            <Abstract>Color ramp for {pollutant} concentration values</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <Name>Concentration Color Ramp</Name>
                    <RasterSymbolizer>
                        <ColorMap type="ramp">
                            <ColorMapEntry color="{AQI_COLORS["good"]}" quantity="0" label="0 {unit}" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["good"]}" quantity="{thresholds["good"]}" label="{thresholds["good"]} {unit}" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["moderate"]}" quantity="{thresholds["moderate"]}" label="{thresholds["moderate"]} {unit}" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["unhealthy"]}" quantity="{thresholds["unhealthy"]}" label="{thresholds["unhealthy"]} {unit}" opacity="0.8"/>
                            <ColorMapEntry color="{AQI_COLORS["hazardous"]}" quantity="{thresholds["hazardous"]}" label="{thresholds["hazardous"]}+ {unit}" opacity="0.8"/>
                        </ColorMap>
                    </RasterSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>'''


# Pollutant-specific thresholds (based on WHO guidelines)
POLLUTANT_THRESHOLDS = {
    "NO2": {
        "unit": "µg/m³",
        "thresholds": {
            "good": 40,
            "moderate": 100,
            "unhealthy": 200,
            "hazardous": 400,
        },
    },
    "SO2": {
        "unit": "µg/m³",
        "thresholds": {
            "good": 40,
            "moderate": 125,
            "unhealthy": 350,
            "hazardous": 500,
        },
    },
    "CO": {
        "unit": "mg/m³",
        "thresholds": {
            "good": 4,
            "moderate": 10,
            "unhealthy": 30,
            "hazardous": 50,
        },
    },
    "O3": {
        "unit": "µg/m³",
        "thresholds": {
            "good": 60,
            "moderate": 100,
            "unhealthy": 180,
            "hazardous": 240,
        },
    },
    "PM25": {
        "unit": "µg/m³",
        "thresholds": {
            "good": 12,
            "moderate": 35,
            "unhealthy": 55,
            "hazardous": 150,
        },
    },
}


def get_district_style() -> str:
    """
    Generate SLD for district boundary vector layer.

    Returns:
        SLD XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>pakistan_districts</Name>
        <UserStyle>
            <Name>district_boundary_style</Name>
            <Title>District Boundaries</Title>
            <Abstract>Style for Pakistan district boundaries</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <Name>District Boundary</Name>
                    <PolygonSymbolizer>
                        <Fill>
                            <CssParameter name="fill">#ffffff</CssParameter>
                            <CssParameter name="fill-opacity">0.1</CssParameter>
                        </Fill>
                        <Stroke>
                            <CssParameter name="stroke">#333333</CssParameter>
                            <CssParameter name="stroke-width">1</CssParameter>
                        </Stroke>
                    </PolygonSymbolizer>
                    <TextSymbolizer>
                        <Label>
                            <ogc:PropertyName>name</ogc:PropertyName>
                        </Label>
                        <Font>
                            <CssParameter name="font-family">Arial</CssParameter>
                            <CssParameter name="font-size">11</CssParameter>
                            <CssParameter name="font-weight">bold</CssParameter>
                        </Font>
                        <LabelPlacement>
                            <PointPlacement>
                                <AnchorPoint>
                                    <AnchorPointX>0.5</AnchorPointX>
                                    <AnchorPointY>0.5</AnchorPointY>
                                </AnchorPoint>
                            </PointPlacement>
                        </LabelPlacement>
                        <Halo>
                            <Radius>2</Radius>
                            <Fill>
                                <CssParameter name="fill">#ffffff</CssParameter>
                            </Fill>
                        </Halo>
                        <Fill>
                            <CssParameter name="fill">#333333</CssParameter>
                        </Fill>
                    </TextSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>"""


def get_station_style() -> str:
    """
    Generate SLD for ground station point layer.

    Returns:
        SLD XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>ground_stations</Name>
        <UserStyle>
            <Name>station_style</Name>
            <Title>Ground Monitoring Stations</Title>
            <Abstract>Style for air quality monitoring stations</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <Name>Active Station</Name>
                    <ogc:Filter>
                        <ogc:PropertyIsEqualTo>
                            <ogc:PropertyName>is_active</ogc:PropertyName>
                            <ogc:Literal>true</ogc:Literal>
                        </ogc:PropertyIsEqualTo>
                    </ogc:Filter>
                    <PointSymbolizer>
                        <Graphic>
                            <Mark>
                                <WellKnownName>circle</WellKnownName>
                                <Fill>
                                    <CssParameter name="fill">#3498db</CssParameter>
                                </Fill>
                                <Stroke>
                                    <CssParameter name="stroke">#ffffff</CssParameter>
                                    <CssParameter name="stroke-width">2</CssParameter>
                                </Stroke>
                            </Mark>
                            <Size>12</Size>
                        </Graphic>
                    </PointSymbolizer>
                    <TextSymbolizer>
                        <Label>
                            <ogc:PropertyName>name</ogc:PropertyName>
                        </Label>
                        <Font>
                            <CssParameter name="font-family">Arial</CssParameter>
                            <CssParameter name="font-size">10</CssParameter>
                        </Font>
                        <LabelPlacement>
                            <PointPlacement>
                                <Displacement>
                                    <DisplacementX>10</DisplacementX>
                                    <DisplacementY>0</DisplacementY>
                                </Displacement>
                            </PointPlacement>
                        </LabelPlacement>
                        <Halo>
                            <Radius>2</Radius>
                            <Fill>
                                <CssParameter name="fill">#ffffff</CssParameter>
                            </Fill>
                        </Halo>
                        <Fill>
                            <CssParameter name="fill">#333333</CssParameter>
                        </Fill>
                    </TextSymbolizer>
                </Rule>
                <Rule>
                    <Name>Inactive Station</Name>
                    <ogc:Filter>
                        <ogc:PropertyIsEqualTo>
                            <ogc:PropertyName>is_active</ogc:PropertyName>
                            <ogc:Literal>false</ogc:Literal>
                        </ogc:PropertyIsEqualTo>
                    </ogc:Filter>
                    <PointSymbolizer>
                        <Graphic>
                            <Mark>
                                <WellKnownName>circle</WellKnownName>
                                <Fill>
                                    <CssParameter name="fill">#95a5a6</CssParameter>
                                </Fill>
                                <Stroke>
                                    <CssParameter name="stroke">#ffffff</CssParameter>
                                    <CssParameter name="stroke-width">2</CssParameter>
                                </Stroke>
                            </Mark>
                            <Size>10</Size>
                        </Graphic>
                    </PointSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>"""


def get_hotspot_style() -> str:
    """
    Generate SLD for hotspot point layer.

    Returns:
        SLD XML string
    """
    return """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
    xmlns="http://www.opengis.net/sld"
    xmlns:ogc="http://www.opengis.net/ogc"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
    <NamedLayer>
        <Name>hotspots</Name>
        <UserStyle>
            <Name>hotspot_style</Name>
            <Title>Pollution Hotspots</Title>
            <Abstract>Style for detected pollution hotspots</Abstract>
            <FeatureTypeStyle>
                <Rule>
                    <Name>Active Hotspot</Name>
                    <ogc:Filter>
                        <ogc:PropertyIsEqualTo>
                            <ogc:PropertyName>is_active</ogc:PropertyName>
                            <ogc:Literal>true</ogc:Literal>
                        </ogc:PropertyIsEqualTo>
                    </ogc:Filter>
                    <PointSymbolizer>
                        <Graphic>
                            <Mark>
                                <WellKnownName>triangle</WellKnownName>
                                <Fill>
                                    <CssParameter name="fill">#e74c3c</CssParameter>
                                </Fill>
                                <Stroke>
                                    <CssParameter name="stroke">#ffffff</CssParameter>
                                    <CssParameter name="stroke-width">2</CssParameter>
                                </Stroke>
                            </Mark>
                            <Size>14</Size>
                        </Graphic>
                    </PointSymbolizer>
                </Rule>
            </FeatureTypeStyle>
        </UserStyle>
    </NamedLayer>
</StyledLayerDescriptor>"""
