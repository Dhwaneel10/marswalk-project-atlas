# Milestone 13AC — Stage 1: Free-Space Propagation Validity Audit
## Fraunhofer Far-Field Boundaries, Reactive Near-Field Limits & Electromagnetic Propagation Semantics

**Document Designation:** `ATLAS-13AC-DOC-STAGE1-FSPL`  
**Milestone:** 13AC — Physics Boundary Qualification  
**Module Audited:** `src/marswalk/core/atlas_network_link_model.py` (`PhysicalLinkBudgetEngine`)  
**Status:** QUALIFIED & IMPLEMENTED  
**Date:** 2026-11-07  

---

## 1. Executive Summary & Problem Formulation

In Milestone 13AA and 13AB, free-space path loss (FSPL) was guarded against crashes (e.g. division-by-zero or $\log_{10}(0)$) by clamping non-positive distances ($R \le 0$) to $0.0\text{ dB}$. While this achieved mathematical stability and satisfied NaN/Inf rejection tests, it created a severe physical inconsistency:
1. **Unphysical Energy Gain / Conservation of Energy Violation:** Friis' transmission equation:
   $$\text{FSPL} = 20\log_{10}\left(\frac{4\pi R}{\lambda}\right) = 20\log_{10}\left(\frac{4\pi R f}{c}\right)$$
   For any distance $R < \frac{\lambda}{4\pi}$, the dimensionless ratio $\frac{4\pi R}{\lambda} < 1$, resulting in $\text{FSPL} < 0.0\text{ dB}$. A negative path loss in passive propagation asserts that received power exceeds transmitted EIRP without an external gain medium or active amplifier—a direct violation of thermodynamics.
2. **Conflation of Local Bus with Free-Space Radiative Transfer:** At $R = 0$, free-space spherical wave expansion is non-existent. Two collocated subsystems (e.g., an instrument connected via SpaceWire, Ethernet, or backplane bus) do not experience electromagnetic propagation across Martian space. Assigning $\text{FSPL} = 0.0\text{ dB}$ via Friis implied free-space propagation with 100% antenna capture, rather than an explicit guided-wave or local bus interface.
3. **Fraunhofer Far-Field Breakdown:** Directive high-gain antennas (such as Ka-band 3.0 m Mars-to-Earth reflectors or UHF 0.5 m helical arrays) require a finite physical distance before spherical wavefronts approximate plane waves across the receiving aperture. Operating inside the Fraunhofer distance violates plane-wave assumptions, causing severe phase cancellation, gain degradation, and reactive coupling.

---

## 2. Electromagnetic Propagation Regimes

Electromagnetic radiation around an antenna aperture of maximum physical dimension $D$ at carrier wavelength $\lambda = c / f$ is rigorously partitioned into three distinct physical regimes:

```
0 ------------ lambda/(4*pi) ---------------- 0.62*sqrt(D^3/lambda) ---------------- 2*D^2/lambda -------------> R
  [Reactive Near-Field]   [Radiating Near-Field / Fresnel]       [Fraunhofer Far-Field]
  (FSPL < 0 dB unphysical)   (Phase variations across aperture)   (Spherical Friis valid)
```

### 2.1 Sub-Wavelength Reactive Near-Field ($R < \frac{\lambda}{4\pi}$)
In this region, non-propagating quasi-static electric and magnetic fields dominate. Energy is stored reactively rather than radiated into the far field.
- For Friis' formula, $R < \frac{\lambda}{4\pi} \implies 4\pi R / \lambda < 1 \implies \text{FSPL} < 0\text{ dB}$.
- **Physical Semantics:** Calculating FSPL in this regime is physically invalid. Attempting to invoke `calculate_free_space_path_loss(R, f)` for $R < \frac{\lambda}{4\pi}$ must raise an explicit `ValueError`.

### 2.2 Radiating Near-Field (Fresnel Zone, $\frac{\lambda}{4\pi} \le R < R_{\text{ff}}$)
Here radiation fields emerge, but the distance from the source antenna varies across the aperture of the receiving antenna by a fraction of a wavelength, causing phase non-uniformity and gain reduction.
- The boundary between radiating near-field and far-field is the **Fraunhofer distance**:
  $$R_{\text{ff}} = \frac{2 D^2}{\lambda} = \frac{2 D^2 f}{c}$$
- For antennas where the physical aperture $D < \lambda$ (e.g. dipoles or low-gain patches), the Fraunhofer distance is bounded by $2\lambda$.
- **Physical Semantics:** Friis spherical expansion does not accurately model power transfer in the Fresnel zone. A link evaluated in this regime cannot claim a closed operational margin based on far-field Friis assumptions. In `evaluate_link`, it is classified as `NEAR_FIELD_OUT_OF_DOMAIN`, with `is_physically_available = False`, `validation_status = "OUT_OF_DOMAIN"`, and `is_link_closed = False`.

### 2.3 Fraunhofer Far-Field ($R \ge R_{\text{ff}}$)
In the Fraunhofer regime, wave fronts are locally planar across the aperture, angular radiation patterns are invariant with distance, and power density decays strictly according to the inverse-square law ($1 / R^2$).
- Friis' spherical expansion equation holds with high precision.
- **Physical Semantics:** Classified as `operating_domain = "FAR_FIELD_FREE_SPACE"` (or `"INTERPLANETARY_DEEP_SPACE"` for interplanetary scales $R > 4\times 10^{11}\text{ m}$), with `validation_status = "VALID"`.

---

## 3. Engineering Quantification of Apertures & Boundaries

To enable automated evaluation across Atlas transceiver configurations, the effective aperture diameter $D$ is derived from nominal antenna gain $G_{\text{dBi}}$ and carrier frequency $f$:

$$G = \eta \left(\frac{\pi D}{\lambda}\right)^2 \implies D = \frac{\lambda}{\pi} \sqrt{\frac{10^{G_{\text{dBi}} / 10}}{\eta}}$$

where $\eta \approx 0.55$ represents nominal aperture efficiency for parabolic and horn antennas. For low-gain antennas ($G_{\text{dBi}} \le 3.0\text{ dBi}$), aperture dimension is bounded by $\lambda / 2$.

### Benchmark Transceiver Regimes in Project Atlas:
| System Configuration | Band | Frequency ($f$) | Wavelength ($\lambda$) | Gain ($G$) | Eff. Aperture ($D$) | Fraunhofer Dist ($R_{\text{ff}}$) | Reactive Limit ($\lambda/4\pi$) |
|:---------------------|:-----|:----------------|:-----------------------|:-----------|:--------------------|:-----------------------------------|:--------------------------------|
| Rover Proximity UHF  | UHF  | 401.5 MHz       | 0.7467 m               | 5.0 dBi    | 0.57 m              | 1.49 m                             | 0.0594 m (5.9 cm)               |
| MRO Relay X-band     | X    | 8.4 GHz         | 0.0357 m               | 35.0 dBi   | 0.86 m              | 41.5 m                             | 0.0028 m (2.8 mm)               |
| DSN Earth Station    | Ka   | 32.0 GHz        | 0.00937 m              | 68.0 dBi   | 34.0 m              | 246.5 km                           | 0.00075 m (0.75 mm)             |
| Deep Space Optical   | Opt  | 193.4 THz       | 1.55 µm                | 110.0 dBi  | 0.22 m              | 62.5 km                            | 0.123 µm                        |

---

## 4. Code Remediation & Semantic Guarantees

In `src/marswalk/core/atlas_network_link_model.py`:
1. `calculate_free_space_path_loss(range_m, freq_hz)`:
   - $R < 0$: raises `ValueError("Propagation range cannot be negative: ...")`.
   - $R == 0$: raises `ValueError("Propagation range cannot be zero for far-field free-space link. Collocated nodes require direct local/wired interface.")`.
   - $R < \frac{\lambda}{4\pi}$: raises `ValueError("Propagation range ... is within sub-wavelength reactive near-field ... Friis free-space formula is invalid (yields negative loss).")`.
2. `PhysicalLinkBudgetEngine.calculate_antenna_aperture_diameter_m(gain_dbi, freq_hz, efficiency)` added.
3. `PhysicalLinkBudgetEngine.calculate_fraunhofer_distance_m(aperture_diameter_m, freq_hz)` added.
4. `evaluate_link(tx, rx, slant_range_m, ...)`:
   - For $R == 0$: returns `operating_domain="COLLOCATED_LOCAL_INTERFACE"`, `validation_status="VALID_LOCAL_DIRECT"`, `is_link_closed=True`, `propagation_delay_s=0.0`.
   - For $0 < R < R_{\text{ff}}$: returns `operating_domain="NEAR_FIELD_OUT_OF_DOMAIN"`, `validation_status="OUT_OF_DOMAIN"`, `is_link_closed=False`, `is_physically_available=False`.
   - For $R \ge R_{\text{ff}}$: proceeds with deterministic link budget calculation.

---

## 5. Verification Evidence
- Legacy tests expecting $0.0\text{ dB}$ on $R \le 0$ have been updated to assert `ValueError`.
- Metamorphic verification confirms $R \ge R_{\text{ff}}$ increases path loss monotonically by $20\log_{10}(2) \approx 6.02\text{ dB}$ upon doubling distance.
- Zero silent clamps remain in the free-space propagation pathway.
