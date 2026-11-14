# ATLAS 13AE: RECEIVER SYSTEM NOISE TEMPERATURE & REFERENCE PLANE AUDIT

**Document Identifier:** `ATLAS-DOC-13AE-STAGE-04`  
**Milestone:** 13AE — Propagation Evidence Closure  
**Parent Milestone:** 13AD — Mars Physics Reference Validation  
**Date:** November 2026  
**Status:** Audit Completed — Reference Planes Formalized  

---

## 1. Executive Summary & Audit Mandate

In Milestone 13AD, the receiver system noise temperature was formalized as:

$$T_{\text{sys}} = T_{\text{ant}} + T_{\text{feed}} + T_{\text{rx}} \cdot L_{\text{feed}}$$

where:
$$T_{\text{feed}} = (L_{\text{feed}} - 1) T_{\text{phys}}, \quad T_{\text{rx}} = (10^{\frac{\text{NF}}{10}} - 1) \cdot 290.0\text{ K}$$

**Audit Objectives:**
1. Establish the precise reference plane of each quantity.
2. Confirm that feed cable attenuation is not double-counted between $P_{\text{rx}}$ and $N_0$.
3. Clarify the physical meaning of the $2.725\text{ K}$ Cosmic Microwave Background (CMB) lower bound as an external environmental sky contribution rather than an electronic receiver property.

---

## 2. Reference Plane Formalization & Network Theory

In RF telecommunications engineering (JPL DESCANSO; Kraus & Marhefka; Pozar Microwave Engineering), a receiving chain consists of an antenna, a passive feed/transmission line, and a Low-Noise Amplifier (LNA):

```
       Antenna Reference Plane (Plane A)
              │
              │  Signal: P_rx,ant
              ▼
    [ Antenna Terminals ]
              │
              │  Feed Line Loss L >= 1.0 at Physical Temp T_L
              │  Power Gain G_feed = 1 / L
              ▼
       LNA Input Reference Plane (Plane B)
              │
              │  Signal: P_rx,lna = P_rx,ant / L
              ▼
    [ Low-Noise Amplifier (NF, T_rx) ]
```

### 2.1 The Two Standard Formulations

#### Formulation A: Antenna Terminal Reference Plane (Input-Referred)
Referred to the output terminals of the ideal antenna (before feed losses):
- **Received Carrier Power:**
  $$P_{\text{rx, ant}} = \text{EIRP} - \text{FSPL} + G_{\text{rx, ant}} - A_{\text{pointing}} - A_{\text{atm}} - A_{\text{impl}}$$
  *(Note: Feed loss $L_{\text{feed}}$ is NOT subtracted here).*
- **Noise Temperature Components:**
  - Antenna delivered noise: $T_{\text{ant}}$
  - Feed line noise referred to Plane A: $T_{\text{feed, A}} = (L - 1) T_L$
  - Receiver LNA noise referred to Plane A: $T_{\text{rx, A}} = L \cdot T_{\text{rx}}$
- **Total System Noise Temperature:**
  $$T_{\text{sys, ant}} = T_{\text{ant}} + (L - 1) T_L + L \cdot T_{\text{rx}}$$
- **Noise Spectral Density:**
  $$N_{0, \text{ant}} = k_B \cdot T_{\text{sys, ant}}$$
- **Carrier-to-Noise Density ($C/N_0$):**
  $$\frac{C}{N_0} = \frac{P_{\text{rx, ant}}}{k_B T_{\text{sys, ant}}}$$

#### Formulation B: LNA Input Reference Plane (Output-Referred)
Referred to the input terminals of the LNA (after feed losses):
- **Received Carrier Power:**
  $$P_{\text{rx, lna}} = \frac{P_{\text{rx, ant}}}{L} \implies P_{\text{rx, lna, dBW}} = P_{\text{rx, ant, dBW}} - L_{\text{feed, dB}}$$
- **Total System Noise Temperature:**
  $$T_{\text{sys, lna}} = \frac{T_{\text{ant}}}{L} + \left(1 - \frac{1}{L}\right) T_L + T_{\text{rx}}$$
- **Carrier-to-Noise Density ($C/N_0$):**
  $$\frac{C}{N_0} = \frac{P_{\text{rx, lna}}}{k_B T_{\text{sys, lna}}} = \frac{P_{\text{rx, ant}} / L}{k_B (T_{\text{sys, ant}} / L)} = \frac{P_{\text{rx, ant}}}{k_B T_{\text{sys, ant}}}$$

### 2.2 Proof of Zero Double-Counting in Project Atlas
Inspection of `atlas_network_link_model.py`:
1. In `PhysicalLinkBudgetEngine.evaluate_link` (line 593):
   $$p_{\text{rx\_dbw}} = \text{EIRP} - \text{FSPL} + G_{\text{rx}} - \text{pointing\_loss} - \text{atm\_loss} - \text{rx.impl\_loss}$$
   Feed loss ($L_{\text{feed}}$) is **not** subtracted from $p_{\text{rx\_dbw}}$. Therefore, received power is evaluated strictly at **Plane A (Antenna Terminals)**.
2. In `ReceiverSpec.calculate_system_noise_temp` (line 166):
   $$T_{\text{sys}} = T_{\text{ant}} + (L - 1) T_{\text{phys}} + L \cdot T_{\text{rx}}$$
   All noise contributions are evaluated strictly at **Plane A (Antenna Terminals)**.
3. Therefore:
   $$C/N_0 = P_{\text{rx, ant}} - 10\log_{10}(k_B T_{\text{sys, ant}})$$
   is mathematically exact and identical to JPL Deep Space Network standards. **There is zero double-counting.**

---

## 3. The 2.725 K Cosmic Microwave Background (CMB) Treatment

### 3.1 External Sky Brightness vs Electronic Noise
The Cosmic Microwave Background temperature ($T_{\text{CMB}} = 2.725 \pm 0.002\text{ K}$, Fixsen 2009) is an **external electromagnetic brightness temperature**, not an internal thermodynamic floor of the receiver hardware.

The antenna brightness temperature $T_{\text{ant}}$ integrates radiation from the surrounding environment over the complete $4\pi$ steradian antenna reception pattern:

$$T_{\text{ant}} = \frac{1}{4\pi} \iint_{4\pi} G(\theta, \phi) T_B(\theta, \phi) \sin\theta \, d\theta \, d\phi$$

where the local brightness temperature $T_B(\theta, \phi)$ includes:
1. **Cosmic Microwave Background:** $T_{\text{CMB}} \approx 2.725\text{ K}$ (pervades all unobstructed sky).
2. **Galactic Background Radiation:** Non-thermal synchrotron radiation, significant below $1\text{ GHz}$ ($T_{\text{gal}} \propto f^{-2.5}$).
3. **Martian Atmospheric Emission:** $T_{\text{atm}} (1 - \exp(-\tau_{\text{slant}}))$.
4. **Martian Surface Regolith Emission:** Thermal blackbody emission ($T_{\text{ground}} \approx 210 - 240\text{ K}, \epsilon \approx 0.95$) captured by antenna backlobes and ground spillover.

### 3.2 Operational Scenarios for $T_{\text{ant}}$
- **Deep Space Antenna Pointed at Cold Sky:** $T_{\text{ant}} \approx 3 - 5\text{ K}$ (CMB dominates).
- **Surface Rover / Lander Pointed Upward ($\theta > 30^\circ$):** Main beam sees cold sky + thin atmosphere ($T_{\text{sky}} \approx 15\text{ K}$), but ground spillover into sidelobes adds $\approx 20 - 40\text{ K}$, yielding $T_{\text{ant}} \approx 35 - 60\text{ K}$.
- **Surface Rover Grazing Horizon ($\theta < 5^\circ$):** Half of the main beam intersects warm Martian ground ($220\text{ K}$), yielding $T_{\text{ant}} \approx 130 - 180\text{ K}$.
- **Solar Alignment (Sun in Main Beam or Near Sidelobes):** Quiet Sun brightness temperature exceeds $10,000\text{ K}$ at X-band, resulting in catastrophic $T_{\text{sys}}$ degradation.

### 3.3 Validity Rule
The guard condition in `ReceiverSpec.calculate_system_noise_temp`:
```python
if t_antenna_k < 2.7:
    raise ValueError(f"Antenna brightness temperature cannot be below CMB (2.7 K), got {t_antenna_k} K")
```
is enforced as a **physical constraint on the environment**, because no passive antenna in the observable universe can view a sky cooler than the Big Bang relic radiation ($2.725\text{ K}$).

---

## 4. Physical Constants & Units Verification

- **Boltzmann Constant ($k_B$):** $1.380649 \times 10^{-23}\text{ J/K}$ (exact SI value, 2019 BIPM redefinition).
- **Reference Noise Temperature ($T_0$):** $290.0\text{ K}$ (IEEE Std 161 standard definition of Noise Figure).
- **Noise Spectral Density ($N_0$):** Units of $\text{W/Hz}$ or $\text{dBW/Hz}$.
  $$N_0 (\text{dBW/Hz}) = 10 \log_{10}(1.380649 \times 10^{-23}) + 10 \log_{10}(T_{\text{sys}}) = -228.60 + 10 \log_{10}(T_{\text{sys}})$$
  This formulation is verified 100% correct in `atlas_network_link_model.py`.
