# Milestone 13T: Deep-Space Autonomy & Asynchronous Command Loop

**Milestone:** 13T — Atlas Planetary Mission OS  
**System Module:** `atlas_autonomous_operations.py`

---

## 1. Interplanetary Light-Time Latency

Because radio signals propagate at the speed of light $c \approx 299,792.458\text{ km/s}$, Earth-to-Mars communication experiences significant latency depending on the planetary orbital configuration ($d \in [0.52, 2.52]\text{ AU}$):

$$\text{OWLT} = \frac{d_{\text{AU}} \times 149,597,870.7\text{ km}}{299,792.458\text{ km/s}}$$

At the nominal mission test epoch ($d = 1.708\text{ AU}$):
- One-Way Light Time: **852.3 seconds (14.20 minutes)**.
- Round-Trip Light Time: **1,704.6 seconds (28.41 minutes)**.

---

## 2. Cryptographic Stale-Hash Guard

Under an asynchronous 14.2 min uplink delay, commanding a rover to execute a high-risk drill or traverse without verifying local surface conditions can result in mission loss if conditions change during packet transit.

Mission OS solves this with an onboard cryptographic guard:
1. When Earth Mission Control creates a command packet, it binds the currently known Martian state hash:
   $$\text{Packet}.\text{expected\_state\_hash} = H_{\text{Earth}}$$
2. Upon packet arrival on Mars, the onboard autonomy kernel compares $H_{\text{Earth}}$ to the live physical state hash $H_{\text{Mars}}(t_{\text{arrival}})$.
3. If $H_{\text{Earth}} == H_{\text{Mars}}$, the command is dispatched (`CommandState.EXECUTED`).
4. If $H_{\text{Earth}} \neq H_{\text{Mars}}$, the command is safely rejected (`CommandState.REJECTED_STALE_HASH`), holding autonomous safe-mode until a verified update is received.
