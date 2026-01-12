"""
Quick verification script for backend implementation.

Run this after applying migrations to verify the setup.
"""

def verify_imports():
    """Test all critical imports."""
    print("=" * 60)
    print("IMPORT VERIFICATION")
    print("=" * 60)
    
    try:
        from users.permissions import IsPremiumUser
        print("✅ users.permissions - OK")
    except ImportError as e:
        print(f"❌ users.permissions - FAIL: {e}")
    
    try:
        from exposure.services.trend_analyzer import TrendAnalyzer
        print("✅ exposure.services.trend_analyzer - OK")
    except ImportError as e:
        print(f"❌ exposure.services.trend_analyzer - FAIL: {e}")
    
    try:
        from reports.services.ai_insights import generate_health_recommendations
        print("✅ reports.services.ai_insights - OK")
    except ImportError as e:
        print(f"❌ reports.services.ai_insights - FAIL: {e}")
    
    try:
        from reports.tasks import generate_location_report_async, cleanup_expired_reports_async
        print("✅ reports.tasks - OK")
    except ImportError as e:
        print(f"❌ reports.tasks - FAIL: {e}")
    
    try:
        from exposure.api.views import create_location_report
        print("✅ exposure.api.views - OK")
    except ImportError as e:
        print(f"❌ exposure.api.views - FAIL: {e}")


def verify_models():
    """Check model fields."""
    print("\n" + "=" * 60)
    print("MODEL VERIFICATION")
    print("=" * 60)
    
    from users.models import CustomUser
    from reports.models import Report
    
    # Check User model
    user_fields = [f.name for f in CustomUser._meta.get_fields()]
    
    if 'subscription_tier' in user_fields:
        print("✅ CustomUser.subscription_tier - OK")
    else:
        print("❌ CustomUser.subscription_tier - MISSING")
    
    if 'premium_until' in user_fields:
        print("✅ CustomUser.premium_until - OK")
    else:
        print("❌ CustomUser.premium_until - MISSING")
    
    # Check Report model
    report_fields = [f.name for f in Report._meta.get_fields()]
    
    if 'location' in report_fields:
        print("✅ Report.location - OK")
    else:
        print("❌ Report.location - MISSING")
    
    if 'radius_km' in report_fields:
        print("✅ Report.radius_km - OK")
    else:
        print("❌ Report.radius_km - MISSING")
    
    if 'include_ai_insights' in report_fields:
        print("✅ Report.include_ai_insights - OK")
    else:
        print("❌ Report.include_ai_insights - MISSING")


def verify_urls():
    """Check URL configuration."""
    print("\n" + "=" * 60)
    print("URL VERIFICATION")
    print("=" * 60)
    
    from django.urls import reverse
    
    try:
        url = reverse('exposure:create-location-report')
        print(f"✅ create-location-report - {url}")
    except Exception as e:
        print(f"❌ create-location-report - FAIL: {e}")
    
    try:
        url = reverse('exposure:list-user-reports')
        print(f"✅ list-user-reports - {url}")
    except Exception as e:
        print(f"❌ list-user-reports - FAIL: {e}")


def verify_lm_studio():
    """Test LM Studio connection."""
    print("\n" + "=" * 60)
    print("LM STUDIO VERIFICATION")
    print("=" * 60)
    
    from reports.services.ai_insights import test_lm_studio_connection
    
    result = test_lm_studio_connection()
    
    if result['status'] == 'connected':
        print(f"✅ LM Studio connected - {result['url']}")
        print(f"   Active model: {result.get('active_model', 'auto')}")
    else:
        print(f"⚠️  LM Studio offline - Using fallback mode")
        print(f"   Error: {result.get('error', 'Unknown')}")


def verify_constants():
    """Check pollutant layer configuration."""
    print("\n" + "=" * 60)
    print("CONSTANTS VERIFICATION")
    print("=" * 60)
    
    from air_quality.constants import POLLUTANT_LAYERS
    
    print(f"✅ POLLUTANT_LAYERS defined - {len(POLLUTANT_LAYERS)} layers")
    
    for layer in POLLUTANT_LAYERS:
        code = layer.get('code', 'UNKNOWN')
        name = layer.get('name', 'Unknown')
        print(f"   - {code}: {name}")


if __name__ == '__main__':
    import os
    import django
    
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'air_risk.settings.base')
    django.setup()
    
    print("\n🔍 BACKEND IMPLEMENTATION VERIFICATION")
    print("=" * 60)
    
    verify_imports()
    verify_models()
    verify_urls()
    verify_lm_studio()
    verify_constants()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Run migrations: python manage.py migrate users reports")
    print("2. Setup Django-Q: python manage.py setup_schedules")
    print("3. Start Django-Q: python manage.py qcluster")
    print("4. Start LM Studio: See LM_STUDIO_SETUP.md")
    print("5. Test endpoints: See BACKEND_IMPLEMENTATION_COMPLETE.md")
