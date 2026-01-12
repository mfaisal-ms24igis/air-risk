"""
URL routes for async report generation API.
"""

from django.urls import path
from .async_views import (
    create_report_async,
    get_report_status,
    list_user_reports,
    delete_report,
)

app_name = 'reports_async'

urlpatterns = [
    # Async report generation
    path('generate/', create_report_async, name='generate_async'),
    path('', list_user_reports, name='list'),
    path('<int:report_id>/status/', get_report_status, name='status'),
    path('<int:report_id>/', delete_report, name='delete'),
]
