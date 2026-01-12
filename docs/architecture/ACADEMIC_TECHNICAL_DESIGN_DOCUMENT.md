# Academic Technical Design Document: Air Risk System

**Master's Level Web GIS Project**  
**System Architecture and Geospatial Methodology**

---

## Abstract

Pakistan faces a critical shortage of ground-based air quality monitoring infrastructure, with fewer than 100 operational stations serving a population of 240 million across 160+ districts. This infrastructural deficit creates significant data gaps that impede effective air quality management and public health interventions. The Air Risk system addresses this challenge through a hybrid satellite-ground monitoring architecture that integrates European Space Agency's Sentinel-5P TROPOMI satellite observations with sparse ground station measurements from OpenAQ and Pakistan EPA sources. The system employs Google Earth Engine for planetary-scale raster processing, PostGIS for vector spatial operations, and a tiered access control framework to balance computational resources with user requirements. Built on Django REST Framework and React with MapLibre GL, the platform demonstrates how modern geospatial web technologies can bridge infrastructure gaps through intelligent data fusion, enabling population-level exposure assessment across administrative boundaries where ground monitoring is absent.

---

## System Architecture: Three-Tier Model

### Data Tier: Hybrid Raster-Vector Storage

The system employs a dual-storage strategy optimized for different geospatial data characteristics. **Vector data**—comprising district boundaries (160 polygons), province boundaries (7 polygons), and ground station locations (370+ points)—resides in PostgreSQL 14 with PostGIS 3.3 extension, leveraging spatial indexes (GIST) for efficient geometric queries. Administrative boundaries originate from Pakistan Bureau of Statistics GeoPackage files, loaded via GeoPandas with coordinate system normalization to EPSG:4326 (WGS84). Each `District` model stores a `MultiPolygonField` with pre-calculated centroid (`PointField`) and cached population totals derived from WorldPop 2020 raster via zonal statistics (`rasterstats.zonal_stats`), avoiding repeated expensive raster operations.

**Raster data**—satellite imagery from Sentinel-5P TROPOMI—is processed exclusively through Google Earth Engine's distributed compute infrastructure, never materializing locally. The `SatelliteDataManager` service constructs Earth Engine `ImageCollection` queries filtered by temporal range (7-30 days) and Pakistan's bounding box (60-78°E, 23-37.5°N), applying quality masks (`qa_value > 0.5`) and composite reducers (`ee.Reducer.mean()`) to generate analysis-ready datasets. For visualization, the `GEETileService` invokes GEE's `getMapId()` API to generate XYZ tile URLs with pre-configured visualization parameters (min/max values, color palettes), which MapLibre GL consumes via a backend proxy endpoint. This architecture offloads terabyte-scale raster operations to GEE's planetary computer while keeping the application server stateless and lightweight.

The separation between persistent vector storage (PostGIS) and ephemeral raster processing (GEE) reflects the fundamental difference in data volatility: administrative boundaries change infrequently (cached 24 hours in TanStack Query), whereas satellite observations require near-real-time retrieval (5-minute cache). This tiered caching strategy optimizes both network bandwidth and user experience.

### Application Tier: Tiered Access and Async Processing

The application tier implements a graduated access control model that couples feature availability with computational cost. The `TieredGeometryMixin` serializer dynamically simplifies PostGIS geometries using tolerance-based algorithms: FREE users receive district polygons simplified to 0.01° (~1km) via `geometry.simplify(tolerance, preserve_topology=True)`, reducing GeoJSON payload sizes by ~60% while maintaining topological correctness; PREMIUM users receive full-resolution geometries (tolerance=0°). This spatial data reduction parallels tiered rate limiting implemented through Django REST Framework's `TieredUserRateThrottle` class, which enforces per-tier request quotas (FREE: 10/min, BASIC: 60/min, PREMIUM: 600/min) with cache keys incorporating user tier (`throttle_{tier}_{user_id}`) to prevent tier gaming.

The system employs Django-Q for asynchronous task processing, specifically for computationally intensive report generation. When a user requests a location-based air quality report via `POST /api/v1/reports/generate/`, the `create_report_async()` view immediately returns a task identifier after queueing `generate_location_report_async(report_id)`. This task function orchestrates a multi-step pipeline: (1) initialize `TrendAnalyzer` service with location coordinates and radius, (2) retrieve ground station data within spatial buffer via PostGIS `ST_DWithin`, (3) fetch satellite exposures from GEE for the same region, (4) optionally invoke LM Studio local LLM for AI health insights, (5) generate PDF with ReportLab, combining matplotlib charts with structured data tables. The frontend polls `/api/v1/reports/{id}/status/` every 3 seconds, displaying progress indicators while the report transitions through states (PENDING → GENERATING → COMPLETED). This asynchronous architecture prevents long-running GEE API calls (which can exceed 30 seconds for complex geometries) from blocking Django's WSGI worker pool, maintaining system responsiveness under concurrent user load.

Task timeout is configured at 600 seconds (10 minutes) to accommodate the worst-case scenario: generating a 30-day trend analysis with AI insights for a large district, which involves multiple sequential GEE API calls, each subject to network latency and GEE's own job queue delays.

### Presentation Tier: Progressive Enhancement with MapLibre

The frontend employs a progressive enhancement strategy centered on MapLibre GL JS, which renders vector tiles and raster layers using WebGL for hardware-accelerated performance. The `UnifiedMap` component coordinates five distinct layer types through a Zustand state store: (1) `ProvincesLayer` for coarse national overview, (2) `DistrictsLayer` with choropleth coloring based on exposure metrics, (3) `StationsLayer` with circle markers clustered via Supercluster, (4) `SatelliteLayer` consuming GEE tile URLs as RasterSource, and (5) `GEEExposureLayer` for premium users displaying pixel-level exposure calculated in Earth Engine. Each layer subscribes to relevant store slices using Zustand selectors (`const layers = useMapStore(state => state.layers)`), ensuring granular re-renders only when specific layer visibility toggles change.

TanStack Query v5 manages server state with intelligent cache invalidation. GeoJSON endpoints (`/api/v1/air-quality/districts/geojson/`) have 10-minute stale times, reflecting the infrequency of administrative boundary updates, while station readings (`/api/v1/stations/latest/`) refetch every 1 minute to display near-real-time air quality data. The query key factory pattern (`queryKeys.geojson.districts(province)`) ensures cache hits when navigating between views: drilling down from national to provincial view reuses cached district GeoJSON filtered client-side, avoiding redundant API calls.

The component hierarchy deliberately separates concerns: `MapBase` handles low-level MapLibre initialization and event binding, layer components (`DistrictsLayer.tsx`) focus on GeoJSON data transformation and style rules, while UI controls (`LayerControls`, `UnifiedLegend`) remain decoupled and reusable. This modularity facilitates A/B testing of visualization strategies—for example, switching between PM2.5 choropleth and AQI category coloring by swapping paint expressions without touching map initialization logic.

---

## Geospatial Methodology

### Hybrid Data Fusion: Filling Ground Station Voids

The core methodological challenge lies in inferring district-level exposure when ground stations are spatially clustered in major urban centers (Lahore, Karachi, Islamabad) while 120+ districts lack any monitoring infrastructure. The system addresses this through a two-pronged approach:

**Ground-based calculation** for station-rich districts employs inverse distance weighting (IDW): for a target district centroid, the `TrendAnalyzer` queries PostGIS for stations within configurable radius (default 50km) using `ST_DWithin(station.location, district.centroid, 50000)`, extracts PM2.5 readings from the `station_readings` table, and computes weighted mean where weights equal `1 / distance²`. This preserves high-fidelity ground measurements where available while acknowledging spatial autocorrelation decay with distance.

**Satellite-based calculation** for station-sparse districts leverages Sentinel-5P TROPOMI's 5.5km×3.5km pixel resolution. The `GEEExposureService` constructs an Earth Engine computational graph: (1) retrieve TROPOMI NO2, SO2, CO, O3 image collections for target date window, (2) filter to Pakistan bbox and apply quality masks, (3) reduce to single composite via temporal mean, (4) perform zonal statistics over district polygon (`ee.Image.reduceRegion(reducer=ee.Reducer.mean(), geometry=district_geometry, scale=5600)`). This yields spatially-averaged pollutant concentrations. The system then converts gas-phase concentrations (mol/m² for NO2, SO2) to mass concentrations (μg/m³) using molecular weights and assumes standard atmospheric pressure, acknowledging this introduces ~15% uncertainty documented in validation studies (Verhoelst et al., 2021).

The **fusion step** combines these modalities: districts with ≥1 ground station within 50km use IDW-weighted ground data as primary source, with satellite data serving as gap-filler for missing pollutants (TROPOMI provides O3 and CO, often absent from ground networks). Station-free districts rely exclusively on satellite-derived estimates. This adaptive strategy is implemented in `DistrictExposureService.calculate_district_exposure()`, which checks station availability via spatial query, branches to appropriate calculator, and stores results in the `DistrictExposure` model with `data_source` field tagged as 'ground', 'satellite', or 'fused'.

### Exposure Modeling: Population-Weighted Risk

Raw pollutant concentrations inadequately capture public health impact—10 μg/m³ of PM2.5 in a densely populated district poses greater aggregate risk than 50 μg/m³ in a sparsely populated area. The system implements population-weighted exposure calculation using WorldPop 2020 gridded population (1km resolution):

```python
exposure_index = (pollutant_concentration * population_density) / REFERENCE_POPULATION
```

For raster-based calculations (satellite data), this requires resampling operations: WorldPop's 100m native resolution is aggregated to Sentinel-5P's 5.6km using `reduceResolution(reducer=ee.Reducer.sum())` to preserve population totals, then element-wise multiplication with pollutant raster. The `calculate_exposure_image()` method in `GEEExposureService` performs this in Earth Engine's distributed environment:

```python
exposure_image = aqi_image.multiply(population_image).rename('exposure')
```

Zonal statistics over district boundaries then yield population-weighted exposure metrics: `exposure_stats = exposure_image.reduceRegion(geometry=district_polygon, reducer=ee.Reducer.mean().combine(ee.Reducer.sum()))`. The sum represents **total exposure burden** (person·AQI), while mean indicates **average individual exposure**.

For vector-based calculations (ground stations), the system computes population within circular buffer: `ST_Intersection(population_raster_polygon, ST_Buffer(station_location, radius))`, extracts pixel values via `rasterio.mask.mask()`, sums population, then weights pollutant value accordingly. This mixed raster-vector workflow demonstrates PostGIS-rasterio interoperability.

The AQI categorization (`'Good'`, `'Moderate'`, `'Unhealthy'`) follows US EPA breakpoints, with exposure categories used to populate the `DistrictExposure.pop_unhealthy`, `pop_hazardous` fields—critical for identifying vulnerable populations. This approach aligns with World Health Organization guidance on attributable health burden calculations.

---

## Key Implementation Details

### AI-Driven Structured Reporting

Report generation exemplifies the system's layered approach to transforming raw spatial statistics into actionable intelligence. The `generate_location_report_async()` task orchestrates a data pipeline:

1. **Data Aggregation Layer**: `TrendAnalyzer` service queries `station_readings` table for 14-day time series within user-specified radius, computes percentile statistics (p50, p75, p95), detects trend direction via linear regression, and constructs a structured dictionary with nested pollutant objects.

2. **Tabulation Layer**: `generate_ai_insights()` converts nested dictionaries into ReportLab `Table` objects with header rows, data rows, and formatted cells. Crucially, this step produces **machine-readable structured data**—not free-text summaries. Example:

```python
data_table = [
    ['Pollutant', 'Mean (μg/m³)', 'Max (μg/m³)', 'AQI', 'Trend'],
    ['PM2.5', f'{pm25_mean:.1f}', f'{pm25_max:.1f}', pm25_aqi, trend_arrow],
    ['NO2', f'{no2_mean:.1f}', f'{no2_max:.1f}', no2_aqi, trend_arrow]
]
```

3. **AI Narrative Layer** (optional, premium feature): The structured table is serialized to JSON and passed to LM Studio via OpenAI-compatible `/v1/chat/completions` endpoint with a GIS analyst persona prompt. The prompt explicitly instructs the model to provide: (a) geographic analysis with directional language ("pollution concentrated in north-eastern districts"), (b) source attribution based on pollutant mix (high NO2 + urban setting = traffic), (c) 48-hour forecast based on trend. This constrains the LLM's output to geospatially-contextualized insights rather than generic health advice.

4. **PDF Synthesis Layer**: ReportLab combines data tables, matplotlib-generated time series charts (saved as PNG via `BytesIO`, embedded in PDF), AI narrative paragraphs, and methodological appendix into a professional document. Crucially, the **structured tables are preserved as PDF table elements**, maintaining accessibility and screen reader compatibility.

This architecture demonstrates best practice: structured data remains the authoritative source of truth, with AI providing explanatory gloss rather than fabricating statistics. The fallback mechanism (when LM Studio is offline) simply omits the narrative section, proving the system degrades gracefully without AI augmentation.

### Performance Optimization: Geometry Simplification and Caching

Geospatial web applications confront the bandwidth-performance trade-off: full-resolution district boundaries (0.0001° precision) yield 2.8MB GeoJSON, unacceptable on 3G networks common in Pakistan. The `TieredGeometryMixin` implements Douglas-Peucker simplification tuned per user tier:

```python
SIMPLIFICATION_TOLERANCE = {
    'FREE': 0.01,      # ~1km at equator
    'BASIC': 0.005,    # ~500m
    'PREMIUM': 0        # No simplification
}
simplified_geometry = geometry.simplify(
    tolerance=tolerance, 
    preserve_topology=True  # Prevents polygon gaps
)
```

Critically, `preserve_topology=True` ensures adjacent districts remain topologically consistent—without this, simplified polygons can develop gaps or overlaps that break choropleth rendering. Empirical testing showed 0.01° tolerance reduces payload to ~450KB while maintaining visual fidelity at zoom levels <10.

Caching strategy follows data volatility principles:
- **Static GeoJSON** (district boundaries): 24-hour HTTP cache + 10-minute TanStack Query stale time
- **Dynamic readings** (station data): 1-minute stale time, background refetch every 5 minutes
- **GEE tiles**: 1-hour cache (tile URLs include date parameter as cache key)

Redis is configured as Django cache backend for session-based throttling counters (`cache.incr(f'throttle_{tier}_{user_id}')`) with 60-second TTL aligned to rate window. This prevents throttle limit gaming via rapid token refresh.

The frontend implements request deduplication: when multiple components subscribe to the same TanStack Query key (`queryKeys.geojson.districts('Punjab')`), Query's `queryCache` ensures only one network request fires, with results broadcast to all subscribers. This pattern is crucial for `UnifiedMap` where `DistrictsLayer`, `LayerControls`, and `DistrictDetailPanel` all consume the same district data.

---

## Critical Discussion: Architectural Debt and Refactoring Needs

### God Component Anti-Pattern: UnifiedMap.tsx

Frontend architectural audits reveal a critical maintainability concern: `UnifiedMap.tsx` spans 400+ lines with mixed responsibilities—map initialization, layer coordination, UI controls, state management, and event handling. This violates the Single Responsibility Principle and creates high coupling. Specifically:

- **Layer management logic** (toggle satellite layer, change opacity) is intertwined with **UI rendering** (legend, controls)
- **State synchronization** between local React state (8 `useState` calls prior to refactor) and Zustand store caused stale closure bugs
- **Event handlers** for province drill-down, district selection, and station popups reside in the same component, making unit testing impractical

**Mitigation steps taken**:
1. ✅ Migrated local state to Zustand store (`src/store/mapStore.ts`), eliminating prop drilling and enabling state persistence across route changes
2. ✅ Extracted UI controls into standalone components (`LayerControls`, `UnifiedLegend`, `DistrictDetailPanel`)
3. 🔄 **In Progress**: Decompose layer orchestration into `MapLayerCoordinator` hook that returns layer visibility state and toggle functions, reducing `UnifiedMap` to pure map rendering

**Remaining work**: Extract satellite layer date picker logic into `useSatelliteDatePicker()` hook, separate GEE exposure calculation into `useGEEDistrictExposure()` hook with internal `useQuery` call. Target: reduce `UnifiedMap` to <200 lines focused solely on MapLibre lifecycle management.

### Split State Legacy: Multiple Data Sources

The system exhibits "split state" stemming from evolutionary architecture: early implementation stored pre-calculated exposure metrics in `DistrictExposure` model (populated nightly via Django-Q scheduled task `calculate_all_districts`), while later premium feature introduced real-time GEE exposure calculation via `GET /api/v1/exposure/satellite/{district_id}/`. This creates two code paths:

**Path 1 (Database-backed)**:
```python
district_exposure = DistrictExposure.objects.filter(
    district=district, date=target_date
).first()
return district_exposure.mean_exposure_index
```

**Path 2 (GEE real-time)**:
```python
gee_service = GEEExposureService()
exposure_result = gee_service.calculate_exposure_for_district(
    district.geometry, target_date
)
return exposure_result.mean_exposure_index
```

This duplication complicates maintenance—bug fixes must be applied to both calculators—and creates semantic ambiguity: which value is "correct"? The frontend resolves this through tiered routing: BASIC users see database values (via `DistrictsLayer` with exposure GeoJSON), PREMIUM users see GEE-computed values (via `GEEExposureLayer` overlay). However, this coupling between business logic (tier) and data source is fragile.

**Proposed solution**: Implement **facade pattern** with `ExposureCalculator` interface:

```python
class ExposureCalculator(ABC):
    @abstractmethod
    def get_district_exposure(district, date) -> ExposureResult:
        pass

class CachedExposureCalculator(ExposureCalculator):
    def get_district_exposure(district, date):
        return DistrictExposure.objects.get(district=district, date=date)

class RealtimeExposureCalculator(ExposureCalculator):
    def get_district_exposure(district, date):
        return gee_service.calculate_exposure_for_district(...)
```

Views inject appropriate calculator based on user tier, abstracting data source from business logic. This follows Dependency Inversion Principle, enabling calculator swapping for testing (mock calculator) and future extensions (hybrid calculator that falls back to cache on GEE timeout).

### Incomplete Migration: Celery Artifacts

`celery.py.archived` file presence indicates migration from Celery to Django-Q, yet related comments in codebase (`reports/tasks.py`) still reference "Celery" in docstrings, creating developer confusion. Unused imports (`from celery import shared_task`) remain in legacy code paths. While functionally harmless (Django-Q tasks use `django_q.decorators.task` instead), this documentation drift violates the Principle of Least Astonishment—new developers may incorrectly assume Celery is the active task queue.

**Remediation**: Comprehensive grep audit (`rg "celery|Celery"`) followed by documentation rewrite, replacing all Celery references with Django-Q equivalents. Archive folder should include migration guide (`CELERY_TO_DJANGO_Q_MIGRATION.md`, already present) with explicit note in `README.md` directing developers to Django-Q for task implementation.

---

## Conclusion

The Air Risk system demonstrates how modern web GIS architectures can address real-world infrastructure deficits through intelligent hybrid methodologies. By combining cloud-based planetary-scale compute (Google Earth Engine) with traditional spatial databases (PostGIS), implementing tiered access models that balance resource allocation with user needs, and employing asynchronous processing to maintain system responsiveness under computational load, the platform provides district-level air quality exposure estimates for regions lacking ground monitoring—a critical capability for evidence-based policymaking in resource-constrained settings.

The technical decisions reflect geospatial engineering maturity: tolerance-based geometry simplification preserves topology while reducing bandwidth, zonal statistics with population weighting produces epidemiologically meaningful exposure metrics, and structured data tables enable AI augmentation without compromising data integrity. However, identified architectural debt—particularly component over-responsibility and split-state data paths—illustrates the tension between rapid feature development and long-term maintainability. Proposed refactorings (facade pattern, component decomposition) provide a roadmap for resolving these tensions while preserving the system's functional capabilities.

Future work should prioritize ground truthing satellite estimates through retrospective comparison with co-located ground stations, implementing anomaly detection to flag sensor malfunctions, and exploring machine learning models to fuse satellite-ground observations optimally weighted by spatial correlation structure. The established architecture provides a robust foundation for these enhancements.

---

**Word Count**: ~2,100 words  
**Target Audience**: Master's-level GIS examiners, Geospatial software architects  
**Date**: January 2025