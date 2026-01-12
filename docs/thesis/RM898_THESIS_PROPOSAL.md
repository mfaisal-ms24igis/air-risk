# NATIONAL UNIVERSITY OF SCIENCES & TECHNOLOGY
## MASTER'S THESIS WORK
### Research Methodology (RM-898) Term Assignment

---

## STUDENT INFORMATION

**Name:** Muhammad Usman Faisal  
**Registration No.:** 00000498120  
**Program:** MS Geographic Information Systems  
**Institute:** IGIS (Institute of Geographical Information Systems)  
**School:** SCEE (School of Civil and Environmental Engineering)  
**Current Semester:** Fall 2025  
**Credit Hours Completed:** 18.0 (as of Spring 2025)  
**CGPA:** 3.75

---

## COURSE WORK COMPLETED

### Fall 2024 (9.0 CH)

| Course Code | Course Title | Credit Hours | Grade |
|-------------|--------------|--------------|-------|
| GIS-XXX | Advanced Geographic Information Systems | 3.0 | A |
| GIS-XXX | Advanced Geodatabase and Programming | 3.0 | A |
| GIS-XXX | Advanced Remote Sensing and Digital Image Processing | 3.0 | A |

### Spring 2025 (9.0 CH)

| Course Code | Course Title | Credit Hours | Grade |
|-------------|--------------|--------------|-------|
| GIS-XXX | Spatial Decision Support System | 3.0 | B |
| GIS-XXX | Spatial Analysis and Modeling | 3.0 | A |
| GIS-XXX | GIS in Agriculture and Natural Resources | 3.0 | B+ |

### Fall 2025 (In Progress - 8.0 CH)

| Course Code | Course Title | Credit Hours | Status |
|-------------|--------------|--------------|--------|
| GIS-838 | Spatial Hydrology | 3.0 | In Progress |
| RM-898 | Research Methodology | 2.0 | In Progress |
| GIS-874 | Web GIS | 3.0 | In Progress |

**Total Credits to Date:** 26.0 CH

---

## PROPOSED THESIS TOPIC

**Hybrid Satellite-Ground Fusion Framework for Air Quality Exposure Assessment in Data-Sparse Environments: A Case Study of Pakistan**

---

## ABSTRACT

Pakistan's 240 million population is served by fewer than 100 operational air quality monitoring stations, creating critical data gaps that hinder public health interventions. This research develops a hybrid satellite-ground data fusion framework addressing monitoring infrastructure deficits through adaptive integration of Sentinel-5P TROPOMI observations, ground station networks (OpenAQ, Pakistan EPA), and WorldPop population grids.

The core methodological innovation is context-aware source selection: districts with adequate ground coverage (≥1 station within 50km) employ Inverse Distance Weighting interpolation, while sparse regions utilize satellite zonal statistics. A hybrid strategy (70% ground, 30% satellite) bridges transition zones. Population-weighted exposure calculations execute entirely on Google Earth Engine cloud infrastructure, avoiding multi-gigabyte data transfers while enabling real-time district assessments.

Key contributions include: (i) first adaptive fusion algorithm for heterogeneous monitoring networks, (ii) empirical validation of server-side exposure computation efficiency (hypothesis: >90% bandwidth reduction), (iii) geographically weighted bias correction with k-fold cross-validation under sparse-network conditions, and (iv) operational web platform deployment (Django REST + PostGIS + React 18) demonstrating research-to-practice translation. The system integrates local LLMs (LM Studio) for structured health reporting while preserving data sovereignty.

Validation employs co-located satellite-ground comparisons, stratified cross-validation (urban/rural), and performance metrics (R², RMSE, MAE). The framework directly supports Pakistan's National Air Quality Standards compliance monitoring and WHO guideline implementation, providing exposure estimates for 120+ previously unmonitored districts at <$500/month operational cost versus $15K+ per physical monitor.

---

## LITERATURE REVIEW

### Satellite-Ground Data Fusion

Existing literature demonstrates three primary approaches: (i) statistical bias correction using collocated measurements (Di et al., 2019; Verhoelst et al., 2021), (ii) geographically weighted regression accommodating spatial heterogeneity (Xue et al., 2020), and (iii) machine learning ensembles (Chen et al., 2022). However, these methods uniformly assume dense station networks (>5 stations per 10,000 km²), rendering them inapplicable to data-sparse regions.

### Exposure Assessment

Population-weighted methodologies integrate demographic data with pollution fields (Tatem, 2017), but rely on chemical transport models (CMAQ, WRF-Chem) requiring extensive computational resources and meteorological inputs unavailable in developing countries.

### Cloud Computing in Environmental Monitoring

Google Earth Engine enables planetary-scale analysis (Gorelick et al., 2017), yet applications remain confined to land cover classification and epidemiological retrospection—not operational real-time surveillance.

### Critical Research Gaps

Four critical gaps emerge from the literature. First, no framework exists for context-aware source selection when station density varies spatially—existing methods uniformly apply single fusion strategies regardless of local data availability. Second, computational accessibility remains problematic as current approaches require local processing of multi-gigabyte satellite datasets, prohibitive for resource-constrained institutions in developing countries. Third, academic fusion algorithms lack integration into deployable surveillance systems with API accessibility, remaining confined to retrospective research studies. Fourth, limited research addresses uncertainty quantification in propagating satellite product uncertainties through population exposure calculations, undermining confidence in derived health risk estimates.

---

## RESEARCH JUSTIFICATION

Air pollution causes 128,000 annual premature deaths in Pakistan (Health Effects Institute, 2020), yet 120+ districts comprising 75% of national territory lack any monitoring infrastructure. These data gaps critically impair evidence-based health interventions, hospital preparedness planning, and vulnerable population targeting. The methodological necessity arises from existing fusion algorithms that assume uniform station density, systematically failing in heterogeneous networks characteristic of developing countries. No published framework addresses automatic source selection under variable data availability—a critical gap for scalable environmental surveillance.

Computational barriers further constrain implementation. Traditional satellite-ground fusion workflows require downloading multi-gigabyte raster datasets, prohibitive for institutions with limited bandwidth and storage infrastructure. Server-side processing remains underexplored in air quality literature despite demonstrated efficacy in land-use studies (Gorelick et al., 2017). Policy implementation gaps compound these challenges: Pakistan's National Environmental Quality Standards mandate compliance monitoring, yet enforcement remains infeasible without spatially comprehensive data. The Ministry of Climate Change identifies monitoring network expansion as priority, but capital constraints of $15,000-$50,000 per reference-grade monitor delay implementation.

This research advances environmental informatics through four contributions: introducing adaptive fusion methodology for heterogeneous networks, quantifying cloud computing efficiency gains for operational surveillance, validating bias correction under sparse monitoring conditions, and translating academic algorithms into deployable public health infrastructure. The work demonstrates cost-effective satellite-based alternatives addressing both methodological and practical barriers to air quality surveillance in resource-constrained settings.

---

## RESEARCH QUESTIONS

**RQ1:** Can adaptive data source selection improve exposure estimation accuracy in districts with heterogeneous station coverage compared to uniform fusion methods?

**RQ2:** What computational efficiency gains result from server-side population-weighting on cloud infrastructure versus traditional local processing?

**RQ3:** How do bias-corrected satellite estimates compare against ground truth in sparse-network contexts (k-fold validation)?

**RQ4:** Does operational deployment maintain real-time performance (<3s query latency) under concurrent load (100+ users)?

---

## RESEARCH OBJECTIVES

### Primary Objective
Develop and empirically validate a context-aware satellite-ground fusion framework that maintains estimation accuracy across spatial gradients of monitoring infrastructure density.

### Specific Objectives

**Objective 1: Investigate Adaptive Fusion Performance** (addresses Gap 1, RQ1). This objective formulates a decision algorithm for automatic source selection based on station proximity thresholds, comparing candidate values of 25km, 50km, and 75km radii. The research will compare Inverse Distance Weighting interpolation, satellite zonal statistics, and hybrid approaches through co-located validation against withheld ground truth. Accuracy degradation will be quantified as a function of station density to test the hypothesis that hybrid fusion maintains R²>0.65 even at densities below 1 station per 10,000 km².

**Objective 2: Optimize Server-Side Exposure Computation** (addresses Gap 2, RQ2). This objective implements pixel-wise population-weighting entirely within Google Earth Engine reducers, avoiding local data downloads. Computational time and bandwidth consumption will be benchmarked against conventional raster download workflows to test the hypothesis that the GEE approach reduces data transfer by >90% while maintaining equivalent numerical precision.

**Objective 3: Develop Spatial Bias Correction Framework** (addresses Gap 4, RQ3). This objective implements geographically weighted regression to model spatially-varying satellite-ground discrepancies, accounting for urban-rural heterogeneity in measurement bias. K-fold cross-validation (k=5) with stratified sampling by urban/rural classification will assess model performance. Uncertainty propagation from satellite QA values through final exposure estimates will be quantified to provide confidence intervals on district-level assessments.

**Objective 4: Deploy Operational Surveillance System** (addresses Gap 3, RQ4). This objective architects a RESTful API providing real-time district exposure queries with <3 second latency requirements. An asynchronous task queue will handle computationally intensive operations including report generation and multi-temporal analysis. System reliability will be validated under concurrent load conditions targeting 100 simultaneous users to ensure production-grade performance.

---

## RESEARCH METHODOLOGY

### Data Sources

The research integrates three primary data sources. Satellite observations derive from Sentinel-5P TROPOMI Level-2 products providing NO₂, SO₂, CO, and O₃ concentrations at 1.1km native resolution. All satellite data processing occurs on Google Earth Engine cloud infrastructure to avoid multi-gigabyte local downloads. Quality filtering applies thresholds of QA value >0.5 and cloud cover <30% to ensure measurement reliability.

Ground monitoring data integrate two networks: the OpenAQ API version 3 providing access to 370+ stations across Pakistan with 5-minute to 1-hour temporal resolution, and Pakistan EPA's real-time monitoring network. A validation subset comprising co-located stations enables algorithm testing through independent ground truth comparison.

Population exposure weighting employs WorldPop 2020 UN-adjusted gridded population density at 1km resolution, aligned with satellite data resolution. Administrative boundaries derive from Pakistan Bureau of Statistics shapefiles normalized to EPSG:4326 coordinate reference system, encompassing 160+ district polygons.

### Algorithmic Framework

**1. Adaptive Fusion Decision Logic:**
```
FOR each district:
    station_count = count_stations_within_radius(50km)
    IF station_count ≥ 1:
        estimate = IDW_interpolation(stations, power=2)
    ELSE IF satellite_data_available:
        estimate = zonal_statistics(sentinel5p_composite)
    ELSE:
        estimate = hybrid_fusion(0.7*ground + 0.3*satellite)
    END IF
END FOR
```

**2. Population-Weighted Exposure:**
- Server-side calculation on Google Earth Engine
- Formula: `exposure = (concentration × population_density) / REF_POP`
- District aggregation: `total_burden = Σ(pixel_exposure × pixel_population)`

**3. Bias Correction:**
- Geographically Weighted Regression (GWR) for spatial non-stationarity
- Training on co-located satellite-ground pairs
- k-fold cross-validation (k=5, stratified by urban/rural)

### Validation Strategy

Model performance assessment employs four metrics: R² (coefficient of determination) quantifying variance explained, RMSE (Root Mean Square Error) measuring average prediction error magnitude, MAE (Mean Absolute Error) providing robust error estimates less sensitive to outliers, and bias calculated as mean residuals indicating systematic over- or under-estimation.

Three complementary validation approaches ensure robustness. Leave-one-out cross-validation addresses sparse station scenarios where traditional k-fold partitioning is infeasible. Temporal validation trains models on 2018-2023 data and tests on 2024 observations to assess temporal transferability. Spatial validation withholds entire districts from training to evaluate performance in unmonitored regions—the primary use case for the framework.

### System Architecture

The backend architecture employs Django 4.2 with Django REST Framework providing RESTful API endpoints. Spatial data management utilizes PostgreSQL 14 with PostGIS 3.3 extension enabling GIST spatial indexing for efficient geometric queries. Asynchronous task orchestration through Django-Q handles computationally intensive operations including report generation and multi-temporal analyses. Redis provides API response caching and request throttling to optimize performance under load.

The frontend implements React 18 with TypeScript 5.x for type-safe component development. Interactive mapping capabilities derive from MapLibre GL JS providing WebGL-accelerated rendering of district geometries and satellite tile layers. TanStack Query version 5 manages server state with automatic caching, background refetching, and optimistic updates.

Deployment architecture utilizes Docker containerization ensuring reproducible environments across development and production. The RESTful API exposes endpoints documented via Swagger UI conforming to OpenAPI 3.0 specification. JWT-based authentication implements tier-based access controls (BASIC, PREMIUM, ENTERPRISE) balancing computational resource allocation across user segments.

---

## PROPOSED TIMELINE

**Total Duration:** 4 months (January 2026 - April 2026)  
**Thesis Submission Deadline:** April 30, 2026

| Month | Activity | Deliverables |
|-------|----------|--------------|
| **Jan 2026** | Literature review; data acquisition; backend setup | Annotated bibliography; Django REST API with PostGIS; GEE integration |
| **Feb 2026** | Adaptive fusion algorithms; exposure framework; bias correction | IDW/zonal statistics modules; population-weighted exposure on GEE; GWR implementation |
| **Mar 2026** | Frontend development; AI pipeline; system testing | React app with MapLibre GL; LM Studio integration; validation results; load testing |
| **Apr 2026** | Documentation; thesis writing; defense preparation | Complete thesis document (Chapters 1-7); presentation slides; final submission |

**Weekly Breakdown:**

**January 2026 (Weeks 1-4):**
- Week 1: Literature review, data downloads
- Week 2-3: Django backend, PostGIS database setup
- Week 4: Google Earth Engine service integration

**February 2026 (Weeks 5-8):**
- Week 5: IDW interpolation and satellite zonal statistics
- Week 6: Hybrid fusion logic and exposure calculations
- Week 7: GWR bias correction implementation
- Week 8: k-fold cross-validation testing

**March 2026 (Weeks 9-12):**
- Week 9: React frontend with MapLibre GL
- Week 10: AI report generation and PDF synthesis
- Week 11: System integration and performance optimization
- Week 12: Comprehensive testing and validation

**April 2026 (Weeks 13-16):**
- Week 13: Results analysis and documentation
- Week 14-15: Thesis writing (all chapters)
- Week 16: Defense presentation preparation and final submission

**Key Milestones:**
- End of January: Backend foundation operational
- End of February: Core algorithms validated
- End of March: Complete platform deployed and tested
- April 30, 2026: Thesis defense and submission

---

## RELEVANCE TO PAKISTAN

The research addresses Pakistan's 128,000 annual air pollution deaths by providing exposure data for 120+ previously unmonitored districts. This spatial coverage enables targeted health interventions, hospital resource planning based on pollution forecasts, and vulnerable population identification for proactive care delivery. The framework directly supports National Environmental Quality Standards compliance monitoring and Clean Air Action Plan implementation, providing evidence base for EPA enforcement activities in regions lacking ground infrastructure.

Technological advancement emerges through demonstration of cloud-native geospatial platforms using open-source technologies including PostGIS, MapLibre GL, and Django, reducing dependency on proprietary solutions while fostering local capacity in environmental informatics. Local LLM deployment ensures data sovereignty—sensitive health information remains within national computational infrastructure rather than external cloud services.

Regional scalability extends the framework's impact beyond Pakistan to Bangladesh, Afghanistan, and Nepal—SAARC nations facing similar monitoring deficits. The work contributes to Sustainable Development Goal 3.9 (reduce deaths from air pollution) and Goal 11.6 (reduce urban environmental impact). Operational cost of <$500 per month versus $15,000-$50,000 per physical monitor represents 97% cost reduction, enabling nationwide coverage previously infeasible under capital budget constraints.

---

## EXPECTED OUTCOMES

The research delivers four primary academic contributions: a novel adaptive fusion algorithm for heterogeneous monitoring networks, empirical validation of server-side exposure computation efficiency under sparse-network conditions, a spatial bias correction framework with explicit uncertainty quantification, and demonstration of research-to-practice translation through operational system deployment.

Practical deliverables include a production-ready web platform with RESTful API accessible to third-party developers, district-level exposure estimates for all 160+ Pakistan districts filling critical data gaps, automated report generation integrating AI-driven health narratives with structured statistical tables, and an open-source codebase released under MIT license via GitHub enabling reproducibility and extension by other researchers.

Publication targets include a primary journal manuscript submitted to *International Journal of Environmental Research and Public Health* (Impact Factor: 4.614) and secondary conference presentation at the American Geophysical Union Fall Meeting or IEEE International Geoscience and Remote Sensing Symposium. The societal impact encompasses 100% spatial coverage filling the 120-district monitoring gap, real-time exposure data supporting public health decision-making, and evidence base for environmental compliance monitoring and policy formulation at national and provincial levels.

---

## REFERENCES

Chen, Z., et al. (2022). Machine learning ensemble methods for air quality prediction. *Environmental Science & Technology*, 56(8), 4523-4534.

Di, Q., et al. (2019). An ensemble-based model of PM2.5 concentration across the contiguous United States with high spatiotemporal resolution. *Environment International*, 130, 104909.

Gorelick, N., et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. *Remote Sensing of Environment*, 202, 18-27.

Health Effects Institute (2020). *State of Global Air 2020*. Special Report. Boston, MA.

Tatem, A. J. (2017). WorldPop, open data for spatial demography. *Scientific Data*, 4, 170004.

Verhoelst, T., et al. (2021). Ground-based validation of the Copernicus Sentinel-5P TROPOMI NO₂ measurements. *Atmospheric Measurement Techniques*, 14, 481-510.

World Bank (2020). *The Cost of Air Pollution in Pakistan*. Washington, DC: World Bank Group.

Xue, T., et al. (2020). Estimating spatiotemporal variation in ambient ozone exposure during 2013-2017 using a data-fusion model. *Environmental Science & Technology*, 54(23), 14877-14888.

---

## SIGNATURE

**Student:**  
Muhammad Usman Faisal  
Registration No.: 00000498120  
Date: December 24, 2025

**Course Instructor:**  
Research Methodology (RM-898)  
Fall 2025

---

**Document Version:** 1.0  
**Submission Date:** December 24, 2025  
**Course:** RM-898 Research Methodology  
**Assignment:** Term Thesis Proposal

