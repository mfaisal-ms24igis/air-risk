"""
Django-Q tasks for report generation.
"""

import logging
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Avg, Max, Min

from .models import Report, ReportSubscription
from .generators import generate_pdf_report
from .charts import (
    create_aqi_trend_chart,
    create_district_bar_chart,
    create_multi_pollutant_chart,
)

logger = logging.getLogger(__name__)


def generate_report_task(report_id: int):
    """
    Generate a single report (Django-Q task).

    Args:
        report_id: ID of the Report object
    """
    try:
        report = Report.objects.get(id=report_id)
        report.status = "processing"
        report.started_at = timezone.now()
        report.save()

        # These report types are deprecated - use generate_location_report_async instead
        # Generate the report
        if report.report_type == "daily_aqi":
            _generate_daily_aqi_report(report)
        elif report.report_type == "exposure":
            _generate_exposure_report(report)
        elif report.report_type == "comparison":
            _generate_comparison_report(report)
        elif report.report_type == "custom":
            _generate_custom_report(report)

        report.status = "completed"
        report.completed_at = timezone.now()
        report.save()

        logger.info(f"Report {report_id} generated successfully")

    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
    except Exception as exc:
        logger.exception(f"Error generating report {report_id}")
        report = Report.objects.filter(id=report_id).first()
        if report:
            report.status = "failed"
            report.error_message = str(exc)
            report.save()
        raise


def _generate_daily_aqi_report(report: Report):
    """Generate daily AQI report."""
    from exposure.models import DistrictExposure

    report_date = report.parameters.get("date", date.today().isoformat())
    pollutant = report.parameters.get("pollutant", "NO2")

    # Get exposure data
    exposures = DistrictExposure.objects.filter(
        date=report_date, pollutant=pollutant
    ).select_related("district")

    # Calculate summary
    if exposures.exists():
        summary = exposures.aggregate(
            avg_aqi=Avg("mean_aqi"), max_aqi=Max("max_aqi"), min_aqi=Min("mean_aqi")
        )
    else:
        summary = {"avg_aqi": 0, "max_aqi": 0, "min_aqi": 0}

    # Get historical trend (last 7 days)
    end_date = (
        date.fromisoformat(report_date) if isinstance(report_date, str) else report_date
    )
    start_date = end_date - timedelta(days=7)

    from exposure.models import ExposureTimeSeries

    trend_data = ExposureTimeSeries.objects.filter(
        region_type="country",
        pollutant=pollutant,
        timestamp__date__gte=start_date,
        timestamp__date__lte=end_date,
    ).order_by("timestamp")

    # Create trend chart
    if trend_data.exists():
        dates = [t.timestamp.date() for t in trend_data]
        values = [t.mean_aqi for t in trend_data]
        trend_chart = create_aqi_trend_chart(
            dates, values, pollutant, f"{pollutant} AQI - Last 7 Days"
        )
    else:
        trend_chart = None

    # Top 10 worst districts
    worst_districts = exposures.order_by("-mean_aqi")[:10]
    if worst_districts:
        district_names = [e.district.name for e in worst_districts]
        district_values = [e.mean_aqi for e in worst_districts]
        district_chart = create_district_bar_chart(
            district_names, district_values, "AQI", "Top 10 Most Polluted Districts"
        )
    else:
        district_chart = None

    # Context for potential template use (currently using generator directly)
    _ = {
        "title": f"Daily AQI Report - {pollutant}",
        "date": report_date,
        "pollutant": pollutant,
        "summary": summary,
        "exposures": list(exposures[:20]),
        "trend_chart": trend_chart,
        "district_chart": district_chart,
        "generated_at": timezone.now(),
    }

    # Generate PDF
    pdf_content = generator.generate_daily_report(
        date=end_date,
        pollutant=pollutant,
        summary=summary,
        districts=exposures,
        trend_chart=trend_chart,
    )

    # Save to report
    filename = f"daily_aqi_{pollutant}_{report_date}.pdf"
    report.file.save(filename, ContentFile(pdf_content))


def _generate_exposure_report(report: Report):
    """Generate exposure report."""
    from exposure.models import DistrictExposure, Hotspot

    report_date = report.parameters.get("date", date.today().isoformat())
    district_id = report.parameters.get("district_id")

    # Get exposure data
    filters = {"date": report_date}
    if district_id:
        filters["district_id"] = district_id

    exposures = DistrictExposure.objects.filter(**filters).select_related("district")

    # Get hotspots
    hotspots = Hotspot.objects.filter(
        detection_date=report_date, is_active=True
    ).select_related("district")

    # Calculate total exposed population
    total_exposed = sum(e.exposed_population for e in exposures)

    # Context for potential template use (currently using generator directly)
    _ = {
        "title": "Exposure Report",
        "date": report_date,
        "exposures": list(exposures[:50]),
        "hotspots": list(hotspots[:20]),
        "total_exposed": total_exposed,
        "generated_at": timezone.now(),
    }

    # Generate PDF
    pdf_content = generator.generate_exposure_report(
        date=date.fromisoformat(report_date)
        if isinstance(report_date, str)
        else report_date,
        exposures=exposures,
        hotspots=hotspots,
    )

    filename = f"exposure_{report_date}.pdf"
    report.file.save(filename, ContentFile(pdf_content))


def _generate_comparison_report(report: Report):
    """Generate multi-pollutant comparison report."""
    from exposure.models import ExposureTimeSeries

    start_date = report.parameters.get("start_date")
    end_date = report.parameters.get("end_date", date.today().isoformat())

    if not start_date:
        end = date.fromisoformat(end_date) if isinstance(end_date, str) else end_date
        start_date = (end - timedelta(days=30)).isoformat()

    pollutants = ["NO2", "SO2", "CO", "O3", "PM25"]

    # Get time series data for each pollutant
    data = {}
    dates = None

    for pollutant in pollutants:
        series = ExposureTimeSeries.objects.filter(
            region_type="country",
            pollutant=pollutant,
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        ).order_by("timestamp")

        if series.exists():
            if dates is None:
                dates = [s.timestamp.date() for s in series]
            data[pollutant] = [s.mean_aqi for s in series]

    # Create comparison chart
    if dates and data:
        comparison_chart = create_multi_pollutant_chart(
            dates, data, "Multi-Pollutant AQI Comparison"
        )
    else:
        comparison_chart = None

    # Context for potential template use (currently using generator directly)
    _ = {
        "title": "Multi-Pollutant Comparison Report",
        "start_date": start_date,
        "end_date": end_date,
        "data": data,
        "comparison_chart": comparison_chart,
        "generated_at": timezone.now(),
    }

    # Generate PDF
    pdf_content = generator.generate_comparison_report(
        start_date=date.fromisoformat(start_date)
        if isinstance(start_date, str)
        else start_date,
        end_date=date.fromisoformat(end_date)
        if isinstance(end_date, str)
        else end_date,
        data=data,
        chart=comparison_chart,
    )

    filename = f"comparison_{start_date}_{end_date}.pdf"
    report.file.save(filename, ContentFile(pdf_content))


def _generate_custom_report(report: Report):
    """Generate custom report from template."""
    template = report.template
    if not template:
        raise ValueError("Custom report requires a template")

    # Parse template and generate
    # This is a simplified implementation
    pdf_content = generator.generate_from_template(
        template=template,
        parameters=report.parameters,
    )

    filename = f"custom_{report.id}_{timezone.now().strftime('%Y%m%d')}.pdf"
    report.file.save(filename, ContentFile(pdf_content))


def generate_subscription_reports():
    """
    Generate reports for all due subscriptions.
    Runs daily via Celery Beat.
    """
    today = date.today()

    # Get active subscriptions
    subscriptions = ReportSubscription.objects.filter(is_active=True)

    for subscription in subscriptions:
        should_generate = False

        if subscription.frequency == "daily":
            should_generate = True
        elif subscription.frequency == "weekly":
            # Generate on Monday
            should_generate = today.weekday() == 0
        elif subscription.frequency == "monthly":
            # Generate on first day of month
            should_generate = today.day == 1

        if should_generate:
            generate_subscription_report.delay(subscription.id)


def generate_subscription_report(subscription_id: int):
    """
    Generate report for a subscription.

    Args:
        subscription_id: ID of the ReportSubscription
    """
    try:
        subscription = ReportSubscription.objects.get(id=subscription_id)

        # Create report record
        report = Report.objects.create(
            user=subscription.user,
            report_type=subscription.report_type,
            title=f"{subscription.name} - {date.today()}",
            parameters=subscription.parameters,
            status="pending",
        )

        # Generate the report
        generate_report_task.delay(report.id)

        # Update subscription
        subscription.last_generated = timezone.now()
        subscription.save()

        # Send email notification (if configured)
        if subscription.parameters.get("email_notification", True):
            send_report_email.delay(report.id, subscription.user.email)

        logger.info(f"Subscription report {subscription_id} queued for generation")

    except ReportSubscription.DoesNotExist:
        logger.error(f"Subscription {subscription_id} not found")
    except Exception as exc:
        logger.exception(f"Error generating subscription report {subscription_id}")
        raise


def send_report_email(report_id: int, email: str):
    """
    Send report via email.

    Args:
        report_id: ID of the Report
        email: Recipient email address
    """
    from django.core.mail import EmailMessage
    from django.conf import settings

    try:
        report = Report.objects.get(id=report_id)

        if report.status != "completed" or not report.file:
            logger.warning(f"Report {report_id} not ready for email")
            return

        email_message = EmailMessage(
            subject=f"Air Quality Report: {report.title}",
            body=f"""
Your air quality report has been generated.

Report Type: {report.get_report_type_display()}
Generated: {report.completed_at}

Please find the report attached.

---
Air Quality Exposure & Risk Intelligence Platform
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

        email_message.attach(
            report.file.name.split("/")[-1], report.file.read(), "application/pdf"
        )

        email_message.send()
        logger.info(f"Report {report_id} emailed to {email}")

    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found for email")
    except Exception:
        logger.exception(f"Error emailing report {report_id}")


def cleanup_old_reports(days: int = 30):
    """
    Delete reports older than specified days.

    Args:
        days: Number of days to retain reports
    """
    cutoff = timezone.now() - timedelta(days=days)

    old_reports = Report.objects.filter(created_at__lt=cutoff)
    count = old_reports.count()

    # Delete files
    for report in old_reports:
        if report.file:
            report.file.delete()

    # Delete records
    old_reports.delete()

    logger.info(f"Cleaned up {count} old reports")


# =============================================================================
# DJANGO-Q TASKS (New Async Task System)
# =============================================================================

def generate_location_report_async(report_id: int):
    """
    Django-Q task to generate location-based PDF report (PREMIUM feature).
    
    Args:
        report_id: Report model ID
    """
    from django.contrib.gis.geos import Point
    from exposure.services.trend_analyzer import TrendAnalyzer
    from reports.generators import generate_pdf_report
    
    try:
        report = Report.objects.get(id=report_id)
        report.status = "GENERATING"
        report.started_at = timezone.now()
        report.save(update_fields=["status", "started_at"])
        
        # Extract parameters
        lat = report.location.y
        lng = report.location.x
        radius_km = report.radius_km or 5.0
        
        # Run trend analysis
        analyzer = TrendAnalyzer(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            start_date=timezone.make_aware(
                timezone.datetime.combine(report.start_date, timezone.datetime.min.time())
            ),
            end_date=timezone.make_aware(
                timezone.datetime.combine(report.end_date, timezone.datetime.max.time())
            ),
        )
        
        trend_summary = analyzer.generate_summary()
        
        # Prepare report context
        context = {
            "report_type": "location",
            "title": f"Location-Based Air Quality Report",
            "user": report.user,
            "location": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "date_range": f"{report.start_date} to {report.end_date}",
            "trend_data": trend_summary,
            "include_ai": report.include_ai_insights,
            "generated_at": timezone.now(),
            "pollutants": ["PM25", "NO2", "O3"],
            "start_date": report.start_date,
            "end_date": report.end_date,
        }
        
        # Generate AI insights if requested
        if report.include_ai_insights:
            try:
                from reports.services.ai_insights import generate_health_recommendations
                ai_insights = generate_health_recommendations(
                    pollutant_data=trend_summary.get("ground_trends", {}),
                    location={"lat": lat, "lng": lng},
                )
                context["ai_insights"] = ai_insights
            except Exception as ai_error:
                logger.warning(f"AI insights failed for report {report_id}: {ai_error}")
                context["ai_insights"] = None
        
        # Generate PDF
        pdf_file_path = generate_pdf_report(report, context)
        
        # Read generated PDF
        with open(pdf_file_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        # Save to media folder
        file_path = f"reports/{report.user.id}/location_{report.id}.pdf"
        from django.core.files.storage import default_storage
        
        saved_path = default_storage.save(file_path, ContentFile(pdf_content))
        
        # Update report status
        report.status = "COMPLETED"
        report.completed_at = timezone.now()
        report.file_path = saved_path
        report.file_size = len(pdf_content)
        report.expires_at = timezone.now() + timedelta(days=30)
        report.save(update_fields=[
            "status", "completed_at", "file_path", "file_size", "expires_at"
        ])
        
        logger.info(f"Location report {report_id} generated: {saved_path}")
        
    except Report.DoesNotExist:
        logger.error(f"Report {report_id} not found")
    except Exception as e:
        logger.error(f"Location report failed for {report_id}: {e}")
        try:
            report = Report.objects.get(id=report_id)
            report.status = "FAILED"
            report.error_message = str(e)
            report.save(update_fields=["status", "error_message"])
        except:
            pass


def cleanup_expired_reports_async():
    """
    Django-Q scheduled task to delete expired report files.
    Run daily at 2 AM.
    """
    from django.core.files.storage import default_storage
    
    expired = Report.objects.filter(
        expires_at__lt=timezone.now(),
        file_path__isnull=False,
    ).exclude(file_path="")
    
    deleted_count = 0
    for report in expired:
        try:
            if default_storage.exists(report.file_path):
                default_storage.delete(report.file_path)
                logger.info(f"Deleted expired report: {report.file_path}")
                deleted_count += 1
            
            report.file_path = ""
            report.file_size = None
            report.save(update_fields=["file_path", "file_size"])
        except Exception as e:
            logger.error(f"Failed to delete report {report.id}: {e}")
    
    logger.info(f"Cleanup completed: {deleted_count} reports deleted")
    return deleted_count

