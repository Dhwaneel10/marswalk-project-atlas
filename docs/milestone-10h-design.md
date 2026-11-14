# MarsWalk 2.0 — Milestone 10H: V1 Release Candidate, Reproducible Setup & Demonstration Package
## Technical Architecture & Engineering Design Specification

### 1. Overview & Objective
Milestone 10H represents the final planned packaging, reproducibility hardening, and acceptance milestone for MarsWalk 2.0 / Project Atlas. It ensures that the application can be cleanly installed, verified, demonstrated, and handed over to other engineers, judges, and teammates without undocumented dependencies, hardcoded developer paths, or external network requirements.

Key design goals:
1. **Zero-Friction Reproducible Setup:** Single-command virtual environment dependency installation with standardized `requirements.txt` and `pyproject.toml`.
2. **Deterministic Dual Launchers:** Both PowerShell (`scripts/start_marswalk.ps1`) and Windows Batch (`scripts/start_marswalk.bat`) launchers featuring automatic port collision detection, existing server health probing, and clean daemon lifecycle management.
3. **Repeatable 10-Stage Demonstration Engine:** Standalone script (`scripts/run_demonstration.py`) and operator runbook (`docs/DEMO_RUNBOOK.md`) covering the end-to-end planning, playback, emergency injection, black-box logging, environmental telemetry, reporting, and decision-gate workflows.
4. **100% Offline Resilience:** Bundled authentic USGS CTX 20m raster topography, IAU planetary gazetteers, Viking MDIM basemaps, and NASA PDS weather observation caches that function without internet access.
5. **Data Preservation & Defensive Governance:** Strict non-destructive invariant ensuring saved missions, experiments, event ledgers, and Decision Packs remain intact across installations and test runs.

---

### 2. Architecture & Packaging Matrix

```
+---------------------------------------------------------------------------------------------------+
|                                 MARSWALK 2.0 REPRODUCIBLE PACKAGING                               |
+---------------------------------------------------------------------------------------------------+
|  [pyproject.toml]            [requirements.txt]             [start_marswalk.ps1 / .bat]          |
|  - Python >= 3.10            - Core Numerical & Geo         - Port 3000 Collision Detection      |
|  - Setuptools build backend  - Data Contracts & JSON Schema - Health Probing (/api/health)       |
|  - Standardized entrypoints  - WebSocket / CDP Automation   - Daemon Lifecycle Management        |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                                    OFFLINE ASSET REPOSITORY                                       |
+---------------------------------------------------------------------------------------------------+
|  Topography:    data/processed/jezero_ready_20m.tif (20 m/pixel USGS CTX DTM GeoTIFF)             |
|  Basemap:       web/public/assets/mola_viking_232m.jpg (USGS MDIM 2.1 Color Basemap)              |
|  Gazetteer:     data/raw/MARS_nomenclature_center_pts.kml (2,061 IAU Planetary Features)         |
|  Weather Cache: data/weather/baseline_jezero_meda.json (Perseverance MEDA Sol 1619 In-Situ)      |
|                 data/weather/baseline_olympus_mcd.json (Mars Climate Database v6.1 Climatology)   |
|  Workspaces:    data/workspaces/missions/ (Persistent saved mission definitions)                  |
|                 data/workspaces/events/ (Sortie Black Box append-only JSONL ledgers)              |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
+---------------------------------------------------------------------------------------------------+
|                                   VERIFICATION & DEMONSTRATION                                    |
+---------------------------------------------------------------------------------------------------+
|  Preflight Check:     python scripts/preflight_check.py --port 3000 (12/12 Automated Diagnostics) |
|  Regression Suite:    pytest -q (504 Automated Tests, 100% Pass Rate in ~230s)                   |
|  10-Stage Rehearsal:  python scripts/run_demonstration.py (Repeatable End-to-End Demonstration)    |
|  Operator Guide:      docs/DEMO_RUNBOOK.md (Checklist, visible outcomes, recovery steps)          |
|  Acceptance Audit:    docs/V1_RELEASE_CHECKLIST.md (Full multi-category verification sign-off)    |
+---------------------------------------------------------------------------------------------------+
```

---

### 3. Ten-Stage Demonstration Architecture

The repeatable demonstration runner (`scripts/run_demonstration.py`) executes 10 sequential operational milestones against authentic USGS CTX Jezero Crater terrain:

1. **Atlas Server Launch & Terrain Overview:** Probes `/api/health`, verifies 24 endpoints, loads 20m GeoTIFF raster, extracts elevation range ($-2624$m to $-2445$m).
2. **Saved Mission Selection & Baseline Planning:** Retrieves mission `m_jezero_delta_scarp_surve_090607`, parses canonical start `(117, 157)` and goal `(194, 131)`, computes optimal A* traversal ($72$ms).
3. **Mission Target Waypoints & Traverse Metrics:** Calculates $3,149$m ground distance, $113$ min traverse duration, $32$m climb, $4.6^\circ$ max slope, and sequences science stops (Three Forks Depot, Artuby Ridge Scarp).
4. **Kinematic Playback & Mid-Sortie Emergency Injection:** Builds continuous kinematic model, advances vehicle to $t=600$s, captures exact state without budget double-counting, and injects a $60$m radius rockfall corridor closure.
5. **3-Stage Trajectory Trade-Off Evaluation:** Evaluates nominal remaining vs disrupted remaining vs adaptive detour, computing detour overhead and operational recommendation (`ABORT_TO_DIRECT_BASELINE`).
6. **Sortie Black-Box Event Ledger History:** Appends chronological sortie events to `outputs/demonstration/events/` and queries them back with sub-second timestamps.
7. **Environmental Intelligence & Source Provenance:** Retrieves Perseverance MEDA in-situ observations (Sol 1619, $589.69$ Pa, null wind speed preservation) and verifies Olympus Mons MCD v6.1 climatological model fallback ($72.4$ Pa).
8. **Mission Science Report Generation & HTML/JSON Export:** Assembles comprehensive report dossier with reproducibility manifest, saving standalone HTML and JSON deliverables.
9. **Mission Readiness & Decision Gate Assessment:** Evaluates planning assurance across 4 categories (feasibility, environmental, robustness, provenance), yielding readiness score ($95.0\%$) and actionable findings.
10. **Decision Pack Cryptographic Verification & Export:** Computes SHA-256 computation fingerprint and execution digest, verifies bundle integrity, and exports RFC 4180 comparison CSV and flight director Markdown briefing.

---

### 4. Path Independence & Cross-Platform Conventions

To ensure MarsWalk operates reliably on any machine without developer-specific dependencies:
- **Zero Absolute Developer Paths:** All scripts derive the project root dynamically via `PROJECT_ROOT = Path(__file__).resolve().parent.parent`.
- **Artifact Directory Fallback:** Evidence capture scripts check for optional environment variables (`MARSWALK_ARTIFACT_DIR`) and mirror files to the conversation artifact store only when present, defaulting cleanly to repository-relative `outputs/`.
- **Platform-Neutral Process Management:** Startup scripts inspect local network sockets using OS-appropriate utilities (`Get-NetTCPConnection` on PowerShell, `netstat` on batch) to prevent port locking or daemon duplication.
