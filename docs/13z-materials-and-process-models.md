# Project Atlas — Milestone 13Z: Materials & Process Models
## Physical-Chemical Properties, Mass Balance & ISRU Transformation Mechanics

**Document Version:** 1.0.0  
**Classification:** Planetary Science & Chemical Engineering Specification  
**System Designation:** ATLAS-FOUNDRY-MATERIALS-13Z  
**Repository:** `E:\Python\NASA-Spaceapps\Marswalk`  

---

### 1. Epistemic Provenance & Evidence Hierarchy

To preserve scientific integrity in accordance with MarsWalk project rules, every physical constant, material density, and energy coefficient carries an explicit epistemic classification:

- **`MEASURED`**: Empirical measurements obtained by planetary flight missions (e.g. InSight HP3 thermal probe, Curiosity APXS/CheMin, Perseverance PIXL/SHERLOC).
- **`PUBLISHED`**: Sourced from peer-reviewed planetary literature or NASA technical memoranda (e.g. Gertsch et al., Mueller et al., Grotzinger et al.).
- **`DERIVED`**: Computed from thermodynamic equations, bulk material constitutive models, and mechanical mechanics.
- **`ASSUMED`**: Baseline engineering design assumptions documented for simulation feasibility.
- **`SYNTHETIC`**: Procedural parameters generated for boundary stress testing.

---

### 2. Material Classification & Engineering Parameters

The system models eight discrete material classes:

| Material Category | Density ($\text{kg/m}^3$) | Particle Size ($\mu\text{m}$) | Compressive Strength ($\text{MPa}$) | Energy ($\text{kWh/kg}$) | Yield / Waste | Epistemic Class | Primary Citation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`REGOLITH_FEEDSTOCK_RAW`** | 1,520 | 120 | 0.15 | 0.005 | 1.00 / 0.00 | `MEASURED` | InSight HP3 / Curiosity CheMin |
| **`REGOLITH_SCREENED`** | 1,650 | 65 | 0.35 | 0.020 | 0.82 / 0.18 | `PUBLISHED` | Gertsch et al. (2008), NASA TM |
| **`REGOLITH_COMPACTED`** | 1,880 | 65 | 2.50 | 0.035 | 0.98 / 0.02 | `DERIVED` | Terzaghi Soil Mechanics / InSight |
| **`REGOLITH_SINTERED_BLOCKS`**| 2,450 | Solid | 45.00 | 0.420 | 0.92 / 0.08 | `PUBLISHED` | Mueller et al. (2018), NASA STMD |
| **`REGOLITH_GEOPOLYMER`** | 2,150 | Solid | 35.00 | 0.180 | 0.95 / 0.05 | `PUBLISHED` | Montes et al. (2015), Adv Space Res |
| **`IMPORTED_STRUCTURAL`** | 4,500 | Monolithic | 850.00 | 0.010 | 1.00 / 0.00 | `PUBLISHED` | Ti-6Al-4V Grade 5 Aerospace Spec |
| **`METALLIC_FASTENERS`** | 7,850 | Fabricated | 650.00 | 0.005 | 1.00 / 0.00 | `PUBLISHED` | Stainless A4-80 High-Tensile Spec |
| **`ELECTRICAL_THERMAL`** | 2,700 | Modular | 180.00 | 0.015 | 1.00 / 0.00 | `PUBLISHED` | Aerogel Composite / Al-Busbars |

---

### 3. Mass-Energy Conservation Formulations

For every transformation operation $k \in \{\text{Excavation}, \text{Screening}, \text{Sintering}, \text{Compaction}\}$:

$$\sum M_{\text{in}} = M_{\text{product}} + M_{\text{waste}}$$

$$\Delta E_{\text{total}} = E_{\text{process}} + E_{\text{kinetic, robot}} + E_{\text{thermal loss}}$$

1. **Mechanical Screening**:
   $$M_{\text{screened}} = 0.82 \times M_{\text{raw}}$$
   $$M_{\text{oversized waste}} = 0.18 \times M_{\text{raw}}$$
   Reject fraction consists of basalt cobbles and boulders ($> 150\,\mu\text{m}$) diverted to foundation rip-rap fill.

2. **Solar Concentrator / Microwave Sintering**:
   $$M_{\text{paver blocks}} = 0.92 \times M_{\text{screened}}$$
   $$M_{\text{spall & vapor waste}} = 0.08 \times M_{\text{screened}}$$
   Thermal processing at $1,150^\circ\text{C}$ requires $0.42\,\text{kWh/kg}$ with $8\%$ volatile loss and thermal spall reject.

3. **Vibratory Compaction**:
   $$M_{\text{compacted bed}} = 0.98 \times M_{\text{screened}}$$
   $$M_{\text{edge spill waste}} = 0.02 \times M_{\text{screened}}$$
   Yields high bearing-capacity road subgrade ($\rho = 1,880\,\text{kg/m}^3$) with $2.5\,\text{MPa}$ unconfined compressive strength.
