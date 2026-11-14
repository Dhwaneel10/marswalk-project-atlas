# Project Atlas — Milestone 13AA: Baseline & Configuration Manifest
## Stage 0 Freeze: System Baseline, Environment, Test Suite & API Verification

**Document Version:** 1.0.0  
**Classification:** Baseline Configuration & Reproducibility Record  
**Milestone:** 13AA — Atlas Assurance Grand Prix  
**Date:** 2026-11-07  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

### 1. Operating Environment & Toolchain

| Component | Verified Specification |
| :--- | :--- |
| **Operating System** | Microsoft Windows 11 Home Single Language (Build 10.0.26300, 64-bit) |
| **Python Runtime** | Python 3.12.4 (`.venv\Scripts\python.exe`) |
| **Package Manager** | pip 24.0 (`.venv\Scripts\pip.exe`) |
| **Test Framework** | pytest 9.1.1 (Plugins: `anyio-4.15.1`) |
| **Headless Browser Engine** | Google Chrome 1920×1080 Headless (`C:\Program Files\Google\Chrome\Application\chrome.exe`) |
| **Working Directory** | `E:\Python\NASA-Spaceapps\Marswalk` |
| **Repository State** | Branch `main`, uncommitted working tree preserved (no commits discarded) |

---

### 2. Available Services & Server Lifecycle

- **Atlas HTTP API Server**: Active background process on port 3000 (`http://127.0.0.1:3000`).
- **Startup Command**: `$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe scripts/run_atlas.py --port 3000 --no-browser`
- **Active Endpoints Verified (HTTP 200)**:
  - Core: `/api/health`, `/api/preflight`, `/api/plan_route`, `/api/gauntlet`, `/api/contingency/simulate`, `/api/scenario_comparison`, `/api/scenario_sensitivity`, `/api/export_briefing`, `/api/export_decision_pack`, `/api/bundle/verify`, `/api/bundle/replay`, `/api/mission/optimize`, `/api/mission/replan`, `/api/missions`, `/api/experiments`, `/api/experiments/compare`, `/api/imagery/status`, `/api/imagery/tile`, `/api/weather/current`, `/api/weather/sites`, `/api/weather/refresh`, `/api/mission/report`, `/api/mission/report/html`, `/api/mission/readiness`.
  - Planetary Network: `/api/planetary-network/overview`, `/api/planetary-network/topology`, `/api/planetary-network/contacts`, `/api/planetary-network/scenarios`, `/api/planetary-network/grand-prix/run`.
  - Planetary Foundry: `/api/planetary-foundry/overview`, `/api/planetary-foundry/catalogue`, `/api/planetary-foundry/fleet`, `/api/planetary-foundry/materials`, `/api/planetary-foundry/scenarios`, `/api/planetary-foundry/scenario/run`, `/api/planetary-foundry/grand-prix/run`.

---

### 3. Preflight Readiness Verification

Executed via `.\.venv\Scripts\python.exe scripts/preflight_check.py` on 2026-11-06 20:34:53 UTC:
- **Total Checkpoints**: 12/12 PASSED (0 warnings, 0 failures).
- **Execution Latency**: 424.5 ms.
- **Checkpoints**:
  1. Atlas HTTP API Server: PASSED (Online on port 3000).
  2. Web Frontend Assets: PASSED (Verified `index.html`, `app.js`, `style.css`).
  3. Planetary Feature Gazetteer: PASSED (2,061 IAU-approved Martian landmarks).
  4. Planetary Imagery Registry: PASSED (9 planetary imagery sources).
  5. Global Mars Basemap Layer: PASSED (Local Viking/MOLA basemap verified).
  6. Jezero CTX Optical Imagery: PASSED (Jezero optical orthomosaic verified).
  7. Jezero Crater 20m DTM: PASSED (GeoTIFF: 250×250 px at 20 m/px).
  8. Route Planning Engine (A*): PASSED (Smoke route 336m, 14 cells).
  9. Gauntlet Disruption & Recovery: PASSED ('Rockfall Detour' evaluated).
  10. Persistent Workspace Storage: PASSED (7 missions, 11 exports writable).
  11. Mission Briefing & Schema Validator: PASSED (Draft 2020-12 valid schema).
  12. Streamlit Tactical Control App: PASSED (`streamlit_app.py` verified).

---

### 4. Full Baseline Test Suite Execution Record

Command: `.\.venv\Scripts\pytest -q`
- Collected Test Files: 86 test modules in `tests/`.
- Total Collected Tests: 1,173.
- Result: **1,173 PASSED, 0 FAILED, 2 WARNINGS** (Deprecation warnings for matrix multiplication operator in campaign simulator).
- Execution Time: ~208 seconds.

---

### 5. Baseline Machine-Readable Configuration Manifest

The baseline manifest is generated and stored at `outputs/13aa_baseline_manifest.json`.
