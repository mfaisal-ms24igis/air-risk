"""
Django-Q task utilities for standardized task execution.

This module provides a unified interface for background tasks using Django-Q.
All tasks should be regular Python functions and scheduled via async_task().
"""

import logging
from typing import Any, Callable, Dict, Optional
from functools import wraps

from django_q.tasks import async_task, result as task_result
from django.conf import settings

logger = logging.getLogger(__name__)


def queue_task(
    func: Callable,
    *args,
    task_name: Optional[str] = None,
    hook: Optional[str] = None,
    timeout: Optional[int] = None,
    **kwargs
) -> str:
    """
    Queue a Django-Q task with standard error handling.
    
    Args:
        func: The function to execute
        *args: Positional arguments for the function
        task_name: Optional custom task name (defaults to function name)
        hook: Optional callback function path after task completes
        timeout: Optional timeout in seconds (default from Q_CLUSTER settings)
        **kwargs: Keyword arguments for the function
    
    Returns:
        Task ID (string)
    
    Example:
        from air_risk.task_utils import queue_task
        from air_quality.tasks import fetch_sentinel5p_data
        
        task_id = queue_task(
            fetch_sentinel5p_data,
            date='2025-12-15',
            task_name='sentinel5p_fetch',
            timeout=600
        )
    """
    task_name = task_name or func.__name__
    timeout = timeout or settings.Q_CLUSTER.get('timeout', 300)
    
    try:
        task_id = async_task(
            func,
            *args,
            task_name=task_name,
            hook=hook,
            timeout=timeout,
            **kwargs
        )
        logger.info(f"Queued task '{task_name}' with ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"Failed to queue task '{task_name}': {e}")
        raise


def get_task_result(task_id: str, wait: int = 0) -> Optional[Any]:
    """
    Get the result of a completed task.
    
    Args:
        task_id: The task ID returned from queue_task()
        wait: Milliseconds to wait for task completion (0 = don't wait)
    
    Returns:
        Task result or None if not completed
    """
    try:
        return task_result(task_id, wait=wait)
    except Exception as e:
        logger.error(f"Failed to get result for task {task_id}: {e}")
        return None


def retry_on_failure(max_retries: int = 3, delay: int = 300):
    """
    Decorator to add retry logic to Django-Q tasks.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay in seconds before retrying
    
    Example:
        @retry_on_failure(max_retries=3, delay=60)
        def my_task(param):
            # Task logic here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = kwargs.pop('_retry_attempt', 0)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Task {func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    # Schedule retry
                    from django_q.tasks import schedule
                    from datetime import timedelta
                    
                    schedule(
                        func,
                        *args,
                        **{**kwargs, '_retry_attempt': attempt + 1},
                        schedule_type='O',  # Once
                        next_run=timedelta(seconds=delay)
                    )
                else:
                    logger.error(
                        f"Task {func.__name__} failed after {max_retries} attempts: {e}"
                    )
                    raise
        
        return wrapper
    return decorator
