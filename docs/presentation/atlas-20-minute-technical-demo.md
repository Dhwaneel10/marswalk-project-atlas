# Project Atlas: 20-Minute In-Depth Technical Demonstration Walkthrough

**Document ID:** `ATLAS-DOC-DEMO-20M`  
**Classification:** Technical Colloquium & Engineering Walkthrough  
**Target Duration:** 20 minutes (1,200 seconds)  
**Repository:** [`E:/Python/NASA-Spaceapps/Marswalk`](file:///e:/Python/NASA-Spaceapps/Marswalk)

---

## 1. Technical Demonstration Structure

```
[00:00 - 02:30] 1. Motivation, Engineering Challenges & Architecture Stack
[02:30 - 05:00] 2. Cartographic Grounding & Geospatial Kernels
[05:00 - 07:30] 3. Multi-Agent Planning & 3-DOF Rotorcraft Aerodynamics
[07:30 - 10:00] 4. Bayesian Discovery & Shannon Information Theory
[10:00 - 12:30] 5. Interplanetary OWLT Communications & Onboard Autonomy
[12:30 - 15:00] 6. Stoichiometric ISRU, Nuclear Sizing & Conservation Ledgers
[15:00 - 17:30] 7. Resilience, FDIR Load-Shedding & Cascading Fault Injection
[17:30 - 20:00] 8. Cryptographic Merkle Replay, Verification Suite & Limitations
```

---

## 2. Segment-by-Segment Technical Presentation

### 1. Motivation, Engineering Challenges & Architecture Stack (0:00 - 2:30)
- **Problem Statement:** Martian surface exploration involves coupled physical constraints that cannot be analyzed in isolation.
- **Architectural Overview:** Walk through the 10-layer software stack in [`docs/research/architecture-overview.md`](file:///e:/Python/NASA-Spaceapps/Marswalk/docs/research/architecture-overview.md).
- **Core Principle:** Separation of computational engines (pure math, vectorized NumPy/SciPy operations) from orchestration managers (event coordination, state synchronization).

### 2. Cartographic Grounding & Geospatial Kernels (2:30 - 5:00)
- **Primary Data Source:** Authentic USGS Context Camera (CTX) GeoTIFF (`data/processed/jezero_ready_20m.tif`, SHA-256: `875e7e...`).
- **Mathematical Kernel:** Display Horn’s 8-neighborhood slope convolution:
  $$\frac{\partial z}{\partial x} = \frac{(z_{++} + 2z_{+0} + z_{+-}) - (z_{-+} + 2z_{-0} + z_{--})}{8 \cdot \Delta x}$$
- **Verification:** Demonstrate how the 20-meter resolution preserves delta channel incisions and steep crater rim scarps ($> 25^\circ$) that constrain traversal corridors.

### 3. Multi-Agent Planning & 3-DOF Rotorcraft Aerodynamics (5:00 - 7:30)
- **Pathfinding Engine:** Bi-level optimization combining pairwise terrain-constrained $A^*$ with 2-Opt local search TSP.
- **Atmospheric Physics:** Hypsometric pressure and density profiles ($H_\rho = 11.1\text{ km}$).
- **Blade Aerodynamics:** Momentum theory in compressible $CO_2$ ($\gamma = 1.29$, speed of sound $a \approx 226.2\text{ m/s}$).
- **Tip Mach Verification:** Show calculations proving tip Mach $M_{\text{tip}} = 0.667 < 0.75$, precluding supersonic compressibility shock losses.

### 4. Bayesian Discovery & Shannon Information Theory (7:30 - 10:00)
- **Active Learning Formalism:** Prior odds multiplied by empirical likelihood ratio $\Lambda(E \mid H)$:
  $$\text{Posterior Odds} = \text{Prior Odds} \cdot \Lambda(E \mid H)$$
- **Shannon Entropy Metric:**
  $$H(p) = - (p \log_2 p + (1-p) \log_2 (1-p))$$
- **Live Demonstration:** Ingest simulated PIXL geochemical telemetry from Delta Scarp; show entropy decreasing from $0.934\text{ bits} \to 0.327\text{ bits}$, achieving a $+0.607\text{ bit}$ information gain.

### 5. Interplanetary OWLT Communications & Onboard Autonomy (10:00 - 12:30)
- **Delay Simulation:** Discrete-event min-heap priority queue advancing discrete Martian seconds without non-deterministic system sleeps.
- **State-Hash Gating:** Inbound commands verified against current SHA-256 state snapshot:
  - If state matches: command executes.
  - If state diverged: command rejected immediately (`REJECTED_STALE_HASH`).
- **Deduplication:** Command hash ring guarantees idempotency.

### 6. Stoichiometric ISRU, Nuclear Sizing & Conservation Ledgers (12:30 - 15:00)
- **Power Model:** 40 kWe Kilopower Stirling core + solar PV array.
- **Chemistry:** Full chemical balancing for MOXIE ($2CO_2 \to 2CO + O_2$) and Sabatier ($CO_2 + 4H_2 \to CH_4 + 2H_2O$).
- **Mass Balance Ledger:** Demonstrate that $\Delta M = |M_{\text{final}} - (M_{\text{initial}} + M_{\text{in}} - M_{\text{out}})| = 0.000000\text{ kg}$, well within the $\le 10^{-4}\text{ kg}$ requirement.

### 7. Resilience, FDIR Load-Shedding & Fault Injection (15:00 - 17:30)
- **Fault Injection:** Inject Sol 48 convective dust storm ($\tau = 2.80$, solar flux drops to $120\text{ W/m}^2$).
- **Closed-Loop Load Shedding:** Autonomous resilience coordinator sheds the $28.0\text{ kWe}$ regolith microwave sintering line within 1 Sol.
- **Thermal Core Stability:** Base habitat heating is preserved; internal core temperature remains at $294.15\text{ K}$ (+21°C).

### 8. Cryptographic Merkle Replay, Verification Suite & Limitations (17:30 - 20:00)
- **Deterministic Replay:** Replay flagship mission `ATLAS-MARS-BASE-ALPHA-001` from scratch; show bit-exact SHA-256 root hash `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14`.
- **Perturbation Sensitivity:** Show that altering reactor power by $20\text{ kWe}$ produces an explainable, deterministic divergent hash (`c34011...`).
- **Test Inventory:** 1,116 automated tests passed (100%).
- **Explicit Limitations:** Remind audience that Atlas is a research simulation framework, not flight software, and does not certify operational safety for human astronauts.
