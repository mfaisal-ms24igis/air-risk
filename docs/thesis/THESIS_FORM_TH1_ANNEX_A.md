# Annex 'A' to Form TH-1
## National University of Sciences & Technology
## MASTER'S THESIS WORK

---

**1. Name:** [Your Name]

**2. Regn No.** [Your Registration Number]

**3. Department / Discipline:** MS [Your Program - e.g., Environmental Informatics / GIS / Computer Science]

**4. Institute:** SEECS / SCEE / SINES

**5. Thesis Topic:** Hybrid Satellite-Ground Fusion Framework for Air Quality Exposure Assessment in Data-Sparse Environments: A Case Study of Pakistan

---

## Brief Description / Abstract

Pakistan's 240 million population is served by fewer than 100 operational air quality monitoring stations, creating critical data gaps that hinder public health interventions. This research develops a hybrid satellite-ground data fusion framework addressing monitoring infrastructure deficits through adaptive integration of Sentinel-5P TROPOMI observations, ground station networks (OpenAQ, Pakistan EPA), and WorldPop population grids.

The core methodological innovation is context-aware source selection: districts with adequate ground coverage (≥1 station within 50km) employ Inverse Distance Weighting interpolation, while sparse regions utilize satellite zonal statistics. A hybrid strategy (70% ground, 30% satellite) bridges transition zones. Population-weighted exposure calculations execute entirely on Google Earth Engine cloud infrastructure, avoiding multi-gigabyte data transfers while enabling real-time district assessments.

Key contributions include: (i) first adaptive fusion algorithm for heterogeneous monitoring networks, (ii) empirical validation of server-side exposure computation efficiency (hypothesis: >90% bandwidth reduction), (iii) geographically weighted bias correction with k-fold cross-validation under sparse-network conditions, and (iv) operational web platform deployment (Django REST + PostGIS + React 18) demonstrating research-to-practice translation. The system integrates local LLMs (LM Studio) for structured health reporting while preserving data sovereignty.

Validation employs co-located satellite-ground comparisons, stratified cross-validation (urban/rural), and performance metrics (R², RMSE, MAE). The framework directly supports Pakistan's National Air Quality Standards compliance monitoring and WHO guideline implementation, providing exposure estimates for 120+ previously unmonitored districts at <$500/month operational cost versus $15K+ per physical monitor.

---

## Level of Research Already Carried Out

**Satellite-Ground Data Fusion:**
Existing literature demonstrates three primary approaches: (i) statistical bias correction using collocated measurements (Di et al., 2019; Verhoelst et al., 2021), (ii) geographically weighted regression accommodating spatial heterogeneity (Xue et al., 2020), and (iii) machine learning ensembles (Chen et al., 2022). However, these methods uniformly assume dense station networks (>5 stations per 10,000 km²), rendering them inapplicable to data-sparse regions.

**Exposure Assessment:**
Population-weighted methodologies integrate demographic data with pollution fields (Tatem, 2017), but rely on chemical transport models (CMAQ, WRF-Chem) requiring extensive computational resources and meteorological inputs unavailable in developing countries.

**Cloud Computing in Environmental Monitoring:**
Google Earth Engine enables planetary-scale analysis (Gorelick et al., 2017), yet applications remain confined to land cover classification and epidemiological retrospection—not operational real-time surveillance.

**Critical Research Gaps:**
1. **Adaptive Fusion Under Data Scarcity:** No framework exists for context-aware source selection when station density varies spatially
2. **Computational Accessibility:** Existing methods require local processing of multi-gigabyte satellite datasets, prohibitive for resource-constrained institutions
3. **Operational Translation:** Academic fusion algorithms lack integration into deployable surveillance systems with API accessibility
4. **Uncertainty Quantification:** Limited research on propagating satellite product uncertainties through population exposure calculations

---

## Justification / Need / Relevance of Your Research

**Public Health Urgency:**
Air pollution causes 128,000 annual premature deaths in Pakistan (HEI, 2020), yet 120+ districts (75% of territory) lack monitoring infrastructure. Current data gaps prevent evidence-based health interventions, hospital preparedness planning, and vulnerable population targeting.

**Methodological Necessity:**
Existing fusion algorithms assume uniform station density, failing in heterogeneous networks characteristic of developing countries. No published framework addresses automatic source selection under variable data availability—a critical gap for scalable environmental surveillance.

**Computational Barrier:**
Traditional satellite-ground fusion requires downloading multi-gigabyte raster datasets, prohibitive for institutions with limited bandwidth/storage. Server-side processing remains underexplored in air quality literature despite proven efficacy in land-use studies (Gorelick et al., 2017).

**Policy Implementation Gap:**
Pakistan's NEQS mandate compliance monitoring, but enforcement remains infeasible without spatial data. Ministry of Climate Change identifies monitoring network expansion as priority, yet capital constraints ($15K-50K per reference monitor) delay implementation. This research demonstrates cost-effective satellite-based alternatives.

**Research Contribution:**
Advances environmental informatics by: (i) introducing adaptive fusion methodology, (ii) quantifying cloud computing efficiency gains for operational surveillance, (iii) validating bias correction under sparse networks, (iv) translating academic algorithms into deployable public health infrastructure.

---

## Objectives

### Research Questions
**RQ1:** Can adaptive data source selection improve exposure estimation accuracy in districts with heterogeneous station coverage compared to uniform fusion methods?

**RQ2:** What computational efficiency gains result from server-side population-weighting on cloud infrastructure versus traditional local processing?

**RQ3:** How do bias-corrected satellite estimates compare against ground truth in sparse-network contexts (k-fold validation)?

### Primary Objective
Develop and empirically validate a context-aware satellite-ground fusion framework that maintains estimation accuracy across spatial gradients of monitoring infrastructure density.

### Specific Research Objectives

**O1: Investigate Adaptive Fusion Performance** *(Addresses Gap 1)*
- Formulate decision algorithm for automatic source selection based on station proximity thresholds (candidate values: 25km, 50km, 75km)
- Compare IDW interpolation, satellite zonal statistics, and hybrid approaches using co-located validation
- Quantify accuracy degradation as function of station density (hypothesis: hybrid fusion maintains R²>0.65 even at <1 station/10,000 km²)

**O2: Optimize Server-Side Exposure Computation** *(Addresses Gap 2)*
- Implement pixel-wise population-weighting entirely within Google Earth Engine reducers
- Benchmark computational time and bandwidth consumption against conventional raster download workflows
- Test hypothesis: GEE approach reduces data transfer by >90% while maintaining equivalent numerical precision

**O3: Develop Spatial Bias Correction Framework** *(Addresses Gap 4)*
- Implement geographically weighted regression to model spatially-varying satellite-ground discrepancies
- Conduct k-fold cross-validation (k=5) with stratified sampling by urban/rural classification
- Quantify uncertainty propagation from satellite QA values through final exposure estimates

**O4: Deploy Operational Surveillance System** *(Addresses Gap 3)*
- Architect RESTful API providing real-time district exposure queries with <3s latency
- Integrate asynchronous task queue for computationally intensive operations (report generation, multi-temporal analysis)
- Validate system reliability under concurrent load (target: 100 simultaneous users)
- Deploy asynchronous task orchestration via Django-Q for computationally intensive operations

**7. Performance Optimization**
- Implement geometry simplification using Douglas-Peucker algorithms for optimized rendering
- Develop multi-tier caching strategy (Redis, TanStack Query) to reduce database load
- Optimize GEE workflows to avoid data downloads (tile URLs and statistics only)

---

**Document Version:** 1.0  
**Date Prepared:** December 24, 2025  
**Form Type:** TH-1 Annex A (Part 1)
