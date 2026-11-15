# NASA & PLANETARY DATA SOURCES CATALOG
## Provenance, Coordinate Systems, Processing & Attribution

**NASA International Space Apps Challenge 2026**  
**Project:** MarsWalk 2.0 / Project Atlas  
**Release:** `v2.2.0-eva-qualified`  

---

### 1. Data Provenance Summary Matrix

All surface models, atmospheric profiles, orbital contexts, and rover ground truth waypoints used in MarsWalk are derived from official NASA, USGS, and international planetary science archives. MarsWalk strictly forbids synthetic terrain generation or fabricated telemetry.

```
Total Project Data Footprint: ~1,532 MB (1.5 GB)
Distribution:
  - USGS Planetary Photogrammetry: 60.3%
  - NASA Planetary Data System (PDS): 18.0%
  - European Space Agency / LMD / MCD: 1.2%
  - Scientific Processing Pipelines & Models: 20.5%
```

| Dataset Name | Primary Instrument & Mission | Sponsoring Agency | Data Source / Archive Node | Native Resolution | Coordinate System / Datum | Local File Location |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Jezero Delta 1m HiRISE DEM** | HiRISE, Mars Reconnaissance Orbiter (MRO) | NASA / JPL / Univ. of Arizona / USGS | USGS Astrogeology Science Center / PDS Cartography Node | $1.0\text{ m/pixel}$ horizontal, sub-meter vertical | Equirectangular / Mars Sphere ($R=3396190\text{ m}$) | `data/raw/jezero_dem_1m.tif` & `data/processed/terrain/` |
| **Jezero Regional 20m CTX DEM** | Context Camera (CTX), MRO | NASA / JPL / Malin Space Science Systems | NASA PDS Geosciences Node / USGS | $20.0\text{ m/pixel}$ horizontal | Equirectangular Mars Sphere | `data/raw/ctx_jezero_20m.tif` |
| **Mars 2020 MEDA Weather Records** | Mars Environmental Dynamics Analyzer (MEDA), Perseverance | NASA / JPL-Caltech / CAB (CSIC-INTA) | NASA PDS Atmospheres Node (`urn:nasa:pds:mars2020_meda`) | 1 Hz sensor records downsampled to hourly averages | Jezero Crater Landing Site ($18.38^\circ\text{ N}, 77.58^\circ\text{ E}$) | `data/processed/weather/meda_processed.json` |
| **Perseverance Surface Waypoints** | Mars 2020 Rover Guidance & Telemetry | NASA / JPL-Caltech | NASA Mars 2020 Mission Telemetry Archive | Actual traversed coordinates Sol 0 - Sol 1000+ | Jezero Local Rover Frame & Planetocentric Lon/Lat | `data/processed/waypoints_jezero.json` |
| **Mastcam-Z Surface Imagery** | Mastcam-Z Stereo Imager, Perseverance | NASA / JPL-Caltech / ASU / Malin | NASA PDS Imaging Node / Mars 2020 Raw Image Archive | Full-resolution radiometrically calibrated PNGs | Local camera line-of-sight pointing vectors | `data/raw/mastcamz/` |
| **Mars Climate Database v6.1 (MCD)** | Mars Global Circulation Model (MGCM) | ESA / CNES / LMD (Sorbonne Univ.) | Laboratoire de Météorologie Dynamique | $5.625^\circ \times 3.75^\circ$ global, downscaled locally | Mars Planetocentric / Solar Longitude ($L_s$) | `data/processed/weather/mcd_climatology.json` |

---

### 2. Dataset Ingestion & Processing Pipelines

#### 2.1 USGS HiRISE Stereogrammetric Elevation Model
- **Source:** High Resolution Imaging Science Experiment (HiRISE) stereo pairs acquired over Jezero Crater (Western Fan Delta and Séítah formation).
- **Processing:** Photogrammetrically processed via the USGS Integrated Software for Imagers and Spectrometers (ISIS3) and the NASA Ames Stereo Pipeline (ASP).
- **Pipeline Implementation:** Ingested via `src/marswalk/data/ingest_dem.py` utilizing GDAL/Rasterio.
- **Transformations:**
  - Reprojected to an isotropic metric grid with pixel scale $dx = dy = 1.0\text{ m}$.
  - Elevation values stored in 32-bit floating-point GeoTIFF format representing orthometric height in meters relative to the Mars MOLA areoid.
  - IEEE-754 NaN values and invalid no-data pixels explicitly masked to prevent algorithmic corruption.

#### 2.2 NASA PDS MEDA Environmental Telemetry
- **Source:** Sensors onboard the Mars 2020 *Perseverance* rover measuring surface atmospheric parameters.
- **Key Parameters Extracted:**
  - **Dust Optical Depth ($\tau$):** Retrieved from the Radiation and Dust Sensor (RDS) measuring atmospheric attenuation at 880 nm.
  - **Ambient Temperature ($T_{\text{air}}$) & Surface Temperature ($T_{\text{ground}}$):** Infrared and thermocouple sensors.
  - **Atmospheric Pressure ($P_{\text{surf}}$):** High-precision Barometer recording seasonal cycles ($680 - 860\text{ Pa}$).
- **Integration:** Processed via `src/marswalk/data/ingest_meda.py` and stored in indexed JSON structures. Fuels the environmental intelligence engine and triggers dynamic contingency state changes (e.g., dust storm $\tau \ge 3.0$ aborts).

#### 2.3 Perseverance Ground Truth Traverse
- **Source:** NASA JPL-Caltech official traverse trajectory data.
- **Attributes:** Timestamped coordinates (Sol number, site index, drive distance, heading, and pitch/roll tilt angles).
- **Function:** Serves as the real-world baseline benchmark for rover route planning validation and scientific sample site selection.

---

### 3. Scientific Units & Standards Compliance

All calculations and interfaces strictly adhere to standard International System of Units (SI) and planetary coordinate conventions:
- **Horizontal Distance:** Meters ($\text{m}$) and Kilometers ($\text{km}$).
- **Elevation:** Meters ($\text{m}$) above the Mars datum (MOLA areoid).
- **Slope Angle:** Degrees ($^\circ$) and Radians ($\text{rad}$).
- **Atmospheric Pressure:** Pascals ($\text{Pa}$).
- **Temperature:** Kelvin ($\text{K}$) and Celsius ($^\circ\text{C}$).
- **Metabolic Work:** Watts ($\text{W} = \text{J/s}$) and Kilocalories ($\text{kcal}$).
- **Life Support Volumes:** Liters at Standard Temperature & Pressure ($\text{L}_{\text{STP}}$).
- **Coordinates:** Planetocentric Longitude ($0^\circ - 360^\circ\text{ E}$) and Latitude ($-90^\circ - +90^\circ\text{ N}$).
