# Milestone 13AC — Stage 7: Physical Model Validity Register
## Comprehensive Catalog of Simulation Models, Validity Domains, Failure Modes & Scientific Provenance

**Document Designation:** `ATLAS-13AC-DOC-STAGE7-VALIDITY-REGISTER`  
**Milestone:** 13AC — Physics Boundary Qualification  
**Scope:** Complete Project Atlas Simulation Ecosystem (13A–13AC)  
**Status:** QUALIFIED & CODIFIED  
**Date:** 2026-11-07  

---

## 1. Register Overview

This register formally defines the mathematical equations, input physical units, valid operating regimes, boundary behaviors, failure modes, and authoritative citations for every primary physical model in Project Atlas. It serves as the definitive engineering reference for all simulations, preventing domain over-extension and unphysical extrapolations.

---

## 2. Comprehensive Model Registry

### 2.1 Free-Space Path Loss (Friis Spherical Expansion)
- **Governing Equation:**
  $$\text{FSPL} = 20\log_{10}\left(\frac{4\pi R f}{c}\right) = 20\log_{10}\left(\frac{4\pi R}{\lambda}\right)\text{ dB}$$
- **Input Parameters & Units:**
  - Slant range $R$ (meters, m)
  - Carrier frequency $f$ (Hertz, Hz)
  - Speed of light $c \approx 299,792,458\text{ m/s}$
- **Valid Input Domain:**
  - $R \ge R_{\text{ff}} = \max\left(\frac{2 D_{\text{max}}^2}{\lambda}, 2\lambda\right)$ (Fraunhofer far-field regime)
  - $f > 0\text{ Hz}$
- **Boundary Behavior:**
  - At $R = 0$: Collocated wired/bus direct interface (`COLLOCATED_LOCAL_INTERFACE`, 0 dB loss, 0 s delay).
  - For $0 < R < R_{\text{ff}}$: Near-field regime (`NEAR_FIELD_OUT_OF_DOMAIN`, `is_link_closed = False`).
- **Failure Mode / Rejection:**
  - $R < 0$: Raises `ValueError`.
  - $R < \frac{\lambda}{4\pi}$: Raises `ValueError` (prevents passive energy gain).
  - $f \le 0$ or NaN/Inf: Raises `ValueError`.
- **Known Approximations:** Assumes isotropic spherical wave expansion in homogeneous lossless dielectric; does not model ground reflection multipath or diffraction.
- **Reference / Citation:** Friis, H. T. (1946). *A Note on a Simple Transmission Formula*, Proc. IRE, 34(5), 254–256. IEEE Standard 145-2013 (Definitions of Terms for Antennas).

---

### 2.2 Atmospheric Attenuation & Extinction (Beer-Lambert & Chapman Airmass)
- **Governing Equation:**
  $$A_{\text{atm}} = 4.3429448 \times \tau \times X(\theta)\text{ dB (Optical)}, \quad A_{\text{atm}} = 0.05 \times X(\theta)\text{ dB (RF UHF)}$$
  $$X(\theta) = \frac{1}{\sin\theta + 0.025 \exp(-11.0 \sin\theta)}\text{ for } 0^\circ < \theta < 5^\circ, \quad X(\theta) = \frac{1}{\sin\theta}\text{ for } \theta \ge 5^\circ$$
- **Input Parameters & Units:**
  - Geometric elevation $\theta$ (degrees, ${}^\circ$)
  - Atmospheric optical depth $\tau$ (dimensionless, dust tau)
  - Communication band enum (`CommunicationBand`)
- **Valid Input Domain:**
  - Elevation $\theta > 0.0^\circ$ (above local tangent horizon)
  - Dust optical depth $\tau \ge 0.0$ (typically $0.2 \le \tau \le 5.0$ on Mars)
- **Boundary Behavior:**
  - For $0.0^\circ < \theta < 5.0^\circ$: Spherical-shell Chapman airmass smoothly transitions without $1/\sin\theta$ divergence.
  - Zenith $\theta = 90.0^\circ$: Minimum airmass $X = 1.000$.
- **Failure Mode / Rejection:**
  - $\theta \le 0.0^\circ$: Raises `ValueError` in direct calculation; classified as `OCCULTED_BELOW_HORIZON` (`is_physically_available = False`) in `evaluate_link`.
  - $\tau < 0.0$: Raises `ValueError`.
- **Known Approximations:** Assumes vertically homogeneous dust exponential scale height ($H \approx 11.1\text{ km}$); neglects horizontal localized dust gradients and molecular gas line absorption.
- **Reference / Citation:** Rozenberg, G. V. (1966). *Twilight: A Study in Atmospheric Optics*, Plenum Press. Smith, M. D. (2004). *Interannual variability in TES mapping of Mars dust and water ice*, Icarus, 167(1), 148–165.

---

### 2.3 Off-Axis Antenna Pointing Loss
- **Governing Equation:**
  $$L_{\text{point}} = 12.0 \left(\frac{\theta_{\text{err}}}{\text{HPBW}}\right)^2\text{ dB}, \quad \text{HPBW} \approx \frac{70.0^\circ}{\sqrt{\max(1.0, 10^{(G_{\text{dBi}}-15)/10})}}$$
- **Input Parameters & Units:**
  - Pointing alignment error $\theta_{\text{err}}$ (degrees, ${}^\circ$)
  - Antenna boresight gain $G_{\text{dBi}}$ (decibels isotropic, dBi)
  - Carrier frequency $f$ (Hertz, Hz)
- **Valid Input Domain:**
  - $\theta_{\text{err}} \ge 0.0^\circ$
  - $G_{\text{dBi}}$ finite real number
- **Boundary Behavior:**
  - For $\theta_{\text{err}} \le 0.0^\circ$ or $G_{\text{dBi}} \le 3.0\text{ dBi}$: Minimal nominal pointing loss $0.1\text{ dB}$.
  - For $\theta_{\text{err}} \ge 2.5 \times \text{HPBW}$: Capped at $40.0\text{ dB}$ (sidelobe null / complete tracking failure).
- **Failure Mode / Rejection:** NaN/Inf values raise `ValueError`.
- **Known Approximations:** Gaussian main-beam approximation; ignores deep sidelobe diffraction rings.
- **Reference / Citation:** Balanis, C. A. (2016). *Antenna Theory: Analysis and Design*, 4th ed., Wiley. ITU-R Recommendation S.580-6.

---

### 2.4 Receiver Noise Spectral Density ($N_0$)
- **Governing Equation:**
  $$N_0 = k_B \times T_{\text{sys}}\text{ (W/Hz)}, \quad N_{0,\text{dBW/Hz}} = 10\log_{10}(k_B \times T_{\text{sys}})$$
- **Input Parameters & Units:**
  - System noise temperature $T_{\text{sys}}$ (Kelvin, K)
  - Boltzmann constant $k_B = 1.380649\times 10^{-23}\text{ J/K}$ (exact SI 2019)
- **Valid Input Domain:**
  - $T_{\text{sys}} > 0.0\text{ K}$ (Third Law of Thermodynamics; absolute zero strictly prohibited)
- **Boundary Behavior:**
  - Deep space cryogenic receiver ($T_{\text{sys}} \approx 20\text{ K} \implies N_0 \approx -215.6\text{ dBW/Hz}$).
  - Surface UHF receiver ($T_{\text{sys}} \approx 250\text{ K} \implies N_0 \approx -204.6\text{ dBW/Hz}$).
- **Failure Mode / Rejection:** $T_{\text{sys}} \le 0.0\text{ K}$ raises `ValueError`.
- **Known Approximations:** Assumes white thermal Johnson-Nyquist noise over the receiver operating channel.
- **Reference / Citation:** Nyquist, H. (1928). *Thermal Agitation of Electric Charge in Conductors*, Physical Review, 32(1), 110–113. BIPM (2019) SI Brochure, 9th edition.

---

### 2.5 Orbital Elevation & Central Body Line-of-Sight Occultation
- **Governing Equation:**
  $$\sin\theta = \frac{(\vec{p}_{\text{target}} - \vec{p}_{\text{surf}}) \cdot \hat{u}_{\text{up}}}{\|\vec{p}_{\text{target}} - \vec{p}_{\text{surf}}\|}$$
  $$\text{Ray Occultation: } \vec{r}(t) = \vec{p}_1 + t(\vec{p}_2 - \vec{p}_1), \quad t^* = -\frac{\vec{p}_1 \cdot (\vec{p}_2 - \vec{p}_1)}{\|\vec{p}_2 - \vec{p}_1\|^2}, \quad d_{\text{min}} = \|\vec{r}(t^*)\|$$
- **Input Parameters & Units:**
  - Asset positions $\vec{p}_1, \vec{p}_2$ in Mars-Centered Mars-Fixed (MCMF) Cartesian frame (meters, m)
  - Mars physical radius $R_M = 3,389,500.0\text{ m}$
  - Atmospheric mask radius $R_{\text{mask}} = R_M + 50,000.0\text{ m}$
- **Valid Input Domain:** Positions in $\mathbb{R}^3$, $\|\vec{p}\| \ge R_M$.
- **Boundary Behavior:**
  - Zenith $\theta = 90.0^\circ$: Direct overhead line of sight.
  - Nadir $\theta = -90.0^\circ$: $d_{\text{min}} = 0 < R_{\text{mask}}$, tagged as body-occulted.
  - Grazing contact $d_{\text{min}} = R_{\text{mask}}$: Tangent graze.
- **Failure Mode / Rejection:** Identical coordinates ($R = 0$) handled as collocated local nodes.
- **Known Approximations:** Spherical Mars reference figure; does not model localized ellipsoidal oblateness ($J_2$) or high-order gravity harmonics in geometric LOS.
- **Reference / Citation:** Vallado, D. A. (2013). *Fundamentals of Astrodynamics and Applications*, 4th ed., Microcosm Press. IAU 2000 Mars Cartographic Constants.

---

### 2.6 Terrain Slope Gradient (Horn 1981)
- **Governing Equation:**
  $$\frac{\partial z}{\partial x} = \frac{(z_{13} + 2z_{23} + z_{33}) - (z_{11} + 2z_{21} + z_{31})}{8 \times \Delta x}, \quad \frac{\partial z}{\partial y} = \frac{(z_{11} + 2z_{12} + z_{13}) - (z_{31} + 2z_{32} + z_{33})}{8 \times \Delta y}$$
  $$\theta_{\text{slope}} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \times \frac{180}{\pi}$$
- **Input Parameters & Units:**
  - 2D Elevation grid $z$ (meters, m)
  - East-West spacing $\Delta x$ (meters, m)
  - North-South spacing $\Delta y$ (meters, m)
- **Valid Input Domain:** $\Delta x > 0.0\text{ m}$, $\Delta y > 0.0\text{ m}$.
- **Boundary Behavior:**
  - Flat terrain: $\frac{\partial z}{\partial x} = 0, \frac{\partial z}{\partial y} = 0 \implies \theta_{\text{slope}} = 0.0^\circ$.
  - Vertical cliff: $\lim_{\Delta z \to \infty} \arctan = 90.0^\circ$ (mathematically bounded).
- **Failure Mode / Rejection:** $\Delta x \le 0$ or $\Delta y \le 0$ raises `ValueError`. Boundary cells with incomplete $3\times 3$ window masked to NaN.
- **Known Approximations:** Assumes local bilinear surface patch; sensitivity depends on DEM raster resolution (HiRISE 1 m vs HRSC 20 m).
- **Reference / Citation:** Horn, B. K. P. (1981). *Hill Shading and the Reflectance Map*, Proceedings of the IEEE, 69(1), 14–47.

---

### 2.7 Terrain Roughness (Standard Deviation of Detrended Residuals)
- **Governing Equation:**
  $$\xi_{\text{rough}} = \sqrt{\frac{1}{N-1} \sum_{i=1}^N (z_i - \bar{z}_{\text{trend}})^2}$$
- **Input Parameters & Units:**
  - Elevation matrix window $z$ (meters, m)
  - Kernel size $k \in \{3, 5, 7\}$
- **Valid Input Domain:** $N \ge 3$.
- **Boundary Behavior:** Perfectly smooth horizontal plane yields $\xi_{\text{rough}} = 0.0\text{ m}$.
- **Failure Mode / Rejection:** Non-positive kernel size raises `ValueError`.
- **Known Approximations:** Does not resolve sub-pixel boulder distributions beneath DEM grid resolution.
- **Reference / Citation:** Shepard, M. K., et al. (2001). *The roughness of natural terrain: A planetary perspective*, JGR: Planets, 106(E12), 32777–32795.

---

### 2.8 Rover Terramechanics & Energy Consumption (Bekker-Wong Heuristic)
- **Governing Equation:**
  $$P_{\text{wheel}} = \left(m \cdot g_M \cdot c_{rr} \cdot \cos\theta_{\text{slope}} + m \cdot g_M \cdot \sin\theta_{\text{slope}}\right) \times v + P_{\text{hotel}}$$
- **Input Parameters & Units:**
  - Rover mass $m$ (kilograms, kg)
  - Mars surface gravity $g_M = 3.72076\text{ m/s}^2$
  - Rolling resistance coefficient $c_{rr}$ (dimensionless, $0.05 \le c_{rr} \le 0.25$)
  - Slope angle $\theta_{\text{slope}}$ (degrees, ${}^\circ$)
  - Forward velocity $v$ (meters/second, m/s)
  - Hotel baseline electrical draw $P_{\text{hotel}}$ (Watts, W)
- **Valid Input Domain:** $m > 0\text{ kg}$, $v \ge 0\text{ m/s}$, $-90^\circ < \theta_{\text{slope}} < 90^\circ$.
- **Boundary Behavior:**
  - Zero velocity ($v = 0$): Consumes baseline hotel load $P_{\text{hotel}}$.
  - Steep slope downhill ($\theta < 0$): Gravity assist capped to prevent negative regenerative power claims on passive skid-steer rovers.
- **Failure Mode / Rejection:** Slope exceeding vehicle tip-over threshold ($\theta > 30^\circ$) triggers traversability impassability (`COST = inf`).
- **Known Approximations:** Steady-state rolling resistance; neglects transient slip-sinkage sinkhole dynamics.
- **Reference / Citation:** Bekker, M. G. (1969). *Introduction to Terrain-Vehicle Systems*, Univ. of Michigan Press. Wong, J. Y. (2008). *Theory of Ground Vehicles*, 4th ed., Wiley.

---

### 2.9 Aerial Flight Dynamics (Rotorcraft Momentum Theory)
- **Governing Equation:**
  $$T = 2 \rho A v_i^2, \quad P_{\text{induced}} = \frac{T^{3/2}}{\sqrt{2 \rho A}}, \quad P_{\text{profile}} = \frac{\rho A (\Omega R)^3 \sigma c_{d0}}{8}, \quad P_{\text{total}} = \frac{P_{\text{induced}}}{\eta_{\text{rotor}}} + P_{\text{profile}} + P_{\text{avionics}}$$
- **Input Parameters & Units:**
  - Mars atmospheric density $\rho$ (kilograms/cubic meter, $\text{kg/m}^3$, $\sim 0.015\text{ kg/m}^3$)
  - Rotor disc area $A$ (square meters, $\text{m}^2$)
  - Total hover thrust $T = m \cdot g_M$ (Newtons, N)
  - Rotor tip speed $\Omega R$ (meters/second, m/s, bounded by speed of sound $a \approx 240\text{ m/s}$)
- **Valid Input Domain:** $\rho > 0.005\text{ kg/m}^3$, $m > 0\text{ kg}$, tip Mach $M_{\text{tip}} < 0.85$.
- **Boundary Behavior:** Hover ceiling reached when required hover power exceeds maximum battery pack discharge rate.
- **Failure Mode / Rejection:** Atmospheric density $\rho \le 0$ raises `ValueError`.
- **Known Approximations:** Actuator disc momentum theory with empirical profile drag correction; assumes steady-state hover/cruise without localized rotor-ground vortex interactions.
- **Reference / Citation:** Leishman, J. G. (2006). *Principles of Helicopter Aerodynamics*, Cambridge Univ. Press. Balaram, J., et al. (2018). *Mars Helicopter Technology Demonstrator*, AIAA Atmospheric Flight Mechanics Conference.

---

### 2.10 ISRU Manufacturing Mass-Energy Balance
- **Governing Equation:**
  $$M_{\text{input}} \equiv M_{\text{usable}} + M_{\text{waste}}, \quad E_{\text{consumed}} = M_{\text{input}} \times e_{\text{spec}}\text{ (kWh)}$$
  $$M_{\text{usable}} = \text{round}(M_{\text{input}} \times \eta_{\text{yield}}, 4), \quad M_{\text{waste}} = \text{round}(M_{\text{input}} - M_{\text{usable}}, 4)$$
- **Input Parameters & Units:**
  - Input feedstock mass $M_{\text{input}}$ (kilograms, kg)
  - Specific processing energy $e_{\text{spec}}$ (kilowatt-hours per kilogram, kWh/kg)
  - Process yield efficiency $\eta_{\text{yield}}$ (dimensionless, $0 < \eta_{\text{yield}} \le 1.0$)
- **Valid Input Domain:** $M_{\text{input}} > 0\text{ kg}$, $0 < \eta_{\text{yield}} \le 1.0$, $e_{\text{spec}} > 0\text{ kWh/kg}$.
- **Boundary Behavior:** At 100% yield ($\eta = 1.0$), waste is exactly $0.0\text{ kg}$.
- **Failure Mode / Rejection:** $M_{\text{input}} \le 0\text{ kg}$ strictly raises `ValueError` (prevents negative excavation or spurious energy production).
- **Known Approximations:** Lumped-parameter thermodynamic efficiency; assumes constant specific energy per processing batch.
- **Reference / Citation:** Sanders, G. B., & Larson, W. E. (2013). *Integration of In-Situ Resource Utilization into lunar/Mars exploration*, Advances in Space Research, 51(12), 2249–2267.
