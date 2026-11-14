# Project Atlas — Milestone 13X: Sensitivity Analysis & Operational Cliffs

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-sensitivity-analysis.md`  
**Status:** **VERIFIED & OPERATIONAL**  

---

## 1. Environmental Dust Optical Depth ($\tau$) Sweep

Sweeping atmospheric dust optical depth from $\tau = 0.3$ (crystal clear) to $\tau = 2.6$ (severe global dust storm):

| Dust $\tau$ | Solar Insolation | `STRAT-01` Greedy | `STRAT-02` MinCost | `STRAT-03` Science | `STRAT-04` ResSafe | `STRAT-05` Pareto | `STRAT-06` Atlas |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **0.3** | $478\text{ W/m}^2$ | Feasible (72.1) | Feasible (64.2) | Feasible (78.4) | Feasible (73.1) | Feasible (68.9) | Feasible (**79.5**) |
| **0.6** | $389\text{ W/m}^2$ | Feasible (70.4) | Feasible (63.0) | Feasible (75.1) | Feasible (72.0) | Feasible (67.4) | Feasible (**78.1**) |
| **1.0** | $293\text{ W/m}^2$ | Feasible (68.1) | Feasible (61.5) | Feasible (70.8) | Feasible (70.8) | Feasible (65.2) | Feasible (**76.4**) |
| **1.4** | $221\text{ W/m}^2$ | Feasible (65.9) | Feasible (59.8) | Feasible (66.5) | Feasible (69.4) | Feasible (63.1) | Feasible (**74.8**) |
| **1.8** | $166\text{ W/m}^2$ | Feasible (63.2) | Feasible (58.1) | Infeasible Cliff | Feasible (67.9) | Feasible (60.8) | Feasible (**73.0**) |
| **2.2** | $126\text{ W/m}^2$ | Feasible (60.5) | Feasible (56.2) | Infeasible Cliff | Feasible (66.1) | Infeasible Cliff | Feasible (**71.2**) |
| **2.6** | $95\text{ W/m}^2$ | Infeasible Cliff| Feasible (54.0) | Infeasible Cliff | Feasible (64.2) | Infeasible Cliff | Feasible (**69.1**) |

### Operational Takeaway:
- `STRAT-03-SCIENCE` experiences an **infeasibility cliff at $\tau \ge 1.8$** due to continuous high-drain instrument operation without load shedding.
- `STRAT-05-PARETO` fails at $\tau \ge 2.2$.
- `STRAT-04-RESSAFE` and `STRAT-06-ATLAS` remain feasible across the entire range up to $\tau = 2.6$, with Atlas maintaining the highest composite index throughout.

---

## 2. Battery Capacity Sweep (30 to 110 kWh)

- **$30\text{ kWh}$:** Only `STRAT-04-RESSAFE` and `STRAT-02-MINCOST` survive. All exploratory strategies experience battery depletion before completing half their scheduled observations.
- **$60\text{ kWh}$:** Atlas and Greedy become viable. Science return jumps from 5.1 to 10.0 points.
- **$90+\text{ kWh}$:** Science-First achieves maximum potential without energy constraint penalties.
