# PROJECT ATLAS — MILESTONE 13P
# AERIAL SCIENCE PAYLOADS & SENSOR OBSERVATION PIPELINE
## High-Resolution Optical Stereo, Near-Infrared Spectrometry, Synthetic Subsurface Radar, and Atmospheric In-Situ Probes

**Milestone:** 13P — Atlas Aerial Corps: Multi-Rotorcraft Intelligence, Aerial Science, Flight Dynamics & Rover–Aircraft Cooperation  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Core Implementation:** `src/marswalk/core/mars_aerial_science.py`

---

## 1. Overview of Planetary Aerial Science Payloads

Autonomous planetary rotorcraft provide a unique vantage point: they bridge the massive scale gap between orbital remote sensing (MRO CTX at $6\text{ m/px}$, HiRISE at $25\text{ cm/px}$) and surface rover in-situ contact instruments (Perseverance PIXL / SHERLOC at millimeter to sub-millimeter scales). Flying at altitudes between $10\text{ and }35\text{ meters}$, an aerial scout achieves optical resolutions under $1\text{ cm/px}$, resolving small boulders, sand ripple crests, and stratified sedimentary layers while covering kilometers of terrain.

```
+----------------------------------------------------------------------------------------------------+
|                                    AERIAL SCIENCE SENSOR SUITE                                     |
+----------------------------------------------------------------------------------------------------+
|  SENSOR MODALITY       | TARGET MEASUREMENT              | GROUND RESOLUTION / GSD | PROVENANCE    |
+------------------------+---------------------------------+-------------------------+---------------+
|  Visible Optical Cam   | High-Res Surface Orthomosaic    | 0.5 to 1.2 cm / pixel   | JPL RTE Optics|
|  NIR Multispectral     | Mineral Band Depths (2.3 um)    | 2.5 to 5.0 cm / pixel   | CRISM Analogs |
|  Synthetic GPR Radar   | Stratigraphic Dielectric Echos  | 50 cm sounding spacing  | SYNTHETIC MOD |
|  Atmospheric Probe     | Boundary Layer T, p, Wind       | Continuous 1 Hz stream  | MEDA Analogs  |
|  Radiation Dosimeter   | GCR / SPE Cosmic Ray Dose Rate  | Integrated 0.1 Hz       | RAD Analogs   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Optical Geometry & Ground Sampling Distance (GSD)

The visible optical sensor geometry is governed by camera pinhole optics:

$$\text{GSD} = \frac{z_{\text{AGL}} \cdot w_{\text{sensor}}}{f \cdot N_{\text{pixels}}}$$

For nominal Jezero scouting parameters:
- Altitude Above Ground: $z_{\text{AGL}} = 15.0\text{ m}$
- Lens Focal Length: $f = 8.5\text{ mm}$ ($0.0085\text{ m}$)
- Sensor Format Width: $w_{\text{sensor}} = 6.4\text{ mm}$ ($0.0064\text{ m}$)
- Horizontal Pixel Count: $N_{\text{pixels}} = 4,056\text{ px}$

$$\text{GSD} = \frac{15.0 \times 0.0064}{0.0085 \times 4,056} = \frac{0.096}{34.476} = 0.00278\text{ m/px} \approx 0.78\text{ cm/pixel}$$

At $0.78\text{ cm/px}$, an aerial scout easily identifies a $0.45\text{ m}$ rockfall boulder that would be a single blurred sub-pixel blur in orbital CTX ($600\text{ cm/px}$) or a 2-pixel feature in HiRISE ($25\text{ cm/px}$).

---

## 3. Near-Infrared (NIR) Multispectral Imager

The Science Scout carries a compact multispectral imager measuring narrow-band spectral reflectance across short-wave infrared wavelengths ($750\text{ nm}$, $850\text{ nm}$, $950\text{ nm}$, and $2.3\ \mu\text{m}$). 

- **Key Mineralogical Signature:** The $2.3\ \mu\text{m}$ absorption band is diagnostic of metal-OH vibrational bonds in magnesium/iron smectite clays (phyllosilicates) and carbonates.
- **Astrobiology Utility:** In Jezero Crater's ancient delta, clay-bearing strata hold the highest potential for preserving biosignatures and organic molecules. Aerial NIR mapping allows rapid localization of clay-rich mudstones, directing the ground rover to prime astrobiology sampling sites.

---

## 4. Synthetic Ground-Penetrating Radar (GPR) Sounding

Aboard the heavy conceptual Science Mapper, a low-frequency Ground-Penetrating Radar sounder (RIMFAX analog) models subsurface stratigraphic reflections:

$$\Delta t_{\text{two-way}} = \frac{2 \cdot d_{\text{depth}} \cdot \sqrt{\epsilon_r}}{c}$$

where $\epsilon_r \approx 3.5 - 4.5$ is the apparent relative dielectric permittivity of dry basaltic/sandstone regolith.

### 4.1. Non-Probabilistic Truth Disclosures
In strict compliance with MarsWalk scientific rules:
1. All subsurface radar echoes are explicitly tagged as **`is_synthetic_scenario_model: true`**.
2. Subsurface reflections represent mathematical stratigraphic models of cross-bedded delta sediments.
3. **MANDATORY WARNING:** Subsurface radar reflections must **NEVER be interpreted as confirmed underground water ice**.

---

## 5. Scientific Observation Data Pipeline

Every observation captured by airborne assets is encapsulated in an immutable data structure:
- Unique Observation ID (`OBS-VIS-...`, `OBS-NIR-...`, `OBS-GPR-...`).
- Georeferenced spatial position ($x, y, z_{\text{AGL}}$) and solar time.
- Physical measurement value, SI units, and quantified uncertainty.
- Geological context dictionary and provenance attribution.
- Ingestion into the Atlas Science Return & Data Logistics engine for queued transmission to Earth or peer transfer to ground rovers over UHF proximity links.

> [!WARNING]
> **MANDATORY ASTRONAUT SAFETY DISCLOSURE:**
> All aerial sensor models, spectral band algorithms, GSD projections, and synthetic radar profiles are robotic research tools. They are not rated or certified for human astronaut life support, extravehicular reconnaissance, or crewed landing site certification.
