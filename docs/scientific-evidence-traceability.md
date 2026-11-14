# MarsWalk 2.0 / Project Atlas — Scientific Evidence & Traceability Matrix
## Model Inputs, Physical Assumptions, Data Provenance, and Verification Tests

**Milestone:** 12A (Scientific Credibility, System Hardening & Demonstration Readiness)  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  
**Contract Dialect:** JSON Schema Draft 2020-12  

---

## 1. Traceability Matrix Master Overview

The following matrix documents every critical calculation, data source, physical assumption, operational constraint, and verifying test suite across MarsWalk 2.0.

| Output / Quantity | Primary Source / Input Data | Mathematical Formulation / Model | Classification | Limitations & Disclosures | Verifying Automated Test Suite |
|---|---|---|---|---|---|
| **Terrain Elevation & Topography** | USGS CTX DTM (`data/processed/jezero_ready_20m.tif`) | 250×250 raster, 20m cell spacing, planetocentric radius $R=3,396,190\text{ m}$ | Measured Remote Sensing | Remote-sensing optical stereo derivation (nominal 20m/px); sub-pixel hazards (meter-scale boulders) unresolvable. | `tests/test_terrain.py` |
| **Ground Metric Distance ($d$)** | Raster row/col coordinates & affine transform | $d = \sqrt{(\Delta c \cdot dx)^2 + (\Delta r \cdot dy)^2}$, $dx = 20.0 \cdot \cos(18.442^\circ) \approx 18.97\text{ m}$ | Deterministic Geodesy | Metric scale factor valid for Jezero latitude ($18.442^\circ\text{ N}$); distortion increases at higher latitudes. | `tests/test_terrain.py` |
| **Local Terrain Slope ($\theta$)** | Elevation matrix $Z(r, c)$ | Horn's 3×3 finite-difference weighted gradient | Derived Planetary Geometry | Smooths localized sub-pixel scarps; cells with $\theta \ge \theta_{\max}$ treated as impassable cutoff. | `tests/test_terrain.py` |
| **Decameter Roughness ($\sigma_r$)** | Elevation matrix $Z(r, c)$ | Root-mean-square residual of 3×3 uniform box filter | Derived Terrain Metric | Statistical decameter proxy for ground roughness, not direct physical rock abundance. | `tests/test_terrain.py` |
| **Directed Edge Traversal Cost ($C$)** | Distance, slope, roughness, elevation delta ($\Delta z$) | $C(u \to v) = d \cdot [1 + \alpha_s (\theta/\theta_c)^2 + \alpha_r (\sigma/\sigma_0) + \alpha_{\text{up}} \max(0, \Delta z/d)]$ | Mathematical Energy Proxy | Calibrated in "meters of equivalent flat-terrain effort"; derived from Minetti metabolic expenditure relation. | `tests/test_terrain.py`, `tests/test_planner.py` |
| **Crew EVA Velocity & Duration** | Apollo Lunar EVA Traverses (NASA SP-287 / Waligora et al. 1975) | $v_{\text{nom}} = 2.0\text{ km/h}$ ($0.556\text{ m/s}$), $t = C / v$; limit $28,800\text{ s}$ (8h) | Terrestrial / Lunar Analogue | **NOT** validated Mars astronaut performance in 0.38g gravity or pressurized planetary suits. | `tests/test_planner.py`, `tests/test_kinematics.py` |
| **Robotic Rover Velocity & Window** | Mars 2020 Perseverance / MSL Curiosity Telemetry (NASA/JPL) | $v_{\text{nom}} = 0.035\text{ m/s}$ ($0.126\text{ km/h}$); single-sol drive window $14,400\text{ s}$ (4h) | Sourced Technical Value | Based on autonomous auto-nav drive rates; varies with rock abundance and slip. | `tests/test_planner.py` |
| **Locomotion Energy Consumption** | Modeled traverse distance & unit type | Rover: $18.5\text{ Wh/km}$; Suited Crew: $92.0\text{ Wh/km}$ | Planning Approximation | Mathematical model approximation based on mobility literature; not certified in-situ electrical measurements. | `tests/test_milestone_11f_campaign_simulator.py` |
| **Jezero In-Situ Weather** | NASA PDS Mars 2020 MEDA derived logs | Ingests atmospheric pressure, air temp, ground temp, wind speed, optical depth ($\tau$) | In-Situ Archival Observation | Historical archived observations (Perseverance Sol 890); never claimed as "live real-time" telemetry. | `tests/test_milestone_10d_weather_intelligence.py` |
| **Gale Crater In-Situ Weather** | NASA PDS MSL REMS derived logs | Ingests pressure, temp, wind, UV flux | In-Situ Archival Observation | Gale Crater archive (Curiosity Sol 3950); strictly isolated from Jezero; never projected onto other sites. | `tests/test_milestone_10d_weather_intelligence.py` |
| **Olympus Mons Climatology** | Mars Climate Database (MCD v6.1) | General circulation model radiative transfer estimates | Numerical Climatology | GCM numerical simulation, not ground-truth surface measurement. | `tests/test_milestone_10d_weather_intelligence.py` |
| **Candidate Pareto Frontier** | Evaluated campaign objective vectors $\mathbf{z}(c)$ | Strict mathematical dominance: $A \succ B \iff (\forall i, z_i^A \ge z_i^B) \land (\exists j, z_j^A > z_j^B) \land \text{Feasible}(A)$ | Multi-Objective Optimization | Evaluated over bounded grid; non-dominated candidates are optimal *only relative to the evaluated set*. | `tests/test_milestone_11h_campaign_design_space.py` |
| **Digital Twin Temporal Replay** | Coordination plan & A* route paths | Piecewise linear path interpolation with interval activity tracking | Deterministic Simulation | Simulated model for planning and rehearsal; does not represent live telemetry or certified flight operations. | `tests/test_milestone_11f_campaign_simulator.py` |
| **Causal Attribution & Lessons** | Executed timeline intervals vs planned sorties & event ledger | Deterministic pattern matching with required corroborating events | Explainable Diagnostic | Uncorroborated delays classified as `undetermined`; advisory recommendations require operator sign-off. | `tests/test_milestone_11g_campaign_analytics.py` |

---

## 2. Spatial Geodesy & Cartographic Integrity

### 2.1 Coordinate Reference System (CRS)
- **Reference Ellipsoid / Datum:** IAU 2000 Mars Planetocentric Sphere.
- **Volumetric Mean Radius:** $R = 3,396,190.0\text{ meters}$.
- **Equirectangular Projection Metric Scale:**
  $$\Delta x = \Delta c \cdot \text{cell\_size\_m} \cdot \cos(\phi_{\text{ref}})$$
  $$\Delta y = \Delta r \cdot \text{cell\_size\_m}$$
  For Jezero Crater ($\phi_{\text{ref}} = 18.442^\circ\text{ N}$):
  $$\cos(18.442^\circ) \approx 0.94864 \implies \Delta x \approx 18.973\text{ meters/column}$$
  $$\Delta y = 20.000\text{ meters/row}$$

### 2.2 Boundary Safety & NoData Handling Invariants
1. **Out-of-Bounds Protection:** Any spatial index $(r, c)$ outside $[0, 249] \times [0, 249]$ immediately yields traversal cost $\infty$ and distance $\infty$.
2. **NoData Sentinel Rejection:** Cells with elevation $-32,768.0\text{ m}$ or outside credible Martian elevations $[-10,000\text{ m}, +30,000\text{ m}]$ are flagged in `invalid_mask`.
3. **NoData Dilation:** To prevent numerical edge artifacts from Horn's $3\times3$ kernel, all invalid cells are dilated by 1 pixel in 8-connectivity.
4. **Cliff Traversal Hard Gate:** If step slope or destination cell slope $\theta \ge \theta_{\max}$ ($16.0^\circ$ conservative, $22.0^\circ$ balanced, $25.0^\circ$ science), traversal cost is $\infty$.

---

## 3. Atmospheric & Environmental Provenance Safeguards

### 3.1 Data Type & Freshness Hierarchy
Every environmental record generated or displayed by MarsWalk carries explicit provenance tags:
- `IN_SITU_ARCHIVED`: Genuine historical measurements from surface rovers/landers (Perseverance MEDA, Curiosity REMS).
- `CLIMATOLOGICAL_ESTIMATE`: Numerical general circulation model output (Mars Climate Database v6.1).
- `SIMULATED_REPLAY`: Deterministic simulation assumptions for hypothetical future sols.
- `CACHED_FALLBACK`: Offline cached snapshot served when network retrieval is unavailable.

### 3.2 Site Isolation Rules
- Measurements from Gale Crater (MSL Curiosity) are **strictly isolated** to the Gale Crater study site.
- They are **never projected, extrapolated, or blended** into Jezero Crater or Olympus Mons environmental views.
- When an evaluator selects Jezero Crater, only MEDA observations or Jezero-specific climatology are served.

### 3.3 Physical Boundary Guards
All parsed environmental metrics are validated by `PhysicalRangeGuard`:
- Surface Atmospheric Pressure: $10.0\text{ Pa} \le P \le 2,000.0\text{ Pa}$
- Atmospheric Temperature: $130.0\text{ K} \le T_{\text{air}} \le 310.0\text{ K}$ ($-143.15^\circ\text{ C}$ to $+36.85^\circ\text{ C}$)
- Ground Surface Temperature: $130.0\text{ K} \le T_{\text{gnd}} \le 310.0\text{ K}$
- Horizontal Wind Velocity: $0.0\text{ m/s} \le v_{\text{wind}} \le 70.0\text{ m/s}$
- Column Dust Optical Depth: $0.0 \le \tau \le 10.0$

---

## 4. Modeling Assumptions & Disclaimers

### 4.1 Locomotion Energy Expenditure
- **Robotic Rover Traversal:** Modeled at $18.5\text{ Wh/km}$ ($66.6\text{ kJ/km}$) based on Mars 2020 autonomous mobility drive telemetry.
- **Suited Astronaut EVA:** Modeled at $92.0\text{ Wh/km}$ ($331.2\text{ kJ/km}$) based on Apollo lunar surface traverse metabolic studies.
- **Scientific Disclosure:** These values represent mathematical planning proxies for evaluating relative route effort. They do **NOT** represent experimentally measured Mars-gravity suit consumables or battery pack state-of-charge telemetry.

### 4.2 Non-Certification Disclosure
> **MANDATORY AEROSPACE INTEGRITY STATEMENT:**  
> MarsWalk 2.0 (Project Atlas) is a scientific decision-support prototype and mission rehearsal simulator. Passing software test gates, automated preflight checks, or benchmark scenarios **does NOT constitute aerospace operational safety certification, flight readiness review authorization, or live flight software clearance for human extravehicular activities or autonomous planetary rovers.**
