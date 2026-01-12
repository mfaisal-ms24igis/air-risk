"""
Management command to verify all infrastructure connections.

Usage:
    python manage.py verify_infrastructure
    python manage.py verify_infrastructure --verbose
    python manage.py verify_infrastructure --skip-external
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = "Verify all infrastructure connections (PostgreSQL, PostGIS, Redis, Celery, GeoServer, external APIs)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Show detailed output for each check",
        )
        parser.add_argument(
            "--skip-external",
            action="store_true",
            help="Skip external API checks (CDSE, OpenAQ)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        skip_external = options.get("skip_external", False)
        output_json = options.get("json", False)

        results = {
            "postgresql": {"status": "pending", "details": {}},
            "postgis": {"status": "pending", "details": {}},
            "redis": {"status": "pending", "details": {}},
            "celery": {"status": "pending", "details": {}},
            "geoserver": {"status": "pending", "details": {}},
        }

        if not skip_external:
            results["cdse"] = {"status": "pending", "details": {}}
            results["openaq"] = {"status": "pending", "details": {}}

        # 1. PostgreSQL Connection
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("🔍 INFRASTRUCTURE VERIFICATION"))
        self.stdout.write("=" * 60 + "\n")

        results["postgresql"] = self.check_postgresql(verbose)
        results["postgis"] = self.check_postgis(verbose)
        results["redis"] = self.check_redis(verbose)
        results["celery"] = self.check_celery(verbose)
        results["geoserver"] = self.check_geoserver(verbose)

        if not skip_external:
            results["cdse"] = self.check_cdse(verbose)
            results["openaq"] = self.check_openaq(verbose)

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.HTTP_INFO("📊 VERIFICATION SUMMARY"))
        self.stdout.write("=" * 60 + "\n")

        passed = 0
        failed = 0
        warnings = 0

        for service, result in results.items():
            status = result["status"]
            if status == "ok":
                self.stdout.write(
                    f"  ✅ {service.upper()}: {self.style.SUCCESS('PASSED')}"
                )
                passed += 1
            elif status == "warning":
                self.stdout.write(
                    f"  ⚠️  {service.upper()}: {self.style.WARNING('WARNING')}"
                )
                warnings += 1
            else:
                self.stdout.write(
                    f"  ❌ {service.upper()}: {self.style.ERROR('FAILED')}"
                )
                failed += 1

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(
            f"  Total: {passed} passed, {warnings} warnings, {failed} failed"
        )
        self.stdout.write("-" * 60 + "\n")

        if output_json:
            import json

            self.stdout.write("\nJSON Output:")
            self.stdout.write(json.dumps(results, indent=2, default=str))

        if failed > 0:
            raise CommandError(
                f"Infrastructure verification failed: {failed} service(s) down"
            )

        return None

    def check_postgresql(self, verbose: bool) -> dict:
        """Check PostgreSQL database connection."""
        self.stdout.write("\n📦 Checking PostgreSQL...")
        result = {"status": "error", "details": {}}

        try:
            with connection.cursor() as cursor:
                # Basic connectivity
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                result["details"]["version"] = version

                # Check database name
                cursor.execute("SELECT current_database();")
                db_name = cursor.fetchone()[0]
                result["details"]["database"] = db_name

                # Check connection info
                cursor.execute("SELECT inet_server_addr(), inet_server_port();")
                host, port = cursor.fetchone()
                result["details"]["host"] = str(host)
                result["details"]["port"] = port

                result["status"] = "ok"
                self.stdout.write(self.style.SUCCESS(f"   ✓ Connected to {db_name}"))

                if verbose:
                    self.stdout.write(f"   → Version: {version[:50]}...")
                    self.stdout.write(f"   → Host: {host}:{port}")

        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ Connection failed: {e}"))

        return result

    def check_postgis(self, verbose: bool) -> dict:
        """Check PostGIS extension is installed and working."""
        self.stdout.write("\n🌍 Checking PostGIS...")
        result = {"status": "error", "details": {}}

        try:
            with connection.cursor() as cursor:
                # Check PostGIS extension
                cursor.execute("SELECT PostGIS_Version();")
                postgis_version = cursor.fetchone()[0]
                result["details"]["postgis_version"] = postgis_version

                # Check GDAL version
                cursor.execute("SELECT PostGIS_GDAL_Version();")
                gdal_version = cursor.fetchone()[0]
                result["details"]["gdal_version"] = gdal_version

                # Test spatial query
                cursor.execute("SELECT ST_AsText(ST_Point(67.0, 30.0));")
                point = cursor.fetchone()[0]
                result["details"]["spatial_test"] = point

                # Check SRID availability (WGS84)
                cursor.execute(
                    "SELECT COUNT(*) FROM spatial_ref_sys WHERE srid = 4326;"
                )
                has_wgs84 = cursor.fetchone()[0] > 0
                result["details"]["has_wgs84"] = has_wgs84

                result["status"] = "ok"
                self.stdout.write(
                    self.style.SUCCESS(f"   ✓ PostGIS {postgis_version} installed")
                )

                if verbose:
                    self.stdout.write(f"   → GDAL Version: {gdal_version}")
                    self.stdout.write(f"   → Spatial Test: {point}")
                    self.stdout.write(
                        f"   → WGS84 (SRID 4326): {'Available' if has_wgs84 else 'Missing'}"
                    )

        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ PostGIS check failed: {e}"))

        return result

    def check_redis(self, verbose: bool) -> dict:
        """Check Redis connection for Celery broker."""
        self.stdout.write("\n🔴 Checking Redis...")
        result = {"status": "error", "details": {}}

        try:
            import redis
            from urllib.parse import urlparse

            broker_url = settings.CELERY_BROKER_URL
            parsed = urlparse(broker_url)
            result["details"]["host"] = parsed.hostname
            result["details"]["port"] = parsed.port
            result["details"]["db"] = parsed.path.strip("/") or "0"

            r = redis.Redis(
                host=parsed.hostname,
                port=parsed.port,
                db=int(parsed.path.strip("/") or 0),
                socket_timeout=5,
            )

            # Ping test
            pong = r.ping()
            result["details"]["ping"] = pong

            # Info
            info = r.info("server")
            result["details"]["redis_version"] = info.get("redis_version", "unknown")

            # Memory info
            memory_info = r.info("memory")
            used_memory_human = memory_info.get("used_memory_human", "unknown")
            result["details"]["used_memory"] = used_memory_human

            result["status"] = "ok"
            self.stdout.write(
                self.style.SUCCESS(
                    f"   ✓ Redis {result['details']['redis_version']} connected"
                )
            )

            if verbose:
                self.stdout.write(f"   → Host: {parsed.hostname}:{parsed.port}")
                self.stdout.write(f"   → Memory Used: {used_memory_human}")

        except ImportError:
            result["status"] = "error"
            result["details"]["error"] = "redis package not installed"
            self.stdout.write(self.style.ERROR("   ✗ redis package not installed"))
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ Redis check failed: {e}"))

        return result

    def check_celery(self, verbose: bool) -> dict:
        """Check Celery worker connectivity."""
        self.stdout.write("\n🥬 Checking Celery...")
        result = {"status": "error", "details": {}}

        try:
            from air_risk.celery import app as celery_app

            # Inspect workers
            inspect = celery_app.control.inspect(timeout=5)

            # Get active workers
            active = inspect.active()
            result["details"]["active_workers"] = list(active.keys()) if active else []

            # Get registered tasks
            registered = inspect.registered()
            if registered:
                all_tasks = []
                for worker, tasks in registered.items():
                    all_tasks.extend(tasks)
                result["details"]["registered_tasks"] = len(set(all_tasks))
            else:
                result["details"]["registered_tasks"] = 0

            # Get stats
            stats = inspect.stats()
            if stats:
                result["details"]["worker_count"] = len(stats)

            if active and len(active) > 0:
                result["status"] = "ok"
                worker_names = ", ".join(result["details"]["active_workers"][:3])
                self.stdout.write(
                    self.style.SUCCESS(f"   ✓ {len(active)} worker(s) online")
                )

                if verbose:
                    self.stdout.write(f"   → Workers: {worker_names}")
                    self.stdout.write(
                        f"   → Registered tasks: {result['details']['registered_tasks']}"
                    )
            else:
                result["status"] = "warning"
                result["details"]["warning"] = "No active workers found"
                self.stdout.write(
                    self.style.WARNING("   ⚠ No active Celery workers found")
                )
                self.stdout.write(
                    self.style.WARNING("   → Workers may not be running yet")
                )

        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ Celery check failed: {e}"))

        return result

    def check_geoserver(self, verbose: bool) -> dict:
        """Check GeoServer REST API connectivity."""
        self.stdout.write("\n🗺️  Checking GeoServer...")
        result = {"status": "error", "details": {}}

        try:
            import requests
            from requests.auth import HTTPBasicAuth

            base_url = settings.GEOSERVER_URL.rstrip("/")
            username = settings.GEOSERVER_ADMIN_USER
            password = settings.GEOSERVER_ADMIN_PASSWORD

            result["details"]["url"] = base_url

            # Test REST API - get workspaces
            rest_url = f"{base_url}/rest/workspaces.json"
            response = requests.get(
                rest_url,
                auth=HTTPBasicAuth(username, password),
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                workspaces = data.get("workspaces", {})
                if workspaces and "workspace" in workspaces:
                    ws_list = [ws["name"] for ws in workspaces["workspace"]]
                    result["details"]["workspaces"] = ws_list
                else:
                    result["details"]["workspaces"] = []

                result["status"] = "ok"
                self.stdout.write(
                    self.style.SUCCESS("   ✓ GeoServer REST API accessible")
                )

                if verbose:
                    self.stdout.write(f"   → URL: {base_url}")
                    self.stdout.write(
                        f"   → Workspaces: {', '.join(result['details']['workspaces']) or 'None'}"
                    )

            elif response.status_code == 401:
                result["status"] = "error"
                result["details"]["error"] = "Authentication failed"
                self.stdout.write(
                    self.style.ERROR("   ✗ GeoServer authentication failed")
                )
            else:
                result["status"] = "error"
                result["details"]["error"] = f"HTTP {response.status_code}"
                self.stdout.write(
                    self.style.ERROR(
                        f"   ✗ GeoServer returned HTTP {response.status_code}"
                    )
                )

        except requests.exceptions.ConnectionError:
            result["status"] = "warning"
            result["details"]["warning"] = (
                "Connection refused - GeoServer may not be running"
            )
            self.stdout.write(self.style.WARNING("   ⚠ Cannot connect to GeoServer"))
            self.stdout.write(
                self.style.WARNING("   → GeoServer may still be starting up")
            )
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ GeoServer check failed: {e}"))

        return result

    def check_cdse(self, verbose: bool) -> dict:
        """Check CDSE (Copernicus Data Space Ecosystem) API connectivity."""
        self.stdout.write("\n🛰️  Checking CDSE API...")
        result = {"status": "error", "details": {}}

        try:
            import requests

            client_id = getattr(settings, "CDSE_CLIENT_ID", "")
            client_secret = getattr(settings, "CDSE_CLIENT_SECRET", "")

            if not client_id or not client_secret:
                result["status"] = "warning"
                result["details"]["warning"] = "CDSE credentials not configured"
                self.stdout.write(
                    self.style.WARNING("   ⚠ CDSE credentials not configured")
                )
                return result

            # Token endpoint
            token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

            token_response = requests.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=15,
            )

            if token_response.status_code == 200:
                token_data = token_response.json()
                result["details"]["token_type"] = token_data.get(
                    "token_type", "unknown"
                )
                result["details"]["expires_in"] = token_data.get("expires_in", 0)
                result["status"] = "ok"
                self.stdout.write(
                    self.style.SUCCESS("   ✓ CDSE authentication successful")
                )

                if verbose:
                    self.stdout.write(
                        f"   → Token Type: {result['details']['token_type']}"
                    )
                    self.stdout.write(
                        f"   → Expires In: {result['details']['expires_in']}s"
                    )
            else:
                result["status"] = "error"
                result["details"]["error"] = f"HTTP {token_response.status_code}"
                self.stdout.write(
                    self.style.ERROR(
                        f"   ✗ CDSE auth failed: HTTP {token_response.status_code}"
                    )
                )

        except requests.exceptions.Timeout:
            result["status"] = "warning"
            result["details"]["warning"] = "Request timed out"
            self.stdout.write(self.style.WARNING("   ⚠ CDSE request timed out"))
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ CDSE check failed: {e}"))

        return result

    def check_openaq(self, verbose: bool) -> dict:
        """Check OpenAQ API v3 connectivity."""
        self.stdout.write("\n🌬️  Checking OpenAQ API...")
        result = {"status": "error", "details": {}}

        try:
            import requests

            api_key = getattr(settings, "OPENAQ_API_KEY", "")
            base_url = getattr(settings, "OPENAQ_BASE_URL", "https://api.openaq.org/v3")

            headers = {}
            if api_key:
                headers["X-API-Key"] = api_key

            # Test locations endpoint for Pakistan
            locations_url = f"{base_url}/locations"
            params = {"countries_id": 162, "limit": 1}  # Pakistan country ID

            response = requests.get(
                locations_url,
                headers=headers,
                params=params,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                result["details"]["api_version"] = "v3"
                result["details"]["results_count"] = len(data.get("results", []))

                # Get meta info
                meta = data.get("meta", {})
                result["details"]["total_found"] = meta.get("found", 0)

                result["status"] = "ok"
                self.stdout.write(self.style.SUCCESS("   ✓ OpenAQ API accessible"))

                if verbose:
                    self.stdout.write("   → API Version: v3")
                    self.stdout.write(
                        f"   → Pakistan stations found: {result['details']['total_found']}"
                    )

            elif response.status_code == 401:
                result["status"] = "warning"
                result["details"]["warning"] = "API key may be invalid or missing"
                self.stdout.write(
                    self.style.WARNING("   ⚠ OpenAQ returned 401 - check API key")
                )
            elif response.status_code == 429:
                result["status"] = "warning"
                result["details"]["warning"] = "Rate limited"
                self.stdout.write(
                    self.style.WARNING("   ⚠ OpenAQ rate limited - try again later")
                )
            else:
                result["status"] = "error"
                result["details"]["error"] = f"HTTP {response.status_code}"
                self.stdout.write(
                    self.style.ERROR(
                        f"   ✗ OpenAQ returned HTTP {response.status_code}"
                    )
                )

        except requests.exceptions.Timeout:
            result["status"] = "warning"
            result["details"]["warning"] = "Request timed out"
            self.stdout.write(self.style.WARNING("   ⚠ OpenAQ request timed out"))
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
            self.stdout.write(self.style.ERROR(f"   ✗ OpenAQ check failed: {e}"))

        return result
