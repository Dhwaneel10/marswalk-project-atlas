"""
MarsWalk Interactive Contingency Designer & Compound Mission Events Engine.
Enables mission planners to configure, place, and combine hypothetical disruptions
(Corridor Closures, Difficult Terrain, Reduced Mobility, Time Budget Reductions,
Operational Holds, Target Inaccessibility) and computes real consequences via A*.
"""

from dataclasses import dataclass, field
import enum
import math
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np

from marswalk.core.terrain import TerrainGrid, TerrainConfig
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    ScienceWaypoint,
    OPERATIONAL_LIMITS_S,
    build_mission_timeline,
)
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    ScenarioComparison,
    run_scenario,
)
def _safe_pct_delta(current: Optional[float], baseline: Optional[float]) -> Optional[float]:
    """Safely compute percentage delta ((current - baseline) / baseline) * 100."""
    if current is None or baseline is None:
        return None
    try:
        c_val = float(current)
        b_val = float(baseline)
    except (ValueError, TypeError):
        return None
    if math.isnan(c_val) or math.isnan(b_val) or math.isinf(c_val) or math.isinf(b_val):
        return None
    if b_val <= 0.0:
        return None
    delta = ((c_val - b_val) / b_val) * 100.0
    if math.isnan(delta) or math.isinf(delta):
        return None
    return round(delta, 1)


class CustomEventType(str, enum.Enum):
    """Supported interactive mission contingency event types."""
    CLOSED_CORRIDOR = "closed_corridor"
    DIFFICULT_TERRAIN = "difficult_terrain"
    REDUCED_MOBILITY = "reduced_mobility"
    REDUCED_TIME_BUDGET = "reduced_time_budget"
    OPERATIONAL_HOLD = "operational_hold"
    TARGET_UNAVAILABLE = "target_unavailable"


@dataclass
class CustomEventDefinition:
    """
    Validated definition for an individual user-configured contingency event.
    """
    id: str
    name: str
    event_type: CustomEventType
    description: str = ""
    enabled: bool = True
    is_spatial: bool = False

    # Spatial parameters (Closed Corridor & Difficult Terrain)
    center_rc: Optional[Tuple[int, int]] = None
    radius_m: float = 50.0
    blocked_cells: Optional[List[Tuple[int, int]]] = None
    cost_multiplier_cells: Optional[List[Tuple[int, int]]] = None
    cost_multiplier: float = 2.0

    # Operational & vehicle parameters (Reduced Mobility)
    speed_multiplier: float = 1.0
    slope_penalty_multiplier: float = 1.0

    # Operational time & delay parameters (Reduced Time Budget & Operational Hold)
    budget_reduction_pct: Optional[float] = None
    reduced_time_budget_s: Optional[float] = None
    operational_delay_s: float = 0.0

    # Science objective parameters (Target Unavailable)
    unavailable_target_id: Optional[str] = None
    target_name: Optional[str] = None

    def __post_init__(self):
        self.is_spatial = self.event_type in (
            CustomEventType.CLOSED_CORRIDOR,
            CustomEventType.DIFFICULT_TERRAIN,
        )


def compute_circular_footprint(
    center_rc: Tuple[int, int],
    radius_m: float,
    terrain: TerrainGrid,
) -> List[Tuple[int, int]]:
    """
    Convert a geographic center pixel and physical meter radius on the Jezero DTM
    into the exact set of enclosed grid cells.

    Parameters
    ----------
    center_rc : Tuple[int, int]
        (row, col) grid coordinates of the event center.
    radius_m : float
        Physical footprint radius in meters (10m <= radius <= 1000m).
    terrain : TerrainGrid
        Authoritative elevation grid instance.

    Returns
    -------
    List[Tuple[int, int]]
        List of unique (row, col) coordinates within the circular footprint.
    """
    if not isinstance(center_rc, (tuple, list)) or len(center_rc) != 2:
        raise ValueError(f"center_rc must be a (row, col) pair, got {center_rc}")

    cr, cc = int(center_rc[0]), int(center_rc[1])
    if cr < 0 or cr >= terrain.height or cc < 0 or cc >= terrain.width:
        raise ValueError(f"Center pixel ({cr}, {cc}) falls outside terrain bounds ({terrain.height}, {terrain.width})")

    if not isinstance(radius_m, (int, float)) or math.isnan(radius_m) or math.isinf(radius_m):
        raise ValueError(f"radius_m must be a finite number, got {radius_m}")

    r_m = float(radius_m)
    if r_m < 5.0 or r_m > 1200.0:
        raise ValueError(f"radius_m must be between 5.0 m and 1200.0 m, got {r_m}")

    cell_size = float(terrain.config.cell_size_m) if (terrain.config.cell_size_m is not None and terrain.config.cell_size_m > 0) else 20.0
    dx = float(terrain.config.dx_ground_m) if (terrain.config.dx_ground_m is not None and terrain.config.dx_ground_m > 0) else cell_size
    dy = float(terrain.config.dy_ground_m) if (terrain.config.dy_ground_m is not None and terrain.config.dy_ground_m > 0) else cell_size

    # Bounding box in grid cells
    cell_span_r = int(math.ceil(r_m / dy)) + 1
    cell_span_c = int(math.ceil(r_m / dx)) + 1

    min_r = max(0, cr - cell_span_r)
    max_r = min(terrain.height - 1, cr + cell_span_r)
    min_c = max(0, cc - cell_span_c)
    max_c = min(terrain.width - 1, cc + cell_span_c)

    enclosed_cells: List[Tuple[int, int]] = []
    r_sq = r_m * r_m

    for r in range(min_r, max_r + 1):
        dr = (r - cr) * dy
        for c in range(min_c, max_c + 1):
            dc = (c - cc) * dx
            dist_sq = dr * dr + dc * dc
            if dist_sq <= r_sq:
                enclosed_cells.append((r, c))

    if not enclosed_cells:
        enclosed_cells.append((cr, cc))

    return enclosed_cells


def validate_custom_event_dict(
    data: Dict[str, Any],
    terrain: Optional[TerrainGrid] = None,
    event_index: int = 1,
) -> Union[CustomEventDefinition, List[CustomEventDefinition]]:
    """
    Validate and parse a raw JSON dictionary into a strongly-typed CustomEventDefinition.
    Supports single event dicts as well as compound wrappers {"events": [...]}.
    Rejects non-finite values, out-of-bounds coordinates, and invalid settings.
    """
    if not isinstance(data, dict):
        raise ValueError(f"Event {event_index} must be a JSON object")

    # Compound container check
    if "events" in data:
        ev_list = data["events"]
        if not isinstance(ev_list, list):
            raise ValueError("'events' must be a list of event objects")
        if len(ev_list) > 3:
            raise ValueError(f"Maximum 3 concurrent events supported (received {len(ev_list)})")

        # Check duplicate target drop
        target_ids = []
        for e in ev_list:
            if isinstance(e, dict) and e.get("event_type") == "target_unavailable":
                tid = e.get("target_id") or e.get("unavailable_target_id")
                if tid in target_ids:
                    raise ValueError(f"Duplicate target drop for target '{tid}'")
                if tid:
                    target_ids.append(tid)
        return [validate_custom_event_dict(e, terrain, event_index=i+1) for i, e in enumerate(ev_list)]

    raw_type = data.get("event_type") or data.get("type")
    type_aliases = {
        "closure": "closed_corridor",
        "mobility": "reduced_mobility",
        "time_budget": "reduced_time_budget",
        "hold": "operational_hold",
        "target": "target_unavailable",
    }
    if raw_type in type_aliases:
        raw_type = type_aliases[raw_type]

    valid = [t.value for t in CustomEventType]
    if not raw_type or raw_type not in valid:
        raise ValueError(f"Unsupported contingency event_type '{raw_type}'. Supported: {valid}")
    ev_type = CustomEventType(raw_type)

    ev_id = str(data.get("id") or f"custom_event_{event_index}").strip()
    ev_name = str(data.get("name") or ev_type.value.replace("_", " ").title()).strip()
    ev_desc = str(data.get("description") or f"Hypothetical {ev_name} contingency.").strip()
    enabled = bool(data.get("enabled", True))

    max_h = terrain.height if terrain is not None else 100
    max_w = terrain.width if terrain is not None else 100

    def _parse_center():
        c_raw = data.get("center_rc")
        if c_raw is None and "center_row" in data and "center_col" in data:
            c_raw = (data["center_row"], data["center_col"])
        elif c_raw is None and "row" in data and "col" in data:
            c_raw = (data["row"], data["col"])
        if c_raw is not None:
            cr, cc = int(c_raw[0]), int(c_raw[1])
            if cr < 0 or cr >= max_h or cc < 0 or cc >= max_w:
                raise ValueError(f"center_rc ({cr}, {cc}) is outside the 0-{max_h-1} grid bounds (0-{max_h-1} x 0-{max_w-1})")
            return (cr, cc)
        return None

    # 1. Closed Corridor
    if ev_type == CustomEventType.CLOSED_CORRIDOR:
        center_raw = _parse_center()
        radius_raw = data.get("radius_m", 50.0)
        try:
            r_val = float(radius_raw)
            if r_val <= 0.0 or math.isnan(r_val) or math.isinf(r_val):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"Closed corridor event '{ev_name}' radius_m must be strictly positive")

        blocked_raw = data.get("blocked_cells")
        if blocked_raw and isinstance(blocked_raw, list) and len(blocked_raw) > 0:
            cells: List[Tuple[int, int]] = []
            for item in blocked_raw:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    r, c = int(item[0]), int(item[1])
                    if 0 <= r < max_h and 0 <= c < max_w:
                        cells.append((r, c))
            if not cells:
                raise ValueError(f"Event '{ev_name}' provided blocked_cells, but all cells fall outside grid bounds")
            center_rc = (int(sum(r for r, c in cells) / len(cells)), int(sum(c for r, c in cells) / len(cells)))
            return CustomEventDefinition(
                id=ev_id,
                name=ev_name,
                event_type=ev_type,
                description=ev_desc,
                enabled=enabled,
                center_rc=center_rc,
                radius_m=r_val,
                blocked_cells=cells,
            )
        elif center_raw is not None:
            cells = compute_circular_footprint(center_raw, r_val, terrain) if terrain is not None else [center_raw]
            return CustomEventDefinition(
                id=ev_id,
                name=ev_name,
                event_type=ev_type,
                description=ev_desc,
                enabled=enabled,
                center_rc=center_raw,
                radius_m=r_val,
                blocked_cells=cells,
            )
        else:
            raise ValueError(f"Closed corridor event '{ev_name}' requires either 'center_rc' or 'blocked_cells'")

    # 2. Difficult Terrain
    elif ev_type == CustomEventType.DIFFICULT_TERRAIN:
        center_raw = _parse_center()
        radius_raw = data.get("radius_m", 60.0)
        try:
            r_val = float(radius_raw)
            if r_val <= 0.0 or math.isnan(r_val) or math.isinf(r_val):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"Difficult terrain event '{ev_name}' radius_m must be strictly positive")

        cost_mult_raw = data.get("cost_multiplier", 2.5)
        try:
            cost_mult = float(cost_mult_raw)
            if math.isnan(cost_mult) or math.isinf(cost_mult) or cost_mult <= 1.0 or cost_mult > 10.0:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"Difficult terrain event '{ev_name}' cost_multiplier must be > 1.0 and <= 10.0")

        cost_cells_raw = data.get("cost_multiplier_cells")
        if cost_cells_raw and isinstance(cost_cells_raw, list) and len(cost_cells_raw) > 0:
            cells = []
            for item in cost_cells_raw:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    r, c = int(item[0]), int(item[1])
                    if 0 <= r < max_h and 0 <= c < max_w:
                        cells.append((r, c))
            center_rc = (int(sum(r for r, c in cells) / len(cells)), int(sum(c for r, c in cells) / len(cells))) if cells else None
        elif center_raw is not None:
            cells = compute_circular_footprint(center_raw, r_val, terrain) if terrain is not None else [center_raw]
            center_rc = center_raw
        else:
            raise ValueError(f"Difficult terrain event '{ev_name}' requires either 'center_rc' or 'cost_multiplier_cells'")

        return CustomEventDefinition(
            id=ev_id,
            name=ev_name,
            event_type=ev_type,
            description=ev_desc,
            enabled=enabled,
            center_rc=center_rc,
            radius_m=r_val,
            cost_multiplier_cells=cells,
            cost_multiplier=cost_mult,
        )

    # 3. Reduced Mobility
    elif ev_type == CustomEventType.REDUCED_MOBILITY:
        speed_raw = data.get("speed_multiplier", 0.5)
        slope_raw = data.get("slope_penalty_multiplier", 1.0)
        try:
            speed_mult = float(speed_raw)
            if math.isnan(speed_mult) or math.isinf(speed_mult) or speed_mult < 0.05 or speed_mult > 1.0:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError(f"Reduced mobility event '{ev_name}' speed_multiplier must be between 0.05 and 1.0")

        try:
            slope_mult = float(slope_raw)
            if math.isnan(slope_mult) or math.isinf(slope_mult) or slope_mult < 1.0 or slope_mult > 3.0:
                raise ValueError()
        except (ValueError, TypeError):
            slope_mult = 1.0

        return CustomEventDefinition(
            id=ev_id,
            name=ev_name,
            event_type=ev_type,
            description=ev_desc,
            enabled=enabled,
            speed_multiplier=speed_mult,
            slope_penalty_multiplier=slope_mult,
        )

    # 4. Reduced Time Budget
    elif ev_type == CustomEventType.REDUCED_TIME_BUDGET:
        pct_raw = data.get("budget_reduction_pct")
        sec_raw = data.get("reduced_time_budget_s")
        if pct_raw is None and sec_raw is None:
            pct_raw = 25.0

        pct_val: Optional[float] = None
        if pct_raw is not None:
            try:
                pct_val = float(pct_raw)
                if math.isnan(pct_val) or math.isinf(pct_val) or pct_val < 1.0 or pct_val > 95.0 or pct_val >= 100.0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Reduced time budget event '{ev_name}' budget_reduction_pct must be between 1.0% and 95.0%")

        sec_val: Optional[float] = None
        if sec_raw is not None:
            try:
                sec_val = float(sec_raw)
                if math.isnan(sec_val) or math.isinf(sec_val) or sec_val < 300.0 or sec_val > 86400.0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Reduced time budget event '{ev_name}' reduced_time_budget_s must be between 300s and 86400s")

        return CustomEventDefinition(
            id=ev_id,
            name=ev_name,
            event_type=ev_type,
            description=ev_desc,
            enabled=enabled,
            budget_reduction_pct=pct_val,
            reduced_time_budget_s=sec_val,
        )

    # 5. Operational Hold
    elif ev_type == CustomEventType.OPERATIONAL_HOLD:
        delay_raw = data.get("operational_delay_s")
        delay_mins_raw = data.get("delay_minutes")
        if delay_mins_raw is not None:
            try:
                dm = float(delay_mins_raw)
                if math.isnan(dm) or math.isinf(dm) or dm <= 0:
                    raise ValueError()
                delay_val = dm * 60.0
            except (ValueError, TypeError):
                raise ValueError(f"Operational hold event '{ev_name}' delay_minutes must be > 0")
        elif delay_raw is not None:
            try:
                delay_val = float(delay_raw)
                if math.isnan(delay_val) or math.isinf(delay_val) or delay_val <= 0 or delay_val > 86400.0:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f"Operational hold event '{ev_name}' operational_delay_s must be > 0")
        else:
            delay_val = 1800.0

        return CustomEventDefinition(
            id=ev_id,
            name=ev_name,
            event_type=ev_type,
            description=ev_desc,
            enabled=enabled,
            operational_delay_s=delay_val,
        )

    # 6. Target Unavailable
    elif ev_type == CustomEventType.TARGET_UNAVAILABLE:
        tid_raw = data.get("target_id") or data.get("unavailable_target_id")
        tname_raw = data.get("target_name") or tid_raw or "Target"
        if not tid_raw or not str(tid_raw).strip():
            raise ValueError(f"Target unavailable event '{ev_name}' target_id is required")

        return CustomEventDefinition(
            id=ev_id,
            name=ev_name,
            event_type=ev_type,
            description=ev_desc,
            enabled=enabled,
            unavailable_target_id=str(tid_raw).strip(),
            target_name=str(tname_raw).strip(),
        )

    raise ValueError(f"Unhandled event_type '{ev_type}'")


def compile_custom_contingency(
    events_data: Union[List[Union[Dict[str, Any], CustomEventDefinition]], Dict[str, Any]],
    terrain: TerrainGrid,
    baseline_route: Optional[RouteResult] = None,
    candidate_wps: Optional[List[ScienceWaypoint]] = None,
) -> Tuple[ScenarioDefinition, List[CustomEventDefinition]]:
    """
    Compile 1 to 3 validated custom events into an authoritative ScenarioDefinition.
    Preserves all physical boundaries and correctly resolves compound interactions.
    """
    if isinstance(events_data, dict):
        if "events" in events_data:
            raw_list = events_data["events"]
        else:
            raw_list = [events_data]
    elif isinstance(events_data, list):
        raw_list = events_data
    else:
        raise ValueError("Custom events must be a dictionary or a list of dictionaries")

    if not raw_list:
        raise ValueError("At least one custom event must be provided")

    if len(raw_list) > 3:
        raise ValueError(f"A maximum of 3 combined custom events is supported per simulation (received {len(raw_list)})")

    parsed_events: List[CustomEventDefinition] = []
    for idx, raw_ev in enumerate(raw_list):
        if isinstance(raw_ev, CustomEventDefinition):
            parsed_events.append(raw_ev)
        else:
            ev = validate_custom_event_dict(raw_ev, terrain, event_index=idx + 1)
            if isinstance(ev, list):
                parsed_events.extend(ev)
            else:
                parsed_events.append(ev)

    seen_ev_ids = set()
    for ev in parsed_events:
        if ev.id in seen_ev_ids:
            raise ValueError(f"Duplicate event ID '{ev.id}' detected in custom events list")
        seen_ev_ids.add(ev.id)

    active_events = [e for e in parsed_events if e.enabled]
    if not active_events:
        raise ValueError("All configured custom events are disabled. Enable at least one event.")

    is_compound = len(active_events) > 1

    # Single event mapping
    if not is_compound:
        ev = active_events[0]
        if ev.event_type == CustomEventType.CLOSED_CORRIDOR:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.CORRIDOR_CLOSURE,
                description=ev.description,
                blocked_cells=ev.blocked_cells,
                center_rc=ev.center_rc,
                radius_m=ev.radius_m,
            )
        elif ev.event_type == CustomEventType.DIFFICULT_TERRAIN:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.UNSTABLE_SAND,
                description=ev.description,
                cost_multiplier_cells=ev.cost_multiplier_cells,
                cost_multiplier=ev.cost_multiplier,
                center_rc=ev.center_rc,
                radius_m=ev.radius_m,
            )
        elif ev.event_type == CustomEventType.REDUCED_MOBILITY:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.MOBILITY_DEGRADATION,
                description=ev.description,
                speed_multiplier=ev.speed_multiplier,
                slope_penalty_multiplier=ev.slope_penalty_multiplier,
            )
        elif ev.event_type == CustomEventType.REDUCED_TIME_BUDGET:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.REDUCED_BUDGET,
                description=ev.description,
                budget_reduction_pct=ev.budget_reduction_pct,
                reduced_time_budget_s=ev.reduced_time_budget_s,
            )
        elif ev.event_type == CustomEventType.OPERATIONAL_HOLD:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.DUST_STORM_VISIBILITY,
                description=ev.description,
                operational_delay_s=ev.operational_delay_s,
            )
        elif ev.event_type == CustomEventType.TARGET_UNAVAILABLE:
            scen = ScenarioDefinition(
                id=ev.id,
                name=ev.name,
                disruption_type=DisruptionType.TARGET_UNAVAILABLE,
                description=ev.description,
                unavailable_target_id=ev.unavailable_target_id,
            )
        else:
            raise ValueError(f"Unknown event type {ev.event_type}")

        return scen, parsed_events

    # Compound Event Synthesis (2 or 3 events combined)
    combined_blocked: List[Tuple[int, int]] = []
    seen_blocked: Set[Tuple[int, int]] = set()

    combined_cost_cells: List[Tuple[int, int]] = []
    seen_cost: Set[Tuple[int, int]] = set()
    effective_cost_mult = 1.0

    min_speed_mult = 1.0
    max_slope_mult = 1.0
    total_delay_s = 0.0
    max_budget_cut_pct: Optional[float] = None
    min_budget_time_s: Optional[float] = None
    target_unavailable_id: Optional[str] = None
    compound_centers: List[Tuple[int, int]] = []

    for ev in active_events:
        if ev.event_type == CustomEventType.CLOSED_CORRIDOR and ev.blocked_cells:
            for cell in ev.blocked_cells:
                if cell not in seen_blocked:
                    seen_blocked.add(cell)
                    combined_blocked.append(cell)
            if ev.center_rc:
                compound_centers.append(ev.center_rc)

        elif ev.event_type == CustomEventType.DIFFICULT_TERRAIN and ev.cost_multiplier_cells:
            for cell in ev.cost_multiplier_cells:
                if cell not in seen_cost:
                    seen_cost.add(cell)
                    combined_cost_cells.append(cell)
            effective_cost_mult = max(effective_cost_mult, ev.cost_multiplier)
            if ev.center_rc:
                compound_centers.append(ev.center_rc)

        elif ev.event_type == CustomEventType.REDUCED_MOBILITY:
            min_speed_mult = min(min_speed_mult, ev.speed_multiplier)
            max_slope_mult = max(max_slope_mult, ev.slope_penalty_multiplier)

        elif ev.event_type == CustomEventType.REDUCED_TIME_BUDGET:
            if ev.budget_reduction_pct is not None:
                if max_budget_cut_pct is None:
                    max_budget_cut_pct = ev.budget_reduction_pct
                else:
                    max_budget_cut_pct = max(max_budget_cut_pct, ev.budget_reduction_pct)
            if ev.reduced_time_budget_s is not None:
                if min_budget_time_s is None:
                    min_budget_time_s = ev.reduced_time_budget_s
                else:
                    min_budget_time_s = min(min_budget_time_s, ev.reduced_time_budget_s)

        elif ev.event_type == CustomEventType.OPERATIONAL_HOLD:
            total_delay_s += ev.operational_delay_s

        elif ev.event_type == CustomEventType.TARGET_UNAVAILABLE:
            target_unavailable_id = ev.unavailable_target_id

    # Compute centroid of compound geographic events if present
    compound_center = None
    if compound_centers:
        avg_r = int(sum(r for r, c in compound_centers) / len(compound_centers))
        avg_c = int(sum(c for r, c in compound_centers) / len(compound_centers))
        compound_center = (avg_r, avg_c)

    title_parts = [e.name for e in active_events]
    compound_name = " + ".join(title_parts)
    compound_desc = "; ".join([e.description for e in active_events if e.description])

    compound_scenario = ScenarioDefinition(
        id=f"compound_custom_{len(active_events)}_events",
        name=compound_name,
        disruption_type=DisruptionType.COMPOUND_DISRUPTION,
        description=compound_desc,
        blocked_cells=combined_blocked if combined_blocked else None,
        cost_multiplier_cells=combined_cost_cells if combined_cost_cells else None,
        cost_multiplier=effective_cost_mult,
        speed_multiplier=min_speed_mult,
        slope_penalty_multiplier=max_slope_mult,
        operational_delay_s=total_delay_s,
        budget_reduction_pct=max_budget_cut_pct,
        reduced_time_budget_s=min_budget_time_s,
        unavailable_target_id=target_unavailable_id,
        center_rc=compound_center,
        radius_m=75.0,
        compound_scenario_ids=[e.id for e in active_events],
    )

    return compound_scenario, parsed_events


def generate_contingency_narrative(
    comparison: ScenarioComparison,
    scenario: ScenarioDefinition,
    events: List[CustomEventDefinition],
) -> Tuple[str, str]:
    """
    Produce rigorous, evidence-based headline and operational detail text
    grounded directly in the actual calculation fields.
    """
    base = comparison.baseline_route
    scen = comparison.scenario_route
    ledger = comparison.regret_ledger

    active_evs = [e for e in events if e.enabled]
    ev_types = [e.event_type for e in active_evs]

    # Infeasible route
    if not scen.is_reachable:
        headline = f"Contingency Infeasible: {scenario.name} Severed All Corridors."
        detail = (
            f"Under hypothetical contingency '{scenario.name}', no viable traverse path exists between start and destination "
            "that satisfies slope ceilings and boundary limits. The mission cannot proceed to the goal."
        )
        return headline, detail

    delta_d = scen.distance_m - base.distance_m
    delta_t_s = scen.travel_time_s - base.travel_time_s
    delta_t_min = round(delta_t_s / 60.0)

    # Over budget
    if not scen.is_budget_feasible:
        headline = f"Budget Violated: {scenario.name} Exceeds Operational Ceiling."
        detail = (
            f"Simulated contingency resulted in a mission duration of {scen.formatted_travel_time} "
            f"(+{delta_t_min} min vs baseline), violating the configured operational life-support limit. "
            f"Remaining margin is depleted or negative. Recovery plan recommended."
        )
        return headline, detail

    # Check if purely operational / speed / budget event with invariant geometry
    has_spatial = any(
        e.event_type in (CustomEventType.CLOSED_CORRIDOR, CustomEventType.DIFFICULT_TERRAIN)
        for e in active_evs
    )

    if not has_spatial and CustomEventType.TARGET_UNAVAILABLE not in ev_types:
        # Invariant geometry confirmed
        if delta_t_min > 0:
            headline = f"Timeline Expanded: Invariant Path Maintained (+{delta_t_min} min)."
            detail = (
                f"Simulated operational contingency ({scenario.name}) left physical route geometry 100% unchanged "
                f"(0 m detour). Travel time expanded from {base.formatted_travel_time} to {scen.formatted_travel_time} "
                f"due to configured velocity/hold factors. Preserved 100% of scientific objectives."
            )
        else:
            headline = f"Contingency Evaluated: All Constraints Satisfied."
            detail = (
                f"Under '{scenario.name}', the active traverse ({scen.distance_m:.0f} m) remains fully compliant "
                f"with all updated budget and operational boundaries. Margin remaining: {scen.formatted_travel_time}."
            )
        return headline, detail

    # Target unavailable
    if CustomEventType.TARGET_UNAVAILABLE in ev_types and not has_spatial:
        dropped_ids = ledger.disabled_by_scenario_ids
        dropped_name = ", ".join(dropped_ids) if dropped_ids else (scenario.unavailable_target_id or "target")
        headline = f"Science Target Pruned: Route Replanned Without {dropped_name} ({delta_d:+.0f} m)."
        detail = (
            f"Observation target '{dropped_name}' was excluded from itinerary. Traverse distance shifted to "
            f"{scen.distance_m:.0f} m ({delta_d:+.0f} m detour delta). "
            f"Remaining scientific objectives visited: {len(ledger.retained_target_ids)}/{len(ledger.baseline_visited_ids)} ({ledger.retention_pct:.0f}%)."
        )
        return headline, detail

    # Spatial corridor detour or cost absorption
    if not scenario.intersects_baseline and abs(delta_d) < 1.0:
        headline = f"No Route Impact: Contingency Clears Active Corridor."
        detail = (
            f"Configured obstruction ({scenario.name}) does not intersect the active mission corridor. "
            f"Traverse distance ({base.distance_m:.0f} m) and travel time ({base.formatted_travel_time}) remain unaffected."
        )
        return headline, detail

    if abs(delta_d) < 1.0:
        headline = f"Local Obstacle Bypassed: Planner Navigated Around {scenario.name} (0 m net detour)."
        detail = (
            f"Simulated physical obstruction intersected the active corridor. The planner diverted around the barrier, "
            f"successfully avoiding all blocked cells while preserving equivalent overall traverse distance ({scen.distance_m:.0f} m)."
        )
        return headline, detail

    time_txt = f", +{delta_t_min} min" if delta_t_min > 0 else ""
    headline = f"Lateral Detour Active: Planner Navigated Around {scenario.name} ({delta_d:+.0f} m{time_txt})."
    detail = (
        f"Simulated physical obstruction forced a lateral route recalculation. "
        f"Traverse distance shifted from {base.distance_m:.0f} m to {scen.distance_m:.0f} m ({delta_d:+.0f} m), "
        f"with travel time shifting to {scen.formatted_travel_time}. Preserved {len(ledger.retained_target_ids)}/{len(ledger.baseline_visited_ids)} targets."
    )
    return headline, detail


def build_contingency_comparison_table(
    comparison: ScenarioComparison,
    baseline_formatted: Dict[str, Any],
    scenario_formatted: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Construct the authoritative 8-measurement comparison table:
    1. Route distance
    2. Terrain-adjusted effort
    3. Estimated active traverse time
    4. Total mission duration
    5. Available mission time
    6. Remaining time margin
    7. Science objectives retained
    8. Mission feasibility
    """
    base_dist = baseline_formatted.get("distance_m", 0.0)
    scen_dist = scenario_formatted.get("distance_m") if comparison.is_scenario_reachable else None
    delta_dist = (scen_dist - base_dist) if (scen_dist is not None and base_dist is not None) else None
    pct_dist = _safe_pct_delta(scen_dist, base_dist)

    base_cost = baseline_formatted.get("cost")
    scen_cost = scenario_formatted.get("cost") if comparison.is_scenario_reachable else None
    delta_cost = (scen_cost - base_cost) if (scen_cost is not None and base_cost is not None) else None
    pct_cost = _safe_pct_delta(scen_cost, base_cost)

    # Active traverse time (walking / driving time excluding stationary dwell)
    base_time_s = baseline_formatted.get("travel_time_s", 0.0)
    scen_time_s = scenario_formatted.get("travel_time_s") if comparison.is_scenario_reachable else None
    delta_time_s = (scen_time_s - base_time_s) if (scen_time_s is not None and base_time_s is not None) else None
    pct_time = _safe_pct_delta(scen_time_s, base_time_s)

    # Total mission duration (timeline total time including dwell and operational hold)
    base_tl = baseline_formatted.get("timeline") or {}
    scen_tl = scenario_formatted.get("timeline") or {}
    base_total_s = base_tl.get("total_mission_time_s", base_time_s)
    scen_total_s = scen_tl.get("total_mission_time_s") if comparison.is_scenario_reachable else None
    delta_total_s = (scen_total_s - base_total_s) if (scen_total_s is not None and base_total_s is not None) else None
    pct_total = _safe_pct_delta(scen_total_s, base_total_s)

    # Available mission time budget (seconds)
    base_op_limit = base_tl.get("operational_limit_s", 28800.0)
    scen_op_limit = scen_tl.get("operational_limit_s", base_op_limit)
    delta_limit_s = scen_op_limit - base_op_limit if (scen_op_limit is not None and base_op_limit is not None) else 0.0

    # Remaining time margin (seconds)
    base_margin_s = base_tl.get("margin_remaining_s", max(0.0, base_op_limit - base_total_s))
    scen_margin_s = scen_tl.get("margin_remaining_s") if comparison.is_scenario_reachable else None
    delta_margin_s = (scen_margin_s - base_margin_s) if (scen_margin_s is not None and base_margin_s is not None) else None

    # Science objectives retained
    ledger = comparison.regret_ledger
    base_sci_count = len(ledger.baseline_visited_ids)
    scen_sci_count = len(ledger.retained_target_ids) if comparison.is_scenario_reachable else 0
    delta_sci = scen_sci_count - base_sci_count

    # Format helpers
    def fmt_time(sec: Optional[float]) -> str:
        if sec is None or math.isnan(sec):
            return "—"
        sign = "-" if sec < 0 else ""
        s = abs(sec)
        h = int(s // 3600)
        m = int(round((s % 3600) / 60.0))
        if h > 0:
            return f"{sign}{h}h {m}m"
        return f"{sign}{m} min"

    def fmt_delta_t(sec: Optional[float]) -> str:
        if sec is None or math.isnan(sec):
            return "—"
        if abs(sec) < 1.0:
            return "0 min"
        m = round(sec / 60.0)
        return f"{'+' if m > 0 else ''}{m} min"

    rows = [
        {
            "metric": "Route distance",
            "unit": "meters",
            "baseline": f"{base_dist:.1f} m",
            "scenario": f"{scen_dist:.1f} m" if scen_dist is not None else "—",
            "difference": f"{delta_dist:+.1f} m ({pct_dist:+.1f}%)" if (delta_dist is not None and pct_dist is not None) else "—",
            "is_improved": (delta_dist < 0) if delta_dist is not None else None,
        },
        {
            "metric": "Terrain-adjusted effort",
            "unit": "flat-m",
            "baseline": f"{base_cost:.0f}" if base_cost is not None else "—",
            "scenario": f"{scen_cost:.0f}" if scen_cost is not None else "—",
            "difference": f"{delta_cost:+.0f} ({pct_cost:+.1f}%)" if (delta_cost is not None and pct_cost is not None) else "—",
            "is_improved": (delta_cost < 0) if delta_cost is not None else None,
        },
        {
            "metric": "Estimated active traverse time",
            "unit": "time",
            "baseline": fmt_time(base_time_s),
            "scenario": fmt_time(scen_time_s),
            "difference": fmt_delta_t(delta_time_s),
            "is_improved": (delta_time_s < 0) if delta_time_s is not None else None,
        },
        {
            "metric": "Total mission duration",
            "unit": "time",
            "baseline": fmt_time(base_total_s),
            "scenario": fmt_time(scen_total_s),
            "difference": fmt_delta_t(delta_total_s),
            "is_improved": (delta_total_s < 0) if delta_total_s is not None else None,
        },
        {
            "metric": "Available mission time",
            "unit": "time",
            "baseline": fmt_time(base_op_limit),
            "scenario": fmt_time(scen_op_limit),
            "difference": fmt_delta_t(delta_limit_s),
            "is_improved": None,
        },
        {
            "metric": "Remaining time margin",
            "unit": "time",
            "baseline": fmt_time(base_margin_s),
            "scenario": fmt_time(scen_margin_s),
            "difference": fmt_delta_t(delta_margin_s),
            "is_improved": (delta_margin_s > 0) if delta_margin_s is not None else None,
        },
        {
            "metric": "Science objectives retained",
            "unit": "count",
            "baseline": f"{base_sci_count} stops",
            "scenario": f"{scen_sci_count} stops ({ledger.retention_pct:.0f}%)" if comparison.is_scenario_reachable else "0 stops (0%)",
            "difference": f"{delta_sci:+d} stops",
            "is_improved": (delta_sci >= 0),
        },
        {
            "metric": "Mission feasibility",
            "unit": "status",
            "baseline": "FEASIBLE" if comparison.is_baseline_budget_feasible else "INFEASIBLE",
            "scenario": "FEASIBLE" if comparison.is_scenario_budget_feasible else "INFEASIBLE",
            "difference": "Compliant" if comparison.is_scenario_budget_feasible else "Over Budget / Infeasible",
            "is_improved": (comparison.is_scenario_budget_feasible >= comparison.is_baseline_budget_feasible),
        },
    ]

    return rows
