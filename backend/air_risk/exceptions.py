"""
Custom exception handlers for standardized API error responses.
"""

import logging
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error responses.
    
    Returns error responses in the format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human-readable error message",
            "details": {...},  # Optional additional details
            "retry_after": 60  # For throttle errors
        }
    }
    """
    
    # Call REST framework's default exception handler first
    response = drf_exception_handler(exc, context)
    
    # If DRF didn't handle it, try custom handlers
    if response is None:
        response = handle_django_exceptions(exc, context)
    
    # If we have a response, format it consistently
    if response is not None:
        error_data = format_error_response(exc, response)
        response.data = error_data
        
        # Log error for monitoring
        log_exception(exc, context, response)
    
    return response


def handle_django_exceptions(exc, context):
    """Handle Django-specific exceptions."""
    from rest_framework.response import Response
    
    if isinstance(exc, Http404) or isinstance(exc, ObjectDoesNotExist):
        return Response(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "The requested resource was not found.",
                }
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    return None


def format_error_response(exc, response):
    """Format error response with consistent structure."""
    error_code = get_error_code(exc)
    error_message = get_error_message(exc)
    error_details = get_error_details(exc)
    
    error_data = {
        "error": {
            "code": error_code,
            "message": error_message,
        }
    }
    
    # Add details if available
    if error_details:
        error_data["error"]["details"] = error_details
    
    # Add retry_after for throttle errors
    if isinstance(exc, Throttled):
        error_data["error"]["retry_after"] = exc.wait
        
        # Add tier information if available
        request = getattr(exc, 'request', None)
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'FREE')
            error_data["error"]["current_tier"] = tier
            error_data["error"]["upgrade_available"] = tier in ['FREE', 'BASIC']
    
    return error_data


def get_error_code(exc):
    """Get standardized error code from exception."""
    if isinstance(exc, NotAuthenticated):
        return "AUTHENTICATION_REQUIRED"
    elif isinstance(exc, AuthenticationFailed):
        return "AUTHENTICATION_FAILED"
    elif isinstance(exc, PermissionDenied):
        return "PERMISSION_DENIED"
    elif isinstance(exc, Throttled):
        return "RATE_LIMIT_EXCEEDED"
    elif isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    elif isinstance(exc, Http404) or isinstance(exc, ObjectDoesNotExist):
        return "NOT_FOUND"
    elif hasattr(exc, 'default_code'):
        return exc.default_code.upper()
    else:
        return "SERVER_ERROR"


def get_error_message(exc):
    """Get human-readable error message."""
    if isinstance(exc, Throttled):
        wait = exc.wait
        if wait:
            minutes = int(wait / 60)
            seconds = int(wait % 60)
            if minutes > 0:
                return f"Rate limit exceeded. Please try again in {minutes} minute(s) and {seconds} second(s)."
            else:
                return f"Rate limit exceeded. Please try again in {seconds} second(s)."
        return "Rate limit exceeded. Please upgrade your subscription for higher limits."
    
    elif isinstance(exc, NotAuthenticated):
        return "Authentication credentials were not provided."
    
    elif isinstance(exc, AuthenticationFailed):
        return "Invalid authentication credentials."
    
    elif isinstance(exc, PermissionDenied):
        # Check if it's a tier-based restriction
        detail = str(exc.detail) if hasattr(exc, 'detail') else str(exc)
        if 'premium' in detail.lower() or 'subscription' in detail.lower():
            return "This feature requires a premium subscription. Please upgrade your account."
        return "You do not have permission to perform this action."
    
    elif hasattr(exc, 'detail'):
        return str(exc.detail)
    
    else:
        return str(exc)


def get_error_details(exc):
    """Extract additional error details if available."""
    details = None
    
    if isinstance(exc, ValidationError):
        # Format validation errors
        if hasattr(exc, 'detail'):
            details = exc.detail
    
    elif isinstance(exc, APIException) and hasattr(exc, 'detail'):
        # For DRF exceptions with structured details
        detail = exc.detail
        if isinstance(detail, dict) and 'detail' in detail:
            # Avoid redundant nesting
            pass
        elif isinstance(detail, dict):
            details = detail
    
    return details


def log_exception(exc, context, response):
    """Log exception for monitoring and debugging."""
    request = context.get('request')
    view = context.get('view')
    
    log_data = {
        'exception_type': type(exc).__name__,
        'status_code': response.status_code,
        'path': request.path if request else None,
        'method': request.method if request else None,
        'user': str(request.user) if request and hasattr(request, 'user') else None,
        'view': view.__class__.__name__ if view else None,
    }
    
    # Log at appropriate level
    if response.status_code >= 500:
        logger.error(f"Server error: {exc}", extra=log_data, exc_info=True)
    elif response.status_code == 429:  # Throttled
        logger.warning(f"Rate limit exceeded: {exc}", extra=log_data)
    elif response.status_code >= 400:
        logger.info(f"Client error: {exc}", extra=log_data)


class TierRestrictionError(PermissionDenied):
    """
    Exception for tier-based feature restrictions.
    
    Usage:
        if user.subscription_tier == 'FREE':
            raise TierRestrictionError(
                "This feature requires a Basic or Premium subscription."
            )
    """
    default_code = 'tier_restriction'
    default_detail = 'This feature is not available in your subscription tier.'


class QuotaExceededError(Throttled):
    """
    Exception for quota-based restrictions (different from rate limiting).
    
    Usage:
        if user.reports_generated_today >= user.daily_report_limit:
            raise QuotaExceededError(
                "Daily report generation quota exceeded. Upgrade for more reports."
            )
    """
    default_code = 'quota_exceeded'
    default_detail = 'You have exceeded your quota for this resource.'
