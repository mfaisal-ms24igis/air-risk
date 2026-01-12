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

from .models import Report, ReportTemplate
from air_quality.models import District
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
            name="CustomBody",
            parent=styles["BodyText"],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY,
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


def _add_location_content(story, context, styles):
    """Add location-based report content with AI insights."""
    # Location information
    location = context.get("location", {})
    if location:
        story.append(Paragraph("Location Analysis", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        location_data = [
            ["Latitude", f"{location.get('lat', 'N/A'):.4f}"],
            ["Longitude", f"{location.get('lng', 'N/A'):.4f}"],
            ["Analysis Radius", f"{context.get('radius_km', 'N/A')} km"],
        ]

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

            trend_table_data = [["Pollutant", "Mean", "Max", "95th Percentile"]]
            for pollutant, data in ground_trends.items():
                trend_table_data.append([
                    pollutant,
                    f"{data.get('mean', 'N/A'):.1f}",
                    f"{data.get('max', 'N/A'):.1f}",
                    f"{data.get('p95', 'N/A'):.1f}",
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

    # AI Insights (Premium feature)
    ai_insights = context.get("ai_insights")
    if ai_insights and context.get("include_ai", False):
        story.append(PageBreak())
        story.append(Paragraph("🤖 AI-Powered Health Insights", styles["CustomHeading2"]))
        story.append(Spacer(1, 0.3 * cm))

        # Summary
        if ai_insights.get("summary"):
            story.append(Paragraph("Summary", styles["CustomHeading3"]))
            story.append(Paragraph(ai_insights["summary"], styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Recommendations
        recommendations = ai_insights.get("recommendations", [])
        if recommendations:
            story.append(Paragraph("Health Recommendations", styles["CustomHeading3"]))
            for rec in recommendations:
                story.append(Paragraph(f"• {rec}", styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Risk level
        risk_level = ai_insights.get("risk_level")
        if risk_level:
            story.append(Paragraph(f"Risk Level: {risk_level.upper()}", styles["CustomHeading3"]))
            story.append(Spacer(1, 0.2 * cm))

        # Sensitive groups
        sensitive_groups = ai_insights.get("sensitive_groups", [])
        if sensitive_groups:
            story.append(Paragraph("Particularly Affected Groups:", styles["CustomBody"]))
            groups_text = ", ".join(sensitive_groups)
            story.append(Paragraph(groups_text, styles["CustomBody"]))
            story.append(Spacer(1, 0.3 * cm))

        # Model info
        model = ai_insights.get("model", "AI Assistant")
        story.append(Paragraph(f"Analysis generated by {model}", styles["CustomBody"]))
        story.append(Spacer(1, 0.5 * cm))

    # Fallback to basic content if no AI
    else:
        _add_daily_content(story, context, styles)


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
