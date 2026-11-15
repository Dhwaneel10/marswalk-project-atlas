# Mission 17: Homepage Information Hierarchy & Redesign

**Project:** MarsWalk 2.0 / Project Atlas  
**Deliverable:** Homepage Architecture, Clean Layout & Responsive Verification  
**Branch:** `mission-17-competition-readiness`  

---

## 1. Problem Statement & Baseline Defect Analysis

In previous iterations (Mission 14–16), the MarsWalk landing page suffered from layout obstruction:
1. **Drawer Occlusion:** The Joint Co-Design Panel (`#jointMissionStudioPanel`) had a root-level DOM declaration without `.hidden` and a styling rule with `z-index: 105`. Because the landing overlay was at `z-index: 50`, the drawer rendered on top of the hero text, blocking the primary action buttons and confusing users.
2. **Crowded Hero Action Row:** Multiple buttons of equal visual weight competed for the evaluator's attention, making it unclear what action to take first.
3. **Spec Grid Telemetry Mismatch:** The fourth metric in the scientific specs grid advertised "0 KB Lost / RFC 9171 DTN Custody", which highlighted an experimental comms simulation rather than our core in-situ planetary science and weather contingency modeling.

---

## 2. Redesigned Information Hierarchy

The redesigned landing page enforces a strict visual and cognitive hierarchy designed for a 15-second first impression by NASA Space Apps evaluators:

```
+-----------------------------------------------------------------------------------+
|  [BRAND HEADER] MARSWALK 2.0  •  PROJECT ATLAS   [TARGET: MARS  •  IAU 2000]       |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [KICKER] NASA SPACE APPS CHALLENGE 2026 SUBMISSION                              |
|  [HEADLINE] Planetary Mission Intelligence & Astronaut EVA Operations Platform   |
|  [SUBTITLE] A physics-grounded human exploration and robotic reconnaissance       |
|             system combining authentic USGS 1m/20m terrain models, Perseverance    |
|             ground truth, and biophysical life-support simulation.                 |
|                                                                                   |
|  [EPISTEMIC PILLS]                                                                |
|  [✔ MEASURED ARCHIVES]       [◆ DERIVED PRODUCTS]       [⚙ SIMULATION MODELS]     |
|                                                                                   |
|  [PRIMARY CTA ROW]                                                                |
|  +------------------------------+   +---------------------------------------+     |
|  | ⚡ ENTER ASTRONAUT EVA MODE  |   | ☀️ Explore Jezero Environment         |     |
|  +------------------------------+   +---------------------------------------+     |
|  [★ Evaluator Tour]   [★ 5-Min Showcase]   [⚙ Preflight Check]   [How It Works]   |
|                                                                                   |
|  [SCIENTIFIC SPECS GRID]                                                          |
|  +-------------------+  +-------------------+  +-------------------+  +---------+ |
|  |      20m / 1m     |  |      33.2 km      |  |    8-Hour PLSS    |  | τ = 1.5 | |
|  |  USGS CTX/HiRISE  |  |  PDS Ground Truth |  |   Life-Support    |  | Sol 89  | |
|  +-------------------+  +-------------------+  +-------------------+  +---------+ |
|                                                                                   |
|  [RESEARCH DISCLAIMER] Not certified operational safety for astronauts.           |
|                                                                                   |
+-----------------------------------------------------------------------------------+
|  [RIGHT COLUMN] JEZERO CRATER OPERATIONAL MISSION HUB (Sole Supported Location)   |
|  • Topography: USGS CTX 20m & HiRISE 1m DTM                                       |
|  • Ground Truth: NASA PDS Sols 0–1000+ (33.2 km)                                  |
|  • Meteorology: PDS MEDA In-Situ (Sol 89 Storm)                                   |
|  • Science Targets: 12 Delta Outcrops & Sample Depot                              |
+-----------------------------------------------------------------------------------+
```

---

## 3. Key Redesign Enhancements

### 3.1 Unobstructed Landing Viewport
- **Fix:** Added `.hidden` class to `#relayNetPanel` and `#jointMissionStudioPanel` in `web/index.html`.
- **Z-Index Correction:** Reduced `.jointstudio-control-panel` z-index from `105` to `28` in `web/styles.css`.
- **State Initialization:** Guaranteed `relayNetVisible = false` and `jointMissionDrawerVisible = false` in `web/app.js`.
- **Result:** The landing page renders cleanly with zero floating drawers or modal occlusions.

### 3.2 Clear Two-Tier Call-to-Action (CTA) Architecture
- **Primary Hero CTA (`#btnLandingEnterEVA`):**
  - **Label:** `⚡ ENTER ASTRONAUT EVA MODE`
  - **Visual Treatment:** Bold amber gradient (`#F59E0B` to `#D97706`), golden glow box-shadow (`0 4px 24px rgba(245, 158, 11, 0.45)`), uppercase high-contrast typography.
  - **Action:** Hides landing page, switches to Jezero Crater 3D surface view, activates Astronaut EVA mode, reveals PLSS telemetry, and selects the `#btnNavAstronautEVA` HUD pill.
- **Secondary Hero CTA (`#btnLandingExploreEnv`):**
  - **Label:** `☀️ Explore Jezero Environment →`
  - **Visual Treatment:** Clean translucent glass button with cyan hover border.
  - **Action:** Hides landing page, switches to Jezero Crater 3D surface view, and directly opens the Environment Studio (`tabEnvironmentStudio`) displaying MEDA Sol 89 telemetry.
- **Tertiary Guided Actions:**
  - `★ Evaluator Tour`: Launches the step-by-step 7-checkpoint golden path walkthrough.
  - `★ 5-Min Showcase`: Starts the automated 5-minute competition showcase script.
  - `⚙ Preflight Check`: Runs the 12-point automated server and data readiness diagnostic.
  - `How It Works`: Smoothly scrolls down to reveal the architectural cards and data pipeline.

### 3.3 Specs Grid Realignment with Authentic Martian Science
The fourth item in the specs grid was updated:
- **Previous:** `0 KB Lost` / `RFC 9171 DTN Custody (Merkle Verified)`
- **Current:** `τ = 1.5 Storm` / `NASA MEDA Sol 89 In-Situ Dust Contingency`
- **Scientific Significance:** Connects directly to our authentic in-situ weather data from Perseverance MEDA, emphasizing our "When Mars Goes Dark" atmospheric dust storm stress-testing rather than abstract networking heuristics.

---

## 4. Visual Verification Evidence

All screenshots were captured using headless Chrome at full resolution:

| Figure | Viewport | Target | Dimensions | File Size | Output Path |
|---|---|---|---|---|---|
| **Figure 1** | Desktop | Homepage Hero & Clear Viewport | $1920 \times 1080$ | 512 KB | [`outputs/mission_17/01_homepage_clean_hero.png`](../outputs/mission_17/01_homepage_clean_hero.png) |
| **Figure 2** | Mobile | Responsive Mobile Landing Screen | $390 \times 844$ | 405 KB | [`outputs/mission_17/11_mobile_responsive_homepage.png`](../outputs/mission_17/11_mobile_responsive_homepage.png) |

Both viewports confirm zero drawer overlap, perfect button alignment, readable typography, and complete responsiveness.
