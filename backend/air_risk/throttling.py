"""
Custom throttling classes for tiered user access.

Implements rate limiting based on user subscription tier:
- Free: 10 requests/minute
- Basic: 60 requests/minute  
- Premium: 600 requests/minute
- Admin: Unlimited
"""

from rest_framework.throttling import UserRateThrottle


class TieredUserRateThrottle(UserRateThrottle):
    """
    Rate throttle based on user subscription tier.
    
    Usage in views:
        from air_risk.throttling import TieredUserRateThrottle
        
        class MyView(APIView):
            throttle_classes = [TieredUserRateThrottle]
    """
    
    # Default rate limits per tier
    TIER_RATES = {
        'FREE': '10/minute',
        'BASIC': '60/minute',
        'PREMIUM': '600/minute',
        'ADMIN': None,  # Unlimited
    }
    
    def get_cache_key(self, request, view):
        """Override to include tier in cache key."""
        if request.user and request.user.is_authenticated:
            # Get user tier
            tier = getattr(request.user, 'subscription_tier', 'FREE')
            ident = request.user.pk
        else:
            # Anonymous users get FREE tier
            tier = 'FREE'
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': f'{self.scope}_{tier}',
            'ident': ident
        }
    
    def get_rate(self):
        """Override to return tier-specific rate."""
        # Get rate from request if available (set by allow_request)
        if hasattr(self, '_tier_rate'):
            return self._tier_rate
        return super().get_rate()
    
    def allow_request(self, request, view):
        """
        Implement the check to see if the request should be throttled.
        Returns True if request is allowed, False otherwise.
        """
        if request.user and request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'FREE')
            
            # Admin/staff get unlimited access
            if request.user.is_staff or tier == 'ADMIN':
                return True
            
            # Set rate for this tier
            self._tier_rate = self.TIER_RATES.get(tier, self.TIER_RATES['FREE'])
        else:
            # Anonymous users
            self._tier_rate = self.TIER_RATES['FREE']
        
        # Call parent to do actual throttle check
        return super().allow_request(request, view)
    
    def wait(self):
        """
        Returns the recommended next request time in seconds.
        """
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
        else:
            remaining_duration = self.duration
            
        available_requests = self.num_requests - len(self.history) + 1
        if available_requests <= 0:
            return None
            
        return remaining_duration / float(available_requests)


class FeatureAccessThrottle(UserRateThrottle):
    """
    Specialized throttle for premium-only features.
    
    - Free: Blocked (0 requests)
    - Basic: 10 requests/hour
    - Premium: 100 requests/hour
    - Admin: Unlimited
    
    Use for expensive operations like report generation, AI analysis, etc.
    """
    
    scope = 'premium_feature'
    
    TIER_RATES = {
        'FREE': '0/hour',  # Blocked
        'BASIC': '10/hour',
        'PREMIUM': '100/hour',
        'ADMIN': None,  # Unlimited
    }
    
    def allow_request(self, request, view):
        """Check if user tier allows access to premium features."""
        if not request.user or not request.user.is_authenticated:
            return False  # Anonymous users blocked
        
        tier = getattr(request.user, 'subscription_tier', 'FREE')
        
        # Admin/staff get unlimited
        if request.user.is_staff or tier == 'ADMIN':
            return True
        
        # Free tier users are blocked
        if tier == 'FREE':
            return False
        
        # Set rate for this tier
        self._tier_rate = self.TIER_RATES.get(tier, '0/hour')
        
        return super().allow_request(request, view)


class GeometryComplexityThrottle(UserRateThrottle):
    """
    Throttle for high-complexity GIS operations.
    
    - Free: 5 requests/hour
    - Basic: 30 requests/hour
    - Premium: 300 requests/hour
    - Admin: Unlimited
    
    Use for operations that return full geometry data (districts, provinces).
    """
    
    scope = 'geometry'
    
    TIER_RATES = {
        'FREE': '5/hour',
        'BASIC': '30/hour',
        'PREMIUM': '300/hour',
        'ADMIN': None,
    }
    
    def allow_request(self, request, view):
        """Check tier-based rate for geometry requests."""
        if request.user and request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'FREE')
            
            if request.user.is_staff or tier == 'ADMIN':
                return True
            
            self._tier_rate = self.TIER_RATES.get(tier, self.TIER_RATES['FREE'])
        else:
            self._tier_rate = self.TIER_RATES['FREE']
        
        return super().allow_request(request, view)
