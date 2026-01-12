"""
Serializers for user authentication and profile management.
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.gis.geos import Point

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user info in response.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user info to response
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "has_location": self.user.has_location,
            "tier": self.user.tier,
            "is_premium": self.user.is_premium,
        }

        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        ]
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile viewing and updating.
    """

    location = serializers.SerializerMethodField()
    preferred_district_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "subscription_tier",
            "is_premium",
            "premium_until",
            "location",
            "preferred_district",
            "preferred_district_name",
            "email_verified",
            "email_preferences",
            "report_frequency",
            "tracked_pollutants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "email_verified",
            "subscription_tier",
            "is_premium",
            "premium_until",
            "created_at",
            "updated_at",
        ]

    def get_location(self, obj):
        if obj.home_location:
            return {
                "longitude": obj.home_location.x,
                "latitude": obj.home_location.y,
            }
        return None

    def get_preferred_district_name(self, obj):
        if obj.preferred_district:
            return obj.preferred_district.name
        return None


class UserLocationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user location.
    """

    longitude = serializers.FloatField(
        min_value=-180, max_value=180, help_text="Longitude in decimal degrees"
    )
    latitude = serializers.FloatField(
        min_value=-90, max_value=90, help_text="Latitude in decimal degrees"
    )

    def validate(self, attrs):
        # Validate coordinates are within Pakistan's approximate bounds
        lon, lat = attrs["longitude"], attrs["latitude"]
        if not (60.87 <= lon <= 77.84 and 23.69 <= lat <= 37.08):
            raise serializers.ValidationError(
                "Location must be within Pakistan boundaries."
            )
        return attrs

    def update(self, instance, validated_data):
        instance.home_location = Point(
            validated_data["longitude"], validated_data["latitude"], srid=4326
        )
        instance.save(update_fields=["home_location", "updated_at"])
        return instance


class UserPreferencesSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user preferences.
    """

    class Meta:
        model = User
        fields = [
            "preferred_district",
            "email_preferences",
            "report_frequency",
            "tracked_pollutants",
        ]

    def validate_tracked_pollutants(self, value):
        valid_pollutants = {"NO2", "SO2", "PM25", "CO", "O3"}
        for pollutant in value:
            if pollutant not in valid_pollutants:
                raise serializers.ValidationError(
                    f"Invalid pollutant: {pollutant}. "
                    f"Valid options are: {', '.join(valid_pollutants)}"
                )
        return value
