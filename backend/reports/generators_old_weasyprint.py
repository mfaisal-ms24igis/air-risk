"""
Report generation utilities using ReportLab.
Replaces WeasyPrint to avoid GTK dependencies on Windows.
"""

import logging
from datetime import date, datetime
from pathlib import Path
from io import BytesIO

from django.conf import settings
from django.template import Template, Context
from django.template.loader import render_to_string

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

from .models import Report, ReportTemplate
from air_quality.models import District
from air_quality.constants import AQI_COLORS, AQI_CATEGORIES
from exposure.models import (
    DistrictExposure,
    ProvinceExposure,
    NationalExposure,
    Hotspot,
)

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

    # Title style
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

    # Heading2 custom
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

    # Heading3 custom
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

    # Body text
    styles.add(
        ParagraphStyle(
            name="CustomBody",
            parent=styles["BodyText"],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
        )
    )

    # Metric value (large numbers)
    styles.add(
        ParagraphStyle(
            name="MetricValue",
            parent=styles["Normal"],
            fontSize=28,
            textColor=colors.HexColor("#1a5276"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
    )

    # Metric label
    styles.add(
        ParagraphStyle(
            name="MetricLabel",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
        )
    )

    return styles


def get_report_context(
    report_type: str,
    pollutants: list,
    start_date: date,
    end_date: date,
    district: District = None,
    province: str = None,
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

    return context
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
                    "province": prov_exp.province,
                    "concentration_mean": prov_exp.concentration_mean,
                    "aqi_mean": prov_exp.aqi_mean,
                    "exposure_index": prov_exp.exposure_index,
                    "rank": prov_exp.rank,
                }

        context["province"] = province_data
        context["province_name"] = province

    # District details
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
                    "concentration_mean": dist_exp.concentration_mean,
                    "aqi_mean": dist_exp.aqi_mean,
                    "exposure_index": dist_exp.exposure_index,
                    "rank": dist_exp.rank,
                    "pop_good": dist_exp.pop_good,
                    "pop_moderate": dist_exp.pop_moderate,
                    "pop_usg": dist_exp.pop_usg,
                    "pop_unhealthy": dist_exp.pop_unhealthy,
                    "pop_very_unhealthy": dist_exp.pop_very_unhealthy,
                    "pop_hazardous": dist_exp.pop_hazardous,
                }

        context["district"] = district_data
        context["district_obj"] = district

    # Top rankings
    rankings = {}
    for pollutant in pollutants:
        top_districts = (
            DistrictExposure.objects.filter(
                pollutant=pollutant,
                date=end_date,
            )
            .select_related("district")
            .order_by("rank")[:10]
        )

        rankings[pollutant] = [
            {
                "rank": exp.rank,
                "name": exp.district.name,
                "province": exp.district.province,
                "aqi_mean": exp.aqi_mean,
                "exposure_index": exp.exposure_index,
            }
            for exp in top_districts
        ]

    context["rankings"] = rankings

    # Hotspots
    hotspots_data = {}
    for pollutant in pollutants:
        hotspots = Hotspot.objects.filter(
            pollutant=pollutant,
            date=end_date,
        ).order_by("-affected_population")[:5]

        hotspots_data[pollutant] = [
            {
                "severity": hs.severity,
                "aqi_mean": hs.aqi_mean,
                "affected_population": hs.affected_population,
                "persistence_days": hs.persistence_days,
            }
            for hs in hotspots
        ]

    context["hotspots"] = hotspots_data

    return context


def generate_html_report(context: dict, template_name: str = None) -> str:
    """
    Generate HTML report from template and context.

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


def generate_pdf_report(report: Report, context: dict = None) -> Path:
    """
    Generate PDF report using WeasyPrint.

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
        )

    context["report"] = report

    # Generate HTML
    html_content = generate_html_report(context)

    # Ensure output directory exists
    REPORTS_PATH.mkdir(parents=True, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report.report_type.lower()}_{report.id}_{timestamp}.pdf"
    output_path = REPORTS_PATH / filename

    # Generate PDF
    html = HTML(string=html_content, base_url=str(settings.BASE_DIR))

    # Get template settings
    try:
        template = ReportTemplate.objects.get(
            report_type=report.report_type, is_active=True
        )
        css = CSS(string=template.css_styles)
    except ReportTemplate.DoesNotExist:
        css = CSS(string=get_default_css())

    html.write_pdf(output_path, stylesheets=[css])

    logger.info(f"Generated PDF report: {output_path}")
    return output_path


def get_default_css() -> str:
    """Get default CSS for PDF reports."""
    return """
    @page {
        size: A4;
        margin: 2cm;
        @top-center {
            content: "Air Quality Report";
            font-size: 10pt;
            color: #666;
        }
        @bottom-center {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
    
    body {
        font-family: 'Helvetica', 'Arial', sans-serif;
        font-size: 11pt;
        line-height: 1.4;
        color: #333;
    }
    
    h1 {
        color: #1a5276;
        font-size: 24pt;
        margin-bottom: 20px;
        border-bottom: 2px solid #1a5276;
        padding-bottom: 10px;
    }
    
    h2 {
        color: #2874a6;
        font-size: 16pt;
        margin-top: 25px;
        margin-bottom: 15px;
    }
    
    h3 {
        color: #3498db;
        font-size: 13pt;
        margin-top: 20px;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    
    th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
    }
    
    th {
        background-color: #2874a6;
        color: white;
        font-weight: bold;
    }
    
    tr:nth-child(even) {
        background-color: #f8f9fa;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    
    .metric-value {
        font-size: 28pt;
        font-weight: bold;
    }
    
    .metric-label {
        font-size: 10pt;
        opacity: 0.9;
    }
    
    .aqi-good { background-color: #00e400; }
    .aqi-moderate { background-color: #ffff00; }
    .aqi-usg { background-color: #ff7e00; }
    .aqi-unhealthy { background-color: #ff0000; color: white; }
    .aqi-very-unhealthy { background-color: #8f3f97; color: white; }
    .aqi-hazardous { background-color: #7e0023; color: white; }
    
    .summary-box {
        background-color: #f8f9fa;
        border-left: 4px solid #2874a6;
        padding: 15px;
        margin: 15px 0;
    }
    
    .hotspot-severe {
        border-left: 4px solid #ff0000;
    }
    
    .hotspot-critical {
        border-left: 4px solid #7e0023;
    }
    """


def create_default_templates():
    """Create default report templates in database."""

    daily_template = """
    <h1>Daily Air Quality Report</h1>
    <p class="subtitle">{{ start_date|date:"F d, Y" }}</p>
    
    <h2>National Summary</h2>
    {% for pollutant, data in national.items %}
    <div class="summary-box">
        <h3>{{ pollutant }}</h3>
        <p><strong>Mean Concentration:</strong> {{ data.concentration_mean|floatformat:2 }} µg/m³</p>
        <p><strong>Mean AQI:</strong> {{ data.aqi_mean|floatformat:0 }}</p>
        <p><strong>Population at Risk:</strong> {{ data.pop_at_risk|intcomma }}</p>
        <p><strong>Active Hotspots:</strong> {{ data.n_hotspots }}</p>
    </div>
    {% endfor %}
    
    <h2>District Rankings (Most Polluted)</h2>
    {% for pollutant, districts in rankings.items %}
    <h3>{{ pollutant }}</h3>
    <table>
        <thead>
            <tr>
                <th>Rank</th>
                <th>District</th>
                <th>Province</th>
                <th>AQI</th>
                <th>Exposure Index</th>
            </tr>
        </thead>
        <tbody>
        {% for d in districts %}
            <tr>
                <td>{{ d.rank }}</td>
                <td>{{ d.name }}</td>
                <td>{{ d.province }}</td>
                <td>{{ d.aqi_mean|floatformat:0 }}</td>
                <td>{{ d.exposure_index|floatformat:1 }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% endfor %}
    
    {% if hotspots %}
    <h2>Pollution Hotspots</h2>
    {% for pollutant, spots in hotspots.items %}
    {% if spots %}
    <h3>{{ pollutant }}</h3>
    {% for spot in spots %}
    <div class="summary-box hotspot-{{ spot.severity|lower }}">
        <p><strong>Severity:</strong> {{ spot.severity }}</p>
        <p><strong>AQI:</strong> {{ spot.aqi_mean }}</p>
        <p><strong>Affected Population:</strong> {{ spot.affected_population|intcomma }}</p>
        <p><strong>Persistence:</strong> {{ spot.persistence_days }} days</p>
    </div>
    {% endfor %}
    {% endif %}
    {% endfor %}
    {% endif %}
    
    <div class="footer">
        <p>Generated on {{ generated_at|date:"F d, Y H:i" }}</p>
    </div>
    """

    ReportTemplate.objects.update_or_create(
        name="daily_default",
        defaults={
            "report_type": "DAILY",
            "html_template": daily_template,
            "css_styles": get_default_css(),
            "is_active": True,
        },
    )

    logger.info("Created default report templates")
