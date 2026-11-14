# Project MarsWalk 2.0 / Atlas — Scientific Claim & Physical Model Audit
**Document ID:** `DOC-MW-M7-CLAIM-AUDIT`  
**Mission Phase:** Mission 7 — Submission Engineering & Final Competition Package (Phase 1)  
**Platform Execution:** Ubuntu 22.04 LTS | Python 3.10.12 (`.venv`)  
**Auditor Role:** Principal Systems Architect, Geodesist, and Independent Scientific Auditor  
**Date of Audit:** 2026-11-14T21:10:00+05:30  

---

## 1. Executive Summary & Epistemological Ground Rules

To ensure complete scientific defensibility for external evaluation, this audit independently verifies the 8 core technical claims, mathematical formulations, physical models, and data provenance in MarsWalk 2.0.

In accordance with NASA planetary science data standards and project rule `AGENTS.md`:
- **Never describe an algorithmic model as a NASA measurement.**
- **Never present synthetic, derived, or simulated quantities as raw historical observations.**
- **Never attribute an equation to physical mechanisms (such as Mie scattering) unless the physical regime, size parameters, and wavelength rigorously support that attribution.**
- **Clearly categorize all data into four distinct tiers:**
  1. `[MEASURED_ARCHIVAL]`: Authentic archived observations directly recorded by Mars surface or orbital instruments (NASA PDS / USGS).
  2. `[DERIVED_GEOSPATIAL]`: Mathematically derived spatial products computed directly from measured datasets (e.g. Horn gradient kernels on DEMs, geodetic coordinate transformations).
  3. `[PHYSICAL_HEURISTIC]`: Algorithmic engineering models based on established physics with simplifying operational assumptions (e.g. A* discrete cost functions, Beer-Lambert optical attenuation).
  4. `[ILLUSTRATIVE_SIMULATION]`: Illustrative engineering proxies created to demonstrate mission operations scenarios, delay-tolerant networking, and failure recovery protocols.

---

## 2. Comprehensive Claim-by-Claim Scientific Audit

### Claim 1: MEDA Dust Optical Depth and the Sol 89 Dust-Storm Preset
- **Claim:** MarsWalk incorporates authentic Mars 2020 MEDA (Mars Environmental Dynamics Analyzer) atmospheric measurements, including surface pressure, air temperature, wind velocity, and column dust optical depth ($\tau$) across diurnal cycles and dust storm scenarios.
- **Original Source / Reference:**
  - Primary Publication: Rodriguez-Manfredi et al. (2021), *The Mars Environmental Dynamics Analyzer (MEDA) Instrument on the Mars 2020 Mission*, Space Science Reviews 217, 48.
  - Data Node: NASA Planetary Data System (PDS) Atmospheres Node, Mars 2020 Mission Archive.
  - Local Catalog: `data/catalogs/meda_environmental_observations.json` (SHA-256: `ed8be71b7b13...`).
- **Implementation Location:**
  - `src/marswalk/api/service.py` (`pillars_environment_meda_api` and `pillars_environment_meda_calibrate_api`, lines 10830–11010).
- **Units & Assumptions:**
  - Pressure: Pascals ($\text{Pa}$), typical diurnal range $690\text{--}775\,\text{Pa}$.
  - Temperature: Degrees Celsius ($^\circ\text{C}$), diurnal range $-88.4^\circ\text{C}$ (night) to $-11.2^\circ\text{C}$ (afternoon).
  - Wind Speed: Meters per second ($\text{m/s}$), baseline mean $4.8\,\text{m/s}$, storm peak $18.4\text{--}24.6\,\text{m/s}$.
  - Column Optical Depth: Dimensionless ($\tau$), measured at $\lambda \sim 880\,\text{nm}$ (MEDA Radiation and Dust Sensors). Baseline clear sol $\tau \approx 0.82$; moderate dust storm $\tau \approx 1.06\text{--}2.45$; severe global storm $\tau \approx 3.25\text{--}4.10$.
- **Classification:** **`[MEASURED_ARCHIVAL]`** (Baseline diurnal profiles and historical MEDA telemetry) + **`[ILLUSTRATIVE_SIMULATION]`** (The specific Sol 88–92 dust storm timing and injection in the flagship scenario).
- **Validation & Limitations:**
  - *Validation:* Values cross-checked against PDS MEDA calibrated data records (CDR).
  - *Limitation:* The flagship mission scenario injects an illustrative composite dust event occurring on Sols 88–92 to stress-test rover autonomy; it reflects realistic Martian seasonal storm magnitude but is not a literal replay of a historical sol-by-sol mission failure.

---

### Claim 2: The Reported 71.3% Solar-Power Loss and 258.1 W Output
- **Claim:** Atmospheric dust extinction reduces rover solar array generation by $71.3\%$, dropping clean rated capacity from $900.0\,\text{W}$ nominal to $258.1\text{--}258.6\,\text{W}$.
- **Original Source / Reference:**
  - Plane-parallel atmospheric extinction: Beer-Lambert-Bouguer law:
    $$T(\tau, z) = \exp\left(-\frac{\tau}{\cos z}\right)$$
    where $\tau$ is column optical depth and $z$ is solar zenith angle ($\cos z \approx 0.85$ for Jezero crater sub-tropical midday at $18.4^\circ\text{N}$).
- **Implementation Location:**
  - `src/marswalk/api/service.py` (`pillars_environment_meda_calibrate_api`, lines 10970–10995):
    ```python
    solar_transmission = float(np.exp(-tau / 0.85))
    solar_power_watts = round(900.0 * solar_transmission, 1)
    solar_attenuation_pct = round((1.0 - solar_transmission) * 100.0, 1)
    ```
- **Units & Assumptions:**
  - Rated Clean Array Output: $P_0 = 900.0\,\text{W}$ at zero optical depth ($\tau = 0$, top of atmosphere).
  - Effective zenith path length: $\cos z \approx 0.85$.
  - Exact derivation of $71.3\%$ loss:
    $$T = \exp\left(-\frac{1.06}{0.85}\right) = \exp(-1.247) = 0.2874 \implies P = 900.0 \times 0.2874 = 258.6\,\text{W} \quad (\text{loss } = 71.3\%)$$
  - Severe Storm ($\tau = 2.45$):
    $$T = \exp\left(-\frac{2.45}{0.85}\right) = \exp(-2.882) = 0.0560 \implies P = 900.0 \times 0.0560 = 50.4\,\text{W} \quad (\text{loss } = 94.4\%)$$
- **Classification:** **`[PHYSICAL_HEURISTIC]`**.
- **Crucial Real-World Disclosure:**
  - **Perseverance itself is powered by an MMRTG** (Multi-Mission Radioisotope Thermoelectric Generator producing $\approx 110\,\text{W}$ steady electrical power from plutonium-238 decay), **NOT solar arrays!**
  - This solar attenuation model is an **analogue mission simulation model** applicable to solar-powered Martian surface vehicles (such as MER Spirit & Opportunity, Mars Pathfinder/Sojourner, InSight, and future solar-powered crew EVA pressurized rovers). The system now explicitly discloses this distinction in all UI headers.

---

### Claim 3 & 4: The RF Dust Attenuation Model & Rejection of "Mie Scattering at X-band"
- **Claim:** Mission 6 reported an RF dust attenuation model:
  $$\alpha_{\text{RF}} = 0.008 + 0.098 \cdot \tau^{1.15}\,\text{dB/km}$$
  and attributed this attenuation to "Mie scattering at X-band".
- **Physical Analysis & Audit Findings:**
  1. **Scattering Regime Examination:**
     - The scattering regime of a spherical particle of radius $a$ illuminated by electromagnetic radiation of wavelength $\lambda$ is governed by the dimensionless size parameter:
       $$x = \frac{2\pi a}{\lambda}$$
     - Airborne Martian dust has a log-normal effective radius distribution with mean $a \approx 1.5\,\mu\text{m} = 1.5 \times 10^{-6}\,\text{m}$ (Pollack et al. 1979; Tomasko et al. 1999).
     - At optical wavelengths ($\lambda \approx 0.6\,\mu\text{m}$), $x \approx \frac{2\pi(1.5)}{0.6} \approx 15.7 \gg 1$. Here, **Mie scattering theory rigorously applies**, causing strong visible sunlight extinction ($\tau$).
     - At **X-band deep-space telecommunications frequencies** ($f \approx 8.4\,\text{GHz}$, $\lambda \approx 3.57\,\text{cm} = 35,700\,\mu\text{m}$):
       $$x = \frac{2\pi(1.5\,\mu\text{m})}{35,700\,\mu\text{m}} \approx 2.64 \times 10^{-4} \ll 1$$
     - Because $x \ll 1$, microwave propagation through Martian dust lies strictly in the **Rayleigh scattering regime**, **NOT Mie scattering!**
  2. **Extinction Physics in the Rayleigh Regime:**
     - In the Rayleigh regime, the scattering cross-section $\sigma_s \propto x^4 \propto \lambda^{-4}$, which is completely negligible at microwave frequencies ($< 10^{-14}\,\text{m}^2$).
     - The absorption cross-section $\sigma_a \propto x \propto \lambda^{-1}$, which dominates over scattering by 4 to 6 orders of magnitude.
     - Published microwave propagation studies for Mars (Goldhirsh 1982; Simpson et al. 1993) confirm that at X-band (8.4 GHz), dust attenuation on Mars is negligible (typically $< 0.01\text{--}0.03\,\text{dB/km}$) even in heavy dust storms.
     - At UHF frequencies (401.58 MHz Electra proximity link to MRO/TGO orbiters, $\lambda \approx 74.7\,\text{cm}$), $x \approx 1.2 \times 10^{-5}$, and dust attenuation is completely imperceptible ($\approx 0.008\,\text{dB/km}$).
- **Verdict & Necessary Corrections:**
  - Attributing this formula to "Mie scattering at X-band" is **scientifically invalid**.
  - The equation $\alpha_{\text{RF}} = 0.008 + 0.098 \cdot \tau^{1.15}\,\text{dB/km}$ is an **`[ILLUSTRATIVE_HEURISTIC_PROXY]`** intended as an operational engineering placeholder to couple atmospheric dust density to communications link margins.
  - *Actions Taken:*
    1. Removed all claims of "Mie scattering at X-band" from the UI, API metadata, and documentation.
    2. Documented the model as `ILLUSTRATIVE_HEURISTIC_PROXY` in `service.py`, explicitly stating that UHF link attenuation is $\approx 0.008\,\text{dB/km}$ (transparent) and X-band dust extinction is Rayleigh absorption-dominated.

---

### Claim 5: The 30m Science-Target Interception Radius
- **Claim:** The route planner requires the rover to approach within $R_{\text{intercept}} = 30.0\,\text{m}$ of a science target's geolocated coordinate for that target to count as "sampled" and award its astrobiological yield.
- **Implementation Location:**
  - `src/marswalk/api/service.py` (`pillars_science_targets_plan_api`, lines 11075–11110):
    ```python
    INTERCEPTION_RADIUS_M = 30.0
    # Euclidean distance from path cells (r, c) to target (r_tgt, c_tgt)
    # Target intercepted if min_dist <= 30.0m
    ```
- **Physical Rationale:**
  - The digital elevation model grid resolution is $\Delta x = 20.0\,\text{m/px}$.
  - A path that transits adjacent diagonally to a target cell center has an offset of $\sqrt{10^2 + 10^2} \approx 14.1\,\text{m}$. A path one cell away has an offset of $20.0\text{--}28.3\,\text{m}$.
  - $R_{\text{intercept}} = 30.0\,\text{m}$ ($1.5 \times$ cell pitch) represents the minimum grid-consistent threshold ensuring the planner purposefully commanded a traversal step to the site.
  - Direct baseline transits bypass Wildcat Ridge by $297.3\,\text{m}$ and Kodiak Butte by $835.5\,\text{m}$, which legitimately fail this threshold.
- **Classification:** **`[PHYSICAL_HEURISTIC]`** (Algorithmic Discretization Threshold).

---

### Claim 6: The 160-Point Science Reward & Route Energy Calculation
- **Claim:** Multi-Objective A* routing from Three Forks Depot to Delta Scarp Rim Crest yields $+160\,\text{points}$ of astrobiological value for Route B at the cost of $+3,096.5\,\text{m}$ ($+134.1\%$) distance and $+907.2\,\text{Wh}$ ($+137.5\%$) mobility energy.
- **Implementation Location:**
  - `src/marswalk/api/service.py` (`pillars_science_targets_plan_api`, lines 11115–11175).
- **Mathematical Formulations:**
  1. *Science Yield Score:*
     - Wildcat Ridge (`sci_wildcat_ridge`): $+95\,\text{pts}$ (SHERLOC deep-UV Raman detection of organic aromatic carbon in sulfate mudstone).
     - Kodiak Butte (`sci_kodiak_butte`): $+65\,\text{pts}$ (Stratified bottomset/foreset deltaic sandstone outcrop).
     - Total: $95 + 65 = 160\,\text{pts}$.
  2. *Mobility Energy Proxy:*
     $$E_{\text{mobility}} = \left(\frac{d}{3.5}\right) + (N_{\text{targets}} \times 11.25)\,\text{Wh}$$
     - Physical translation: $d / 3.5 = 0.2857\,\text{Wh/m} \approx 286\,\text{Wh/km}$.
     - For a $1,025\,\text{kg}$ rover with 6 drive motors moving at $0.042\,\text{m/s}$ consuming $\approx 100\,\text{W}$ drive power, energy expenditure is $\approx 0.66\,\text{Wh/m}$ on loose sand, or $\approx 0.25\text{--}0.35\,\text{Wh/m}$ for steady cruising on hard deltaic pavement.
     - $11.25\,\text{Wh}$ represents $\approx 45\,\text{minutes}$ of robotic arm turret deployment and instrument sensor interrogation at $\approx 15\,\text{W}$.
- **Classification:** **`[PHYSICAL_HEURISTIC]`** (Engineering Heuristic Mobility & Payload Energy Proxy).

---

### Claim 7: 33.2 km Rover Traverse and 10 Three Forks Depot Sample Tubes
- **Claim:** MarsWalk indexes 33.2 km of historical tactical positions across 1,896 sols and 10 sealed titanium sample tubes deposited at the Three Forks surface cache.
- **Original Source / Reference:**
  - NASA Planetary Data System (PDS) Geosciences Node, Mars 2020 Mission Archive.
  - `data/raw/m2020_places/best_tactical.csv` (SHA-256: `9da19e4f7028...`, 577 tactical localization sites).
  - NASA JPL Three Forks Sample Depot Catalog, Sols 653–680 (`data/catalogs/three_forks_sample_depot.json`, SHA-256: `afdf6515ed00...`).
- **Classification:** **`[MEASURED_ARCHIVAL]`**.
- **Provenance Accuracy Check:**
  - Tube #241 (*Malay*, Amalik outcrop) is confirmed at Three Forks depot (deposited Sol 653).
  - Tube #239 (*Bearwallow*, paired core with Hazelton) is confirmed at Three Forks depot (deposited Sol 674).
  - Tube #268 (*Hazelton*, cored from Wildcat Ridge) is confirmed **retained onboard Perseverance**.

---

### Claim 8: Merkle Root and DTN Recovery Claims
- **Claim:** The "When Mars Goes Dark" scenario reconciles 7 lifecycle state snapshots into a bit-exact Merkle root `0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8` and achieves 100% DTN bundle custody (0 bytes lost during 4-hour blackout).
- **Implementation Location:**
  - `src/marswalk/simulation/flagship/` and `src/marswalk/api/service.py` (`flagship_when_mars_goes_dark_replay_api`).
- **Technical Analysis:**
  - *Merkle Tree:* A deterministic cryptographic tree hashing the exact JSON state strings of the 7 stages (Initial Sortie, Dust Front Ingress, Comms Blackout, Rockfall Hazard, Safe Hold, Autonomous Detour, Line-of-Sight Restored). Root: `0380a7cf...`.
  - *DTN Protocol:* A simulation of the RFC 9171 Delay-Tolerant Networking Bundle Protocol. Six simulated telemetry bundles are stored in an in-memory custodian buffer during the communication loss and released when Line-of-Sight to MRO is restored.
- **Classification:** **`[DETERMINISTIC_CRYPTOGRAPHIC]`** (Merkle Tree) + **`[ILLUSTRATIVE_SIMULATION]`** (RFC 9171 DTN Protocol Execution).

---

## 3. Epistemological Classification Matrix

| Claim / Capability | Primary Source | Implementation File | Category | Scientific Defensibility |
| :--- | :--- | :--- | :--- | :--- |
| **USGS Jezero CTX 20m DEM** | USGS Astrogeology (DOI: 10.5066/P9T31O12) | `terrain.py`, `service.py` | `[MEASURED_ARCHIVAL]` | High (Peer-reviewed USGS planetary DTM) |
| **USGS TRN HiRISE 1m DTM** | USGS Astrogeology (DOI: 10.5066/P13CPYYU) | `terrain.py`, `service.py` | `[MEASURED_ARCHIVAL]` | High (1.0m/px stereo photogrammetry) |
| **Horn 8-Neighbor Slope** | Horn (1981) finite-difference kernel | `terrain.py` | `[DERIVED_GEOSPATIAL]` | High (Standard GIS slope formulation) |
| **Rover PLACES Traverse (33.2km)** | NASA PDS Mars 2020 (`best_tactical.csv`) | `service.py` | `[MEASURED_ARCHIVAL]` | High (Archival NASA localization) |
| **Three Forks Sample Depot (10 Tubes)** | NASA JPL Mars 2020 Depot Manifest | `service.py` | `[MEASURED_ARCHIVAL]` | High (Corrected tube serials & paired cores) |
| **MEDA Atmospheric Profiles** | NASA PDS MEDA (Rodriguez-Manfredi 2021) | `service.py` | `[MEASURED_ARCHIVAL]` | High (In-situ ground truth) |
| **Solar Power Attenuation** | Beer-Lambert Law $T = \exp(-\tau / 0.85)$ | `service.py` | `[PHYSICAL_HEURISTIC]` | Solid (Disclosed as analogue rover model) |
| **RF Dust Path Attenuation** | Empirical formula $\alpha = 0.008 + 0.098\tau^{1.15}$ | `service.py` | `[ILLUSTRATIVE_HEURISTIC_PROXY]` | Reclassified (Rayleigh absorption proxy, Mie rejected) |
| **30m Science Interception Radius** | Grid cell pitch geometry ($1.5 \times 20\text{m}$) | `service.py` | `[PHYSICAL_HEURISTIC]` | Solid (Standard raster proximity threshold) |
| **A* Multi-Objective Routes** | Multi-Objective A* on CTX 20m grid | `service.py` | `[PHYSICAL_HEURISTIC]` | Solid (Deterministic, non-human-safe) |
| **Merkle State Proof** | SHA-256 Merkle tree on 7 state snapshots | `service.py` | `[DETERMINISTIC_CRYPTOGRAPHIC]` | High (Bit-exact, tamper-evident) |
| **DTN Comms Blackout Replay** | RFC 9171 Bundle Protocol custodian buffer | `service.py` | `[ILLUSTRATIVE_SIMULATION]` | Solid (Demonstrator for autonomous resilience) |

---

## 4. UI & Documentation Adjustments Made

1. **Replaced Misleading "Mie Scattering at X-band" Labels:**
   - In `service.py`, `web/app.js`, and documentation, removed assertions that microwave X-band attenuation is governed by Mie scattering.
   - Added explicit disclosures that at X-band ($8.4\,\text{GHz}$), Martian dust ($a \sim 1.5\,\mu\text{m}$) operates strictly in the **Rayleigh scattering regime** ($x \sim 2.6 \times 10^{-4} \ll 1$), where absorption dominates and UHF links are transparent ($\approx 0.008\,\text{dB/km}$).
2. **Explicit Solar Rover Analogue Disclosure:**
   - Updated documentation and UI badges to explicitly note that Perseverance is powered by an MMRTG, and that the solar array model is an **analogue mission simulation model** for solar-powered planetary exploration.
3. **API Parameter Injection:**
   - Updated `pillars_environment_meda_calibrate_api` to actively parse custom operator inputs (`optical_depth_tau`, `air_temp_c`, `pressure_pa`, `wind_speed_ms`), ensuring calibration actions directly affect derived values.
4. **Three Forks Depot Integrity:**
   - Ensured Tube #241 (*Malay*) and Tube #239 (*Bearwallow*) are accurately displayed at Three Forks, while *Hazelton* (#268) is marked as retained onboard the rover.
