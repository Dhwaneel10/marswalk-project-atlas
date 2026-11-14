# Milestone 13AC — Stage 4: Cross-Module Boundary Review
## Orbital Contacts, Planetary Terrain Geometry, and ISRU Mass-Energy Conservation Boundaries

**Document Designation:** `ATLAS-13AC-DOC-STAGE4-CROSS-MODULE`  
**Milestone:** 13AC — Physics Boundary Qualification  
**Modules Audited:**  
1. `src/marswalk/core/atlas_orbital_contact_planner.py` (Orbital Astrodynamics & Contact Planning)  
2. `src/marswalk/core/terrain.py` (Planetary DEM Topography & Horn Slope Geometry)  
3. `src/marswalk/core/atlas_foundry_resource_processing.py` (ISRU Production & Mass-Energy Balances)  
**Status:** QUALIFIED & HARDENED  
**Date:** 2026-11-07  

---

## 1. Scope & Objective

Following the deep remediation of RF and optical propagation in Stages 1–3, Stage 4 audits boundary conditions, mathematical singularities, and physical conservation laws across three core simulation domains:
1. Orbital contact geometry (zenith/nadir passes, grazing contacts, infinitesimal contact durations).
2. Terrain slope calculations (vertical cliff singularities, DEM border padding, negative pixel spacing).
3. Industrial ISRU manufacturing (mass conservation invariants, non-positive mass rejection, power draw monotonicity).

---

## 2. Module 1: Orbital Contact Planner (`atlas_orbital_contact_planner.py`)

### 2.1 Zenith Pass Geometry ($\theta = +90.0^\circ$)
- **Physical Situation:** An orbiter passes directly through the local zenith of a Martian surface asset (e.g., Jezero Base).
- **Mathematical Evaluation:**
  $$\vec{r} = \vec{p}_{\text{orb}} - \vec{p}_{\text{surf}}, \quad \hat{u}_{\text{up}} = \frac{\vec{p}_{\text{surf}}}{\|\vec{p}_{\text{surf}}\|}$$
  $$\sin\theta = \frac{\vec{r} \cdot \hat{u}_{\text{up}}}{\|\vec{r}\|} = 1.0 \implies \theta = \arcsin(1.0) = 90.0^\circ$$
- **Finding:** Airmass is $X(90^\circ) = 1.000$ (exact vertical atmospheric column). Slant range is at its perigee minimum ($R = h_{\text{alt}}$). Path loss is minimized and link margin is maximized. No division-by-zero or numerical instability occurs.

### 2.2 Nadir / Antipodal Occultation Geometry ($\theta = -90.0^\circ$)
- **Physical Situation:** The orbiter is positioned directly on the opposite side of Mars beneath the ground station's feet.
- **Mathematical Evaluation:**
  $$\sin\theta = \frac{\vec{r} \cdot \hat{u}_{\text{up}}}{\|\vec{r}\|} = -1.0 \implies \theta = -90.0^\circ$$
- **Finding:** In 13AA/13AB, geometric elevation was clamped to $+1.0^\circ$ inside atmospheric loss, which risked scheduling contact windows through the planet. In 13AC:
  1. Ray-sphere intersection `is_line_of_sight_occulted_by_mars` returns `True` ($t^* = 0.5$, closest approach distance $d = 0 < R_M$).
  2. `evaluate_link` detects $\theta \le 0.0^\circ$ and tags the link as `OCCULTED_BELOW_HORIZON` (`is_physically_available = False`, `is_link_closed = False`).
  3. `plan_contact_schedule` asserts `res.is_physically_available`, guaranteeing zero false contact windows.

### 2.3 Infinitesimal Duration & Grazing Contacts
- **Physical Situation:** An orbiter grazes the operational elevation mask ($\theta \approx 5.0^\circ$) for a fleeting interval $\Delta t \to 0$.
- **Finding:** If $\Delta t$ is less than the serialization time of a single data frame:
  $$\Delta t < \frac{\text{Frame Size (bits)}}{\text{Operational Rate (bps)}}$$
  the link cannot complete custody transfer. In `atlas_network_link_model.py`, `calculate_transmission_time_s` returns $\infty$ if operational rate is 0 or link is not closed, and the DTN engine drops fractional uncommitted chunks during handover.

---

## 3. Module 2: Terrain Geometry & Slope Calculation (`terrain.py`)

### 3.1 Horn's Weighted Finite-Difference Slope Formulation
Horn's $3\times 3$ kernel computes the gradient components:
$$\frac{\partial z}{\partial x} = \frac{(z_{13} + 2 z_{23} + z_{33}) - (z_{11} + 2 z_{21} + z_{31})}{8 \times \Delta x_{\text{ground}}}$$
$$\frac{\partial z}{\partial y} = \frac{(z_{11} + 2 z_{12} + z_{13}) - (z_{31} + 2 z_{32} + z_{33})}{8 \times \Delta y_{\text{ground}}}$$
$$\theta_{\text{slope}} = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \times \frac{180}{\pi}$$

### 3.2 Vertical Cliff Boundary ($\frac{\partial z}{\partial x} \to \infty$)
- **Mathematical Invariant:** The range of the real arctangent function is strictly bounded:
  $$\lim_{u \to \infty} \arctan(u) = \frac{\pi}{2} \text{ radians} = 90.0^\circ$$
- **Finding:** Slope can never exceed $90.0^\circ$ or wrap around to negative numbers regardless of elevation disparity across adjacent pixels.

### 3.3 DEM Edges and Pixel Spacing Invariants
- `dx_ground_m <= 0` or `dy_ground_m <= 0` strictly raises `ValueError(f"Ground spacings must be positive: dx={dx}, dy={dy}")`.
- Horn's $3\times 3$ convolution cannot evaluate boundary cells ($x = 0, y = 0, x = W-1, y = H-1$). Atlas handles this by propagating invalid masks and setting edge cells to NaN rather than fabricating zero slopes.
- When pathfinding across DEM boundaries, `AStarPlanner` and `traverse_cost` treat NaN cells as strictly impassable ($c = \infty$).

---

## 4. Module 3: Resource/ISRU Balance Models (`atlas_foundry_resource_processing.py`)

### 4.1 First Law of Thermodynamics: Strict Mass Conservation
Every physical transformation in the Planetary Foundry obeys:
$$M_{\text{input}} \equiv M_{\text{usable}} + M_{\text{waste}}$$
where:
$$M_{\text{usable}} = \text{round}(M_{\text{input}} \times \eta_{\text{yield}}, 4), \quad M_{\text{waste}} = \text{round}(M_{\text{input}} - M_{\text{usable}}, 4)$$
No mass is created or destroyed.

### 4.2 Non-Positive Mass Input Hardening (13AC Remediation)
Prior to 13AC, negative mass inputs (e.g. $M_{\text{input}} = -500\text{ kg}$) were not explicitly guarded at the method entry points of `execute_excavation`, `execute_screening`, `execute_sintering`, and `execute_compaction`. A negative input would subtract mass from feedstock buffers and add negative energy consumption, effectively modeling "free energy generation" and reverse excavation.

In Milestone 13AC, all processing entry points enforce:
```python
if math.isnan(mass_kg) or math.isinf(mass_kg) or mass_kg <= 0:
    raise ValueError(f"Processing mass must be a positive finite number, got {mass_kg}")
```
This guarantees:
1. No zero or negative excavation operations.
2. Energy consumption $E = M \times e_{\text{spec}}$ is strictly positive ($E > 0\text{ kWh}$).
3. Robot battery drain is monotonic with work performed.

---

## 5. Summary Matrix of Cross-Module Physical Boundaries

| Module | Boundary Condition | Physical Consequence | Atlas 13AC Defense Mechanism | Status |
|:-------|:-------------------|:---------------------|:-----------------------------|:-------|
| Orbital Contacts | Nadir pass ($\theta = -90^\circ$) | Total Martian occultation | Ray-sphere intersection + `OCCULTED_BELOW_HORIZON` tag | HARDENED |
| Orbital Contacts | Grazing pass ($\theta \approx \theta_{\text{mask}}$) | Transient contact $\Delta t \to 0$ | Serialization latency check + DTN custody rejection | HARDENED |
| Terrain | Vertical cliff ($\Delta z \to \infty$) | Slope approaches $90.0^\circ$ | Mathematical boundedness of $\arctan$ in $[0, \pi/2]$ | HARDENED |
| Terrain | DEM boundary border | Missing $3\times 3$ neighborhood | 1-pixel border masking to NaN; infinite traversal cost | HARDENED |
| ISRU Foundry | Negative mass input ($M \le 0$) | Spurious power generation | Strict `ValueError` rejection on non-positive mass | HARDENED |
| ISRU Foundry | Mass balance | Mass destruction or creation | Exact equality $M_{\text{in}} = M_{\text{usable}} + M_{\text{waste}}$ | HARDENED |
