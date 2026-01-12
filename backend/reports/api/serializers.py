"""
Serializers for reports API.
"""

from rest_framework import serializers

from ..models import Report, ReportSubscription, ReportTemplate


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ReportTemplate."""

    class Meta:
        model = ReportTemplate
        fields = [
            "id",
            "name",
            "description",
            "template_type",
            "html_template",
            "default_parameters",
            "is_active",
        ]
        read_only_fields = ["id"]


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report listings."""

    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "report_type",
            "report_type_display",
            "status",
            "status_display",
            "file_url",
            "created_at",
            "completed_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ReportSerializer(serializers.ModelSerializer):
    """Full serializer for Report details."""

    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    template = ReportTemplateSerializer(read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "title",
            "report_type",
            "report_type_display",
            "parameters",
            "status",
            "status_display",
            "file",
            "file_url",
            "template",
            "created_at",
            "started_at",
            "completed_at",
            "error_message",
        ]
        read_only_fields = [
            "id",
            "status",
            "file",
            "created_at",
            "started_at",
            "completed_at",
            "error_message",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reports."""

    template_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Report
        fields = [
            "title",
            "report_type",
            "parameters",
            "template_id",
        ]

    def validate_parameters(self, value):
        """Validate parameters based on report type."""
        report_type = self.initial_data.get("report_type")

        if report_type == "daily_aqi":
            # Validate date and pollutant
            if "pollutant" not in value:
                value["pollutant"] = "NO2"  # Default

        elif report_type == "exposure":
            # Date is optional, defaults to today
            pass

        elif report_type == "comparison":
            # Validate date range
            if "end_date" not in value:
                from datetime import date

                value["end_date"] = date.today().isoformat()

        return value

    def create(self, validated_data):
        """Create report and queue generation task."""
        template_id = validated_data.pop("template_id", None)

        # Set user from context
        validated_data["user"] = self.context["request"].user
        validated_data["status"] = "pending"

        # Set template if provided
        if template_id:
            try:
                validated_data["template"] = ReportTemplate.objects.get(id=template_id)
            except ReportTemplate.DoesNotExist:
                raise serializers.ValidationError({"template_id": "Template not found"})

        report = Report.objects.create(**validated_data)

        # Queue generation task
        from ..tasks import generate_report_task

        generate_report_task.delay(report.id)

        return report


class ReportSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for ReportSubscription details."""

    frequency_display = serializers.CharField(
        source="get_frequency_display", read_only=True
    )
    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )

    class Meta:
        model = ReportSubscription
        fields = [
            "id",
            "name",
            "report_type",
            "report_type_display",
            "frequency",
            "frequency_display",
            "parameters",
            "is_active",
            "last_generated",
            "created_at",
        ]
        read_only_fields = ["id", "last_generated", "created_at"]


class ReportSubscriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating subscriptions."""

    class Meta:
        model = ReportSubscription
        fields = [
            "name",
            "report_type",
            "frequency",
            "parameters",
            "is_active",
        ]

    def validate(self, data):
        """Validate subscription parameters."""
        report_type = data.get("report_type")
        parameters = data.get("parameters", {})

        # Set default parameters based on type
        if report_type == "daily_aqi":
            if "pollutant" not in parameters:
                parameters["pollutant"] = "NO2"
            data["parameters"] = parameters

        return data

    def create(self, validated_data):
        """Create subscription with user from context."""
        validated_data["user"] = self.context["request"].user
        return ReportSubscription.objects.create(**validated_data)
