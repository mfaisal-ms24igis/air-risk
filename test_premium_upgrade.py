#!/usr/bin/env python
"""
Test script to upgrade a user to premium and verify persistence.
"""

import os
import sys
import django
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
import json

User = get_user_model()

def test_premium_upgrade():
    """Test the premium upgrade functionality."""

    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )

    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")

    print(f"User before upgrade: tier={user.subscription_tier}, is_premium={user.is_premium}")

    # Create API client and authenticate
    client = APIClient()

    # First, login to get tokens
    login_response = client.post('/api/v1/auth/login/', {
        'username': 'testuser',
        'password': 'testpass123'
    })

    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.content.decode())
        return

    tokens = login_response.json()
    access_token = tokens['access']

    # Set authorization header
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    # Call premium upgrade endpoint
    upgrade_response = client.post('/api/v1/auth/upgrade-premium/')

    print(f"Upgrade response status: {upgrade_response.status_code}")
    if upgrade_response.status_code == 200:
        data = upgrade_response.json()
        print(f"Upgrade successful: {data['message']}")

        # Refresh user from database
        user.refresh_from_db()
        print(f"User after upgrade: tier={user.subscription_tier}, is_premium={user.is_premium}")

        # Test profile endpoint
        profile_response = client.get('/api/v1/auth/profile/')
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"Profile shows: tier={profile_data['subscription_tier']}, is_premium={profile_data['is_premium']}")
        else:
            print(f"Profile fetch failed: {profile_response.status_code}")
    else:
        print(f"Upgrade failed: {upgrade_response.content.decode()}")

if __name__ == '__main__':
    test_premium_upgrade()