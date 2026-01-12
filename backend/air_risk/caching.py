"""
Caching utilities for API endpoints.

Provides tier-based caching with different TTLs based on subscription level.
"""

from functools import wraps
from django.core.cache import cache
from django.utils.encoding import force_str
from rest_framework.response import Response
import hashlib
import json


class TieredCache:
    """
    Tier-based cache with different TTLs for different subscription levels.
    
    Free tier: 5 minute cache
    Basic tier: 2 minute cache
    Premium tier: 1 minute cache (fresher data)
    """
    
    TTL_BY_TIER = {
        'FREE': 300,      # 5 minutes
        'BASIC': 120,     # 2 minutes
        'PREMIUM': 60,    # 1 minute
        'ADMIN': 30,      # 30 seconds
    }
    
    @staticmethod
    def get_cache_key(request, view_name, **kwargs):
        """
        Generate cache key based on request parameters.
        
        Args:
            request: Django request object
            view_name: Name of the view/endpoint
            **kwargs: Additional parameters to include in key
        
        Returns:
            Cache key string
        """
        # Get user tier
        if request.user and request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'FREE')
            user_id = request.user.id
        else:
            tier = 'ANON'
            user_id = 'anon'
        
        # Build key components
        key_parts = [
            view_name,
            tier,
            str(user_id),
        ]
        
        # Add query parameters
        query_params = sorted(request.query_params.items())
        if query_params:
            query_str = json.dumps(query_params, sort_keys=True)
            query_hash = hashlib.md5(query_str.encode()).hexdigest()[:8]
            key_parts.append(query_hash)
        
        # Add additional kwargs
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        
        cache_key = ':'.join(key_parts)
        return cache_key
    
    @staticmethod
    def get_ttl(request):
        """Get TTL based on user tier."""
        if request.user and request.user.is_authenticated:
            tier = getattr(request.user, 'subscription_tier', 'FREE')
        else:
            tier = 'FREE'
        
        return TieredCache.TTL_BY_TIER.get(tier, 300)


def cached_api_view(view_name=None, cache_timeout=None, tier_based=True):
    """
    Decorator to cache API view responses with tier-based TTL.
    
    Usage:
        @cached_api_view('districts_list')
        def my_view(request):
            # Expensive operation
            return Response(data)
    
    Args:
        view_name: Name for cache key (defaults to function name)
        cache_timeout: Fixed timeout in seconds (overrides tier-based)
        tier_based: Use tier-based TTL (default: True)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Determine cache key
            cache_view_name = view_name or func.__name__
            cache_key = TieredCache.get_cache_key(
                request,
                cache_view_name,
                **kwargs
            )
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                # Add cache header
                response = Response(cached_response)
                response['X-Cache'] = 'HIT'
                response['X-Cache-Key'] = cache_key[:50]  # Truncate for header
                return response
            
            # Call the actual view
            response = func(request, *args, **kwargs)
            
            # Cache successful responses
            if response.status_code == 200:
                # Determine TTL
                if cache_timeout is not None:
                    ttl = cache_timeout
                elif tier_based:
                    ttl = TieredCache.get_ttl(request)
                else:
                    ttl = 300  # Default 5 minutes
                
                # Cache the response data
                cache.set(cache_key, response.data, ttl)
                
                # Add cache headers
                response['X-Cache'] = 'MISS'
                response['X-Cache-TTL'] = str(ttl)
            
            return response
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern.
    
    Note: This requires Redis with key pattern matching.
    For LocMemCache, this will only clear the default cache.
    
    Args:
        pattern: Cache key pattern (e.g., 'districts_list:*')
    """
    try:
        from django.core.cache.backends.redis import RedisCache
        
        if isinstance(cache, RedisCache):
            # Redis supports pattern-based deletion
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
        else:
            # Fallback: clear all cache
            cache.clear()
    except Exception:
        # If anything fails, just clear all
        cache.clear()


def cache_page_tiered(view_func):
    """
    Simple page-level caching with tier-based TTL.
    
    Usage:
        @cache_page_tiered
        @api_view(['GET'])
        def my_view(request):
            return Response(data)
    """
    return cached_api_view(tier_based=True)(view_func)
