"""
API Utility functions and standard response wrappers.

This module provides:
- Standardized API response wrapper
- Deprecation decorator for marking deprecated endpoints
- File hygiene utilities for processed data management
- Common response formatting helpers

All API responses follow the structure:
{
    "status": "success" | "error",
    "data": <GeoJSON FeatureCollection | Dict | List>,
    "message": <string>
}
"""

import functools
import logging
import os
import shutil
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar

from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# Type variable for generic function return
F = TypeVar('F', bound=Callable[..., Any])


# =============================================================================
# STANDARD RESPONSE WRAPPER
# =============================================================================

class APIResponse:
    """
    Standard API response wrapper.
    
    Ensures all API responses follow the structure:
    {
        "status": "success" | "error",
        "data": <payload>,
        "message": <string>
    }
    """
    
    @staticmethod
    def success(
        data: Union[Dict, List, None] = None,
        message: str = "Request successful",
        status_code: int = status.HTTP_200_OK,
        **kwargs
    ) -> Response:
        """
        Create a success response.
        
        Args:
            data: The response payload (dict, list, or None)
            message: Human-readable success message
            status_code: HTTP status code (default 200)
            **kwargs: Additional top-level fields to include
            
        Returns:
            Response: DRF Response object with standardized structure
        """
        response_data = {
            "status": "success",
            "data": data,
            "message": message,
            **kwargs
        }
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message: str = "An error occurred",
        data: Union[Dict, List, None] = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: Optional[str] = None,
        **kwargs
    ) -> Response:
        """
        Create an error response.
        
        Args:
            message: Human-readable error message
            data: Optional error details
            status_code: HTTP status code (default 400)
            error_code: Optional machine-readable error code
            **kwargs: Additional top-level fields to include
            
        Returns:
            Response: DRF Response object with standardized structure
        """
        response_data = {
            "status": "error",
            "data": data,
            "message": message,
        }
        if error_code:
            response_data["error_code"] = error_code
        response_data.update(kwargs)
        return Response(response_data, status=status_code)
    
    @staticmethod
    def geojson(
        features: List[Dict],
        message: str = "GeoJSON data retrieved",
        properties: Optional[Dict] = None,
        status_code: int = status.HTTP_200_OK
    ) -> Response:
        """
        Create a GeoJSON FeatureCollection response.
        
        Args:
            features: List of GeoJSON Feature objects
            message: Human-readable message
            properties: Optional collection-level properties
            status_code: HTTP status code
            
        Returns:
            Response: DRF Response with GeoJSON FeatureCollection
        """
        feature_collection = {
            "type": "FeatureCollection",
            "features": features,
        }
        if properties:
            feature_collection["properties"] = properties
            
        return Response({
            "status": "success",
            "data": feature_collection,
            "message": message,
        }, status=status_code)
    
    @staticmethod
    def paginated(
        data: List,
        total_count: int,
        page: int,
        page_size: int,
        message: str = "Data retrieved successfully"
    ) -> Response:
        """
        Create a paginated response.
        
        Args:
            data: List of items for current page
            total_count: Total number of items across all pages
            page: Current page number (1-indexed)
            page_size: Number of items per page
            message: Human-readable message
            
        Returns:
            Response: DRF Response with pagination metadata
        """
        total_pages = (total_count + page_size - 1) // page_size
        return Response({
            "status": "success",
            "data": data,
            "message": message,
            "pagination": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            }
        }, status=status.HTTP_200_OK)


# =============================================================================
# DEPRECATION DECORATOR
# =============================================================================

def deprecated(
    reason: str = "This endpoint is deprecated",
    removal_version: Optional[str] = None,
    alternative: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorator to mark API endpoints as deprecated.
    
    Adds deprecation warning header to response and logs usage.
    
    Args:
        reason: Explanation of why the endpoint is deprecated
        removal_version: Version when the endpoint will be removed
        alternative: Suggested alternative endpoint
        
    Returns:
        Decorated function that adds deprecation headers
        
    Example:
        @deprecated(
            reason="Use /api/v1/exposure/satellite/ instead",
            removal_version="2.0.0",
            alternative="/api/v1/exposure/satellite/"
        )
        def get(self, request):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Log deprecation warning
            warning_msg = f"Deprecated endpoint called: {func.__name__}. {reason}"
            if alternative:
                warning_msg += f" Use {alternative} instead."
            logger.warning(warning_msg)
            warnings.warn(warning_msg, DeprecationWarning, stacklevel=2)
            
            # Call the original function
            response = func(*args, **kwargs)
            
            # Add deprecation headers
            if hasattr(response, '__setitem__'):
                response['X-Deprecated'] = 'true'
                response['X-Deprecation-Reason'] = reason
                if removal_version:
                    response['X-Removal-Version'] = removal_version
                if alternative:
                    response['X-Alternative'] = alternative
            
            return response
        return wrapper  # type: ignore
    return decorator


# =============================================================================
# FILE HYGIENE UTILITIES
# =============================================================================

class FileHygiene:
    """
    Utility class for managing generated files.
    
    Automatically moves runtime-generated files (CSVs, SHPs, logs, etc.)
    to a processed_data folder for organization.
    """
    
    PROCESSED_DATA_DIR = "processed_data"
    
    # File patterns to track
    TRACKED_EXTENSIONS = {
        '.csv', '.shp', '.shx', '.dbf', '.prj', '.cpg',  # GIS files
        '.geojson', '.json',  # JSON files
        '.log', '.txt',  # Logs
        '.tif', '.tiff',  # Rasters
        '.zip', '.tar', '.gz',  # Archives
    }
    
    @classmethod
    def get_processed_dir(cls) -> Path:
        """
        Get the processed data directory path.
        
        Returns:
            Path: Absolute path to processed_data directory
        """
        base_dir = Path(settings.BASE_DIR)
        processed_dir = base_dir / cls.PROCESSED_DATA_DIR
        processed_dir.mkdir(parents=True, exist_ok=True)
        return processed_dir
    
    @classmethod
    def move_to_processed(
        cls,
        file_path: Union[str, Path],
        category: Optional[str] = None,
        preserve_original: bool = False
    ) -> Optional[Path]:
        """
        Move a file to the processed_data directory.
        
        Args:
            file_path: Path to the file to move
            category: Optional subdirectory category (e.g., 'exports', 'logs')
            preserve_original: If True, copy instead of move
            
        Returns:
            Path: New file path, or None if operation failed
        """
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return None
        
        # Determine destination directory
        dest_dir = cls.get_processed_dir()
        if category:
            dest_dir = dest_dir / category
            dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        dest_path = dest_dir / new_name
        
        try:
            if preserve_original:
                shutil.copy2(file_path, dest_path)
                logger.info(f"Copied {file_path} to {dest_path}")
            else:
                shutil.move(str(file_path), str(dest_path))
                logger.info(f"Moved {file_path} to {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to move/copy file: {e}")
            return None
    
    @classmethod
    def cleanup_loose_files(
        cls,
        directory: Union[str, Path],
        recursive: bool = False,
        dry_run: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find and optionally move loose files to processed_data.
        
        Args:
            directory: Directory to scan for loose files
            recursive: Whether to scan subdirectories
            dry_run: If True, only report files without moving
            
        Returns:
            List of dicts with file info and action taken
        """
        directory = Path(directory)
        results = []
        
        # Directories to skip
        skip_dirs = {
            'node_modules', '__pycache__', '.git', 'venv', 
            'env', '.venv', cls.PROCESSED_DATA_DIR
        }
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            # Skip directories and files in skip_dirs
            if file_path.is_dir():
                continue
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
            
            # Check if file matches tracked extensions
            if file_path.suffix.lower() in cls.TRACKED_EXTENSIONS:
                result = {
                    "file": str(file_path),
                    "size_bytes": file_path.stat().st_size,
                    "extension": file_path.suffix,
                    "action": "would_move" if dry_run else "moved",
                }
                
                if not dry_run:
                    new_path = cls.move_to_processed(file_path)
                    result["new_path"] = str(new_path) if new_path else None
                    result["action"] = "moved" if new_path else "failed"
                
                results.append(result)
        
        return results
    
    @classmethod
    def create_export_path(
        cls,
        filename: str,
        category: str = "exports"
    ) -> Path:
        """
        Create a path for a new export file in processed_data.
        
        Args:
            filename: Desired filename (timestamp will be added)
            category: Subdirectory category
            
        Returns:
            Path: Full path for the new file
        """
        dest_dir = cls.get_processed_dir() / category
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        
        return dest_dir / f"{stem}_{timestamp}{suffix}"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_population(value: Optional[int]) -> str:
    """
    Format population number for display.
    
    Args:
        value: Population count
        
    Returns:
        str: Formatted string (e.g., "1.2M", "500K")
    """
    if value is None:
        return "N/A"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def get_aqi_color(aqi: Optional[float]) -> str:
    """
    Get hex color code for an AQI value.
    
    Args:
        aqi: Air Quality Index value
        
    Returns:
        str: Hex color code
    """
    if aqi is None:
        return "#999999"
    if aqi <= 50:
        return "#00E400"  # Good - Green
    elif aqi <= 100:
        return "#FFFF00"  # Moderate - Yellow
    elif aqi <= 150:
        return "#FF7E00"  # USG - Orange
    elif aqi <= 200:
        return "#FF0000"  # Unhealthy - Red
    elif aqi <= 300:
        return "#8F3F97"  # Very Unhealthy - Purple
    else:
        return "#7E0023"  # Hazardous - Maroon


def get_aqi_category(aqi: Optional[float]) -> str:
    """
    Get AQI category name for a value.
    
    Args:
        aqi: Air Quality Index value
        
    Returns:
        str: Category name
    """
    if aqi is None:
        return "Unknown"
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"


def geometry_to_geojson(geom) -> Optional[Dict]:
    """
    Convert Django GEOSGeometry to GeoJSON dict.
    
    Args:
        geom: Django GEOSGeometry object
        
    Returns:
        Dict: GeoJSON geometry object or None
    """
    if geom is None:
        return None
    return {
        "type": geom.geom_type,
        "coordinates": geom.coords if geom.geom_type != "MultiPolygon" 
                      else list(geom.coords)
    }
