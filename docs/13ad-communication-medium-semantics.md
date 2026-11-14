# ATLAS 13AD: COMMUNICATION MEDIUM SEMANTICS & INTERFACE ISOLATION

**Document Identifier:** `ATLAS-DOC-13AD-STAGE-05`  
**Milestone:** 13AD — Mars Physics Reference Validation  
**Parent:** `ATLAS-13AC-PHYSICS-BOUNDARY`  
**Status:** Approved & Enforced  
**Date:** November 2026  

---

## 1. Executive Summary

Milestone 13AD establishes explicit, physics-based boundaries between communication transport media in Project Atlas. In previous implementations, collocated avionics subsystems (e.g. MastCam and Rover Central Compute, or Habitat Sensors and Core Bus) evaluated communication links using general link-budget methods, risking non-physical free-space approximations or synthetic 0-meter singularities.

This review formalizes the physical distinction between four discrete communication transport media:
1. `LOCAL_BUS`: Avionics digital backplanes (SpaceWire, MIL-STD-1553, CAN bus, Ethernet backplane) operating within a physical vehicle or habitat envelope.
2. `WIRED_CABLE`: Physical RF coaxial or optical fiber umbilicals between surface equipment, towers, and power stations.
3. `RF_WIRELESS`: Free-space spherical electromagnetic radiation across UHF (401.5 MHz), S-band (2.2 GHz), X-band (8.4 GHz), and Ka-band (32.0 GHz).
4. `OPTICAL_FREE_SPACE`: Free-space optical laser communications (1550 nm / 193.4 THz) utilizing directional telescopes and diffraction-limited apertures.

Furthermore, 13AD enforces **strict interface isolation** in the orbital contact planner: orbital contact passes cannot be satisfied or closed by local bus interfaces.

---

## 2. Taxonomy of Communication Media

```
                         Planetary Communications
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         │                                                     │
   Guided Channels                                    Radiated Channels
   (Bounded Waveguides)                               (Unbounded Free Space)
         │                                                     │
    ┌────┴────┐                                           ┌────┴────┐
    │         │                                           │         │
LOCAL_BUS  WIRED_CABLE                                RF_WIRELESS  OPTICAL_FREE_SPACE
(SpaceWire, (Coaxial,                                  (UHF, S,      (1550 nm DSOC,
 1553, CAN)  Fiber)                                     X, Ka)       Diffraction)
```

### 2.1 LOCAL_BUS
- **Physical Realm:** Intra-vehicle chassis, avionics racks, rover masts, habitat structures.
- **Physical Range:** $R = 0\text{ m}$ (model designation) or $R < 10\text{ m}$ (chassis bus harness).
- **Propagation Model:** Guided transmission line. Speed of light propagation delay is zero or negligible ($< 50\text{ ns}$).
- **Path Loss:** Free-Space Path Loss (FSPL) does not apply ($\text{FSPL} = 0.0\text{ dB}$). Signal attenuation is governed by bus transceivers, terminations, and digital error-checking.
- **Data Rates:** Governed by transceiver bus specifications (e.g. SpaceWire 200 Mbps to 1 Gbps, 1553 1 Mbps), not Friis carrier-to-noise ratio.
- **Operational Classification:** `COLLOCATED_LOCAL_INTERFACE` with validation status `VALID_LOCAL_DIRECT`.

### 2.2 WIRED_CABLE
- **Physical Realm:** Umbilicals between lander and rover, EVA tether data links, power mast hardlines.
- **Propagation Model:** Coaxial line ($Z_0 = 50\,\Omega$) or single-mode optical fiber ($1310/1550\text{ nm}$).
- **Path Loss:** Linear attenuation per unit length ($\alpha_{\text{cable}}\text{ dB/m}$), strictly independent of $4\pi R / \lambda$ spherical divergence.

### 2.3 RF_WIRELESS
- **Physical Realm:** Rover-to-orbiter proximity links, orbiter crosslinks, ground-to-satellite relays, Earth Deep Space Network (DSN).
- **Carrier Frequencies:** 401.5 MHz (UHF Proximity-1), 2.2 GHz (S-Band), 8.4 GHz (X-Band proximity/deep space), 32.0 GHz (Ka-Band deep space).
- **Propagation Model:** Spherical wave divergence $\text{FSPL} = 20\log_{10}(4\pi R f / c)$ in the Fraunhofer far-field region ($R \ge R_{\text{FF}}$).
- **Atmospheric Attenuation:** Governed strictly by Martian CO2 gas continuum absorption ($< 0.1\text{ dB}$) without optical dust contamination.

### 2.4 OPTICAL_FREE_SPACE
- **Physical Realm:** Deep Space Optical Communications (DSOC) between Mars orbiters/settlements and Earth/lunar optical ground stations.
- **Carrier Wavelength:** $1550\text{ nm}$ ($f \approx 193.4\text{ THz}$).
- **Propagation Model:** Narrow-beam diffraction disc ($J_1(u)/u$), sub-microradian pointing alignment.
- **Atmospheric Attenuation:** Governed by Beer-Lambert radiative transfer with Ångström spectral scaling ($\alpha_{\text{ang}} = 0.35$ relative to $880\text{ nm}$ MER reference record).

---

## 3. Interface Isolation in Orbital Contact Planning

A critical failure mode identified during assurance auditing was the theoretical risk of a collocated local bus or umbilical link falsely closing an orbital contact pass.

### 3.1 The Contamination Vulnerability
In a multi-node planetary simulation, if an asset (such as an orbital relay spacecraft) and a surface rover or lander share a synthetic coordinate or are evaluated with zero slant range:
- A generic link budget evaluation with $R = 0$ returns `is_link_closed = True` and data rate $= 1\text{ Gbps}$.
- If the orbital contact planner checks only `res.is_link_closed and res.operational_rate_bps > 0`, it would record an orbital pass closed by an internal bus!

### 3.2 Formal Architectural Isolation Rule
In `atlas_orbital_contact_planner.py` (Method `evaluate_node_pair_contact`):
```python
if (
    res.is_link_closed
    and res.is_physically_available
    and res.communication_medium in (CommunicationMedium.RF_WIRELESS, CommunicationMedium.OPTICAL_FREE_SPACE)
    and res.operational_rate_bps > best_rate
):
    best_rate = res.operational_rate_bps
    best_band = band
```
This guarantees that **only unguided over-the-air RF or optical channels can establish and sustain orbital contact windows**. Local bus connections and wired umbilicals cannot fulfill orbital contact passes.

---

## 4. API & Data Contract Metadata Schema

All `LinkBudgetResult` and API payload representations now surface explicit medium identification and provenance fields:

| Field Name | Type | Permitted Values | Definition |
| :--- | :--- | :--- | :--- |
| `communication_medium` | string | `LOCAL_BUS`, `WIRED_CABLE`, `RF_WIRELESS`, `OPTICAL_FREE_SPACE` | Physical propagation medium of the link. |
| `antenna_category` | string | `DIRECT_BUS_COUPLER`, `DIPOLE_OMNI`, `PATCH_MICROSTRIP`, `PARABOLIC_REFLECTOR`, `OPTICAL_TELESCOPE` | Structural antenna or interface category. |
| `field_region` | string | `COLLOCATED_INTERFACE`, `REACTIVE_NEAR_FIELD`, `RADIATING_NEAR_FIELD_FRESNEL`, `FRAUNHOFER_FAR_FIELD` | Field region classification at target range. |
| `pointing_model_tier` | string | `NOT_APPLICABLE`, `TIER_1_REFERENCE_MEASURED`, `TIER_2_ANALYTICAL_APPROXIMATION`, `TIER_3_OUT_OF_DOMAIN_GUARD` | Rigor tier of the pointing degradation model. |
| `pointing_guard_applied` | boolean | `true` / `false` | Explicit flag if computational tracking guard was invoked. |
| `spectral_optical_depth` | float/null | Real $\ge 0.0$ or `null` | Wavelength-scaled optical depth (for optical laser links). |

---

## 5. Verification Disposition

All communication medium boundaries have been integrated into `atlas_network_link_model.py` and `atlas_orbital_contact_planner.py`. Collocated nodes evaluate with zero unphysical path loss, and all orbital passes require valid radiated RF or optical channels.
