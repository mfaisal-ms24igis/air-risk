"""
Views for user authentication and profile management.
"""

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    UserLocationUpdateSerializer,
    UserPreferencesSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Authenticate user and obtain JWT tokens.
    
    Returns access and refresh tokens along with user info.
    
    **Request Body:**
    - `email`: User email address
    - `password`: User password
    
    **Response:**
    - `access`: JWT access token (short-lived)
    - `refresh`: JWT refresh token (long-lived)
    - `user`: User profile data
    """

    serializer_class = CustomTokenObtainPairSerializer


class UserRegistrationView(generics.CreateAPIView):
    """
    Register a new user account.
    
    Creates a new user and returns JWT tokens for immediate login.
    
    **Request Body:**
    - `email`: Valid email address
    - `password`: Strong password
    - `first_name`: User's first name
    - `last_name`: User's last name (optional)
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "user": UserProfileSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get or update current user's profile.
    
    Requires authentication via JWT token.
    
    **GET:** Returns user profile data
    **PUT/PATCH:** Update profile fields
    """

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserLocationUpdateView(APIView):
    """
    Update user's home location for local air quality alerts.
    
    **POST:** Set home location (latitude, longitude)
    **DELETE:** Remove home location
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserLocationUpdateSerializer(
            instance=request.user, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": "Location updated successfully",
                "location": {
                    "longitude": user.home_location.x,
                    "latitude": user.home_location.y,
                },
            }
        )

    def delete(self, request):
        request.user.home_location = None
        request.user.save(update_fields=["home_location", "updated_at"])

        return Response({"message": "Location removed successfully"})


class UserPreferencesView(generics.UpdateAPIView):
    """
    Update user notification preferences.
    
    Configure alert thresholds, tracked pollutants, and notification settings.
    """

    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)  # Allow partial updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {
                "message": "Preferences updated successfully",
                "preferences": serializer.data,
            }
        )


class PremiumUpgradeView(APIView):
    """
    Upgrade user to premium subscription.

    **POST:** Upgrade to premium (sets subscription_tier to PREMIUM and premium_until to 1 year from now)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user

        # Check if already premium
        if user.is_premium:
            return Response(
                {"message": "User is already premium", "user": UserProfileSerializer(user).data},
                status=status.HTTP_200_OK
            )

        # Upgrade to premium
        from django.utils import timezone
        premium_until = timezone.now() + timezone.timedelta(days=365)  # 1 year

        user.subscription_tier = user.SubscriptionTier.PREMIUM
        user.premium_until = premium_until
        user.save(update_fields=['subscription_tier', 'premium_until', 'updated_at'])

        return Response(
            {
                "message": "Successfully upgraded to premium!",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK
        )


class LogoutView(APIView):
    """
    Logout user by invalidating their refresh token.
    
    **Request Body:**
    - `refresh`: Refresh token to blacklist
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response(
                {"message": "Successfully logged out"}, status=status.HTTP_200_OK
            )
        except Exception:
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
