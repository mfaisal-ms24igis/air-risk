# Annex 'B' to Form TH-1
## Proposed Timeline for Research

---

## Rules/Regulation Awareness

**Are you aware of your last date to complete thesis (without Rector's extension)?**  
**Please mention date:** ________________

**Are you aware of the regulations and schedule of the University for MS programmes?**  
☐ Yes / ☐ No

**Are you aware of the plagiarism policy?**  
☐ Yes / ☐ No

**Have you read the HEC Policy on PG programmes?**  
☐ Yes / ☐ No

**Did you receive a copy of the PG Handbook?**  
☐ Yes / ☐ No

**Have you attended any MS/PhD thesis seminar?**  
☐ Yes / ☐ No

**If Yes, No of thesis/seminar:** ________________

---

## Proposed Timeline

| Ser | Activity | To be completed by (Date) |
|-----|----------|---------------------------|
| 1 | **Literature Review Completion**<br>• Review satellite-ground fusion methodologies<br>• Study Google Earth Engine applications<br>• Analyze exposure assessment frameworks<br>• Survey AI integration in environmental monitoring | [Month 1] |
| 2 | **Data Acquisition & Preprocessing**<br>• Download Sentinel-5P historical archive (2018-present)<br>• Establish OpenAQ API integration (370+ stations)<br>• Acquire WorldPop 2020 gridded population data<br>• Normalize Pakistan district boundary shapefiles to EPSG:4326 | [Month 2] |
| 3 | **Backend Architecture Development**<br>• Set up Django REST Framework with PostGIS database<br>• Configure Google Earth Engine service account authentication<br>• Implement user authentication with JWT tokens<br>• Develop RESTful API endpoints with Swagger documentation | [Month 3] |
| 4 | **Spatial Fusion Algorithm Implementation**<br>• Develop Inverse Distance Weighting (IDW) interpolator<br>• Implement zonal statistics extractor for Sentinel-5P<br>• Create adaptive fusion decision logic (50km threshold)<br>• Integrate quality filtering (QA values, cloud cover) | [Month 4] |
| 5 | **Exposure Assessment Module**<br>• Implement pixel-wise population-weighted exposure calculation on GEE<br>• Develop EPA AQI computation with breakpoint interpolation<br>• Create district-level aggregation and summary statistics<br>• Generate exposure burden metrics (person·AQI) | [Month 4] |
| 6 | **Bias Correction & Validation**<br>• Implement Linear Regression, RANSAC, GWR correctors<br>• Conduct k-fold cross-validation (k=5)<br>• Calculate performance metrics (R², RMSE, MAE, Bias)<br>• Compare corrected estimates against withheld ground truth | [Month 5] |
| 7 | **AI Report Generation Pipeline**<br>• Integrate LM Studio with Mistral-7B-Instruct model<br>• Develop structured data extraction (30-day time series, trends)<br>• Implement AI narrative generation with geographic context<br>• Create PDF synthesis using ReportLab with charts and tables | [Month 5] |
| 8 | **Frontend Development**<br>• Build React 18 application with TypeScript<br>• Integrate MapLibre GL for interactive mapping<br>• Implement tiered access controls (BASIC, PREMIUM, ENTERPRISE)<br>• Develop asynchronous task polling with TanStack Query | [Month 6] |
| 9 | **Performance Optimization**<br>• Implement Douglas-Peucker geometry simplification<br>• Configure Redis caching for API responses<br>• Set up TanStack Query stale-while-revalidate caching<br>• Create Docker containerization with docker-compose | [Month 6] |
| 10 | **System Testing & Validation**<br>• Conduct comprehensive API endpoint testing<br>• Perform ground-truth comparison with co-located stations<br>• Execute load testing (concurrent users, request throughput)<br>• Conduct user acceptance testing with domain experts | [Month 7] |
| 11 | **Documentation Preparation**<br>• Write technical design document (architecture, algorithms)<br>• Create API documentation with endpoint specifications<br>• Develop deployment guide (Docker, environment setup)<br>• Draft academic manuscript for journal submission | [Month 7] |
| 12 | **Thesis Writing - Core Chapters**<br>• Chapter 1: Introduction (background, problem statement, objectives)<br>• Chapter 2: Literature Review (existing research, gaps)<br>• Chapter 3: Methodology (data sources, algorithms, architecture)<br>• Chapter 4: Implementation (system design, technologies) | [Month 8] |
| 13 | **Thesis Writing - Results & Discussion**<br>• Chapter 5: Results (validation metrics, case studies)<br>• Chapter 6: Discussion (findings interpretation, limitations)<br>• Chapter 7: Conclusion (contributions, future work)<br>• Appendices (code snippets, API documentation, sample reports) | [Month 8] |
| 14 | **Thesis Defense Preparation**<br>• Create presentation slides (25-30 slides)<br>• Develop live demo videos (platform walkthrough)<br>• Compile anticipated questions and responses<br>• Practice defense presentation (3 rehearsals) | [Month 9] |
| 15 | **Final Thesis Submission**<br>• Incorporate supervisor feedback and revisions<br>• Format per NUST thesis guidelines (fonts, margins, citations)<br>• Run Turnitin plagiarism check (<15% similarity)<br>• Submit soft and hard copies to PGP Directorate | [Month 9] |

---

## Milestone Deliverables

### Month 3 Milestone: Backend Foundation
- Functional Django REST API with authentication
- PostGIS database with Pakistan district geometries
- Google Earth Engine integration test successful

### Month 5 Milestone: Core Algorithms
- Adaptive fusion algorithm validated
- Population-weighted exposure calculations operational
- Bias correction models with cross-validation metrics

### Month 6 Milestone: Complete Platform
- Full-stack application deployed locally
- Interactive map visualization functional
- AI-driven report generation working end-to-end

### Month 7 Milestone: Testing & Validation
- Ground-truth validation completed
- Performance benchmarks documented
- User acceptance testing report

### Month 9 Milestone: Thesis Submission
- Complete thesis document (100-150 pages)
- Academic manuscript draft submitted to journal
- Defense presentation ready

---

## Risk Mitigation Strategies

### Technical Risks
- **GEE API Rate Limits:** Implement exponential backoff, request batching
- **Satellite Data Gaps:** Fallback to ground-only estimates during outages
- **LLM Integration Failures:** Graceful degradation (reports without narratives)

### Timeline Risks
- **Development Delays:** Allocate 2-week buffer before each milestone
- **Data Acquisition Issues:** Begin downloads early, use cached datasets
- **Validation Challenges:** Identify alternative ground truth sources

### Resource Constraints
- **Computational Resources:** Utilize GEE cloud processing, optimize queries
- **Data Storage:** Implement database archival, compress historical data
- **Internet Connectivity:** Develop offline testing capabilities

---

**Student's Signature:** ___________________  
**Student Name:** [Your Name]  
**Regn No.:** [Your Registration Number]  
**Date:** December 24, 2025

**Supervisor's Signature:** ___________________  
**Supervisor Name:** [Supervisor Name]  
**Date:** ___________________

---

**Note:** Any change in the proposed timeline is to be intimated to the PGP Dte by submitting fresh Annex 'B' to TH-1.

---

**Document Version:** 1.0  
**Date Prepared:** December 24, 2025  
**Form Type:** TH-1 Annex B (Timeline)
