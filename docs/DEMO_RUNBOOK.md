# MarsWalk 2.0 (Project Atlas) — V1 Demonstration Runbook & Operator Guide

This runbook guides operators, judges, and developers through demonstrating the complete MarsWalk 2.0 planetary mission rehearsal workflow.

---

## 1. Quick Launch (60-Second Setup)

### Option A: Interactive Browser Demonstration (Recommended)
```powershell
# 1. Start MarsWalk Atlas workstation (Port 3000)
.\scripts\start_marswalk.ps1
# (or on cmd: scripts\start_marswalk.bat)

# 2. Run Preflight Diagnostics
python scripts\preflight_check.py --port 3000
```
Open your browser to: **`http://127.0.0.1:3000`**

### Option B: Automated Headless Demonstration & Export
```powershell
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe scripts\run_demonstration.py
```
Generates verified HTML, JSON, CSV, and Markdown dossiers into `outputs/demonstration/`.

---

## 2. Ten-Stage Demonstration Walkthrough

| Stage | Action / UI Trigger | Expected Visible Outcome | Recovery Step if Stage Fails |
| :--- | :--- | :--- | :--- |
| **01. Workstation & Topography** | Open `http://127.0.0.1:3000`. Globe loads with Viking MDIM 2.1 color basemap; fly to Jezero Crater. | 3D terrain canvas renders Jezero Crater at 20m/px USGS CTX resolution. HUD shows server `online` and elevation bounds ($-2624$m to $-2445$m). | If canvas is blank, verify WebGL is enabled in browser (`chrome://gpu`) or run `python scripts/preflight_check.py`. |
| **02. Mission Selection** | Select `m_jezero_delta_scarp_surve_090607` ("Jezero Delta Scarp Survey") from Saved Missions dropdown. | Start coordinates `(117, 157)` and Goal `(194, 131)` populate with 2 sequenced science waypoints. | If dropdown is empty, check `data/workspaces/missions/` directory permissions. |
| **03. Route Planning & Metrics** | Click **"Calculate Route"** (`#btnCalculateRoute`). | Optimal green traversal path drawn across DTM. Inspector displays: Distance: $3,149$m, Traverse Time: $\approx 113$ min, Max Slope: $4.6^\circ$. | If route fails, check that Start and Goal are not placed in NoData or steep cliff $>15^\circ$. |
| **04. Playback & Disruption** | Open Playback drawer, press Play, seek to $t=600$s, click **"Inject Contingency"** (`#btnEmergencyInjection`). | Vehicle marker advances along route. Emergency modal opens; select Rockfall/Corridor Closure ($60$m radius). | If vehicle does not animate, check that speed multiplier is set $\ge 1.0\times$. |
| **05. 3-Stage Trade-Off** | Click **"Calculate Continuation"** (`#btnCalcContinuation`). | Three-stage comparison table populates: Nominal Remaining ($1,737$m) vs Disrupted (Blocked) vs Adaptive Detour ($1,737$m). Recommendation displayed. | If detour is unreachable, reduce hazard radius or increase operational budget limit. |
| **06. Sortie Black Box** | Click **"Sortie Black Box"** (`#btnHeaderBlackBox`). | Chronological event ledger displays: `sortie_started`, `contingency_injected`, and `continuation_selected` with exact coordinates and timestamps. | If ledger is empty, verify `data/workspaces/events/` is writable. |
| **07. Environmental Intel** | Inspect Environmental Widget / Weather HUD. Click site selector to toggle Jezero Crater vs Olympus Mons. | Jezero displays: `IN_SITU_OBSERVATION` (Sol 1619, $589.69$ Pa, wind null). Olympus Mons displays: `CLIMATOLOGICAL_MODEL` (MCD v6.1, $72.4$ Pa). | If external PDS network is down, engine seamlessly uses offline local cache (`data/weather/`). |
| **08. Mission Science Report** | Click **"Generate Report"** in header or workspace menu. | Report modal displays executive summary, mobility metrics, and provenance manifest. Click **"Download HTML"** and **"Download JSON"**. | Check browser popup blocker if file download prompt does not trigger. |
| **09. Decision Gate Audit** | Click **"Mission Readiness"** (`#btnHeaderReadiness`). | Decision Gate modal opens with overall score ($95.0\%$), status `CONDITIONAL`, 4 category status cards, and actionable findings with evidence references. | If status is `BLOCKED`, inspect findings accordion for route reachability or budget issues. |
| **10. Decision Pack Export** | Click **"Export Decision Pack"** (`#btnExportDecisionPack`). | Generates audit ZIP bundle containing canonical run bundle JSON, RFC 4180 comparison CSV, Markdown briefing, and SHA-256 integrity manifest. | Run `python -c "from marswalk.api.decision_pack import verify_bundle_integrity; ..."` to audit offline. |

---

## 3. Operator Troubleshooting & Edge Recovery

### Issue: Port 3000 is occupied by a prior process
- **Diagnosis:** `netstat -ano | findstr :3000` shows `LISTENING`.
- **Resolution:**
  ```powershell
  # Probe if it's already an active MarsWalk server:
  Invoke-RestMethod http://127.0.0.1:3000/api/health
  # If so, simply open http://127.0.0.1:3000
  # If a rogue process occupies it, terminate by PID:
  Stop-Process -Id <PID> -Force
  ```

### Precise Offline Capabilities & Asset Architecture
MarsWalk 2.0 is designed for high resilience in field and competition presentation environments:
- **100% Offline Core Subsystems:**
  - Python A* cost surface and kinematic route planning.
  - Authentic USGS CTX 20m Jezero Crater GeoTIFF DTM (`data/processed/jezero_ready_20m.tif`).
  - Planetary nomenclature gazetteer (2,061 landmarks).
  - Playback engine, mid-sortie emergency injection, and adaptive replanning.
  - Sortie Black Box append-only JSONL ledgers.
  - Mission Science Report generation and dual HTML/JSON dossiers.
  - Mission Readiness Decision Gate evaluations and Decision Pack cryptographic verification.
  - Environmental Intelligence: Bundled NASA PDS MEDA baseline observations (Sol 1619) and MCD v6.1 climatological models operate without internet connection.
- **Visual & Web Assets:**
  - Three.js 3D viewport libraries (`three.min.js`, `OrbitControls.js`) are bundled locally in `web/libs/`.
  - Report HTML exports embed internal CSS styling and system font fallbacks (`-apple-system`, `Segoe UI`, `Roboto`, `monospace`) requiring no external font downloads.
  - *Optional External Assets:* If an internet connection is available, the global landing page can load Google Web Fonts (`Cinzel`, `Inter`, `JetBrains Mono`) and CesiumJS (`cesium.com CDN`); when offline, the interface falls back seamlessly to local system typography and Three.js 3D terrain canvas without breaking core mission planning functionality.

### Issue: Route Planning Takes $>5$ Seconds
- The Jezero CTX DTM is a $250 \times 250$ grid ($62,500$ cells). Standard A* traversals complete in $<150$ms.
- If planning stalls, verify that the start/goal points are within the Jezero bounding box (Rows: 0–249, Cols: 0–249).

---

## 4. Deliverable Verification Checklist for Judges

Run this quick command to verify all generated deliverables:
```powershell
Get-ChildItem outputs\demonstration
```
Expected output files:
1. `jezero_mission_science_report.html` — Self-contained responsive HTML dossier with CSS styling and charts.
2. `jezero_mission_science_report.json` — Draft 2020-12 valid structured JSON mission report.
3. `decision_pack_comparison.csv` — RFC 4180 compliant 8-metric trajectory comparison table.
4. `mission_decision_briefing.md` — Markdown briefing for flight directors and science teams.
