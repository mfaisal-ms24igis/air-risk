"""
Async report generation views using Django-Q.

Provides endpoints for:
- Creating report generation tasks
- Polling task status
- Downloading completed reports
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_q.tasks import async_task, result as task_result
from django_q.models import Task as DjangoQTask

from reports.models import Report
from reports.tasks import generate_report_task
from air_risk.throttling import FeatureAccessThrottle
from air_risk.exceptions import TierRestrictionError, QuotaExceededError


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@throttle_classes([FeatureAccessThrottle])
def create_report_async(request):
    """
    Create a report generation task.
    
    POST /api/v1/reports/generate/
    
    Request body:
    {
        "report_type": "daily_aqi|exposure|comparison|custom",
        "parameters": {
            "date": "2025-12-15",
            "pollutant": "NO2",
            ...
        }
    }
    
    Response:
    {
        "task_id": "uuid-string",
        "report_id": 123,
        "status": "pending",
        "message": "Report generation started"
    }
    """
    
    # Check tier restrictions
    tier = getattr(request.user, 'subscription_tier', 'FREE')
    if tier == 'FREE':
        raise TierRestrictionError(
            "Report generation requires a Basic or Premium subscription."
        )
    
    # Check daily quota (example - adjust based on your requirements)
    daily_limit = {
        'BASIC': 5,
        'PREMIUM': 50,
        'ADMIN': 999999,
    }.get(tier, 0)
    
    from django.utils import timezone
    from datetime import datetime, timedelta
    
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    reports_today = Report.objects.filter(
        user=request.user,
        created_at__gte=today_start
    ).count()
    
    if reports_today >= daily_limit:
        raise QuotaExceededError(
            f"Daily report generation limit ({daily_limit}) exceeded. "
            f"Upgrade your subscription or wait until tomorrow."
        )
    
    # Extract parameters
    report_type = request.data.get('report_type', 'LOCATION')
    parameters = request.data.get('parameters', {})
    
    # Handle location-based parameters
    from django.contrib.gis.geos import Point
    import datetime
    
    lat = request.data.get('lat')
    lng = request.data.get('lng')
    radius_km = request.data.get('radius_km', 5.0)
    start_date_str = request.data.get('start_date')
    end_date_str = request.data.get('end_date')
    
    if not all([lat, lng, start_date_str, end_date_str]):
        return Response({
            'error': 'Missing required fields: lat, lng, start_date, end_date'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Parse dates
    try:
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError as e:
        return Response({
            'error': f'Invalid date format: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create report record with location
    report = Report.objects.create(
        user=request.user,
        report_type=report_type,
        title=f'Location Report {lat:.4f}, {lng:.4f}',
        location=Point(lng, lat, srid=4326),
        radius_km=float(radius_km),
        start_date=start_date,
        end_date=end_date,
        include_ai_insights=True,
        pollutants=['PM25', 'NO2', 'O3'],
        status='PENDING'
    )
    
    # Queue the location-based task
    from reports.tasks import generate_location_report_async
    task_id = async_task(
        generate_location_report_async,
        report.id,
        task_name=f'location_report_{report.id}',
        timeout=600  # 10 minute timeout
    )
    
    # Store task_id in report for tracking
    report.task_id = task_id
    report.save(update_fields=['task_id'])
    
    return Response({
        'task_id': task_id,
        'report_id': report.id,
        'status': 'pending',
        'message': 'Report generation started',
        'poll_url': f'/api/v1/reports/{report.id}/status/'
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_report_status(request, report_id):
    """
    Get the status of a report generation task.
    
    GET /api/v1/reports/{report_id}/status/
    
    Response:
    {
        "report_id": 123,
        "status": "pending|processing|completed|failed",
        "progress": 75,  // Optional percentage
        "message": "Generating charts...",
        "download_url": "/api/v1/reports/123/download/",  // Only when completed
        "error": "Error message"  // Only when failed
    }
    """
    
    # Get report and verify ownership
    report = get_object_or_404(
        Report,
        id=report_id,
        user=request.user
    )
    
    response_data = {
        'report_id': report.id,
        'status': report.status,
        'created_at': report.created_at,
    }
    
    # Add started/completed timestamps if available
    if report.started_at:
        response_data['started_at'] = report.started_at
    if report.completed_at:
        response_data['completed_at'] = report.completed_at
    
    # Check Django-Q task status if task_id exists
    if report.task_id:
        try:
            # Try to get task result (non-blocking)
            task_result_data = task_result(report.task_id, wait=0)
            
            # Get task object for more details
            try:
                django_task = DjangoQTask.objects.get(id=report.task_id)
                response_data['task_info'] = {
                    'started': django_task.started,
                    'stopped': django_task.stopped,
                    'success': django_task.success,
                }
            except DjangoQTask.DoesNotExist:
                pass
            
        except Exception:
            # Task not found or still running
            pass
    
    # Add download URL if completed
    if report.status == 'completed' and report.file:
        response_data['download_url'] = f'/api/v1/reports/{report.id}/download/'
        response_data['file_size'] = report.file.size
    
    # Add error message if failed
    if report.status == 'failed' and report.error_message:
        response_data['error'] = report.error_message
    
    # Add estimated time remaining for pending/processing
    if report.status in ['pending', 'processing']:
        response_data['message'] = (
            'Waiting in queue...' if report.status == 'pending'
            else 'Generating report...'
        )
        response_data['estimated_seconds'] = 60  # Rough estimate
    
    return Response(response_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_user_reports(request):
    """
    List all reports for the current user.
    
    GET /api/v1/reports/
    
    Query parameters:
    - status: Filter by status (pending|processing|completed|failed)
    - limit: Number of results (default: 20, max: 100)
    - offset: Pagination offset
    
    Response:
    {
        "count": 50,
        "next": "/api/v1/reports/?offset=20",
        "previous": null,
        "results": [...]
    }
    """
    
    queryset = Report.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Pagination
    limit = min(int(request.query_params.get('limit', 20)), 100)
    offset = int(request.query_params.get('offset', 0))
    
    total_count = queryset.count()
    reports = queryset[offset:offset + limit]
    
    # Build response
    results = []
    for report in reports:
        result = {
            'id': report.id,
            'report_type': report.report_type,
            'status': report.status,
            'created_at': report.created_at,
            'parameters': report.parameters,
        }
        
        if report.status == 'completed' and report.file:
            result['download_url'] = f'/api/v1/reports/{report.id}/download/'
            result['file_size'] = report.file.size
        
        if report.status == 'failed':
            result['error'] = report.error_message
        
        results.append(result)
    
    # Build pagination links
    next_url = None
    previous_url = None
    
    if offset + limit < total_count:
        next_url = f'/api/v1/reports/?offset={offset + limit}&limit={limit}'
        if status_filter:
            next_url += f'&status={status_filter}'
    
    if offset > 0:
        previous_offset = max(0, offset - limit)
        previous_url = f'/api/v1/reports/?offset={previous_offset}&limit={limit}'
        if status_filter:
            previous_url += f'&status={status_filter}'
    
    return Response({
        'count': total_count,
        'next': next_url,
        'previous': previous_url,
        'results': results
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_report(request, report_id):
    """
    Delete a report and its file.
    
    DELETE /api/v1/reports/{report_id}/
    """
    
    report = get_object_or_404(
        Report,
        id=report_id,
        user=request.user
    )
    
    # Delete file if exists
    if report.file:
        report.file.delete()
    
    report.delete()
    
    return Response(
        {'message': 'Report deleted successfully'},
        status=status.HTTP_204_NO_CONTENT
    )
