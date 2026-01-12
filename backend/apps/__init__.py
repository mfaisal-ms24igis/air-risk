"""
Apps Package - Service-Oriented Modules
========================================

This package contains all business logic modules organized as
independent, scalable Django applications.

Each app follows the service-oriented pattern:
- models.py: Data models only
- services/: Business logic layer
- tasks.py: Background jobs (Django-Q)
- views.py: Thin HTTP handlers
- urls.py: API routing
"""
