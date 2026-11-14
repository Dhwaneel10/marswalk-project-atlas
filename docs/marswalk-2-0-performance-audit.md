# MarsWalk 2.0 — Performance, Motion & Cartographic Architecture Audit
**Milestone 9C: Mars Atlas — Global Exploration, Cartographic Labels & Fluid Camera Navigation**
*Author: Principal Planetary Visualization Engineer, Geospatial Cartographer & Graphics Performance Architect*
*Date: October 2026*
*Target System: Three.js 3D Engine, WebGL, High-Resolution CTX Jezero Mesh, USGS Viking MDIM 2.1*

---

## 1. Executive Summary

MarsWalk 2.0 has successfully demonstrated a working 3D planetary globe and high-resolution $250 \times 250$ surface mesh driven by a live Python A* routing engine and Gauntlet stress-testing service. However, the application currently exhibits noticeable interaction flaws:
1. **Abrupt scene swapping:** The transition from space orbit to Jezero Crater abruptly unhides a detached flat rectangular mesh while instantly hiding the globe.
2. **Camera clipping & piercing:** Camera flights interpolate Cartesian $(x, y, z)$ linearly with `lerpVectors`, cutting straight through the core of the planetary sphere during orbital pans.
3. **Timer-based race conditions:** Flights rely on unmanaged `setTimeout()` calls that clash if a user initiates a new navigation or search action mid-flight.
4. **Complete geographic vacuum:** Beyond six local Jezero waypoints, Mars is completely barren of cartographic nomenclature, missing Olympus Mons, Valles Marineris, major impact basins, and historic rover landing sites.
5. **Redundant per-frame allocations:** Hot render paths recompute DOM strings and lack dirty flags for telemetry bars and label positions.

This audit provides a factual analysis of the current code and defines the architectural remedies for Milestone 9C.

---

## 2. Comprehensive Subsystem Audit

### 2.1 Camera Flight Controller & Orbit Transitions
**Observed Issue:** Linear interpolation (`THREE.Vector3.lerpVectors`) in Cartesian space causes the camera to plunge into or through the planet body when flying between distant planetary coordinates. Furthermore, concurrent flight commands corrupt animation states.

**Code Inspection (`web/app.js:958-977` & `1378-1386`):**
```javascript
function startCameraFlight(targetPos, targetLookAt, duration = 2500, onComplete = null) {
  flightStartPos.copy(camera.position);
  flightTargetPos.copy(targetPos);
  flightStartLookAt.copy(controls.target);
  flightTargetLookAt.copy(targetLookAt);
  flightStartTime = performance.now();
  flightDuration = duration;
  isFlying = true;
  controls.enabled = false;

  setTimeout(() => {
    isFlying = false;
    controls.enabled = true;
    camera.position.copy(targetPos);
    controls.target.copy(targetLookAt);
    if (onComplete) onComplete();
  }, duration);
}
```

**Root Causes:**
1. **Linear Chord vs. Spherical Great-Circle:** Lerping directly from $P_{\text{start}}$ to $P_{\text{target}}$ travels along a Euclidean chord connecting two points on a sphere. For angular distances $\Delta\sigma > 60^\circ$, the midpoint distance from the origin $r_{\text{mid}} = R \cos(\Delta\sigma/2)$ is significantly smaller than $R$, causing the camera to penetrate the terrain or atmosphere.
2. **Asynchronous Timeout De-synchronization:** `setTimeout` executes on the JS event loop independently of `requestAnimationFrame`. If the tab loses focus or drops frames, `setTimeout` fires prematurely or late, snapping the camera abruptly to the final position while `t < 1.0`.
3. **Non-Interruptible Controller:** If a user selects another destination or moves the mouse during an active flight, the previous `setTimeout` still executes, resetting controls and overwriting the camera target unexpectedly.

**Remediation Plan:**
- Implement a **Spherical Great-Circle / Slerp Camera Navigator** with altitude parabolic arc:
  $$r(t) = R_{\text{surface}} + h_{\text{start}} (1-t) + h_{\text{target}} t + h_{\text{apex}} \cdot 4t(1-t)$$
  The camera orientation and position smoothly follow great-circle geodesics with dynamic apex elevation clearing planetary obstacles.
- Replace `setTimeout` with pure time-based state updates inside `animate()` (`elapsed / duration >= 1.0`), allowing any flight to be smoothly interrupted by a new navigation command.

---

### 2.2 Globe-to-Jezero Scene Transitions & Coordinate Continuity
**Observed Issue:** Switching between Orbit View and Jezero Surface View looks like two disconnected applications glued together. The global planet instantly disappears, replaced by an isolated floating rectangle centered at $(0, 0, 0)$.

**Code Inspection (`web/app.js:1003-1020`):**
```javascript
function flyToJezeroView() {
  currentViewMode = 'jezero';
  marsGlobeGroup.visible = false;  // Immediate cut!
  jezeroSurfaceGroup.visible = true; // Immediate cut!
  const targetPos = new THREE.Vector3(0, 2400, 3200);
  const targetLookAt = new THREE.Vector3(0, 0, 0);
  startCameraFlight(targetPos, targetLookAt, 2500);
}
```

**Root Causes:**
1. **Disconnected Reference Frames:** The globe is centered at $(0,0,0)$ with radius $R=1000$ (representing $R_{\text{Mars}} = 3,396,190\text{ m}$, scale $1:3396.19$). The local CTX mesh is centered at $(0,0,0)$ in local meters ($5000 \times 5000\text{ m}$).
2. **Instant Binary Visibility Toggle:** Toggling `visible = false` on frame 0 destroys visual depth and spatial continuity.

**Remediation Plan:**
- Introduce a **Three-Stage Hierarchical Flight & Regional Handoff**:
  1. *Stage 1 (Orbital Alignment):* Camera smoothly arcs from current orbital position to sub-observer orbit directly above Jezero Crater ($77.44^\circ\text{E}, 18.44^\circ\text{N}$) facing down.
  2. *Stage 2 (Atmospheric Descent):* Camera glides downward toward the crater surface with altitude scaling while the globe remains visible.
  3. *Stage 3 (Regional Cross-fade / Workstation Lock):* As camera descends through regional ceiling, the high-resolution CTX surface mesh smoothly cross-fades into view, with clear $5.0 \times 5.0\text{ km}$ study boundaries displayed.
- The reverse flight seamlessly elevates the camera through the atmosphere before rotating out into global orbit.

---

### 2.3 Cartographic Nomenclature & Progressive Label Decluttering
**Observed Issue:** There are no geographic labels on Mars except the six local Jezero waypoints. There is no gazetteer, no search for famous Martian features (Olympus Mons, Valles Marineris, Gale Crater), and no landing site markers.

**Root Causes:**
1. Missing planetary nomenclature database.
2. Lack of a screen-space label projection and occlusion culling pipeline.

**Remediation Plan:**
- Ingest the official **USGS Gazetteer of Planetary Nomenclature (IAU WGPSN)** data for Mars into a compact, optimized JSON catalog (`web/data/mars_places.json`).
- Include verified robotic mission landing sites (Curiosity at Gale, Perseverance at Jezero, Spirit at Gusev, Opportunity at Meridiani, InSight at Elysium, Viking 1 & 2, Pathfinder).
- Implement a **Three-Tier Progressive Level-of-Detail (LOD) Label Engine**:
  - **Tier 1 (Global, Zoom < 1800):** Only prominent planetary landmarks (Olympus Mons, Valles Marineris, Hellas, major volcanic provinces, active rover landing sites). Max 12–16 labels.
  - **Tier 2 (Regional, 600 < Zoom < 1800):** Major named craters, planitiae, chasmata, terrae facing the camera.
  - **Tier 3 (Local, Zoom < 600):** Fine-scale craters, scientific waypoints, local traverse landmarks.
- **Occlusion Culling:** Compute dot product of feature surface normal $\hat{n}$ with camera vector $\hat{v}$. If $\hat{n} \cdot \hat{v} \le 0.1$, the feature is on the planetary limb or far side and is hidden instantly without DOM overhead.
- **Screen-Space Collision Detection:** Fast $O(N)$ bounding box decluttering prevents overlapping text tags.

---

### 2.4 Render Loop & DOM Update Performance
**Observed Issue:** Telemetry values (lon, lat, alt, pitch, FOV) are updated on mouse move and camera flights by directly modifying DOM `.textContent` strings, triggering layout recalculations.

**Remediation Plan:**
- Cache last rendered telemetry values and only mutate DOM when numeric display values change beyond resolution thresholds ($\Delta\text{lon} > 0.01^\circ$, $\Delta\text{alt} > 5\text{ m}$).
- Reuse `THREE.Vector3`, `THREE.Matrix4`, and `THREE.Frustum` allocations across animation cycles rather than creating garbage in hot loops.
- Implement an optional, lightweight developer diagnostic overlay (FPS, visible label count, memory stats).

---

## 3. Performance Acceptance Criteria for Milestone 9C

| Metric | Current State | Milestone 9C Target |
| :--- | :--- | :--- |
| **Global Planetary Landmarks** | 0 features (only Jezero) | $\ge 40$ authoritative USGS/IAU features + verified landing sites |
| **Label Decluttering** | None | 3-tier zoom LOD + planetary limb occlusion culling |
| **Search & Discovery** | Waypoint dropdown only | Real-time gazetteer search, category filters, autocomplete |
| **Camera Orbit Pan** | Linear chord (cuts into Mars) | Great-circle arc trajectory avoiding planetary intersection |
| **Globe-to-Jezero Transition** | Instant binary pop | Continuous multi-stage descent with atmospheric handoff |
| **Full Pytest Suite** | 106 passed | $\ge 115$ passed (all 106 preserved + catalog & coordinate tests) |
| **Live A\* & Gauntlet API** | Fully functional | 100% preserved and active on localhost:3000 |
