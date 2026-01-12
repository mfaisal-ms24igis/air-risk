"""
Django management command to test premium upgrade functionality.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Test premium upgrade functionality'

    def handle(self, *args, **options):
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
            self.stdout.write(f"Created test user: {user.username}")

        self.stdout.write(f"User before upgrade: tier={user.subscription_tier}, is_premium={user.is_premium}")

        # Create API client and authenticate
        client = APIClient()

        # First, login to get tokens
        login_response = client.post('/api/v1/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })

        if login_response.status_code != 200:
            self.stderr.write(f"Login failed: {login_response.status_code}")
            self.stderr.write(login_response.content.decode())
            return

        tokens = login_response.json()
        access_token = tokens['access']

        # Set authorization header
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Call premium upgrade endpoint
        upgrade_response = client.post('/api/v1/auth/upgrade-premium/')

        self.stdout.write(f"Upgrade response status: {upgrade_response.status_code}")
        if upgrade_response.status_code == 200:
            data = upgrade_response.json()
            self.stdout.write(f"Upgrade successful: {data['message']}")

            # Refresh user from database
            user.refresh_from_db()
            self.stdout.write(f"User after upgrade: tier={user.subscription_tier}, is_premium={user.is_premium}")

            # Test profile endpoint
            profile_response = client.get('/api/v1/auth/profile/')
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                self.stdout.write(f"Profile shows: tier={profile_data['subscription_tier']}, is_premium={profile_data['is_premium']}")
            else:
                self.stderr.write(f"Profile fetch failed: {profile_response.status_code}")
        else:
            self.stderr.write(f"Upgrade failed: {upgrade_response.content.decode()}")