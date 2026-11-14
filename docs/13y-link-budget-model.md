# Milestone 13Y: Physical Link Budget & Propagation Specification

**Milestone:** 13Y — Atlas Planetary Network  
**Component:** `src/marswalk/core/atlas_network_link_model.py`  
**Classification:** Scientific Specification & RF Engineering Manual

---

## 1. Overview & Theoretical Principles

The communications architecture in Project Atlas simulates physical transmission physics across planetary surface-to-surface, surface-to-orbit, orbiter-to-orbiter, and orbiter-to-Earth channels.

Every simulated link budget computes:
1. **Free-Space Path Loss ($FSPL$):**
   $$FSPL = 20 \log_{10}\left(\frac{4 \pi R f}{c}\right)$$
2. **Equivalent Isotropically Radiated Power ($EIRP$):**
   $$EIRP = P_{tx}\text{ (dBW)} + G_{tx}\text{ (dBi)} - L_{\text{cable}}\text{ (dB)}$$
3. **Received Power ($P_{rx}$):**
   $$P_{rx} = EIRP - FSPL + G_{rx} - L_{\text{pointing}} - L_{\text{atm}} - L_{\text{implementation}}$$
4. **Noise Spectral Density ($N_0$):**
   $$N_0 = k_B \cdot T_{sys}\quad (\text{W/Hz})$$
   $$N_0\text{ (dBW/Hz)} = 10 \log_{10}(k_B) + 10 \log_{10}(T_{sys})$$
   where $k_B = 1.380649 \times 10^{-23}\text{ J/K}$.
5. **Carrier-to-Noise Ratio ($C/N_0$):**
   $$C/N_0\text{ (dB-Hz)} = P_{rx} - N_0$$
6. **Bit Energy to Noise Spectral Density Ratio ($E_b/N_0$):**
   $$\frac{E_b}{N_0} = C/N_0 - 10 \log_{10}(R_{\text{data}})$$

---

## 2. Standardized Frequency Bands & Hardware Profiles

| Band Profile | Carrier Freq | Typical Emitter | Typical Power | Antenna Gain (Tx) | Target Receiver | Typical Noise Temp ($T_{sys}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UHF Proximity** | 401.5 MHz | Rover / Outpost | 5–10 W | 3–6 dBi (monopole/patch) | Orbiter Nadir Helix | 350 K |
| **S-Band Surface**| 2.20 GHz | Settlement Mast | 20–50 W | 12–18 dBi (sector horn) | Rover / Habitat | 300 K |
| **X-Band Proximity**| 8.40 GHz | Orbiter Crosslink | 35 W | 28 dBi (reflector) | Orbiter Receiver | 250 K |
| **X-Band Deep Space**| 8.42 GHz | Orbiter / Settlement | 100 W | 42 dBi (high-gain dish) | DSN 34m/70m Ground Station | 25 K (cryogenic) |
| **Ka-Band Deep Space**| 32.0 GHz | Heavy Orbiter | 50 W | 48 dBi (high-gain dish) | DSN 34m/70m Ground Station | 35 K (cryogenic) |
| **Optical / Laser**| 1550 nm | Laser Transceiver | 5 W | 95 dBi (optical telescope) | Earth Optical Station | 290 K |

---

## 3. Propagation & Serialization Delays

Every transmission event is governed by two physical delays:
1. **Serialization Latency ($t_{tx}$):**
   $$t_{tx} = \frac{8 \times \text{PayloadBytes}}{R_{\text{data}}}$$
2. **Speed-of-Light Propagation Latency ($t_{prop}$):**
   $$t_{prop} = \frac{R}{c}$$
   where $c = 299,792,458\text{ m/s}$.

The absolute arrival timestamp is strictly:
$$t_{\text{arrival}} \ge t_{\text{start}} + t_{tx} + t_{prop}$$
No scheduling algorithm may deliver data prior to this physical lower bound.
