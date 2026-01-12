"""
Base service classes for air quality services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseService(ABC):
    """
    Base class for all services.
    Provides common functionality like logging and error handling.
    """

    def __init__(self, logger_name: str = None):
        self.logger = logging.getLogger(logger_name or self.__class__.__name__)

    def log_info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)

    def log_error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)

    def log_warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)


class APIClient(BaseService):
    """
    Base class for API clients.
    """

    def __init__(self, base_url: str, logger_name: str = None):
        super().__init__(logger_name)
        self.base_url = base_url
        self.session = None

    @abstractmethod
    def _setup_session(self):
        """Setup the requests session."""
        pass

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request with error handling."""
        try:
            response = self.session.request(method, f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            self.log_error(f"Request failed: {e}")
            raise


class DataProcessor(BaseService):
    """
    Base class for data processing services.
    """

    def __init__(self, logger_name: str = None):
        super().__init__(logger_name)

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process the data."""
        pass