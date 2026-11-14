# Project MarsWalk 2.0 / Atlas — Official Release Manifest
**Release ID:** `MARSWALK-2.0.0-MISSION7-QUALIFIED`  
**Generated At (UTC):** `2026-11-14T16:22:36.032162+00:00`  
**Platform:** `Linux 6.8.0-149-generic (x86_64)`  
**Python Runtime:** `3.10.12`  
**Cryptographic Merkle Root:** `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8`  

---

## 1. Release Verification Scorecard

| Test Suite / Quality Gate | Verification Command | Status | Result |
| :--- | :--- | :--- | :--- |
| **NASA Data Manifest Audit** | `.venv/bin/python scripts/audit_nasa_data.py` | **PASS** | 8/8 datasets verified against disk |
| **Planetary Science Validation Gates** | `.venv/bin/python scripts/validate_nasa_data.py` | **PASS** | 25/25 scientific gates passed |
| **Five-Pillar Integration Suite** | `./scripts/run_tests.sh tests/test_nasa_data_integration.py` | **PASS** | 8/8 tests passed |
| **When Mars Goes Dark Flagship Suite** | `./scripts/run_tests.sh tests/test_when_mars_goes_dark_integration.py` | **PASS** | 9/9 tests passed |
| **Headless Browser Golden Path Audit** | `.venv/bin/python scripts/audit_golden_path_browser.py` | **PASS** | 7/7 interactive steps verified via CDP |
| **One-Command Showcase Runner** | `./scripts/run_showcase.sh 3000` | **PASS** | DETERMINISTIC & QUALIFIED |

---

## 2. Planetary Datasets Provenance & Integrity (8/8 Verified)

| Dataset Key | Dataset Product Name | Size (Bytes) | Disk SHA-256 Digest | Status |
| :--- | :--- | :--- | :--- | :--- |
| `USGS_CTX_DEM_RAW_20M` | USGS_CTX_DEM_RAW_20M | 9,662,387 | `16a1aa66c3f48c1b...` | ✅ VERIFIED |
| `USGS_CTX_DEM_PROCESSED_20M` | USGS_CTX_DEM_PROCESSED_20M | 252,206 | `875e7e80c170b84e...` | ✅ VERIFIED |
| `USGS_TRN_HIRISE_1M` | USGS_TRN_HIRISE_DTM_HAWKSBILL_1M | 1,441,904 | `0258c9e15d4bcca9...` | ✅ VERIFIED |
| `PDS_ROVER_PLACES` | PDS_ROVER_PLACES_BEST_TACTICAL | 171,404 | `9da19e4f70287fe0...` | ✅ VERIFIED |
| `NASA_MMGIS_WAYPOINTS_AND_TRAVERSE` | NASA_MMGIS_M20_WAYPOINTS | 603,126 | `bd143ee692412299...` | ✅ VERIFIED |
| `PDS_THREE_FORKS_SAMPLE_DEPOT` | PDS_THREE_FORKS_SAMPLE_DEPOT | 539 | `afdf6515ed007e21...` | ✅ VERIFIED |
| `NASA_PDS_MEDA` | PDS_M2020_MEDA_OBSERVATIONS | 2,674 | `ed8be71b7b1394b4...` | ✅ VERIFIED |
| `SCIENCE_OBSERVATION_TARGETS` | NASA_M2020_SCIENCE_TARGETS_CATALOG | 3,924 | `8a5756127ad2c2a7...` | ✅ VERIFIED |

---

## 3. Critical Code & Configuration Digests

| File Relative Path | Size (Bytes) | SHA-256 Digest |
| :--- | :--- | :--- |
| `src/marswalk/api/service.py` | 486,747 | `f4244bf6947cb7d21b8555d7...` |
| `src/marswalk/core/terrain.py` | 21,040 | `7f07f9968a035e3bdc62f2ca...` |
| `web/index.html` | 665,018 | `d2741a1e9647619b2653302c...` |
| `web/app.js` | 1,261,878 | `2e0ac57fcfe0841698c9fdc5...` |
| `scripts/run_atlas.py` | 108,657 | `c8dd6c7cdf6a08b1957d3448...` |
| `scripts/start_atlas.sh` | 3,146 | `2bcea5660f4ffa29b785e71c...` |
| `scripts/run_tests.sh` | 736 | `1444fe84e2785ececd285ba0...` |
| `scripts/run_showcase.sh` | 5,284 | `3087105303d5ac98b3baccfb...` |
| `scripts/audit_nasa_data.py` | 5,256 | `a26f2186a108ba338f598324...` |
| `scripts/validate_nasa_data.py` | 9,807 | `1c77cbecf1f14ed81d77b875...` |
| `scripts/audit_golden_path_browser.py` | 8,891 | `ea09293a82eefacdf94eab2c...` |
| `scripts/audit_browser_linux.py` | 9,504 | `f53a40c7becc065879a42111...` |

---

## 4. Key Runtime Dependencies

- **NumPy:** `2.2.6`
- **SciPy:** `1.15.3`
- **Rasterio:** `1.4.4`
- **Pytest:** `9.2.0`
- **Websockets:** `16.1.1`
- **JSONSchema:** `4.26.0`

*Manifest generated automatically by `scripts/build_release_manifest.py`.*
