"""
Views for reports API.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse

from ..models import Report, ReportSubscription, ReportTemplate
from .serializers import (
    ReportSerializer,
    ReportListSerializer,
    ReportCreateSerializer,
    ReportSubscriptionSerializer,
    ReportSubscriptionCreateSerializer,
    ReportTemplateSerializer,
)


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reports.

    list:
        Get all reports for the current user.

    create:
        Create a new report and queue for generation.

    retrieve:
        Get report details including download URL.

    destroy:
        Delete a report and its file.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter reports to current user."""
        return (
            Report.objects.filter(user=self.request.user)
            .select_related("template")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ReportListSerializer
        elif self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    def perform_destroy(self, instance):
        """Delete file when report is deleted."""
        if instance.file:
            instance.file.delete()
        instance.delete()

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """
        Download the report PDF file.

        Returns:
            FileResponse with the PDF
        """
        report = self.get_object()

        if not report.file:
            return Response(
                {"error": "Report file not available"}, status=status.HTTP_404_NOT_FOUND
            )

        if report.status != "completed":
            return Response(
                {"error": "Report is not ready for download"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = FileResponse(report.file.open("rb"), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{report.file.name.split("/")[-1]}"'
        )
        return response

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """
        Regenerate a report.

        Returns:
            Updated report status
        """
        report = self.get_object()

        # Reset status
        report.status = "pending"
        report.error_message = ""
        report.started_at = None
        report.completed_at = None

        # Delete old file
        if report.file:
            report.file.delete()

        report.save()

        # Queue for regeneration
        from ..tasks import generate_report_task

        generate_report_task.delay(report.id)

        return Response(ReportSerializer(report, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """
        Get available report templates.

        Returns:
            List of active templates
        """
        templates = ReportTemplate.objects.filter(is_active=True)
        serializer = ReportTemplateSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get report statistics for the current user.

        Returns:
            Report counts by type and status
        """
        queryset = self.get_queryset()

        stats = {
            "total": queryset.count(),
            "by_status": {},
            "by_type": {},
        }

        # Count by status
        for status_choice in ["pending", "processing", "completed", "failed"]:
            stats["by_status"][status_choice] = queryset.filter(
                status=status_choice
            ).count()

        # Count by type
        for type_choice in ["daily_aqi", "exposure", "comparison", "custom"]:
            stats["by_type"][type_choice] = queryset.filter(
                report_type=type_choice
            ).count()

        return Response(stats)


class ReportSubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing report subscriptions.

    list:
        Get all subscriptions for the current user.

    create:
        Create a new subscription.

    update:
        Update subscription settings.

    destroy:
        Delete a subscription.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter subscriptions to current user."""
        return ReportSubscription.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ReportSubscriptionCreateSerializer
        return ReportSubscriptionSerializer

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        """
        Toggle subscription active status.

        Returns:
            Updated subscription
        """
        subscription = self.get_object()
        subscription.is_active = not subscription.is_active
        subscription.save()

        return Response(ReportSubscriptionSerializer(subscription).data)

    @action(detail=True, methods=["post"])
    def generate_now(self, request, pk=None):
        """
        Generate a report immediately for this subscription.

        Returns:
            Created report
        """
        subscription = self.get_object()

        # Create report
        report = Report.objects.create(
            user=subscription.user,
            report_type=subscription.report_type,
            title=f"{subscription.name} - Manual",
            parameters=subscription.parameters,
            status="pending",
        )

        # Queue generation
        from ..tasks import generate_report_task

        generate_report_task.delay(report.id)

        return Response(
            ReportSerializer(report, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
