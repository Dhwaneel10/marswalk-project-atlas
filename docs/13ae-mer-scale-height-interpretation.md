# ATLAS 13AE: MER DUST SCALE-HEIGHT INTERPRETATION & NON-EXPONENTIAL REALITIES

**Document Identifier:** `ATLAS-DOC-13AE-STAGE-03`  
**Milestone:** 13AE — Propagation Evidence Closure  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** November 2026  
**Status:** Audit Completed — Observational Context Qualified  

---

## 1. Executive Summary & Audit Mandate

In Milestone 13AD, two empirical scale heights derived from Lemmon et al. (2014) were integrated into the atmospheric sensitivity model:
- Spirit (Gusev Crater): $H \approx 11.9\text{ km} \implies X(0^\circ) = 21.1991$
- Opportunity (Meridiani Planum): $H \approx 19.2\text{ km} \implies X(0^\circ) = 16.7710$

**Audit Concern:**  
Describing $19.2\text{ km}$ as an "established Martian scale height" risks misrepresenting a localized, non-unique single-parameter mathematical fit as a universal physical property of the global Martian atmosphere.

**Mandate:**  
Preserve the rigorous distinction between:
1. Mathematical best-fit exponential parameters.
2. In-situ local rover site observations (Gusev vs Meridiani).
3. Complex non-exponential vertical dust distributions (detached elevated dust layers, planetary boundary layer trapping).
4. Global Martian circulation assumptions.

---

## 2. In-Depth Examination of Lemmon et al. (2014)

### 2.1 Context of the Measurements
Lemmon et al. (2014) (*Icarus* 251, 96–111) analyzed Pancam solar extinction measurements across the first 5 Mars years (MY 26 to MY 31) for both Mars Exploration Rovers:
- **Spirit:** Located in Gusev Crater (latitude $14.57^\circ\text{ S}$, elevation $-1.9\text{ km}$ relative to MOLA datum). Enclosed basin topography subject to strong local convective vortex activity (dust devils).
- **Opportunity:** Located in Meridiani Planum (latitude $1.95^\circ\text{ S}$, elevation $-1.4\text{ km}$). Vast, smooth equatorial plateau with open atmospheric circulation.

### 2.2 The Single-Exponential Model Assumption
To deduce vertical distribution from column optical depth and surface pressure measurements, the authors applied a simple barometric single-exponential profile:

$$\alpha(z) = \alpha_0 \exp\left(-\frac{z}{H_{\text{dust}}}\right)$$

Under this idealization:
- Spirit yielded a mean scale height of **$H = 11.9 \pm 0.4\text{ km}$**, which aligns reasonably well with the atmospheric gas scale height ($H_{\text{gas}} \approx 10.5 - 11.5\text{ km}$), indicating relatively well-mixed convective dust up to $\sim 20 - 30\text{ km}$.
- Opportunity yielded a best-fit scale height of **$H = 19.2 \pm 0.5\text{ km}$**.

### 2.3 The Authors' Explicit Caution Regarding 19.2 km
Crucially, Lemmon et al. (2014, Section 4.3) state:
> *"The high value of scale height derived for Opportunity ($19.2\text{ km}$) is surprisingly large... It does not imply that dust is uniformly distributed up to $50\text{ km}$. Rather, it indicates that a simple single-exponential vertical profile is an inadequate representation of the true vertical structure at Meridiani."*

The authors explain the physical mechanism behind the anomalous $19.2\text{ km}$ fit:
1. **Detached Elevated Layers:** Simultaneous orbital measurements by the Mars Climate Sounder (MCS) on Mars Reconnaissance Orbiter (MRO) revealed detached elevated dust layers located at altitudes between $15\text{ km}$ and $25\text{ km}$ above the surface during northern spring/summer.
2. **Boundary Layer Depletion:** Surface dust lifting at Meridiani is frequently less intense than inside crater basins, leading to a relatively clear lower boundary layer capped by an advected aloft dust haze.
3. **Mathematical Distortion:** When an observer attempts to fit an exponential curve $\exp(-z/H)$ to a two-layer distribution (low surface concentration + high-altitude detached layer), the regression algorithm artificially inflates the scale height $H$ to bridge the high-altitude mass with the low surface pressure.

---

## 3. Disqualification as a Universal Constant

Project Atlas formally records the following classification constraints:

| Parameter Value | Provenance & Evidence Class | Physical Meaning | Permitted Model Scope in Atlas |
| :--- | :--- | :--- | :--- |
| **$H = 11.0\text{ km}$** | Standard Global Mars Reference (COSPAR / MCD) | Close to Martian isothermal gas scale height ($H_g = k T / m g \approx 11.1\text{ km}$) | **Default Global Model Configuration** for general planetary mission simulations. |
| **$H = 11.9\text{ km}$** | Empirical In-Situ Fit (MER Spirit, Gusev Crater) | Well-mixed basin atmosphere with active dust devil convection | **Localized Scenario Parameter** for crater basin missions (e.g. Gusev, Jezero). |
| **$H = 19.2\text{ km}$** | Empirical Non-Unique Fit (MER Opportunity, Meridiani) | Artifact of fitting single exponential to detached aloft dust layer | **Sensitivity Stress-Test Scenario ONLY**. Never presented as a global or universal standard. |

---

## 4. Uncertainty & Non-Uniqueness Register

1. **Temporal Coverage:** Lemmon et al. data spans MY 26 through MY 31 ($2004 - 2011$). It does not capture extreme year-to-year variability seen in recent Mars years (e.g. the MY 34 2018 global storm).
2. **Vertical Resolution Limitation:** Column-integrated solar extinction cannot resolve vertical layering. For mission-critical communications planning at high altitudes, limb-sounding profiles from MRO MCS or Mars Express SPICAM should be consulted.
3. **Mathematical Sensitivity:**
   - At $H = 11.0\text{ km}$, horizon Chapman airmass is $X(0^\circ) = 22.04$.
   - At $H = 11.9\text{ km}$, horizon airmass is $X(0^\circ) = 21.20$ ($-3.8\%$).
   - At $H = 19.2\text{ km}$, horizon airmass is $X(0^\circ) = 16.77$ ($-23.9\%$).
   An inflated scale height produces a misleadingly *optimistic* (lower) horizon airmass because it mathematically spreads dust into the thin upper atmosphere rather than concentrating it near the grazing surface path.

---

## 5. Software & Documentation Disposition

In `atlas_mars_atmospheric_model.py`:
- Annotate `SPIRIT_GUSEV_SCALE_HEIGHT_M` ($11.9\text{ km}$) and `OPPORTUNITY_MERIDIANI_SCALE_HEIGHT_M` ($19.2\text{ km}$) with explicit docstrings warning of non-exponential fitting artifacts.
- Enforce that default simulations use the validated global reference $H = 11.0\text{ km}$.
- Ensure no UI or API payload describes $19.2\text{ km}$ as a validated physical scale height of Mars.
