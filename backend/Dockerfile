# Base image with GDAL support
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.0

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-dev \
    python3-venv \
    libpq-dev \
    gcc \
    g++ \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements
COPY requirements/ /app/requirements/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /app/requirements/dev.txt

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/data/rasters /app/data/worldpop /app/data/districts /app/staticfiles /app/media

# Expose port
EXPOSE 8000

# Default command
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
