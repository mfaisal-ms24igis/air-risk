# Quick Improvements (In No Time)

Here are high-impact, low-effort improvements you can implement immediately to polish the **Air Risk** application.

## 1. Cleanup Legacy Code (Immediate)
**Time Estimate:** 5 minutes
**Impact:** High (Eliminates confusion and technical debt)

The codebase has a "split state" where legacy views coexist with the new refactored ones. Since `urls.py` already points to the new code, the old files are dead weight.

*   **Delete**: `backend/air_quality/views.py`
    *   *Why*: Contains buggy code referencing non-existent `pm10` fields.
*   **Delete**: `backend/air_quality/api/views.py`
    *   *Why*: Superseded by `views_refactored.py`.
*   **Action**:
    ```bash
    # Run in terminal
    rm backend/air_quality/views.py
    rm backend/air_quality/api/views.py
    # Optional: Rename refactored file to standard name
    mv backend/air_quality/api/views_refactored.py backend/air_quality/api/views.py
    # (Remember to update imports in urls.py if you rename)
    ```

## 2. Security Configuration Tweak (Quick Win)
**Time Estimate:** 2 minutes
**Impact:** High (Security)

Your `settings/base.py` currently has a hardcoded insecure default for `SECRET_KEY` and allows `DEBUG=True` by default via `env.bool`.

*   **Action**: Ensure your `.env` file exists and has a strong random key.
    ```bash
    # Generate a key
    python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
    ```
*   **Update**: Add this key to your `.env` file:
    ```
    SECRET_KEY=your-generated-key-here
    DEBUG=True # Keep True for dev, change to False for prod
    ```

## 3. Add Missing Documentation (Low Hanging Fruit)
**Time Estimate:** 10 minutes
**Impact:** Medium (Onboarding)

There is no `README.md` in the project root, making it hard for a new developer to know how to start the app.

*   **Action**: Create a root `README.md` with:
    *   **Prerequisites**: Python 3.10+, Node.js 18+, PostgreSQL + PostGIS.
    *   **Quick Start**:
        ```markdown
        # Air Risk Setup

        ## Backend
        1. `cd backend`
        2. `conda activate air_quality`
        3. `python manage.py runserver`

        ## Frontend
        1. `cd frontend`
        2. `npm install`
        3. `npm run dev`
        ```

## 4. Frontend Type Safety (Quick Fix)
**Time Estimate:** 10 minutes
**Impact:** Medium (Stability)

The frontend `UnifiedMap.tsx` and API services likely rely on inferred types or `any`.
*   **Action**: Create a centralized `types/api.ts` file that matches the `APIResponse` structure from the backend (`status`, `data`, `message`). This prevents "undefined" errors when the backend response wrapper changes.

## 5. Simplify Map Logic (Refactor Lite)
**Time Estimate:** 15 minutes
**Impact:** Medium (Maintainability)

`UnifiedMap.tsx` is large (~400 lines). You can quickly extract the `LEGEND_ITEMS` constant and the helper function `districtCenter` into separate files.

*   **Action**: Move `LEGEND_ITEMS` to `frontend/src/constants/map.ts`.
