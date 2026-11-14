# MarsWalk 2.0 — Project Atlas: Engineering Handoff

> **Generated:** 2026-10-20  
> **Outgoing agent:** Gemini / Antigravity (conversation `0a1bc6e9-d3cc-4c3b-b1fe-4875c358b144`)  
> **Incoming agent:** Claude (or any successor agent)  
> **Status at handoff:** Milestone 10C complete, repository clean, Atlas server verified healthy.

---

## 1. Project Purpose

**MarsWalk 2.0 (Project Atlas)** is an end-to-end planetary mission-planning and rehearsal workstation built for the NASA Space Apps Challenge 2026. It lets mission planners:

- Explore Mars in an interactive 3D globe with a verified planetary gazetteer.
- Plan multi-stop surface traverses across a real 20 m/px Jezero Crater DTM using A* routing.
- Design, compare, and stress-test mission variants under compound hazards.
- Simulate mid-sortie emergencies and calculate adaptive re-routes in real time.
- Replay past missions frame-by-frame with camera director modes, audio cues, and a sortie black-box event ledger.
- Export cryptographically hashed, auditable Decision Pack ZIP bundles.

The application respects strict scientific provenance rules: **no synthetic topography is presented as real data; measured, derived, and hypothetical values are always distinguished**.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│  Browser  (Three.js 3D renderer + vanilla JS UI)    │
│  web/index.html  web/app.js  web/styles.css         │
└────────────────────┬────────────────────────────────┘
                     │ HTTP REST (port 3000)
┌────────────────────▼────────────────────────────────┐
│  Atlas HTTP Server  (scripts/run_atlas.py)           │
│  Pure-Python WSGI-less HTTP server                   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  API Layer  (src/marswalk/api/service.py)            │
│  Routing, contracts validation, workspace I/O        │
└───────┬────────────────────┬────────────────────────┘
        │                    │
┌───────▼──────┐  ┌──────────▼──────────────────────┐
│  Core Engine │  │  Persistence Layer               │
│  src/mars-   │  │  data/workspaces/                │
│  walk/core/  │  │    missions/*.json               │
└──────────────┘  │    experiments/*.json            │
                  │    events/<id>_events.json       │
                  └──────────────────────────────────┘
```

There is also a legacy **Streamlit** tactical app (checked by preflight, port varies). The Three.js Atlas app is the primary demo surface.

---

## 3. Repository Layout

```
E:\Python\NASA-Spaceapps\Marswalk\
│
├── web/
│   ├── index.html          # Single-page application shell; all modals live here
│   ├── app.js              # ~6 000+ lines: Three.js renderer, UI state machine,
│   │                       #   API calls, playback loop, camera director,
│   │                       #   emergency injection, black-box ledger
│   └── styles.css          # Mission-ops dark theme
│
├── src/marswalk/
│   ├── api/
│   │   ├── service.py      # All HTTP handlers (route, plan, playback, continue,
│   │   │                   #   black-box, export, preflight …)
│   │   ├── contracts.py    # JSON-schema validation helpers
│   │   ├── decision_pack.py# ZIP bundle assembly & cryptographic manifest
│   │   ├── preflight.py    # 12-point preflight check implementation
│   │   └── workspace.py    # missions/experiments/events CRUD helpers
│   │
│   └── core/
│       ├── planner.py              # A* terrain routing (primary planner)
│       ├── adaptive_replanner.py   # Post-disruption alternative route search
│       ├── mission_optimizer.py    # TSP / 2-Opt waypoint ordering
│       ├── mission_playback.py     # Timeline generation for nominal/disrupted/adaptive
│       ├── mission_continuation.py # Mid-sortie resumption from interpolated position
│       ├── mission_event_ledger.py # Sortie black-box: log, query, filter events
│       ├── incident_replay.py      # Re-simulate a past event and compare to ledger
│       ├── robustness.py           # Monte-Carlo stress-testing
│       ├── contingency.py          # Contingency scenario engine (Milestone 9R)
│       ├── explainer.py / route_explainer.py  # Human-readable route narrative
│       ├── science_budget.py       # Dwell / life-support budget accounting
│       ├── stress_test.py          # Compound hazard simulation
│       ├── terrain.py              # DTM raster loading, slope computation, A* grid
│       └── preferences.py         # User preference persistence
│
├── scripts/
│   ├── run_atlas.py                # ← START HERE (main server entry point)
│   ├── preflight_check.py          # CLI preflight diagnostics
│   ├── capture_milestone_10[abc]_evidence.py  # Chrome CDP screenshot runners
│   └── … (various data-prep and audit scripts)
│
├── tests/
│   ├── test_milestone_10a_camera_experience.py   # 20 tests — camera / audio cues
│   ├── test_milestone_10b_live_replanning.py     # 20 tests — emergency injection
│   ├── test_milestone_10c_sortie_black_box.py    # 20 tests — black-box ledger
│   └── test_milestone_9[d-z]_*.py               # 364 tests — earlier milestones
│
├── schemas/api/v1/
│   ├── mission-event.schema.json                # Black-box event payload
│   ├── mission-continue-response.schema.json    # Continuation handoff
│   ├── mission-playback-response.schema.json    # Timeline + waypoints
│   ├── incident-replay-response.schema.json     # Replay fidelity result
│   ├── route-result.schema.json
│   ├── saved-mission.schema.json
│   └── … (15 schemas total)
│
├── data/
│   ├── workspaces/
│   │   ├── missions/       # Saved mission JSON files — DO NOT DELETE
│   │   ├── experiments/    # Saved experiment comparison JSON — DO NOT DELETE
│   │   └── events/         # Black-box event ledgers — DO NOT DELETE
│   └── … (DTM tiles, orthomosaic, gazetteer)
│
├── outputs/                # Evidence screenshots (see §8)
├── docs/                   # Milestone design docs, reports, architecture docs
└── README.md
```

---

## 4. How to Start Atlas

### Start the server
```powershell
cd E:\Python\NASA-Spaceapps\Marswalk
.\.venv\Scripts\python.exe scripts/run_atlas.py --port 3000 --no-browser
```

Open `http://localhost:3000` in Chrome (Chromium-based browser recommended for CDP evidence capture).

### Run preflight diagnostics
```powershell
.\.venv\Scripts\python.exe scripts/preflight_check.py --port 3000
```
Expected: **12/12 checks passed**.

### Run the full test suite
```powershell
.\.venv\Scripts\python.exe -m pytest
```
Expected: **424 tests passed** (last confirmed run: 2026-10-19 ~23:01 UTC, 152.84 s).

### Run a specific milestone's tests
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_milestone_10c_sortie_black_box.py -v
```

### Capture evidence screenshots (Chrome must be open with remote debugging)
```powershell
# Launch Chrome first with:
# chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\tmp\chrome-debug http://localhost:3000
.\.venv\Scripts\python.exe scripts/capture_milestone_10c_evidence.py
```

---

## 5. Completed Milestones (through 10C)

| Milestone | Name | Key Deliverables |
|-----------|------|-----------------|
| 9D–9H | Terrain & planning foundations | DTM loading, A* planner, slope hazard, science waypoints |
| 9I–9L | Science & cartography | USGS gazetteer (2 061 entries), regional imagery, place catalog |
| 9M–9N | Verification & contracts | JSON-schema API contracts, integration tests |
| 9O–9P | Imagery & integration | Orthomosaic draping, multi-scale texture pipeline |
| 9Q | Demo mode | 5-min guided showcase, safe session snapshot/restore |
| 9R | Contingency Designer | Rockfall/dune/motor hazard placement, 8-measure comparison table |
| 9S | Reliability | Stress-test runner, Monte-Carlo robustness analysis |
| 9T | Run Bundle | Decision Pack ZIP export with SHA-256 manifest |
| 9U | Integration polish | End-to-end demo walkthrough, preflight CI |
| 9V | Mission Design Lab | TSP optimizer, 3-way variant comparison panel |
| 9W | Adaptive Replanning | Post-disruption A* re-route, adaptive variant generation |
| 9X | Robustness Analysis | Monte-Carlo compound hazard scoring, risk tiers |
| 9Y | Route Explainer | Step-by-step human-readable route narrative |
| 9Z | Mission Playback | Play/pause/scrub timeline, 3D rover marker, 3 mission variants |
| **10A** | **Camera Director** | Orbit, rover-follow, cockpit, overhead camera modes; audio/visual event cues; rover heading from route geometry |
| **10B** | **Emergency Injection** | Mid-sortie pause → inject hypothetical hazard → replan from rover position → continuation playback from interruption point |
| **10C** | **Sortie Black Box** | Event ledger (log/query/filter), incident replay with fidelity scoring, replay UI modal, `window.__atlas` debug exports |

---

## 6. Key APIs

All endpoints are served by [`src/marswalk/api/service.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/api/service.py).

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/route` | Compute A* route between coordinates |
| POST | `/api/mission/plan` | Full mission plan (TSP + budgets + variants) |
| POST | `/api/mission/optimize` | Re-order waypoints (TSP/2-Opt) |
| POST | `/api/mission/playback` | Generate playback timeline for a saved mission |
| POST | `/api/mission/continue` | Compute continuation from interruption position |
| POST | `/api/mission/replan` | Adaptive replan with hazard overlay |
| POST | `/api/mission/robustness` | Monte-Carlo robustness scoring |
| POST | `/api/route/explain` | Human-readable route narrative |
| POST | `/api/mission/events` | Log an event to a mission's black-box ledger |
| GET  | `/api/mission/events/<mission_id>` | Retrieve all events for a mission |
| POST | `/api/mission/replay` | Replay an incident and compare to ledger |
| POST | `/api/export_decision_pack` | Generate Decision Pack ZIP bundle |
| POST | `/api/bundle/verify` | Verify a bundle's SHA-256 manifest |
| POST | `/api/bundle/replay` | Replay a Decision Pack bundle |
| GET  | `/api/preflight` | 12-point preflight diagnostics |
| GET  | `/api/health` | Simple liveness check (`{"status":"ok"}`) |

### Event Ledger Schema
Events posted to `/api/mission/events` must match [`schemas/api/v1/mission-event.schema.json`](file:///E:/Python/NASA-Spaceapps/Marswalk/schemas/api/v1/mission-event.schema.json):
```json
{
  "event": {
    "event_type": "WAYPOINT_REACHED",
    "mission_time_s": 1234.5,
    "position_lat": 18.44,
    "position_lon": 77.45,
    "metadata": { "label": "Hawksbill Gap", "dwell_s": 300 }
  }
}
```
Required `event_type` values include: `MISSION_STARTED`, `WAYPOINT_REACHED`, `SCIENCE_DWELL`, `DISRUPTION_DETECTED`, `EMERGENCY_HALT`, `MISSION_RESUMED`, `REPLANNING_TRIGGERED`, `MISSION_COMPLETED`, `CONTINGENCY`.

---

## 7. Persistence Locations

> **Critical rule: never delete, overwrite, or mutate these directories during development.**

| Path | Contents | Notes |
|------|----------|-------|
| `data/workspaces/missions/*.json` | Saved mission plans | Schema: `saved-mission.schema.json` |
| `data/workspaces/experiments/*.json` | Saved experiment comparisons | Schema: `saved-experiment.schema.json` |
| `data/workspaces/events/<mission_id>_events.json` | Black-box event ledgers | Created on first event log |
| `data/workspaces/preferences.json` | User UI preferences | Managed by `preferences.py` |

Test-generated ledger files use the prefix `test_api_XXXXXX_events.json` and are safe to inspect but must not be deleted by hand during a live test run.

The **live nominal-mission ledger** at `data/workspaces/events/mission_nominal_events.json` is the only non-test ledger file currently on disk. It should not be deleted.

---

## 8. Evidence Files

### Milestone 10A — Camera Director
| File | Demonstrates |
|------|-------------|
| `outputs/m10a_01_camera_orbit_mode.png` | Orbit camera mode active |
| `outputs/m10a_02_camera_follow_chase.png` | Rover-follow chase camera |
| `outputs/m10a_03_camera_cockpit_view.png` | First-person cockpit view |
| `outputs/m10a_04_camera_overhead_nadir.png` | Overhead nadir (2D-like) mode |
| `outputs/m10a_05_audio_cues_dwell_trigger.png` | Audio cue triggered on science dwell |

### Milestone 10B — Emergency Injection
| File | Demonstrates |
|------|-------------|
| `outputs/m10b_01_mid_sortie_playback_pause.png` | Playback paused mid-route |
| `outputs/m10b_02_emergency_injection_drawer.png` | Emergency injection panel open |
| `outputs/m10b_03_continuation_tradeoff_eval.png` | 3-way continuation comparison |
| `outputs/m10b_04_3d_detour_preview_footprint.png` | Adaptive detour shown in 3D |
| `outputs/m10b_05_resumed_continuation_traversal.png` | Playback resumed on new route |

### Milestone 10C — Sortie Black Box
| File | Demonstrates |
|------|-------------|
| `outputs/m10c_01_black_box_event_ledger.png` | 3-event ledger with filter pills |
| `outputs/m10c_02_incident_event_detail.png` | CONTINGENCY filter, JSON inspector pane |
| `outputs/m10c_03_incident_replay_fidelity.png` | INCIDENT VERIFIED, 0 m / 0 s variance |

### Earlier Milestones
- `outputs/m9r_06_contingency_experiment_persisted.png` — Contingency Designer
- `outputs/m9z_0[1-5]_playback_*.png` — Mission Playback (Milestone 9Z)
- `outputs/marswalk_atlas_*.png` — Various Atlas UI states (9D–9Q era)

---

## 9. Known Bugs & Suspicious Areas

### Fixed in 10C (verify the fix is stable)
1. **`destination_rc` NoneType crash** — When no waypoints are set, `incident_replay.py` would fail with `TypeError: 'NoneType' object is not subscriptable` on `destination_rc[0]`. Fixed with a `None` guard in [`src/marswalk/core/incident_replay.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/incident_replay.py). The fix must remain; do not regress it.
2. **Mission ID mismatch** — The frontend was using continuation IDs (`cont_XXXX`) as the ledger key for root mission events. Fixed in `getActiveBlackBoxMissionId()` in `web/app.js` to prefer `"mission_nominal"` and fall back to the active mission ID only when a continuation is genuinely active.
3. **Schema-noncompliant event payloads** — `logMissionEvent()` originally sent payloads without the required `"event"` wrapper and missing required schema fields, causing HTTP 400 errors. Fixed to wrap in `{ "event": { ... } }` with all required fields.
4. **Unclosed HTML div** — `preflightModal` was missing its closing `</div>`, causing `blackBoxModal` to be nested inside it. Fixed in [`web/index.html`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/index.html).

### Open / Unverified
5. **Audio cue Web Audio API** — Synthesized audio uses the Web Audio API (oscillator-based beeps). Some browsers mute Web Audio until user interaction. If audio cues silently fail in a fresh browser session, this is expected browser behavior, not a bug.
6. **TSP permutation limit** — The exact TSP solver is used for ≤ 7 waypoints; 2-Opt kicks in above that. The 2-Opt solution is deterministic but not globally optimal. No regression test covers > 7 waypoints end-to-end.
7. **DTM boundary conditions** — Routes that exit the Jezero DTM coverage area fall back to flat-terrain approximation. There is no explicit boundary warning in the UI.
8. **Continuation playback from exact interruption** — The implementation interpolates rover position at the chosen `mission_time_s`. Verify that this interpolation is monotonically consistent with the original timeline before the interruption point.
9. **Evidence screenshots depend on CDP timing** — `capture_milestone_10c_evidence.py` uses fixed `asyncio.sleep()` delays. Slow machines or high server load can cause state to not yet be rendered when the screenshot fires. If evidence capture fails, increase sleep values.
10. **Test ledger cleanup** — Test files use unique prefixed IDs so they do not pollute live missions. However, the test runner does not delete `test_api_*_events.json` files. These accumulate in `data/workspaces/events/`. Safe to prune manually after confirming no tests are running.

---

## 10. Compatibility Concerns

- **Python version:** 3.12 (pinned in README badge). Do not upgrade without re-running the full suite.
- **Venv:** `.venv\` — always activate before running any `python` command. Use `.\.venv\Scripts\python.exe` explicitly in scripts to avoid PATH conflicts.
- **Three.js:** Loaded from CDN in `web/index.html`. No bundler. Any CDN version change requires regression testing of the 3D renderer.
- **Chrome CDP capture:** Evidence scripts require `chrome.exe --remote-debugging-port=9222`. Chromium-based browsers only. Firefox is not supported for CDP captures.
- **Schemas:** All API I/O is validated against `schemas/api/v1/*.schema.json`. Adding new fields to an endpoint requires updating the corresponding schema file first, then the service handler.
- **No external database:** Persistence is flat JSON files. Concurrent writes from multiple clients are not protected (single-user application).

---

## 11. Upcoming Milestone Sequence (10D & 10E)

The development roadmap has been refined to establish authentic Martian environmental intelligence prior to generating formal science reports:

- **Milestone 10D — Mars Environmental Intelligence:**
  Weather-source integration, freshness-aware updates, source provenance, regional atmospheric conditions, and environmental context for mission planning.
- **Milestone 10E — Mission Science Report & Export Dashboard:**
  Integrate existing mission plans, terrain-derived route analysis, sortie black-box event ledgers, and validated environmental weather snapshots into reproducible, exportable scientific reports and Decision Packs.

Completed milestones 9D through 10C remain immutable and fully verified (424/424 passing full-suite tests).

---

## 12. Mars Environmental & Weather Intelligence Specification (Milestone 10D Strategy)

### 12.1 Scientific Principles & Operational Realism
Planetary weather on Mars operates under starkly different operational realities compared to terrestrial meteorology:
- **No Global Real-Time Grid:** Mars does not possess a dense meteorological satellite or surface station network. Ground observations exist exclusively at sparse in-situ landed sites (e.g., Jezero Crater, Gale Crater, Elysium Planitia).
- **Telemetry Latencies & Archival Cadence:** Downlink passes via Mars relay orbiters (MRO, Odyssey, TGO, MAVEN) occur in discrete batches. Formal Planetary Data System (PDS) releases undergo multi-stage science validation and are published in archival tranches (often weeks or months after acquisition). "Live" ground observations from Mars reflect the most recently downlinked sol, not instant seconds-ago telemetry.
- **In-Situ Measurement vs. Climatology Model:** A numerical atmospheric model (such as the Mars Climate Database) is a climatological circulation model, **not a real-time weather forecast**. The system must explicitly label modeled data as `DATA_TYPE: CLIMATOLOGICAL_MODEL` and in-situ observations as `DATA_TYPE: IN_SITU_OBSERVATION`.
- **Spatial Separation & Prohibition of Spatial Projection:** Jezero Crater (Perseverance) and Gale Crater (Curiosity) are separated by approximately 3,700 km (~62° longitude, across hemispheres). Elysium Planitia (InSight) is ~3,400 km away. **Never project Gale or InSight sensor readings onto Jezero Crater as if they were local measurements.** Never silently interpolate point observations across planetary distances without explicit, attributed regional modeling.

### 12.2 Primary Data Sources Inventory & Ingestion Reality

Claude must inspect and evaluate each of the following primary sources during Milestone 10D implementation:

1. **Perseverance Mars 2020 MEDA (Mars Environmental Dynamics Analyzer):**
   - **Primary Archive:** [NASA PDS Mars 2020 MEDA Instrument Context](https://pds.nasa.gov/ds-view/pds/viewContext.jsp?identifier=urn:nasa:pds:context:instrument:mars2020.meda&version=1.0)
   - **Station Location:** Jezero Crater (18.44°N, 77.45°E) — the primary surface planning workspace for MarsWalk.
   - **Sensors:** Atmospheric Pressure Sensor (PS), Air Temperature Sensors (ATS at multiple mast heights), Ground Temperature Sensor (GTS - infrared thermopile), Wind Sensors (WS1 & WS2), Relative Humidity Sensor (HS), Radiation and Dust Sensor (RDS / optical depth $\tau$).
   - **Ingestion Strategy:** PDS4 bundles are formatted as XML labels with associated CSV/TAB tables. Claude must investigate whether an authenticated or open public endpoint, pre-packaged PDS release bundle, or recent mission telemetry table is most robust. For offline and CI test resilience, bundle a verified baseline dataset of authentic Jezero MEDA sol records in `data/weather/` rather than relying on unauthenticated brittle web scraping.

2. **Curiosity MSL REMS (Rover Environmental Monitoring Station):**
   - **Primary Archive:** [NMSU PDS Atmospheres MSL REMS Archive](https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/MARS/curiosity/rems.html)
   - **Station Location:** Gale Crater (4.59°S, 137.44°E).
   - **Sensors:** Daily maximum/minimum air temperature, ground temperature, atmospheric pressure, relative humidity, UV flux.
   - **Role:** Regional comparative context when exploring Gale Crater or investigating latitude-dependent atmospheric pressure cycles. Must remain strictly attributed to Gale Crater.

3. **Mars Climate Database (MCD v5.3 / v6):**
   - **Primary Access:** [Laboratoire de Météorologie Dynamique (LMD) / ESA / CNES](https://www-mars.lmd.jussieu.fr/mars/access.html)
   - **Product:** Derived global circulation model (GCM) simulation predicting diurnal and seasonal variations of surface pressure, temperature, wind vectors, and atmospheric density as a function of solar longitude ($L_s$) and coordinates.
   - **Role:** Provides authentic modeled climatological baselines across all gazetteer locations where no surface lander is present (e.g., Olympus Mons, Valles Marineris). Must be clearly distinguished from observed empirical data.

4. **NASA Mars Color Imager (MARCI) on MRO:**
   - **Primary Access:** [NASA Science Mars Color Imager (MARCI) MRO](https://science.nasa.gov/resource/mars-color-imager-marci-for-mars-reconnaissance-orbiter/)
   - **Product:** Wide-angle global daily weather maps, tracking regional dust storm progression, polar hood clouds, and atmospheric optical depth.
   - **Role:** Visual and synoptic atmospheric context; global dust alert status.

5. **NASA InSight Weather Archive:**
   - **Primary Access:** [NASA InSight Mars Weather Service](https://mars.nasa.gov/insight/weather/)
   - **Station Location:** Elysium Planitia (4.50°N, 135.62°E).
   - **Role:** Historical archive only (InSight operational lifetime: Sol 1 to Sol 1440, ending December 2022). Useful as a multi-year seasonal reference dataset and test calibration baseline, but must be explicitly badged as `HISTORICAL_MISSION_ARCHIVE`.

### 12.3 Realistic Update Behavior & Freshness Lifecycle

The weather architecture must implement a strict freshness-aware state machine:

- **Dashboard Scoping:** Centered on Jezero Crater by default, with dynamic switching based on the selected destination/mission region.
- **Freshness Classification:**
  - `CURRENT`: Observation acquired within nominal operational mission cadence (< 48 Earth hours or within 1–2 Martian sols of active telemetry).
  - `DELAYED`: Observation valid, but downlink telemetry or archive pipeline indicates expected multi-sol transmission lag.
  - `STALE`: Source checked successfully, but latest available record exceeds normal update threshold.
  - `HISTORICAL`: Mission has terminated or query references past sols/archived missions (e.g., InSight, past seasons).
  - `UNAVAILABLE`: Upstream source unreachable or no sensor coverage exists for the region.
  - `CACHED_FALLBACK`: Upstream network request failed or rate-limited; verified local cache served with prominent warning badge.
- **Required Metadata & Telemetry Fields:**
  - `observation_sol`: Martian Sol number (e.g., Sol 1024).
  - `observation_time_utc`: UTC timestamp of the measurement.
  - `solar_longitude_ls_deg`: Planetary season indicator ($L_s \in [0^\circ, 360^\circ)$).
  - `last_checked_utc`: Timestamp when Atlas checked the source.
  - `cache_age_seconds`: Elapsed time since local cache write.
  - `provenance`: Full attribution including source organization, instrument name, platform, archive DOI/URL, and data tier (measured vs modeled).
  - `measurements`:
    - Surface Atmospheric Pressure ($P$ in Pascals / hPa).
    - Air Temperature ($T_{air}$ in °C and K, with sensor height).
    - Ground / Surface Temperature ($T_{ground}$ in °C and K).
    - Wind Velocity & Direction ($v$ in m/s, bearing in degrees, with gust metrics if available).
    - Atmospheric Dust Opacity ($\tau$ / optical depth at 880 nm).
    - Ambient UV / Solar Irradiance ($W/m^2$).
- **Update Controls:**
  - Manual "Refresh Weather" trigger in UI.
  - Bounded automatic polling (configurable TTL, minimum interval $\ge 15$ minutes to prevent rate-limiting).
  - Fallback cache stored under `data/weather/` or `data/workspaces/weather_cache/`.

### 12.4 Integration with Mission Planning (Safety & Provenance Boundary)
- **Non-Intrusive by Default:** Environmental data must NOT silently tamper with the existing A* heuristic, pathfinding costs, or Minetti metabolic walking speeds.
- **Advisory Operational Context:** Display weather impacts as advisory operational constraints:
  - High dust opacity ($\tau > 1.5$) flags reduced solar array power and degraded visibility.
  - Extreme low temperatures ($< -80^\circ\text{C}$) flag battery thermal heater overhead.
  - Elevated wind speeds flag rover mast stability considerations.
- **Decision Pack & Ledger Snapshotting:** When a user saves a mission, logs an incident, or exports a Decision Pack, capture the active environmental state as an immutable, timestamped `weather_snapshot` inside the bundle. This ensures that past routing decisions can be audited against the exact atmospheric context at rehearsal time.

### 12.5 Test Suite Requirements for Milestone 10D
The incoming agent must implement focused tests covering:
1. **Freshness State Machine:** Correct transitions between `CURRENT`, `DELAYED`, `STALE`, `HISTORICAL`, and `UNAVAILABLE`.
2. **Missing Sensor Tolerance:** Partial telemetry payloads (e.g., wind sensor failure on Sol 400+) do not crash the service; missing fields are explicitly `null` with flags.
3. **Network Resilience & Fallback:** Simulating 503/timeout from upstream sources correctly engages `CACHED_FALLBACK` without data loss or fabricated numbers.
4. **Unit Verification:** Consistent conversion between Pa/hPa, Kelvin/Celsius, m/s/km/h; out-of-physical-range rejection ($T < 100\text{K}$ or $P > 2000\text{Pa}$).
5. **Provenance & Coordinate Guard:** Rejection of mismatched regional coordinates (preventing Gale REMS from satisfying a Jezero query without explicit disclaimer); clear separation of climatology vs in-situ measurements.
6. **Schema Compliance:** Validation of all responses against a new `weather-report.schema.json`.

---

## 13. Copy-Ready First-Session Prompt for Claude

Paste the following as the first message in a new Claude session:

---

```
# MarsWalk 2.0 — Claude Engineering Takeover: Milestone 10D

You are taking over development of the MarsWalk 2.0 / Project Atlas repository.

**Workspace:** E:\Python\NASA-Spaceapps\Marswalk
**Primary reference:** docs/CLAUDE_ENGINEERING_HANDOFF.md  ← read this first

## Immediate Orientation & Baseline Verification (before writing code)

1. Read docs/CLAUDE_ENGINEERING_HANDOFF.md in full.
2. Verify that the repository is completely clean and all tests pass:
   .\.venv\Scripts\python.exe scripts/preflight_check.py --port 3000
   .\.venv\Scripts\python.exe -m pytest
   (Expected baseline: 424 passed full suite, 12/12 preflight passed).
3. Confirm existing persistence rules from AGENTS.md:
   - Work strictly within E:\Python\NASA-Spaceapps\Marswalk.
   - Never delete data/workspaces/missions/, experiments/, or events/ files.
   - Do not commit, push, deploy, or download large (>100MB) external files.
   - Distinguish measured observations, derived quantities, and model estimates.

## Milestone 10D Objective: Mars Environmental Intelligence

Implement an authentic, freshness-aware Martian weather and atmospheric intelligence service for Project Atlas:

1. **Inspect Official Sources:**
   - Perseverance MEDA (Jezero Crater): https://pds.nasa.gov/ds-view/pds/viewContext.jsp?identifier=urn:nasa:pds:context:instrument:mars2020.meda&version=1.0
   - Curiosity REMS (Gale Crater): https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/MARS/curiosity/rems.html
   - Mars Climate Database (MCD): https://www-mars.lmd.jussieu.fr/mars/access.html
   - MARCI MRO Imagery: https://science.nasa.gov/resource/mars-color-imager-marci-for-mars-reconnaissance-orbiter/
   - InSight Archive (historical reference only): https://mars.nasa.gov/insight/weather/

2. **Core Deliverables:**
   - Backend module: `src/marswalk/core/weather.py` (or `environmental_intelligence.py`)
   - Schema: `schemas/api/v1/weather-report.schema.json`
   - API endpoints in `src/marswalk/api/service.py` and `scripts/run_atlas.py`:
     - `GET /api/weather/current?region=jezero`
     - `POST /api/weather/refresh`
   - Caching & Fallback: Local file-backed cache with freshness lifecycle (`CURRENT`, `DELAYED`, `STALE`, `HISTORICAL`, `UNAVAILABLE`, `CACHED_FALLBACK`).
   - UI Integration: Atmospheric intelligence widget / drawer in `web/index.html`, `web/app.js`, `web/styles.css` displaying Jezero conditions, observation sol, timestamps, cache age, source attribution, and units.
   - Comprehensive Tests: Dedicated suite in `tests/test_milestone_10d_weather_intelligence.py` (~20 tests).

Begin by reviewing docs/CLAUDE_ENGINEERING_HANDOFF.md and running the baseline checks, then present your implementation plan for Milestone 10D.
```

---

## 14. File Change Log (Milestone 10C & Handoff Updates)

The following files were created or modified during Milestone 10C and the subsequent handoff updates:

| File | Change |
|------|--------|
| `docs/CLAUDE_ENGINEERING_HANDOFF.md` | Created comprehensive engineering handoff; updated with Milestone 10D/10E sequence and Mars Environmental Intelligence specification. |
| `web/app.js` | +~500 lines: black-box modal, `logMissionEvent()`, `openBlackBoxModal()`, `loadBlackBoxEvents()`, `renderBlackBoxEvents()`, `selectBlackBoxEvent()`, `triggerIncidentReplay()`, `getActiveBlackBoxMissionId()`. Event logging added to `playMissionPlayback()`, `calculateMissionContinuation()`, `applyMissionContinuation()`. `window.__atlas` debug exports added. |
| `web/index.html` | Fixed missing `</div>` closing tag for `preflightModal`; added `blackBoxModal` HTML structure. |
| `web/styles.css` | Black-box modal styles, event filter pills, incident detail panel, fidelity score badge. |
| `src/marswalk/core/incident_replay.py` | Added `None` guard for `destination_rc` to prevent crash when no waypoints are set. |
| `src/marswalk/core/mission_continuation.py` | Updated `source_mission_id` default to `or "mission_nominal"`. |
| `src/marswalk/core/mission_event_ledger.py` | New file: event storage, retrieval, filter-by-type, statistics. |
| `src/marswalk/api/service.py` | Added `POST /api/mission/events`, `GET /api/mission/events/<id>`, `POST /api/mission/replay` handlers. |
| `schemas/api/v1/mission-event.schema.json` | New schema for black-box event payloads. |
| `schemas/api/v1/incident-replay-response.schema.json` | New schema for replay fidelity responses. |
| `tests/test_milestone_10c_sortie_black_box.py` | 20 new tests covering ledger, replay, and API contracts. |
| `scripts/capture_milestone_10c_evidence.py` | Chrome CDP evidence capture script. |
| `docs/milestone-10c-design.md` | Milestone design specification. |
| `docs/milestone-10c-report.md` | Verification report with test results. |
| `README.md` | Tests badge updated 404→424; Section 15 (Sortie Black Box) added; pointer to Engineering Handoff. |

---

*This document was generated and refined by the outgoing Gemini/Antigravity agent. The incoming agent should verify all claimed test counts and preflight results independently before relying on them.*
