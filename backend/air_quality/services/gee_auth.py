"""
Google Earth Engine Authentication Service.

Handles GEE authentication using service account credentials with singleton pattern
to avoid multiple authentications within the same process.
"""

import os
import json
import logging
from typing import Optional
from pathlib import Path
from functools import lru_cache

import ee

logger = logging.getLogger(__name__)


class GEEAuthError(Exception):
    """Raised when GEE authentication fails."""
    pass


class GEEAuth:
    """
    Google Earth Engine authentication manager.
    
    Supports:
    - Service account authentication (production)
    - Interactive OAuth (development)
    - Environment variable credentials
    
    Usage:
        gee_auth = GEEAuth()
        gee_auth.initialize()
        
        # Now use ee.* functions
        image = ee.Image('COPERNICUS/S5P/OFFL/L3_NO2/...')
    """
    
    _instance: Optional['GEEAuth'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'GEEAuth':
        """Singleton pattern to prevent multiple authentications."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize GEE auth manager."""
        if hasattr(self, '_init_done'):
            return
        self._init_done = True
        self._credentials = None
        self._project_id = None
    
    @property
    def is_initialized(self) -> bool:
        """Check if GEE is initialized."""
        return self._initialized
    
    @property
    def project_id(self) -> Optional[str]:
        """Get the GEE project ID."""
        return self._project_id
    
    def _find_service_account_key(self) -> Optional[Path]:
        """
        Find the service account key file.
        
        Searches in order:
        1. GEE_SERVICE_ACCOUNT_KEY env variable
        2. gee-service-account.json in project root
        3. .gee-credentials.json in project root
        """
        # Check environment variable first
        env_path = os.environ.get('GEE_SERVICE_ACCOUNT_KEY')
        if env_path and Path(env_path).exists():
            return Path(env_path)
        
        # Check common locations
        base_dir = Path(__file__).resolve().parent.parent.parent
        candidates = [
            base_dir / 'gee-service-account.json',
            base_dir / '.gee-credentials.json',
            base_dir / 'credentials' / 'gee-service-account.json',
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        return None
    
    def initialize(
        self,
        service_account_key: Optional[str] = None,
        project_id: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Initialize Google Earth Engine.
        
        Args:
            service_account_key: Path to service account JSON file (optional).
            project_id: GEE project ID (optional, read from key file).
            force: Force re-initialization even if already initialized.
            
        Returns:
            True if initialization successful.
            
        Raises:
            GEEAuthError: If authentication fails.
        """
        if self._initialized and not force:
            logger.debug("GEE already initialized")
            return True
        
        try:
            # Try service account authentication
            key_path = service_account_key or self._find_service_account_key()
            
            if key_path:
                return self._init_service_account(Path(key_path), project_id)
            
            # Fall back to interactive authentication
            logger.warning("No service account found, trying interactive auth")
            return self._init_interactive()
            
        except Exception as e:
            logger.error(f"GEE initialization failed: {e}")
            raise GEEAuthError(f"Failed to initialize GEE: {e}") from e
    
    def _init_service_account(
        self, 
        key_path: Path, 
        project_id: Optional[str] = None
    ) -> bool:
        """Initialize with service account credentials."""
        logger.info(f"Initializing GEE with service account: {key_path}")
        
        # Read the service account key
        with open(key_path) as f:
            key_data = json.load(f)
        
        # Extract project ID if not provided
        self._project_id = project_id or key_data.get('project_id')
        
        # Create credentials
        self._credentials = ee.ServiceAccountCredentials(
            email=key_data['client_email'],
            key_file=str(key_path)
        )
        
        # Initialize Earth Engine
        ee.Initialize(
            credentials=self._credentials,
            project=self._project_id,
            opt_url='https://earthengine-highvolume.googleapis.com'
        )
        
        self._initialized = True
        logger.info(f"GEE initialized successfully (project: {self._project_id})")
        return True
    
    def _init_interactive(self) -> bool:
        """Initialize with interactive OAuth flow."""
        logger.info("Initializing GEE with interactive authentication")
        
        # Try to use existing credentials
        try:
            ee.Initialize()
            self._initialized = True
            logger.info("GEE initialized with existing credentials")
            return True
        except ee.EEException:
            pass
        
        # Trigger authentication flow
        ee.Authenticate()
        ee.Initialize()
        self._initialized = True
        logger.info("GEE initialized after authentication")
        return True
    
    def test_connection(self) -> dict:
        """
        Test the GEE connection.
        
        Returns:
            Dictionary with connection test results.
        """
        if not self._initialized:
            self.initialize()
        
        results = {
            'connected': False,
            'project_id': self._project_id,
            'test_image': None,
            'error': None,
        }
        
        try:
            # Try to get info about the S5P collection (more reliable than specific image)
            collection = ee.ImageCollection('COPERNICUS/S5P/OFFL/L3_NO2')
            # Get count of images in collection
            count = collection.size().getInfo()
            results['connected'] = True
            results['test_image'] = f"S5P NO2 collection ({count} images)"
        except Exception as e:
            results['error'] = str(e)
            logger.error(f"GEE connection test failed: {e}")
        
        return results


# Singleton accessor
@lru_cache(maxsize=1)
def get_gee_auth() -> GEEAuth:
    """Get the GEE authentication singleton."""
    return GEEAuth()


def initialize_gee(**kwargs) -> bool:
    """
    Convenience function to initialize GEE.
    
    Args:
        **kwargs: Arguments passed to GEEAuth.initialize()
        
    Returns:
        True if initialization successful.
    """
    auth = get_gee_auth()
    return auth.initialize(**kwargs)


def ensure_gee_initialized(func):
    """
    Decorator to ensure GEE is initialized before function execution.
    
    Usage:
        @ensure_gee_initialized
        def get_satellite_data(...):
            image = ee.Image(...)
            ...
    """
    def wrapper(*args, **kwargs):
        gee_auth = get_gee_auth()
        if not gee_auth.is_initialized:
            gee_auth.initialize()
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
