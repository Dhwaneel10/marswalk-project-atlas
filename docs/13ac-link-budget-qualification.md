# Milestone 13AC — Stage 3: Link Budget Semantic Qualification
## Boundary Classification, Typed Invariants, Collocated Interfaces & Physical Domain Contracts

**Document Designation:** `ATLAS-13AC-DOC-STAGE3-LINK-BUDGET`  
**Milestone:** 13AC — Physics Boundary Qualification  
**Module Audited:** `src/marswalk/core/atlas_network_link_model.py`  
**Status:** QUALIFIED & IMPLEMENTED  
**Date:** 2026-11-07  

---

## 1. Executive Summary & Semantic Principles

Milestone 13AC establishes a core epistemological standard for Project Atlas:
> **"A mathematically finite result is not necessarily physically meaningful. A numerically stable calculation is not necessarily a valid physical approximation. An API response that contains no NaN is not necessarily a correct engineering result."**

To ensure absolute engineering defensibility across all communication layers, the link budget evaluation engine (`PhysicalLinkBudgetEngine`) implements a strict, typed semantic hierarchy. Every calculation result unequivocally distinguishes between:
1. **Valid Physical Calculations:** Parameters within the analytical and empirical domain of the model.
2. **Invalid Physical Inputs:** Nonsensical values (negative distances, temperatures at or below absolute zero, non-positive carrier frequencies, negative optical depths) that are immediately rejected with `ValueError`.
3. **Out-of-Domain Scenarios:** Physically valid configurations that exceed the applicability boundaries of a specific mathematical model (e.g. near-field antenna distances evaluated with Friis far-field equations).
4. **Physically Unavailable Links:** Configurations where propagation is physically impossible (planetary body occultation, unpowered transceivers, elevation below operational terrain mask).
5. **Collocated Local Interfaces:** Nodes occupying the identical spatial coordinate ($R = 0$), where free-space electromagnetic propagation does not occur, but a physical wired/bus interface is established.

---

## 2. The Link Budget Semantic State Machine

```
                              [Input Parameters]
                                      |
         +----------------------------+----------------------------+
         | (NaN, Inf, R < 0, f <= 0, T <= 0, tau < 0)              | (Finite, Valid Physical Inputs)
         v                                                         v
  [RAISE ValueError]                                         Is R == 0.0?
  (Immediate Rejection)                                       /          \
                                                            YES           NO
                                                            /              \
           [COLLOCATED_LOCAL_INTERFACE] <------------------+                |
           - is_physically_available: True                                  v
           - validation_status: VALID_LOCAL_DIRECT                 Is Tx Power <= 0 W?
           - is_link_closed: True                                   /          \
           - propagation_delay_s: 0.0                             YES           NO
           - operational_rate: 1 Gbps (bus)                       /              \
                                          [UNPOWERED_TRANSMITTER] <+              v
                                          - is_physically_available: False      Is R < R_ff?
                                          - validation_status: UNAVAILABLE       /          \
                                          - is_link_closed: False              YES           NO
                                                                               /              \
                                                [NEAR_FIELD_OUT_OF_DOMAIN] <----+              v
                                                - is_physically_available: False       Is Elev <= 0.0°?
                                                - validation_status: OUT_OF_DOMAIN      /          \
                                                - is_link_closed: False               YES           NO
                                                                                      /              \
                                                  [OCCULTED_BELOW_HORIZON] <---------+                v
                                                  - is_physically_available: False       Is Elev < Elev_Mask?
                                                  - validation_status: UNAVAILABLE        /          \
                                                  - is_link_closed: False               YES           NO
                                                                                        /              \
                                                    [BELOW_ELEVATION_MASK] <-----------+                v
                                                    - is_physically_available: False      [FAR-FIELD EVALUATION]
                                                    - validation_status: UNAVAILABLE      - Friis Path Loss
                                                    - is_link_closed: False               - Rozenberg/Slab Loss
                                                                                          - Off-axis Pointing Loss
                                                                                          - Receiver N0 & Margin
                                                                                                    |
                                                                                  +-----------------+-----------------+
                                                                                  | R > 400e9 m                       | R <= 400e9 m
                                                                                  v                                   v
                                                                    [INTERPLANETARY_DEEP_SPACE]             [FAR_FIELD_FREE_SPACE]
                                                                    - validation_status: VALID              - validation_status: VALID
```

---

## 3. Structural Specification of `LinkBudgetResult`

To preserve 100% backward compatibility while delivering complete transparency, `LinkBudgetResult` incorporates 4 explicit semantic fields:

| Field | Type | Default | Permitted Values | Semantic Definition |
|:------|:-----|:--------|:-----------------|:--------------------|
| `is_physically_available` | `bool` | `True` | `True`, `False` | Whether a physical signal path exists and is capable of carrying power. |
| `operating_domain` | `str` | `"FAR_FIELD_FREE_SPACE"` | `"FAR_FIELD_FREE_SPACE"`, `"INTERPLANETARY_DEEP_SPACE"`, `"COLLOCATED_LOCAL_INTERFACE"`, `"NEAR_FIELD_OUT_OF_DOMAIN"`, `"OCCULTED_BELOW_HORIZON"`, `"BELOW_ELEVATION_MASK"`, `"UNPOWERED_TRANSMITTER"` | Identifies the physical and operational regime in which the calculation occurred. |
| `validation_status` | `str` | `"VALID"` | `"VALID"`, `"VALID_LOCAL_DIRECT"`, `"OUT_OF_DOMAIN"`, `"PHYSICALLY_UNAVAILABLE"` | Machine-readable qualification verdict of the link evaluation. |
| `evidence_class` | `str` | `"THEORETICAL_DERIVED"` | `"THEORETICAL_DERIVED"`, `"MEASURED_EMPIRICAL"`, `"SIMULATED_APPROXIMATION"` | Provenance classification distinguishing first-principles physics from empirical fits. |

All four fields are serialized in `LinkBudgetResult.to_dict()` for full inspection by API consumers, web dashboards, and DTN routing daemons.

---

## 4. Subsystem Physical Hardening

### 4.1 Collocated Local Interface ($R = 0$)
Collocated components (e.g. science instruments on a rover mast, co-sited habitats connected via fiber optic umbilical) do not radiate spherical EM waves through the Martian atmosphere.
- Path loss is set to $0.0\text{ dB}$.
- Propagation delay is $0.0\text{ s}$.
- Operating domain is set to `COLLOCATED_LOCAL_INTERFACE`.
- Validation status is `VALID_LOCAL_DIRECT`.
- Link is marked `is_link_closed = True`, providing high-bandwidth local serial communication (1 Gbps) without Friis singularity.

### 4.2 Fraunhofer Near-Field Boundary ($R < R_{\text{ff}}$)
For two antennas of effective aperture $D_{\text{tx}}$ and $D_{\text{rx}}$ at carrier frequency $f$:
$$R_{\text{ff}} = \max\left(\frac{2 D_{\text{max}}^2}{\lambda}, 2\lambda\right)$$
- If slant range $R < R_{\text{ff}}$, Friis spherical expansion is physically invalid.
- Link is marked `is_physically_available = False`, `is_link_closed = False`.
- Validation status is `OUT_OF_DOMAIN`.
- Downstream orbital planners and DTN routers are prohibited from opening transmission windows.

### 4.3 Off-Axis Pointing Loss & Tracking Failure
For directive antennas, pointing loss is quadratic with off-axis angle $\theta_{\text{err}}$ relative to the half-power beamwidth $\text{HPBW}$:
$$L_{\text{point}} = 12 \left(\frac{\theta_{\text{err}}}{\text{HPBW}}\right)^2\text{ dB}$$
- For $\theta_{\text{err}} \ge 2.5 \times \text{HPBW}$, the receiver has dropped into the sidelobe null structure or lost mechanical tracking entirely.
- Loss is capped at $40.0\text{ dB}$ (severe tracking loss), preventing unphysical infinite attenuation while ensuring link closure failure.

### 4.4 Thermal Noise Spectral Density ($N_0$) & Boltzmann Constant
Noise spectral density is defined by:
$$N_0 = k_B \times T_{\text{sys}} \implies N_{0,\text{dBW/Hz}} = 10\log_{10}(k_B \times T_{\text{sys}})$$
- $k_B = 1.380649\times 10^{-23}\text{ J/K}$ (exact SI definition).
- If $T_{\text{sys}} \le 0.0\text{ K}$, `ReceiverSpec` raises `ValueError` (third law of thermodynamics).

---

## 5. Verification Disposition

All 40 regression tests in the existing suites pass without warnings. The newly introduced semantic contract guarantees that physical boundary violations are caught either as immediate exceptions or as structured out-of-domain results, preventing any silent invalidation of mission telemetry.
