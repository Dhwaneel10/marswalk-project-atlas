# Milestone 13U: Research Software Description & Open Science Roadmap

**Project:** Project Atlas / MarsWalk 2.0  
**Software Class:** Autonomous Planetary Mission Operating System & Simulation Environment  
**Software DOI / Provenance:** MarsWalk Research Package (NASA Space Apps Challenge Ecosystem)

---

## 1. System Abstract

Project Atlas is an open-architecture planetary mission simulation and operating system designed to investigate autonomous multi-robot coordination, deep-space communication delays, closed-loop In-Situ Resource Utilization (ISRU), and resilient surface settlement operations in Jezero Crater, Mars.

The platform couples real USGS 20 m CTX terrain elevation rasters, NASA PDS4 archived MEDA climate records, and peer-reviewed physical equations (Horn slopes, BEMT rotor aerodynamics, Beer-Lambert solar attenuation, Sabatier thermochemistry) into an end-to-end discrete-event microkernel (`atlas_mission_execution_core.py`).

---

## 2. Mathematical Architecture & Core Methods

1. **Topographic Traversability:**
   Evaluates 2D slope fields using Horn 3×3 finite differences and applies terramechanics cost penalties for rover pathfinding via A*.
2. **Line-of-Sight & RF Visibility:**
   Bresenham-variant raymarching over 20 m elevation cells detects RF horizon occlusions between surface rovers, aerial scouts, and orbital relay orbiters (e.g. MRO).
3. **Interplanetary Latency Modeling:**
   Calculates One-Way Light Time ($\text{OWLT} \in [180, 1340]\text{ s}$) from instantaneous orbital distance $d_{\text{AU}}$, buffering command uplinks and rejecting out-of-date packets targeting obsolete Martian state signatures.
4. **Bayesian Active Learning:**
   Updates scientific hypothesis probabilities via Bayes' rule upon receiving simulated spectroscopic observations, evaluating information gain via Shannon binary entropy reduction.
5. **Closed-Loop Mass & Energy Ledger:**
   Enforces $\Delta M \le 10^{-4}\text{ kg}$ and $\Delta E \le 10^{-4}\text{ kWh}$ across Kilopower fission generation, solar PV arrays, battery storage, and atmospheric SOXE/Sabatier reactions.

---

## 3. Open Research Questions for External Collaborators

1. *Multi-Agent Conflict Resolution under Intermittent RF Links:* How can decentralized consensus protocols (e.g. Raft variants or CRDTs) optimize rover-aircraft task handoffs when crater rim shadows cause localized 30-minute communication blackouts?
2. *Adaptive GCM Residual Modeling:* Can online neural Gaussian Processes better capture multi-year interannual dust storm variability in Mars climate models without over-fitting to single-sol local anomalies?
3. *Heterogeneous Fleet Energy Trades:* What is the optimal division of labor between heavy ground rovers (high payload, low speed) and aerial rotorcraft (high speed, strict battery constraints) for regional sample return logistics?
