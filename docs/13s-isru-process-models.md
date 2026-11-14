# Atlas Milestone 13S: In-Situ Resource Utilization (ISRU) Process Models

## 1. Closed Mass Conservation Law
Every ISRU chemical, physical, and thermodynamic process in Atlas adheres strictly to the First Law of Thermodynamics and conservation of mass:

$$m_{\text{inputs}} = m_{\text{products}} + m_{\text{waste\_byproducts}} + m_{\text{process\_losses}}$$

$$\text{Residual} = m_{\text{inputs}} - \left( \sum m_{\text{products}} + \sum m_{\text{waste}} + \sum m_{\text{losses}} \right)$$

Every reaction audit verifies:
$$|\text{Residual}| < 10^{-4}\text{ kg}$$
If this condition is violated, the simulation flags an integrity error and halts state progression.

---

## 2. The Four Primary In-Situ Conversion Chains

### A. Subsurface Water Extraction from Phyllosilicates
Extracts structural and pore water from hydrated clays via enclosed thermal auger desorption:
- **Operating Temperature:** $450^\circ\text{C}$ to release interlayer $OH^-$ groups.
- **Stoichiometric Balance:**
  - $1,000\text{ kg}$ clay feedstock at $7.5\text{ wt}\%$ water content.
  - Recovery yield: $\eta_{\text{thermal}} = 0.85$.
  - Products: $63.75\text{ kg}$ potable water ($H_2O$).
  - Waste byproducts: $925.0\text{ kg}$ dry spent tailings.
  - Losses: $11.25\text{ kg}$ unrecovered steam and dust spallation.
  - Residual: $|63.75 + 925.0 + 11.25 - 1000.0| = 0.0\text{ kg}$.
- **Specific Energy:** $1.75\text{ kWh/kg } H_2O$ recovered.

---

### B. Atmospheric Solid Oxide Electrolysis (MOXIE Scaling)
Ingests ambient Martian atmosphere ($95.3\% \text{ CO}_2$ at $650\text{ Pa}$) and splits it at $800^\circ\text{C}$ across ceramic scandia-stabilized zirconia (YSZ) membranes:
$$2\text{CO}_2 \longrightarrow 2\text{CO} + \text{O}_2$$
- Stoichiometric mass ratios:
  - $88\text{ g/mol } 2\text{CO}_2 \longrightarrow 56\text{ g/mol } 2\text{CO} + 32\text{ g/mol } \text{O}_2$.
  - Maximum theoretical $O_2$ mass yield: $32 / 88 = 36.36\%$.
- Process breakdown per $500\text{ kg } CO_2$ intake:
  - Compressor seal loss ($0.5\%$): $2.5\text{ kg}$.
  - Electrolysis cell conversion ($42\%$): $208.95\text{ kg } CO_2$ converted.
  - Oxygen product net: $75.60\text{ kg } O_2$ (liquefied to cryogenic storage).
  - Oxygen venting loss: $0.38\text{ kg}$.
  - Carbon monoxide byproduct: $132.97\text{ kg } CO$.
  - Unreacted $CO_2$ purge: $288.55\text{ kg}$.
  - Total inputs: $500.0\text{ kg} = \text{Products } (75.60) + \text{Waste } (421.52) + \text{Losses } (2.88) = 500.0000\text{ kg}$.
- **Electrical Specific Energy:** $4.2\text{ kWh/kg } O_2$.

---

### C. Catalytic Sabatier Methanation ($CH_4$ Propellant Production)
Synthesizes return propellant for the Mars Ascent Vehicle (MAV) over a ruthenium-on-alumina catalyst bed:
$$\text{CO}_2 + 4\text{H}_2 \longrightarrow \text{CH}_4 + 2\text{H}_2\text{O}$$
- Stoichiometric mass ratios:
  - $44\text{ kg } CO_2 + 8\text{ kg } H_2 \longrightarrow 16\text{ kg } CH_4 + 36\text{ kg } H_2O$.
- **Strict Hydrogen Conservation:** Hydrogen cannot be generated out of thin air. It must be supplied from imported reserves or local water electrolysis ($2H_2O \to 2H_2 + O_2$).
- Tracking: Atlas dynamically updates hydrogen inventory and identifies limiting reagents.
- Water recovery: The $36\text{ kg } H_2O$ byproduct is condensed, filtered, and returned to the water cache.

---

### D. Microwave Regolith Sintering
Sintering raw basaltic regolith into load-bearing blocks, landing pad pavers, and blast deflection berms:
- Operating frequency: $2.45\text{ GHz}$ magnetron heating.
- Volatile release: $4.0\text{ wt}\%$ (adsorbed moisture and trace gases vented).
- Dense sintered yield: $94.0\%$ of solid mass rigidized into $25\text{ kg}$ high-compression blocks.
- Specific energy: $0.35\text{ kWh/kg}$ regolith sintered.
