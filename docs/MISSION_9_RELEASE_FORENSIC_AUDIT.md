# Mission 9: Release Candidate Forensic Audit Report

**Document Identifier:** `MW-M9-FORENSIC-AUDIT`  
**Target Release Candidate:** `v2.0.0-rc1`  
**Archive File:** `outputs/releases/marswalk-v2.0.0-rc1.tar.gz`  
**Archive Checksum File:** `outputs/releases/marswalk-v2.0.0-rc1.sha256`  
**Expected SHA-256 Digest:** `8604af64bac2ed24486bc370e01d4965f13f6c23a0fc1b18a6b1803b6977218a`  
**Auditor:** MarsWalk Lead Systems Engineer & Release Qualification Auditor  
**Audit Date:** 2026-11-14T22:05:00+05:30  
**Git Baseline Commit:** `d2ffdd1` (`feat(release): Mission 8 certified Release Candidate 1 (v2.0.0-rc1)`)  
**Audit Target Branch:** `mission-9-clean-room-submission` (branched from `mission-8-release-candidate`)  

---

## 1. Executive Summary & Forensic Verdict

A comprehensive forensic inspection of Release Candidate 1 (`v2.0.0-rc1`) was conducted across Git repository provenance, archive packaging integrity, filesystem hygiene, dataset bundling completeness, and launch dependencies.

### Forensic Verdict: **CONDITIONALLY SELF-CONTAINED WITH ONE PACKAGING DEFECT (MW-M9-DEF-01)**
The release candidate archive successfully bundles all application code, Three.js 3D web assets, pytest verification harnesses, PDS rover waypoints, Three Forks sample depot records, and historical MEDA weather series without leaking developer virtual environments, binary caches, secrets, or hardcoded absolute paths. 

**However, one critical data packaging defect was discovered:**
The raw USGS CTX 20m digital elevation model raster (`data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`, 9.66 MB) was excluded from the archive by `scripts/package_release.py`. While the runtime server and 3D UI execute normally using the processed sub-raster (`data/processed/jezero_ready_20m.tif`), the preflight verification gate (`scripts/audit_nasa_data.py` / Gate 2) directly audits the master manifest entry `USGS_CTX_DEM_RAW_20M`. Consequently, in a strict clean-room environment lacking this raw raster, Gate 2 fails with a file-missing error.

---

## 2. Git Repository & Source Provenance Audit

| Dimension | Audit Observation | Status |
| :--- | :--- | :--- |
| **Active Branch** | `mission-9-clean-room-submission` branched cleanly from `mission-8-release-candidate` | **PASS** |
| **Commit HEAD** | `d2ffdd1`: `feat(release): Mission 8 certified Release Candidate 1 (v2.0.0-rc1)` | **PASS** |
| **Preceding Commit** | `e0cdca8`: `chore(baseline): Mission 7 certified state before Mission 8 sprint` | **PASS** |
| **Working Tree** | Completely clean (`git status --short` returns empty) | **PASS** |
| **Untracked Files** | 0 untracked files in source, web, or test directories | **PASS** |
| **Reference Isolation** | Reference folder `Atlas-Source/MarsWalk` remains strictly untouched | **PASS** |

---

## 3. Archive Physical Integrity & Checksum Verification

The archive was verified against its companion SHA-256 checksum file using GNU coreutils `sha256sum`:

```bash
cd outputs/releases && sha256sum -c marswalk-v2.0.0-rc1.sha256
```
**Output:** `marswalk-v2.0.0-rc1.tar.gz: OK`

### Archive Metrics
- **Filesystem Path:** `/home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/outputs/releases/marswalk-v2.0.0-rc1.tar.gz`
- **File Size:** `9,263,702 bytes` (8.83 MB)
- **Archive Format:** POSIX `tar` archive compressed with `gzip`
- **Total Archived Members:** 1,040 files
- **Root Directory in Archive:** `marswalk-v2.0.0-rc1/` (standard single-root packaging)
- **Top-Level Directories:** `src/`, `web/`, `scripts/`, `tests/`, `docs/`, `data/`
- **Top-Level Configuration:** `pyproject.toml`, `requirements.txt`, `requirements-lock.txt`, `README.md`, `AGENTS.md`, `DATA_PROVENANCE_AND_LICENSES.md`, `THIRD_PARTY_NOTICES.md`, `.env.example`, `.gitignore`

---

## 4. Exclusion & Cleanliness Audit (No Leaks or Secrets)

The archive was scanned using regular expressions for accidental inclusion of development artifacts, Python bytecode, virtual environments, or secrets:

```bash
tar -ztvf outputs/releases/marswalk-v2.0.0-rc1.tar.gz | grep -E "(\.pyc|\.git/|\.venv|venv/|\.env$|__pycache__|secrets)"
```

### Scan Results:
- **`__pycache__/` and `*.pyc`:** **0 instances** (cleanly excluded).
- **`.git/` directory:** **0 instances** (cleanly excluded; only `.gitignore` and `.gitkeep` present).
- **`.venv/` and `venv/`:** **0 instances** (cleanly excluded).
- **Local environment secrets (`.env`):** **0 instances** (only public template `.env.example` included).
- **Developer scratch directories:** **0 instances**.
- **Intermediate browser screenshots:** **0 instances** (`outputs/browser_qa/` excluded from archive).

---

## 5. Repository vs Archive Differential Comparison

Comparing the working repository against the 1,040 archived files:

### A. Code, Tests, and Documentation (100% Bundled)
- **`src/`:** All 87 Python modules included (API routes, terrain analysis, A* planner, DTN resilience, Merkle auditing).
- **`web/`:** Complete frontend included (`index.html`, `app.js`, `styles.css`, Three.js libraries, assets, static place catalogs).
- **`scripts/`:** All operational launchers, preflight gates, CDP audit runners, and packaging tools included.
- **`tests/`:** All pytest suites included (NASA data integration, cross-pillar, When Mars Goes Dark, API resilience).
- **`docs/`:** All historical and Mission 8 reports included.

### B. Data Directory Inventory (Differential Analysis)
The workspace repository contains 5,313 data files, of which **39 certified core datasets** are included in the archive:
- **Included Datasets:**
  1. `data/catalogs/` (5/5 JSON catalogs: places, sample depot, science targets, MEDA observations, curated waypoints).
  2. `data/manifests/` (`nasa_data_provenance_manifest.json`).
  3. `data/processed/` (`jezero_ready_20m.tif` [252 KB], `jezero_hirise_hawksbill_1m.tif` [1.44 MB]).
  4. `data/missions/` (`mission_when_mars_goes_dark.json` [2.18 KB]).
  5. `data/weather/` (5/5 weather baselines: Gale REMS, InSight, Jezero MEDA, Olympus MCD, cache).
  6. `data/preferences/` (`commander_preferences.json`).
  7. `data/environment/` (17/17 raw MCD/MEDA series, normalized series, and uncertainty audits).
  8. `data/waypoints_jezero.json` (6.62 KB).
  9. `data/raw/` (`pds_places_best_tactical.csv`, `pds_three_forks_sample_drops.csv`, `nasa_m20_traverse.json`, `nasa_m20_waypoints.json`).

- **Excluded Datasets (5,274 files):**
  1. `data/workspaces/` (~5,100 files): Historical local rehearsal bundles, sortie black-box logs, and past experiment JSONs. (Appropriately excluded to prevent release bloat).
  2. `data/cache/imagery/` (~170 files): Intermediate static tile PNGs for Gale and Olympus regional preview cards. (Appropriately excluded; fallbacks exist in `web/assets/`).
  3. `data/raw/MARS_nomenclature_center_pts.kmz` (2.61 MB) & `.kml` (2.57 MB): Raw IAU gazetteer files. (Appropriately excluded; compiled catalog `web/data/mars_places.json` is bundled).
  4. **`data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif` (9.66 MB):** Raw USGS CTX digital elevation model. **INADVERTENTLY EXCLUDED (Defect MW-M9-DEF-01).**

---

## 6. Launch & Runtime Dependency Analysis

### A. Runtime Dependencies
To launch the MarsWalk Atlas HTTP server and 3D web workstation, the application requires:
- Python $\ge 3.10$
- Dependencies in `requirements.txt`: `numpy`, `scipy`, `rasterio`, `affine`, `jsonschema`, `requests`, `websockets`, `pytest`.
- Processed terrain raster: `data/processed/jezero_ready_20m.tif` (Present in archive).
- Mission specification: `data/missions/mission_when_mars_goes_dark.json` (Present in archive).
- Weather profile: `data/weather/baseline_jezero_meda.json` (Present in archive).
- Web assets: `web/index.html`, `web/app.js`, `web/libs/three.min.js` (Present in archive).

**Finding:** The runtime application can launch and serve the 3D dashboard and REST APIs purely from the archived files without depending on any external network resources or developer workspace paths.

### B. Preflight Quality Gate Dependencies
Gate 2 of `./scripts/release_preflight.sh` executes `.venv/bin/python scripts/audit_nasa_data.py`.
Line 60 of `audit_nasa_data.py` inspects `local_path` for each dataset defined in `nasa_data_provenance_manifest.json`.
For entry `USGS_CTX_DEM_RAW_20M`, `local_path` is `"data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"`.
Because this file was omitted from `scripts/package_release.py`, `audit_nasa_data.py` will exit with code 1 in a clean environment lacking this file.

---

## 7. Hardcoded Path & Environment Audit

A global code scan for developer username `/home/mech_ka_launda` was conducted across all Python source code, shell scripts, JavaScript, and configuration files:
- **Total matches in active code:** **0**
- All paths are dynamically anchored using `os.path.dirname(os.path.abspath(__file__))`, `Path(__file__).resolve()`, or `cd "$(dirname "${BASH_SOURCE[0]}")/.."`.

---

## 8. Defect Remediation Plan for Phase 2

1. **Remedy Defect MW-M9-DEF-01:**
   Add `"data/raw/JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif"` to `INCLUDE_FILES` in `scripts/package_release.py`.
   *Impact on archive:* Adds $\approx 3.0\,\text{MB}$ compressed to tarball, bringing total size from $8.83\,\text{MB}$ to $\approx 11.8\,\text{MB}$ (well below the 100 MB rule in `AGENTS.md`).
2. **Execute Clean-Room Extraction & Qualification:**
   In Phase 2, extract the release into `/tmp/marswalk-clean-room/`, build a fresh `.venv`, run `setup_atlas.sh`, execute all preflight gates, and verify complete independence from the developer workspace.
3. **Regenerate Release Candidate:**
   Re-package and produce verified `v2.0.0-rc2` (or certified `v2.0.0-rc1` update) after clean-room test passes.
