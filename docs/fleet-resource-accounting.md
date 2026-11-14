# Fleet Resource Accounting & Independent Ledgers
## Rigorous Zero-Energy-Pooling Power Budgeting & Finite Downlink Logistics

**Component:** `src/marswalk/core/fleet_resource_manager.py`  
**JSON Contract:** `schemas/api/v1/fleet-resources.schema.json`  
**Core Invariant:** Strictly Independent Per-Rover Battery Registers ($\forall i \neq j, \partial SOC_i / \partial E_j = 0$)

---

## 1. Principles of Physical Resource Modeling

In multi-rover planetary surface operations, treating resources as an interchangeable "fleet pool" is a critical modeling error. Electricity, onboard storage, and physical actuators reside in discrete mechanical chassis.

The Atlas Fleet Resource Manager enforces **independent ledger accounting**:
1. **Isolated Battery Registers:** Each rover tracks its own State of Charge ($SOC_{\text{rover}}$), discharge rate, thermal battery efficiency, and reserve safety margin ($20.0–25.0\%$).
2. **Local Solid-State Storage:** Science data products are recorded into individual non-volatile flash memory buffers ($32,768–65,536\text{ MB}$).
3. **Shared Downlink Channel:** All rovers share a finite surface-to-orbiter / DTE downlink pass bandwidth ($2.0\text{ Mbps}$ aggregate), requiring time-multiplexed data transfer scheduling.

---

## 2. Power & Energy Consumption Formulation

For each exploration unit $r_i$ executing mission activity sequence $\mathcal{A}$, the total energy consumed across Sol $s$ is:

$$E_{\text{consumed}}(r_i) = E_{\text{drive}}(r_i) + E_{\text{avionics}}(r_i) + E_{\text{instruments}}(r_i) + E_{\text{comms}}(r_i)$$

### Component Models:
1. **Drive Energy:**
   $$E_{\text{drive}} = \int_0^{T_{\text{drive}}} \left( P_{\text{rolling}} + P_{\text{gradient}}(\theta) \right) dt = \sum_{k=1}^K \frac{d_k}{v_k} \cdot \left[ \mu_{\text{roll}} M g_{\text{Mars}} + M g_{\text{Mars}} \sin(\theta_k) \right] \cdot \frac{1}{\eta_{\text{drivetrain}}}$$
   Where $M = 1,025\text{ kg}$, $g_{\text{Mars}} = 3.721\text{ m/s}^2$, $\mu_{\text{roll}} = 0.08$, $\eta = 0.72$.
2. **Base Avionics Load:**
   $$E_{\text{avionics}} = P_{\text{base}} \cdot T_{\text{operating}} \quad (P_{\text{base}} = 110\text{ W})$$
3. **Science Instruments:**
   $$E_{\text{instruments}} = \sum_{t \in \mathcal{T}(r_i)} P_{\text{inst}}(t) \cdot \tau_{\text{dwell}}(t)$$
   - PIXL: $85\text{ W}$, dwell $1800\text{ s}$ $\implies 42.5\text{ Wh}$
   - SHERLOC: $95\text{ W}$, dwell $2400\text{ s}$ $\implies 63.3\text{ Wh}$
   - RIMFAX: $40\text{ W}$, dwell $1200\text{ s}$ $\implies 13.3\text{ Wh}$
   - CORING_TOOL: $180\text{ W}$, dwell $3600\text{ s}$ $\implies 180.0\text{ Wh}$
4. **Communications Transceiver:**
   $$E_{\text{comms}} = P_{\text{tx}} \cdot \frac{\text{DataVolume}}{\text{DataRate}} \quad (P_{\text{tx}} = 35\text{ W}, R = 2.0\text{ Mbps})$$

---

## 3. Solar Insolation & Recharge Model

Solar generation is computed per sol based on the Mars Climate Database solar flux at Jezero ($18.38^\circ\text{ N}$):

$$E_{\text{solar}}(r_i) = A_{\text{panel}} \cdot \eta_{\text{PV}} \cdot \int_{\text{sunrise}}^{\text{sunset}} I_0 \cdot \exp\left(-\frac{\tau}{\cos(\theta_z(t))}\right) \cdot \cos(\theta_{\text{inc}}(t)) \, dt$$

Where:
- $A_{\text{panel}} = 1.4\text{ m}^2$ (triple-junction GaAs solar array).
- $\eta_{\text{PV}} = 0.285$.
- $\tau$: Atmospheric dust optical depth ($\tau = 0.65$ nominal, $\tau = 2.10$ during dust storm disturbance F4).
- Diurnal energy yield: $\approx 1,850\text{ Wh/sol}$ nominal.

---

## 4. Onboard Flash Memory & Shared Downlink Logistics

1. **Storage Utilization:**
   $$M_{\text{used}}(t) = M_{\text{initial}} + \sum \text{Data}_{\text{science}} - \sum \text{Data}_{\text{downlinked}}$$
2. **Storage Pressure Alert Thresholds:**
   - $\le 60\%$: `NOMINAL` (green)
   - $60–80\%$: `ELEVATED` (amber)
   - $>80\%$: `CRITICAL_BACKLOG` (red, triggers emergency downlink window preemption)
3. **Finite Downlink Bandwidth Management:**
   During a 60-minute orbiter overflight window, total downlink capacity is:
   $$\text{Cap}_{\text{downlink}} = 2.0\text{ Mbps} \times 3600\text{ s} = 7,200\text{ Mbits} = 900\text{ MB}$$
   The Fleet Resource Manager allocates transmission timeslots based on target science priority ($P(t)$), ensuring critical sample coring logs and Raman spectral cubes are returned before low-priority meteorological logs.
