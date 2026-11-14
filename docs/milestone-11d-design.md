# MarsWalk 2.0 — Milestone 11D Design Specification
## Campaign What-If Simulation Lab & Scenario Comparison

**Milestone:** 11D (MarsWalk 2.0 V2)  
**Status:** DRAFT & DESIGN BASELINE  
**Date:** 2026-10-29  
**Target Environment:** Mars (IAU 2000 Sphere / USGS CTX DTM 20m Jezero Crater Topography)  

---

## 1. Objective & Operational Scope

The **Campaign What-If Simulation Lab** provides mission planners, flight directors, and science teams with an interactive, deterministic sandbox to evaluate how hypothetical operational disruptions, degraded vehicle capabilities, environmental constraints, and strategic priority shifts impact multi-sol campaign feasibility and science yield **before** deciding whether to promote a revised plan to active status.

### Guarantees & Non-Goals:
- **Deterministic Evaluation**: Calculations are strictly grounded in authentic USGS CTX 20m Jezero topography, physical locomotion models, and deterministic A* pathfinding.
- **No Probabilistic Fabrication**: Does not present deterministic what-if runs as probabilistic Monte Carlo failure rates or statistical hazard likelihoods.
- **Baseline Immutability**: Evaluating scenarios never mutates the baseline campaign, completed targets, recorded observations, or historical Black Box event ledgers.
- **Safe Version Promotion**: Promoting a scenario creates an explicit, versioned successor (`v{n+1}`), archiving all prior versions on disk.

---

## 2. Core Architecture & Scenario Types

### 2.1 Bounded Scenario Types

| Scenario Type | Key Parameters | Model Mechanism |
| :--- | :--- | :--- |
| `mobility_change` | `speed_factor` ($[0.1, 1.5]$), `max_slope_deg` ($[5.0, 25.0]$) | Derates travel velocity and adjusts slope hazard ceiling in A* cost function. |
| `target_loss` | `target_id` (string), `reason` (string) | Excludes specified target from candidate pool; severs downstream dependent prerequisites in topological DAG. |
| `corridor_closure` | `center_row`, `center_col`, `radius_m` ($[10.0, 500.0]$) | Reuses `compute_circular_footprint` to place geometric obstacle barrier on Jezero DTM, forcing deterministic detour routing. |
| `operational_delay` | `delay_s` ($[0, 14400]$), `sol_index` (optional) | Incorporates mandatory operational hold into sortie duration budget without double-counting dwell time. |
| `time_constraint` | `max_duration_per_sortie_s` ($[1800, 28800]$), `max_sols` ($[1, 10]$) | Contracts daily life-support or campaign sol window, causing low-priority targets to be deferred. |
| `objective_priority_change` | `objective_weights` (map of floats $[0.0, 3.0]$) | Rescales target priority scores to reflect modified high-level mission directives. |
| `combined` | Array of compatible modification records | Applies compound changes in deterministic precedence order, disclosing interactions. |

### 2.2 Execution Precedence Order for Combined Scenarios
To ensure deterministic reproducibility, multi-factor combined scenarios execute modifications in strict topological order:
1. `corridor_closure` (Establishes physical terrain obstacle masks)
2. `target_loss` (Removes unavailable objectives and prunes dependent branches)
3. `mobility_change` (Adjusts velocity and slope constraints)
4. `operational_delay` (Injects hold time requirements)
5. `time_constraint` (Enforces per-sol and campaign-wide duration ceilings)
6. `objective_priority_change` (Re-weights remaining candidate targets)

---

## 3. Data Models & Schemas

### 3.1 `CampaignScenario`
```python
@dataclass
class CampaignScenario:
    scenario_id: str
    campaign_id: str
    source_version: int
    name: str
    description: str
    scenario_type: str
    modifications: List[Dict[str, Any]]
    planning_profile: Optional[str] = None
    created_at_utc: str = ""
    status: str = "PENDING"  # PENDING, COMPLETED, INFEASIBLE, UNSUPPORTED, FAILED
    is_feasible: bool = False
    failure_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    comparison: Optional[ScenarioComparison] = None
    simulated_campaign: Optional[Dict[str, Any]] = None
    schema_version: str = "1.0.0"
    provenance: str = "DETERMINISTIC_WHAT_IF_SIMULATION"
```

### 3.2 `ScenarioComparison`
```python
@dataclass
class ScenarioComparison:
    delta_sols: int
    delta_sorties: int
    delta_distance_m: float
    delta_duration_s: float
    delta_science_score: float
    targets_scheduled_delta: int
    lost_target_ids: List[str]
    gained_target_ids: List[str]
    deferred_target_ids: List[str]
    blocked_target_ids: List[str]
    causal_attribution: Dict[str, str]
    feasibility_status: str
```

---

## 4. REST API Endpoints

- `POST /api/campaign/scenarios/evaluate`:
  - Request: `{ campaign_id: str, base_version: Optional[int], scenarios: List[ScenarioSpec] }`
  - Response: `{ campaign_id: str, base_version: int, results: List[CampaignScenario] }`
- `GET /api/campaign/scenarios?campaign_id=<id>`:
  - Response: `{ campaign_id: str, count: int, scenarios: List[CampaignScenario] }`
- `GET /api/campaign/scenarios/<scenario_id>`:
  - Response: `{ scenario: CampaignScenario }`
- `POST /api/campaign/scenarios/apply`:
  - Request: `{ campaign_id: str, scenario_id: str }`
  - Response: `{ campaign: MissionCampaign, applied_scenario_id: str, version: int }`

---

## 5. Atlas Web UI Integration

A dedicated **What-If Simulation Lab** panel will be added to the Campaign Orchestrator modal (`web/index.html` and `web/app.js`):
1. **Scenario Configurator**: Presets (Dust Storm Motor Derating, Rockfall Corridor Closure, Target Failure, Life-Support Limit) + Custom Parameter Adjusters.
2. **Batch Evaluation Runner**: Executes up to 10 scenarios in single-pass deterministic comparison.
3. **Multi-Scenario Comparison Matrix**: Side-by-side trade-off table displaying Sols, Distance, Time, Science Yield, Delta Targets, and Feasibility badges.
4. **Target Gain/Loss Inspector**: Visual breakdown of why targets were expedited, postponed, or unscheduled.
5. **Promotion Action**: One-click promotion of any feasible scenario into an official new campaign version.
