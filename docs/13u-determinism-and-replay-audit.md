# Milestone 13U: Determinism & Cryptographic Replay Audit

**Milestone:** 13U — Atlas Independent Qualification Program  
**Scope:** Discrete-Event Determinism, Floating-Point Precision, Canonical State Serialization & SHA-256 Hash Chain Integrity  
**Subsystem Audited:** `atlas_mission_replay.py` and `atlas_mission_state.py`

---

## 1. Cryptographic State Hashing Formulation

State hashing computes a 256-bit cryptographic signature over the canonical operational state:
$$H_i = \text{SHA-256}\left( \text{JSON}_{\text{canonical}}(S_i) \right)$$

### Canonical Serialization Rules Enforced
1. **Key Sorting:** `sort_keys=True` ensures alphabetical dictionary ordering regardless of Python dict insertion history.
2. **Compact Separators:** `separators=(",", ":")` eliminates trailing space variability across OS platforms.
3. **Fixed Floating-Point Rounding:** Continuous variables are explicitly bounded:
   - Time / MET: `round(met_seconds, 2)`
   - Atmospheric dust: `round(atmospheric_dust_tau, 4)`
   - Surface / Interior temperature: `round(temp_k, 2)`
   - Power generation: `round(reactor_power_gross_kwe, 2)`
   - Consumable mass: `round(water_kg, 2)`, `round(oxygen_kg, 2)`
4. **Collection Normalization:** Task lists are deterministically sorted: `sorted(active_task_ids)`.

---

## 2. Replay Chain Continuity Verification

Every state snapshot records its predecessor's signature:
$$\text{Snapshot}_i = \{ \text{step\_index}: i, \text{state\_hash}: H_i, \text{prev\_state\_hash}: H_{i-1} \}$$

$$\text{Root Hash } R = \text{SHA-256}\left( H_0 \parallel H_1 \parallel \dots \parallel H_N \right)$$

The audit verified:
- [x] **Monotonicity:** $\text{step\_index}_i = i$ for all $i \in [0, N-1]$.
- [x] **Link Integrity:** $\text{Snapshot}_i.\text{prev\_state\_hash} == \text{Snapshot}_{i-1}.\text{state\_hash}$.
- [x] **Root Hash Match:** Bit-exact agreement between calculated and expected hash chains.

---

## 3. Empirical Determinism Experiment

The flagship campaign `ATLAS-MARS-BASE-ALPHA-001` was executed across multiple independent runs from pristine initial memory:

| Run Identifier | Configuration State | State Snapshots | Root Hash (SHA-256) | Verdict |
|:---|:---|:---:|:---:|:---:|
| **Run 1** | Pristine Flagship Configuration (120 kWe reactor, tau=0.45) | 62 | `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14` | **REFERENCE** |
| **Run 2** | Independent Relaunch (identical configuration) | 62 | `f9d124cfac3738ddb403be883ba273c2c9bc4af96b75f71a6ca66a96cb65bd14` | **BIT-EXACT MATCH** |
| **Run 3 (Perturbed)**| Single Perturbation (reactor throttled to 90 kWe) | 62 | `c34011dc536adcbb6562991b5440031919a5bb9dabb6fca1da4e11bd8981b53c` | **EXPLAINABLE DIVERGENCE** |

### Findings:
1. Two consecutive independent executions from identical configurations yielded **100% bit-exact identical hash signatures** across all 62 simulation steps.
2. Perturbing a single parameter (throttling reactor output by 30 kWe) produced a divergent, explainable root hash with zero unexplained state drift.
3. *Scientific Epistemology Caveat:* A matching cryptographic hash proves that the encoded simulation state is mathematically reproducible under the specified serialization. It does *not* prove that the simulation is an exact reflection of physical Mars reality.
