# Project Atlas — Milestone 13X: Benchmark Metrics & Constraint Verification

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Document:** `docs/13x-benchmark-metrics.md`  
**Status:** **VERIFIED & OPERATIONAL**  

---

## 1. Multi-Dimensional Performance Categories

The Grand Prix evaluation engine rejects single-scalar optimization in favor of 5 orthogonal categories:

### Category 1: Scientific Yield
- **Raw Science Points:** Cumulative value of completed observations.
- **Shannon Information Gain ($IG$):** Formulated as $IG = H(S) - H(S \mid Y)$, measuring entropy reduction over active planetary hypotheses.
- **Hypotheses Discriminated:** Integer count of hypothesis discrimination thresholds crossed.
- **Observation Completion Rate:** Ratio of surveyed targets to total candidate waypoints.

### Category 2: Operational Efficacy
- **Traverse Distance (km):** True ground distance traversed across all fleet assets.
- **Duration (Sols):** Elapsed mission sols to complete planned activities.
- **Route Efficiency Ratio:** $\frac{\text{Geodesic Shortest Distance}}{\text{Actual Path Distance}}$.
- **Task Success vs. Failure Counts:** Verified completion vs. aborted operations.

### Category 3: Resource Economics
- **Energy Consumed (kWh):** Direct electrical expenditure including drive motors, instrumentation, heating, and communications.
- **Battery Minimum State of Charge (SOC %):** Lowest instantaneous battery reserve margin observed.
- **Energy per Target Visited (kWh/target):** Unit resource cost of exploration.

### Category 4: Resilience & Fault Containment
- **Fault Containment Rate:** $\frac{\text{Faults Contained}}{\text{Total Injected Faults}}$.
- **Recovery Latency (Sols):** Cumulative schedule delay incurred during autonomous FDIR recovery.

### Category 5: Computational Efficiency
- **Planning Latency (ms):** Wall-clock time required to compile the complete initial mission plan.
- **Peak Memory Footprint (Bytes):** Memory allocated during plan synthesis.

---

## 2. Hard Constraint Infeasibility Rules

A strategy that violates physical or operational boundaries is declared **INFEASIBLE**:
1. **Chassis Rollover Threshold:** Traversal across terrain slopes exceeding vehicle mechanical limits ($>15.0^\circ$ for rovers). Marked as `INFEASIBLE_SLOPE`.
2. **Battery Depletion:** Net battery state of charge dropping to $0.0\%$. Marked as `INFEASIBLE_ENERGY`.
3. **Mission Clock Expiration:** Total execution duration exceeding scenario sol deadline. Marked as `INFEASIBLE_TIME`.

Infeasible runs suffer a **70% data loss penalty** and forfeit eligibility for top composite rankings.
