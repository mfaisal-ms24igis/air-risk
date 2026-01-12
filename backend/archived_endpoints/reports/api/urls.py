"""
URL configuration for reports API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ReportViewSet, ReportSubscriptionViewSet


router = DefaultRouter()
router.register(r"reports", ReportViewSet, basename="report")
router.register(r"subscriptions", ReportSubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("", include(router.urls)),
]
