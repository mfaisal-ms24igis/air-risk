"""
URL Configuration - AQI Monitor API
"""

from django.urls import path
from . import views

app_name = 'aqi_monitor'

urlpatterns = [
    # Risk map endpoints
    path('risk/tiles/', views.get_risk_tiles, name='risk-tiles'),
    path('risk/status/', views.get_data_status, name='data-status'),
    path('risk/check/', views.trigger_manual_check, name='manual-check'),
]
