# Project Atlas: Resource Accounting & Mass-Energy Conservation

**Document ID:** `ATLAS-DOC-RES-001`  
**Classification:** Space Systems Engineering  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. The Closed Conservation Principle

To prevent simulation artifacts from creating "free energy" or "phantom resources", Project Atlas models all physical flows through strict conservation ledgers managed by [`ResourceOperationsManager`](file:///e:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/atlas_resource_operations.py).

At every discrete Sol step, the mass ledger enforces:
$$M_{\text{final}} = M_{\text{initial}} + M_{\text{inflow}} - M_{\text{consumed}} - M_{\text{vented}}$$

The mass balance discrepancy $\Delta M$ is computed:
$$\Delta M = \Big| M_{\text{final}} - \big( M_{\text{initial}} + M_{\text{inflow}} - M_{\text{consumed}} - M_{\text{vented}} \big) \Big|$$
**Audit Gate Requirement:** $\Delta M \le 1.0 \times 10^{-4}\text{ kg}$ across every operational phase.

---

## 2. In-Situ Resource Utilization (ISRU) Stoichiometry

### 1. Solid Oxide Electrolysis (MOXIE Analogue)
Atmospheric carbon dioxide is split at high temperatures ($800^\circ\text{C}$) into carbon monoxide and breathable oxygen:
$$2\text{CO}_2 \to 2\text{CO} + \text{O}_2$$
**Molar Mass Balance:**  
$$2(44.01\text{ g}) \to 2(28.01\text{ g}) + 32.00\text{ g}$$
$$88.02\text{ g } \text{CO}_2 \to 56.02\text{ g } \text{CO} + 32.00\text{ g } \text{O}_2 \quad (\Delta m = 0.000\text{ g})$$

### 2. Sabatier Methanation
Carbon dioxide combined with feedstock hydrogen generates propellant-grade methane and water:
$$\text{CO}_2 + 4\text{H}_2 \to \text{CH}_4 + 2\text{H}_2\text{O}$$
**Molar Mass Balance:**  
$$44.01\text{ g } \text{CO}_2 + 4(2.016\text{ g}) \text{H}_2 \to 16.04\text{ g } \text{CH}_4 + 2(18.015\text{ g}) \text{H}_2\text{O}$$
$$52.07\text{ g reactants} \to 52.07\text{ g products} \quad (\Delta m = 0.000\text{ g})$$

---

## 3. Power System & Sintering Energy Balance

### Kilopower KRUSTY Fission Baseline
- **Thermal Core Rating:** $160\text{ kW}_{\text{thermal}}$
- **Stirling Conversion Efficiency:** $25.0\%$
- **Net Electrical Generation:** $40.0\text{ kWe}$ (continuous baseline)
- **Secondary Solar PV Grid:** Variable insolation based on dust tau:
  $$P_{\text{solar}} = A_{\text{pv}} \cdot \eta_{\text{pv}} \cdot S_0 \cdot \exp(-\tau / \cos \theta_z)$$

### Microwave Regolith Sintering
- **Specific Energy Required:** $1.4\text{ kWh per 20 kg basaltic block}$ ($70.0\text{ kWh/tonne}$)
- **Sintering Line Draw:** $28.0\text{ kWe}$
- **Production Rate:** 20 blocks per hour ($400\text{ kg/hour}$) under nominal power availability.
- When an electrical deficit occurs during dust storms, sintering is load-shed first to preserve life support thermal baselines ($294.15\text{ K}$).
