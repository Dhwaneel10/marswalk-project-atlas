# MarsWalk 2.0 — Milestone 10B Design Document
## Mid-Sortie Emergency Injection, Mission State Handoff & Live Adaptive Replanning

### 1. Executive Summary

Milestone 10B extends MarsWalk 2.0 from an offline route calculator and playback animator into an interactive, operational mission-response system. A user or flight controller can pause an active sortie along its planned trajectory in Jezero Crater, inject a simulated contingency (such as a rockfall corridor closure, mobility derating, operational hold, or target loss), capture the vehicle's exact instantaneous state without double-counting elapsed duration, compute a 3-way operational trade-off (Nominal Remaining vs. Disrupted Remaining vs. Adaptive Continuation), preview the spatial hazard footprint and detour route in the 3D Atlas, and seamlessly hand off execution to a newly computed continuation mission that resumes directly from the rover's interrupted coordinates.

### 2. State Handoff Architecture & Mathematical Rigor

#### 2.1 Instantaneous Rover State Capture (`MidSortieState`)
At interruption time $t_{\text{int}}$, the vehicle's position along the active route is determined by interpolating the verified playback model samples:
$$s(t_{\text{int}}) = \operatorname{Interpolate}(S, t_{\text{int}})$$
The captured state encapsulates:
- Subcell coordinates $[r, c]$ and grid cell $[r_{\text{cell}}, c_{\text{cell}}]$.
- Interpolated elevation $z_{\text{interp}}$ (m) and terrain slope $\theta_{\text{slope}}$ (deg).
- Traversal status: active leg, distance traversed $d_{\text{elapsed}}$, speed $v_{\text{inst}}$, and stationary flag (dwell or hold).
- Strict separation of completed target waypoints ($t_{\text{complete}} \le t_{\text{int}}$) from unvisited target waypoints ($t_{\text{complete}} > t_{\text{int}}$).

#### 2.2 Budget Deductibility Without Double-Counting
If a total operational budget $T_{\text{budget}}$ is specified for the sortie, the remaining operational budget $T_{\text{rem}}$ available for continuation from $t_{\text{int}}$ is computed strictly as:
$$T_{\text{rem}} = \max\left(0, T_{\text{budget}} - t_{\text{int}}\right)$$
Elapsed drive time, completed science dwell durations, and prior delays are not double-counted.

#### 2.3 Three-Way Sortie Continuation Trade-Off
When a simulated contingency event $\mathcal{E}$ is injected, the engine evaluates three parallel options:
1. **Nominal Remaining**: The remaining planned trajectory from $[r_{\text{cell}}, c_{\text{cell}}]$ across unvisited targets to destination, assuming nominal conditions.
2. **Disrupted Remaining**: The nominal remaining path evaluated against the contingency (e.g., checking for intersections with rockfall hazard cells, scaling traversal time by mobility deratings, or adding operational delay).
3. **Adaptive Continuation**: A re-optimized sequential multi-stop or direct return route originating at $[r_{\text{cell}}, c_{\text{cell}}]$, evading hazard footprints, dropping unavailable targets, adjusting for derated speeds, and strictly constrained by $T_{\text{rem}}$.

### 3. API Contract & Service Specification

- **Endpoint**: `POST /api/mission/continue`
- **Schema**: `schemas/api/v1/mission-continue-response.schema.json` (Draft 2020-12 compliant).
- **Core Engine**: `src/marswalk/core/mission_continuation.py`
  - `MidSortieState`: Frozen dataclass representing the state snapshot.
  - `capture_mid_sortie_state(...)`: Safe state extractor with bounds and NoData validation.
  - `plan_mission_continuation(...)`: Multi-stage replanner and recommendation synthesizer.
- **Recommendations**:
  - `continue_nominal`: Disruption is non-intersecting or negligible.
  - `continue_with_detour`: Adaptive path successfully detours around hazard within $T_{\text{rem}}$.
  - `drop_target_and_proceed`: One or more scientific targets dropped to preserve feasible return.
  - `abort_to_direct_baseline`: Direct emergency transit to recovery/base coordinates.
  - `unresolvable_critical_hazard`: Destination unreachable or vehicle stranded; no feasible path exists.

### 4. Playback & Visualization Integration

- **Continuation Playback Model**: Rebuilt from $t=0$ corresponding to the vehicle's captured position $[r, c]$, with elapsed distance reset to 0 m and completed event cues omitted.
- **3D Spatial Markers**:
  - Historical track rendered in muted slate (`#546E7A`).
  - Active hazard footprint rendered as a semi-transparent coral cylinder (`#FF5722`).
  - Adaptive continuation route rendered in high-contrast neon green (`#00E676`).
- **Seamless Handoff**: Applying continuation updates vehicle position, resets scrubber to 0, sets duration to $T_{\text{continuation}}$, and allows immediate playback resumption at custom speeds (1x to 100x).
