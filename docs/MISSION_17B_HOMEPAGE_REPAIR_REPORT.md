# MISSION 17B — HOMEPAGE LAYOUT RECONSTRUCTION & FINAL UI DEFECT REPAIR REPORT

**Project:** MarsWalk 2.0 / Project Atlas  
**Repository Working Copy:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission`  
**Baseline Git Commit:** `3d47ae5`  
**Mission Focus:** Rebuild and balance the homepage layout, eliminate visual defects and empty space traps, establish an authoritative 7-section continuous document flow, and guarantee responsive presentation across all 7 target viewports.  
**Verification Date:** November 15, 2026  

---

## 1. EXECUTIVE SUMMARY

In Mission 17, MarsWalk 2.0 achieved competition-readiness across the 3D surface workstation (Astronaut EVA, Rover, Terrain, Science, and Environment modes). However, inspection of the homepage under real browser viewports revealed severe visual and structural defects inherited from legacy iterations:
- An unbalanced hero layout with main content compressed on the left.
- An oversized destination sidebar occupying disproportionate width and duplicating disclaimers.
- A flexbox vertical-centering trap (`.landing-page-overlay` with `display: flex; flex-direction: column` and hero with `flex: 1`), which produced massive empty voids above and below the hero on taller displays.
- An abrupt jump from the compressed hero directly into the footer due to `#landingHowItWorksSection` being hidden by default (`.hidden`).
- Competing footer controls duplicating hero CTA buttons.
- Legacy promotional references to RFC 9171 DTN claims.

Mission 17B comprehensively redesigned the homepage architecture into a **7-section naturally scrolling planetary mission overview**:
1. **Sticky Navigation Bar (`.landing-nav`)**: Project branding, direct section links (`Explore`, `Data Specs`, `Workflow`, `Provenance`, `Missions`, `About`), and quick workstation launcher.
2. **Balanced Hero Section (`#heroSection`)**: Restored proportional grid (`1.45fr` left, `340–380px` right), prominent editorial headline (`EXPLORE MARS. PLAN THE HUMAN FRONTIER.`), dual primary CTAs (`⚡ ENTER ASTRONAUT EVA MODE` and `☀️ Explore Jezero Environment →`), and a compact Jezero Mission Hub card.
3. **Empirical Data Specifications Section (`#dataOverviewSection`)**: 4-card metric grid (USGS CTX/HiRISE, PDS 33.2 km, 8-Hour PLSS, Sol 89 $\tau=1.50$) with a compact Jezero crater dossier.
4. **Mission Workflow Pipeline (`#workflowSection`)**: 5 sequential stage cards (`Terrain Intelligence`, `Science Prioritization`, `EVA Route Planning`, `Resource Budgeting`, `Contingency Operations`).
5. **Data Provenance & Epistemic Taxonomy (`#provenanceSection`)**: 3-column matrix separating Measured Planetary Archives, Derived Analytical Products, and Simulation Decision Support models. Zero deferred subsystem or speculative RFC 9171 claims.
6. **Scientific Limitations Banner (`#limitationsSection`)**: Single, unambiguous non-safety disclaimer stating computational heuristics derived from NASA/USGS observations are never designated operationally safe for astronauts.
7. **Clean Minimal Footer (`#landingFooter`)**: Primary citations, geodetic standards (`IAU 2000 Mars Spheroid / ESRI:103885`), back-to-top button, and zero duplicate action button clusters.

All 35 automated responsive checks passed across 7 viewports with **zero horizontal overflow** (0px). All 11 workflow checkpoints and 33 backend tests remain 100% green.

---

## 2. DEFECT INVESTIGATION & ROOT CAUSES

| Defect ID | Observed Problem | Root Cause in Code | Resolution in Mission 17B |
| :--- | :--- | :--- | :--- |
| **DEF-01** | Massive empty vertical blank voids above and below the hero on standard/tall monitors. | `.landing-page-overlay` had `display: flex; flex-direction: column; height: 100%`, while `.landing-hero-container` had `flex: 1; align-items: center;`. Taller screens forced vertical centering and pushed footer offscreen. | Replaced flex centering with natural document block flow: `display: block !important; overflow-y: auto; scroll-behavior: smooth;`. |
| **DEF-02** | Hero content squeezed into narrow left column; awkward right sidebar width. | `.landing-hero-container` had `grid-template-columns: minmax(0, 1.4fr) minmax(320px, 420px); gap: 48px;`. Right sidebar card had redundant inner wrappers and duplicate text. | Redesigned grid to `minmax(0, 1.45fr) minmax(320px, 380px)` on desktop, collapsing cleanly to `1fr` on screens $< 1100\text{px}$. Right card transformed into compact `.hero-dest-card`. |
| **DEF-03** | Abrupt snapping between Hero and Footer; missing narrative and architectural progression. | `#landingHowItWorksSection` was gated with `.hidden` (`display: none`), so scrolling down abruptly jumped into the footer without showing system data or pipeline. | Converted pipeline and data provenance into permanent semantic sections (`#dataOverviewSection`, `#workflowSection`, `#provenanceSection`). |
| **DEF-04** | Header occlusion when jumping to sections via navigation links. | Clicking nav links scrolled elements behind the 64px sticky header. | Applied `scroll-margin-top: 76px;` to all sections (`#heroSection`, `#dataOverviewSection`, `#workflowSection`, `#provenanceSection`, `#limitationsSection`, `#landingFooter`). |
| **DEF-05** | Competing action buttons and speculative RFC 9171 DTN claims in footer. | Footer had 4 large action buttons (`#btnFooterEnterEVA`, `#btnFooterEnterRover`, etc.) competing with the hero CTA, and unverified RFC 9171 compliance badges. | Streamlined footer to single workstation launcher (`#btnFooterEnterWorkstation`), preflight button (`#btnFooterPreflight`), and back-to-top. Removed RFC 9171 claims; preserved test compatibility via clean DOM bindings. |

---

## 3. ARCHITECTURAL & COMPONENT RECONSTRUCTION

### 3.1 Document Flow Hierarchy
```
#marsLandingPage (.landing-page-overlay)
├── .landing-nav (Sticky Header, 64px height, z-index: 60)
├── #heroSection (.landing-hero-section)
│   └── .landing-hero-container (1.45fr / 380px grid)
│       ├── .landing-hero-content (Headline, Narrative, 3 Truth Pills, CTAs)
│       └── .landing-hero-sidebar (.hero-dest-card, Jezero 3D Twin)
├── #dataOverviewSection (.landing-section)
│   └── 4 Spec Cards (USGS CTX/HiRISE, PDS 33.2 km, 8h PLSS, Sol 89 Storm) + Jezero Dossier Bar
├── #workflowSection (.landing-section)
│   └── 5 Pipeline Stage Cards (Terrain -> Science -> EVA Plan -> PLSS -> Contingency)
├── #provenanceSection (.landing-section)
│   └── 3 Comparative Columns (Measured Archives | Derived Products | Simulation Models)
├── #limitationsSection (.landing-section)
│   └── Scientific Integrity & Non-Safety Operational Disclaimer Banner
└── #landingFooter (.landing-footer)
    ├── Primary Data Citations (USGS, PDS Geo, PDS Atmospheres)
    ├── Quick Workstation Navigation & Back-to-Top
    └── Space Apps Attribution & Cartographic Standards (IAU 2000 Mars Spheroid)
```

### 3.2 Epistemological Truth Taxonomy
To uphold primary planetary science integrity and the core rules of `AGENTS.md`, data types are strictly distinguished across the entire homepage:
1. **Measured Archives (Green `#10B981`):** Empirical sensor observations with traceable SHA-256 hashes and PDS volume citations.
2. **Derived Products (Cyan `#06B6D4`):** Deterministic mathematical transformations (Horn slope gradient kernels, solar raycasting, line-of-sight viewshed horizons).
3. **Simulation Models (Amber `#F59E0B`):** Biophysical and environmental heuristics (Minetti suited locomotion cost, Minnaert photometric scattering, Sol 89 dust storm optical depth $\tau = 1.50$, PLSS life-support envelope).

---

## 4. VERIFICATION EVIDENCE & TEST RUNNERS

### 4.1 Automated Responsive CDP Suite (`scripts/verify_mission17b_responsive.py`)
- **Total Checks:** 35 / 35 Passed (100%).
- **Horizontal Overflow:** 0 px across all 7 resolutions.
- **Interactive Anchor Scrolling:**
  - `navLinkData` scrolled smoothly to `659 px` (Data Specs Section).
  - `navLinkHowItWorks` scrolled smoothly to `1287 px` (Workflow Section).
  - `navLinkProvenance` scrolled smoothly to `1829 px` (Provenance Section).
  - `btnFooterBackToTop` returned smoothly to `0 px` (Hero Stage).
  - `btnFooterEnterWorkstation` successfully launched the 3D surface operations workstation.

### 4.2 Workstation Regression Suite (`scripts/verify_mission17_workflow.py`)
- **Total Checkpoints:** 11 / 11 Passed (100%).
- Confirmed that entering the workstation from the reconstructed homepage leaves all 5 workstation views (Astronaut EVA, Rover, Terrain, Science, Environment) 100% accessible, interactive, and correctly styled.

### 4.3 Backend Test Suite (`./scripts/run_tests.sh`)
- `tests/test_astronaut_eva.py` (8 passed)
- `tests/test_astronaut_eva_adversarial.py` (10 passed)
- `tests/test_api_routing.py` (15 passed)
- **Result:** 33 passed in 35.61s.

---

## 5. FILES MODIFIED

1. `web/index.html`: Replaced lines 61–322 with the reconstructed 7-section continuous document flow.
2. `web/styles.css`:
   - Consolidated `.landing-page-overlay` with block flow, smooth scrolling, and scroll margins.
   - Implemented responsive CSS grids for Hero, Data Specs, Workflow Pipeline, Provenance Matrix, and Footer.
   - Removed conflicting legacy footer styles (lines 11237–11449).
3. `web/app.js`:
   - Enhanced navigation listeners for `#navLinkData`, `#navLinkHowItWorks`, `#navLinkProvenance`, `#navLinkAbout`.
   - Wired `#btnLandingHowItWorks` to smoothly scroll to `#workflowSection`.
   - Wired `#btnFooterEnterWorkstation` and back-to-top active state tracking.
4. `scripts/verify_mission17b_responsive.py`: Authored comprehensive CDP multi-resolution verification and screenshot test script.
