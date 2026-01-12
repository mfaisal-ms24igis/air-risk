"""
AQI Monitor App - Air Quality Intelligence Service
===================================================

This service module provides real-time air quality monitoring
by fusing local ground station data (OpenAQ) with cloud-based
satellite imagery (Google Earth Engine).

Architecture:
- models.py: Data models for stations, readings, status tracking
- services/: Business logic layer (GEE integration, data processing)
- tasks.py: Background jobs for data updates
- views.py: Thin API endpoints
- urls.py: API routing
"""
