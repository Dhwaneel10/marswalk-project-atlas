# Distributed Science Task Allocation Methods
## Multi-Rover Target Prioritization & Instrument Compatibility Optimization

**Component:** `src/marswalk/core/fleet_task_allocator.py`  
**JSON Contract:** `schemas/api/v1/fleet-allocation.schema.json`  
**Target Catalog:** 12 Calibrated Jezero Science Targets (Hawksbill Gap, Skinner Ridge, Enchanted Lake, Belva Crater, etc.)

---

## 1. Problem Formulation

Given a fleet of heterogeneous planetary rovers $\mathcal{R} = \{r_1, r_2, \dots, r_m\}$ and a set of prioritized science targets $\mathcal{T} = \{t_1, t_2, \dots, t_n\}$, determine a binary assignment matrix $X \in \{0, 1\}^{m \times n}$ where $x_{ij} = 1$ if target $t_j$ is allocated to rover $r_i$.

### Constraints:
1. **Target Exclusivity:** Every science target is investigated at most once:
   $$\sum_{i=1}^m x_{ij} \le 1, \quad \forall j \in \{1, \dots, n\}$$
2. **Authoritative Instrument Compatibility:** A rover $r_i$ can only be assigned target $t_j$ if it carries an instrument capable of fulfilling $t_j$'s primary science objective:
   $$x_{ij} = 1 \implies \exists \text{inst} \in \mathcal{I}(r_i) \text{ s.t. } \text{Objective}(t_j) \in \text{Objectives}(\text{inst})$$
3. **Energy Margin Feasibility:** The estimated energy required for mobility, instrument operation, avionics, and data transmission must not exceed the rover's usable battery reserve:
   $$\sum_{j=1}^n x_{ij} E_{\text{op}}(r_i, t_j) + E_{\text{traverse}}(r_i) \le E_{\text{usable}}(r_i) \cdot (1 - \text{Margin}_{\text{reserve}})$$
4. **Onboard Memory Capacity:** Generated science data must not overflow local solid-state flash memory buffers before scheduled downlink passes:
   $$\sum_{j=1}^n x_{ij} D(t_j) - D_{\text{downlink}}(r_i) \le M_{\text{storage}}(r_i)$$

---

## 2. Objective Function: Science Utility Maximization

The fleet optimization objective balances science return against mobility costs and risk:

$$\max_{X} \quad \mathcal{U}_{\text{fleet}} = \sum_{i=1}^m \sum_{j=1}^n x_{ij} \left[ w_{\text{prio}} P(t_j) + w_{\text{util}} U_{\text{base}}(t_j) - w_{\text{dist}} \frac{d(r_i, t_j)}{d_{\text{max}}} - w_{\text{risk}} \mathcal{R}_{\text{terrain}}(r_i, t_j) \right]$$

Where:
- $P(t_j)$: Priority multiplier ($\text{CRITICAL} = 4.0, \text{HIGH} = 2.5, \text{NORMAL} = 1.5, \text{LOW} = 1.0$).
- $U_{\text{base}}(t_j)$: Calibrated scientific yield (points).
- $d(r_i, t_j)$: Estimated Euclidean / topographic ground traverse distance.
- $\mathcal{R}_{\text{terrain}}$: Slope and roughness hazard penalty along the direct traverse corridor.

---

## 3. Allocation Algorithms

Project Atlas provides two complementary allocation engines:

### Method A: Bounded Pareto Optimization (Recommended)
Performs branch-and-bound combinatorial optimization with feasibility pruning. Generates Pareto-optimal assignments across science yield, total traverse distance, and rover battery margins.
- **Pruning rule:** If assigning $t_j$ to $r_i$ breaches minimum reserve SOC ($20\%$), the entire subtree is eliminated.
- **Load balancing:** Enforces an entropy term that penalizes leaving an eligible rover idle while another rover is oversubscribed.

### Method B: Greedy Priority Allocation (Fast Baseline)
Sequentially iterates through targets sorted by priority $P(t_j) \times U_{\text{base}}(t_j)$. For each target, it identifies all compatible rovers, ranks them by proximity and current SOC margin, and assigns the target to the highest-scoring eligible vehicle.
- Runtimes are sub-millisecond ($<5\text{ ms}$).
- Serves as the quantitative benchmark for Pareto candidate evaluation.

---

## 4. Quantitative Audit Explanations

For full traceability, every target allocation produces a deterministic decision record:
```json
{
  "target_id": "TGT_HAWKSBILL_GAP",
  "assigned_rover_id": "ATLAS_ROVER_A",
  "selected_instrument": "PIXL",
  "score": 482.5,
  "competing_candidates": [
    { "rover_id": "ATLAS_ROVER_A", "eligible": true, "instrument": "PIXL", "score": 482.5 },
    { "rover_id": "ATLAS_ROVER_B", "eligible": false, "reason": "Lacks PIXL/SHERLOC for ELEMENTAL_CHEMISTRY" },
    { "rover_id": "ATLAS_ROVER_C", "eligible": true, "instrument": "SHERLOC", "score": 395.0 },
    { "rover_id": "ATLAS_ROVER_D", "eligible": false, "reason": "Lacks contact petrology spectrometer" }
  ],
  "exclusion_rationale": "Rover A selected over Rover C due to 34% shorter traverse and +87.5 pt PIXL micro-focus elemental yield."
}
```
This guarantees complete transparency for evaluators and science teams.
