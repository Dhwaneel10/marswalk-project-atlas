# Project MarsWalk 2.0 / Atlas — Evaluator Experience & Interface Review
**Document ID:** `DOC-MW-M7-EVALUATOR-EXPERIENCE`  
**Mission Phase:** Mission 7 — Submission Engineering & Final Competition Package (Phase 3)  
**Evaluator Perspective:** First-time NASA Space Apps Judge / Planetary Systems Reviewer  
**Platform Execution:** Ubuntu 22.04 LTS | Python 3.10.12 | WebGL 3D Workstation  

---

## 1. The 15-Second Evaluator Heuristic

When a judge opens [http://127.0.0.1:3000/](http://127.0.0.1:3000/), the interface must communicate five essential truths within **15 seconds**, without requiring manual scrolling or prior documentation reading:

```
+-------------------------------------------------------------------------------------------------------+
|                                  THE 15-SECOND EVALUATION COCKPIT                                     |
+-------------------+-----------------------------------------------------------------------------------+
| 1. WHAT IT DOES   | Autonomous rover route planning, astrobiology site prioritization, and            |
|                   | delay-tolerant deep-space communications resilience.                              |
+-------------------+-----------------------------------------------------------------------------------+
| 2. WHY IT MATTERS | Martian rovers cannot be driven in real time (4-24 min RTLT); bypassing science   |
|                   | targets wastes multi-billion-dollar missions, while steep slopes risk vehicle tip.|
+-------------------+-----------------------------------------------------------------------------------+
| 3. REAL MARS DATA | 100% grounded in authentic USGS CTX 20m & HiRISE 1m DTMs, NASA PDS Rover PLACES,  |
|                   | Three Forks sample depot manifests, and MEDA in-situ atmospheric dynamics.        |
+-------------------+-----------------------------------------------------------------------------------+
| 4. FIVE PILLARS   | 1. Terrain Geodesy | 2. Rover Operations | 3. Atmospheric Physics |            |
|                   | 4. Multi-Objective A* Science Routing | 5. DTN RFC 9171 Autonomous Detour.     |
+-------------------+-----------------------------------------------------------------------------------+
| 5. REAL VS SIM    | Explicitly distinguishes MEASURED ARCHIVAL telemetry from SIMULATED AUTONOMY.    |
+-------------------+-----------------------------------------------------------------------------------+
```

---

## 2. Interface Hierarchy & Workflow Enhancements

### 2.1 The Unified Landing Page Experience
The opening screen features high-contrast, epistemologically clear visual cues:
- **Title Banner:** `MARSWALK 2.0 / ATLAS — REAL MARS SCIENCE. AUTONOMOUS RESILIENCE.`
- **Kicker:** `NASA SPACE APPS CHALLENGE 2026 • FIVE-PILLAR MISSION ARCHITECTURE • USGS CTX+HiRISE`
- **Epistemological Truth Badges:**
  - `✔ MEASURED ARCHIVES: USGS 20m/1m DTMs • PDS 33.2 km Traverse • MEDA Weather` (Green badge)
  - `⚙ SIMULATION MODELS: Multi-Objective A* Detours • RFC 9171 DTN Buffer` (Yellow badge)
- **Direct Entry CTA Button:**
  - `[★ EVALUATOR TOUR →]`: Bypasses manual navigation, takes the judge directly to Jezero Crater, opens the 7-step guided HUD, and preloads Step 1.
  - `[★ 5-Min Showcase →]`: Runs the automated multi-waypoint guided sortie.
  - `[Explore Workstation →]`: Enters free-roam planetary GIS mode.
  - `[⚙ Preflight Check]`: Executes 12-point system self-tests.

### 2.2 The Five-Pillar Deck as a Cohesive Mission Pipeline
Rather than five disconnected dashboards, the Five Pillars follow the sequential logic of a real planetary mission:
1. **Pillar 1 (Terrain Geodesy):** Where can the rover physically drive? (USGS CTX 20m corridor + HiRISE 1m micro-hazards at Hawksbill Gap).
2. **Pillar 2 (Ground Truth Operations):** Where has the rover already been, and what has it cached? (PDS 33.2 km traverse and 10 sealed sample tubes at Three Forks).
3. **Pillar 3 (Atmospheric Replay):** What environmental constraints govern today's drive? (MEDA air temp, pressure, and dust storm solar/thermal limits).
4. **Pillar 4 (Science Planning):** Which astrobiology targets should be visited, and at what cost? (Multi-Objective A* trade study: Route A direct vs Route B science detour: $+160\,\text{pts}$ yield for $+134\%$ distance).
5. **Pillar 5 (Autonomous Resilience):** How does the rover survive unforeseen hazards and blackouts? (Safe hold, lateral ridge detour restoring MRO orbiter link, and bit-exact Merkle state continuity).

---

## 3. Epistemological Disclosures & Labeling Audit

### 3.1 Historical Observations vs. Live Telemetry
- **Correction Made:** Explicit disclaimers were added across all PDS tabs and REST endpoints:
  > *Notice: Historical archived observations (PDS Mars 2020 Sols 13–1896) anchor the baseline terrain and mission state; they do not represent real-time live spacecraft downlink.*

### 3.2 Rover Power Architecture Disclosure
- **Correction Made:** Explicit notice added in UI and documentation:
  > *Physical Disclosure: The real Perseverance rover is powered by an MMRTG (nuclear decay producing ~110W steady power). The solar array power model ($900\text{W} \to 258\text{W} \to 50\text{W}$) is an analogue simulation model for solar-powered planetary exploration vehicles.*

### 3.3 RF Telecommunications Physics
- **Correction Made:** Removed misleading claims of "Mie scattering at X-band".
  > *Physical Disclosure: At X-band (8.4 GHz) and microwave frequencies, Martian dust particles ($a \sim 1.5\,\mu\text{m}$) operate strictly in the Rayleigh scattering regime ($x \sim 2.6 \times 10^{-4} \ll 1$), where absorption dominates. UHF proximity links (401.58 MHz) are near-transparent ($\approx 0.008\,\text{dB/km}$). The empirical formula $\alpha = 0.008 + 0.098\tau^{1.15}\,\text{dB/km}$ is documented as an illustrative engineering proxy for dust storm link degradation.*

---

## 4. Evaluator Verification of the Golden Path

The Evaluator Golden Path Tour HUD remains 100% operational across server restarts:
1. When launched, `#evaluatorGoldenPathCard` opens seamlessly with active step navigation.
2. Step 1 executes manifest validation (8/8 datasets).
3. Step 2 inspects Hawksbill Gap 1m slope ($9.4^\circ$, caution ascent) vs crater floor 20m slope ($3.0^\circ$).
4. Step 3 displays the 10 sealed tubes at Three Forks depot.
5. Step 4 applies MEDA dust calibration and computes subsystem loads.
6. Step 5 computes Route A ($2,309.7\,\text{m}$, 0 pts) vs Route B ($5,406.2\,\text{m}$, $+160\,\text{pts}$).
7. Step 6 executes the "When Mars Goes Dark" flagship replay.
8. Step 7 audits the bit-exact Merkle root (`0380a7cf112a7bd3...`) and confirms 100% DTN bundle delivery (0 bytes lost).
