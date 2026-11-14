# MarsWalk 2.0 — Milestone 9N Technical Audit
## State Assessment: Planetary Exploration, Waypoint Visibility, Mission Reset Controls, and Regional Imagery

**Project:** MarsWalk 2.0 — Project Atlas  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 18, 2026  
**Auditor:** Senior Frontend Engineer, Planetary GIS Engineer, Three.js Developer, and Mission Systems Verification Engineer  
**Baseline Test Status:** **201 passed in 79.25s** (100% pass rate)

---

## 1. Executive Summary & Problem Diagnosis

Milestone 9M introduced several architectural improvements:
- Scoped selectors preventing 3D terrain mesh destruction during vehicle mode switching.
- Preservation of intermediate research stops during traverse profile toggles.
- Dual-ceiling feasibility enforcement separating physical traverse distance from operational life-support time.
- Expansion of the mission inspector panel to 480px with a 4-tab structure.
- Entry points for four featured Martian destinations (Jezero Crater, Olympus Mons, Valles Marineris, Gale Crater).

However, live browser interaction surfaced three high-priority functional limitations:

1. **Disappearance of Local Waypoint Labels:**
   - **Symptom:** Upon entering the Jezero Crater local 3D workstation, only the departure and destination waypoints appeared; the other 10 candidate scientific research waypoints were missing.
   - **Root Cause:** In `web/app.js`, `buildWaypointBeacons()` and `updateJezeroLabels()` conditioned waypoint visibility on:
     ```javascript
     const showAll = chkShowAllWaypoints ? chkShowAllWaypoints.checked : false;
     const isMissionActive = Boolean(activeRoutePath && activeRoutePath.length > 0);
     if (!showAll && isMissionActive && !isRelevant) { return; }
     ```
     At application startup, `updateRoutePolyline('conservative')` immediately assigned the precomputed baseline route to `activeRoutePath`. Consequently, `isMissionActive` was `true` from the moment the Jezero workstation initialized. Because `#chkShowAllWaypoints` defaulted to `false` (unchecked), all unselected waypoints were immediately filtered out. Furthermore, the toggle control was an obscure checkbox located at the bottom of the Expedition Budget card in Tab 1, making it difficult for users to discover.

2. **Absence of Dedicated Clear and Reset Controls:**
   - **Symptom:** Users could not clear the departure endpoint, clear the destination endpoint, or reset the mission to a clean, empty planning state.
   - **Root Cause:** In `web/index.html` and `web/app.js`, the only reset affordance was `#btnResetPlanning`, which executed:
     ```javascript
     function resetPlanning() {
       customStart = { row: 117, col: 157, name: 'Octavia Landing (117, 157)' };
       customGoal = { row: 66, col: 128, name: 'Delta Rim Overlook (66, 128)' };
       activeRoutePath = missionData.routes[currentProfile].path_rc;
       drawLiveRoute(activeRoutePath, currentProfile);
     }
     ```
     This function hardcoded a reset back to the default endpoints and immediately drew the default route polyline. There were no actions to clear start independently, clear destination independently, swap endpoints, or clear active mission state without destroying saved workspaces.

3. **Regional Imagery Provenance & Verification:**
   - **Symptom:** The four featured destinations were presented on the landing page, but their regional optical assets varied significantly in source resolution and provenance. Specifically, Valles Marineris previously relied on a cropped raster from the global Viking basemap (`mars_viking_color_fallback.jpg`) rather than genuine high-resolution CTX imagery.
   - **Resolution:** NASA Mars Trek WMTS was queried, confirming that genuine MRO CTX tiles for `SE_Marineris_CTX_BlockAdj_dd` (Level 6, rows [38, 39], cols [45, 46]) are available. Fetching and stitching these tiles upgrades Valles Marineris to genuine $6\text{ m/px}$ CTX optical data.

---

## 2. Inventory of Affected Components

### 2.1 Frontend Files
- `web/index.html`:
  - Replace `#chkShowAllWaypoints` with a prominent segmented pill control (`All Locations` vs `Mission Locations Only`).
  - Add explicit `Clear Start` (`#btnClearStart`) and `Clear Destination` (`#btnClearGoal`) buttons to the Departure and Destination summary rows.
  - Add `Swap Endpoints` (`#btnSwapEndpoints`) affordance between departure and destination.
  - Add a dedicated, safe `Reset Mission` (`#btnResetMission`) button with confirmation handling.
- `web/styles.css`:
  - Styles for `.visibility-pills`, `.visibility-pill.active`.
  - Styles for `.endpoint-clear-btn` and `.endpoint-swap-btn`.
  - Styles for `.btn-reset-mission` and confirmation modals.
  - Distinguishable visual styling for Start (Green glow), Destination (Cyan diamond), Intermediate Stops (Amber beacon), and Unselected Catalog Waypoints (Sky blue pin).
- `web/app.js`:
  - Default Jezero exploration mode to `All Locations` on entry.
  - Provide `setVisibilityMode('all' | 'mission')` with reactive DOM updates.
  - Implement `clearStart()`, `clearGoal()`, `swapEndpoints()`, and `resetMission()`.
  - Ensure clearing endpoints removes 3D markers, clears the route line, invalidates telemetry, sets feasibility badge to a waiting state, and disables the calculate route button.
  - Retain safety guarantee: `resetMission()` must never delete saved missions or historical experiments.
- `web/data/mars_imagery_registry.json`:
  - Accurate spatial bounds, resolution, provenance, and elevation capability disclosures for all four featured destinations.
- `scripts/prepare_regional_imagery.py`:
  - Add NASA Mars Trek WMTS fetch and stitch pipeline for Valles Marineris `SE_Marineris_CTX_BlockAdj_dd`.

---

## 3. Baseline Verification

The existing automated test suite was executed in `.venv`:
- Command: `.\.venv\Scripts\python.exe -m pytest -q`
- Result: **201 passed in 79.25s**
- Status: Baseline fully operational with zero failing tests.
