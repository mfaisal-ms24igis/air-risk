"""
CDSE OAuth2 Authentication Service
Handles token creation, caching, and refresh for Copernicus Data Space Ecosystem.
"""

import time
import requests
from django.conf import settings
from django.core.cache import cache

CDSE = settings.CDSE

TOKEN_CACHE_KEY = "cdse_oauth_access_token"
TOKEN_EXPIRY_CACHE_KEY = "cdse_oauth_expires_at"


def get_cdse_token():
    """
    Returns a valid OAuth2 token. Auto-refreshes if expired.
    """
    token = cache.get(TOKEN_CACHE_KEY)
    expiry = cache.get(TOKEN_EXPIRY_CACHE_KEY)

    # Token still valid?
    if token and expiry and (expiry - time.time() > 30):
        return token

    # Refresh token
    data = {
        "grant_type": "password",
        "client_id": CDSE["CLIENT_ID"],
        "username": CDSE["USERNAME"],
        "password": CDSE["PASSWORD"],
    }

    r = requests.post(CDSE["TOKEN_URL"], data=data, timeout=20)
    r.raise_for_status()
    js = r.json()

    token = js["access_token"]
    expires_in = js.get("expires_in", 3600)
    expiry_time = time.time() + expires_in

    # Cache new token
    cache.set(TOKEN_CACHE_KEY, token, timeout=expires_in - 20)
    cache.set(TOKEN_EXPIRY_CACHE_KEY, expiry_time, timeout=expires_in - 20)

    return token