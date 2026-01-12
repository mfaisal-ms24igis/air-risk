"""
Base Service Classes
====================

Provides abstract base classes for all service modules to ensure
consistent patterns, error handling, and logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from datetime import datetime

# Type variable for generic service results
T = TypeVar('T')


class ServiceResult(Generic[T]):
    """
    Standardized service operation result.
    
    Provides consistent structure for service method returns,
    including success state, data, errors, and metadata.
    """
    
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def success_result(cls, data: T, **metadata) -> 'ServiceResult[T]':
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)
    
    @classmethod
    def error_result(cls, error: str, **metadata) -> 'ServiceResult[T]':
        """Create an error result."""
        return cls(success=False, error=error, metadata=metadata)


class BaseService(ABC):
    """
    Abstract base class for all service modules.
    
    Enforces:
    - Proper logging setup
    - Error handling patterns
    - Service initialization
    - Clean separation from views/models
    """
    
    def __init__(self):
        """Initialize service with logger."""
        self.logger = logging.getLogger(self.__class__.__module__)
        self._initialize()
    
    def _initialize(self) -> None:
        """
        Optional initialization hook for subclasses.
        Override to set up service-specific resources.
        """
        pass
    
    def _handle_error(
        self,
        operation: str,
        exception: Exception,
        **context
    ) -> ServiceResult:
        """
        Standardized error handling for service operations.
        
        Args:
            operation: Name of the operation that failed
            exception: The caught exception
            **context: Additional context for logging
            
        Returns:
            ServiceResult with error information
        """
        error_msg = f"{operation} failed: {str(exception)}"
        self.logger.error(
            error_msg,
            exc_info=True,
            extra={'operation': operation, **context}
        )
        
        return ServiceResult.error_result(
            error=error_msg,
            operation=operation,
            exception_type=type(exception).__name__,
            **context
        )
    
    def _log_operation(
        self,
        operation: str,
        level: str = 'info',
        **context
    ) -> None:
        """
        Log service operation with context.
        
        Args:
            operation: Description of the operation
            level: Log level (info, warning, error)
            **context: Additional context data
        """
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(
            f"Service operation: {operation}",
            extra={'operation': operation, **context}
        )


class GeoSpatialServiceMixin:
    """
    Mixin providing common geospatial utilities.
    
    Use this for services that work with geographic data,
    GeoJSON, coordinate transformations, etc.
    """
    
    @staticmethod
    def validate_geojson(geojson: Dict[str, Any]) -> bool:
        """
        Validate basic GeoJSON structure.
        
        Args:
            geojson: GeoJSON dictionary
            
        Returns:
            True if valid structure
        """
        required_keys = {'type', 'features'}
        if not all(key in geojson for key in required_keys):
            return False
        
        if geojson['type'] != 'FeatureCollection':
            return False
        
        if not isinstance(geojson['features'], list):
            return False
        
        return True
    
    @staticmethod
    def extract_coordinates(feature: Dict[str, Any]) -> Optional[tuple]:
        """
        Extract coordinates from a GeoJSON feature.
        
        Args:
            feature: GeoJSON feature dictionary
            
        Returns:
            Tuple of (longitude, latitude) or None
        """
        try:
            geometry = feature.get('geometry', {})
            if geometry.get('type') == 'Point':
                coords = geometry.get('coordinates', [])
                if len(coords) >= 2:
                    return (coords[0], coords[1])
        except (KeyError, IndexError, TypeError):
            pass
        return None


class CachingServiceMixin:
    """
    Mixin providing caching utilities for service operations.
    
    Useful for services that fetch expensive data that can be
    cached (e.g., satellite imagery, model results).
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, Any] = {}
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        import hashlib
        import json
        
        cache_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Retrieve cached value."""
        return self._cache.get(key)
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Store value in cache."""
        self._cache[key] = value
    
    def _clear_cache(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class TimeoutMixin:
    """
    Mixin for handling operation timeouts.
    
    Particularly useful for external API calls (GEE, OpenAQ, etc.)
    """
    
    DEFAULT_TIMEOUT: int = 30  # seconds
    
    def _with_timeout(
        self,
        func,
        timeout: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout.
        
        Args:
            func: Function to execute
            timeout: Timeout in seconds (uses DEFAULT_TIMEOUT if None)
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            TimeoutError: If operation exceeds timeout
        """
        import signal
        
        timeout = timeout or self.DEFAULT_TIMEOUT
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {timeout}s")
        
        # Note: signal.alarm only works on Unix systems
        # For Windows, consider using threading.Timer or concurrent.futures
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = func(*args, **kwargs)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        
        return result
