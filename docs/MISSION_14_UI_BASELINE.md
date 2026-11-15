# MISSION 14: CINEMATIC UI TRANSFORMATION BASELINE & AUDIT
## Ascend-Inspired Design Language | Technical Baseline

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository:** `MarsWalk-Submission`  
**Starting Branch:** `mission-13-eva-qualification`  
**Active Sprint Branch:** `mission-14-cinematic-ui`  
**Starting Commit:** `6490617` (`v2.2.0-eva-qualified`)  
**Sprint Window:** 5 Hours Maximum Autonomous Execution  
**Timestamp:** 2026-11-15T17:30:00+05:30  
**Status:** PHASE 0 BASELINE AUDIT COMPLETE  

---

### 1. Executive Summary & Sprint Directive

Mission 14 elevates MarsWalk 2.0 / Project Atlas into a world-class, cinematic planetary exploration and astronaut mission-control experience. Drawing inspiration from modern aerospace and cinematic design standards (such as the Ascend dark-space visual language), MarsWalk will be upgraded with:
- **Immersive Dark-Space Palette:** `#05070D` space void background, `#0A0E18` elevated secondary surfaces, and `rgba(13, 19, 31, 0.72)` glassmorphic panels.
- **Glassmorphism & Atmospheric Lighting:** Fine hairline borders (`rgba(148, 163, 184, 0.15)`), backdrop blur (`blur(16px)`), subtle inner highlights, and atmospheric Martian glow.
- **Cinematic Landing Stage:** A dramatic, science-authentic hero section featuring:
  - Headline: **EXPLORE MARS. PLAN THE HUMAN FRONTIER.**
  - Narrative: *"An integrated planetary exploration platform combining Martian terrain intelligence, rover observations, environmental science and human EVA mission planning."*
  - Direct CTAs: **[Enter Astronaut EVA Mode]** and **[Explore Planetary Environment]**.
- **Astronaut EVA Primacy:** Elevating human surface excursion planning, life-support consumable budgets, and dual-track polyline rendering (Amber outbound, Cyan return) as the primary mission workflow.
- **Micro-Interactions & Choreographed Motion:** Staggered scroll reveals, animated numeric telemetry counters, live PLSS oxygen gauge transitions, and responsive multi-viewport adaptation without external dependencies.
- **Scientific Integrity Invariance:** Preserving authentic USGS HiRISE/CTX terrain, NASA PDS telemetry, and prominent operational safety disclaimers.

---

### 2. Forensic UI Architecture Audit

#### 2.1 File Structure & Line Count Inventory
- **`web/index.html` (9,633 lines):**
  - Lines 1–46: Preconnect headers, Google Fonts (Inter, JetBrains Mono, Orbitron, Cinzel, Playfair Display), local Three.js `three.min.js`, and `OrbitControls.js`.
  - Lines 58–253: `#marsLandingPage.landing-page-overlay` with navigation, hero section, CTA buttons, and specs grid.
  - Lines 321–326: `#viewport3d` Three.js canvas container and labels overlay.
  - Lines 329–420: `#cockpitHudOverlay`, `#evaVisorHudOverlay`, and `#missionTheaterHUD`.
  - Lines 942–7860+: `#inspectorPanel.hud-inspector` sidebar containing 22 mission tabs, notably `#tabPlan` (lines 5813–6401) housing the Astronaut EVA Planning Studio and Rover Mode switcher.
- **`web/styles.css` (9,409 lines):**
  - Defines CSS custom properties (`:root`), dark aerospace glassmorphism, responsive breakpoints, HUD positioning, and EVA route card styles.
- **`web/app.js` (28,253 lines):**
  - Three.js WebGL scene lifecycle (camera, orbit controls, directional sun lighting, DEM mesh generation).
  - Lines 19370–19740: Astronaut EVA Mode event handlers, API communications, dual-track 3D rendering (`drawDualEvaRoute`), contingency state progression, and Visor HUD updates.

#### 2.2 Existing Browser Screenshot Review (Missions 12 & 13)
Inspection of visual evidence in `outputs/mission_13/browser_qa/`:
- `m13_01_astronaut_eva_landing_disclaimer.png`: Functional layout with dark panels, but landing stage lacks dramatic depth, atmospheric starfields, and modern typography hierarchy.
- `m13_02_eva_dual_track_3routes.png`: 3 route cards are functional, but card borders and elevation states feel flat rather than layered glassmorphic telemetry.
- `m13_03_eva_visor_hud_telemetry.png`: Visor HUD is positioned well in the top right, but gauges lack subtle animated glow and micro-interactions.
- `m13_06_responsive_compact_1366.png`: Responsive layout holds without overflow, but padding and font sizes can be optimized for tighter visual cohesion.

#### 2.3 Existing CSS & Animation Conflicts Identified
1. **Multiple Conflicting Background Colors:** Legacy `#03060c`, `#060a14`, `#0f172a`, and `#0b0f19` scattered across panels create visual inconsistency. These will be unified to the strict restrained palette (`#05070D` base, `#0A0E18` elevated, `rgba(13, 19, 31, 0.72)` glass).
2. **Heavy Opacity / Low-Contrast Text:** Muted labels occasionally use low-contrast grey (`#475569`) which drops below WCAG AA on dark backgrounds. These will be standardized to `#9AA7B8` (secondary) and `#66758A` (muted).
3. **Static Telemetry Values:** Numbers update abruptly on API resolution. We will implement smooth numerical transitions and pulse indicators on value updates.
4. **Hero Stage Visual Isolation:** The existing hero overlay hides the 3D planetary canvas with a flat semi-transparent backdrop rather than letting the ambient Martian atmosphere breathe through subtle glassmorphism and star particles.

---

### 3. Non-Negotiable Invariance Constraints

1. **Workspace Boundary:** Work strictly inside `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`.
2. **Reference Immutability:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/Atlas-Source/MarsWalk` remains strictly untouched.
3. **Real Planetary Terrain:** Keep authentic 1m USGS HiRISE & 20m CTX terrain models. Never substitute real terrain with synthetic or Earth-like assets.
4. **Preserve Dual-Mode & Five Pillars:** All existing API endpoints, route planning algorithms, consumable equations, and rover ground truth must remain 100% operational.
5. **Operational Safety Notice:** Mandatory non-safety disclosures must remain prominent:  
   `"RESEARCH DECISION-SUPPORT MODEL — NOT AN OPERATIONAL FLIGHT SAFETY CERTIFICATION"`
