"""
URL configuration for reports app.
"""

from django.urls import path, include

from .api.urls import urlpatterns as api_urls


app_name = "reports"

urlpatterns = [
    path("api/", include(api_urls)),
]
