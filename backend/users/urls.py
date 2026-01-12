"""
URL configuration for users app.

Authentication Endpoints:
    POST /api/v1/auth/login/           - Get JWT access & refresh tokens
    POST /api/v1/auth/logout/          - Invalidate token
    POST /api/v1/auth/token/refresh/   - Refresh access token
    POST /api/v1/auth/register/        - Create new user account

Profile Endpoints (Requires Authentication):
    GET/PUT /api/v1/auth/profile/      - User profile
    PUT /api/v1/auth/profile/location/ - Update user location
    GET/PUT /api/v1/auth/profile/preferences/ - Notification preferences
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CustomTokenObtainPairView,
    UserRegistrationView,
    UserProfileView,
    UserLocationUpdateView,
    UserPreferencesView,
    PremiumUpgradeView,
    LogoutView,
)

app_name = "users"

urlpatterns = [
    # Authentication
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", UserRegistrationView.as_view(), name="register"),
    
    # Profile (requires auth)
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/location/", UserLocationUpdateView.as_view(), name="profile_location"),
    path("profile/preferences/", UserPreferencesView.as_view(), name="profile_preferences"),
    path("upgrade-premium/", PremiumUpgradeView.as_view(), name="upgrade_premium"),
]
