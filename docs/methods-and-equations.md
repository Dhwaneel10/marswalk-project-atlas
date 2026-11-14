# MarsWalk 2.0 / Project Atlas: Methods and Equations
## Formal Mathematical, Geodetic & Physical Formulation of Martian Route Optimization

**Milestone:** 13A — Independent Scientific Validation & Conference Qualification  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Date:** October 31, 2026  
**Auditor Classification:** Rigorous Mathematical Formulation & Primary Physical Derivations  
**Standard Units:** SI Base Units (meters, kilograms, seconds, radians/degrees, Kelvin)  

---

## 1. Geodetic Coordinate Systems & Spatial Metric Scaling

### 1.1 Planetary Reference Sphere (IAU 2000 Mars Datum)
Mars is approximated using the IAU 2000 planetocentric reference sphere recommended by the International Astronomical Union / International Association of Geodesy (Seidelmann et al., 2002):
- **Mean Volumetric Radius:**
  $$R_{\text{Mars}} = 3,396,190.0\text{ m} \approx 3,396.19\text{ km}$$
- **Meridional Arc Length per Degree:**
  $$M_{\text{lat}} = \frac{\pi \cdot R_{\text{Mars}}}{180^\circ} \approx 59,274.6975\text{ m/deg}$$

### 1.2 Equirectangular Projection Metric Scale Factors
The terrain raster is projected in Equirectangular (Simple Cylindrical) coordinates with standard parallel at the equator ($\phi_0 = 0^\circ$). Because parallels contract towards the poles, metric grid spacing is anisotropic as a function of latitude $\phi$:
- **North-South Metric Cell Spacing ($dy_{\text{ground}}$):**
  Lines of latitude are evenly spaced, yielding a constant distance invariant across all latitudes:
  $$dy_{\text{ground}} = C = 20.00000000\text{ m}$$
  where $C$ is the nominal grid resolution ($20.0\text{ m}$).
- **East-West Metric Cell Spacing ($dx_{\text{ground}}$):**
  Parallels of latitude contract with the cosine of the reference latitude $\phi_{\text{ref}}$:
  $$dx_{\text{ground}}(\phi) = C \cdot \cos(\phi)$$
  For Jezero Crater Western Delta Front ($\phi_{\text{ref}} = 18.442^\circ\text{ N}$):
  $$\phi_{\text{rad}} = 18.442^\circ \times \frac{\pi}{180^\circ} \approx 0.32187362\text{ rad}$$
  $$\cos(18.442^\circ) \approx 0.94864437$$
  $$dx_{\text{ground}} = 20.0000 \times 0.94864437 = 18.97288748\text{ m} \approx 18.973\text{ m}$$
- **Diagonal Metric Ground Step ($d_{\text{diag}}$):**
  $$d_{\text{diag}} = \sqrt{dx_{\text{ground}}^2 + dy_{\text{ground}}^2} = \sqrt{(18.97288748)^2 + (20.00000000)^2} = 27.56756172\text{ m}$$

### 1.3 8-Connected Discrete Ground Distance
On an 8-connected grid, the true ground distance $d(u, v)$ between node $u = (r_1, c_1)$ and adjacent node $v = (r_2, c_2)$ with row displacement $\Delta r = r_2 - r_1 \in \{-1, 0, 1\}$ and column displacement $\Delta c = c_2 - c_1 \in \{-1, 0, 1\}$ is:
$$d(u, v) = \sqrt{(\Delta c \cdot dx_{\text{ground}})^2 + (\Delta r \cdot dy_{\text{ground}})^2}$$

This formulation guarantees the standard metric space properties:
1. **Non-negativity & Identity:** $d(u, v) \ge 0$, and $d(u, v) = 0 \iff u = v$.
2. **Symmetry:** $d(u, v) = d(v, u)$.
3. **Triangle Inequality:** $d(u, w) \le d(u, v) + d(v, w)$.

---

## 2. Terrain Surface Derivatives & Slope Hazard Modeling

### 2.1 Point-to-Point Step Slope ($\theta_{\text{step}}$)
For a direct transition between adjacent grid cells $u$ and $v$ with elevations $z(u)$ and $z(v)$:
$$\theta_{\text{step}}(u, v) = \arctan\left(\frac{|z(v) - z(u)|}{d(u, v)}\right) \times \frac{180^\circ}{\pi}$$

### 2.2 Horn (1981) 3x3 Surface Normal Gradient Kernel
To measure the true two-dimensional facet orientation rather than a single line segment, MarsWalk computes spatial partial derivatives using the standard Horn weighted convolution kernel across a $3 \times 3$ window centered at cell $(r, c)$:

$$\begin{bmatrix} z_{11} & z_{12} & z_{13} \\ z_{21} & z_{22} & z_{23} \\ z_{31} & z_{32} & z_{33} \end{bmatrix} = \begin{bmatrix} z(r-1, c-1) & z(r-1, c) & z(r-1, c+1) \\ z(r, c-1) & z(r, c) & z(r, c+1) \\ z(r+1, c-1) & z(r+1, c) & z(r+1, c+1) \end{bmatrix}$$

The finite-difference partial derivatives in the ground coordinate system are:
$$\frac{\partial z}{\partial x} = \frac{(z_{13} + 2 z_{23} + z_{33}) - (z_{11} + 2 z_{21} + z_{31})}{8 \cdot dx_{\text{ground}}}$$
$$\frac{\partial z}{\partial y} = \frac{(z_{11} + 2 z_{12} + z_{13}) - (z_{31} + 2 z_{32} + z_{33})}{8 \cdot dy_{\text{ground}}}$$

The Horn slope magnitude in degrees is:
$$\theta_{\text{Horn}}(r, c) = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \times \frac{180^\circ}{\pi}$$

### 2.3 The Dual-Slope Maximum: Side-Hill Roll-Over Hazard Mitigation
A critical flaw in naive digital path planning is evaluating only $\theta_{\text{step}}$. Consider an astronaut or rover traversing along a horizontal contour line on a $25^\circ$ scarp. Because $z(v) = z(u)$, $\Delta z = 0$ and $\theta_{\text{step}} = 0.0^\circ$. A naive planner would treat this contour as flat, routing crew or vehicles across dangerous side-hill slip and vehicle roll-over hazards.

MarsWalk solves this by integrating facet slope and step slope via the maximum operator:
$$\theta_{uv} = \max\left(\theta_{\text{dest}}, \theta_{\text{step}}(u, v)\right)$$
where $\theta_{\text{dest}} = \theta_{\text{Horn}}(r_2, c_2)$.

**Physical Impact:**
- Walking directly up/down a slope: $\theta_{\text{step}} \approx \theta_{\text{dest}} \implies \theta_{uv} \approx \theta_{\text{dest}}$.
- Walking along a contour on a steep scarp: $\theta_{\text{step}} \approx 0^\circ \implies \theta_{uv} = \theta_{\text{dest}}$, correctly penalizing the scarp traverse.

### 2.4 Surface Roughness Proxy ($\sigma_r$)
Surface roughness is calculated as the root-mean-square (RMS) deviation of local elevation from a moving $3 \times 3$ mean filter:
$$\bar{z}(r, c) = \frac{1}{9} \sum_{i=-1}^{1} \sum_{j=-1}^{1} z(r+i, c+j)$$
$$\sigma_r(r, c) = \sqrt{\frac{1}{9} \sum_{i=-1}^{1} \sum_{j=-1}^{1} \left(z(r+i, c+j) - \bar{z}(r, c)\right)^2}$$

---

## 3. Traversal Cost Model & Energy Mechanics

### 3.1 Multi-Component Traversal Cost Function
The cost $C(u \to v)$ of traversing a directed edge from $u$ to $v$ represents the *equivalent flat-terrain effort distance* in meters:
$$C(u \to v) = d(u, v) \cdot \left[ 1.0 + P_{\text{slope}} + P_{\text{roughness}} + P_{\text{uphill}} \right]$$

where:
- **Base Distance Component:**
  $$C_{\text{base}} = d(u, v)$$
- **Slope Penalty (Quadratic Traction Slip Penalty):**
  $$P_{\text{slope}} = \alpha_{\text{slope}} \cdot \left(\frac{\theta_{uv}}{\theta_{\text{critical}}}\right)^2$$
  where $\theta_{\text{critical}} = 15.0^\circ$ (nominal slope limit) and $\alpha_{\text{slope}} = 4.0$.
- **Roughness Penalty (Linear Mechanical Impedance):**
  $$P_{\text{roughness}} = \alpha_{\text{rough}} \cdot \left(\frac{\sigma_r(v)}{\sigma_0}\right)$$
  where $\sigma_0 = 1.0\text{ m}$ (nominal roughness reference) and $\alpha_{\text{rough}} = 2.0$.
- **Uphill Climbing Work (Asymmetric Gravitational Penalty):**
  $$P_{\text{uphill}} = \alpha_{\text{uphill}} \cdot \frac{\max(0, z(v) - z(u))}{d(u, v)}$$
  where $\alpha_{\text{uphill}} = 3.0$.

### 3.2 Additive Cost Decomposition
Multiplying through by $d(u, v)$:
$$C(u \to v) = C_{\text{base}} + C_{\text{slope}} + C_{\text{rough}} + C_{\text{uphill}}$$
where:
$$C_{\text{base}} = d(u, v)$$
$$C_{\text{slope}} = d(u, v) \cdot \alpha_{\text{slope}} \left(\frac{\theta_{uv}}{\theta_{\text{critical}}}\right)^2$$
$$C_{\text{rough}} = d(u, v) \cdot \alpha_{\text{rough}} \left(\frac{\sigma_r(v)}{\sigma_0}\right)$$
$$C_{\text{uphill}} = \alpha_{\text{uphill}} \cdot \max(0, z(v) - z(u))$$

### 3.3 Physical Orthogonality (Zero Double-Counting Proof)
A common critique in path planning is whether slope and uphill penalties double-count topographic impedance. In MarsWalk:
1. **$P_{\text{slope}}$ is Symmetric with Respect to Elevation Delta Sign:**
   A $20^\circ$ facet penalizes movement whether walking downhill, uphill, or across the contour. It represents the loss of traction, lateral slip, and reduced stepping velocity caused by incline angle.
2. **$P_{\text{uphill}}$ is Purely Directional (Gravitational Work):**
   Climbing against Martian gravity ($g_{\text{Mars}} = 3.72076\text{ m/s}^2$) requires mechanical potential energy work:
   $$\Delta W = m \cdot g_{\text{Mars}} \cdot \Delta z \quad (\Delta z > 0)$$
   When descending ($\Delta z < 0$), $P_{\text{uphill}} = 0$.
3. **Conclusion:** Traction loss and gravitational work represent distinct, non-overlapping physical phenomena. Their additive separation is physically rigorous and introduces zero double-counting.

---

## 4. Cumulative Elevation & Conservation Laws

### 4.1 Elevation Conservation Invariant
For any discrete route sequence $p = (p_0, p_1, \dots, p_{N-1})$ with elevation samples $z_k = z(p_k)$:
- **Cumulative Climb (Gain):**
  $$G = \sum_{k=0}^{N-2} \max(0, z_{k+1} - z_k)$$
- **Cumulative Descent (Loss):**
  $$D = \sum_{k=0}^{N-2} \max(0, z_k - z_{k+1})$$

**Conservation Theorem:**
$$\max(0, \Delta z) - \max(0, -\Delta z) \equiv \Delta z$$
Summing across all $N-1$ segments:
$$G - D = \sum_{k=0}^{N-2} (z_{k+1} - z_k) = z_{N-1} - z_0 = \Delta z_{\text{net}}$$

This identity is enforced and analytically verified in the test harness to machine epsilon ($10^{-14}\text{ m}$).

---

## 5. Discrete Graph Optimization & Heuristic Search

### 5.1 Admissible & Consistent Generalized Octile Heuristic
To accelerate shortest-path search without sacrificing global optimality, MarsWalk employs the generalized octile distance heuristic tailored to anisotropic grid dimensions:

$$h(u, v) = \min(|\Delta r|, |\Delta c|) \cdot d_{\text{diag}} + \left| |\Delta r| - |\Delta c| \right| \cdot d_{\text{step}}$$
where:
$$d_{\text{step}} = \begin{cases} dx_{\text{ground}} & \text{if } |\Delta c| \ge |\Delta r| \\ dy_{\text{ground}} & \text{if } |\Delta r| > |\Delta c| \end{cases}$$

### 5.2 Proof of Global Optimality (A* Equivalence to Dijkstra)
1. **Admissibility ($h(u) \le h^*(u)$):**
   Since all penalty multipliers satisfy $P_{\text{slope}} \ge 0$, $P_{\text{rough}} \ge 0$, and $P_{\text{uphill}} \ge 0$, every directed edge cost satisfies:
   $$C(u \to v) \ge d(u, v)$$
   The octile heuristic $h(u, v)$ is the exact obstacle-free Euclidean ground distance on the 8-connected grid. Therefore, for all nodes $u$, $h(u, v) \le h^*(u, v)$, proving $h$ is strictly admissible.
2. **Consistency (Monotonicity):**
   For every edge $(u, v)$:
   $$h(u, \text{dest}) \le d(u, v) + h(v, \text{dest}) \le C(u \to v) + h(v, \text{dest})$$
   Monotonicity guarantees that when node $u$ is selected for expansion, the shortest path to $u$ has been permanently found. No node is re-expanded, and the first path found to the destination is globally optimal.

---

## 6. Multi-Objective Pareto Optimization

### 6.1 Mathematical Formulation of Pareto Dominance
Let a mission campaign design candidate $x$ be evaluated across an objective vector $F(x) = (f_1(x), f_2(x), \dots, f_K(x))$ where objectives are minimized ($f_k \downarrow$) or maximized ($f_m \uparrow$).

For minimization objectives, candidate $A$ strictly dominates candidate $B$ ($A \succ B$) if and only if:
$$A \succ B \iff \left( \forall i \in \{1, \dots, K\}, f_i(A) \le f_i(B) \right) \land \left( \exists j \in \{1, \dots, K\}, f_j(A) < f_j(B) \right)$$

### 6.2 Infeasibility & Constraint Handling
Let $\mathcal{F}$ be the feasible set defined by operational EVA constraints (e.g., maximum sortie duration $T \le 14,400\text{ s}$, consumable margin $\ge 20\%$, slope $\le 25^\circ$).
The dominance relation is partitioned:
1. If $A \in \mathcal{F}$ and $B \notin \mathcal{F}$, then $A \succ B$ strictly.
2. If $A \notin \mathcal{F}$ and $B \notin \mathcal{F}$, neither dominates; both are placed in the `INFEASIBLE` set with documented rejection reasons.
3. If $A \in \mathcal{F}$ and $B \in \mathcal{F}$, standard vector dominance applies.
4. Duplicate candidates ($F(A) \equiv F(B)$) do not dominate each other; both remain in the non-dominated Pareto set.

---

## 7. Mission Simulation, Robustness & Rehearsal Mechanics

### 7.1 Martian Sol Conversion
The Martian mean solar day (sol) is defined by the IAU/NASA standard:
$$1\text{ Sol} = 88,775.244\text{ SI seconds} = 24^{\text{h}}\; 39^{\text{m}}\; 35.244^{\text{s}}$$
Multi-sol campaign schedules and timeline scrubs convert sol offsets to cumulative seconds via:
$$T_{\text{mission}}(s, t_{\text{sol}}) = s \cdot 88,775.244\text{ s} + t_{\text{sol}}$$
where $s \in \{0, 1, \dots, N_{\text{sols}}-1\}$ and $t_{\text{sol}} \in [0, 88775.244)$.

### 7.2 Deterministic Robustness Ratio ($R_{\text{test}}$)
In the Mission Robustness Lab, a baseline mission plan is subjected to a set of $N_{\text{evaluated}}$ deterministic perturbation scenarios $\mathcal{S}$.
The robustness ratio $R_{\text{test}}$ is:
$$R_{\text{test}} = \frac{N_{\text{feasible}}}{N_{\text{evaluated}}}$$
where:
- $N_{\text{feasible}}$ is the count of scenarios where the mission was executed or adapted within all safety and consumable limits without mission failure or critical abort.
- Scenarios resulting in `DEGRADED`, `PENDING`, or `FAILED` are strictly excluded from $N_{\text{feasible}}$.

### 7.3 Safe Percentage Delta ($\Delta_{\%}$)
When comparing perturbed metrics $v_{\text{test}}$ against baseline $v_{\text{base}}$:
$$\Delta_{\%}(v_{\text{test}}, v_{\text{base}}) = \begin{cases} \left(\frac{v_{\text{test}} - v_{\text{base}}}{v_{\text{base}}}\right) \times 100\% & \text{if } v_{\text{base}} \ne 0 \\ \text{None (JSON null)} & \text{if } v_{\text{base}} = 0 \end{cases}$$
This avoids invalid division-by-zero errors or infinite percentage artifacts.

### 7.4 Sensitivity & Elasticity Derivatives
The Mission Robustness Lab calculates local parameter sensitivities using forward finite differences:
$$S_i = \frac{\Delta M}{\Delta P_i} = \frac{M(P_i + \Delta P_i) - M(P_i)}{\Delta P_i}$$
where $M$ is a mission metric (e.g., total campaign duration) and $P_i$ is an operational parameter (e.g., walking speed, rover derating).
The dimensionless elasticity $\epsilon_i$ is:
$$\epsilon_i = \frac{P_{i, 0}}{M_0} \cdot S_i$$
Elasticity allows direct cross-parameter comparison of mission vulnerability.
