 # Task: Implement Frontend Recommendations

## High Priority: Architecture & Safety
- [ ] **Architecture Cleanup**
- [x] Delete legacy `src/store/auth-store.ts` (conflicts with `authStore.ts`) <!-- id: 0 -->
    - [x] Move `src/modules/AqiRiskLayer.ts` to `src/features/map/logic/` <!-- id: 1 -->
    - [x] Delete empty `src/modules` directory <!-- id: 2 -->
- [ ] **Strict Typing**
    - [x] Refactor `src/api/districts.ts` to remove `any` and use precise types <!-- id: 3 -->
    - [x] Update `ExposureAnalysisPage.tsx` to use `queryKeys` factory <!-- id: 4 -->

## Medium Priority: Maintenance & Refactoring
- [ ] **Map Component Refactoring**
    - [x] Move `UnifiedMap.tsx` to `src/features/map/components/` <!-- id: 5 -->
    - [x] Create `src/features/map/components/DrilldownMap.tsx` (move from existing) <!-- id: 6 -->

## Low Priority: Optimization
- [x] **Build Tuning**
    - [x] Update `vite.config.ts` with rollup options for chunk splitting <!-- id: 7 -->
