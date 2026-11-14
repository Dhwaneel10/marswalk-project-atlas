# Project Atlas — Milestone 13X: Strategy Performance Comparison

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-strategy-comparison.md`  
**Dataset:** 1,020 Simulations (170 Scenarios $\times$ 6 Competing Strategies)  
**Status:** **BENCHMARK EXECUTED & VERIFIED**  

---

## 1. Overall Championship Standings

The formal 8-round tournament results (exported directly from `strategy_rankings_summary.csv`):

| Strategy ID | Strategy Name | Algorithm Family | Feasibility Rate | Science Mean | Energy Mean (kWh) | Distance (km) | Fault Cont. | Composite Index | CVaR 5% | Category Award |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `STRAT-03-SCIENCE` | **Science-First Explorer** | `BAYESIAN_ACTIVE` | 92.9% | **11.82** | 74.66 | 2.74 | 0.43 | 62.64 | 5.05 | **Science Champion** |
| `STRAT-04-RESSAFE` | **Resource-Safe Planner** | `CONSERVATIVE` | **100.0%** | 5.13 | **13.80** | **1.31** | **1.00** | 71.41 | 56.50 | **Efficiency Champion** |
| `STRAT-06-ATLAS` | **Atlas Adaptive Director**| `INTEGRATED_OS` | **100.0%** | 10.04 | 49.21 | 2.55 | **1.00** | **75.95** | **63.57** | **Overall Grand Prix Champion** |
| `STRAT-01-GREEDY` | **Greedy Explorer** | `GREEDY_HEURISTIC`| **100.0%** | 10.89 | 47.66 | 2.79 | 0.43 | 68.59 | 46.42 | Runner-Up Science |
| `STRAT-05-PARETO` | **Multi-Objective Optimizer**| `PARETO_NSGA2` | 92.4% | 6.85 | 15.28 | 1.82 | 0.70 | 65.19 | 5.00 | Balanced Compromise |
| `STRAT-02-MINCOST` | **Minimum-Cost Navigator** | `COST_MINIMIZE` | **100.0%** | 6.88 | 19.69 | 1.43 | 0.29 | 61.12 | 36.12 | Low-Cost Baseline |

---

## 2. In-Depth Trade-Off Analysis

### 2.1 The Science vs. Energy Frontier
- **`STRAT-03-SCIENCE`** achieved the highest raw science yield ($11.82$ points) by hunting high-entropy hypotheses. However, its high power draw ($74.66\text{ kWh}$) resulted in an **infeasibility rate of 7.1%** in severe scenarios, causing its lower-tail $\text{CVaR}_{5\%}$ score to collapse to $5.05$.
- **`STRAT-04-RESSAFE`** achieved an unbroken **100% feasibility rate** and minimal energy footprint ($13.80\text{ kWh}$), but at the cost of sacrificing more than half of available scientific discoveries ($5.13$ mean science).

### 2.2 Why Atlas Won the Overall Title
- **`STRAT-06-ATLAS`** did not win the pure Science award (10.04 vs 11.82) or the pure Efficiency award (49.21 vs 13.80 kWh).
- However, by coupling forward aerial reconnaissance with ground rover drives and resilient load shedding, Atlas achieved **100% feasibility, 100% fault containment, and the highest worst-case CVaR (63.57)**, earning the balanced Championship title.
