"""
Report generation utilities using ReportLab.
Replaces WeasyPrint to avoid GTK dependencies on Windows.
"""

import logging
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.template import Template, Context
from django.template.loader import render_to_string
from django.contrib.gis.geos import Point

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
import io
import requests
import numpy as np

from .models import Report, ReportTemplate
from air_quality.models import District
from exposure.models import (
    DistrictExposure,
    ProvinceExposure,
    NationalExposure,
    Hotspot,
)
from exposure.services.trend_analyzer import TrendAnalyzer
from .services.ai_insights import generate_professional_narrative

logger = logging.getLogger(__name__)

# Report storage path
REPORTS_PATH = Path(settings.BASE_DIR) / "media" / "reports"


class NumberedCanvas(canvas.Canvas):
    """Custom canvas for adding page numbers and headers."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Add page numbers and headers to all pages."""
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        """Draw header and footer on each page."""
        # Footer with page number
        self.setFont("Helvetica", 9)
        self.setFillColorRGB(0.4, 0.4, 0.4)
        page_num_text = f"Page {self._pageNumber} of {page_count}"
        self.drawCentredString(A4[0] / 2.0, 0.75 * cm, page_num_text)

        # Header
        self.drawCentredString(A4[0] / 2.0, A4[1] - 0.75 * cm, "Air Quality Report")
        self.line(2 * cm, A4[1] - 1 * cm, A4[0] - 2 * cm, A4[1] - 1 * cm)


def get_aqi_color(aqi_value: float) -> colors.Color:
    """Get ReportLab color for AQI value."""
    if aqi_value <= 50:
        return colors.HexColor("#00e400")  # Good
    elif aqi_value <= 100:
        return colors.HexColor("#ffff00")  # Moderate
    elif aqi_value <= 150:
        return colors.HexColor("#ff7e00")  # USG
    elif aqi_value <= 200:
        return colors.HexColor("#ff0000")  # Unhealthy
    elif aqi_value <= 300:
        return colors.HexColor("#8f3f97")  # Very Unhealthy
    else:
        return colors.HexColor("#7e0023")  # Hazardous


def get_aqi_category(aqi_value: float) -> str:
    """Get AQI category name."""
    if aqi_value <= 50:
        return "Good"
    elif aqi_value <= 100:
        return "Moderate"
    elif aqi_value <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi_value <= 200:
        return "Unhealthy"
    elif aqi_value <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def get_custom_styles():
    """Get custom paragraph styles for reports."""
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1a5276"),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomHeading2",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#2874a6"),
            spaceBefore=20,
            spaceAfter=12,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomHeading3",
            parent=styles["Heading3"],
            fontSize=13,
            textColor=colors.HexColor("#3498db"),
            spaceBefore=15,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomHeading4",
            parent=styles["Heading4"],
            fontSize=11,
            textColor=colors.HexColor("#5dade2"),
            spaceBefore=10,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomBody",
            parent=styles["BodyText"],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
        )
    )

    styles.add(
        ParagraphStyle(
            name="CustomCaption",
            parent=styles["BodyText"],
            fontSize=9,
            textColor=colors.grey,
            leading=12,
            alignment=TA_JUSTIFY,
        )
    )

    return styles


def generate_ai_insights(trend_data: dict) -> dict:
    """
    Generate comprehensive AI-powered health insights from trend data.
    
    Provides structured tabular data and detailed analysis for better AI reasoning.
    
    Args:
        trend_data: Trend analysis data from TrendAnalyzer
        
    Returns:
        AI insights dictionary with structured data tables
    """
    insights = {
        "summary": "",
        "recommendations": [],
        "risk_level": "low",
        "sensitive_groups": [],
        "model": "AI Health Assistant v1.0",
        "data_tables": {},
        "analysis": {},
        "trends": {},
        "comparisons": {}
    }
    
    # Extract all data sources
    location_info = trend_data.get("location", {})
    ground_trends = trend_data.get("ground_trends", {})
    gee_data = trend_data.get("gee_data", {})
    stations = trend_data.get("stations", {})
    temporal_patterns = trend_data.get("temporal_patterns", {})
    
    # === DATA TABLES FOR AI ANALYSIS ===
    
    # 1. Location Context Table
    insights["data_tables"]["location_context"] = {
        "title": "Location Analysis Context",
        "headers": ["Parameter", "Value", "Description"],
        "rows": [
            ["Latitude", f"{location_info.get('lat', 'N/A'):.4f}", "Location latitude"],
            ["Longitude", f"{location_info.get('lng', 'N/A'):.4f}", "Location longitude"],
            ["Analysis Radius", f"{location_info.get('radius_km', 'N/A')} km", "Search radius for data"],
            ["District", location_info.get('district', {}).get('name', 'N/A'), "Administrative district"],
            ["Province", location_info.get('district', {}).get('province', 'N/A'), "Administrative province"],
            ["District Population", f"{location_info.get('district', {}).get('population', 'N/A'):,}", "Total population"],
            ["District Area", f"{location_info.get('district', {}).get('area_km2', 'N/A')} km²", "Area coverage"],
        ]
    }
    
    # 2. Ground Station Measurements Table
    ground_rows = []
    for pollutant, data in ground_trends.items():
        mean_val = data.get('mean', 'N/A')
        max_val = data.get('max', 'N/A')
        p95_val = data.get('p95', 'N/A')
        
        # Format values
        mean_str = f"{mean_val:.1f}" if isinstance(mean_val, (int, float)) else str(mean_val)
        max_str = f"{max_val:.1f}" if isinstance(max_val, (int, float)) else str(max_val)
        p95_str = f"{p95_val:.1f}" if isinstance(p95_val, (int, float)) else str(p95_val)
        
        ground_rows.append([
            pollutant,
            f"{mean_str} µg/m³",
            f"{max_str} µg/m³", 
            f"{p95_str} µg/m³",
            "Ground station measurements"
        ])
    
    insights["data_tables"]["ground_measurements"] = {
        "title": "Ground Station Air Quality Measurements",
        "headers": ["Pollutant", "Mean", "Maximum", "95th Percentile", "Data Source"],
        "rows": ground_rows
    }
    
    # 3. Satellite Measurements Table
    satellite_rows = []
    for pollutant_key in ["no2", "so2", "co", "o3"]:
        if pollutant_key in gee_data:
            data = gee_data[pollutant_key]
            mean_val = data.get('mean', 'N/A')
            max_val = data.get('max', 'N/A')
            
            # Format satellite values (scientific notation for small values)
            mean_str = f"{mean_val:.2e}" if isinstance(mean_val, (int, float)) else str(mean_val)
            max_str = f"{max_val:.2e}" if isinstance(max_val, (int, float)) else str(max_val)
            
            pollutant_name = pollutant_key.upper()
            unit = data.get('unit', 'mol/m²')
            
            satellite_rows.append([
                pollutant_name,
                f"{mean_str} {unit}",
                f"{max_str} {unit}",
                "Sentinel-5P Satellite (GEE)"
            ])
    
    insights["data_tables"]["satellite_measurements"] = {
        "title": "Satellite Air Quality Measurements",
        "headers": ["Pollutant", "Mean", "Maximum", "Data Source"],
        "rows": satellite_rows
    }
    
    # 4. Station Information Table
    station_rows = []
    if stations.get("count", 0) > 0:
        station_rows.append([
            "Total Stations Found",
            str(stations.get("count", 0)),
            "Number of monitoring stations within radius"
        ])
        if stations.get("nearest"):
            station_rows.extend([
                ["Nearest Station", stations["nearest"].get("name", "N/A"), "Closest monitoring station"],
                ["Distance to Nearest", f"{stations['nearest'].get('distance_km', 'N/A')} km", "Distance from location"]
            ])
    
    insights["data_tables"]["station_info"] = {
        "title": "Air Quality Monitoring Stations",
        "headers": ["Parameter", "Value", "Description"],
        "rows": station_rows
    }
    
    # 5. Health Risk Assessment Table
    risk_assessment = []
    
    # AQI Categories and Health Risks
    aqi_categories = {
        "PM25": [
            ("0-12", "Good", "Minimal health risk"),
            ("12-35", "Moderate", "Acceptable for most people"),
            ("35-55", "Unhealthy for Sensitive Groups", "Children, elderly, respiratory conditions"),
            ("55-150", "Unhealthy", "Everyone may experience health effects"),
            ("150-250", "Very Unhealthy", "Emergency conditions"),
            ("250+", "Hazardous", "Serious health effects")
        ],
        "PM10": [
            ("0-54", "Good", "Minimal health risk"),
            ("54-154", "Moderate", "Acceptable for most people"),
            ("154-254", "Unhealthy for Sensitive Groups", "Children, elderly, respiratory conditions"),
            ("254-354", "Unhealthy", "Everyone may experience health effects"),
            ("354-424", "Very Unhealthy", "Emergency conditions"),
            ("424+", "Hazardous", "Serious health effects")
        ],
        "NO2": [
            ("0-40", "Good", "Minimal health risk"),
            ("40-80", "Moderate", "Acceptable for most people"),
            ("80-180", "Unhealthy for Sensitive Groups", "Children, elderly, respiratory conditions"),
            ("180-280", "Unhealthy", "Everyone may experience health effects"),
            ("280-400", "Very Unhealthy", "Emergency conditions"),
            ("400+", "Hazardous", "Serious health effects")
        ]
    }
    
    for pollutant, categories in aqi_categories.items():
        if pollutant in ground_trends:
            mean_val = ground_trends[pollutant].get('mean', 0)
            current_category = "Unknown"
            health_risk = "Unknown"
            
            for range_str, category, risk in categories:
                if "-" in range_str:
                    min_val, max_val = range_str.split("-")
                    min_val = float(min_val)
                    max_val = float(max_val) if max_val != "+" else float('inf')
                    
                    if min_val <= mean_val < max_val:
                        current_category = category
                        health_risk = risk
                        break
                elif range_str.endswith("+"):
                    min_val = float(range_str[:-1])
                    if mean_val >= min_val:
                        current_category = category
                        health_risk = risk
                        break
            
            risk_assessment.append([
                pollutant,
                f"{mean_val:.1f} µg/m³",
                current_category,
                health_risk
            ])
    
    insights["data_tables"]["health_risk_assessment"] = {
        "title": "Health Risk Assessment by Pollutant",
        "headers": ["Pollutant", "Current Level", "AQI Category", "Health Risk"],
        "rows": risk_assessment
    }
    
    # === AI ANALYSIS SECTION ===
    
    # Comprehensive risk analysis
    high_risk_pollutants = []
    moderate_risk_pollutants = []
    
    for pollutant, data in ground_trends.items():
        mean_val = data.get('mean', 0)
        
        if pollutant == "PM25":
            if mean_val >= 55:
                high_risk_pollutants.append(f"PM2.5 ({mean_val:.1f} µg/m³)")
            elif mean_val >= 35:
                moderate_risk_pollutants.append(f"PM2.5 ({mean_val:.1f} µg/m³)")
        elif pollutant == "PM10":
            if mean_val >= 254:
                high_risk_pollutants.append(f"PM10 ({mean_val:.1f} µg/m³)")
            elif mean_val >= 154:
                moderate_risk_pollutants.append(f"PM10 ({mean_val:.1f} µg/m³)")
        elif pollutant == "NO2":
            if mean_val >= 180:
                high_risk_pollutants.append(f"NO2 ({mean_val:.1f} µg/m³)")
            elif mean_val >= 80:
                moderate_risk_pollutants.append(f"NO2 ({mean_val:.1f} µg/m³)")
    
    # Determine overall risk level
    if high_risk_pollutants:
        insights["risk_level"] = "high"
    elif moderate_risk_pollutants:
        insights["risk_level"] = "moderate"
    else:
        insights["risk_level"] = "low"
    
    # Generate comprehensive summary
    summary_parts = []
    
    if insights["risk_level"] == "high":
        summary_parts.append(f"CRITICAL: Extremely high pollution levels detected with {', '.join(high_risk_pollutants)}.")
    elif insights["risk_level"] == "moderate":
        summary_parts.append(f"MODERATE: Elevated pollution levels with {', '.join(moderate_risk_pollutants)} require attention.")
    else:
        summary_parts.append("Air quality is within acceptable ranges for general population.")
    
    # Add data source information
    data_sources = []
    if ground_trends:
        data_sources.append(f"{len(ground_trends)} pollutants from {stations.get('count', 0)} ground stations")
    if satellite_rows:
        data_sources.append(f"{len(satellite_rows)} pollutants from satellite observations")
    
    if data_sources:
        summary_parts.append(f"Analysis based on {', '.join(data_sources)}.")
    
    # Add location context
    district_info = location_info.get('district', {})
    if district_info.get('name'):
        summary_parts.append(f"Location: {district_info['name']}, {district_info.get('province', '')} with population of {district_info.get('population', 'N/A'):,}.")
    
    insights["summary"] = " ".join(summary_parts)
    
    # === DETAILED ANALYSIS ===
    
    insights["analysis"] = {
        "pollution_sources": analyze_pollution_sources(ground_trends, gee_data),
        "temporal_patterns": analyze_temporal_patterns(temporal_patterns),
        "spatial_coverage": analyze_spatial_coverage(stations, gee_data),
        "health_impacts": analyze_health_impacts(ground_trends),
        "recommendations_detail": generate_detailed_recommendations(ground_trends, insights["risk_level"])
    }
    
    # === SPECIFIC RECOMMENDATIONS ===
    
    insights["recommendations"] = generate_detailed_recommendations(ground_trends, insights["risk_level"])
    
    # === SENSITIVE GROUPS ===
    
    insights["sensitive_groups"] = identify_sensitive_groups(ground_trends, temporal_patterns)
    
    # === TRENDS ANALYSIS ===
    
    insights["trends"] = {
        "short_term": analyze_short_term_trends(temporal_patterns),
        "seasonal_patterns": analyze_seasonal_patterns(temporal_patterns),
        "data_completeness": analyze_data_completeness(ground_trends, stations)
    }
    
    # === PROFESSIONAL NARRATIVE ===
    
    insights["professional_narrative"] = generate_professional_narrative(trend_data)
    
    return insights


def analyze_pollution_sources(ground_trends: dict, gee_data: dict) -> dict:
    """Analyze potential pollution sources based on pollutant ratios."""
    analysis = {
        "likely_sources": [],
        "confidence_level": "low",
        "explanation": ""
    }
    
    # Analyze pollutant ratios to infer sources
    pm25 = ground_trends.get("PM25", {}).get("mean", 0)
    pm10 = ground_trends.get("PM10", {}).get("mean", 0)
    no2 = ground_trends.get("NO2", {}).get("mean", 0)
    so2 = ground_trends.get("SO2", {}).get("mean", 0)
    co = ground_trends.get("CO", {}).get("mean", 0)
    
    sources = []
    
    # Traffic pollution indicators
    if no2 > 40 and co > 2:
        sources.append("vehicular traffic")
    
    # Industrial pollution indicators
    if so2 > 20 and pm10 > 100:
        sources.append("industrial emissions")
    
    # Dust/street pollution indicators
    if pm10 > pm25 * 2:
        sources.append("construction/dust")
    
    # Biomass burning indicators
    if pm25 > 50 and co > 1:
        sources.append("biomass burning")
    
    if sources:
        analysis["likely_sources"] = sources
        analysis["confidence_level"] = "medium"
        analysis["explanation"] = f"Pollutant ratios suggest contribution from: {', '.join(sources)}."
    else:
        analysis["explanation"] = "Insufficient data to determine specific pollution sources."
    
    return analysis


def analyze_temporal_patterns(temporal_patterns: dict) -> dict:
    """Analyze temporal patterns in the data."""
    return {
        "peak_hours": temporal_patterns.get("peak_hours", "Unknown"),
        "seasonal_variation": temporal_patterns.get("seasonal", "Unknown"),
        "trend_direction": temporal_patterns.get("trend", "stable"),
        "variability": temporal_patterns.get("variability", "moderate")
    }


def analyze_spatial_coverage(stations: dict, gee_data: dict) -> dict:
    """Analyze spatial coverage of monitoring data."""
    coverage = {
        "ground_stations": stations.get("count", 0),
        "satellite_coverage": "global" if gee_data else "none",
        "data_density": "low"
    }
    
    station_count = stations.get("count", 0)
    if station_count > 5:
        coverage["data_density"] = "high"
    elif station_count > 2:
        coverage["data_density"] = "medium"
    
    return coverage


def analyze_health_impacts(ground_trends: dict) -> dict:
    """Analyze potential health impacts based on pollutant levels."""
    impacts = {
        "respiratory": "low",
        "cardiovascular": "low", 
        "general_population": "minimal",
        "vulnerable_groups": "low"
    }
    
    pm25 = ground_trends.get("PM25", {}).get("mean", 0)
    pm10 = ground_trends.get("PM10", {}).get("mean", 0)
    no2 = ground_trends.get("NO2", {}).get("mean", 0)
    
    # Respiratory impacts
    if pm25 > 35 or pm10 > 150:
        impacts["respiratory"] = "moderate" if pm25 < 55 else "high"
    
    # Cardiovascular impacts
    if pm25 > 25 or no2 > 40:
        impacts["cardiovascular"] = "moderate"
    
    # General population impacts
    if pm25 > 35:
        impacts["general_population"] = "moderate"
    
    # Vulnerable groups
    if pm25 > 25:
        impacts["vulnerable_groups"] = "moderate" if pm25 < 35 else "high"
    
    return impacts


def generate_detailed_recommendations(ground_trends: dict, risk_level: str) -> list:
    """Generate detailed, specific recommendations based on pollutant levels."""
    recommendations = []
    
    pm25 = ground_trends.get("PM25", {}).get("mean", 0)
    pm10 = ground_trends.get("PM10", {}).get("mean", 0)
    no2 = ground_trends.get("NO2", {}).get("mean", 0)
    
    if risk_level in ["moderate", "high"]:
        recommendations.extend([
            "Limit outdoor activities, especially during peak pollution hours (typically morning and evening)",
            "Use air purifiers with HEPA filters indoors if available",
            "Wear N95 or higher-rated masks when outdoors",
            "Keep windows closed during high pollution periods",
            "Stay hydrated and maintain a healthy diet to support respiratory health"
        ])
        
        if pm25 > 55:
            recommendations.extend([
                "Avoid strenuous outdoor exercise",
                "Consider rescheduling outdoor activities to cleaner air days",
                "Use public transportation instead of personal vehicles if possible"
            ])
        
        if no2 > 80:
            recommendations.extend([
                "Avoid areas with heavy traffic",
                "Ensure good ventilation in indoor spaces",
                "Consider indoor air quality monitoring"
            ])
    
    # General recommendations
    recommendations.extend([
        "Monitor local air quality forecasts regularly",
        "Stay informed about pollution alerts from local authorities",
        "Consider using air quality monitoring apps for real-time updates"
    ])
    
    return list(set(recommendations))  # Remove duplicates


def identify_sensitive_groups(ground_trends: dict, temporal_patterns: dict) -> list:
    """Identify groups particularly sensitive to current pollution levels."""
    sensitive_groups = []
    
    pm25 = ground_trends.get("PM25", {}).get("mean", 0)
    pm10 = ground_trends.get("PM10", {}).get("mean", 0)
    no2 = ground_trends.get("NO2", {}).get("mean", 0)
    
    # Base sensitive groups for particulate matter
    if pm25 > 25 or pm10 > 100:
        sensitive_groups.extend([
            "Children under 14 years old",
            "Elderly adults (65+ years)",
            "Individuals with respiratory conditions (asthma, COPD)",
            "People with cardiovascular diseases",
            "Pregnant women"
        ])
    
    # Additional groups for high NO2
    if no2 > 40:
        sensitive_groups.extend([
            "Individuals with lung diseases",
            "People with diabetes",
            "Outdoor workers"
        ])
    
    # Remove duplicates and sort
    return list(set(sensitive_groups))


def analyze_short_term_trends(temporal_patterns: dict) -> dict:
    """Analyze short-term trends."""
    return {
        "daily_pattern": temporal_patterns.get("daily_pattern", "Unknown"),
        "recent_change": temporal_patterns.get("recent_trend", "stable"),
        "volatility": temporal_patterns.get("volatility", "moderate")
    }


def analyze_seasonal_patterns(temporal_patterns: dict) -> dict:
    """Analyze seasonal patterns."""
    return {
        "seasonal_variation": temporal_patterns.get("seasonal_variation", "moderate"),
        "peak_season": temporal_patterns.get("peak_season", "Unknown"),
        "typical_range": temporal_patterns.get("typical_range", "Unknown")
    }


def analyze_data_completeness(ground_trends: dict, stations: dict) -> dict:
    """Analyze data completeness and reliability."""
    completeness = {
        "pollutants_covered": len(ground_trends),
        "stations_available": stations.get("count", 0),
        "data_quality": "good",
        "temporal_coverage": "partial"
    }
    
    if len(ground_trends) >= 3:
        completeness["data_quality"] = "excellent"
    elif len(ground_trends) >= 2:
        completeness["data_quality"] = "good"
    else:
        completeness["data_quality"] = "limited"
    
    return completeness


def get_report_context(
    report_type: str,
    pollutants: list,
    start_date: date,
    end_date: date,
    district: District = None,
    province: str = None,
    location: Point = None,
    radius_km: float = 5.0,
    include_ai: bool = False,
) -> dict:
    """
    Gather data for report generation.

    Args:
        report_type: Type of report
        pollutants: List of pollutant codes
        start_date: Start date
        end_date: End date
        district: Optional district filter
        province: Optional province filter
        location: Optional location point for location-based reports
        radius_km: Search radius for location-based reports
        include_ai: Whether to include AI insights

    Returns:
        Context dictionary for report rendering
    """
    context = {
        "report_type": report_type,
        "pollutants": pollutants,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now(),
    }

    # National summary
    national_data = {}
    for pollutant in pollutants:
        national = (
            NationalExposure.objects.filter(
                pollutant=pollutant,
                date__gte=start_date,
                date__lte=end_date,
            )
            .order_by("-date")
            .first()
        )

        if national:
            national_data[pollutant] = {
                "date": national.date,
                "total_population": national.total_population,
                "concentration_mean": national.concentration_mean,
                "aqi_mean": national.aqi_mean,
                "exposure_index": national.exposure_index,
                "pop_at_risk": (
                    national.pop_usg
                    + national.pop_unhealthy
                    + national.pop_very_unhealthy
                    + national.pop_hazardous
                ),
                "n_hotspots": national.n_hotspots,
            }

    context["national"] = national_data

    # Province summaries
    if province:
        province_data = {}
        for pollutant in pollutants:
            prov_exp = (
                ProvinceExposure.objects.filter(
                    province=province,
                    pollutant=pollutant,
                    date__gte=start_date,
                    date__lte=end_date,
                )
                .order_by("-date")
                .first()
            )
            if prov_exp:
                province_data[pollutant] = {
                    "date": prov_exp.date,
                    "total_population": prov_exp.total_population,
                    "concentration_mean": prov_exp.concentration_mean,
                    "aqi_mean": prov_exp.aqi_mean,
                    "exposure_index": prov_exp.exposure_index,
                }
        context["province"] = province_data

    # District data
    if district:
        district_data = {}
        for pollutant in pollutants:
            dist_exp = (
                DistrictExposure.objects.filter(
                    district=district,
                    pollutant=pollutant,
                    date__gte=start_date,
                    date__lte=end_date,
                )
                .order_by("-date")
                .first()
            )
            if dist_exp:
                district_data[pollutant] = {
                    "date": dist_exp.date,
                    "total_population": dist_exp.total_population,
                    "concentration_mean": dist_exp.concentration_mean,
                    "aqi_mean": dist_exp.aqi_mean,
                    "exposure_index": dist_exp.exposure_index,
                }
        context["district"] = district_data

    # Get district rankings (top 10 most polluted)
    rankings = {}
    for pollutant in pollutants:
        top_districts = (
            DistrictExposure.objects.filter(
                pollutant=pollutant,
                date__gte=start_date,
                date__lte=end_date,
            )
            .select_related("district")
            .order_by("-aqi_mean")[:10]
        )
        rankings[pollutant] = [
            {
                "rank": idx + 1,
                "name": d.district.name,
                "province": d.district.province,
                "aqi_mean": d.aqi_mean,
                "exposure_index": d.exposure_index,
            }
            for idx, d in enumerate(top_districts)
        ]
    context["rankings"] = rankings

    # Hotspots
    hotspots = {}
    for pollutant in pollutants:
        spots = Hotspot.objects.filter(
            pollutant=pollutant,
            detected_date__gte=start_date,
            detected_date__lte=end_date,
            status="ACTIVE",
        ).order_by("-severity", "-aqi_mean")[:5]

        hotspots[pollutant] = [
            {
                "severity": h.severity,
                "aqi_mean": h.aqi_mean,
                "affected_population": h.affected_population,
                "persistence_days": (date.today() - h.detected_date).days
                if h.detected_date
                else 0,
            }
            for h in spots
        ]
    context["hotspots"] = hotspots

    # Location-based analysis (for LOCATION report type)
    if report_type == "LOCATION" and location:
        from datetime import datetime
        analyzer = TrendAnalyzer(
            lat=location.y,  # Point.y is latitude
            lng=location.x,  # Point.x is longitude
            radius_km=radius_km,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
        )
        
        trend_data = analyzer.generate_summary()
        context["trend_data"] = trend_data
        context["radius_km"] = radius_km
        context["include_ai"] = include_ai
        
        # Add AI insights if requested
        if include_ai:
            context["ai_insights"] = generate_ai_insights(trend_data)

    return context


def generate_pdf_report(report: Report, context: dict = None) -> Path:
    """
    Generate PDF report using ReportLab.

    Args:
        report: Report model instance
        context: Optional pre-built context

    Returns:
        Path to generated PDF file
    """
    # Build context if not provided
    if context is None:
        context = get_report_context(
            report_type=report.report_type,
            pollutants=report.pollutants,
            start_date=report.start_date,
            end_date=report.end_date,
            district=report.district,
            province=report.province,
            location=report.location,
            radius_km=report.radius_km or 5.0,
            include_ai=report.include_ai_insights,
        )

    context["report"] = report

    # Ensure output directory exists
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report.report_type.lower()}_{report.id}_{timestamp}.pdf"
    output_path = REPORTS_PATH / filename

    # Create PDF document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    # Build story (content elements)
    story = []
    styles = get_custom_styles()

    # Title
    title = f"{report.get_report_type_display()}"
    story.append(Paragraph(title, styles["CustomTitle"]))
    story.append(Spacer(1, 0.5 * cm))

    # Date range
    date_range = f"{report.start_date.strftime('%B %d, %Y')} to {report.end_date.strftime('%B %d, %Y')}"
    story.append(Paragraph(date_range, styles["CustomBody"]))
    story.append(Spacer(1, 0.5 * cm))

    # Generate report type specific content
    if report.report_type == "DAILY":
        _add_daily_content(story, context, styles)
    elif report.report_type == "WEEKLY":
        _add_weekly_content(story, context, styles)
    elif report.report_type == "DISTRICT":
        _add_district_content(story, context, styles)
    elif report.report_type == "LOCATION":
        _add_location_content(story, context, styles)
    else:
        _add_custom_content(story, context, styles)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)

    logger.info(f"Generated PDF report: {output_path}")
    return output_path


def _add_daily_content(story, context, styles):
    """Add daily report specific content."""
    # National summary section
    story.append(Paragraph("National Summary", styles["CustomHeading2"]))
    story.append(Spacer(1, 0.3 * cm))

    national = context.get("national", {})

    for pollutant, data in national.items():
        # Pollutant heading
        story.append(Paragraph(f"{pollutant}", styles["CustomHeading3"]))

        # Create metrics table
        metrics_data = [
            ["Metric", "Value"],
            ["Mean Concentration", f"{data['concentration_mean']:.2f} µg/m³"],
            ["Mean AQI", f"{data['aqi_mean']:.0f}"],
            ["AQI Category", get_aqi_category(data["aqi_mean"])],
            ["Population at Risk", f"{data['pop_at_risk']:,}"],
            ["Active Hotspots", str(data["n_hotspots"])],
        ]

        metrics_table = Table(metrics_data, colWidths=[8 * cm, 8 * cm])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2874a6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]
            )
        )

        story.append(metrics_table)
        story.append(Spacer(1, 0.5 * cm))

    # District rankings
    rankings = context.get("rankings", {})
    if rankings:
        story.append(PageBreak())
        story.append(Paragraph("District Rankings (Most Polluted)", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        for pollutant, districts in rankings.items():
            if districts:
                story.append(Paragraph(f"{pollutant}", styles["CustomHeading3"]))

                # Create rankings table
                table_data = [["Rank", "District", "Province", "AQI", "Exposure Index"]]

                for d in districts[:10]:  # Top 10
                    table_data.append(
                        [
                            str(d["rank"]),
                            d["name"],
                            d["province"],
                            f"{d['aqi_mean']:.0f}",
                            f"{d['exposure_index']:.1f}",
                        ]
                    )

                rankings_table = Table(table_data, colWidths=[2 * cm, 5 * cm, 4 * cm, 2 * cm, 3 * cm])
                rankings_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2874a6")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 10),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 1), (-1, -1), 9),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                        ]
                    )
                )

                story.append(rankings_table)
                story.append(Spacer(1, 0.5 * cm))

    # Hotspots
    hotspots = context.get("hotspots", {})
    has_hotspots = any(spots for spots in hotspots.values())

    if has_hotspots:
        story.append(PageBreak())
        story.append(Paragraph("Pollution Hotspots", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        for pollutant, spots in hotspots.items():
            if spots:
                story.append(Paragraph(f"{pollutant}", styles["CustomHeading3"]))

                for spot in spots:
                    # Hotspot box with colored border
                    spot_data = [
                        ["Severity", spot["severity"]],
                        ["Mean AQI", f"{spot['aqi_mean']:.0f}"],
                        ["Affected Population", f"{spot['affected_population']:,}"],
                        ["Persistence", f"{spot['persistence_days']} days"],
                    ]

                    spot_table = Table(spot_data, colWidths=[6 * cm, 10 * cm])

                    # Color based on severity
                    border_color = colors.red if spot["severity"] in ["SEVERE", "CRITICAL"] else colors.orange

                    spot_table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8f9fa")),
                                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                                ("BOX", (0, 0), (-1, -1), 3, border_color),
                                ("FONTSIZE", (0, 0), (-1, -1), 9),
                                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ]
                        )
                    )

                    story.append(spot_table)
                    story.append(Spacer(1, 0.3 * cm))

    # Footer
    story.append(Spacer(1, 1 * cm))
    generated_text = f"Generated on {context['generated_at'].strftime('%B %d, %Y at %H:%M')}"
    story.append(Paragraph(generated_text, styles["CustomBody"]))


def _add_weekly_content(story, context, styles):
    """Add weekly report specific content."""
    # Similar to daily but with trend analysis
    _add_daily_content(story, context, styles)


def _add_district_content(story, context, styles):
    """Add district-specific report content."""
    story.append(Paragraph("District Detailed Report", styles["CustomHeading2"]))
    story.append(Spacer(1, 0.3 * cm))

    district_data = context.get("district", {})

    if district_data:
        for pollutant, data in district_data.items():
            story.append(Paragraph(f"{pollutant} Exposure", styles["CustomHeading3"]))

            metrics_data = [
                ["Metric", "Value"],
                ["Mean Concentration", f"{data['concentration_mean']:.2f} µg/m³"],
                ["Mean AQI", f"{data['aqi_mean']:.0f}"],
                ["AQI Category", get_aqi_category(data["aqi_mean"])],
                ["Exposure Index", f"{data['exposure_index']:.2f}"],
                ["Total Population", f"{data['total_population']:,}"],
            ]

            metrics_table = Table(metrics_data, colWidths=[8 * cm, 8 * cm])
            metrics_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2874a6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ]
                )
            )

            story.append(metrics_table)
            story.append(Spacer(1, 0.5 * cm))


def generate_pollutant_comparison_chart(ground_trends: dict, gee_data: dict) -> Image:
    """
    Generate a comparison bar chart of different pollutants.
    
    Args:
        ground_trends: Ground station measurements
        gee_data: Satellite measurements from GEE
        
    Returns:
        ReportLab Image object
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=100)
        
        # === LEFT: Ground Station Pollutants ===
        if ground_trends:
            pollutants = []
            means = []
            colors_list = []
            
            for pollutant, data in ground_trends.items():
                if data.get('mean'):
                    pollutants.append(pollutant)
                    means.append(data['mean'])
                    
                    # Color based on pollutant type
                    if 'PM' in pollutant.upper():
                        colors_list.append('#e74c3c')  # Red for PM
                    elif 'NO' in pollutant.upper():
                        colors_list.append('#3498db')  # Blue for NOx
                    elif 'SO' in pollutant.upper():
                        colors_list.append('#f39c12')  # Orange for SO2
                    elif 'CO' in pollutant.upper():
                        colors_list.append('#9b59b6')  # Purple for CO
                    else:
                        colors_list.append('#95a5a6')  # Gray for others
            
            if pollutants:
                bars = ax1.barh(pollutants, means, color=colors_list, edgecolor='black', linewidth=1.5)
                ax1.set_xlabel('Concentration (μg/m³)', fontsize=11, fontweight='bold')
                ax1.set_title('Ground Station Measurements', fontsize=13, fontweight='bold', pad=15)
                ax1.grid(axis='x', alpha=0.3, linestyle='--')
                ax1.set_axisbelow(True)
                
                # Add value labels
                for bar in bars:
                    width = bar.get_width()
                    ax1.text(width, bar.get_y() + bar.get_height()/2, 
                            f'{width:.1f}', ha='left', va='center', 
                            fontsize=9, fontweight='bold', color='black')
        
        # === RIGHT: Satellite Pollutants ===
        if gee_data:
            pollutants_sat = []
            means_sat = []
            colors_sat = []
            
            for poll_key in ['no2', 'so2', 'co', 'o3']:
                if poll_key in gee_data and gee_data[poll_key].get('mean'):
                    pollutants_sat.append(poll_key.upper())
                    means_sat.append(gee_data[poll_key]['mean'])
                    
                    # Color coding
                    if poll_key == 'no2':
                        colors_sat.append('#3498db')
                    elif poll_key == 'so2':
                        colors_sat.append('#f39c12')
                    elif poll_key == 'co':
                        colors_sat.append('#9b59b6')
                    else:
                        colors_sat.append('#1abc9c')
            
            if pollutants_sat:
                bars2 = ax2.barh(pollutants_sat, means_sat, color=colors_sat, edgecolor='black', linewidth=1.5)
                ax2.set_xlabel('Column Density (mol/m²)', fontsize=11, fontweight='bold')
                ax2.set_title('Satellite Measurements (Sentinel-5P)', fontsize=13, fontweight='bold', pad=15)
                ax2.grid(axis='x', alpha=0.3, linestyle='--')
                ax2.set_axisbelow(True)
                ax2.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
                
                # Add value labels
                for bar in bars2:
                    width = bar.get_width()
                    ax2.text(width, bar.get_y() + bar.get_height()/2, 
                            f'{width:.2e}', ha='left', va='center', 
                            fontsize=8, fontweight='bold', color='black')
        
        plt.tight_layout()
        
        # Convert to ReportLab Image
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return Image(buf, width=18*cm, height=6*cm)
        
    except Exception as e:
        logger.error(f"Failed to generate pollutant comparison chart: {e}")
        return None


def generate_pm25_trend_chart(ground_trends: dict, date_range: str) -> Image:
    """
    Generate PM2.5 trend visualization with health threshold lines.
    
    Args:
        ground_trends: Ground station measurements
        date_range: Date range string for the report
        
    Returns:
        ReportLab Image object
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        pm25_data = ground_trends.get('PM25', {})
        if not pm25_data:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 5), dpi=100)
        
        # Get statistics
        mean_val = pm25_data.get('mean', 0)
        max_val = pm25_data.get('max', 0)
        min_val = pm25_data.get('min', 0)
        p95 = pm25_data.get('p95', 0)
        
        # Create visualization
        categories = ['Minimum', 'Mean', '95th Percentile', 'Maximum']
        values = [min_val, mean_val, p95, max_val]
        colors = ['#2ecc71', '#f39c12', '#e67e22', '#e74c3c']
        
        bars = ax.bar(categories, values, color=colors, edgecolor='black', linewidth=2, alpha=0.8)
        
        # Add WHO guideline line
        ax.axhline(y=15, color='blue', linestyle='--', linewidth=2, label='WHO 24-hr Guideline (15 μg/m³)')
        ax.axhline(y=35, color='orange', linestyle='--', linewidth=2, label='National Standard (35 μg/m³)')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_ylabel('PM2.5 Concentration (μg/m³)', fontsize=12, fontweight='bold')
        ax.set_title(f'PM2.5 Trends - {date_range}', fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        
        plt.tight_layout()
        
        # Convert to ReportLab Image
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return Image(buf, width=16*cm, height=7*cm)
        
    except Exception as e:
        logger.error(f"Failed to generate PM2.5 trend chart: {e}")
        return None


def generate_aqi_gauge(aqi_value: float) -> Image:
    """
    Generate an AQI gauge/indicator visualization.
    
    Args:
        aqi_value: Air Quality Index value
        
    Returns:
        ReportLab Image object
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Wedge, Rectangle
        from io import BytesIO
        
        fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        
        # AQI categories and colors
        categories = [
            (0, 50, 'Good', '#00e400'),
            (51, 100, 'Moderate', '#ffff00'),
            (101, 150, 'USG', '#ff7e00'),
            (151, 200, 'Unhealthy', '#ff0000'),
            (201, 300, 'Very Unhealthy', '#8f3f97'),
            (301, 500, 'Hazardous', '#7e0023')
        ]
        
        # Draw gauge
        radius = 1.0
        for i, (min_aqi, max_aqi, label, color) in enumerate(categories):
            theta1 = 180 - (i * 30)
            theta2 = 180 - ((i + 1) * 30)
            wedge = Wedge((0, 0), radius, theta2, theta1, width=0.3, 
                         facecolor=color, edgecolor='black', linewidth=2)
            ax.add_patch(wedge)
        
        # Calculate needle angle based on AQI
        if aqi_value <= 50:
            angle = 180 - (aqi_value / 50) * 30
        elif aqi_value <= 100:
            angle = 150 - ((aqi_value - 50) / 50) * 30
        elif aqi_value <= 150:
            angle = 120 - ((aqi_value - 100) / 50) * 30
        elif aqi_value <= 200:
            angle = 90 - ((aqi_value - 150) / 50) * 30
        elif aqi_value <= 300:
            angle = 60 - ((aqi_value - 200) / 100) * 30
        else:
            angle = 30 - ((min(aqi_value, 500) - 300) / 200) * 30
        
        # Draw needle
        import numpy as np
        angle_rad = np.radians(angle)
        needle_length = 0.7
        ax.plot([0, needle_length * np.cos(angle_rad)], 
               [0, needle_length * np.sin(angle_rad)],
               'k-', linewidth=4, zorder=5)
        ax.plot(0, 0, 'ko', markersize=15, zorder=6)
        
        # Add AQI value text
        ax.text(0, -0.3, f'{aqi_value:.0f}', ha='center', va='center',
               fontsize=36, fontweight='bold', color='black')
        ax.text(0, -0.5, 'AQI', ha='center', va='center',
               fontsize=16, fontweight='bold', color='gray')
        
        # Get category
        category_name = 'Hazardous'
        for min_aqi, max_aqi, label, color in categories:
            if min_aqi <= aqi_value <= max_aqi:
                category_name = label
                break
        
        ax.text(0, -0.7, category_name, ha='center', va='center',
               fontsize=14, fontweight='bold', color='red' if aqi_value > 150 else 'black')
        
        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-1, 1)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title('Air Quality Index (AQI)', fontsize=16, fontweight='bold', pad=10)
        
        plt.tight_layout()
        
        # Convert to ReportLab Image
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='white')
        buf.seek(0)
        plt.close(fig)
        
        return Image(buf, width=10*cm, height=8*cm)
        
    except Exception as e:
        logger.error(f"Failed to generate AQI gauge: {e}")
        return None


def generate_location_map(lat: float, lng: float, radius_km: float = 5.0, 
                          gee_data: dict = None) -> Image:
    """
    Generate a static map image with satellite overlay using static map APIs and GEE getThumbURL().
    
    Args:
        lat: Latitude of center point
        lng: Longitude of center point
        radius_km: Radius for analysis area
        gee_data: Optional GEE data dictionary with satellite measurements
        
    Returns:
        ReportLab Image object or None if generation fails
    """
    logger.info(f"🗺️ STARTING MAP GENERATION for ({lat}, {lng}) with radius {radius_km}km")
    logger.info(f"📊 GEE Data available: {bool(gee_data)}")
    
    try:
        # Import all required libraries at the top
        from PIL import Image as PILImage, ImageDraw, ImageFont
        from io import BytesIO
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.colorbar import ColorbarBase
        from matplotlib.colors import Normalize, LinearSegmentedColormap
        from datetime import datetime, timedelta
        # Note: Don't import matplotlib.cm as cm - it conflicts with reportlab.lib.units.cm
        
        logger.info("✅ Successfully imported PIL and matplotlib")
        
        # Initialize GEE early to ensure authentication is available
        try:
            from air_quality.services.gee_auth import initialize_gee
            initialize_gee()
            logger.info("✅ GEE initialized successfully for map generation")
        except Exception as e:
            logger.warning(f"⚠️ GEE initialization warning: {e}")
        
        # Calculate map bounds
        lat_delta = (radius_km / 111) * 1.8
        lng_delta = (radius_km / (111 * abs(np.cos(np.radians(lat))))) * 1.8
        
        min_lat, max_lat = lat - lat_delta, lat + lat_delta
        min_lng, max_lng = lng - lng_delta, lng + lng_delta
        
        # Create composite image with two maps side by side
        map_width, map_height = 800, 400
        composite = PILImage.new('RGB', (map_width * 2 + 40, map_height + 100), 'white')
        draw = ImageDraw.Draw(composite)
        
        # === LEFT: OpenStreetMap Static Image ===
        try:
            # Use OpenStreetMap static map API
            zoom = max(10, min(15, int(17 - np.log2(radius_km))))
            osm_url = f"https://tile.openstreetmap.org/{zoom}/{int((lng + 180) / 360 * 2**zoom)}/{int((1 - np.log(np.tan(lat * np.pi / 180) + 1 / np.cos(lat * np.pi / 180)) / np.pi) / 2 * 2**zoom)}.png"
            
            # For better results, use StaticMap API or similar service
            # Using a simple approach with center marker
            base_url = "https://maps.geoapify.com/v1/staticmap"
            api_key = "YOUR_API_KEY"  # Replace with actual key or use env variable
            
            # Create enhanced visualization using matplotlib
            logger.info("📍 Creating enhanced base map with matplotlib...")
            
            fig1, ax1 = plt.subplots(1, 1, figsize=(8, 4), dpi=120)
            
            # Draw base map with gradient background
            ax1.set_xlim(min_lng, max_lng)
            ax1.set_ylim(min_lat, max_lat)
            
            # Create gradient background
            import matplotlib.patches as patches
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            ax1.imshow(gradient, extent=[min_lng, max_lng, min_lat, max_lat], 
                      aspect='auto', cmap='Blues', alpha=0.3, zorder=0)
            
            ax1.grid(True, alpha=0.4, linestyle='--', linewidth=0.8, color='gray')
            
            # Draw multiple radius circles for depth
            for i, alpha_val in zip([1.5, 1.2, 1.0, 0.7], [0.05, 0.08, 0.12, 0.15]):
                circle_bg = mpatches.Circle((lng, lat), radius_km/111 * i, 
                                          fill=True, facecolor='red', alpha=alpha_val, zorder=1)
                ax1.add_patch(circle_bg)
            
            # Draw main radius circle
            circle = mpatches.Circle((lng, lat), radius_km/111, fill=False, 
                                   edgecolor='#e74c3c', linewidth=3, linestyle='--',
                                   alpha=0.9, label=f'{radius_km}km Analysis Radius', zorder=4)
            ax1.add_patch(circle)
            
            # Draw center point with glow effect
            ax1.plot(lng, lat, 'o', color='#e74c3c', markersize=25, alpha=0.3, zorder=4)
            ax1.plot(lng, lat, 'o', color='#e74c3c', markersize=18, alpha=0.5, zorder=5)
            ax1.plot(lng, lat, 'o', color='#c0392b', markersize=12, 
                    markeredgecolor='white', markeredgewidth=2, label='Analysis Center', zorder=6)
            
            # Add grid lines for reference
            ax1.axhline(y=lat, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
            ax1.axvline(x=lng, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
            
            # Labels
            ax1.set_xlabel('Longitude (°E)', fontsize=10, fontweight='bold')
            ax1.set_ylabel('Latitude (°N)', fontsize=10, fontweight='bold')
            ax1.set_title('Analysis Location', fontsize=12, fontweight='bold', pad=10)
            ax1.legend(loc='upper right', fontsize=9, framealpha=0.9)
            
            # Add coordinate text
            ax1.text(0.02, 0.98, f'{lat:.4f}°N, {lng:.4f}°E', 
                    transform=ax1.transAxes, fontsize=9,
                    verticalalignment='top', bbox=dict(boxstyle='round', 
                    facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            
            # Convert to PIL Image
            buf1 = BytesIO()
            plt.savefig(buf1, format='png', dpi=100, bbox_inches='tight')
            buf1.seek(0)
            base_map = PILImage.open(buf1)
            composite.paste(base_map, (20, 50))
            plt.close(fig1)
            
        except Exception as e:
            logger.warning(f"Base map generation failed: {e}")
        
        # === RIGHT: Satellite NO2 Overlay using GEE ===
        satellite_added = False
        
        # Only attempt GEE if we have satellite data in context
        if gee_data and gee_data.get('no2') and not gee_data.get('error'):
            try:
                import ee
                
                logger.info("🛰️ Generating NO2 satellite overlay from GEE...")
                
                # Define region of interest
                region = ee.Geometry.Rectangle([min_lng, min_lat, max_lng, max_lat])
                
                # Get Sentinel-5P NO2 data (last 30 days for cleaner composite)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                
                logger.info(f"📅 Date range: {start_date.date()} to {end_date.date()}")
                
                collection = (ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2')
                            .filterDate(start_date.strftime('%Y-%m-%d'), 
                                       end_date.strftime('%Y-%m-%d'))
                            .filterBounds(region)
                            .select('tropospheric_NO2_column_number_density'))
                
                # Calculate mean NO2
                no2_mean = collection.mean().clip(region)
                
                # Define visualization parameters matching GEE palette
                vis_params = {
                    'min': 0,
                    'max': 0.0002,
                    'palette': ['black', 'blue', 'purple', 'cyan', 'green', 
                               'yellow', 'orange', 'red']
                }
                
                # Get thumbnail URL for static PNG
                logger.info("📡 Requesting GEE thumbnail URL...")
                thumb_params = {
                    'region': region,
                    'dimensions': 800,
                    'format': 'png',
                    **vis_params
                }
                
                thumb_url = no2_mean.getThumbURL(thumb_params)
                
                logger.info(f"🌍 Downloading satellite image (URL length: {len(thumb_url)} chars)...")
                
                # Download the satellite image
                response = requests.get(thumb_url, timeout=90)
                logger.info(f"📥 GEE response status: {response.status_code}")
                
                if response.status_code == 200:
                    satellite_img = PILImage.open(BytesIO(response.content))
                    logger.info(f"✅ Downloaded satellite image: {satellite_img.size}")
                    
                    # Create figure for satellite overlay
                    fig2, ax2 = plt.subplots(1, 1, figsize=(8, 4), dpi=100)
                    
                    # Display satellite image
                    ax2.imshow(satellite_img, extent=[min_lng, max_lng, min_lat, max_lat], 
                              aspect='auto', interpolation='bilinear')
                    
                    # Overlay analysis location
                    ax2.plot(lng, lat, 'w*', markersize=20, markeredgecolor='black', 
                            markeredgewidth=2, zorder=5)
                    
                    # Draw radius circle
                    circle2 = mpatches.Circle((lng, lat), radius_km/111, fill=False, 
                                            edgecolor='white', linewidth=2.5, linestyle='--',
                                            alpha=0.9)
                    ax2.add_patch(circle2)
                    
                    ax2.set_xlabel('Longitude (°E)', fontsize=10, fontweight='bold')
                    ax2.set_ylabel('Latitude (°N)', fontsize=10, fontweight='bold')
                    ax2.set_title('NO₂ Tropospheric Column\n(Sentinel-5P, 30-day mean)', 
                                 fontsize=11, fontweight='bold', pad=10)
                    
                    # Add colorbar with custom colormap matching GEE palette
                    colors_list = ['black', 'blue', 'purple', 'cyan', 'green', 
                                  'yellow', 'orange', 'red']
                    n_bins = 100
                    cmap = LinearSegmentedColormap.from_list('gee_no2', colors_list, N=n_bins)
                    
                    cax = fig2.add_axes([0.92, 0.15, 0.02, 0.7])
                    norm = Normalize(vmin=0, vmax=0.0002)
                    cb = ColorbarBase(cax, cmap=cmap, norm=norm, orientation='vertical')
                    cb.set_label('NO₂ (mol/m²)', fontsize=9, fontweight='bold')
                    cb.ax.tick_params(labelsize=8)
                    
                    plt.tight_layout()
                    
                    # Convert to PIL Image
                    buf2 = BytesIO()
                    plt.savefig(buf2, format='png', dpi=100, bbox_inches='tight', 
                               facecolor='white')
                    buf2.seek(0)
                    satellite_map = PILImage.open(buf2)
                    composite.paste(satellite_map, (map_width + 60, 50))
                    plt.close(fig2)
                    
                    satellite_added = True
                    logger.info("✅ Successfully generated GEE NO2 satellite overlay")
                else:
                    logger.warning(f"Failed to download GEE thumbnail: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ GEE satellite overlay failed: {str(e)[:200]}")
        
        # If no satellite overlay, create enhanced visualization from GEE data we already have
        if not satellite_added and gee_data:
            logger.info("📊 Creating enhanced satellite data visualization from existing GEE measurements...")
            fig3, ax3 = plt.subplots(1, 1, figsize=(8, 4), dpi=120)
            
            # Create a heatmap-style visualization of NO2 data
            no2_data = gee_data.get('no2', {})
            if no2_data and no2_data.get('mean'):
                # Create visualization showing NO2 concentration
                no2_mean = no2_data.get('mean', 0)
                no2_max = no2_data.get('max', 0)
                
                # Set up the plot with dark theme
                ax3.set_xlim(min_lng, max_lng)
                ax3.set_ylim(min_lat, max_lat)
                ax3.set_facecolor('#0a0a1a')
                
                # Create a gradient circle representing NO2 concentration
                from matplotlib.patches import Circle
                from matplotlib.collections import PatchCollection
                
                # Multiple circles with decreasing alpha for gradient effect
                circles = []
                colors_list = []
                alphas = []
                
                num_circles = 20
                max_radius = radius_km / 111
                
                for i in range(num_circles):
                    r = max_radius * (1 - i / num_circles)
                    circle = Circle((lng, lat), r)
                    circles.append(circle)
                    
                    # Color based on NO2 concentration
                    intensity = (no2_mean / 0.0002) if no2_mean > 0 else 0
                    intensity = min(1.0, intensity)
                    
                    if intensity < 0.2:
                        color = 'cyan'
                    elif intensity < 0.4:
                        color = 'green'
                    elif intensity < 0.6:
                        color = 'yellow'
                    elif intensity < 0.8:
                        color = 'orange'
                    else:
                        color = 'red'
                    
                    colors_list.append(color)
                    alphas.append(0.3 * (1 - i / num_circles))
                
                pc = PatchCollection(circles, facecolors=colors_list, alpha=0.3)
                ax3.add_collection(pc)
                
                # Add center marker
                ax3.plot(lng, lat, 'w*', markersize=20, markeredgecolor='black', 
                        markeredgewidth=2, zorder=5)
                
                # Add grid
                ax3.grid(True, alpha=0.2, color='white', linestyle='--')
                
                ax3.set_xlabel('Longitude (°E)', fontsize=10, fontweight='bold', color='white')
                ax3.set_ylabel('Latitude (°N)', fontsize=10, fontweight='bold', color='white')
                ax3.set_title(f'NO₂ Concentration Visualization\n(Mean: {no2_mean:.2e} mol/m²)', 
                             fontsize=11, fontweight='bold', pad=10, color='white')
                
                # Make tick labels white
                ax3.tick_params(colors='white')
                
                # Add text annotation
                ax3.text(0.02, 0.98, f'Sentinel-5P Data\n{no2_mean:.2e} mol/m²', 
                        transform=ax3.transAxes, fontsize=9, color='white',
                        verticalalignment='top', bbox=dict(boxstyle='round', 
                        facecolor='black', alpha=0.7, edgecolor='white'))
            else:
                # No NO2 data - show placeholder
                ax3.text(0.5, 0.5, 'Satellite Data Visualization\n\nNO₂ measurements from\nSentinel-5P satellite',
                        ha='center', va='center', fontsize=11, color='white',
                        bbox=dict(boxstyle='round', facecolor='#2a2a3e', alpha=0.9, edgecolor='cyan'))
                ax3.set_xlim(0, 1)
                ax3.set_ylim(0, 1)
                ax3.axis('off')
                ax3.set_facecolor('#1a1a2e')
            
            ax3.set_title('Satellite Data Visualization', fontsize=12, fontweight='bold', 
                         pad=10, color='white')
            
            buf3 = BytesIO()
            plt.savefig(buf3, format='png', dpi=100, bbox_inches='tight', 
                       facecolor='#1a1a2e', edgecolor='none')
            buf3.seek(0)
            satellite_vis_map = PILImage.open(buf3)
            composite.paste(satellite_vis_map, (map_width + 60, 50))
            plt.close(fig3)
            
            satellite_added = True  # Mark as added so we don't show "unavailable" message
        
        # Add title and footer to composite
        try:
            font_title = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 11)
        except:
            font_title = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((composite.width // 2, 20), 'Geographic Analysis & Satellite Overlay', 
                 fill='black', font=font_title, anchor='mm')
        draw.text((composite.width // 2, composite.height - 20), 
                 f'Center: {lat:.4f}°N, {lng:.4f}°E | Analysis Radius: {radius_km}km', 
                 fill='gray', font=font_small, anchor='mm')
        
        # Convert composite to ReportLab Image
        img_buffer = BytesIO()
        composite.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Create ReportLab Image
        reportlab_img = Image(img_buffer, width=17*cm, height=8.5*cm)
        
        logger.info(f"✅ Successfully generated complete location map for {lat}, {lng}")
        return reportlab_img
        
    except Exception as e:
        logger.error(f"❌ Failed to generate location map: {e}", exc_info=True)
        
        # Create a simple error placeholder image instead of returning None
        try:
            from PIL import Image as PILImage, ImageDraw, ImageFont
            from io import BytesIO
            
            # Create simple error message image
            error_img = PILImage.new('RGB', (1600, 500), 'white')
            draw = ImageDraw.Draw(error_img)
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 14)
            except:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            draw.text((800, 200), '⚠️ Map Generation Temporarily Unavailable', 
                     fill='black', font=font_large, anchor='mm')
            draw.text((800, 250), f'Location: {lat:.4f}°N, {lng:.4f}°E', 
                     fill='gray', font=font_small, anchor='mm')
            draw.text((800, 280), f'Analysis Radius: {radius_km}km', 
                     fill='gray', font=font_small, anchor='mm')
            draw.text((800, 350), 'Check logs for details', 
                     fill='red', font=font_small, anchor='mm')
            
            # Convert to ReportLab Image
            img_buffer = BytesIO()
            error_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return Image(img_buffer, width=17*cm, height=8.5*cm)
        except:
            # Last resort - return None and let calling code handle it
            logger.error("Even fallback image generation failed!")
            return None


def _add_location_content(story, context, styles):
    """Add location-based report content with AI insights."""
    # Location information
    location = context.get("location", {})
    if location:
        story.append(Paragraph("Location Analysis", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))
        
        # Add location map with satellite overlay
        trend_data = context.get("trend_data", {})
        gee_data = trend_data.get("gee_data", {}) if trend_data else {}
        
        try:
            map_image = generate_location_map(
                lat=location.get('lat'),
                lng=location.get('lng'),
                radius_km=context.get('radius_km', 5.0),
                gee_data=gee_data if not gee_data.get('error') else None
            )
            if map_image:
                story.append(Paragraph("Geographic Analysis & Satellite Overlay", styles["CustomHeading3"]))
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph(
                    "Left: Analysis location with radius boundary. Right: Sentinel-5P NO₂ satellite overlay showing pollution concentration.",
                    styles["CustomCaption"]
                ))
                story.append(Spacer(1, 0.2 * cm))
                story.append(map_image)
                story.append(Spacer(1, 0.4 * cm))
            else:
                logger.warning("Map generation returned None - skipping map in report")
        except Exception as e:
            logger.error(f"Error adding map to report: {e}", exc_info=True)

        # Build location data table with proper None handling
        lat = location.get('lat')
        lng = location.get('lng')
        radius = context.get('radius_km')
        
        location_data = [
            ["Latitude", f"{lat:.4f}" if lat is not None else 'N/A'],
            ["Longitude", f"{lng:.4f}" if lng is not None else 'N/A'],
            ["Analysis Radius", f"{radius} km" if radius is not None else 'N/A'],
        ]
        
        # Add district information if available
        district_info = location.get('district')
        if district_info:
            pop = district_info.get('population')
            area = district_info.get('area_km2')
            
            location_data.extend([
                ["District", district_info.get('name', 'N/A')],
                ["Province", district_info.get('province', 'N/A')],
                ["District Population", f"{pop:,}" if pop is not None else 'N/A'],
                ["District Area", f"{area:.1f} km²" if area is not None else 'N/A'],
            ])

        location_table = Table(location_data, colWidths=[6 * cm, 10 * cm])
        location_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        story.append(location_table)
        story.append(Spacer(1, 0.5 * cm))

    # Trend data
    trend_data = context.get("trend_data", {})
    if trend_data:
        story.append(Paragraph("Air Quality Trends", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        # Ground trends
        ground_trends = trend_data.get("ground_trends", {})
        if ground_trends:
            story.append(Paragraph("Ground Station Measurements", styles["CustomHeading3"]))

            trend_table_data = [["Pollutant", "Mean (µg/m³)", "Max (µg/m³)", "95th Percentile (µg/m³)"]]
            for pollutant, data in ground_trends.items():
                mean_val = data.get('mean', 'N/A')
                max_val = data.get('max', 'N/A')
                p95_val = data.get('p95', 'N/A')
                
                # Format values appropriately
                if isinstance(mean_val, (int, float)):
                    mean_str = f"{mean_val:.1f}"
                else:
                    mean_str = str(mean_val)
                    
                if isinstance(max_val, (int, float)):
                    max_str = f"{max_val:.1f}"
                else:
                    max_str = str(max_val)
                    
                if isinstance(p95_val, (int, float)):
                    p95_str = f"{p95_val:.1f}"
                else:
                    p95_str = str(p95_val)
                
                trend_table_data.append([
                    pollutant,
                    mean_str,
                    max_str,
                    p95_str,
                ])

            trend_table = Table(trend_table_data, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm])
            trend_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2874a6")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]
                )
            )

            story.append(trend_table)
            story.append(Spacer(1, 0.5 * cm))
            
            # Add PM2.5 trend chart if available
            if 'PM25' in ground_trends or 'PM2.5' in ground_trends:
                pm25_chart = generate_pm25_trend_chart(ground_trends, context.get('date_range', ''))
                if pm25_chart:
                    story.append(Paragraph("PM2.5 Trend Analysis", styles["CustomHeading3"]))
                    story.append(Spacer(1, 0.2 * cm))
                    story.append(pm25_chart)
                    story.append(Spacer(1, 0.5 * cm))

        # GEE Satellite data
        gee_data = trend_data.get("gee_data", {})
        if gee_data and not gee_data.get("error"):
            story.append(Paragraph("Satellite Measurements (GEE)", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))
            
            # Add note about satellite data
            story.append(Paragraph(
                "Data from Google Earth Engine Sentinel-5P satellite observations",
                styles["CustomCaption"]
            ))
            story.append(Spacer(1, 0.2 * cm))

            gee_table_data = [["Pollutant", "Mean", "Max", "Unit"]]
            for pollutant in ["no2", "so2", "co", "o3"]:
                if pollutant in gee_data:
                    data = gee_data[pollutant]
                    gee_table_data.append([
                        pollutant.upper(),
                        f"{data.get('mean', 'N/A'):.2e}",
                        f"{data.get('max', 'N/A'):.2e}",
                        data.get('unit', 'N/A'),
                    ])

            if len(gee_table_data) > 1:  # Only add table if we have data
                gee_table = Table(gee_table_data, colWidths=[3 * cm, 3 * cm, 3 * cm, 2 * cm])
                gee_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#28a745")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ]
                    )
                )

                story.append(gee_table)
                story.append(Spacer(1, 0.3 * cm))
                
                # Add note about satellite vs ground data
                story.append(Paragraph(
                    "Note: Satellite data provides broader spatial coverage but may differ from ground measurements due to different measurement methods and altitudes.",
                    styles["CustomCaption"]
                ))
                story.append(Spacer(1, 0.5 * cm))
        
        # Add pollutant comparison chart
        if ground_trends or gee_data:
            comparison_chart = generate_pollutant_comparison_chart(ground_trends, gee_data)
            if comparison_chart:
                story.append(Paragraph("Pollutant Comparison", styles["CustomHeading3"]))
                story.append(Spacer(1, 0.2 * cm))
                story.append(Paragraph(
                    "Comparative analysis of ground station and satellite measurements for different pollutants.",
                    styles["CustomCaption"]
                ))
                story.append(Spacer(1, 0.2 * cm))
                story.append(comparison_chart)
                story.append(Spacer(1, 0.5 * cm))
        
        # Add AQI Gauge if PM2.5 data available
        if ground_trends and ('PM25' in ground_trends or 'PM2.5' in ground_trends):
            pm25_data = ground_trends.get('PM25') or ground_trends.get('PM2.5')
            if pm25_data and pm25_data.get('mean'):
                # Calculate AQI from PM2.5
                pm25_mean = pm25_data['mean']
                # Simple AQI calculation (US EPA formula)
                if pm25_mean <= 12.0:
                    aqi = pm25_mean * 50 / 12.0
                elif pm25_mean <= 35.4:
                    aqi = 50 + (pm25_mean - 12.0) * 50 / (35.4 - 12.0)
                elif pm25_mean <= 55.4:
                    aqi = 100 + (pm25_mean - 35.4) * 50 / (55.4 - 35.4)
                elif pm25_mean <= 150.4:
                    aqi = 150 + (pm25_mean - 55.4) * 50 / (150.4 - 55.4)
                elif pm25_mean <= 250.4:
                    aqi = 200 + (pm25_mean - 150.4) * 100 / (250.4 - 150.4)
                else:
                    aqi = 300 + (pm25_mean - 250.4) * 200 / (500.4 - 250.4)
                
                aqi_gauge = generate_aqi_gauge(aqi)
                if aqi_gauge:
                    story.append(Paragraph("Air Quality Index", styles["CustomHeading3"]))
                    story.append(Spacer(1, 0.2 * cm))
                    story.append(Paragraph(
                        f"Based on PM2.5 mean concentration of {pm25_mean:.1f} µg/m³",
                        styles["CustomCaption"]
                    ))
                    story.append(Spacer(1, 0.2 * cm))
                    story.append(aqi_gauge)
                    story.append(Spacer(1, 0.5 * cm))

        # Satellite Imagery
        if gee_data and not gee_data.get("error"):
            story.append(Paragraph("Satellite Pollution Maps", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))
            
            # Add note about satellite imagery
            story.append(Paragraph(
                "Interactive pollution maps showing satellite-derived measurements around your location:",
                styles["CustomCaption"]
            ))
            story.append(Spacer(1, 0.2 * cm))
            
            # Add tile URLs as clickable links
            tile_urls = gee_data.get("tile_urls", {})
            if tile_urls:
                map_data = []
                for pollutant, url in tile_urls.items():
                    map_data.append([
                        pollutant.upper(),
                        f"View {pollutant.upper()} Map"
                    ])
                
                if map_data:
                    # Create a table with pollutant names and map links
                    map_table = Table(map_data, colWidths=[3 * cm, 10 * cm])
                    map_table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#28a745")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                                ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ]
                        )
                    )
                    
                    story.append(map_table)
                    story.append(Spacer(1, 0.2 * cm))
                    
                    # Add note about accessing maps
                    story.append(Paragraph(
                        "Note: Interactive maps are available in the web dashboard. Satellite data provides broader spatial coverage than ground stations.",
                        styles["CustomCaption"]
                    ))
            else:
                story.append(Paragraph(
                    "Map tiles are being processed. Check the web dashboard for interactive pollution maps.",
                    styles["CustomCaption"]
                ))
            
            story.append(Spacer(1, 0.5 * cm))

    # AI Insights (Premium feature)
    ai_insights = context.get("ai_insights")
    if ai_insights:
        story.append(PageBreak())
        story.append(Paragraph("🤖 AI-Powered Health Insights", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        # Data Tables Analyzed by AI
        data_tables = ai_insights.get("data_tables", {})
        if data_tables:
            story.append(Paragraph("Data Analysis Tables", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))
            story.append(Paragraph(
                "The AI analyzes the following comprehensive data tables to provide health insights:",
                styles["CustomCaption"]
            ))
            story.append(Spacer(1, 0.3 * cm))

            for table_key, table_data in data_tables.items():
                if table_data.get("rows"):  # Only show tables with data
                    # Table title
                    story.append(Paragraph(table_data["title"], styles["CustomHeading4"]))
                    story.append(Spacer(1, 0.1 * cm))

                    # Create table
                    headers = table_data["headers"]
                    rows = table_data["rows"]

                    # Combine headers and rows
                    table_data_rows = [headers] + rows

                    # Create table with appropriate column widths
                    num_cols = len(headers)
                    col_width = 16 * cm / num_cols if num_cols > 0 else 8 * cm

                    table = Table(table_data_rows, colWidths=[col_width] * num_cols)
                    table.setStyle(
                        TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e86c1")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                                ("FONTSIZE", (0, 0), (-1, 0), 9),
                                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                                ("FONTSIZE", (0, 1), (-1, -1), 8),
                                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ]
                        )
                    )

                    story.append(table)
                    story.append(Spacer(1, 0.4 * cm))

        # AI Analysis Section
        analysis = ai_insights.get("analysis", {})
        if analysis:
            story.append(Paragraph("AI Analysis Details", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))

            # Pollution Sources Analysis
            pollution_sources = analysis.get("pollution_sources", {})
            if pollution_sources.get("likely_sources"):
                story.append(Paragraph("Potential Pollution Sources:", styles["CustomHeading4"]))
                sources_text = f"Based on pollutant ratios, likely sources include: {', '.join(pollution_sources['likely_sources'])}."
                if pollution_sources.get("explanation"):
                    sources_text += f" {pollution_sources['explanation']}"
                story.append(Paragraph(sources_text, styles["CustomBody"]))
                story.append(Spacer(1, 0.2 * cm))

            # Health Impacts Analysis
            health_impacts = analysis.get("health_impacts", {})
            if any(impact != "low" and impact != "minimal" for impact in health_impacts.values()):
                story.append(Paragraph("Health Impact Assessment:", styles["CustomHeading4"]))
                impact_details = []
                for system, level in health_impacts.items():
                    if level not in ["low", "minimal"]:
                        impact_details.append(f"{system.replace('_', ' ').title()}: {level}")
                if impact_details:
                    story.append(Paragraph("; ".join(impact_details), styles["CustomBody"]))
                    story.append(Spacer(1, 0.2 * cm))

            # Spatial Coverage
            spatial_coverage = analysis.get("spatial_coverage", {})
            if spatial_coverage:
                story.append(Paragraph("Data Coverage:", styles["CustomHeading4"]))
                coverage_text = f"Ground stations: {spatial_coverage.get('ground_stations', 0)}, Satellite coverage: {spatial_coverage.get('satellite_coverage', 'none')}, Data density: {spatial_coverage.get('data_density', 'unknown')}"
                story.append(Paragraph(coverage_text, styles["CustomBody"]))
                story.append(Spacer(1, 0.2 * cm))

        # Summary
        if ai_insights.get("summary"):
            story.append(Paragraph("AI Summary", styles["CustomHeading3"]))
            story.append(Paragraph(ai_insights["summary"], styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Professional Narrative (High Class Report)
        professional_narrative = ai_insights.get("professional_narrative")
        if professional_narrative:
            story.append(Paragraph("Executive Analysis", styles["CustomHeading2"]))
            story.append(Spacer(1, 0.2 * cm))

            # Executive Summary
            if professional_narrative.get("executive_summary"):
                story.append(Paragraph("Executive Summary", styles["CustomHeading3"]))
                story.append(Paragraph(professional_narrative["executive_summary"], styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

            # Geographic Analysis (NEW - Spatial Analysis)
            if professional_narrative.get("geographic_analysis"):
                story.append(Paragraph("Geographic Analysis", styles["CustomHeading3"]))
                story.append(Paragraph(professional_narrative["geographic_analysis"], styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

            # Source Identification (Enhanced)
            if professional_narrative.get("source_identification"):
                story.append(Paragraph("Pollution Source Identification", styles["CustomHeading3"]))
                story.append(Paragraph(professional_narrative["source_identification"], styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

            # Trend Narrative
            if professional_narrative.get("trend_narrative"):
                story.append(Paragraph("Temporal Trend Analysis", styles["CustomHeading3"]))
                story.append(Paragraph(professional_narrative["trend_narrative"], styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

            # Forecast & Advisory (NEW - 48-hour forecast)
            if professional_narrative.get("forecast_advisory"):
                story.append(Paragraph("48-Hour Forecast & Advisory", styles["CustomHeading3"]))
                story.append(Paragraph(professional_narrative["forecast_advisory"], styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

            # Professional Recommendations
            if professional_narrative.get("recommendations"):
                story.append(Paragraph("Policy & Health Recommendations", styles["CustomHeading3"]))
                for rec in professional_narrative["recommendations"]:
                    story.append(Paragraph(f"• {rec}", styles["CustomBody"]))
                story.append(Spacer(1, 0.3 * cm))

        # Recommendations
        recommendations = ai_insights.get("recommendations", [])
        if recommendations:
            story.append(Paragraph("Personalized Health Recommendations", styles["CustomHeading3"]))
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Risk level
        risk_level = ai_insights.get("risk_level")
        if risk_level:
            risk_colors = {
                "low": colors.green,
                "moderate": colors.orange,
                "high": colors.red
            }
            risk_color = risk_colors.get(risk_level.lower(), colors.black)

            story.append(Paragraph(f"Overall Risk Level: {risk_level.upper()}", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))

        # Sensitive groups
        sensitive_groups = ai_insights.get("sensitive_groups", [])
        if sensitive_groups:
            story.append(Paragraph("Particularly Vulnerable Groups:", styles["CustomBody"]))
            groups_text = ", ".join(sensitive_groups)
            story.append(Paragraph(groups_text, styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Trends Analysis
        trends = ai_insights.get("trends", {})
        if trends:
            story.append(Paragraph("Trend Analysis", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))

            data_completeness = trends.get("data_completeness", {})
            if data_completeness:
                completeness_text = f"Data Quality: {data_completeness.get('data_quality', 'unknown').title()} | Pollutants Covered: {data_completeness.get('pollutants_covered', 0)} | Stations: {data_completeness.get('stations_available', 0)}"
                story.append(Paragraph(completeness_text, styles["CustomCaption"]))
                story.append(Spacer(1, 0.2 * cm))

        # Model info
        model = ai_insights.get("model", "AI Assistant")
        story.append(Paragraph(f"Analysis generated by {model}", styles["CustomBody"]))
        story.append(Spacer(1, 0.5 * cm))


def generate_html_report(context: dict, template_name: str = None) -> str:
    """
    Generate HTML report from template and context.
    Kept for backwards compatibility and HTML export option.

    Args:
        context: Template context
        template_name: Template name to use

    Returns:
        Rendered HTML string
    """
    # Try to get custom template
    if template_name:
        try:
            template = ReportTemplate.objects.get(name=template_name, is_active=True)
            html = Template(template.html_template).render(Context(context))
            css = template.css_styles
            return f"<style>{css}</style>{html}"
        except ReportTemplate.DoesNotExist:
            pass

    # Use default template
    return render_to_string("reports/default_report.html", context)


def create_default_templates():
    """Create default report templates in database."""
    # This can be used for HTML templates if needed
    logger.info("Default templates creation skipped - using ReportLab PDF generation")
