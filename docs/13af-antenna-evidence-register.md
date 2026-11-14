# PROJECT ATLAS — MILESTONE 13AF
# Antenna Evidence Register, Radiation Pattern Provenance & Aperture Demarcation

**Document Identifier:** `ATLAS-DOC-13AF-ANTENNA-REGISTER`  
**Milestone:** 13AF — Atlas Independent Benchmark & Research Freeze  
**Parent Milestone:** 13AE — Propagation Evidence Closure  
**Date:** 2026-11-07  
**Status:** QUALIFIED ELECTROMAGNETIC REGISTER

---

## 1. Executive Summary & Epistemological Boundaries

In Milestone 13AD and 13AE, circular aperture diffraction theory (Airy disc) was implemented to evaluate off-axis pointing losses for directional parabolic dishes.

Milestone 13AF establishes a definitive **Antenna Evidence Register** for all antenna categories utilized across the Atlas communications simulation ecosystem:
1. **The Ideal Airy Pattern is a Theoretical Bound, Not a Universal Dish Model:**
   The classical Airy formula $F(u) = |2 J_1(u) / u|^2$ represents an unblocked, uniformly illuminated circular aperture with a first sidelobe peak down by $-17.57\text{ dB}$. Real reflector antennas incorporate edge illumination taper (reducing sidelobes to $-24\text{ to } -30\text{ dB}$) and feed-support strut blockage (scattering energy and elevating wide-angle sidelobes to $-14\text{ to } -16\text{ dB}$).
2. **Wire and Array Antennas Bypassed:**
   Dipoles, monopoles, and microstrip patch arrays do not follow Bessel/Airy diffraction. They are strictly segregated into broadbeam and cosine-power radiation models.
3. **Evidence Classification:**
   Every antenna model in Atlas is explicitly tagged with its evidence class (`THEORETICAL_IDEAL_APPROXIMATION`, `EMPIRICAL_ITU_MEASURED`, or `ANALYTICAL_BROADBEAM`).

---

## 2. Antenna Evidence Inventory & Technical Classification

Atlas incorporates five distinct antenna categories across its surface rovers, aerial scouts, settlement hubs, and relay orbiters:

| ID | Antenna Category | Primary Application & Band | Physical Geometry | Half-Power Beamwidth (HPBW) | Radiation Pattern Formulation | First Sidelobe Level | Polarization Assumption | Evidence Classification |
|:---|:---|:---|:---|:---|:---|:---:|:---:|:---:|
| **ANT-01** | **Dipole / Monopole** | Rover UHF Proximity Relay (401.5 MHz) | Quarter-wave vertical wire ($L \approx 0.186\text{ m}$) over rover ground plane | $\text{HPBW} \approx 78.0^\circ$ (Omnidirectional in azimuth) | Broadbeam flat model for $\theta \le 40^\circ$; roll-off near ground plane | None (Omni) | Linear Vertical | `ANALYTICAL_BROADBEAM` |
| **ANT-02** | **Parabolic Reflector (Uniform)** | High-Gain Ka-Band Deep Space Dish (32 GHz) | Axisymmetric circular reflector ($D = 1.0 - 3.0\text{ m}$) | $\text{HPBW} \approx 70.0^\circ \frac{\lambda}{D}$ ($0.66^\circ$ for $1.0\text{ m}$ Ka-band) | Airy disc: $F(u) = \|2 J_1(u) / u\|^2$, $u = \frac{\pi D}{\lambda} \sin\theta$ | **$-17.57\text{ dB}$** (Bessel peak at $u = 5.136$) | Right-Hand Circular (RHCP) | `THEORETICAL_IDEAL_APPROXIMATION` |
| **ANT-03** | **Parabolic Reflector (Tapered / Blocked)** | Deep Space Earth Station (Goldstone/Canberra/Madrid DSN) | Cassegrain / Gregorian reflector ($D = 34\text{ m} - 70\text{ m}$) | $\text{HPBW} \approx 75.0^\circ \frac{\lambda}{D}$ | ITU-R S.580 reference envelope: $G(\theta) = 29 - 25 \log_{10}\theta$ | **$-25.0\text{ dB}$** (Maintained via $12\text{ dB}$ feed taper) | Dual Circular (RHCP / LHCP) | `EMPIRICAL_ITU_MEASURED` |
| **ANT-04** | **Conical / Pyramidal Horn** | Medium-Gain X-Band Telemetry (8.4 GHz) | Flared metallic waveguide ($D = 0.20 - 0.40\text{ m}$) | $\text{HPBW} \approx 80.0^\circ \frac{\lambda}{D}$ ($\approx 14.3^\circ$ for $0.20\text{ m}$) | Gaussian main beam approximation: $G(\theta) = G_0 \exp\left(-2.772 (\theta/\text{HPBW})^2\right)$ | **$-20.0\text{ dB}$** | Circular (RHCP) | `ANALYTICAL_APPROXIMATION` |
| **ANT-05** | **Microstrip Patch Array** | Orbiter Relay & Proximity Link (2.2 / 8.4 GHz) | Planar $4 \times 4$ printed patch matrix ($0.15 \times 0.15\text{ m}$) | $\text{HPBW} \approx 32.0^\circ$ | Cosine-power array factor: $F(\theta) = \cos^n(\theta)$ ($n \approx 4 - 6$) | **$-13.0\text{ dB}$** | Circular (RHCP) | `ANALYTICAL_APPROXIMATION` |

---

## 3. Mathematical Formulation of Pattern Models

### 3.1 Model 1: Ideal Circular Aperture (Airy Disc)
Valid strictly for `AntennaCategory.PARABOLIC_REFLECTOR` with uniform aperture distribution:

$$u = \frac{\pi D}{\lambda} \sin\theta$$

$$F(u) = \begin{cases} 
1.0, & |u| < 0.01 \\
\left|\frac{2 J_1(u)}{u}\right|^2, & 0.01 \le |u| \le u_2 \approx 7.0156 \\
\text{Guard Level } (-40.0\text{ dB}), & |u| > 7.0156 \text{ (Tier 3 Out-of-Domain)}
\end{cases}$$

- First Null: $u_1 = 3.831706$ ($\theta_1 = \arcsin(1.22 \lambda / D)$).
- First Sidelobe Peak: $u_{\text{peak}} = 5.135622$, $F(u) = 0.01750$, loss $= -10 \log_{10}(0.01750) = \mathbf{17.57\text{ dB}}$.
- Second Sidelobe Peak: $u_{\text{peak2}} = 8.417244$, $F(u) = 0.00416$, loss $= \mathbf{23.83\text{ dB}}$.

### 3.2 Impact of Realistic Aperture Degradations

#### Edge Illumination Taper
Real feed horns do not illuminate the parabolic reflector uniformly. A typical feed provides a **$-10\text{ dB}$ to $-12\text{ dB}$ edge taper**:
$$E(\rho) = (1 - \rho^2)^p, \quad p \approx 1 - 2$$
- Beam broadening factor: $\text{HPBW} \approx 75.0^\circ \frac{\lambda}{D}$ (vs $58.9^\circ$ for uniform).
- Sidelobe suppression: The first sidelobe level is suppressed from **$-17.57\text{ dB}$ to $-24.5\text{ dB}$** ($p=1$) or **$-30.6\text{ dB}$** ($p=2$).

#### Strut & Subreflector Blockage
Cassegrain subreflectors and quadripod struts obstruct the central aperture and scatter energy:
- Aperture blockage ratio: $\delta = d_{\text{sub}} / D \approx 0.10 - 0.15$.
- Sidelobe elevation: Wide-angle scattered energy raises the average sidelobe envelope by **$+3\text{ to }+6\text{ dB}$**, resulting in net sidelobes near **$-14\text{ to } -16\text{ dB}$**.

---

## 4. Multi-Tier Pointing Error Architecture

To prevent unphysical singular calculations when antennas experience extreme tracking errors, Atlas enforces a three-tier pointing architecture:

```
+-------------------------------------------------------------+
|                  Pointing Error Angle (theta)               |
+-------------------------------------------------------------+
         |
         +---> theta <= HPBW / 2 : TIER 2 (Main Beam)
         |     Loss: -10 * log10(|2*J1(u)/u|^2) in [0, 3 dB]
         |     Guard Applied: False
         |
         +---> HPBW / 2 < theta <= 2.5 * HPBW : TIER 2 (Sidelobes)
         |     Loss: -10 * log10(|2*J1(u)/u|^2) in [3, 24 dB]
         |     Guard Applied: False
         |
         +---> theta > 2.5 * HPBW : TIER 3 (Out-of-Domain Guard)
               Loss: Clamped to 40.0 dB
               Guard Applied: True
               Status: "Tracking null guard applied"
```

If an external measured pattern is available (e.g. DSN standard):
- Evaluates via **`TIER_1_REFERENCE_MEASURED`** using ITU-R S.580.
- `computational_guard_applied = False`.

---

## 5. Software Defensive Guardrails in Atlas

In `src/marswalk/core/atlas_antenna_model.py`:
1. **Aperture Type Discrimination:** Calling `evaluate_radiation_pattern` with `AntennaCategory.DIPOLE_OMNI` or `PATCH_MICROSTRIP` immediately bypasses Airy Bessel calculations and applies broadbeam models.
2. **Dimension Validity:** Physical diameter $D \le 0$ raises `ValueError`.
3. **Carrier Frequency Validity:** Frequency $f \le 0$ raises `ValueError`.
4. **Pointing Disclosures:** Every radiation pattern calculation returns a structured `AntennaRadiationPatternResult` disclosing `model_tier`, `computational_guard_applied`, `hpbw_deg`, and `status_reason`.
