# Project Atlas — Milestone 13X: Strategy Registry & Competitor Contracts

**Project:** MarsWalk 2.0 / Project Atlas  
**Milestone:** 13X — Atlas Mission Grand Prix  
**Module:** [`src/marswalk/core/atlas_strategy_registry.py`](file:///E:/Python/NASA-Spaceapps/Marswalk/src/marswalk/core/atlas_strategy_registry.py)  
**Status:** **IMPLEMENTED & VERIFIED**  

---

## 1. Overview & Information Gating Principles

The **Atlas Strategy Registry** provides a unified, strictly isolated planning interface for competing planetary mission optimization algorithms.

To ensure scientific fairness, every competing strategy adheres to strict **epistemic boundaries**:
1. **No Oracle Information:** A strategy receives only initial mission specifications, surveyed terrain, initial resource budgets, known asset parameters, and observable environmental conditions. Future hidden failure events (e.g., sudden dust storms, telemetry dropouts, battery cell faults) are not exposed to the strategy during upfront planning.
2. **Version Locking:** Strategies are version-locked (`v1.0.0`) with immutable hyperparameter declarations.
3. **Common State Gating:** Strategies execute on isolated copies of the `ScenarioPlanningContext`, preventing memory or variable leakage across competitors.

---

## 2. Standard Strategy Contracts

### 2.1 Inputs: `ScenarioPlanningContext`
```python
@dataclass
class ScenarioPlanningContext:
    scenario_id: str
    seed: int
    site_id: str
    mission_title: str
    duration_sols: int
    start_coord: Tuple[int, int]
    elevation_grid: np.ndarray          # 2D USGS DTM raster (meters)
    slope_grid: np.ndarray              # 2D Horn gradient raster (degrees)
    resolution_m: float                # Grid cell pitch (20.0 m)
    science_targets: List[Dict[str, Any]]
    fleet_assets: List[Dict[str, Any]]
    environmental_params: Dict[str, Any]
    comms_params: Dict[str, Any]
    resource_initial: Dict[str, Any]
    active_hypotheses: List[Dict[str, Any]]
```

### 2.2 Outputs: `StrategyPlan`
```python
@dataclass
class StrategyPlan:
    strategy_id: str
    version: str
    scenario_id: str
    selected_tasks: List[Dict[str, Any]]
    routes: Dict[str, List[Tuple[int, int]]]
    asset_assignments: Dict[str, List[str]]
    observation_schedule: List[Dict[str, Any]]
    resource_trajectory: List[Dict[str, float]]
    feasibility_status: str             # FEASIBLE, INFEASIBLE_ENERGY, INFEASIBLE_SLOPE, etc.
    constraint_evaluation: Dict[str, bool]
    planning_explanation: str
    causal_decisions: List[Dict[str, Any]]
    predicted_metrics: Dict[str, float]
    pareto_frontier: Optional[List[Dict[str, float]]]
    execution_time_ms: float
    plan_hash: str
```

---

## 3. The Six Foundational Competitors

| Strategy ID | Name | Algorithm Family | Primary Objective | Key Weakness / Risk |
|:---|:---|:---|:---|:---|
| `STRAT-01-GREEDY` | **Greedy Explorer** | `GREEDY_HEURISTIC` | Maximize immediate science yield per kilometer. | Short-term horizon creates energy starvation traps and poor multi-sol return paths. |
| `STRAT-02-MINCOST` | **Minimum-Cost Navigator** | `COST_MINIMIZATION` | Minimize travel distance, energy demand, and vehicle operations. | Overlooks valuable distant geological formations; lowest science return. |
| `STRAT-03-SCIENCE` | **Science-First Explorer** | `BAYESIAN_ACTIVE_LEARNING`| Maximize Shannon information gain ($IG = H(S) - H(S \mid Y)$) over competing hypotheses. | Aggressive power draw; pushes terrain slope limits near escarpments. |
| `STRAT-04-RESSAFE` | **Resource-Safe Planner** | `CONSERVATIVE_RESERVES` | Strictly maintain $\ge 40\%$ battery reserve and $\le 7^\circ$ slopes. | Rejects viable scientific sites; low overall mission achievement. |
| `STRAT-05-PARETO` | **Multi-Objective Optimizer** | `PARETO_NSGA2` | Extract non-dominated Pareto frontier across Science, Energy, Distance, and Risk. | Higher computational search time; requires trade-off preference selection. |
| `STRAT-06-ATLAS` | **Atlas Adaptive Director** | `INTEGRATED_MISSION_OS` | 7-Phase closed-loop Mission OS orchestration (DAG, fleet leasing, FDIR, ISRU). | Higher architectural overhead; must compete fairly without cheat flags. |

---

## 4. Verification

Unit tests in `tests/test_milestone_13x_grand_prix.py` verify that all 6 strategies:
- Successfully instantiate via `StrategyRegistry.create_all_competitors()`.
- Return fully populated `StrategyPlan` objects on identical contexts.
- Produce deterministic plan hashes for identical seeds.
- Adhere to exclusive asset leases and valid spatial coordinates.
