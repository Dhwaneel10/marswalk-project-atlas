# PROJECT ATLAS — MILESTONE 13Q
# INSTRUMENT COMPATIBILITY & PHYSICAL CONSTRAINTS SPECIFICATION
## Spectral Domains, Wavelength Bounds, Standoff Requirements & Environmental Limits

**Milestone:** 13Q — Atlas Autonomous Science Discovery Engine  
**Module:** `src/marswalk/core/science_experiment_design.py`  
**Status:** `QUALIFIED`

---

## 1. Physical Wavelength Boundaries

A core mandate of Milestone 13Q is to enforce physical instrument reality: **an instrument cannot measure what its optics and detectors cannot physically see.**

| Instrument ID | Platform | Spectral Range (nm) | Physical Domain | Supported Measurements | Hard Exclusions |
|---|---|---|---|---|---|
| `MASTCAM_Z` | Rover Mast | $400 - 1000$ nm | VIS + NIR | Color stereo, morphology, 950 nm ferric oxide | **Cannot detect $2.3\ \mu\text{m}$ band** |
| `SUPERCAM_VISIR` | Rover Mast | $400 - 2600$ nm | VIS + NIR + SWIR | Remote micro-imaging, $1.4\ \mu\text{m}, 1.9\ \mu\text{m}, 2.3\ \mu\text{m}$ | Non-contact standoff ($2 - 20\text{ m}$) |
| `PIXL` | Rover Arm | $0.01 - 1.0$ nm | X-Ray Lithochemistry | In-situ sub-mm elemental maps ($\text{Si, Al, Ca, Mg, Fe}$) | Requires abraded rock contact ($< 3\text{ cm}$) |
| `SHERLOC` | Rover Arm | $248.6$ nm | Deep UV Raman | Organic biosignatures, mineral crystal structures | Requires surface contact ($< 5\text{ cm}$) |
| `RIMFAX` | Rover Belly | $150 - 1200$ MHz | GPR Subsurface Radar | Dielectric permittivity layers to $10\text{ m}$ depth | **Synthetic model only; no liquid water claims** |
| `AERO_NAVCAM` | Rotorcraft | $400 - 700$ nm | Visible Optical | High-res aerial scout imagery ($0.78\text{ cm/px}$ at $15\text{ m}$) | Visible only; no mineral spectroscopy |
| `AERO_NIR_SPECTROMETER` | Rotorcraft | $700 - 1050$ nm | Strictly NIR | Iron oxides, mafic silicates | **Excludes $2.3\ \mu\text{m}$ SWIR band** |
| `AERO_SWIR_SOUNDER` | Heavy Mapper | $900 - 2500$ nm | NIR + SWIR | Airborne mapping of $2.3\ \mu\text{m}$ clay/carbonate | High power ($35\text{ W}$), payload mass ($2.5\text{ kg}$) |

---

## 2. Hard Experiment Rejection Conditions

In `ScienceExperimentDesigner.design_experiment()`, invalid experimental configurations are rejected with descriptive exceptions:
1. **Wavelength Out of Range:** Attempting to assign `AERO_NIR_SPECTROMETER` to measure a $2,300\text{ nm}$ absorption feature triggers an immediate exception:
   `"Physical wavelength violation: AERO_NIR operates in range [700, 1050] nm, which CANNOT measure requested 2300 nm."`
2. **Atmospheric Dust Tolerance Exceeded:** If ambient dust optical depth $\tau$ (from MEDA) exceeds an instrument's tolerance ($\tau > 0.60$ for airborne spectrometers), experiment execution is aborted.
3. **Standoff Distance Violation:** In-situ contact instruments (PIXL, SHERLOC) cannot be executed while the rover is in transit or standoff ($d > 0.05\text{ m}$).
