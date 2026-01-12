# 🚀 Quick Start Guide

Get AIR RISK running on your local machine in under 10 minutes!

## 📋 Prerequisites Checklist

Before you begin, ensure you have:

- [ ] **Python 3.10+** installed ([Download](https://www.python.org/downloads/))
- [ ] **Node.js 18+** with npm ([Download](https://nodejs.org/))
- [ ] **PostgreSQL 14+** with PostGIS extension ([Download](https://www.postgresql.org/download/))
- [ ] **Conda** (optional but recommended) ([Download Miniconda](https://docs.conda.io/en/latest/miniconda.html))
- [ ] **Git** for version control ([Download](https://git-scm.com/downloads))
- [ ] **Google Earth Engine** service account (see [GEE Setup](#gee-setup))

---

## 🗄️ Database Setup

### 1. Create PostgreSQL Database

```bash
# Create database
createdb air_risk

# Enable PostGIS extension
psql -d air_risk -c "CREATE EXTENSION postgis;"

# Verify PostGIS installation
psql -d air_risk -c "SELECT PostGIS_version();"
```

**Expected Output**: PostGIS version (e.g., `3.3 USE_GEOS=1 USE_PROJ=1...`)

### 2. Create Database User (Optional)

```bash
# Create user with password
psql -d air_risk -c "CREATE USER air_risk_user WITH PASSWORD 'secure_password';"

# Grant privileges
psql -d air_risk -c "GRANT ALL PRIVILEGES ON DATABASE air_risk TO air_risk_user;"
psql -d air_risk -c "GRANT ALL ON SCHEMA public TO air_risk_user;"
```

---

## 🐍 Backend Setup

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/air-risk.git
cd air-risk
```

### 2. Create Python Environment

**Option A: Using Conda (Recommended)**
```bash
cd backend
conda create -n air_quality python=3.10
conda activate air_quality
```

**Option B: Using venv**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements/local.txt
```

**Common Issues**:
- If `psycopg2` fails: Install PostgreSQL development libraries
  - Ubuntu/Debian: `sudo apt-get install libpq-dev`
  - macOS: `brew install postgresql`
  - Windows: Usually pre-installed with PostgreSQL

- If `GDAL` fails: Install GDAL libraries
  - Ubuntu/Debian: `sudo apt-get install gdal-bin libgdal-dev`
  - macOS: `brew install gdal`
  - Windows: Use conda: `conda install -c conda-forge gdal`

### 4. Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate Django secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Edit .env file with your values
# Windows: notepad .env
# macOS/Linux: nano .env
```

**Minimum required variables**:
```env
SECRET_KEY=<generated-key-from-above>
DEBUG=True
POSTGRES_DB=air_risk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
GEE_SERVICE_ACCOUNT_KEY=gee-service-account.json
```

### 5. Run Migrations

```bash
python manage.py migrate
```

**Expected Output**: `Applying <app>.<migration>... OK` for each migration

### 6. Load Initial Data

```bash
# Load districts and provinces (GeoJSON to PostGIS)
python manage.py loaddata fixtures/districts.json
python manage.py loaddata fixtures/provinces.json
```

### 7. Create Admin User

```bash
python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: admin@example.com
# Password: <your-secure-password>
```

### 8. Start Backend Server

```bash
python manage.py runserver
```

**Verify**: Visit http://localhost:8000/admin/ and log in with admin credentials

---

## ⚛️ Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd ../frontend  # From backend/ directory
```

### 2. Install Node Dependencies

```bash
npm install
```

**If you encounter errors**:
```bash
# Clear npm cache
npm cache clean --force

# Try again
npm install
```

### 3. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env
# Windows: notepad .env
# macOS/Linux: nano .env
```

**Minimum required variables**:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

### 4. Start Frontend Server

```bash
npm run dev
```

**Verify**: Visit http://localhost:5173/ to see the application

---

## 🛰️ Google Earth Engine Setup {#gee-setup}

### 1. Create GEE Service Account

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "air-risk-gee")
3. Enable **Earth Engine API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Earth Engine API"
   - Click "Enable"
4. Create Service Account:
   - Navigate to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Name: `air-risk-gee`
   - Click "Create and Continue"
   - Skip role assignment (click "Continue")
   - Click "Done"
5. Create Key:
   - Click on the service account you just created
   - Navigate to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON" format
   - Click "Create" (downloads `project-id-xxxxx.json`)

### 2. Register Service Account with Earth Engine

1. Copy the service account email from the JSON file (e.g., `air-risk-gee@project-id.iam.gserviceaccount.com`)
2. Visit [Earth Engine Code Editor](https://code.earthengine.google.com/)
3. Click "Register a new Cloud Project"
4. Select "Register a Noncommercial or Commercial Cloud project"
5. Enter your project ID
6. The service account will be automatically registered

### 3. Add Credentials to Project

```bash
# Move the downloaded JSON file to backend directory
# Rename it to gee-service-account.json
mv ~/Downloads/project-id-xxxxx.json backend/gee-service-account.json

# Verify .env references this file
# Should show: GEE_SERVICE_ACCOUNT_KEY=gee-service-account.json
cat backend/.env | grep GEE_SERVICE_ACCOUNT_KEY
```

**⚠️ CRITICAL**: Never commit `gee-service-account.json` to git! It's already in `.gitignore`.

### 4. Test GEE Connection

```bash
cd backend
python -c "import ee; ee.Initialize(ee.ServiceAccountCredentials('SERVICE_ACCOUNT_EMAIL', 'gee-service-account.json')); print('GEE connected successfully!')"
```

Replace `SERVICE_ACCOUNT_EMAIL` with your service account email from the JSON file.

---

## ✅ Verification

### Backend Health Check

```bash
# Test API endpoints
curl http://localhost:8000/api/v1/air-quality/stations/
curl http://localhost:8000/api/v1/air-quality/districts/
```

### Frontend Health Check

1. Open http://localhost:5173/
2. You should see the AIR RISK dashboard
3. Map should load with district boundaries
4. No console errors in browser DevTools (F12)

### Database Verification

```bash
# Connect to database
psql -d air_risk

# Check loaded data
SELECT COUNT(*) FROM air_quality_district;  -- Should show ~160 districts
SELECT COUNT(*) FROM air_quality_province;  -- Should show ~5 provinces

# Exit
\q
```

---

## 🔧 Common Issues & Troubleshooting

### "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### "GDAL not found"
```bash
# Using conda (easiest)
conda install -c conda-forge gdal

# Or system package manager
# Ubuntu: sudo apt-get install gdal-bin libgdal-dev
# macOS: brew install gdal
```

### "Port 8000 already in use"
```bash
# Kill process on port 8000
# Windows: netstat -ano | findstr :8000, then taskkill /PID <pid> /F
# macOS/Linux: lsof -ti:8000 | xargs kill -9
```

### "Migrations not found"
```bash
# Reset migrations (development only!)
python manage.py migrate --fake-initial
```

### "GEE authentication failed"
```bash
# Verify JSON file exists
ls -la gee-service-account.json

# Check .env has correct filename
cat .env | grep GEE_SERVICE_ACCOUNT_KEY

# Ensure service account is registered with Earth Engine
```

---

## 📚 Next Steps

1. **Load Sample Data**:
   ```bash
   python manage.py fetch_openaq_data  # Fetch latest ground station readings
   ```

2. **Explore Admin Panel**: http://localhost:8000/admin/
   - View/edit stations
   - Manage districts and provinces
   - Create user tiers

3. **API Documentation**: http://localhost:8000/api/docs/
   - Interactive Swagger UI
   - Test endpoints directly

4. **Read Implementation Docs**:
   - [GEE Integration](../docs/implementation/GEE_INTEGRATION_COMPLETE.md)
   - [AI Insights](../docs/implementation/ENHANCED_AI_INSIGHTS_COMPLETE.md)
   - [Frontend Architecture](../docs/implementation/FRONTEND_IMPLEMENTATION_COMPLETE.md)

---

## 🐳 Docker Alternative (Quick Setup)

If you prefer Docker:

```bash
# From project root
docker-compose up

# Services:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:5173
# - PostgreSQL: localhost:5432
```

See [Docker Setup Guide](./docker-setup.md) for details.

---

## 💬 Get Help

- **Issues**: https://github.com/YOUR_USERNAME/air-risk/issues
- **Discussions**: https://github.com/YOUR_USERNAME/air-risk/discussions
- **Email**: [your.email@example.com]

---

Happy coding! 🎉
