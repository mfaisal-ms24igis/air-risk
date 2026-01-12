# Implementation Plan - Frontend Improvements

## User Review Required
> [!WARNING]
> This plan involves deleting legacy files (`src/store/auth-store.ts`) and restructuring directories. While I have confirmed `authStore.ts` is the active store, please ensure no other parts of your system rely on the deprecated file.

## Proposed Changes

### Architecture Cleanup
#### [DELETE] [auth-store.ts](file:///e:/AIR%20RISK/frontend/src/store/auth-store.ts)
- Remove conflicting legacy auth store.

#### [MOVE] [AqiRiskLayer.ts](file:///e:/AIR%20RISK/frontend/src/modules/AqiRiskLayer.ts) -> [src/features/map/logic/AqiRiskLayer.ts](file:///e:/AIR%20RISK/frontend/src/features/map/logic/AqiRiskLayer.ts)
- Consolidate business logic into `features`.

### Strict Typing & API
#### [MODIFY] [districts.ts](file:///e:/AIR%20RISK/frontend/src/api/districts.ts)
- Remove `any` casts.
- Define strict interfaces for GeoJSON responses.

#### [MODIFY] [ExposureAnalysisPage.tsx](file:///e:/AIR%20RISK/frontend/src/pages/ExposureAnalysisPage.tsx)
- Use `queryKeys.geojson.districts()` instead of hardcoded string.
- Add strict type assertions for API responses.

## Verification Plan
### Automated Tests
- Run `npm run tsc` (if available) or `npx tsc --noEmit` to verify type safety after changes.
- Ensure build passes: `npm run build`.

### Manual Verification
1.  **Auth Flow:** Verify login/logout works (ensuring we didn't delete the wrong store).
2.  **Exposure Page:** Visit `/exposure-analysis` and verify districts load correctly without errors.
3.  **Map:** Verify AQI layers still load after moving `AqiRiskLayer.ts`.
