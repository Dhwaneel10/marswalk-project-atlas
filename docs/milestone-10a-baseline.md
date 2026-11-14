# MarsWalk 2.0 — Milestone 10A Baseline & Architectural Audit

**Milestone:** 10A — Mission Camera Director, Rover Follow Modes & Synchronized Telemetry Cues  
**Status:** Baseline Audited & Verified  
**Date:** 2026-10-19  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

## 1. Baseline Verification

Before initiating Milestone 10A development, the repository status, test suite, and operational preflight health were verified independently:

1. **Test Suite Execution (`pytest -q`):**
   - **Result:** **369 passed** across 33 test files in 149.56 seconds.
   - **Failures / Warnings:** 0 failures, 0 warnings.
   - **Coverage:** Core terrain cost modeling, Apollo walking equations, A* search, contingency gauntlet detours, compound stress scenarios, multi-stop optimization, adaptive replanning, sensitivity analysis, explainability attribution, and Milestone 9Z mission playback interpolation.

2. **Preflight Readiness Verification (`scripts/preflight_check.py`):**
   - **Result:** **12/12 checks passed** in 407.9 ms on `http://127.0.0.1:3000`.
   - **Subsystems Verified:**
     - 01 Atlas HTTP API Server (`/api/health`)
     - 02 Web Frontend Assets (`index.html`, `app.js`, `styles.css`)
     - 03 Planetary Feature Gazetteer (2,061 Martian features)
     - 04 Planetary Imagery Registry (9 imagery products)
     - 05 Global Mars Basemap Layer (Viking MDIM2.1 / MGS MOLA)
     - 06 Jezero CTX Optical Imagery
     - 07 Jezero Crater 20m DTM (250x250 GeoTIFF)
     - 08 Route Planning Engine (A*)
     - 09 Gauntlet Disruption & Recovery Engine
     - 10 Persistent Workspace Storage (7 missions, 11 experiments preserved)
     - 11 Mission Briefing & Schema Validator (Draft 2020-12 valid)
     - 12 Streamlit Tactical Control App

---

## 2. Playback & Camera Architecture Audit

### 2.1 Existing Camera & Rendering Loop (`web/app.js`)
- **Camera:** `THREE.PerspectiveCamera(45, aspect, 0.1, 10000)` configured for the Jezero workstation surface coordinate system.
- **Controls:** `THREE.OrbitControls` bound to `canvas`.
- **Render Loop:** A single `requestAnimationFrame(animate)` loop running at ~60 FPS.
- **Marker Tracking in Milestone 9Z:**
  - `playbackVehicleMesh` is a 3D composite group (bronze chassis, dark sapphire solar deck, sensor mast, forward cyan cone, pulsing point light).
  - Milestone 9Z implemented basic tracking via `controls.target.lerp(currentPos, 0.08)` when a checkbox was ticked, leaving `camera.position` stationary. This allowed the rover to drive away from the camera viewpoint or forced awkward orbital angles.
  - No dedicated camera director existed to frame the rover from third-person chase, first-person cockpit, or nadir overhead vantage points.

### 2.2 Heading Calculation & Stationary Latching
- Currently, heading is calculated via look-ahead sampling:
  ```javascript
  const futureT = Math.min(model.total_duration_s, timeSeconds + 1.5);
  const futureState = interpolateLocalPlaybackState(model, futureT);
  if (futureState && (futureState.rc[0] !== r || futureState.rc[1] !== c)) {
    const nextPos = rcToLocalPos(futureState.rc[0], futureState.rc[1], futureState.elevation_m, currentExaggeration);
    nextPos.y += 8.0;
    playbackVehicleMesh.lookAt(nextPos);
  }
  ```
- **Deficiency Identified:**
  - When the vehicle is stationary (`is_stationary === true` during science dwell or contingency delay), `r` and `c` do not change, but floating-point rounding or sudden edge transitions can cause jitter.
  - Furthermore, for follow/cockpit camera modes, sudden step changes in heading create jarring camera snap rotations.
  - **Solution for 10A:** We will implement an exponential smoothing filter on heading yaw $\theta$ combined with an explicit **heading latch** that strictly preserves heading orientation when `is_stationary` is true.

### 2.3 Audio & Visual Event Telemetry Cues
- **Current State:** Milestone 9Z displays phase badges (`DEPARTURE`, `TRAVERSE`, `SCIENCE DWELL`, `OPERATIONAL HOLD`, `MISSION COMPLETE`) and updates numeric HUD fields. No auditory feedback or synchronized telemetry cues occur.
- **Audio Constraints:**
  - Must use standard browser `AudioContext` (Web Audio API) with pure synthetic oscillators (sine/triangle waves).
  - Absolutely **NO external audio asset downloads**, WAV/MP3 files, or third-party audio libraries.
  - Must be **strictly MUTED by default** to comply with browser autoplay policies and aerospace HUD quiet-cockpit discipline.
  - Audio must be enabled only via explicit user interaction (toggle button).
  - Event triggers must be edge-detected (triggering only once when entering an event) and suppressed during manual high-speed scrubbing.

---

## 3. Milestone 10A Design & Acceptance Criteria

### 3.1 Four Dedicated Camera Director Modes
1. **ORBIT (Free / Manual):**
   - Retains full manual orbital rotation, panning, and zoom via `OrbitControls`.
   - Playback marker moves across terrain without forcing camera displacement.
2. **ROVER FOLLOW (3rd-Person Chase):**
   - Camera smoothly follows behind the rover marker along its latched heading vector:
     $$\mathbf{p}_{\text{cam}} = \mathbf{p}_{\text{marker}} - \mathbf{h}_{\text{unit}} \cdot D_{\text{follow}} + \mathbf{u} \cdot H_{\text{follow}}$$
     where $D_{\text{follow}} \approx 70\,\text{m}$ offset behind, $H_{\text{follow}} \approx 40\,\text{m}$ elevation above terrain, smoothly interpolated via spherical/exponential decay.
   - Target tracks the rover marker: $\mathbf{t}_{\text{cam}} = \mathbf{p}_{\text{marker}} + (0, 10, 0)$.
3. **ROVER COCKPIT (1st-Person Perspective):**
   - Camera positioned directly atop the rover deck / sensor mast:
     $$\mathbf{p}_{\text{cam}} = \mathbf{p}_{\text{marker}} + (0, 9.5, 0)$$
   - Camera aims ahead along the forward travel vector:
     $$\mathbf{t}_{\text{cam}} = \mathbf{p}_{\text{cam}} + \mathbf{h}_{\text{unit}} \cdot 120\,\text{m}$$
   - Includes an explicit HUD disclosure label: *"Illustrative Visualization — Not a Certified Flight Envelope"*.
4. **OVERHEAD (Stabilized Nadir):**
   - Top-down orthographic/nadir perspective directly above the vehicle:
     $$\mathbf{p}_{\text{cam}} = (\mathbf{p}_{\text{marker}}.x, \mathbf{p}_{\text{marker}}.y + 500, \mathbf{p}_{\text{marker}}.z)$$
   - Aims directly down onto the vehicle marker.

### 3.2 Synchronized Event Telemetry & Audio Synthesizer
- **Synthesizer Implementation:**
  - Pure Web Audio API `AudioContext` created/resumed on user toggle.
  - Distinct harmonic cue profiles:
    - `start`: Departure dual-chime ($523.25\,\text{Hz} \to 659.25\,\text{Hz}$).
    - `science_dwell`: Ascending scientific sample chime ($587.33\,\text{Hz} \to 739.99\,\text{Hz} \to 880.0\,\text{Hz}$).
    - `scenario_delay`: Cautionary low pulse ($349.23\,\text{Hz}$).
    - `arrival`: Mission complete harmonic triad ($523.25\,\text{Hz} + 659.25\,\text{Hz} + 783.99\,\text{Hz}$).
  - Gated by `isMuted` (default: `true`).
  - Scrubbing debounce: Audio cues suppressed when user drags the scrubber slider.

### 3.3 Acceptance Criteria
1. Single Three.js render loop maintained (no secondary RAF loop).
2. All 4 camera modes selectable via clean HUD button group with instant feedback and active state highlighting.
3. Smooth transition between camera modes without viewport disorientation or gimbal jumps.
4. Latching heading calculation prevents marker/camera jitter during stationary stops.
5. Audio synthesizer operates purely in-memory with zero external assets, strictly muted by default.
6. Full test suite remains 100% green with new comprehensive Milestone 10A tests added.
7. Visual evidence captured for all 4 camera modes, stationary dwell, and audio/event triggers.
