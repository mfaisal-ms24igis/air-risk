# Air Risk: A Hybrid Satellite-Ground Air Quality Monitoring & Risk Intelligence Platform
## Academic Technical Design Document

**Author:** Senior GIS Architect
**Date:** December 15, 2025
**Version:** 1.0

---

## 1. Abstract

The scarcity of reliable air quality data in Pakistan presents a significant public health challenge, exacerbating the impact of pollution-related diseases. Conventional monitoring relies heavily on sparse and expensive ground stations, leaving vast geographic areas, particularly rural and semi-urban regions, unmonitored.

**Air Risk** addresses this spatial data gap by implementing a **Hybrid Satellite-Ground Monitoring System**. This platform synthesizes distinct data streams—real-time measurements from 370+ OpenAQ ground stations and high-resolution (1.1 km) satellite-derived pollutant layers from the Sentinel-5P mission via Google Earth Engine (GEE)—to provide a comprehensive, national-scale air quality intelligence solution.

The system is engineered on a robust modern technology stack comprising a **Django REST Framework (DRF)** backend with **PostGIS** for vector processing, integrated with **Google Earth Engine (GEE)** for raster spectral analysis. The frontend utilizes **React 18** and **MapLibre GL JS** to deliver a performant, interactive geospatial interface suitable for public viewing, academic research, and policy-making.

---

## 2. System Architecture

The solution employs a classic **Three-Tier Architecture**, strictly decoupled to ensure scalability, maintainability, and security.

### 2.1. Data Tier: Hybrid Storage & Processing
The data layer is bifurcated into **Vector** and **Raster** domains to optimize for the distinct nature of the datasets:
*   **Vector Storage (PostgreSQL + PostGIS):**
    *   Stores static administrative boundaries (Provinces, Districts) and dynamic point data (Monitoring Stations).
    *   Capabilities: Performs complex spatial queries (e.g., *k-Nearest Neighbors* for station finding, *ST_Intersects* for point-in-polygon checks).
*   **Raster Processing (Google Earth Engine):**
    *   Stores and processes multi-petabyte satellite archives (Sentinel-5P TROPOMI).
    *   Capabilities: Handles computationally intensive spectral pixel arithmetic and zonal statistics on the cloud, returning only processed tiles or aggregate statistics to the application server.

### 2.2. Application Tier: Business Logic & Orchestration
The core logic resides in a **Django** application, structured around a **Service-Oriented** design pattern:
*   **API Gateway (DRF):** Exposes RESTful endpoints versioned at `/api/v1/`.
*   **Tiered Access Control System:** Implements business logic to differentiate service levels:
    *   **BASIC Tier:** Access to simplified administrative geometries (100m tolerance), limited station queries (max 10), and pre-calculated AQI aggregates.
    *   **PREMIUM Tier:** Access to high-fidelity geometries, expanded station queries (max 50), raw pollutant concentrations (NO₂, SO₂, CO, O₃), and real-time GEE raster tiles.
*   **Asynchronous Task Queue (Django-Q):** Offloads heavy computation tasks, specifically the **AI Report Generation Pipeline**, ensuring the main thread remains non-blocking and responsive.

### 2.3. Presentation Tier: Modern Geospatial Interface
The client-side application is built with **React 18** and **TypeScript**, focused on data visualization and state integrity:
*   **Visualization Engine (MapLibre GL JS):** Renders millions of vector vertices and high-resolution raster tiles using WebGL, ensuring 60FPS performance even with complex map overlays.
*   **State Management (Zustand):** Manages global application state (Authentication, User Tiers, Map Viewport) with a minimal footprint compared to Redux.
*   **Data Synchronization (TanStack Query):** Implements "stale-while-revalidate" caching strategies.
    *   *Static Data* (Districts): Cached for 10 minutes.
    *   *Real-time Data* (Stations): Cached for 1 minute with 5-minute background polling.
    *   *Expensive Data* (GEE Tiles): Cached for 1 hour to minimize quota usage.

---

## 3. Geospatial Methodology

### 3.1. Hybrid Data Fusion
The "Hybrid" approach fuses two disparate data models to create a holistic view of air quality:
1.  **Static Vector Integration:** Administrative boundaries are served as **GeoJSON** FeatureCollections.
    *   *Method:* PostGIS generalization functions (`ST_Simplify`) reduce vertex count for non-premium users to optimize network payload.
2.  **Dynamic Raster Integration:** Satellite data is served via **WMS/XYZ Tiles**.
    *   *Method:* The backend requests GEE to generate signed tile URLs for specific pollutant bands (e.g., `CO_column_number_density`). These URLs are overlayed on the MapLibre canvas, allowing users to "see" pollution distribution between ground stations.

### 3.2. Spatial Analytics
*   **Exposure Calculation (Zonal Statistics):**
    *   *Algorithm:* The system calculates the intersection of pollution raster pixels with district vector polygons to derive mean pollutant values.
    *   *Population Weighting:* These mean values are cross-referenced with **WorldPop** population density rasters to calculate "Population at Risk," prioritizing high-pollution zones in densely populated areas.
*   **Nearest Neighbor Analysis (KNN):**
    *   *Algorithm:* Uses PostGIS `<->` operator (KNN) to efficiently index and retrieve the *N* closest monitoring stations to a user's geolocation or selected district centroid.

---

## 4. Key Implementation Details

### 4.1. AI-Driven Health Reporting
The system transcends simple data visualization by generating narrative intelligence via an **AI Pipeline**:
1.  **Data Aggregation:** The backend aggregates comprehensive statistics: location context (area, demographics), ground measurements (PM2.5, PM10), satellite observations (gas columns), and WHO guideline variances.
2.  **Structured Prompt Engineering:** These statistics are formatted into five distinct markdown data tables.
3.  **LLM Inference:** An integrated Language Model (LLM) analyzes these tables to generate:
    *   **Pollution Source Inference:** Analyzing ratios (e.g., high NO₂/CO suggests traffic vs. industrial).
    *   **Health Risk Assessment:** Categorizing risks for varying demographics (Children, Elderly).
4.  **PDF Generation:** The narrative and tables are compiled into a professional-grade PDF report using **ReportLab**, delivered asynchronously via a secure download link.

### 4.2. Performance Optimization Strategy
*   **Payload Reduction:** Implementing geometry simplification for the `BASIC` tier reduces GeoJSON payload sizes by approximately **60%**, significantly improving First Contentful Paint (FCP) on mobile and low-bandwidth networks.
*   **Intelligent Caching:** Utilizing **Redis** (via Django cache) for API responses and **TanStack Query** for client-side state eliminates redundant network requests. "Expensive" operations like GEE tile URL generation are cached aggressively (1 hour), protecting downstream API quotas.

---

## 5. Critical Discussion

### 5.1. The "God Component" Refactoring
A significant architectural debt identified in the initial audit was the presence of a "God Component"—`UnifiedMap.tsx`. This single file had accumulated excessive responsibilities: creating map instances, managing 6+ different layer types, handling UI state, and processing data logic.
*   **Resolution:** The component was decomposed using the **Compound Component Pattern**. Logic was segregated into distinct functional units: `MapBase` (initialization), `DistrictsLayer` (vector visualization), `GEEExposureLayer` (raster visualization), and custom hooks (`useMapState`). This separation of concerns improves testability and allows independent development of map features.

### 5.2. Legacy State Fragmentation
The backend initially suffered from "Split State" logic, where distinct models (`GroundStation` vs. `AirQualityStation`) represented similar entities due to incomplete migrations.
*   **Resolution:** The data model was unified under the robust `AirQualityStation` schema. Deprecated endpoints were marked for sunsetting, and the API was realigned to serve a single truth source. This eliminated data inconsistencies where legacy views returned partial datasets compared to the modern API.

### 5.3. Limitations & Future Work
While the hybrid model is robust, it relies on orbital mechanics (Sentinel-5P overpass times) which limits satellite data temporal resolution to once daily. Future iterations could integrate geostationary satellite data (GEMS) for hourly raster updates or employ machine learning to interpolate "blind spots" between ground stations using the available satellite correlation columns.
