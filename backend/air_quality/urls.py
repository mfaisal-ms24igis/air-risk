"""
Air quality app URL configuration.
"""

from django.urls import path, include

from . import views

app_name = "air_quality"

urlpatterns = [
    path("api/", include("air_quality.api.urls")),
    path("api-tester/", views.api_tester, name="api_tester"),
]
