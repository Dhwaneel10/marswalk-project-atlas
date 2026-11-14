# Project Atlas: Known Limitations & Scientific Boundaries

**Document ID:** `ATLAS-DOC-LIMIT-001`  
**Classification:** Scientific Disclosure & Research Scope  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. Explicit Scientific Disclosures

Project Atlas / MarsWalk 2.0 is an academic and engineering research simulation framework developed for mission architecture studies. It is **NOT flight-certified operational software**, and **CANNOT be used to certify human life-support safety for real astronaut missions**.

Reviewers and researchers must take note of the following explicit engineering simplifications:

---

## 2. Technical Limitations by Subsystem

### 1. Planetary Topography & Spatial Extent
- **Surveyed Boundary:** Quantitative traversals and hazard analyses are strictly valid within the $5.0 \times 5.0\text{ km}$ study zone of Jezero Crater covered by the USGS 20 m/pixel CTX DTM.
- **Sub-Pixel Hazards:** Micro-boulders ($< 0.5\text{ m}$) and localized wheel-trap sand ripples below the 20 m DTM spatial resolution are modeled statistically via terrain roughness heuristics rather than direct optical detection.

### 2. Rotorcraft Aerodynamics & Flight Mechanics
- **Point-Mass Dynamics:** Aerial vehicle simulation utilizes 3-degree-of-freedom (3-DOF) point-mass momentum theory with empirical compressible drag corrections.
- **Excluded Aeroelasticity:** Non-linear blade vortex interactions (BVI), cyclic swashplate flutter, and unsteady gusts during transition from forward flight to hover are not modeled.

### 3. Deep Space Telecommunications
- **Geometric LOS Modeling:** Radio frequency (RF) line-of-sight between rovers, rotorcraft, and orbiters accounts for DTM terrain occlusion and planetary curvature, but does not simulate multi-path surface scattering or ionospheric scintillation.
- **Orbital Passes:** Orbiter overflight communication windows use Keplerian orbital geometry with fixed antenna gain profiles.

### 4. Chemical ISRU & Catalytic Degradation
- **Ideal Kinetic Yields:** Chemical reactions (Sabatier methanation and solid oxide electrolysis) assume stoichiometric yields under regulated thermal envelopes. Real-world catalyst poisoning (e.g. sulfur or chlorine in Martian dust) is not modeled dynamically.
- **Phase Separation:** Complete cryogenic separation of liquid methane ($CH_4$) and water ($H_2O$) is assumed without thermodynamic boil-off losses.

### 5. Habitat Thermal & Structural Fidelity
- **Lumped Thermal Model:** Habitat internal thermal regulation uses a single-node lumped thermal capacitance model with bulk conductive heat loss ($U \cdot A \cdot \Delta T$). Finite-element internal airflow and 3D thermal stratification are simplified.
- **Radiation Attenuation:** Regolith shielding effectiveness against Galactic Cosmic Rays (GCR) and Solar Particle Events (SPE) is modeled using published linear mass-attenuation coefficients rather than full Monte Carlo HZETRN transport codes.

### 6. Probability & Risk Assertions
- **Gauntlet Scenarios:** Stress-testing gauntlets (rockfalls, motor deratings, dust storms) represent deterministic engineering stress tests rather than empirical failure probability distributions.
