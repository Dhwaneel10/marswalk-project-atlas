# ATLAS 13AE: ANTENNA FIELD-REGION STANDARDS & AIRY MODEL APPLICABILITY

**Document Identifier:** `ATLAS-DOC-13AE-STAGE-05`  
**Milestone:** 13AE — Propagation Evidence Closure  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** November 2026  
**Status:** Audit Completed — Normative Scope Formalized  

---

## 1. Executive Summary & Audit Mandate

In Milestone 13AD, the antenna modeling subsystem introduced:
1. The triple-condition Fraunhofer far-field threshold:
   $$R_{\text{FF}} = \max\left(\frac{2 D^2}{\lambda}, 5 D, 2\lambda\right)$$
   presented as if it were a universal IEEE/ISED mandated transition distance.
2. The circular aperture Airy diffraction pattern:
   $$F(u) = \left|\frac{2 J_1(u)}{u}\right|^2, \quad u = \frac{\pi D}{\lambda} \sin\theta$$
   applied broadly to parabolic reflectors and optical telescopes.

**Audit Mandate:**
- Separate fundamental electromagnetic field definitions from heuristic engineering screening rules.
- Clarify IEEE Std 145-2013 normative definitions and the findings of foundational antenna literature (e.g. *Where Does the Far Field of an Antenna Start?*, IEEE Antennas and Propagation Magazine).
- Explicitly bound the Airy diffraction formulation to its exact mathematical origin: an **ideal, unobstructed, uniformly illuminated circular planar aperture**.

---

## 2. Demarcating Physical Field Regions from Screening Rules

Electromagnetic field regions surrounding an antenna are continuous wave phenomena. Sharp numerical boundaries are engineering conventions rather than physical discontinuities.

```
                          Antenna Field Regions
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                     │
   Reactive Near-Field                               Radiating Field
   (Energy Storage Zone)                             (Propagating Wavefront)
         │                                                     │
    R < R_reactive                                        ┌────┴────┐
    (Small: lambda / 2*pi)                                │         │
    (Large: 0.62 * sqrt(D^3 / lambda))            Radiating Near-Field  Fraunhofer Far-Field
                                                  (Fresnel Zone)        (Plane Wavefront)
                                                  R_reactive <= R < R_FF  R >= R_FF
```

### 2.1 The Normative IEEE Std 145-2013 Definition
IEEE Std 145-2013 defines the **far-field region (Fraunhofer region)** as:
> *"That region of the field of an antenna where the angular field distribution is essentially independent of the distance from a specified point in the antenna region."*

The standard notes that for an electrically large antenna of maximum overall dimension $D \gg \lambda$:
- The criterion $R \ge \frac{2 D^2}{\lambda}$ corresponds to a maximum wavefront phase deviation of $\pi/8$ radians ($22.5^\circ$) across the aperture from a spherical wavefront compared to an ideal plane wave.
- This phase curvature introduces less than $\approx 0.05\text{ dB}$ to $0.1\text{ dB}$ reduction in on-axis gain and negligible distortion of the first sidelobe.

### 2.2 Provenance of the Triple Condition $\max(2D^2/\lambda, 5D, 2\lambda)$
1. **$R \ge \frac{2 D^2}{\lambda}$ (Rayleigh Phase Criterion):** The classical Fraunhofer criterion for $D \gg \lambda$.
2. **$R \ge 5 D$ (Aperture Distance Ratio):** A rule-of-thumb to ensure higher-order $1/R^2$ reactive terms have decayed by $> 30\text{ dB}$ relative to the $1/R$ radiation term when $D$ is moderate.
3. **$R \ge 2\lambda$ (Small Antenna Wavelength Criterion):** Applied to electrically small antennas ($D \le \lambda / 2$) such as dipoles, monopoles, and small slots (Balanis, *Antenna Theory*, Sec 2.2.4; IEEE Std 145-2013).
   *Crucial Insight:* If one applied $2 D^2 / \lambda$ to a half-wave dipole ($D = \lambda/2$), the resulting distance would be $2 (\lambda/2)^2 / \lambda = 0.5 \lambda$, which falls inside the reactive storage field ($\lambda / 2\pi \approx 0.16\lambda$). Enforcing $R \ge 2\lambda$ prevents this physical absurdity.

**Normative Distinction:**  
The triple condition $\max(2D^2/\lambda, 5D, 2\lambda)$ is **not** an IEEE or ISED legally mandated universal standard. Rather, it is a **conservative engineering screening envelope** that guarantees far-field validity across both electrically small and electrically large apertures without requiring full numerical Maxwell field solvers.

---

## 3. Applicability of the Airy Diffraction Pattern

### 3.1 Physical Derivation & Ideal Assumptions
The Airy pattern:
$$F(u) = \left|\frac{2 J_1(u)}{u}\right|^2, \quad \text{where } u = \frac{\pi D}{\lambda} \sin\theta_{\text{err}}$$
is derived from the Fourier transform of a **uniform aperture field distribution** over a circular planar opening:
$$E(\rho, \phi) = E_0 \quad \text{for } \rho \le D/2$$

Under these ideal mathematical conditions:
- **First Null:** $u_1 = 3.831706 \implies \sin\theta_1 \approx 1.22 \frac{\lambda}{D}$.
- **First Sidelobe Peak:** $u_{\text{peak}} \approx 5.136 \implies F(u) \approx 0.01746$ (**$-17.58\text{ dB}$** relative to boresight).
- **Second Sidelobe Peak:** $u_{\text{peak}} \approx 8.417 \implies F(u) \approx 0.00416$ (**$-23.81\text{ dB}$**).

### 3.2 Deviations in Real Antenna Systems
Real spacecraft and ground antennas deviate significantly from the ideal Airy pattern:

| Antenna Type | Aperture Illumination / Blockage | Real Sidelobe Level vs Ideal Airy ($-17.58\text{ dB}$) | Impact on Pointing Loss & Interference |
| :--- | :--- | :--- | :--- |
| **Parabolic Dish with Taper** | Edge taper ($-10\text{ dB}$ to $-12\text{ dB}$ illumination at rim) | Sidelobes drop to **$-24\text{ dB}$ to $-30\text{ dB}$**; beamwidth broadens ($1.22 \to 1.4\lambda/D$) | Main beam is broader; off-axis sidelobe power is significantly lower than Airy disc. |
| **Cassegrain / Prime Focus Dish** | Central blockage from subreflector + feed struts | Sidelobes increase to **$-14\text{ dB}$ to $-16\text{ dB}$** | Blockage scatters energy into inner sidelobes, degrading gain. |
| **Corrugated Conical Horn** | Hybrid $HE_{11}$ mode taper | Sidelobes suppressed to **$< -35\text{ dB}$** | Near-zero sidelobes; Airy disc completely misrepresents horn patterns. |
| **Microstrip Patch / Array** | Discrete array factor + patch element factor | Grating lobes and asymmetric pattern | Governed by array synthesis, not continuous circular aperture Bessel integral. |

### 3.3 Antenna Pattern Rigor Tiers in Project Atlas
To maintain transparency, Atlas enforces four pattern classifications:
1. **TIER 1 (Authoritative Measured):** Actual measured test-range patterns or regulatory envelopes (e.g. ITU-R S.580 earth station envelope).
2. **TIER 2 (Analytical Approximation):** Ideal circular aperture Airy disc ($J_1(u)/u$), strictly tagged as an analytical approximation valid for circular apertures without blockage.
3. **TIER 3 (Out-of-Domain Guard):** When pointing error exceeds the first two sidelobes ($u > 7.0156$ or $\theta > 2.5\times\text{HPBW}$), a numerical tracking guard ($40.0\text{ dB}$) is applied. **This guard is explicitly declared as a computational limiter (`computational_guard_applied = True`), never disguised as a physical sidelobe measurement.**
4. **TIER 4 (Empirical / Broadbeam):** Omnidirectional dipoles and low-gain antennas ($G \le 3\text{ dBi}$) assigned nominal broadbeam loss ($0.1\text{ dB}$).
