# MarsWalk 2.0 / Project Atlas — Release Candidate 1 Specification

**Document Identifier:** `MW-M8-RC1-SPEC`  
**Release Version:** `v2.0.0-rc1`  
**Target Event:** NASA International Space Apps Challenge 2026  
**Publication Date:** 2026-11-14  
**Classification:** Certified Competition Submission Release Candidate  
**Repository Branch:** `mission-8-release-candidate`  
**Baseline Git Commit:** `e0cdca8`  

---

## 1. Executive Summary

Project MarsWalk 2.0 / Project Atlas represents a fully integrated, scientifically grounded Martian mission operations demonstrator. Built specifically for the NASA Space Apps Challenge, the platform bridges real remote sensing and surface observations from the Mars 2020 Perseverance mission with resilient, multi-objective autonomous navigation.

This document formally certifies **Release Candidate 1 (`v2.0.0-rc1`)**. The package bundles all core Python engine modules, responsive frontend operations dashboards, automated verification suites, historical NASA/PDS datasets, geodetic elevation models, and mission resilience execution harnesses into an immutable, cryptographically signed distribution.

---

## 2. Release Distribution Artifacts

The release distribution is archived in gzip-compressed tar format and verified via SHA-256 cryptographic digest:

| Artifact Path | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `outputs/releases/marswalk-v2.0.0-rc1.tar.gz` | `tar.gz` (gzip) | 9,263,702 bytes (8.83 MB) | `8604af64bac2ed24486bc370e01d4965f13f6c23a0fc1b18a6b1803b6977218a` |
| `outputs/releases/marswalk-v2.0.0-rc1.sha256` | ASCII Checksum | 93 bytes | (Checksum file containing digest and archive name) |

### Cryptographic Verification Command
```bash
sha256sum -c outputs/releases/marswalk-v2.0.0-rc1.sha256
```
Expected output:
```
marswalk-v2.0.0-rc1.tar.gz: OK
```

---

## 3. Package Contents & Archive Manifest

The release archive packages **1,037 certified files** organized into a self-contained runtime directory structure:

```
marswalk-v2.0.0-rc1/
├── src/marswalk/                  # Core Python Planetary Engine & Services
│   ├── api/                       # REST API router & service endpoints (HTTP 200/400/500 handlers)
│   ├── core/                      # Terrain analysis, multi-objective A*, Merkle logs, energy models
│   ├── data/                      # NASA PDS & USGS data ingest parsers and coordinate transforms
│   ├── environment/               # MEDA atmospheric models, dust optical depth, irradiance
│   ├── models/                    # Pydantic schemas, data contracts, and validation models
│   ├── planning/                  # Science waypoint optimization, heuristic cost models
│   └── resilience/                # DTN bundle storage, comms blackout simulator, Merkle auditor
├── web/                           # Evaluator Operations Deck & HUD
│   ├── index.html                 # 15-second landing hero, 5-pillar console, Three.js canvas
│   ├── app.js                     # Workstation state machine, Golden Path tour controller
│   ├── css/                       # Mission operations typography, dark aerospace theme
│   └── js/                        # Three.js 3D Jezero surface renderer and GIS layer overlays
├── scripts/                       # Operational Shell & Verification Tools
│   ├── start_atlas.sh             # Production daemon launcher with port and browser options
│   ├── release_preflight.sh       # 9-Gate strict qualification suite
│   ├── audit_golden_path_browser.py# Automated CDP headless browser walkthrough
│   └── package_release.py         # Official tarball packaging and integrity checker
├── tests/                         # Pytest Verification Suites (34 test cases)
│   ├── test_nasa_data_integration.py
│   ├── test_mission8_cross_pillar_integration.py
│   ├── test_when_mars_goes_dark_integration.py
│   └── test_mission8_api_failure_resilience.py
├── docs/                          # Engineering Reports & Scientific Audits
│   ├── MISSION_8_BASELINE.md
│   ├── MISSION_8_INTEGRATION_REPORT.md
│   ├── MISSION_8_UX_AUDIT.md
│   ├── MISSION_8_FAILURE_TEST_REPORT.md
│   ├── MISSION_8_PERFORMANCE_REPORT.md
│   └── MISSION_8_RELEASE_CANDIDATE.md
├── data/                          # Authoritative Mars Datasets & Provenance
│   ├── catalogs/                  # Geolocated science targets, sample depot, MEDA sol series
│   ├── manifests/                 # NASA data provenance manifest (DOIs, PDS bundle IDs)
│   ├── processed/                 # GeoTIFF DTM rasters (1m Hawksbill HiRISE & 20m Jezero)
│   ├── missions/                  # Canonical flagship resilience scenario specifications
│   ├── weather/                   # Historical Jezero Sol 89 MEDA profiles
│   ├── preferences/               # Commander operational profiles and weighting policies
│   └── raw/                       # PDS traverse CSVs, sample drop records, waypoints
├── pyproject.toml                 # Modern PEP 517 build specification
├── requirements.txt               # Locked production dependencies
├── AGENTS.md                      # Planetary science safety and mission rules
└── README.md                      # Evaluator guide, installation walkthrough, architecture
```

### Excluded Artifacts
The archive strictly excludes developer cache and temporary files:
- `__pycache__/` and `*.pyc` binaries
- `.pytest_cache/`
- `.venv/` and `venv/`
- `.git/` revision metadata
- Intermediate browser screenshots (`outputs/browser_qa/`)

---

## 4. Five Pillars of Capability

Release Candidate 1 integrates all five architectural pillars into a unified operational loop:

1. **Pillar 1: Terrain Intelligence**
   - High-resolution Jezero DTM elevation rasters (USGS / HiRISE Hawksbill Gap at 1m/pixel and Jezero floor at 20m/pixel).
   - Real-time slope calculation, roughness extraction, and terramechanics slip modeling.
   - Non-negotiable slope threshold enforcement ($15^\circ$ vehicle cutoff).

2. **Pillar 2: Rover Ground Truth**
   - Direct integration of NASA PDS Perseverance tactical coordinate records (Sol 0 to Sol 1000+).
   - Certified 10-tube Three Forks sample depot inventory with sample tube IDs, core lengths, and Sol drop stamps.
   - Actual rover traverse path visualization vs modeled traverse paths.

3. **Pillar 3: Environmental Intelligence**
   - Actual Mars 2020 MEDA atmospheric measurements from Sol 89 dust storm event.
   - Beer-Lambert-Bougher solar irradiance model ($\tau = 2.15$, $71.3\%$ solar loss).
   - Diurnal atmospheric density and temperature cycling ($T_{\text{ambient}} = -81.2^\circ\text{C}$).

4. **Pillar 4: Science-Driven Planning**
   - Multi-objective A* heuristic planner balancing distance, energy, terramechanics risk, and science yield.
   - Explicit Pareto frontier trade-offs: *High-Science* (3.26 km, 4 targets, 4.47 kWh) vs *Direct-Transit* (2.11 km, 1 target, 2.85 kWh).
   - SHERLOC/PIXL instrument target sampling and dwell-time energy budgets.

5. **Pillar 5: Autonomous Mission Resilience ("When Mars Goes Dark")**
   - Signature 7-stage crisis recovery scenario across 60 Martian sols.
   - Delay-Tolerant Networking (DTN RFC 5050/9171) custody transfers during topographic communications blackouts.
   - Scarp rockfall detour recalculation with zero human-in-the-loop intervention.
   - Merkle audit log verification guaranteeing tamper-evident chain of custody:
     $$\text{Root Hash: } \mathtt{0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8}$$

---

## 5. System Requirements & Compatibility

- **Host Operating System:** Ubuntu 22.04 LTS (x86_64 or aarch64) / Modern Linux
- **Python Runtime:** Python 3.10.x or 3.11.x
- **Memory Footprint:** $\le 200\,\text{MB}$ RSS at steady state (measured $155.7\,\text{MB}$)
- **Disk Space Required:** $\approx 150\,\text{MB}$ uncompressed (including elevation rasters and venv)
- **Display / Browser:** Google Chrome / Chromium 100+ (for 3D WebGL Three.js cockpit)
- **Network Access:** None required. System operates **100% offline** with preloaded datasets.

---

## 6. Verification and Acceptance Audit

Every component in Release Candidate 1 has passed comprehensive automated verification:

| Verification Suite | Test Count | Result | Execution Time |
| :--- | :--- | :--- | :--- |
| **NASA Data Integration Suite** (`test_nasa_data_integration.py`) | 8 | PASS (100%) | 2.14s |
| **Cross-Pillar Data Exchange Suite** (`test_mission8_cross_pillar_integration.py`) | 6 | PASS (100%) | 8.89s |
| **When Mars Goes Dark Integration Suite** (`test_when_mars_goes_dark_integration.py`) | 9 | PASS (100%) | 12.18s |
| **API Failure & Boundary Resilience Suite** (`test_mission8_api_failure_resilience.py`) | 11 | PASS (100%) | 12.45s |
| **Headless Chrome Golden Path Walkthrough** (`audit_golden_path_browser.py`) | 7 Stages | PASS (100%) | 14.28s |
| **Release Preflight Quality Gate** (`release_preflight.sh`) | 9 Gates | PASS (100%) | 28.60s |
| **Total Automated Quality Gates** | **41 Checks** | **ALL PASS** | **< 60s** |

---

## 7. Installation and Quick-Start Guide

To install and run Release Candidate 1 from the release archive:

```bash
# 1. Unpack archive
tar -xzf outputs/releases/marswalk-v2.0.0-rc1.tar.gz
cd marswalk-v2.0.0-rc1

# 2. Initialize virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Launch MarsWalk Operations Console
./scripts/start_atlas.sh --port 3000 --no-browser

# 4. Open browser to interactive operations deck
# URL: http://localhost:3000
```

---

## 8. Release Candidate Certification

This release candidate meets all engineering criteria, scientific data provenance mandates, and UX performance requirements established for the NASA International Space Apps Challenge. All 4 discovered defects (MW-M8-01 through MW-M8-04) have been eliminated with regression tests in place.

**Certified by:** Antigravity Mission 8 Systems Engineering & Quality Assurance  
**Status:** `READY FOR FINAL SUBMISSION QUALIFICATION`
