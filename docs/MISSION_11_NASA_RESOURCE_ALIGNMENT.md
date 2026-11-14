# MISSION 11 — OFFICIAL NASA RESOURCE ALIGNMENT & DATA MAPPING

**Project:** MarsWalk 2.0 / Project Atlas  
**Alignment Standard:** NASA Open Science Data Initiative & 2026 Space Apps Challenge Resources  
**Companion Documents:**
- [`MISSION_11_COMPLETE_DATA_PROVENANCE.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_COMPLETE_DATA_PROVENANCE.md)
- [`MISSION_11_CHALLENGE_REQUIREMENT_MATRIX.md`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/docs/MISSION_11_CHALLENGE_REQUIREMENT_MATRIX.md)

---

## 1. Executive Summary: Official NASA Resources Cross-Reference

The 2026 NASA Space Apps "Marswalk" challenge provides a curated list of official NASA and USGS planetary exploration tools and datasets.

The table below demonstrates how MarsWalk 2.0 directly incorporates, cross-references, or adapts each official resource into its local offline platform:

| Official NASA / Partner Resource | Primary Host / Node | Role in Challenge | MarsWalk 2.0 Implementation & Integration |
| :--- | :--- | :--- | :--- |
| **NASA Mars Trek (WMTS)** | NASA Solar System Treks / JPL | Planetary basemap viewer & layered GIS layers | Ingested into [`mars_imagery_registry.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/web/data/mars_imagery_registry.json) with local tile caching in `data/cache/imagery/` and offline Viking MDIM 2.1 color fallback texture. |
| **USGS Astrogeology Jezero Geologic Mapping** | USGS Astrogeology Science Center / ScienceBase | High-resolution elevation DTMs for Jezero Crater | Ingested raw CTX 20m DTM (`JEZ_ctx_B_soc_008...tif`, $9.66\,\text{MB}$) and HiRISE 1m DTM (`hawksbill_1m.tif`, $1.44\,\text{MB}$) driving all slope and hazard computations. |
| **NASA Mars 2020 MMGIS ("Where is Perseverance?")** | NASA JPL / MMGIS Maps Platform | Official public web visualizer of rover position and traversed path | Ingested authentic MMGIS GeoJSON layers: [`nasa_m20_waypoints.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/nasa_m20_waypoints.json) ($603\,\text{KB}$) and [`nasa_m20_traverse.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/nasa_m20_traverse.json) ($256\,\text{KB}$). |
| **NASA PDS Geosciences Node (Rover PLACES)** | Washington University in St. Louis / NASA PDS | Archived ground-truth tactical rover localization stations | Ingested raw PDS4 bundle [`pds_places_best_tactical.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/pds_places_best_tactical.csv) (577 records, Sols 13–1896) used to compare planned traverses against actual rover paths. |
| **NASA PDS Atmospheres Node (Mars 2020 MEDA)** | New Mexico State University / NASA PDS | In-situ calibrated weather sensor time series from Jezero Crater floor | Ingested calibrated pressure (PS), air temp (ATS), ground temp (TRS), humidity (RHS), and wind vectors into [`meda_environmental_observations.json`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/catalogs/meda_environmental_observations.json). |
| **NASA JPL Mars 2020 Sample Depot Logs** | NASA JPL / Mars Sample Return | Telemetry records for titanium sample tubes dropped at Three Forks | Ingested [`pds_three_forks_sample_drops.csv`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/pds_three_forks_sample_drops.csv) for all 10 deposited tubes with geological provenance and drop coordinates. |
| **IAU Gazetteer of Planetary Nomenclature** | USGS / IAU WGPSN | Standardized nomenclature database of named features on Mars | Ingested [`MARS_nomenclature_center_pts.kml`](file:///home/mech_ka_launda/projects/NASA-SpaceApps-2026/MarsWalk-Submission/data/raw/MARS_nomenclature_center_pts.kml) ($5.42\,\text{MB}$) compiling 2,061 named Martian craters, planitia, valles, and historic landing sites into `mars_places.json`. |

---

## 2. Ingestion & Preprocessing Pipeline

To ensure reliability during competition evaluation, MarsWalk does not rely on fragile live scraping of external websites during runtime. Instead, an ingestion pipeline scripts each source into local, optimized formats:

```
┌───────────────────────────────────────┐
│     PRIMARY UPSTREAM REPOSITORIES     │
│  NASA PDS • USGS ScienceBase • MMGIS  │
└───────────────────────────────────────┘
                    │
                    ▼ (Ingestion & Sanitization Scripts)
┌───────────────────────────────────────┐
│        LOCAL ARCHIVE STORAGE          │
│   GeoTIFF Rasters • Normalized JSON   │
└───────────────────────────────────────┘
                    │
                    ▼ (Local Memory Preload on Startup)
┌───────────────────────────────────────┐
│       MARSWALK RUNTIME ENGINE         │
│  A* Pathfinder • Pareto • Three.js 3D │
└───────────────────────────────────────┘
```

1. **Raster Standardization (`prepare_jezero_clip.py`):**
   - Reads USGS CTX 20m GeoTIFF.
   - Extracts bounding coordinates matching the Mars 2020 landing and delta ascent corridor ($5.0 \times 5.0\,\text{km}$).
   - Verifies coordinate reference system `ESRI:103885` and writes `data/processed/jezero_ready_20m.tif`.
2. **Tabular Telemetry Parsing (`build_mars_place_catalog.py`):**
   - Parses IAU nomenclature KML and PDS rover localization CSVs.
   - Transforms planetocentric longitude/latitude into local projected meters $(x, y)$ and grid indices $(\text{row}, \text{col})$.
   - Indexes records by Sol number and feature category.
3. **Atmospheric Baseline Normalization:**
   - Evaluates raw MEDA ATS and PS logs.
   - Computes daily mean, minimum, maximum, and semi-diurnal thermal tide oscillations.
   - Packages summary metrics into `meda_environmental_observations.json`.

---

## 3. Comparison with NASA MMGIS and Mars Trek

| Functional Capability | NASA Mars Trek | NASA MMGIS (Where is Perseverance) | MarsWalk 2.0 / Project Atlas |
| :--- | :--- | :--- | :--- |
| **Primary Focus** | Public global mosaic browsing | Tactical daily rover tracking | **Autonomous route planning, trade-off optimization & contingency resilience** |
| **Offline Operation** | No (requires web access) | No (requires web access) | **100% Offline Self-Contained** |
| **A\* Pathfinding** | No (manual measuring tool) | No (historical paths only) | **Full 2D/3D A\* with Horn slope & Bekker slip** |
| **Multi-Objective Trade-Offs** | None | None | **3-Objective Pareto Frontiers (Distance vs Risk vs Science)** |
| **Contingency Stress Testing** | None | None | **"When Mars Goes Dark" 60-Sol resilience simulation** |
| **Human EVA Support** | None | None | **Apollo-analogue `crew_eva` mode with metabolic disclosures** |
