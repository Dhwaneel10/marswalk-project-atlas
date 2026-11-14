# Multi-Sol Scheduling Methods & Mathematical Formulation
**MarsWalk 2.0 / Project Atlas • Milestone 13H**
**Topographic Datum:** USGS CTX 20m Jezero Crater DTM, IAU 2000 Mars Spheroid ($R = 3,396,190\text{ m}$)

---

## 1. Mathematical Formulation

A Mars exploration campaign spans a sequence of $N$ sols:
$$\mathcal{S} = \{ S_1, S_2, \dots, S_N \}$$
Each sol $S_k$ consists of an ordered sequence of mission activities $\mathcal{A}_k = [a_{k,1}, a_{k,2}, \dots, a_{k,m}]$, where each activity $a \in \mathcal{A}_k$ belongs to one of four primitive types:
1. $\text{TRAVERSE}$: Locomotion between spatial coordinates over USGS 20m Jezero terrain mesh.
2. $\text{SCIENCE}$: Scientific observation, laser spectrometer firing (SuperCam), or core drilling (PIXL/SHERLOC).
3. $\text{RELAY\_DEPLOY}$: Deployment and RF alignment of an autonomous surface relay mast.
4. $\text{BIVOUAC}$: Overnight stationary rest, thermal maintenance, and battery trickle recharge.

---

## 2. Activity Energy & Time Equations

### 2.1 Locomotion Energy ($E_{\text{traverse}}$)
For each segment along the traverse of ground distance $\Delta s$ and slope angle $\theta$:
$$W_{\text{rolling}} = m \cdot g_{\text{mars}} \cdot C_{rr} \cdot \cos\theta \cdot \Delta s$$
$$W_{\text{gravity}} = m \cdot g_{\text{mars}} \cdot \sin\theta \cdot \Delta s$$
$$P_{\text{mech}} = \frac{\max(0, W_{\text{rolling}} + \max(0, W_{\text{gravity}}))}{\Delta t \cdot \eta_{\text{drivetrain}}}$$
$$E_{\text{segment}} = (P_{\text{mech}} + P_{\text{hotel\_base}}) \cdot \Delta t$$
where:
- $m = 1025.0\text{ kg}$ (Perseverance rover nominal class + payload)
- $g_{\text{mars}} = 3.71\text{ m/s}^2$
- $C_{rr} = 0.08$ (wheel rolling resistance on Jezero sandy regolith)
- $\eta_{\text{drivetrain}} = 0.72$ (mechanical drivetrain efficiency)
- $\eta_{\text{regen}} = 0.0$ (non-regenerative; zero descent energy recovery)

### 2.2 Science Observation Energy ($E_{\text{science}}$)
For target $T_j$ with active instruments $\mathcal{I}_j$:
$$E_{\text{sci}} = \sum_{I \in \mathcal{I}_j} (P_I + P_{\text{base}}) \cdot t_{I}$$
subject to the **Turret Singularity Protection Rule**: PIXL and SHERLOC cannot operate simultaneously due to shared mechanical arm turret kinematics and focal standoff constraints.

### 2.3 Data Generation & Transfer
For instrument $I \in \mathcal{I}_j$:
$$\Delta S_{\text{gen}} = D_I \quad (\text{MB})$$
During communication pass over link with bandwidth $R_{\text{link}}$:
$$\Delta S_{\text{rel}} = \min(S_{\text{buffer}}, R_{\text{link}} \cdot \Delta t_{\text{pass}})$$
$$S_{\text{buffer}}(t + \Delta t) = S_{\text{buffer}}(t) + \Delta S_{\text{gen}} - \Delta S_{\text{rel}}$$

---

## 3. Cross-Sol Carryover Invariants

At the boundary between Sol $k$ and Sol $k+1$:
1. **Battery State of Charge:**
   $$E_{\text{start}}(k+1) = \min(E_{\text{cap}}, E_{\text{end}}(k) + E_{\text{recharge}})$$
2. **Onboard Storage Buffer:**
   $$S_{\text{start}}(k+1) = S_{\text{end}}(k)$$
   Unrelayed data products remain queued in solid-state flash memory.
3. **Completed Target Set:**
   $$\mathcal{T}_{\text{completed}}(k+1) = \mathcal{T}_{\text{completed}}(k) \cup \mathcal{T}_{\text{visited}}(k)$$
   Completed targets are marked immutable and excluded from subsequent scheduling.
4. **Relay Network Topology:**
   $$\mathcal{R}_{\text{active}}(k+1) = \mathcal{R}_{\text{active}}(k) \cup \mathcal{R}_{\text{deployed}}(k)$$
   Deployed relay towers permanently provide microwave Line-of-Sight visibility.
