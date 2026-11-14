# MarsWalk 2.0 / Project Atlas — Milestone 13L: API Reference & Schema Contracts

## 1. Overview
All Milestone 13L capabilities are exposed via RESTful HTTP endpoints served on port 3000 (`scripts/run_atlas.py` and `src/marswalk/api/service.py`). All responses strictly validate against JSON Schema Draft 2020-12 specifications.

## 2. API Endpoints Summary

| Method | Path | Description | Schema Key |
|---|---|---|---|
| `GET` | `/api/environment/catalog` | Returns product metadata, provenance classes, SHA-256 hashes, and DOIs | `environmental-catalog` |
| `GET` | `/api/environment/solar` | Computes solar ephemeris for given sol and LTST decimal hours | `environmental-solar` |
| `GET` | `/api/environment/scenarios` | Lists calibrated deterministic stress scenarios (ENV-A to ENV-E) | `environmental-scenario` |
| `GET` | `/api/environment/raster` | Downsampled 2D spatial raster grid for UI heatmaps (illumination, temp, shadow) | Dynamic 2D Matrix |
| `POST` | `/api/environment/point` | Point environmental evaluation: flux, shadows, thermal, dust, wind, hazards | `environmental-point-eval` |
| `POST` | `/api/environment/windows` | Synthesizes optimal, hazard-free observation window for target | `environmental-window` |

## 3. Sample Payloads & Schemas

### 3.1 Point Evaluation Request & Response
```json
// POST /api/environment/point
{
  "sol": 1,
  "ltst_hours": 12.0,
  "row": 125.0,
  "col": 125.0,
  "instrument_name": "MASTCAM_Z",
  "scenario_code": "BASELINE_NOMINAL"
}
```

```json
// Response (200 OK)
{
  "sol": 1,
  "ltst_hours": 12.0,
  "row": 125.0,
  "col": 125.0,
  "elevation_m": -2512.4,
  "slope_deg": 4.2,
  "solar_elevation_deg": 71.56,
  "solar_azimuth_deg": 180.0,
  "is_illuminated": true,
  "is_terrain_shadowed": false,
  "direct_flux_w_m2": 340.2,
  "air_temperature_c": -32.4,
  "ground_temperature_c": -18.2,
  "optical_depth_tau": 0.45,
  "pressure_pa": 763.8,
  "wind_speed_m_s": 4.8,
  "wind_gust_m_s": 7.4,
  "is_hazard_free": true,
  "hazards": []
}
```

### 3.2 Observation Window Request & Response
```json
// POST /api/environment/windows
{
  "target_id": "tgt_delta_crest",
  "row": 125.0,
  "col": 125.0,
  "instrument_name": "SUPERCAM",
  "sol": 1,
  "duration_hours": 1.0
}
```

```json
// Response (200 OK)
{
  "target_id": "tgt_delta_crest",
  "instrument_name": "SUPERCAM",
  "sol": 1,
  "start_ltst": 10.75,
  "end_ltst": 12.75,
  "duration_hours": 1.0,
  "is_valid": true,
  "quality_score": 0.942,
  "mean_solar_elevation_deg": 62.4,
  "mean_direct_flux_w_m2": 410.5,
  "min_air_temperature_c": -38.2,
  "max_air_temperature_c": -24.1,
  "mean_optical_depth_tau": 0.45,
  "shadow_fraction": 0.0,
  "peak_wind_gust_m_s": 11.2,
  "violation_reasons": []
}
```
