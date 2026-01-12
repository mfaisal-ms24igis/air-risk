"""
Exposure app URL configuration.
"""

from django.urls import path, include

app_name = "exposure"

urlpatterns = [
    path("api/", include("exposure.api.urls")),
]
