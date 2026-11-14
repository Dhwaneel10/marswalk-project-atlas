# Milestone 13AD — Stage 3: Antenna Field-Region Qualification
## Reactive Near-Field, Radiating Near-Field (Fresnel) & Fraunhofer Far-Field Operational Semantics

**Document Designation:** `ATLAS-13AD-DOC-ANTENNA-FIELD-REGIONS`  
**Milestone:** 13AD — Mars Physics Reference Validation  
**Primary Standards & References:**  
1. IEEE Std 145-2013: *IEEE Standard for Definitions of Terms for Antennas*, IEEE Antennas and Propagation Society.  
2. Innovation, Science and Economic Development Canada (ISED) GL-01 (Issue 3), Section 2.3: *Field Regions of Antennas*.  
3. Balanis, C. A. (2016). *Antenna Theory: Analysis and Design*, 4th ed., John Wiley & Sons.  
**Implementation:** `src/marswalk/core/atlas_antenna_model.py` (`AdvancedAntennaEngine`)  
**Status:** QUALIFIED & CODIFIED  
**Date:** 2026-11-07  

---

## 1. Executive Summary & Defect Remediation

In earlier milestones (13AA–13AC), the Fraunhofer far-field distance was implemented as a single threshold:
$$R_{\text{ff}} = \max\left(\frac{2 D^2}{\lambda}, 2\lambda\right)$$
While this guarded against applying Friis' free-space spherical wave loss when nodes were collocated, it suffered from three critical physical oversimplifications:
1. **Conflation of Near-Field Regimes:** It failed to distinguish between the **reactive near-field** (where quasi-static non-propagating energy dominates and power oscillates back into the transceiver) and the **radiating near-field / Fresnel zone** (where real radiation fields emerge, but wave front curvature across the aperture causes phase errors exceeding $\pi/8$).
2. **Incompleteness of Far-Field Criteria:** Classical antenna engineering (IEEE 145 and ISED GL-01) dictates that the Fraunhofer condition requires three concurrent physical bounds, not just $2 D^2 / \lambda$:
   - Phase error bound across aperture: $R \ge \frac{2 D^2}{\lambda}$ ($\Delta \phi \le 22.5^\circ$).
   - Amplitude uniformity / size bound: $R \gg D$ (conventionally $R \ge 5 D$).
   - Wavelength bound: $R \gg \lambda$ (conventionally $R \ge 2\lambda$ or $1.6\lambda$).
3. **Electrically Small Antennas ($D \le \lambda / 2$):** For electrically small antennas (such as UHF half-wavelength dipoles or rover patch antennas), $2 D^2 / \lambda \le \lambda / 2$. This value lies entirely *inside* the reactive storage field ($R < \lambda / 2\pi$), making $2 D^2 / \lambda$ completely invalid as a far-field demarcation.

---

## 2. Quantitative Tri-Region Demarcation

According to IEEE Std 145-2013 and ISED GL-01 Section 2.3, space surrounding an antenna of maximum physical dimension $D$ radiating at carrier wavelength $\lambda = c / f$ is partitioned into three distinct physical field regions:

```
0 ------------- R_1 = 0.62*sqrt(D^3/lambda) ---------------- R_FF = 2*D^2/lambda -------------> R
  [REACTIVE NEAR-FIELD]       [RADIATING NEAR-FIELD / FRESNEL]        [FRAUNHOFER FAR-FIELD]
  - Stored reactive energy    - Propagating radiation fields          - Planar wavefronts
  - E & H out of phase        - Pattern shape varies with distance     - Invariant angular pattern
  - Friis undefined           - Phase deviation across aperture > pi/8 - Friis 1/R^2 valid
```

### 2.1 Reactive Near-Field ($R < R_1$)
- **Physical Principle:** Non-propagating quasi-static electric and magnetic fields store inductive or capacitive energy. Energy circulates reactively without net real power radiation into the far field.
- **Boundary Expression:**
  - For directive apertures ($D > \lambda$): $R_1 = 0.62 \sqrt{\frac{D^3}{\lambda}}$.
  - For electrically small antennas ($D \le \lambda / 2$): $R_1 = \frac{\lambda}{2\pi} \approx 0.159 \lambda$.
- **Simulation Invariant:** Calculating Friis path loss or claiming an operational radio link in this region is physically invalid. Any transmission in this zone is classified as `REACTIVE_NEAR_FIELD` and strictly rejected.

### 2.2 Radiating Near-Field / Fresnel Zone ($R_1 \le R < R_{\text{FF}}$)
- **Physical Principle:** Radiation fields predominate, but because the distance from the source antenna varies across the physical aperture by more than $\lambda/16$ to $\lambda/8$, spherical wavefronts cannot be approximated as planes. Sidelobes fill in, main-beam gain is depressed, and nulls disappear.
- **Boundary Expression:**
  $$R_{\text{FF}} = \frac{2 D^2}{\lambda}$$
- **Simulation Invariant:** A link budget evaluated in the Fresnel zone cannot close under the assumption of calibrated far-field antenna gain. It is classified as `RADIATING_NEAR_FIELD_FRESNEL` with `validation_status = "OUT_OF_DOMAIN"` and `is_link_closed = False`.

### 2.3 Fraunhofer Far-Field ($R \ge R_{\text{FF}}$)
- **Physical Principle:** Wavefront curvature over the aperture creates a maximum phase deviation $\Delta \phi \le \frac{\pi}{8}\text{ rad} = 22.5^\circ$. Power density decays strictly according to the inverse-square law ($1/R^2$). Angular radiation patterns are independent of distance.
- **Governing Triple Criteria (ISED GL-01 & IEEE 145):**
  $$R \ge \max\left(\frac{2 D^2}{\lambda},\; 5 D,\; 2\lambda\right)$$
- **Simulation Invariant:** Full far-field Friis path loss and standard antenna gain models apply cleanly (`FRAUNHOFER_FAR_FIELD`, `VALID`).

---

## 3. Benchmark Planetary Transceiver Classification

| Planetary Transceiver | Category | Frequency ($f$) | Wavelength ($\lambda$) | Physical Dimension ($D$) | $R_1$ (Reactive) | $R_{\text{Fresnel}}$ | $R_{\text{FF}}$ (Fraunhofer) | Governing Criterion |
|:----------------------|:---------|:----------------|:-----------------------|:-------------------------|:-----------------|:---------------------|:-----------------------------|:--------------------|
| **Rover Proximity UHF** | Dipole/Omni | 401.5 MHz | 0.7467 m | 0.10 m (small) | **0.119 m** | 0.747 m | **1.493 m** | IEEE 145 Small Antenna ($2\lambda$) |
| **MRO Relay X-band** | Parabolic Dish | 8.4 GHz | 0.0357 m | 0.86 m (dish) | **2.622 m** | 41.44 m | **41.44 m** | $2 D^2 / \lambda$ Phase Bound |
| **DSN 70m Earth Station** | High-Gain Dish | 32.0 GHz (Ka) | 0.00938 m | 34.0 m (half-dish) | **3,747 m** | 246.6 km | **246.6 km** | $2 D^2 / \lambda$ Phase Bound |
| **Orbital Laser DSOC** | Telescope | 193.4 THz (1550nm) | 1.55 µm | 0.22 m (aperture) | **1,625 m** | 62.45 km | **62.45 km** | $2 D^2 / \lambda$ Phase Bound |

---

## 4. Metadata Contract & Operating Semantics

In `src/marswalk/core/atlas_antenna_model.py`, every transceiver aperture evaluation yields structured metadata:
- `category: AntennaCategory` (e.g. `PARABOLIC_REFLECTOR`, `DIPOLE_OMNI`)
- `physical_dimension_m: float`
- `wavelength_m: float`
- `reactive_near_field_boundary_m: float`
- `radiating_near_field_boundary_m: float`
- `fraunhofer_far_field_distance_m: float`
- `governing_criterion: str`
- `reference_source: str`
- `is_electrically_small: bool`

Any communication attempt inside $R < R_{\text{FF}}$ returns an explicit `OUT_OF_DOMAIN` qualification, ensuring that near-field operations are never silently computed as closed far-field radio contacts.
