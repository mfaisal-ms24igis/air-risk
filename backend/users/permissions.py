"""
Custom DRF permission classes for tiered access control.
"""

from rest_framework import permissions


class IsPremiumUser(permissions.BasePermission):
    """
    Permission class that only allows access to premium users.
    
    Usage:
        class MyPremiumView(APIView):
            permission_classes = [IsAuthenticated, IsPremiumUser]
    """

    message = "This feature requires a premium subscription."

    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user has active premium subscription
        return request.user.is_premium


class IsBasicOrPremiumUser(permissions.BasePermission):
    """
    Permission class that allows access to both basic and premium users.
    Just ensures user is authenticated.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
