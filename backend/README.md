# Air Quality Exposure & Risk Intelligence Platform

A Django-based backend platform for air quality monitoring, bias correction, and population exposure assessment for Pakistan.

## Features

- **Satellite Data Integration**: Automated ingestion of Sentinel-5P data (NO2, SO2, CO, O3, Aerosol Index) via CDSE API
- **Ground Station Data**: OpenAQ integration for ground truth measurements
- **Bias Correction**: Geographically Weighted Regression (GWR) with linear fallback for satellite-ground calibration
- **Population Exposure**: Pixel-level exposure calculation using WorldPop 1km population grid
- **Time-enabled WMS**: GeoServer ImageMosaic stores with TIME dimension for historical analysis
- **PDF Reporting**: Automated report generation with charts and subscriptions
- **REST API**: Complete API with JWT authentication

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Future)                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                         Django REST API                          │
│  ┌─────────┐ ┌───────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ │
│  │  Users  │ │Air Quality│ │Correction│ │Exposure │ │ Reports │ │
│  └─────────┘ └───────────┘ └──────────┘ └─────────┘ └─────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                          Data Layer                              │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ PostgreSQL  │  │    Redis      │  │      GeoServer         │ │
│  │  + PostGIS  │  │ (Celery/Cache)│  │  (ImageMosaic + TIME)  │ │
│  └─────────────┘  └───────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                       External Services                          │
│  ┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │  CDSE/Sentinel   │  │    OpenAQ     │  │    WorldPop      │  │
│  │   Hub API        │  │    API v3     │  │  (Population)    │  │
│  └──────────────────┘  └───────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Django 5.x, Django REST Framework, Celery 5.x
- **Database**: PostgreSQL 15 + PostGIS 3.3
- **Cache/Queue**: Redis 7
- **GIS Server**: GeoServer 2.23 with ImageMosaic
- **Auth**: JWT via SimpleJWT
- **PDF Generation**: ReportLab (pure Python, no GTK dependencies)
- **Bias Correction**: mgwr (GWR), scikit-learn (linear fallback)
- **Raster Processing**: rasterio, numpy

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- CDSE account (for Sentinel-5P data)

### Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd air-risk
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Configure `.env` with your credentials:
```env
# CDSE Credentials
CDSE_CLIENT_ID=your-client-id
CDSE_CLIENT_SECRET=your-client-secret

# Database
POSTGRES_DB=air_quality
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure-password

# Django
SECRET_KEY=your-secret-key
DEBUG=False
```

4. Start services:
```bash
docker-compose up -d
```

5. Run migrations:
```bash
docker-compose exec web python manage.py migrate
```

6. Create superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

7. Load district boundaries:
```bash
docker-compose exec web python manage.py load_districts /data/pakistan_districts.geojson
```

8. Setup GeoServer:
```bash
docker-compose exec web python manage.py setup_geoserver
```

### Automation: CDSE → Correction → GeoServer ✅

To fully automate the pipeline where CDSE rasters are downloaded, bias-corrected, and published to GeoServer, follow these steps:

1. Ensure `.env` includes valid Copernicus Data Space (CDSE) credentials and GeoServer settings:
```dotenv
CDSE_CLIENT_ID=your-client-id
CDSE_CLIENT_SECRET=your-client-secret
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_ADMIN_USER=admin
GEOSERVER_ADMIN_PASSWORD=geoserver
RASTER_DATA_PATH=/app/data/rasters
```

2. Start services (Docker Compose):
```powershell
docker-compose up -d
```

3. Create GeoServer workspace and ImageMosaic stores. This creates stores named like `no2_corrected` and configures the `TIME` dimension:
```powershell
docker-compose exec web python manage.py setup_geoserver
```

4. If you need an initial bias correction model (recommended), run training after you have ground data:
```powershell
docker-compose exec web python manage.py train_correction_model NO2 180
```

5. Trigger the ingestion + correction pipeline manually for testing, or let Celery Beat schedule it:
```powershell
# Manual (runs synchronously via Celery apply):
docker-compose exec web python manage.py runscript trigger_daily_pipeline

# Or directly run the Celery task via management command or worker:
docker-compose exec web python manage.py shell -c "from air_quality.tasks import run_daily_ingestion_pipeline; run_daily_ingestion_pipeline.apply(args=['2025-12-01']).get()"
```

6. Confirm success:
  - Check `PollutantRaster` entries in the Django Admin for `corrected_file` and `stats`.
  - Verify GeoServer layers show the new time-enabled raster in the GeoServer UI.
  - Use the WMS endpoint with a `time` parameter to visualize the layer:
    - `http://localhost:8080/geoserver/air_risk/wms?service=WMS&version=1.1.1&request=GetMap&layers=air_risk:no2_corrected&bbox=60,23,78,37.5&width=800&height=600&srs=EPSG:4326&format=image/png&time=2025-12-01`

Notes / Troubleshooting:
- The GeoServer instance must be able to read the host `raster_data` volume; Docker Compose mounts it under `/opt/geoserver/data_dir/rasters`.
- The ImageMosaic indexer expects files with the filename format of `no2_corrected_YYYYMMDDT000000.tif` (the RasterManager sets this format when copying to mosaic). Do not change filename pattern unless you update `geoserver/mosaic_config.py`.
- If `django-environ` is missing: `pip install -r requirements/dev.txt` or `pip install django-environ`.
- If GeoServer REST calls fail with permission errors, double-check `GEOSERVER_ADMIN_USER` and `GEOSERVER_ADMIN_PASSWORD` config in .env and that `GEOSERVER_URL` is correct.

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/login/` - Obtain JWT tokens
- `POST /api/v1/auth/token/refresh/` - Refresh access token

### Air Quality
- `GET /api/v1/air-quality/districts/` - List districts with latest AQI
- `GET /api/v1/air-quality/stations/` - List ground stations
- `GET /api/v1/air-quality/rasters/` - List available raster layers
- `GET /api/v1/air-quality/rasters/time-slider/` - Get time slider bounds

### Exposure
- `GET /api/v1/exposure/district-exposure/` - District exposure data
- `GET /api/v1/exposure/hotspots/` - Pollution hotspots (GeoJSON)
- `GET /api/v1/exposure/time-series/` - Exposure time series
- `GET /api/v1/exposure/rankings/` - District rankings

### Reports
- `GET /api/v1/reports/reports/` - List user reports
- `POST /api/v1/reports/reports/` - Generate new report
- `GET /api/v1/reports/reports/{id}/download/` - Download PDF
- `GET /api/v1/reports/subscriptions/` - Report subscriptions

### API Documentation
- `GET /api/docs/` - Swagger UI
- `GET /api/redoc/` - ReDoc
- `GET /api/schema/` - OpenAPI schema

## Celery Tasks

### Daily Pipeline (runs at 6 AM UTC)
1. Fetch Sentinel-5P rasters from CDSE
2. Fetch ground readings from OpenAQ
3. Apply bias correction
4. Calculate exposure metrics
5. Generate subscription reports

### Weekly Tasks
- Model retraining (Sundays at 2 AM)
- Report cleanup (30 days retention)

## GeoServer WMS

Access corrected air quality rasters via WMS:

```
http://localhost:8080/geoserver/air_risk/wms?
  service=WMS&
  version=1.1.1&
  request=GetMap&
  layers=air_risk:no2_corrected&
  bbox=60,23,78,37.5&
  width=800&
  height=600&
  srs=EPSG:4326&
  format=image/png&
  time=2024-01-15
```

## Development

### Local Setup (without Docker)

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements/local.txt
```

3. Start PostgreSQL and Redis (or use Docker):
```bash
docker-compose up -d db redis
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Start development server:
```bash
python manage.py runserver
```

6. Start Celery worker:
```bash
celery -A air_risk worker -l info
```

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=. --cov-report=html
```

## Project Structure

```
air-risk/
├── air_risk/              # Django project settings
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── celery.py
│   └── urls.py
├── users/                 # User authentication app
├── air_quality/           # Core air quality app
│   ├── models.py          # District, Station, Raster models
│   ├── services/          # CDSE, OpenAQ, GeoServer clients
│   ├── tasks.py           # Celery tasks
│   └── api/               # REST API
├── correction/            # Bias correction app
│   ├── models.py          # CorrectionModel, CalibrationPoint
│   ├── methods/           # GWR, Linear correctors
│   └── tasks.py
├── exposure/              # Population exposure app
│   ├── models.py          # DistrictExposure, Hotspot
│   ├── calculators.py     # Exposure calculation
│   └── api/
├── reports/               # PDF report generation
│   ├── models.py          # Report, Subscription
│   ├── generators.py      # WeasyPrint PDF generation
│   └── charts.py          # Matplotlib charts
├── geoserver/             # GeoServer configuration
│   ├── sld_templates.py   # SLD style definitions
│   └── mosaic_config.py   # ImageMosaic configuration
├── requirements/
├── docker-compose.yml
└── Dockerfile
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `False` |
| `SECRET_KEY` | Django secret key | Required |
| `POSTGRES_HOST` | Database host | `db` |
| `POSTGRES_DB` | Database name | `air_quality` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | Required |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `CDSE_CLIENT_ID` | CDSE OAuth client ID | Required |
| `CDSE_CLIENT_SECRET` | CDSE OAuth client secret | Required |
| `GEOSERVER_URL` | GeoServer URL | `http://geoserver:8080/geoserver` |
| `GEOSERVER_USER` | GeoServer admin user | `admin` |
| `GEOSERVER_PASSWORD` | GeoServer admin password | `geoserver` |

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.
