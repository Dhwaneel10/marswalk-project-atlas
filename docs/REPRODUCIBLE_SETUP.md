# Project MarsWalk 2.0 / Atlas — Clean-Start Reproduction & Setup Guide
**Document ID:** `DOC-MW-M7-REPRODUCIBLE-SETUP`  
**Platform:** Ubuntu 22.04 LTS (x86_64) | **Python:** 3.10 (`.venv`)  
**Target Audience:** NASA Space Apps Evaluators, Peer Reviewers, Systems Auditors  

---

## 1. Prerequisites & Environment Architecture

MarsWalk 2.0 runs locally on Linux with zero cloud dependencies. It relies on an isolated Python 3.10 virtual environment (`.venv`) and standard native packages.

### System Requirements:
- **Operating System:** Ubuntu 22.04 LTS (or compatible Linux x86_64 distribution).
- **Python:** Python 3.10.x (with `python3-venv` and `python3-pip`).
- **Node.js (Optional):** Node 16+ (used solely for offline static syntax verification via `node -c`).
- **Web Browser:** Google Chrome, Chromium, or Mozilla Firefox with WebGL support.
- **Port:** Port `3000` (configurable via `--port <PORT>`).

---

## 2. Clean-Start Verification Procedure (Step-by-Step)

Follow these exact steps from a clean terminal to ensure an isolated, deterministic execution:

### Step 1: Clone or Navigate to the Workspace
```bash
cd /home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission
```

### Step 2: Stop Any Pre-Existing MarsWalk or Atlas Server
Ensure port `3000` is free:
```bash
# Check if port 3000 is occupied
lsof -i :3000 || ss -tulpn | grep 3000 || true

# If a previous instance is running, terminate it cleanly:
pkill -f "run_atlas.py" || true
sleep 1
```

### Step 3: Bootstrap Python Virtual Environment & Dependencies
```bash
# Verify Python 3.10 availability
python3 --version

# Run the automated setup script (creates .venv, installs pinned requirements):
./scripts/setup_atlas.sh
```
*Note: Dependencies are strictly installed into `.venv`. System Python is never modified.*

### Step 4: Launch the Atlas Operations Workstation
```bash
# Start the HTTP REST service and static workstation daemon:
./scripts/start_atlas.sh --port 3000 --no-browser
```
*Expected Terminal Output:*
```
[MarsWalk Atlas] Preloading Jezero terrain from .../data/processed/jezero_ready_20m.tif...
[MarsWalk Atlas] Terrain preloaded (250x250). 12 waypoints ready.
========================================================================
  MARSWALK 2.0 — PROJECT ATLAS: 3D PLANETARY WORKSTATION & LIVE API
  Local Web URL:    http://127.0.0.1:3000
  Health Status:    http://127.0.0.1:3000/api/health (GET)
========================================================================
```

### Step 5: Verify Service Health & Endpoint Readiness
In a separate terminal or curl session:
```bash
curl -s http://127.0.0.1:3000/api/health | jq .
```
*Expected JSON Response:*
```json
{
  "status": "online",
  "engine": "MarsWalk 2.0 Routing Intelligence",
  "target": "Mars (IAU 2000 Sphere / USGS CTX DTM 20m)",
  "terrain_loaded": true,
  "waypoints_count": 12
}
```

### Step 6: Execute the Single-Command Release Preflight Pipeline
Run the consolidated qualification engine:
```bash
./scripts/release_preflight.sh 3000
```
This single script executes all 9 quality gates:
1. Virtual environment and JavaScript syntax checks.
2. Planetary data SHA-256 integrity audit (8/8).
3. Planetary science validation gates (25/25).
4. Five-pillar integration pytest suite (8/8).
5. Flagship resilience pytest suite (9/9).
6. Live HTTP service health check.
7. One-command flagship showcase execution.
8. Chrome DevTools Protocol (CDP) headless Golden Path audit (7/7).
9. Official release manifest build.

---

## 3. Data Acquisition & Storage Architecture

MarsWalk enforces non-fabrication guarantees. Datasets are acquired from primary planetary science repositories and verified cryptographically on disk:

```
data/
├── raw/
│   ├── ctx/               # USGS Astrogeology Jezero CTX 20m Stereo DEM (DOI: 10.5066/P9T31O12)
│   ├── hirise/            # USGS TRN HiRISE 1m DTM Hawksbill Gap Window (DOI: 10.5066/P13CPYYU)
│   └── m2020_places/      # NASA PDS Mars 2020 Rover PLACES Tactical Sites (best_tactical.csv)
├── processed/
│   ├── jezero_ready_20m.tif # Cleaned, nodata-masked, georeferenced GeoTIFF (250x250 cells)
│   └── hirise_1m.tif      # 1.0 m/px Hawksbill Gap sub-grid (600x600 cells)
├── catalogs/
│   ├── three_forks_sample_depot.json       # NASA JPL 10-Tube Cache Manifest
│   ├── meda_environmental_observations.json # NASA PDS MEDA Atmospheric Observations
│   └── geolocated_science_targets.json    # Astrobiology Targets (SHERLOC / PIXL)
└── manifests/
    └── nasa_data_provenance_manifest.json  # Master SHA-256 Provenance Ledger
```

### Re-Authenticating Datasets:
Evaluators can re-verify all 8 planetary datasets at any time:
```bash
.venv/bin/python scripts/audit_nasa_data.py
```
If any file is corrupted or missing, the audit will immediately exit with a failure code and report the offending path.

---

## 4. Browser Workstation Verification

### Manual Browser Verification:
1. Open Google Chrome, Firefox, or any modern browser to:  
   **[http://127.0.0.1:3000/](http://127.0.0.1:3000/)**
2. Confirm the 3D WebGL Jezero Crater terrain loads with contour shaders and hypsometric tinting.
3. In the top-right header of the Five-Pillar Deck, click the yellow **`★ EVALUATOR TOUR`** button.
4. Click `[▶ EXECUTE STEP ACTION]` on each step to watch the automated inspection, 3D camera focusing, and trade study tables.

### Automated Headless Browser Verification (CDP):
If running in a headless Linux environment without an X11 desktop display:
```bash
.venv/bin/python scripts/audit_golden_path_browser.py
```
This launches `/usr/bin/google-chrome --headless=new`, navigates to `http://127.0.0.1:3000`, executes all 7 steps via Chrome DevTools Protocol, verifies 0 unhandled console errors, and captures a 1080p visual proof PNG to:
`outputs/browser_qa/evaluator_golden_path_live.png`.

---

## 5. Troubleshooting & FAQ

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `Address already in use: 3000` | Stale background server process running | Run `pkill -f "run_atlas.py"` or pass an alternate port: `./scripts/start_atlas.sh --port 3001` |
| `ModuleNotFoundError: No module named 'rasterio'` | Executing with system Python instead of `.venv` | Always invoke with `.venv/bin/python` or run `./scripts/run_tests.sh` |
| `PluginValidationError: unknown hook 'pytest_launch...'` | Host ROS 2 Humble environment in `PYTHONPATH` | Use `./scripts/run_tests.sh`, which sanitizes `PYTHONPATH` and disables external launch plugins |
| `Headless Chrome: Connection refused on 9498` | Chrome already running or port in use | Script automatically manages ephemeral profiles; kill stray Chrome processes with `pkill -f chrome` |
