# MarsWalk 2.0 — Milestone 10D Design Specification
## Mars Environmental Intelligence & Atmospheric In-Situ Ingestion

> **Status:** Implemented & Verified  
> **Milestone:** 10D  
> **Primary Source:** NASA Planetary Data System (PDS) Mars 2020 Perseverance MEDA Archive  
> **Secondary Sources:** MSL Curiosity REMS, Mars Climate Database (MCD v6.1), InSight APSS  
> **Schema:** `schemas/api/v1/weather-report.schema.json`  
> **Core Engine:** `src/marswalk/core/weather.py`

---

## 1. Executive Summary & Objective

Milestone 10D introduces authentic **Mars Environmental Intelligence** to Project Atlas. Previous milestones (9D–10C) established high-resolution terrain routing, compound hazard analysis, camera director modes, emergency mid-sortie replanning, and black-box event reconstruction across Jezero Crater. However, atmospheric conditions—surface pressure, air and ground temperatures, atmospheric dust opacity, and surface winds—were previously static or unrepresented.

Milestone 10D implements an end-to-end meteorological intelligence vertical slice that:
1. **Acquires authentic in-situ ground observations** from official NASA PDS archives (Perseverance MEDA at Jezero Crater).
2. **Enforces planetary operational realism:** distinguishes empirical surface station observations from global numerical circulation models (Mars Climate Database) and historical archives (InSight).
3. **Guarantees multi-site isolation:** strictly prevents cross-site spatial projection (e.g. Gale Crater readings are never projected onto Jezero sorties).
4. **Protects physical integrity:** filters missing/sentinel values (`999999999` $\to$ `null`, never zero) and enforces physical range bounds.
5. **Maintains offline resiliency:** provides atomic file-backed caching with graceful fallback (`CACHED_FALLBACK`) and deduplication.
6. **Preserves non-intrusive mission planning:** provides advisory environmental context without silently altering core A* heuristics or claiming astronaut EVA operational safety.

---

## 2. Architecture & Component Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Atlas Frontend (Vanilla JS)                       │
│  web/index.html (#weatherModal)  web/styles.css  web/app.js             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTP REST
┌────────────────────────────────────▼────────────────────────────────────┐
│                       Atlas HTTP Server (Port 3000)                     │
│  GET /api/weather/current  GET /api/weather/sites  POST /weather/refresh│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                    API Layer (src/marswalk/api/service.py)               │
│  Input validation, contract validation (weather-report.schema.json)     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│              Weather Core Engine (src/marswalk/core/weather.py)          │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌────────────────┐  │
│  │   PdsMedaProvider    │  │   PdsRemsProvider   │  │ McdClimatology │  │
│  │ (Jezero Perseverance)│  │ (Gale MSL Curiosity)│  │ (Olympus Mons) │  │
│  └──────────┬───────────┘  └──────────┬──────────┘  └────────┬───────┘  │
│             │                         │                      │          │
│  ┌──────────▼─────────────────────────▼──────────────────────▼───────┐  │
│  │                Physical Range Guard & Unit Converters              │  │
│  │             (Pa bounds, Kelvin/Celsius, null filter)              │  │
│  └────────────────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────────────┼─────────────────────────────────┘
                                        │ Atomic File I/O
┌───────────────────────────────────────▼─────────────────────────────────┐
│                        Data Layer (data/weather/)                       │
│  baseline_jezero_meda.json   baseline_gale_rems.json                    │
│  baseline_olympus_mcd.json   baseline_insight.json                      │
│  cache_jezero_crater.json    (atomic .tmp replacement)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources & Archival Boundaries

| Site | Platform / Instrument | Source Archive | Coordinates | Data Classification | Primary Metrics |
|---|---|---|---|---|---|
| **Jezero Crater** | Mars 2020 Perseverance / MEDA | NASA PDS Atmospheres Node | 18.44°N, 77.45°E | `IN_SITU_OBSERVATION` | $P = 589.7\text{ Pa}$, $T_{air} = -61.7^\circ\text{C}$, $T_{gnd} = -60.0^\circ\text{C}$, $\text{RH} = 5.6\%$, $\tau = 0.35$ |
| **Gale Crater** | MSL Curiosity / REMS | NASA PDS Atmospheres Node | 4.59°S, 137.44°E | `IN_SITU_OBSERVATION` | $P = 842.1\text{ Pa}$, $T_{air} = -65.0^\circ\text{C}$, $T_{gnd} = -50.0^\circ\text{C}$, $v_{wind} = 4.2\text{ m/s}$ |
| **Olympus Mons** | Mars Climate Database (MCD v6.1) | LMD / CNES / ESA | 18.65°N, 226.20°E | `CLIMATOLOGICAL_MODEL` | $P = 72.4\text{ Pa}$ (summit vacuum), $T_{air} = -108.0^\circ\text{C}$, $v_{wind} = 12.8\text{ m/s}$ |
| **Elysium Planitia**| InSight Lander / APSS TWINS | NASA InSight Archive | 4.50°N, 135.62°E | `HISTORICAL_MISSION_ARCHIVE`| Sol 1440 terminal archive ($P = 718.5\text{ Pa}$, $T_{air} = -55.0^\circ\text{C}$) |

### Site Isolation Rule
Because Gale Crater and Jezero Crater are separated by 3,700 km across opposing hemispheres, MarsWalk strictly refuses to blend or project Gale observations onto Jezero route evaluations. Each station's report displays explicit disclosures regarding planetary spatial constraints.

---

## 4. Freshness Lifecycle State Machine

1. **`LATEST_AVAILABLE`:** Observation successfully retrieved from the latest official PDS archival release tranche (downlink and science validation lag accounted for).
2. **`CURRENT`:** Climatological or simulated model synchronized to current simulation coordinate and solar longitude ($L_s$).
3. **`DELAYED`:** Telemetry pipeline indicates expected orbital relay transmission delay.
4. **`STALE`:** Last check exceeded maximum cache TTL without successful upstream verification.
5. **`HISTORICAL`:** Station mission concluded (e.g. InSight Sol 1440, December 2022).
6. **`CACHED_FALLBACK`:** Upstream network unavailable; serving verified local cache with clear warning indicator.
7. **`UNAVAILABLE`:** No sensor coverage or corrupted record.

---

## 5. UI Integration

- **Header Trigger (`#btnHeaderWeather`):** Provides instant one-click access with live atmospheric styling.
- **Atmospheric Telemetry Dashboard (`#weatherModal`):**
  - Station banner with Martian Sol, UTC timestamp, local mean solar time (LMST), $L_s$ season, and cache age.
  - Six primary measurement tiles: Atmospheric Pressure (Pa & hPa), Air Temperature (°C & K), Ground Temperature (°C & K), Relative Humidity (%), Wind Vector (speed in m/s & direction in °), and Dust Optical Depth ($\tau$).
  - Missing-value handling: Displays `RESTRICTED` or `null` for damaged sensors rather than synthetic zero.
  - Interactive site selector supporting all 4 verified stations.
  - Bounded auto-refresh toggle (15-minute interval).
  - Provenance card with clickable NASA PDS archive links.
