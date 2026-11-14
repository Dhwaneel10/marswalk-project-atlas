# PROJECT ATLAS — RESEARCH RELEASE 2.0
# EXTERNAL SCIENTIFIC CHALLENGE QUESTIONNAIRE
## 36 Falsifiable Inquiries Across Planetary Physics, RF Engineering, and Computational Verification

**Document Designation:** `ATLAS-EXTERNAL-CHALLENGE-QUESTIONS-2.0`  
**Milestone:** `13AG`  
**Parent:** `13AF`  
**Date:** 2026-11-07  
**System:** Project Atlas / MarsWalk 2.0  

---

## Instructions for External Reviewers

This questionnaire is designed to invite **rigorous scientific challenge, critical scrutiny, and falsification**. Reviewers are explicitly urged **not** to accept Atlas models at face value. 

If any equation, assumption, boundary guard, or default value in Project Atlas is physically invalid, ungrounded, or mathematically fragile, please submit your findings using the structure in [`REVIEW_RESPONSE_REGISTER.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/research/Atlas_Research_Release_2.0/REVIEW_RESPONSE_REGISTER.md).

---

## Track A: Planetary Atmosphere & Optical Propagation (Questions 1–12)

### Q-ATM-01: Extrapolation of 1550 nm from Pancam Wavelengths
*Primary Code:* `atlas_mars_atmospheric_model.py:calculate_optical_attenuation_db`  
**Question:** Given that the Ångström exponent $\alpha = -0.082$ was derived from MER Pancam observations spanning only $440\text{ nm}$ to $880\text{ nm}$, what physical evidence justifies extrapolating this power-law out to the telecom laser wavelength of $1550\text{ nm}$? Does anomalous diffraction or changing imaginary index of refraction (e.g. silicate/hematite absorption features in the near-IR) invalidate power-law scaling between 880 nm and 1550 nm?

### Q-ATM-02: Top-Heavy and Detached Aloft Dust Layers
*Primary Code:* `atlas_mars_atmospheric_model.py:spherical_airmass`  
**Question:** Atlas assumes an exponential dust vertical profile $\exp(-z / H_{\text{dust}})$. MRO Mars Climate Sounder (MCS) observations frequently reveal detached, elevated dust layers at 25–40 km altitude during global dust storms. Does an exponential model systematically underestimate slant-path optical depth for low-elevation grazing rays passing through elevated detached layers?

### Q-ATM-03: Spatial Representativeness of MER Opportunity Scale Heights
*Primary Code:* `data/parameter_provenance_registry.json:dust_scale_height_typical_km`  
**Question:** The $H_{\text{dust}} = 10.0\text{ km}$ baseline is derived from equatorial MER Opportunity observations in Meridiani Planum. Is this scale height valid for high-latitude settlements (e.g. Arcadia Planitia or Deuteronilus Mensae) where the polar vortex and seasonal CO2 condensation compress the vertical aerosol profile?

### Q-ATM-04: Numerical Stability of Spherical Slant-Path Integration near Horizon
*Primary Code:* `atlas_mars_atmospheric_model.py:calculate_spherical_path_integral`  
**Question:** At grazing elevation angles ($0^\circ \le \theta \le 2^\circ$), does the Simpson/trapezoidal integration of the spherical shell curvature introduce numerical truncation error or artificial divergence compared to Chapman function analytical asymptotics?

### Q-ATM-05: Non-Uniqueness of Inverted Vertical Dust Profiles
*Primary Code:* `docs/13af-mer-scale-height-provenance.md`  
**Question:** Column optical depth $\tau$ is a line-of-sight path integral $\int \sigma_{\text{ext}} n(z) dz$. Since an infinite family of distinct vertical profiles can yield the exact same zenith optical depth, what is the maximum error in slant-path attenuation at $5^\circ$ elevation caused by profile non-uniqueness?

### Q-ATM-06: Decoupling of Mineral Dust from Water-Ice Clouds
*Primary Code:* `atlas_mars_atmospheric_model.py`  
**Question:** Atlas models atmospheric extinction solely via mineral dust and gaseous CO2 absorption. During northern hemisphere spring/summer, the aphelion cloud belt introduces substantial water-ice cloud opacity ($\tau_{\text{ice}} \approx 0.1 - 0.3$). Does the omission of ice clouds create an optimistic bias in optical link availability?

### Q-ATM-07: Daytime Atmospheric Optical Turbulence and Beam Scintillation
*Primary Code:* `atlas_network_link_model.py`  
**Question:** Strong surface thermal gradients on Mars generate intense refractive index structure constant values ($C_n^2 \sim 10^{-13} - 10^{-12}\text{ m}^{-2/3}$) in the lowest 100 meters of the boundary layer. Does the absence of an atmospheric turbulence / beam-wander model invalidate the optical link margin for surface-to-surface or surface-to-air links?

### Q-ATM-08: Forward Scattering Phase Function and Receiver Field of View
*Primary Code:* `benchmark_optical_dust.py`  
**Question:** Martian dust particles have large asymmetry parameters ($g \approx 0.65 - 0.75$), resulting in strong forward scattering. Does simple Beer-Lambert direct-beam extinction overestimate total optical attenuation for ground receivers with wide field-of-view collectors that capture forward-scattered photons?

### Q-ATM-09: Validity of the Unmodified Gaseous CO2 Absorption Model
*Primary Code:* `atlas_mars_atmospheric_model.py:calculate_co2_absorption_db`  
**Question:** Is the molecular CO2 absorption model at 1550 nm parameterized with realistic pressure-broadened line-mixing coefficients for low-pressure ($6\text{ mbar}$) pure CO2 Martian conditions, or does it apply terrestrial air-broadened approximations?

### Q-ATM-10: Diurnal and Seasonal Dynamic Range of Column Opacity
*Primary Code:* `data/optical_angstrom_sensitivity_table.csv`  
**Question:** Does the 5-regime sensitivity table sufficiently span the full dynamic range between ultra-clear Martian conditions ($\tau < 0.1$) and major planet-encircling dust storms ($\tau > 4.0$), or does the simulator suffer from clipping at extreme opacities?

### Q-ATM-11: Terrain Horizon Masking vs Atmospheric Refraction
*Primary Code:* `terrain_visibility.py`  
**Question:** At near-zero elevations, does Martian atmospheric refraction significantly bend optical and RF rays downward, extending the radio horizon beyond the purely geometric line-of-sight modeled in `terrain_visibility.py`?

### Q-ATM-12: Dust Deposition on Optical Terminal Apertures
*Primary Code:* `atlas_network_link_model.py`  
**Question:** Even if the atmospheric column remains moderately transmissive, dust settling on horizontal optical window surfaces degrades throughput by $0.2 - 0.5\%\text{ per sol}$. How should operational models account for terminal window fouling versus atmospheric extinction?

---

## Track B: RF & Space Communications Engineering (Questions 13–24)

### Q-RF-01: Validity of Dry Basalt Dielectric Analogs
*Primary Code:* `data/parameter_provenance_registry.json:rf_dust_relative_permittivity_real`  
**Question:** Atlas adopts $\epsilon_r = 2.80 - j 0.0420$ based on terrestrial volcanic basalt and Apollo lunar regolith. Given that Martian dust contains significant iron oxides (hematite, magnetite, ferric clays), could magnetic permeability ($\mu_r \ne 1.0$) or higher conductivity substantially increase microwave absorption beyond dielectric predictions?

### Q-RF-02: Mie Scattering Corrections at 32 GHz for Coarse Particles
*Primary Code:* `benchmarks/benchmark_rf_dust.py`  
**Question:** Atlas demonstrates that $x = 2 \pi r / \lambda \le 0.0134 \ll 1$ for $r \le 20\,\mu\text{m}$ at 32 GHz. However, during saltation and initial storm lofting, dust grains up to $50 - 100\,\mu\text{m}$ can be momentarily suspended in the lowest boundary layer. At what particle radius and frequency does the Rayleigh absorption assumption fail by more than $5\%$ relative to full Mie scattering?

### Q-RF-03: Goldhirsh vs Ho & Golshan Mass-Normalization Rigor
*Primary Code:* `EVIDENCE_RECONCILIATION.md:Section 4`  
**Question:** Is the proof that Goldhirsh and Ho & Golshan agree when normalized by column mass loading $\mathcal{M}$ physically robust, or does it obscure differences in assumed particle density $\rho_{\text{grain}}$ and loss tangent $\tan\delta$ between the two studies?

### Q-RF-04: Far-Field Fraunhofer Distance for Large Surface Reflectors
*Primary Code:* `atlas_antenna_model.py:calculate_field_regions`  
**Question:** For a 5-meter Ka-band ground station reflector at 32 GHz, the Fraunhofer distance is $R_{\text{ff}} = 2 D^2 / \lambda = 5,333\text{ meters}$. Does Atlas's rejection of links inside $R_{\text{ff}}$ create false communication outages for low-altitude rovers or aerial drones operating within 5 km of a settlement?

### Q-RF-05: Real Antenna Blockage and Sidelobe Envelopes vs Bessel Airy Patterns
*Primary Code:* `atlas_antenna_model.py:calculate_gain_pattern_dbi`  
**Question:** Real space communications reflector antennas experience subreflector and strut blockage that fills in diffraction nulls and raises wide-angle sidelobes (e.g. ITU-R S.580). Is using an ideal Bessel $J_1(u)/u$ Airy pattern too optimistic regarding null depth and interference rejection?

### Q-RF-06: Planck vs Rayleigh-Jeans CMB Equivalent Brightness Convention
*Primary Code:* `benchmarks/benchmark_receiver_noise.py`  
**Question:** At 32 GHz, $T_{\text{RJ}} = 2.029\text{ K}$, departing by $-0.70\text{ K}$ ($-25.54\%$) from thermodynamic $2.725\text{ K}$. Is enforcing a flat $2.7\text{ K}$ floor in Atlas an acceptable conservative engineering shortcut, or should the software strictly use the frequency-dependent Planck equivalent?

### Q-RF-07: Reference Plane Consistency in Cascaded Receiver Noise
*Primary Code:* `atlas_network_link_model.py:calculate_receiver_noise_figure`  
**Question:** Does the mathematical proof of invariance between Plane A (antenna terminals) and Plane B (LNA input) hold under all impedance mismatch conditions, or does it assume an idealized matched transmission line?

### Q-RF-08: Low-Elevation Tropospheric Phase and Amplitude Scintillation
*Primary Code:* `atlas_network_link_model.py`  
**Question:** At low elevation angles ($\theta < 10^\circ$), atmospheric temperature and pressure fluctuations cause RF phase scintillation and fading. Does Atlas's omission of a scintillation fading variance model compromise link availability predictions?

### Q-RF-09: Surface Multipath Reflections for Rover UHF Links
*Primary Code:* `atlas_network_link_model.py`  
**Question:** For low-mounted rover antennas, ground reflections create a 2-ray multipath interference pattern with severe periodic fading nulls. Does Atlas's free-space path loss model overestimate the link margin of rover proximity communications?

### Q-RF-10: Cross-Polarization Discrimination in Severe Dust Storms
*Primary Code:* `atlas_network_link_model.py`  
**Question:** Suspended non-spherical Martian dust particles aligned by atmospheric electric fields can cause cross-polarization discrimination (XPD) degradation. Does Atlas account for polarization tilt or depolarization losses during dust storms?

### Q-RF-11: Truth Demarcation between Propagation Loss and Operational Closure
*Primary Code:* `benchmarks/benchmark_link_budget_scenarios.py:Scenario 3`  
**Question:** Scenario 3 shows a link failing despite negligible dust loss ($0.009\text{ dB}$). Does Atlas's link budget engine correctly and consistently prioritize net link margin over raw atmospheric transmissivity in all scheduling decisions?

### Q-RF-12: Battery and Thermal Constraints on Transmitter Duty Cycle
*Primary Code:* `atlas_orbital_contact_planner.py`  
**Question:** High-power RF transmitters (e.g. 20–50 W TWTA) generate significant waste heat and power drain. Does the contact planner verify spacecraft power and thermal dissipation limits before scheduling full-duration high-rate contact passes?

---

## Track C: Software Verification & Scientific Computing (Questions 25–36)

### Q-SW-01: True Software Independence of Benchmark Harness
*Primary Code:* `research/Atlas_Research_Release_2.0/benchmarks/`  
**Question:** Are the scripts in `benchmarks/` genuinely independent reference implementations, or do they share hidden mathematical structures, constants, or approximations with the production code in `src/marswalk/core/`?

### Q-SW-02: Automated Mutation Testing Scope and Killing Power
*Primary Code:* `scratch/run_13af_mutations.py`  
**Question:** While the 8 tested mutations were all killed (100% score), were these mutations chosen specifically because tests already existed to catch them? How would the suite perform against automated high-order AST mutation frameworks (e.g. `mutmut`) applied broadly across the entire codebase?

### Q-SW-03: Floating-Point Determinism across Operating Systems and Hardware
*Primary Code:* `benchmarks/test_clean_environment_reproducibility.py`  
**Question:** Does the link budget engine produce bit-exact identical floating-point outputs when compiled and executed on ARM64 macOS, Linux x86_64, and Windows x86_64 systems with differing math libraries?

### Q-SW-04: Out-of-Domain Physical Boundary Handling
*Primary Code:* `tests/test_milestone_13ac_physics_boundaries.py`  
**Question:** When physical inputs fall outside valid approximation regimes (e.g. slant range inside reactive near-field, elevation angle $< -90^\circ$, frequency $\le 0\text{ Hz}$), does Atlas guarantee structured graceful degradation, or can unhandled exceptions crash autonomous mission planners?

### Q-SW-05: Statistical Rigor of Monte Carlo Convergence in Grand Prix
*Primary Code:* `src/marswalk/core/atlas_grand_prix_statistics.py`  
**Question:** Are the confidence intervals reported in the Mission Grand Prix benchmarks computed using rigorous bootstrap or Student-t distributions, and has sample size sufficiency been validated against central limit theorem requirements?

### Q-SW-06: Absence of Synthetic Data Presented as Measured Reality
*Primary Code:* `data/parameter_provenance_registry.json`  
**Question:** Has Project Atlas adhered strictly to the rule prohibiting synthetic or generated numbers from being represented as real in-situ Martian observations?

### Q-SW-07: Handling of Numerical Singularity at Zenith ($\theta = 90^\circ$) and Nadir
*Primary Code:* `atlas_mars_atmospheric_model.py`  
**Question:** In spherical airmass formulas, does the geometric integrand encounter division by zero or numerical stiffness at exact zenith ($\theta = 90.000^\circ$) or when slant range approaches zero?

### Q-SW-08: State Consistency in Asynchronous DTN Routing
*Primary Code:* `atlas_dtn_engine.py`  
**Question:** Under heavy packet drop rates and intermittent multi-hop contact windows, does the DTN bundle router prevent memory leaks, duplicate bundle delivery, and routing loops?

### Q-SW-09: Test Suite Execution Time Scaling
*Primary Code:* `TEST_EXECUTION_RECORD.json`  
**Question:** The full test suite takes 241.54 seconds across 94 test files. Are tests properly isolated, and could slow end-to-end integration tests mask flaky intermittent race conditions?

### Q-SW-10: Traceability of Schema Validation for Mission Briefings
*Primary Code:* `schemas/`  
**Question:** Are mission scenario configurations strictly validated against Draft 2020-12 JSON Schemas before execution, preventing untyped or malformed parameters from entering the physics pipeline?

### Q-SW-11: Data Provenance and License Auditing
*Primary Code:* `DATA_PROVENANCE_AND_LICENSES.md`  
**Question:** Are all planetary terrain models (MOLA, HRSC, HiRISE) and atmospheric datasets properly attributed to NASA PDS / ESA PSA with compliant open-science licensing?

### Q-SW-12: External Reproducibility without Proprietary Tooling
*Primary Code:* `RELEASE_README.md`  
**Question:** Can an external auditor with a stock Python 3.10 installation successfully reproduce all benchmarks in under 5 minutes without creating an account, registering an API key, or accessing proprietary cloud servers?
