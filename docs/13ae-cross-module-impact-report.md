# PROJECT ATLAS — MILESTONE 13AE
# Cross-Module Downstream Impact Evaluation & Consistency Report

**Mission Designation:** `ATLAS-13AE-PROPAGATION-EVIDENCE-CLOSURE`  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** 2026-11-07  
**Status:** COMPLETE & VERIFIED

---

## 1. Executive Summary

Milestone 13AE establishes verified, scientifically grounded physical models for:
1. Martian atmospheric dust spectral extinction (inverting the erroneous positive Ångström exponent to the validated negative in-situ value $\alpha = -0.082$).
2. Microwave RF dielectric dust-storm attenuation separating CO2 continuum gas absorption from Rayleigh aerosol loss.
3. Rigorous receiver noise temperature transformations invariant across reference planes.
4. IEEE Std 145-2013 compliant antenna field-region screening and aperture applicability boundaries.

This report evaluates the downstream operational impact across the integrated Atlas ecosystem:
- **Orbital Contact Planning & Scheduling** (`atlas_contact_scheduler.py`)
- **Physical Link Budget Engine** (`atlas_network_link_model.py`)
- **Multi-Settlement Network Topology & DTN Routing** (`atlas_network_topology.py`, `atlas_dtn_router.py`)
- **Mission Operations & Environmental Intelligence** (`atlas_environment_*.py`)

---

## 2. Downstream Module Interaction Architecture

The figure below outlines the flow of validated propagation and antenna parameters into operational engines:

```
+-------------------------------------------------------------+
|        atlas_mars_atmospheric_model.py (Remediated)         |
|  - tau_optical(lambda) = tau_880 * (lambda/880)^(-alpha)    |
|  - alpha = -0.082 (Fernandez-Rodriguez 2024 / Lemmon 2019)  |
|  - alpha_dust,RF = 8.186e4 * (M / lambda_cm) * Im(-K)       |
|  - Spherical Chapman Path Integral X(theta)                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|          atlas_network_link_model.py (Remediated)           |
|  - evaluate_atmospheric_loss_db(band, elev, tau)            |
|  - T_sys,A = T_ant + (L-1)*T_L + L*T_rx (Reference Plane A) |
|  - Strict CMB floor (2.725 K) enforcement                   |
+-------------------------------------------------------------+
                              |
            +-----------------+-----------------+
            |                                   |
            v                                   v
+-----------------------+           +-----------------------+
| atlas_contact_        |           | atlas_dtn_router.py   |
| scheduler.py          |           | (Delay-Tolerant Net)  |
| - Dynamic pass contact|           | - Dynamic hop rate    |
|   windows             |           |   adaptation          |
| - Optical/RF handovers|           | - Persistent bundle   |
| - Modulation fallback |           |   custody & storage   |
+-----------------------+           +-----------------------+
```

---

## 3. Detailed Impact Analysis

### 3.1 Optical Communication Link Budgets (1550 nm Deep Space & Proximity)

- **Prior 13AD Behavior:**
  13AD assumed a terrestrial aerosol Ångström exponent of $\alpha = +0.35$. At $\lambda = 1550\text{ nm}$, this resulted in $\tau_{1550} = 0.8202 \cdot \tau_{880}$ (an unphysical 18% thinning of optical depth). At $\tau_{880} = 0.5$, zenith loss was modeled as $1.78\text{ dB}$, and at $10^\circ$ elevation ($X \approx 5.60$), loss was $9.97\text{ dB}$.

- **Remediated 13AE Behavior:**
  Adopting the in-situ coarse dust reference $\alpha = -0.082$ yields $\tau_{1550} = 1.0475 \cdot \tau_{880}$.
  - At $\tau_{880} = 0.5$, zenith optical loss is **$2.27\text{ dB}$** ($+0.49\text{ dB}$ higher than 13AD).
  - At $\tau_{880} = 1.5$ (regional storm), zenith optical loss rises to **$6.82\text{ dB}$** ($+1.48\text{ dB}$ higher than 13AD).
  - At $10^\circ$ elevation during a regional storm ($X \approx 5.60$), optical path loss reaches **$38.2\text{ dB}$** (vs $29.9\text{ dB}$ in 13AD).

- **Operational Consequence:**
  High-rate optical links terminate substantially earlier during low-elevation passes as storm intensity increases. The contact scheduler must advance the optical-to-RF handover threshold, transitioning high-priority telemetry to Ka-band or X-band when optical path attenuation exceeds $15\text{ dB}$.

---

### 3.2 RF Microwave Propagation (UHF, S, X, Ka Bands)

- **Prior 13AD Behavior:**
  13AD asserted that RF attenuation on Mars was $< 0.5\text{ dB}$ across all bands under all dust storm conditions, attributing loss solely to gaseous CO2 continuum absorption.

- **Remediated 13AE Behavior:**
  In accordance with NASA/JPL DESCANSO Pub 02-05 and Goldhirsh (2000), dielectric absorption in basaltic dust aerosols scales linearly with carrier frequency and mass loading $M$:
  $$\alpha_{\text{dust, dB/km}} = 8.186 \times 10^4 \cdot \frac{M}{\lambda_{\text{cm}}} \cdot 0.005468$$

| Scenario | $\tau_{\text{vis}}$ | UHF (401.5 MHz) | X-Band (8.4 GHz) | Ka-Band (32.0 GHz) | Slant Ka ($10^\circ$) |
|:---|:---:|:---:|:---:|:---:|:---:|
| Clear | 0.2 | 0.009 dB | 0.095 dB | 0.332 dB | 1.86 dB |
| Typical | 0.5 | 0.014 dB | 0.208 dB | 0.762 dB | 4.27 dB |
| Regional Storm | 1.5 | 0.032 dB | 0.584 dB | 2.195 dB | 12.29 dB |
| Severe Storm | 3.0 | 0.059 dB | 1.148 dB | 4.345 dB | 24.33 dB |
| Global Dust Event | 5.0 | 0.095 dB | 1.900 dB | 7.212 dB | 40.38 dB |

- **Operational Consequences:**
  1. **UHF Proximity Survivability:** UHF remains virtually impervious ($< 0.1\text{ dB}$ even in global dust events), guaranteeing that surface rover-to-orbiter survival beaconing remains 100% operational.
  2. **X-Band Resilience:** X-band experiences $< 1.2\text{ dB}$ zenith loss in severe storms, maintaining link closure for critical command and science uplinks.
  3. **Ka-Band Degradation:** Ka-band experiences substantial degradation ($> 24\text{ dB}$ slant loss in severe storms). The contact scheduler dynamically throttles Ka-band data rates from 100 Mbps to 10 Mbps or renegotiates forward error correction (FEC) code rates (e.g. LDPC rate 1/2).

---

### 3.3 Receiver System Noise Temperature & Reference Invariance

- **Verification:**
  We demonstrated that evaluating $P_{\text{rx}}$ and $T_{\text{sys}}$ at Plane A (Antenna Terminals) versus Plane B (LNA Input) yields mathematically identical carrier-to-noise spectral density:
  $$\left(\frac{C}{N_0}\right)_A = \frac{P_{\text{ant}}}{k T_{\text{sys,A}}} = \frac{P_{\text{ant}} / L}{k (T_{\text{sys,A}} / L)} = \left(\frac{C}{N_0}\right)_B$$
- **Downstream Consistency:**
  `PhysicalLinkBudgetEngine.evaluate_link` calculates $T_{\text{sys}}$ at Plane A:
  $$T_{\text{sys,A}} = T_{\text{ant}} + (L - 1) T_L + L T_{\text{rx}}$$
  and applies the received power $P_{\text{rx}}$ at the antenna terminals, completely eliminating previous ambiguity or risk of double-counting cable loss $L$.

---

### 3.4 Antenna Field-Region Screening

- **Electrically Small Monopoles (UHF):**
  Monopoles with $D = 0.15\text{ m}$ ($\lambda = 0.747\text{ m}$) are governed by $R_{\text{ff}} = 2\lambda = 1.493\text{ m}$, not $2D^2/\lambda = 0.060\text{ m}$. Proximity links at distances $< 1.5\text{ m}$ (e.g. docked rovers or surface sensor dropoffs) are correctly tagged as radiating near-field (Fresnel), preventing invalid application of far-field Friis path loss.
- **Large Apertures (Ka-Band Dishes):**
  Large dishes ($D = 1.0\text{ m}$) are governed by $2D^2/\lambda = 213.5\text{ m}$. All orbital relay passes ($R > 300\text{ km}$) operate strictly in the far field.

---

## 4. Test Verification Summary

Cross-module consistency has been validated across:
1. `tests/test_milestone_13ae_propagation_evidence_closure.py` (11/11 passed)
2. `tests/test_milestone_13ad_mars_physics_validation.py` (11/11 passed)
3. `tests/test_milestone_13ac_physics_boundaries.py` (17/17 passed)
4. `tests/test_milestone_13ab_numerical_and_defect_closure.py` (13/13 passed)
5. `tests/test_milestone_13y_planetary_network.py` (20/20 passed)

**Conclusion:** All downstream modules operate with full mathematical and scientific consistency under the remediated propagation models. No regressions or interface incompatibilities exist.
