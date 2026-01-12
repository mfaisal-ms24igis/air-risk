<div align="center">

# 🌍 AIR RISK

### Air Quality Exposure & Risk Intelligence Platform

**Bridging Pakistan's Air Quality Data Gap with Satellite-Ground Fusion**

[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)
[![Google Earth Engine](https://img.shields.io/badge/Google_Earth_Engine-API-yellow.svg)](https://earthengine.google.com/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.3-blue.svg)](https://postgis.net/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)]()

[Features](#-key-features) • [Tech Stack](#-technology-stack) • [Quick Start](#-quick-start) • [Architecture](#-system-architecture) • [Documentation](#-documentation)

</div>

---

## 🎯 Project Impact

> **Independent Research & Development Project** - Addressing Pakistan's critical air quality monitoring crisis

- 🌐 **240 million people** served by fewer than 100 ground monitoring stations
- 📍 **160+ districts** now covered with comprehensive air quality data
- 🛰️ **120+ previously unmonitored districts** now accessible via satellite fusion
- 📊 **370+ OpenAQ ground stations** integrated for real-time monitoring
- 🔬 **1.1km resolution** pixel-wise exposure assessment using Google Earth Engine
- 💰 **<$500/month** operational cost vs. $15K+ per physical monitor

---

## ✨ Key Features

### 🛰️ Adaptive Data Fusion Framework
- **Context-Aware Source Selection**: IDW interpolation for station-rich districts, satellite zonal statistics for sparse regions, hybrid 70/30 blending for transition zones
- **Sentinel-5P TROPOMI Integration**: NO₂, SO₂, CO, O₃, HCHO pollutant monitoring at 1113.2m resolution
- **Bias Correction**: Geographically Weighted Regression (MGWR) for calibrating satellite estimates

### 📊 Pixel-Wise Exposure Calculation
- **Population-Weighted Risk Assessment**: WorldPop 100m grids aggregated to 1.1km for exposure analysis
- **GEE Server-Side Processing**: >90% bandwidth reduction by offloading terabyte-scale computations to planetary infrastructure
- **Temporal Compositing**: 7-day moving averages for noise reduction in satellite observations

### 🤖 AI-Powered Health Insights
- **Local LLM Integration**: LM Studio generating structured health reports from 5 comprehensive data tables
- **Demographic Risk Assessment**: Population-specific exposure profiles by age groups
- **Source Attribution**: Pollution origin inference from spatial patterns and meteorological data

### 🗺️ Interactive Geospatial Visualization
- **WebGL Acceleration**: MapLibre GL JS maintaining 60 FPS with complex multi-layer overlays
- **Choropleth Maps**: District-level color-coded air quality visualization
- **XYZ Tile Serving**: Google Earth Engine cloud-optimized raster delivery

### 🔐 Tiered Access Control
- **FREE/BASIC/PREMIUM Tiers**: Progressive feature unlocking with rate limiting
- **Geometry Simplification**: 60% payload reduction for free tier users
- **ReportLab PDF Generation**: Custom reports with matplotlib charts and AI narratives

---

## 🛠️ Technology Stack

### Backend Infrastructure
- **Framework**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 14 + PostGIS 3.3 (spatial indexing with GIST)
- **Task Queue**: Django-Q for asynchronous processing
- **Geospatial**: Google Earth Engine Python API, Rasterio, GeoPandas, Shapely
- **Data Science**: scikit-learn (bias correction), PySAL (MGWR)
- **PDF Generation**: ReportLab with matplotlib chart embedding
- **APIs**: OpenAQ integration, Sentinel-5P TROPOMI, WorldPop population grids

### Frontend Architecture
- **Framework**: React 18 + TypeScript 5.0
- **Mapping**: MapLibre GL JS (WebGL rendering)
- **State Management**: 
  - TanStack Query v5 (server state, caching, mutations)
  - Zustand (client state)
- **UI/UX**: Tailwind CSS, Framer Motion, Radix UI primitives
- **Build Tool**: Vite (hot module replacement)

### Data Sources
- **Satellite**: Sentinel-5P TROPOMI (ESA Copernicus)
- **Ground Stations**: OpenAQ API (370+ stations)
- **Population**: WorldPop 100m resolution grids
- **Administrative**: GADM Pakistan district/province boundaries

### Infrastructure
- **Compute**: Google Earth Engine (cloud raster processing)
- **Storage**: PostgreSQL + PostGIS (spatial queries)
- **Deployment**: Docker + Docker Compose

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React + TS)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  MapLibre GL │  │ TanStack     │  │ Zustand State      │   │
│  │  WebGL Maps  │  │ Query Cache  │  │ Management         │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
                    REST API / Django DRF
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (Django 5.0)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Air Quality  │  │ Exposure     │  │ Reports            │   │
│  │ API          │  │ Calculation  │  │ (ReportLab+AI)     │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Django-Q     │  │ Bias         │  │ Tiered Access      │   │
│  │ Task Queue   │  │ Correction   │  │ Control            │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATA LAYER (PostgreSQL + PostGIS)                  │
│  • 370+ Ground Stations with spatial indexing (GIST)           │
│  • District/Province geometries (simplified for performance)   │
│  • Historical readings with time-series queries                │
│  • User subscriptions and access tiers                         │
└─────────────────────────────────────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXTERNAL SERVICES                                  │
│  ┌──────────────────────┐  ┌────────────────────────────┐     │
│  │ Google Earth Engine  │  │ OpenAQ API                 │     │
│  │ • Sentinel-5P tiles  │  │ • Real-time readings       │     │
│  │ • Zonal statistics   │  │ • Station metadata         │     │
│  │ • WorldPop grids     │  │ • Historical data          │     │
│  └──────────────────────┘  └────────────────────────────┘     │
│  ┌──────────────────────┐                                      │
│  │ LM Studio (Local)    │                                      │
│  │ • Health insights    │                                      │
│  │ • Risk narratives    │                                      │
│  └──────────────────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow: Adaptive Fusion Logic

```python
if ground_station_count >= 5:
    # Station-rich: IDW interpolation
    method = "IDW"
elif ground_station_count == 0:
    # Station-sparse: Satellite-only zonal stats
    method = "GEE_SATELLITE"
else:
    # Hybrid: 70% satellite + 30% station (bias-corrected)
    method = "HYBRID_FUSION"
```

---

## 📋 Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **PostgreSQL** 14+ with PostGIS 3.3+ extension
- **Conda** (recommended for Python environment)
- **Google Earth Engine** service account (see [Setup Guide](#gee-setup))

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/air-risk.git
cd air-risk
```

### 2. Backend Setup

```bash
cd backend

# Create conda environment
conda create -n air_quality python=3.10
conda activate air_quality

# Install dependencies
pip install -r requirements/local.txt

# Set up environment variables (see Configuration section below)
cp .env.example .env
# Edit .env with your database and API credentials

# Set up PostgreSQL database
createdb air_risk
psql -d air_risk -c "CREATE EXTENSION postgis;"

# Run migrations
python manage.py migrate

# Load initial geographic data
python manage.py loaddata fixtures/districts.json
python manage.py loaddata fixtures/provinces.json

# Create superuser for admin access
python manage.py createsuperuser

# Start Django development server
python manage.py runserver
```

Backend API: `http://localhost:8000/api/v1/`  
Admin Panel: `http://localhost:8000/admin/`

### 3. Frontend Setup

```bash
cd ../frontend

# Install Node dependencies
npm install

# Configure API endpoint
cp .env.example .env
# Edit .env: VITE_API_URL=http://localhost:8000/api/v1

# Start Vite development server
npm run dev
```

Frontend App: `http://localhost:5173/`

---

## ⚙️ Configuration

### Backend Environment Variables

Create `backend/.env` from the template:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL + PostGIS)
DATABASE_URL=postgis://username:password@localhost:5432/air_risk

# Site
SITE_URL=http://localhost:8000

# Google Earth Engine (DO NOT COMMIT!)
# Place your GEE service account JSON file in backend/ directory
# and reference it here (this file is gitignored)
GEE_SERVICE_ACCOUNT_KEY=gee-service-account.json

# OpenAQ API (optional - for station updates)
OPENAQ_API_KEY=your-openaq-key

# LM Studio (Local AI - optional)
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=local-model

# Email (for user notifications)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

<a id="gee-setup"></a>
### Google Earth Engine Setup

1. **Create GEE Service Account**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or use existing
   - Enable Earth Engine API
   - Create Service Account → Download JSON key

2. **Register Service Account with Earth Engine**:
   - Go to [Earth Engine Asset Manager](https://code.earthengine.google.com/)
   - Register service account email from JSON file

3. **Add Credentials to Project**:
   ```bash
   # Place the JSON file in backend/ directory
   mv ~/Downloads/your-gee-key.json backend/gee-service-account.json
   
   # Update .env file
   GEE_SERVICE_ACCOUNT_KEY=gee-service-account.json
   ```

**⚠️ IMPORTANT**: The `gee-service-account.json` file is automatically excluded from git via `.gitignore`. Never commit credentials!

### Frontend Environment Variables

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000/api/v1
VITE_MAPBOX_TOKEN=your-mapbox-token (optional - for satellite basemap)
```

---

## 📁 Project Structure

```
AIR RISK/
├── backend/                          # Django backend
│   ├── air_quality/                  # Core air quality app
│   │   ├── api/                      # REST API endpoints
│   │   │   ├── serializers.py        # DRF serializers
│   │   │   └── views.py              # API views (stations, districts, GEE tiles)
│   │   ├── management/commands/      # Django management commands
│   │   │   ├── fetch_openaq_data.py  # Import ground station data
│   │   │   └── sync_gee_data.py      # Sync satellite observations
│   │   ├── models.py                 # Data models (Station, Reading, District)
│   │   ├── tasks.py                  # Django-Q async tasks
│   │   └── constants.py              # Pollutant thresholds, WHO guidelines
│   ├── exposure/                     # Exposure calculation engine
│   │   ├── api/views.py              # Exposure API endpoints
│   │   ├── services/                 # Business logic
│   │   │   ├── gee_exposure.py       # Pixel-wise GEE exposure
│   │   │   ├── fusion.py             # Adaptive satellite-ground fusion
│   │   │   └── interpolation.py      # IDW, kriging algorithms
│   │   └── models.py                 # ExposureResult, DataSource
│   ├── correction/                   # Bias correction methods
│   │   ├── mgwr.py                   # Multiscale GWR implementation
│   │   └── calibration.py            # Satellite calibration utilities
│   ├── reports/                      # PDF report generation
│   │   ├── api/views.py              # Report generation endpoints
│   │   ├── generators/               # ReportLab report builders
│   │   │   ├── premium_report.py     # Custom PDF templates
│   │   │   └── charts.py             # Matplotlib chart generation
│   │   └── models.py                 # Report, ReportRequest
│   ├── users/                        # User authentication & tiers
│   │   ├── models.py                 # CustomUser, Subscription
│   │   ├── permissions.py            # Tier-based permissions
│   │   └── middleware.py             # Rate limiting
│   ├── air_risk/                     # Django project settings
│   │   ├── settings/                 # Environment-based configs
│   │   │   ├── base.py
│   │   │   ├── local.py
│   │   │   └── production.py
│   │   └── urls.py                   # URL routing
│   ├── data/                         # External data files
│   │   ├── geojson/                  # District/province boundaries
│   │   └── rasters/                  # Cached satellite rasters (gitignored)
│   ├── requirements/                 # Python dependencies
│   │   ├── base.txt
│   │   ├── local.txt                 # Development extras
│   │   └── production.txt
│   └── manage.py                     # Django CLI
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── api/                      # API client services
│   │   │   ├── client.ts             # Axios instance with auth
│   │   │   └── endpoints/            # Typed API functions
│   │   ├── components/               # React components
│   │   │   ├── Map/                  # MapLibre components
│   │   │   │   ├── MapContainer.tsx
│   │   │   │   ├── ChoroplethLayer.tsx
│   │   │   │   └── StationMarkers.tsx
│   │   │   ├── Dashboard/            # Analytics dashboard
│   │   │   ├── Reports/              # Report viewer/downloader
│   │   │   └── common/               # Reusable UI components
│   │   ├── contexts/                 # React contexts
│   │   │   ├── AuthContext.tsx       # User authentication state
│   │   │   └── MapContext.tsx        # Map state management
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useStations.ts        # TanStack Query for stations
│   │   │   ├── useExposure.ts        # TanStack Query for exposure
│   │   │   └── useReports.ts         # Report generation hook
│   │   ├── pages/                    # Route pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Map.tsx
│   │   │   ├── Reports.tsx
│   │   │   └── Login.tsx
│   │   ├── store/                    # Zustand stores
│   │   │   ├── mapStore.ts           # Map viewport, layers
│   │   │   └── uiStore.ts            # UI state (modals, sidebars)
│   │   ├── types/                    # TypeScript definitions
│   │   │   ├── api.ts                # API response types
│   │   │   └── models.ts             # Domain models
│   │   ├── utils/                    # Utility functions
│   │   │   ├── formatters.ts         # Date, number formatting
│   │   │   └── colors.ts             # AQI color scales
│   │   ├── App.tsx                   # Root component
│   │   └── main.tsx                  # Entry point
│   ├── public/                       # Static assets
│   ├── package.json                  # Node dependencies
│   └── vite.config.ts                # Vite build config
├── docs/                             # Documentation (create this)
│   ├── thesis/                       # Academic documentation
│   ├── architecture/                 # System design docs
│   └── setup/                        # Deployment guides
├── .gitignore                        # Git exclusions (credentials!)
└── README.md                         # This file
```

---

## 🔌 Key API Endpoints

### Air Quality Module
```http
GET  /api/v1/air-quality/stations/          # List all ground monitoring stations
GET  /api/v1/air-quality/stations/{id}/     # Station details + recent readings
GET  /api/v1/air-quality/districts/         # District boundaries (GeoJSON support)
GET  /api/v1/air-quality/provinces/         # Province boundaries
GET  /api/v1/air-quality/readings/          # Historical pollutant readings
GET  /api/v1/air-quality/gee/tiles/{z}/{x}/{y}/  # Sentinel-5P satellite tiles
```

### Exposure Assessment
```http
GET  /api/v1/exposure/districts/            # District-level exposure aggregates
GET  /api/v1/exposure/geojson/districts/    # Choropleth-ready GeoJSON
POST /api/v1/exposure/calculate-gee/        # Trigger pixel-wise GEE calculation
GET  /api/v1/exposure/results/{district_id}/  # Exposure results by district
```

### Premium Features (Requires Authentication)
```http
POST /api/v1/reports/generate/              # Generate custom PDF report
GET  /api/v1/reports/download/{id}/         # Download generated report
GET  /api/v1/ai-insights/district/{id}/     # AI-powered health insights
POST /api/v1/ai-insights/batch/             # Batch insights for multiple districts
```

### Authentication
```http
POST /api/v1/auth/register/                 # User registration
POST /api/v1/auth/login/                    # Login (returns JWT token)
POST /api/v1/auth/refresh/                  # Refresh access token
GET  /api/v1/auth/user/                     # Current user profile
```

**API Documentation**: `http://localhost:8000/api/docs/` (Swagger UI)

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
python manage.py test

# Test specific module
python manage.py test air_quality
python manage.py test exposure

# Test GEE exposure calculation
python test_gee_exposure.py

# Test premium report generation
python premium_report_demo.py

# Test AI insights
python test_enhanced_ai_insights.py

# Coverage report
coverage run --source='.' manage.py test
coverage html
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

---

## 📊 Performance Benchmarks

| Metric | Value | Description |
|--------|-------|-------------|
| **GEE Tile Load** | <500ms | XYZ tile serving for 1113.2m resolution |
| **District Query** | <50ms | PostGIS spatial queries with GIST indexing |
| **Exposure Calc** | ~2-3 min | Pixel-wise calculation for entire country (160+ districts) |
| **PDF Generation** | ~5-10s | ReportLab with 5 matplotlib charts + AI narrative |
| **Payload Reduction** | 60% | Geometry simplification for free tier users |
| **Map FPS** | 60 FPS | WebGL choropleth with 160+ districts |
| **Bandwidth Savings** | >90% | GEE server-side processing vs. local raster downloads |

---

## 📚 Documentation

### Project Documentation
- 📘 **[Technical Design Document](Technical_Design_Document.md)** - System architecture and design decisions
- 📗 **[Academic Technical Design](ACADEMIC_TECHNICAL_DESIGN_DOCUMENT.md)** - Research methodology and thesis context
- 📕 **[Implementation Plan](implementation_plan.md)** - Development roadmap and milestones

### Implementation Guides
- 🛰️ **[GEE Integration](backend/GEE_INTEGRATION_COMPLETE.md)** - Google Earth Engine setup and satellite data processing
- 🤖 **[AI Insights](ENHANCED_AI_INSIGHTS_COMPLETE.md)** - LM Studio integration and health report generation
- 📊 **[Enhanced Reports](ENHANCED_REPORTS_COMPLETE.md)** - ReportLab PDF generation with charts
- 🎨 **[Frontend Architecture](frontend/FRONTEND_IMPLEMENTATION_COMPLETE.md)** - React component structure and state management
- 🔄 **[Backend-Frontend Alignment](FRONTEND_BACKEND_ALIGNMENT_COMPLETE.md)** - API contracts and data flow

### Thesis Documentation
- 📋 **[Thesis Proposal (RM898)](RM898_THESIS_PROPOSAL.md)** - Research objectives and methodology
- 📝 **[Form TH1 Main](THESIS_FORM_TH1_MAIN.md)** - Official thesis submission form
- ⏱️ **[Timeline (Annex B)](THESIS_FORM_TH1_ANNEX_B_TIMELINE.md)** - Research timeline and milestones
- 🎯 **[Relevance & Advantages](THESIS_FORM_TH1_RELEVANCE_ADVANTAGES.md)** - Research contribution
- 📚 **[Reference Guide](THESIS_REFERENCE_GUIDE.md)** - Citation management

### Setup & Deployment
- 🔧 **[Backend README](backend/README.md)** - Backend-specific setup instructions
- 🖥️ **[LM Studio Setup](backend/LM_STUDIO_SETUP.md)** - Local AI model configuration
- 🔒 **[Security Guide](backend/SECURITY_GUIDE.md)** - Production security checklist

---

## � Research & Innovation

This project addresses the critical gap in air quality monitoring infrastructure across Pakistan through innovative use of satellite-ground data fusion.

### Key Research Areas
1. Adaptive fusion algorithms for heterogeneous monitoring networks in resource-constrained environments
2. Cloud-based exposure assessment leveraging Google Earth Engine's planetary-scale infrastructure
3. Geographically weighted regression for calibrating satellite estimates in data-sparse regions

### Technical Contributions
- **Novel adaptive fusion algorithm** optimizing data source selection based on local monitoring density
- **Cloud-native exposure assessment** achieving >90% bandwidth reduction through server-side processing
- **Open-source implementation** enabling deployment in other developing countries with similar monitoring challenges
- **Scalable architecture** supporting <$500/month operational cost vs. $15K+ per physical monitor

---

## 🚀 Deployment

### Development
```bash
# Start both backend and frontend
docker-compose up

# Access services
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# PostgreSQL: localhost:5432
```

### Production Considerations
- ☁️ **Hosting**: Deploy backend on Railway/Render/DigitalOcean (~$10-20/month), frontend on Vercel/Netlify (free tier)
- 🗄️ **Database**: Managed PostgreSQL with PostGIS (Supabase, DigitalOcean, AWS RDS)
- 🌐 **CDN**: Cloudflare for static assets and tile caching
- 🔐 **Secrets**: Use environment-based secrets management (never commit credentials!)
- 📊 **Monitoring**: Sentry for error tracking, Plausible Analytics for usage metrics
- 🔄 **CI/CD**: GitHub Actions for automated testing and deployment

See [backend/DEPLOYMENT.md](backend/DEPLOYMENT.md) for detailed production deployment guide.

---

## 🤝 Contributing

Contributions are welcome! This is an open-source project aimed at improving air quality monitoring in resource-constrained regions.

To contribute:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

For questions or collaboration inquiries, please open an issue.

---

## 📄 License

**MIT License** - Open Source

This project is open-source and available for use, modification, and distribution under the MIT License.

For commercial partnerships or custom deployments, please contact the maintainer.

---

## 🙏 Acknowledgments

- **Google Earth Engine** team for providing planetary-scale geospatial processing
- **OpenAQ** for curating global air quality data
- **Sentinel-5P TROPOMI** team at ESA for open satellite data
- **NUST GIS Department** for academic guidance and infrastructure support
- **WorldPop** project for open-access population grids

---

## 📧 Contact

**Developer**: Muhammad Faisal  
**GitHub**: [@mfaisal-ms24igis](https://github.com/mfaisal-ms24igis)  
**Project**: Air Quality Intelligence Platform for Pakistan  
**Email**: Contact via GitHub

---

<div align="center">

**Built with ❤️ for improving public health through geospatial intelligence**

⭐ Star this repo if you find it useful for your research or learning!

</div>
