# Atlas Milestone 13S: Surface Power Systems & Energy Balance Model

## 1. NASA 2024 ACR Surface Power Alignment
In NASA's 2024 Architecture Concept Review (ACR), surface power was identified as the single greatest architectural determinant for crewed Mars operations.

While solar photovoltaic (PV) arrays are lightweight and deployable, pure solar surface architectures suffer catastrophic vulnerabilities on Mars:
1. **Diurnal Inactivity:** Zero generation during the 12-hour Martian night.
2. **Dust Attenuation:** Global dust storms elevate atmospheric optical depth ($\tau > 2.5$), attenuating direct solar flux by over 80%.
3. **Massive Energy Storage Penalty:** Sizing batteries to survive a 60-sol global dust storm requires tens of tonnes of battery mass, overwhelming launch manifests.

Accordingly, Atlas implements **Nuclear Fission Baseload Power (100–260 kWe)** as the primary reference, while providing comparative Solar PV and Hybrid configurations for trade studies.

---

## 2. Instantaneous Energy Balance Equations
At every timestep $\Delta t$, the settlement energy balance is governed by:

$$P_{\text{net}}(t) = P_{\text{generation}}(t) - P_{\text{distribution\_loss}}(t) - P_{\text{demand}}(t)$$

$$E_{\text{battery}}(t + \Delta t) = E_{\text{battery}}(t) + \eta_{\text{rt}} \cdot P_{\text{surplus}}(t) \cdot \Delta t \quad (\text{if } P_{\text{net}} > 0)$$

$$E_{\text{battery}}(t + \Delta t) = E_{\text{battery}}(t) - \frac{P_{\text{deficit}}(t) \cdot \Delta t}{\eta_{\text{discharge}}} \quad (\text{if } P_{\text{net}} < 0)$$

Where:
- $\eta_{\text{rt}} = 0.92$ (battery roundtrip efficiency).
- Minimum allowable depth of discharge: $E_{\text{reserve}} = 0.15 \cdot E_{\text{capacity}}$.

---

## 3. Power Generation Modeling

### A. Nuclear Fission Stirling Reactor (NASA Reference)
Continuous baseload generation modeled after the NASA Kilopower/Surface Fission Power project:
$$P_{\text{fission}}(t) = P_{\text{nameplate}} \cdot A_{\text{generator}}$$
- Completely independent of atmospheric optical depth ($\tau$), diurnal sun elevation, and dust storms.
- Availability factor $A_{\text{generator}} = 0.995$ nominal.
- Safety standoff distance: placed $1,000\text{ m}$ away in natural terrain depression with buried 5 kV transmission lines.

### B. Solar Photovoltaic (PV) with Dust Deposition
Modeled with diurnal solar geometry and exponential atmospheric absorption:
$$I_{\text{direct}}(t) = I_0 \cdot \exp\left(-\frac{\tau}{\max(0.1, \sin \theta_{\text{elev}}(t))}\right) \cdot \sin \theta_{\text{elev}}(t)$$
$$P_{\text{pv}}(t) = \frac{I_{\text{direct}}(t) \cdot A_{\text{array}} \cdot \eta_{\text{cell}} \cdot F_{\text{dust}}(t)}{1000}$$
- Dust degradation factor: $F_{\text{dust}}(t) = 1.0 - (1.0 - e^{-0.0008 \cdot \text{sol}})$.
- Electrostatic mitigation wipers restore $F_{\text{dust}}$ by $+0.35$ on command.

---

## 4. Seven-Tier Priority Load Shedding
When generation and battery capacity are insufficient to meet total demand, the Atlas automated power dispatcher sheds loads according to strict priority tiers:

| Tier | Priority Class | Load Name | Nominal Power | Shed Condition |
|---|---|---|---|---|
| **Tier 1** | Safety Critical | Habitat Pressurization & Life Support ECLSS | 22.0 kW | **NEVER SHED** |
| **Tier 2** | Mission Critical | Telecommunications Relay Mast & Avionics | 4.0 kW | Battery $< 5\%$ |
| **Tier 3** | Thermal Vital | Habitat Active Trace Heaters | 12.0 kW | Battery $< 15\%$ |
| **Tier 4** | Production Vital | Subsurface Water Extraction Reactor | 25.0 kW | Net generation deficit |
| **Tier 5** | Propellant Vital | Sabatier Methanation & O2 Liquefaction | 18.0 kW | Net generation deficit |
| **Tier 6** | Utilization | Science Laboratory & Mass Spectrometers | 14.0 kW | Nighttime / Off-peak |
| **Tier 7** | Deferrable | Robotic Charging Bay & Regolith Sintering | 20.0 kW | First to be shed |
