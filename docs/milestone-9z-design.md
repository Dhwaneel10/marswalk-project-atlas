# Milestone 9Z Technical Design & Mathematical Formulation
## Mission Timeline Playback, Synchronized 3D Route Animation & Event Reconstruction

**Project:** MarsWalk 2.0 (NASA Space Apps Challenge)  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 19, 2026  
**Status:** Architecture & Mathematical Specification Approved

---

## 1. Executive Overview

Milestone 9Z implements an interactive, mathematically rigorous **Mission Timeline Playback & 3D Route Animation Engine** for MarsWalk 2.0. It bridges discrete spatial grid routing with continuous temporal mission operations, enabling engineers and competition evaluators to scrub, play, and inspect mission execution across authentic Jezero crater topography.

The system supports:
1. High-resolution time-parameterized trajectory sampling along planned A* paths.
2. Directed slope-cost weighted step timing: steeper segments naturally demand more time.
3. Rigorous stationary holds: marker coordinates remain pinned during scientific dwell and contingency delay periods while elapsed time advances.
4. Synchronized 3D vehicle marker translation in Three.js with terrain-conforming elevation and dynamic vertical exaggeration.
5. Multi-variant playback isolation: independent playback state for Nominal Baseline, Disrupted Detour, and Adaptive Replacement missions.
6. Responsive HUD controls (Play/Pause, Reset, Scrubber, 1x–100x Speed Multipliers) and live telemetry readouts.

---

## 2. Mathematical Formulation

### 2.1 Trajectory Parameterization & Leg Cost Allocation
Let a computed mission route leg $L$ consist of a sequence of $M+1$ 2D terrain grid cells:
$$\mathcal{P}_L = \left( v_0, v_1, v_2, \dots, v_M \right), \quad v_k = (r_k, c_k)$$

For each transition step $e_k = (v_k \to v_{k+1})$, the directed traversal cost $c_k = C(v_k \to v_{k+1})$ is determined by the authoritative Minetti-based slope cost model:
$$c_k = d_k \cdot \phi(\alpha_k)$$
where $d_k$ is the 3D Euclidean distance between grid cells and $\phi(\alpha_k) \ge 1.0$ is the metabolic/mechanical slope penalty for grade $\alpha_k$.

The total leg traversal cost is:
$$C_L = \sum_{k=0}^{M-1} c_k$$

The authoritative leg traverse duration from the mission timeline is $T_{L} = t_{\text{end}} - t_{\text{start}}$.
The continuous modeled time $\Delta t_k$ consumed traversing edge $e_k$ is assigned proportionally to its directed cost:
$$\Delta t_k = \begin{cases}
\dfrac{c_k}{C_L} \cdot T_L, & C_L > 0 \\
\dfrac{d_k}{D_L} \cdot T_L, & C_L = 0, D_L > 0 \\
\dfrac{T_L}{M}, & C_L = 0, D_L = 0
\end{cases}$$

This guarantees exact temporal conservation:
$$\sum_{k=0}^{M-1} \Delta t_k = T_L$$

The discrete arrival timestamp at grid cell $v_k$ is:
$$\tau_k = t_{\text{start}} + \sum_{j=0}^{k-1} \Delta t_j, \quad \tau_0 = t_{\text{start}}, \quad \tau_M = t_{\text{end}}$$

### 2.2 Stationary Periods (Dwell & Scenario Delay)
During a science dwell event $E_{\text{dwell}}$ of duration $T_{\text{dwell}}$ at target waypoint $w = (r_w, c_w)$:
$$\forall t \in [t_{\text{start}}, t_{\text{end}}]: \quad \mathbf{p}(t) = (r_w, c_w), \quad v(t) = 0, \quad D(t) = D(t_{\text{start}})$$

Similarly, for an operational scenario hold $E_{\text{delay}}$ of duration $T_{\text{delay}}$ at hold position $h = (r_h, c_h)$:
$$\forall t \in [t_{\text{start}}, t_{\text{end}}]: \quad \mathbf{p}(t) = (r_h, c_h), \quad v(t) = 0, \quad D(t) = D(t_{\text{start}})$$

### 2.3 Continuous Interpolation at Arbitrary Scrub Time $t$
Given arbitrary elapsed mission time $t \in [0, T_{\text{total}}]$:
1. Locate the active interval $[\tau_k, \tau_{k+1}]$ using binary search ($\mathcal{O}(\log N)$).
2. If the active interval is a stationary dwell or delay:
   $$\mathbf{p}(t) = v_k, \quad \text{elevation}(t) = z(v_k), \quad \text{distance}(t) = D_k$$
3. If the active interval is a traverse step $v_k \to v_{k+1}$:
   $$u = \frac{t - \tau_k}{\tau_{k+1} - \tau_k} \in [0, 1]$$
   $$\mathbf{p}(t) = (1 - u) v_k + u v_{k+1}$$
   $$\text{elevation}(t) = (1 - u) z(v_k) + u z(v_{k+1})$$
   $$\text{distance}(t) = (1 - u) D_k + u D_{k+1}$$
   $$\text{speed}(t) = \frac{d_k}{\Delta t_k}$$

### 2.4 Three.js 3D Coordinate Mapping
In the Mars Atlas Three.js scene, terrain position $(x, y, z)$ is rendered via `rcToLocalPos(r, c, elevation, exaggeration)`:
$$x = (c - c_{\text{origin}}) \cdot \Delta x_{\text{scale}}$$
$$z_{\text{three}} = (r - r_{\text{origin}}) \cdot \Delta y_{\text{scale}}$$
$$y_{\text{three}} = (\text{elevation} - z_{\text{min}}) \cdot \Delta z_{\text{scale}} \cdot \text{exaggeration} + y_{\text{offset}}$$
The vehicle marker mesh is positioned at $(x, y_{\text{three}} + \delta_{\text{clearance}}, z_{\text{three}})$ with $\delta_{\text{clearance}} = 1.8\,\text{m}$ (scaled) to ensure clear line-of-sight visibility above the terrain mesh and polyline tubes without clipping or z-fighting.

---

## 3. Architecture & Data Structures

### 3.1 Backend: `src/marswalk/core/mission_playback.py`
- `PlaybackSample`: Discrete timestamped point along the route with grid coordinates, elevation, slope, cumulative distance, instantaneous speed, and event tag.
- `PlaybackTimelineEvent`: Structured leg/dwell/delay interval with bounding coordinates, duration, cumulative distance bounds, and metadata.
- `MissionPlaybackModel`: Comprehensive serialization container containing all events, samples, waypoint records, and summary telemetry.
- `build_mission_playback_model(...)`: Authoritative builder supporting direct `RouteResult`, `MultiStopRouteResult`, or serialized route dictionaries.
- `interpolate_playback_state(...)`: Deterministic state evaluator for any query timestamp $t$.

### 3.2 API & Contracts
- Endpoint: `POST /api/mission/playback`
- Schema: `schemas/api/v1/mission-playback-response.schema.json`
- Contract Registry: Registered in `src/marswalk/api/contracts.py` as `"mission-playback-response"`.
- Service Layer: `mission_playback_api(...)` in `src/marswalk/api/service.py`.

### 3.3 Frontend: Three.js Integration & UI
- Vehicle Marker: Composite 3D mesh consisting of a metallic rover chassis cylinder, heading indicator cone, and pulsating point light beacon.
- Render Loop Integration: Evaluated inside `animate(time)` using delta-time advancement:
  $$\Delta t_{\text{sim}} = \Delta t_{\text{wall}} \cdot \mu_{\text{speed}}$$
  where $\mu_{\text{speed}} \in \{1, 5, 10, 25, 50, 100\}$.
- Multi-Variant Switching: Supports Nominal (`nominal`), Disrupted (`disrupted`), and Adaptive (`adaptive`) variants with zero cross-talk or geometry leakage.
