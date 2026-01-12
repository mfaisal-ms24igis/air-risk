# Frontend Code Audit and Improvement Suggestions

This document outlines a review of the Air Risk frontend codebase, highlighting areas for improvement in architecture, performance, type safety, and maintainability.

## 1. Executive Summary
The frontend codebase is built with a modern stack (React, TypeScript, Vite, Zustand, React Query) and shows evidence of advanced features like GEE integration and JWT authentication. However, the project suffers from architectural fragmentation, particularly in map-related components, and contains legacy/duplicate code that hinders maintainability. Addressing these organizational issues and cleaning up dead code is the highest priority.

## 2. Architecture and Code Organization
*Analysis of project structure, component separation, and state management.*

**Findings:**
-   **Inconsistent Feature Architecture:** The codebase uses multiple directories for similar purposes (`features`, `modules`, `components`). For example:
    -   `src/features/map` contains `DistrictDrilldownMap.tsx`.
    -   `src/components` contains `UnifiedMap.tsx`, `DashboardMap.tsx`, and `RiskMapLayer.tsx`.
    -   `src/modules` contains `AqiRiskLayer.ts`.
    -   This scattering makes it difficult to locate logic and understand the separation of concerns.
-   **Duplicate State Stores:** `src/store` contains both `authStore.ts` (the active, full implementation) and `auth-store.ts` (a likely deprecated mock). This creates confusion about the source of truth for authentication.
-   **God Components:** `UnifiedMap.tsx` in `components` is quite large (13KB) and appears to handle too many responsibilities (layer management, routing, UI controls), suggesting it should be decomposed.
-   **Cluttered Components Directory:** The root `components` directory contains business-specific components (`DashboardMap.tsx`) mixed with generic utilities (`ErrorBoundary.tsx`, `SplashScreen.tsx`).

**Recommendations:**
1.  **Adopt a Strict Feature-Based Structure:** Move all domain-specific logic (like Mapping, Reports, Auth) into `src/features`.
    -   `src/features/map`: Should contain `UnifiedMap`, `DistrictDrilldown`, `RiskMapLayer`, and related hooks/stores.
    -   `src/features/auth`: Should contain `authStore.ts`, login forms, and types.
2.  **Clean Up `src/components`:** Restrict this directory to truly generic, reusable UI components (Buttons, Inputs, Modals). Use `src/components/ui` for primitives.
3.  **Delete Legacy Code:** Remove `src/store/auth-store.ts` and `src/modules` (move `AqiRiskLayer` to `features/map`).

## 3. Type Safety and TypeScript Usage
*Review of strict mode compliance, usage of `any`, and interface definitions.*

**Findings:**
-   **Loosely Typed API Calls:** While the project uses TypeScript, there is a recurring pattern of bypassing type safety using `any`. specificically in `frontend/src/api/districts.ts` (`apiClient.get<any>`) and `ExposureAnalysisPage.tsx` (`(districtsData as any)`). This negates the benefits of TypeScript and leads to runtime errors (like the `districts.find` crash).
-   **Duplicate Type Definitions:** `src/types/index.ts` is a good entry point, but there appears to be overlap between `types/models.ts` and component-specific types.
-   **Good Query Keys:** The presence of `queryKeys` factory in `src/lib/query-client.ts` is excellent, but it is not consistently used across the application (e.g., `ExposureAnalysisPage` uses the hardcoded string `['districts']` instead of the factory).

**Recommendations:**
1.  **Ban `any`:** Enable `no-explicit-any` validation in ESLint and strictly type all API responses.
2.  **Enforce Query Key Factory:** Refactor all `useQuery` calls to use the `queryKeys` object from `src/lib/query-client.ts` to prevent cache mismatches.

## 4. Performance and Optimization
*Analysis of React Query usage, re-render avoidance, and bundle size considerations.*

**Findings:**
-   **Excellent React Query Config:** `src/lib/query-client.ts` is well-configured with tiered cache times (Static vs Realtime) and appropriate default settings for a GIS application (`refetchOnWindowFocus: false`).
-   **Basic Build Setup:** `vite.config.ts` lacks advanced build optimizations. There is no manual chunk splitting, gzip/brotli compression, or visualizer plugin. This may lead to a large initial bundle size given the heavy mapping libraries (MapLibre, Turf.js).
-   **Lazy Loading:** Route-based code splitting is implemented in `routes.tsx`, which is good.

**Recommendations:**
1.  **Optimize Build:** Configure `build.rollupOptions` in `vite.config.ts` to separate vendor chunks (React, MapLibre) from application code.
2.  **Enable Compression:** Add `vite-plugin-compression` to serve compressed assets.

## 5. UI/UX and Design System
*Consistency of styles, loading states, error handling, and component reusability.*

**Findings:**
-   **Tailwind Usage:** The project correctly uses Tailwind CSS via `globals.css` and utility classes, ensuring design consistency.
-   **Monolithic Map UI:** The `UnifiedMap` component likely bundles too much UI logic (panels, toggles, legend) into one file, making it hard to iterate on the UX without regression risks.

**Recommendations:**
1.  **Decompose Map UI:** Break down `UnifiedMap` into smaller, independent UI widgets (e.g., `<LayerControl />`, `<Legend />`, `<FilterPanel />`) composed in a layout.

## 6. Security and Best Practices
*Environment variable usage, authentication handling, and API security.*

**Findings:**
-   **Secure Defaults:** `apiClient.ts` correctly handles JWT tokens in interceptors.
-   **Secrets:** No hardcoded secrets were found in the sampled frontend code.

## 7. Recommendations (Prioritized)

### High Priority (Immediate Action)
1.  **Fix Architecture:** Delete `src/store/auth-store.ts` and legacy modules. Move feature logic to `src/features`.
2.  **Strict Typing:** audit `src/api` and remove `any` casts. Ensure `ExposureAnalysisPage` uses strict types.

### Medium Priority (Maintainability)
1.  **Refactor Map Components:** Decompose `UnifiedMap.tsx` and organize map components into `src/features/map/components`.
2.  **Standardize React Query:** Refactor all queries to use `queryKeys` factory.

### Low Priority (Optimization)
1.  **Vite Build Tuning:** Add chunk splitting and compression plugins.
