"""
Background Tasks - Django-Q
============================

Scheduled and on-demand tasks for the AQI Monitor service.

Tasks are executed by Django-Q cluster workers using PostgreSQL
ORM as the broker (no Redis required).

Configured in settings.Q_CLUSTER['schedule']
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from django.utils import timezone

from .models import DataFreshness
from .services import RiskMapService

logger = logging.getLogger(__name__)


def check_sentinel5p_updates() -> Dict[str, Any]:
    """
    Scheduled task: Check for new Sentinel-5P imagery.
    
    Runs every 6 hours to monitor data freshness.
    Updates DataFreshness model with latest availability.
    
    Returns:
        Task result dictionary
    """
    logger.info("Starting Sentinel-5P data freshness check")
    
    try:
        # Get or create freshness record
        freshness = DataFreshness.get_or_create_source(
            DataFreshness.DataSourceChoices.SENTINEL5P_NO2
        )
        
        freshness.mark_processing("Checking GEE for latest Sentinel-5P data")
        
        # Initialize service
        service = RiskMapService()
        
        # Check for latest data (last 30 days)
        result = service._get_latest_sentinel5p_no2(lookback_days=30)
        
        if result.success:
            latest_date = result.data['date']
            
            # Update freshness record
            freshness.update_availability(
                available_date=latest_date,
                success=True,
                image_count=1,
                lookback_days=30
            )
            
            logger.info(
                f"Sentinel-5P data available: {latest_date.isoformat()}"
            )
            
            return {
                'success': True,
                'latest_date': latest_date.isoformat(),
                'message': 'Data freshness check completed'
            }
        else:
            # Mark as failed
            freshness.mark_failed(f"No data available: {result.error}")
            
            logger.warning(f"Sentinel-5P check failed: {result.error}")
            
            return {
                'success': False,
                'error': result.error,
                'message': 'Data freshness check failed'
            }
            
    except Exception as e:
        logger.error(f"Sentinel-5P check error: {e}", exc_info=True)
        
        # Try to update freshness record
        try:
            freshness = DataFreshness.get_or_create_source(
                DataFreshness.DataSourceChoices.SENTINEL5P_NO2
            )
            freshness.mark_failed(str(e))
        except Exception:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'message': 'Task execution error'
        }


def manual_trigger_risk_calculation(
    region_bounds: list = None,
    hours_back: int = 24
) -> Dict[str, Any]:
    """
    On-demand task: Generate risk map for testing or manual refresh.
    
    Can be triggered via admin interface or API endpoint.
    
    Args:
        region_bounds: Optional [west, south, east, north]
        hours_back: Hours to look back for ground data
        
    Returns:
        Task result dictionary
    """
    logger.info(
        f"Manual risk calculation triggered (hours_back={hours_back})"
    )
    
    try:
        from .services import LocalDataService
        
        # Get local data
        local_service = LocalDataService()
        data_result = local_service.get_recent_pm25_geojson(
            hours=hours_back,
            region_bounds=region_bounds
        )
        
        if not data_result.success:
            return {
                'success': False,
                'error': data_result.error,
                'message': 'Failed to retrieve local data'
            }
        
        # Generate risk map
        risk_service = RiskMapService()
        risk_result = risk_service.generate_risk_map(
            openaq_geojson=data_result.data,
            region_bounds=region_bounds
        )
        
        if risk_result.success:
            # Update calculation status
            calc_status = DataFreshness.get_or_create_source(
                DataFreshness.DataSourceChoices.RISK_CALCULATION
            )
            calc_status.update_availability(
                available_date=timezone.now(),
                success=True,
                stations_used=risk_result.metadata.get('stations_count'),
                tile_url=risk_result.data['tile_url'][:100]  # Truncate for storage
            )
            
            logger.info("Risk calculation completed successfully")
            
            return {
                'success': True,
                'tile_url': risk_result.data['tile_url'],
                'metadata': risk_result.data['metadata'],
                'message': 'Risk map generated successfully'
            }
        else:
            return {
                'success': False,
                'error': risk_result.error,
                'message': 'Risk calculation failed'
            }
            
    except Exception as e:
        logger.error(f"Risk calculation error: {e}", exc_info=True)
        
        return {
            'success': False,
            'error': str(e),
            'message': 'Task execution error'
        }


def cleanup_old_freshness_records(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Maintenance task: Clean up old freshness check records.
    
    Args:
        days_to_keep: Number of days of history to retain
        
    Returns:
        Task result dictionary
    """
    logger.info(f"Cleaning up freshness records older than {days_to_keep} days")
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Note: We keep the latest record for each source
        # This task would delete historical snapshots if we were storing them
        
        logger.info("Cleanup task completed (placeholder)")
        
        return {
            'success': True,
            'message': 'Cleanup completed',
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}", exc_info=True)
        
        return {
            'success': False,
            'error': str(e),
            'message': 'Cleanup failed'
        }
