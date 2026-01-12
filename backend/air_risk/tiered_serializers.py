"""
Tier-based serializers that adjust geometry complexity based on user subscription.

Free tier: Simplified geometry (tolerance=0.01 degrees ~1km)
Basic tier: Medium simplification (tolerance=0.005 degrees ~500m)
Premium tier: Full resolution geometry (no simplification)
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import GEOSGeometry


class TieredGeometryMixin:
    """
    Mixin to simplify geometry based on user subscription tier.
    
    Usage:
        class MySerializer(TieredGeometryMixin, GeoFeatureModelSerializer):
            class Meta:
                model = MyModel
                geo_field = "geometry"
    """
    
    # Simplification tolerances by tier (in degrees)
    SIMPLIFICATION_TOLERANCE = {
        'FREE': 0.01,      # ~1km simplification
        'BASIC': 0.005,    # ~500m simplification
        'PREMIUM': 0,      # No simplification
        'ADMIN': 0,        # No simplification
    }
    
    def to_representation(self, instance):
        """Override to simplify geometry based on user tier."""
        representation = super().to_representation(instance)
        
        # Get user tier from request context
        request = self.context.get('request')
        if not request:
            return representation
        
        user = request.user
        if not user or not user.is_authenticated:
            tier = 'FREE'
        else:
            tier = getattr(user, 'subscription_tier', 'FREE')
        
        # Get simplification tolerance
        tolerance = self.SIMPLIFICATION_TOLERANCE.get(tier, 0.01)
        
        # Simplify geometry if needed
        if tolerance > 0 and 'geometry' in representation:
            try:
                # Get the geometry field name from Meta
                geo_field = getattr(self.Meta, 'geo_field', 'geometry')
                geometry = getattr(instance, geo_field)
                
                if geometry:
                    # Simplify the geometry
                    simplified = geometry.simplify(
                        tolerance=tolerance,
                        preserve_topology=True
                    )
                    
                    # Update representation with simplified geometry
                    representation['geometry'] = simplified.geojson
            except Exception as e:
                # If simplification fails, return original
                pass
        
        return representation


class TieredDistrictSerializer(TieredGeometryMixin, GeoFeatureModelSerializer):
    """
    District serializer with tier-based geometry simplification.
    
    - Free: Simplified boundaries
    - Basic: Medium detail boundaries
    - Premium: Full resolution boundaries
    """
    
    from air_quality.models import District
    
    class Meta:
        model = District
        geo_field = "geometry"
        fields = [
            "id",
            "name",
            "province",
            "population",
            "area_km2",
        ]


class TieredProvinceSerializer(TieredGeometryMixin, GeoFeatureModelSerializer):
    """
    Province serializer with tier-based geometry simplification.
    
    - Free: Simplified boundaries
    - Basic: Medium detail boundaries
    - Premium: Full resolution boundaries
    """
    
    from air_quality.models import Province
    
    class Meta:
        model = Province
        geo_field = "geometry"
        fields = [
            "id",
            "name",
            "population",
            "area_km2",
        ]


class GeometryDetailField(serializers.Field):
    """
    Custom field that returns geometry with tier-based detail level.
    
    Usage:
        class MySerializer(serializers.ModelSerializer):
            geometry = GeometryDetailField()
            
            class Meta:
                model = MyModel
                fields = ['id', 'name', 'geometry']
    """
    
    def to_representation(self, value):
        """Convert geometry to GeoJSON with tier-based simplification."""
        if not value:
            return None
        
        # Get request from context
        request = self.context.get('request')
        if not request:
            # No request context, return full geometry
            return value.geojson
        
        # Get user tier
        user = request.user
        if not user or not user.is_authenticated:
            tier = 'FREE'
        else:
            tier = getattr(user, 'subscription_tier', 'FREE')
        
        # Simplification tolerances
        tolerances = {
            'FREE': 0.01,
            'BASIC': 0.005,
            'PREMIUM': 0,
            'ADMIN': 0,
        }
        
        tolerance = tolerances.get(tier, 0.01)
        
        if tolerance > 0:
            try:
                simplified = value.simplify(
                    tolerance=tolerance,
                    preserve_topology=True
                )
                return simplified.geojson
            except Exception:
                # Fallback to original on error
                return value.geojson
        
        return value.geojson


def get_tier_metadata(request):
    """
    Helper function to get tier metadata for responses.
    
    Returns dict with:
    - tier: User's subscription tier
    - geometry_detail: Description of geometry detail level
    - upgrade_available: Whether user can upgrade for better detail
    """
    if not request or not request.user or not request.user.is_authenticated:
        tier = 'FREE'
    else:
        tier = getattr(request.user, 'subscription_tier', 'FREE')
    
    detail_levels = {
        'FREE': 'simplified (~1km tolerance)',
        'BASIC': 'medium detail (~500m tolerance)',
        'PREMIUM': 'full resolution',
        'ADMIN': 'full resolution',
    }
    
    return {
        'tier': tier,
        'geometry_detail': detail_levels.get(tier, 'simplified'),
        'upgrade_available': tier in ['FREE', 'BASIC'],
    }


class TieredFeatureCollectionSerializer(serializers.Serializer):
    """
    Wrapper serializer for GeoJSON FeatureCollection with tier metadata.
    
    Usage:
        # In view
        districts = District.objects.all()
        serializer = TieredDistrictSerializer(
            districts,
            many=True,
            context={'request': request}
        )
        
        # Wrap in FeatureCollection
        return Response({
            'type': 'FeatureCollection',
            'features': serializer.data,
            'metadata': get_tier_metadata(request)
        })
    """
    
    type = serializers.CharField(default='FeatureCollection', read_only=True)
    features = serializers.ListField(child=serializers.DictField())
    metadata = serializers.DictField()
