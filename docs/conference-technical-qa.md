# MarsWalk 2.0 / Project Atlas: Conference Technical Q&A
## Grounded, Defensible Responses to Space Science & Robotics Evaluators

**Milestone:** 13A — Independent Scientific Validation & Conference Qualification  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 31, 2026  
**Audience:** NASA Space Apps Challenge Judges, Planetary Cartographers, Autonomous Systems Engineers, Space Mission Planners  

---

### Q1: What specific terrain dataset powers MarsWalk 2.0? Is it HiRISE or CTX?
**Answer:**  
MarsWalk 2.0 is powered exclusively by the **USGS Astrogeology Mars 2020 TRN CTX Digital Terrain Model (DTM) Mosaic** (Fergason et al., 2020), accessible under USGS DOI: [`10.5066/P906QQT8`](https://doi.org/10.5066/P906QQT8).
- **Raw File:** `JEZ_ctx_B_soc_008_DTM_MOLAtopography_DeltaGeoid_20m_Eqc_latTs0_lon0.tif`  
  *Size:* 9,662,387 bytes | *SHA-256:* `16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b`
- **Processed Terrain:** `data/processed/jezero_ready_20m.tif`  
  *Size:* 252,206 bytes | *SHA-256:* `875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3`  
  This is a lossless $250 \times 250$ sub-grid crop centered on the Western Delta Front ($77.440^\circ\text{ E}, 18.442^\circ\text{ N}$). Maximum absolute elevation difference between raw and cropped pixels is exactly $0.000000\text{ m}$.
- **Attribution Correction:** Earlier Milestone 12I sprint notes colloquially referred to a 20m HiRISE DTM. Our independent data audit revealed that zero HiRISE rasters exist in the repository; the 20m data is 100% authentic USGS CTX. HiRISE 1m represents a future zoom tier on our product roadmap. All code contracts, HUD headers, and briefings have been updated to explicitly cite "USGS CTX 20m DTM".

---

### Q2: Is the route returned by MarsWalk 2.0 globally optimal, or an approximation?
**Answer:**  
The route is **mathematically guaranteed to be globally optimal** for the discrete 8-connected grid graph under the configured cost objective function.
- **Proof:** MarsWalk utilizes an A* graph search algorithm paired with a generalized octile heuristic $h(u)$. Because the traversal cost function satisfies $C(u \to v) \ge d(u, v)$ for all edges, and the octile heuristic is the exact obstacle-free Euclidean ground distance on an 8-connected grid, $h(u) \le h^*(u)$ strictly holds everywhere (admissibility). Furthermore, $h(u)$ satisfies the triangle inequality $h(u) \le C(u \to v) + h(v)$ across all edges (consistency/monotonicity).
- **Empirical Validation:** Benchmarked against an independent, pure Dijkstra reference solver on identical graphs across flat planes, asymmetric slopes, steep scarps, and real Jezero crater DTM topography. The optimal path cost difference between A* and Dijkstra is strictly $0.000000\text{ m}$ (exact match), while A* pruned up to $97.9\%$ of node expansions.

---

### Q3: How does MarsWalk handle Mars' planetary curvature and latitude distortion?
**Answer:**  
MarsWalk models Mars using the **IAU 2000 planetocentric sphere** with mean radius $R_{\text{Mars}} = 3,396,190.0\text{ m}$.  
Because the raster is in Equirectangular projection with standard parallel $\phi_0 = 0^\circ$, parallels of latitude contract towards the poles with $\cos(\phi)$. MarsWalk applies exact geodetic scale factors:
- North-South meridional step: $dy_{\text{ground}} = 20.000000\text{ m}$ (invariant).
- East-West parallel step: $dx_{\text{ground}} = 20.0 \cdot \cos(18.442^\circ) = 18.972887\text{ m} \approx 18.973\text{ m}$.
- Diagonal step: $d_{\text{diag}} = \sqrt{dx^2 + dy^2} = 27.567562\text{ m}$.  
A naive planar Euclidean calculation ($20\sqrt{2} \approx 28.284\text{ m}$) would overestimate East-West and diagonal distances by $2.53\%$. Incorporating the Equirectangular metric ensures physical scale fidelity.

---

### Q4: How are terrain slopes calculated? Do you measure point-to-point elevation deltas or 2D facet normals?
**Answer:**  
MarsWalk computes **both**, and integrates them using a **dual-slope maximum operator**:
$$\theta_{uv} = \max\left(\theta_{\text{dest}}, \theta_{\text{step}}\right)$$
1. $\theta_{\text{dest}}$ is the 2D surface facet slope computed via the standard **Horn (1981) $3 \times 3$ finite-difference convolution kernel**, measuring the true terrain gradient vector.
2. $\theta_{\text{step}}$ is the directional point-to-point grade $\arctan(|\Delta z| / d)$.
- **Why this is critical for astronaut safety:**  
  If a planner relies only on point-to-point slope ($\theta_{\text{step}}$), an astronaut or rover walking horizontally along a contour line on a $25^\circ$ scarp has $\Delta z = 0 \implies \theta_{\text{step}} = 0.0^\circ$. A naive planner would classify the scarp contour as "flat terrain" and route the mission across dangerous side-hill slip and vehicle rollover hazards. Taking $\max(\theta_{\text{dest}}, \theta_{\text{step}})$ guarantees that side-hill scarp traverses are heavily penalized ($+800\%$ effort cost).

---

### Q5: How do you prevent double-counting between slope penalties and uphill climbing costs?
**Answer:**  
They represent distinct, orthogonal physical mechanisms:
1. **Slope Penalty ($P_{\text{slope}} \propto (\theta/\theta_c)^2$):** Quadratic and **symmetric**. Walking on a $20^\circ$ incline induces slip, reduced stride length, and traction loss regardless of whether the crew is moving uphill, downhill, or traversing the contour.
2. **Uphill Climbing Cost ($P_{\text{uphill}} \propto \max(0, \Delta z)$):** Strictly **asymmetric and directional**. It models the mechanical work $\Delta W = m \cdot g_{\text{Mars}} \cdot \Delta z$ required to lift crew mass against Martian gravity ($g = 3.72076\text{ m/s}^2$). When descending ($\Delta z < 0$), $P_{\text{uphill}} = 0$.
Additive decomposition tests confirm that $C_{\text{model}} = C_{\text{dist}} + C_{\text{slope}} + C_{\text{rough}} + C_{\text{uphill}}$ reconciles down to $1.42 \times 10^{-14}\text{ m}$ with zero mathematical overlap.

---

### Q6: What is measured data vs. what is a derived model estimate in MarsWalk?
**Answer:**  
MarsWalk maintains strict separation across all APIs, UI displays, and briefings:
- **Measured Data:**  
  - USGS CTX DTM elevation matrix $Z(r, c)$ referenced to the MOLA DeltaGeoid datum.
  - Planetocentric ground distance $d(u, v)$.
  - Horn 2D surface gradient vector $\nabla Z$.
  - Local surface roughness RMS residual $\sigma_r$.
  - In-situ atmospheric telemetry from Perseverance MEDA and Curiosity REMS PDS4 archives.
- **Derived Model Estimates:**  
  - Equivalent flat-terrain effort cost $C$.
  - Nominal walking speed range ($1.5 - 2.5\text{ km/h}$) and rover mobility derating factors.
  - Suit consumable depletion rates ($O_2$, battery, thermal loop).
  - Traversal duration and sol timeline scheduling.
  - Parameter sensitivities and elasticity gradients.

---

### Q7: Can a route planned by MarsWalk 2.0 be considered operationally safe for astronauts?
**Answer:**  
**NO. MarsWalk routes must NEVER be characterized as certified safe for human spaceflight.**  
MarsWalk is a strategic, high-level planning decision-support instrument based on 20m satellite orbital altimetry. Sub-pixel micro-hazards (such as 0.5m meter-scale boulders, fissures, unconsolidated regolith, and mechanical rover track entrapment) cannot be resolved at 20m/pixel. Operational astronaut safety requires ground-truth micro-reconnaissance, real-time suit telemetry, geotechnical soil testing, and human-in-the-loop mission director sign-off.  
This truth disclosure is hardcoded into `src/marswalk/api/contracts.py` and rendered prominently on every UI cockpit screen and technical briefing.

---

### Q8: Why does the Mission Robustness Lab use deterministic parameter sweeps instead of Monte Carlo failure odds?
**Answer:**  
Claiming that a mission has a "94.2% probability of astronaut survival on Mars" is scientifically ungrounded because there is no empirical statistical prior for Martian component failure distributions. Assigning an arbitrary Gaussian or Poisson distribution to rockfalls or spacesuit life-support failures produces synthetic pseudo-precision.  
Instead, MarsWalk uses **deterministic sensitivity analysis and stress testing**:
- Systematic parameter sweeps (e.g., walking speed from $0.5$ to $2.5\text{ km/h}$, slope penalty weighting from $1.0$ to $8.0$).
- Explicit boundary condition envelopes that pinpoint the exact threshold where a mission transitions from `FEASIBLE` to `INFEASIBLE`.
- Clear mathematical elasticity metrics ($\epsilon_i$) that inform mission architects which engineering assumptions most heavily drive mission risk.

---

### Q9: How does the system handle in-stride disruptions during a mission rehearsal?
**Answer:**  
MarsWalk implements a deterministic **closed-loop recovery triage hierarchy**:
1. **Level 1 (In-Situ Resume):** Transient disturbances (e.g., temporary sensor glitch, brief telemetry blackout) resolve in-place without altering the route geometry.
2. **Level 2 (Local A* Detour):** Spatial terrain hazards (e.g., localized boulder fall, sudden slope scarp) trigger dynamic graph cost re-weighting ($C_{\text{hazard}} = \infty$) and compute a minimal detour path around the obstacle.
3. **Level 3 (Target Pruning):** Consumable or mobility deratings that make completing all science waypoints infeasible trigger automated science-value triage, dropping the lowest-priority targets to safeguard return margins.
4. **Level 4 (Direct Abort):** Critical suit or life-support emergencies trigger an immediate abort, routing the crew back to the habitat via the fastest safe corridor.

---

### Q10: How do you guarantee the integrity of exported Mission Evidence Dossiers?
**Answer:**  
Exported dossier ZIP archives are protected by a cryptographically verifiable **Evidence Manifest**:
- Every constituent file (`experiment_dossier.json`, `cross_scenario_matrix.csv`, `executive_briefing.md`, `provenance.json`, `README.txt`) is hashed with SHA-256.
- The manifest records individual digests and an overall manifest SHA-256 signature.
- `verify_experiment_dossier_zip()` validates the entire archive upon ingestion:
  - If any file's bytes are altered $\to$ **REJECTED (hash mismatch)**.
  - If an unauthorized extra file is injected $\to$ **REJECTED (untracked file detected)**.
  - If an expected evidence artifact is missing $\to$ **REJECTED (missing artifact)**.

---

### Q11: How is time modeled across multi-sol campaigns?
**Answer:**  
Time is modeled using the IAU/NASA Martian solar day standard:
$$1\text{ Sol} = 88,775.244\text{ SI seconds} = 24^{\text{h}}\; 39^{\text{m}}\; 35.244^{\text{s}}$$
Campaign schedules enforce strict operational EVA windows (e.g., maximum 4 to 8 hours of daylight sortie time per sol) with mandatory overnight rest and battery recharging periods in the habitat. Sol timeline scrubbers map second-level simulation telemetry to exact sol offsets without drift.

---

### Q12: How are raster boundaries and missing (NoData) pixels handled?
**Answer:**  
- **NoData Imputation during Convolutions:** Sentinels ($\le -1000\text{ m}$) are masked. To prevent NaN poisoning and boundary distortion during $3 \times 3$ spatial convolutions, invalid cells are temporarily assigned the median valid elevation before reflective edge convolution.
- **Dilated Hazard Buffering:** After convolution, the invalid mask is dilated by 1 cell using an 8-connected structuring element. All dilated border cells are assigned `NaN`.
- **Traversal Barrier:** The graph router assigns infinite cost ($C = \infty$) to any node or neighbor possessing `NaN` slope or elevation, physically barring routes from approaching unmapped territory.
- **Zero-Injection Safety:** In Jezero Crater ($-2500\text{ m}$ datum), naive code defaulting `None` to `0.0m` injects a false $+2500\text{ m}$ climb spike. MarsWalk evaluates elevation deltas only when both adjacent samples are valid, completely preventing false elevation spikes.

---

### Q13: How does MarsWalk balance conflicting mission objectives like distance, suit consumable cost, and science return?
**Answer:**  
MarsWalk uses **multi-objective Pareto optimization**:
- Candidates are evaluated across an objective vector (e.g., minimize ground distance, minimize equivalent effort cost, maximize scientific sample diversity).
- The system computes the non-dominated Pareto frontier: candidate $A$ dominates candidate $B$ if and only if $A$ is no worse than $B$ across all objectives and strictly superior in at least one.
- Candidates violating operational EVA constraints are partitioned into the `INFEASIBLE` set with documented failure reasons. The mission architect is presented with the complete Pareto trade-off curve, allowing evidence-based decision making.

---

### Q14: How was the frontend validated to ensure UI telemetry matches backend physics?
**Answer:**  
The web interface was verified via automated **Chrome DevTools Protocol (CDP)** sessions across all 5 studios (Mission Control, Robustness Lab, Rehearsal Director, Causal Replay, Experiment Studio) at desktop ($1920\times 1080$) and laptop ($1366\times 768$) viewports:
- UI DOM metrics were directly cross-referenced against backend `/api/` JSON responses.
- SI unit formatting (m, km, °, s, sols) was asserted with regular expressions.
- Horizontal page overflow was verified to be strictly $0\text{ px}$ (`scrollWidth <= innerWidth`).
- Zero unhandled JavaScript exceptions or console errors were confirmed.
- Evidence screenshots were captured and archived for demonstration.
