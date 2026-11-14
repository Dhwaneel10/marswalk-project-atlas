"""
MarsWalk 2.0 — Canonical API Data Contracts, Fingerprinting, and Schema Validation Engine.
Enforces JSON Schema Draft 2020-12 compliance across planner, simulation, API, and briefings.
Preserves strict RFC 8259 compliance, safe zero-baseline deltas, and backward compatibility.
"""

import os
import json
import math
import hashlib
from typing import Dict, Any, List, Tuple, Optional
import jsonschema
import rasterio

from marswalk.core.terrain import TerrainGrid

SCHEMA_VERSION = "1.0.0"

# Processed local raster (Jezero Western Delta 250x250, 20m/px, 5km x 5km)
TERRAIN_DATASET_ID = "USGS_CTX_DTM_JEZERO_20M"
TERRAIN_SHA256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"
PROCESSED_TERRAIN_DATASET_ID = "USGS_CTX_DTM_JEZERO_20M"
PROCESSED_TERRAIN_SHA256 = "875e7e80c170b84e4b2a3dd650b12abbee289e6d3fae5664e4d3cb93e9a1f5b3"

# Raw USGS source product (Mars 2020 TRN CTX DTM Mosaic, Fergason et al. 2020)
RAW_TERRAIN_DATASET_ID = "USGS_MARS2020_TRN_CTX_DTM_MOSAIC"
RAW_TERRAIN_DOI = "10.5066/P906QQT8"
RAW_TERRAIN_SHA256 = "16a1aa66c3f48c1bca252795827db7b417876217aff0f5e1aff18027fab2327b"

# Directory containing versioned JSON schemas
SCHEMAS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "schemas", "api", "v1")
)

# Schema file mapping
SCHEMA_FILE_MAP = {
    "mission-request": "mission-request.schema.json",
    "mission-snapshot": "mission-snapshot.schema.json",
    "route-result": "route-result.schema.json",
    "scenario-comparison-request": "scenario-comparison-request.schema.json",
    "scenario-comparison-response": "scenario-comparison-response.schema.json",
    "scenario-sensitivity-request": "scenario-sensitivity-request.schema.json",
    "scenario-sensitivity-response": "scenario-sensitivity-response.schema.json",
    "mission-briefing-export": "mission-briefing-export.schema.json",
    "mission-run-bundle": "mission-run-bundle.schema.json",
    "api-error": "api-error.schema.json",
    "saved-mission": "saved-mission.schema.json",
    "saved-experiment": "saved-experiment.schema.json",
    "experiment-comparison-request": "experiment-comparison-request.schema.json",
    "experiment-comparison-response": "experiment-comparison-response.schema.json",
    "mission-robustness-response": "mission-robustness-response.schema.json",
    "route-explanation-response": "route-explanation-response.schema.json",
    "mission-playback-response": "mission-playback-response.schema.json",
    "mission-continue-response": "mission-continue-response.schema.json",
    "mission-event": "mission-event.schema.json",
    "incident-replay-response": "incident-replay-response.schema.json",
    "weather-report": "weather-report.schema.json",
    "mission-science-report": "mission-science-report.schema.json",
    "mission-readiness-assessment": "mission-readiness-assessment.schema.json",
    "mission-campaign": "mission-campaign.schema.json",
    "science-observation": "science-observation.schema.json",
    "campaign-progress-event": "campaign-progress-event.schema.json",
    "campaign-reprioritization": "campaign-reprioritization.schema.json",
    "campaign-scenario": "campaign-scenario.schema.json",
    "campaign-coordination": "campaign-coordination.schema.json",
    "campaign-simulation": "campaign-simulation.schema.json",
    "campaign-analytics": "campaign-analytics.schema.json",
    "campaign-design-space": "campaign-design-space.schema.json",
    "campaign-benchmark": "campaign-benchmark.schema.json",
    "route-terrain-analysis": "route-terrain-analysis.schema.json",
    "mission-robustness-experiment": "mission-robustness-experiment.json",
    "mission-rehearsal": "mission-rehearsal.schema.json",
    "mission-experiment": "mission-experiment.schema.json",
    "campaign-operations": "campaign-operations.schema.json",
    "campaign-operations-event": "campaign-operations-event.schema.json",
    "mission-assurance": "mission-assurance.schema.json",
    "campaign-branch": "campaign-branch.schema.json",
    "counterfactual-scenario": "counterfactual-scenario.schema.json",
    "campaign-robustness": "campaign-robustness.schema.json",
    "fleet-configuration": "fleet-configuration.schema.json",
    "fleet-state": "fleet-state.schema.json",
    "fleet-allocation": "fleet-allocation.schema.json",
    "fleet-route": "fleet-route.schema.json",
    "fleet-schedule": "fleet-schedule.schema.json",
    "fleet-network": "fleet-network.schema.json",
    "fleet-resources": "fleet-resources.schema.json",
    "fleet-optimization": "fleet-optimization.schema.json",
    "fleet-scenario": "fleet-scenario.schema.json",
    "fleet-assurance": "fleet-assurance.schema.json",
    "mission-intent": "mission-intent.schema.json",
    "mission-intent-validation": "mission-intent-validation.schema.json",
    "mission-task-graph": "mission-task-graph.schema.json",
    "mission-plan-candidate": "mission-plan-candidate.schema.json",
    "mission-plan-compilation": "mission-plan-compilation.schema.json",
    "mission-constraint-diagnosis": "mission-constraint-diagnosis.schema.json",
    "environmental-catalog": "environmental-catalog.schema.json",
    "environmental-solar": "environmental-solar.schema.json",
    "environmental-point-eval": "environmental-point-eval.schema.json",
    "environmental-scenario": "environmental-scenario.schema.json",
    "environmental-window": "environmental-window.schema.json",
    "environmental-ingestion-manifest": "environmental-ingestion-manifest.schema.json",
    "environmental-collocation": "environmental-collocation.schema.json",
    "environmental-model-evaluation": "environmental-model-evaluation.schema.json",
    "environmental-calibration": "environmental-calibration.schema.json",
    "environmental-experiment": "environmental-experiment.schema.json",
    "environmental-tribunal-audit": "environmental-tribunal-audit.schema.json",
    "deep-space-autonomy": "deep-space-autonomy.schema.json",
    "aerial-corps": "aerial-corps.schema.json",
    "science-discovery": "science-discovery.schema.json",
    "mission-resilience": "mission-resilience.schema.json",
    "settlement-engine": "settlement-engine.schema.json",
    "mission-os": "mission-os.schema.json",
}

# Validator cache
_VALIDATOR_CACHE: Dict[str, jsonschema.Draft202012Validator] = {}


class ContractValidationError(Exception):
    """Raised when an API payload fails JSON Schema contract validation."""

    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None, schema_name: str = ""):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
        self.schema_name = schema_name


def get_validator(schema_name: str) -> jsonschema.Draft202012Validator:
    """Load, compile, and cache a Draft 2020-12 validator for the given schema key."""
    if schema_name in _VALIDATOR_CACHE:
        return _VALIDATOR_CACHE[schema_name]

    filename = SCHEMA_FILE_MAP.get(schema_name)
    if not filename:
        raise ValueError(f"Unknown schema name '{schema_name}'. Known schemas: {list(SCHEMA_FILE_MAP.keys())}")

    schema_path = os.path.join(SCHEMAS_DIR, filename)
    if not os.path.isfile(schema_path):
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_dict = json.load(f)

    validator = jsonschema.Draft202012Validator(schema_dict)
    _VALIDATOR_CACHE[schema_name] = validator
    return validator


def validate_contract(
    data: Dict[str, Any],
    schema_name: str,
    raise_on_error: bool = False,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validate a dictionary against the named JSON schema.
    Returns (is_valid, list_of_error_dicts).
    If raise_on_error is True, raises ContractValidationError on failure.
    """
    validator = get_validator(schema_name)
    errors: List[Dict[str, Any]] = []

    # Use iter_errors for full report
    for err in sorted(validator.iter_errors(data), key=lambda e: str(e.path)):
        field_path = ".".join(str(p) for p in err.path) if err.path else "root"
        errors.append({
            "field": field_path,
            "issue": err.message,
            "value": err.instance if not isinstance(err.instance, (dict, list)) else f"<{type(err.instance).__name__}>",
        })

    is_valid = len(errors) == 0
    if not is_valid and raise_on_error:
        first_msg = errors[0]["issue"] if errors else "Contract validation failed"
        raise ContractValidationError(
            f"Validation failed against schema '{schema_name}': {first_msg}",
            errors=errors,
            schema_name=schema_name,
        )

    return is_valid, errors


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize data structures for strict RFC 8259 JSON compliance.
    Converts float NaN, Infinity, -Infinity to None (null).
    Preserves booleans, integers, valid floats, strings, lists, and dicts.
    """
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    return obj


def calculate_safe_pct_delta(
    current: Optional[float],
    baseline: Optional[float],
) -> Optional[float]:
    """
    Safely compute percentage delta ((current - baseline) / baseline) * 100.
    Returns None (JSON null) if:
      - baseline is None, 0, or non-finite
      - current is None or non-finite
    Guarantees that 0-baseline or unreachable missions never yield NaN, Infinity, or 0.0% artifact.
    """
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


def compute_input_fingerprint(
    mission_data: Dict[str, Any],
    dataset_id: str = TERRAIN_DATASET_ID,
) -> str:
    """
    Compute a deterministic SHA-256 hex hash from canonical mission inputs.
    Excludes ephemeral fields (timestamps, client request IDs, render options).
    Guarantees:
      - Changing start, goal, stops, profile, vehicle mode, or constraints alters the fingerprint.
      - Identical mission parameters always produce the exact same fingerprint.
    """
    # Canonical start
    start_obj = mission_data.get("start", {})
    start_r = int(start_obj.get("row", 0))
    start_c = int(start_obj.get("col", 0))

    # Canonical goal
    goal_obj = mission_data.get("goal", {})
    goal_r = int(goal_obj.get("row", 0))
    goal_c = int(goal_obj.get("col", 0))

    # Canonical stops
    stops_list = mission_data.get("stops", [])
    allow_reorder = bool(mission_data.get("optimize_stops", False))

    parsed_stops = []
    if isinstance(stops_list, list):
        for s in stops_list:
            if isinstance(s, dict) and "row" in s and "col" in s:
                sid = str(s.get("id", ""))
                r = int(s["row"])
                c = int(s["col"])
                p = round(float(s.get("priority_score", 50.0)), 2)
                d = round(float(s.get("dwell_time_s", 900.0)), 1)
                parsed_stops.append((r, c, sid, p, d))

    if allow_reorder:
        # If stops are permutation-optimizable, order in request should not change the canonical set
        parsed_stops = sorted(parsed_stops)

    # Mission constraints
    constraints = mission_data.get("mission_constraints", {})
    max_dist = constraints.get("max_distance_m", mission_data.get("max_distance_m"))
    max_dur = constraints.get("max_duration_s", mission_data.get("max_duration_s"))

    canonical_rep = {
        "dataset_id": str(dataset_id),
        "start": [start_r, start_c],
        "goal": [goal_r, goal_c],
        "stops": parsed_stops,
        "profile": str(mission_data.get("profile", "conservative")).lower(),
        "vehicle_mode": str(mission_data.get("vehicle_mode", mission_data.get("mode", "crew_eva"))).lower(),
        "speed_multiplier": round(float(mission_data.get("speed_multiplier", 1.0)), 4),
        "allow_reorder": allow_reorder,
        "max_distance_m": round(float(max_dist), 2) if max_dist is not None else None,
        "max_duration_s": round(float(max_dur), 1) if max_dur is not None else None,
    }

    raw_bytes = json.dumps(canonical_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def create_api_error_response(
    error_code: str,
    message: str,
    status_code: int = 400,
    details: Optional[List[Dict[str, Any]]] = None,
    is_retryable: bool = False,
    input_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized error response adhering to api-error.schema.json.
    Includes backward-compatible 'error' and 'status' fields.
    """
    res = {
        "schema_version": SCHEMA_VERSION,
        "error_code": error_code,
        "message": message,
        "status_code": status_code,
        "is_retryable": is_retryable,
        "details": details or [],
        # Backward compatibility
        "error": message,
        "status": status_code,
    }
    if input_fingerprint:
        res["input_fingerprint"] = input_fingerprint
    return res


def build_mission_snapshot(
    canonical_mission: Dict[str, Any],
    ordered_points: List[Tuple[int, int]],
    ordered_stop_ids: List[str],
    terrain: TerrainGrid,
    input_fingerprint: str,
    mission_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construct a full mission snapshot adhering to mission-snapshot.schema.json.
    """
    elev_min = float(terrain.elevation[~terrain.invalid_mask].min()) if (~terrain.invalid_mask).any() else 0.0
    elev_max = float(terrain.elevation[~terrain.invalid_mask].max()) if (~terrain.invalid_mask).any() else 0.0

    return {
        "schema_version": SCHEMA_VERSION,
        "input_fingerprint": input_fingerprint,
        "mission_id": mission_id or f"mission_{input_fingerprint[:8]}",
        "canonical_mission": canonical_mission,
        "ordered_points": [list(pt) for pt in ordered_points],
        "ordered_stop_ids": ordered_stop_ids,
        "terrain_dataset": {
            "dataset_id": TERRAIN_DATASET_ID,
            "version": "1.0",
            "grid_cell_size_m": 20.0,
            "dimensions": {
                "height": int(terrain.height),
                "width": int(terrain.width),
            },
            "elevation_bounds_m": {
                "min_m": round(elev_min, 2),
                "max_m": round(elev_max, 2),
            },
        },
        "model_version": "2.0.0",
        "assumptions_version": "1.0.0",
    }


def compute_bundle_fingerprint(
    mission_data: Dict[str, Any],
    contingency_events: Optional[List[Dict[str, Any]]] = None,
    dataset_id: str = TERRAIN_DATASET_ID,
    terrain_sha256: str = TERRAIN_SHA256,
) -> str:
    """
    Compute a deterministic SHA-256 computation fingerprint representing the complete
    scientific and operational input state of a mission run.

    Guarantees:
    - Sorts keys and standardizes JSON structure canonically.
    - Excludes volatile metadata (timestamps, client IDs, run UUIDs).
    - Includes terrain dataset ID and exact raster SHA-256.
    - Includes start, goal, intermediate stops (with priority and dwell).
    - Includes routing profile, vehicle mode, speed derating, operational limits, distance caps.
    - Includes validated contingency events (types, centers, footprints, penalties, delays).
    - Validates that numeric values are finite (rejects NaN / Infinity).
    """
    # Canonical start
    start_obj = mission_data.get("start", {})
    start_r = int(start_obj.get("row", 0))
    start_c = int(start_obj.get("col", 0))

    # Canonical goal
    goal_obj = mission_data.get("goal", {})
    goal_r = int(goal_obj.get("row", 0))
    goal_c = int(goal_obj.get("col", 0))

    # Canonical stops
    stops_list = mission_data.get("stops", [])
    allow_reorder = bool(mission_data.get("optimize_stops", False))

    parsed_stops = []
    if isinstance(stops_list, list):
        for s in stops_list:
            if isinstance(s, dict) and "row" in s and "col" in s:
                sid = str(s.get("id", ""))
                r = int(s["row"])
                c = int(s["col"])
                p_raw = float(s.get("priority_score", 50.0))
                d_raw = float(s.get("dwell_time_s", 900.0))
                if math.isnan(p_raw) or math.isinf(p_raw) or math.isnan(d_raw) or math.isinf(d_raw):
                    raise ValueError("Stop priority and dwell time must be finite numbers")
                p = round(p_raw, 2)
                d = round(d_raw, 1)
                parsed_stops.append((r, c, sid, p, d))

    if allow_reorder:
        parsed_stops = sorted(parsed_stops)

    # Mission constraints
    constraints = mission_data.get("mission_constraints", {})
    max_dist_raw = constraints.get("max_distance_m", mission_data.get("max_distance_m"))
    max_dur_raw = constraints.get("operational_limit_s", mission_data.get("operational_limit_s", mission_data.get("max_duration_s")))
    dwell_per_stop_raw = mission_data.get("dwell_time_per_stop_s", 900.0)

    if max_dist_raw is not None and (math.isnan(float(max_dist_raw)) or math.isinf(float(max_dist_raw))):
        raise ValueError("max_distance_m must be finite")
    if max_dur_raw is not None and (math.isnan(float(max_dur_raw)) or math.isinf(float(max_dur_raw))):
        raise ValueError("operational_limit_s must be finite")

    max_dist = round(float(max_dist_raw), 2) if max_dist_raw is not None else None
    max_dur = round(float(max_dur_raw), 1) if max_dur_raw is not None else None
    dwell_per_stop = round(float(dwell_per_stop_raw), 1) if dwell_per_stop_raw is not None else 900.0

    spd_raw = float(mission_data.get("speed_multiplier", 1.0))
    if math.isnan(spd_raw) or math.isinf(spd_raw):
        raise ValueError("speed_multiplier must be finite")
    speed_mult = round(spd_raw, 4)

    # Canonical contingency events
    canonical_events = []
    ev_raw_list = contingency_events or mission_data.get("custom_events") or mission_data.get("events") or []
    if isinstance(ev_raw_list, list):
        for ev in ev_raw_list:
            if not isinstance(ev, dict) or not ev.get("enabled", True):
                continue
            ev_id = str(ev.get("id", "")).strip()
            ev_type = str(ev.get("event_type", "")).strip().lower()
            c_rc = ev.get("center_rc") or (
                [ev["center_row"], ev["center_col"]]
                if ("center_row" in ev and "center_col" in ev)
                else None
            )

            # Check finiteness of numeric fields
            for k in ("radius_m", "cost_multiplier", "speed_multiplier", "slope_penalty_multiplier", "budget_reduction_pct", "reduced_time_budget_s", "operational_delay_s"):
                if k in ev and ev[k] is not None:
                    fv = float(ev[k])
                    if math.isnan(fv) or math.isinf(fv):
                        raise ValueError(f"Contingency event field '{k}' must be finite")

            canonical_ev = {
                "id": ev_id,
                "event_type": ev_type,
                "center_rc": [int(c_rc[0]), int(c_rc[1])] if c_rc else None,
                "radius_m": round(float(ev["radius_m"]), 2) if "radius_m" in ev and ev["radius_m"] is not None else None,
                "cost_multiplier": round(float(ev["cost_multiplier"]), 2) if "cost_multiplier" in ev and ev["cost_multiplier"] is not None else None,
                "speed_multiplier": round(float(ev["speed_multiplier"]), 4) if "speed_multiplier" in ev and ev["speed_multiplier"] is not None else None,
                "slope_penalty_multiplier": round(float(ev["slope_penalty_multiplier"]), 2) if "slope_penalty_multiplier" in ev and ev["slope_penalty_multiplier"] is not None else None,
                "budget_reduction_pct": round(float(ev["budget_reduction_pct"]), 2) if "budget_reduction_pct" in ev and ev["budget_reduction_pct"] is not None else None,
                "reduced_time_budget_s": round(float(ev["reduced_time_budget_s"]), 1) if "reduced_time_budget_s" in ev and ev["reduced_time_budget_s"] is not None else None,
                "operational_delay_s": round(float(ev["operational_delay_s"]), 1) if "operational_delay_s" in ev and ev["operational_delay_s"] is not None else None,
                "unavailable_target_id": str(ev["unavailable_target_id"]).strip() if "unavailable_target_id" in ev and ev["unavailable_target_id"] else None,
            }
            canonical_events.append(canonical_ev)
    canonical_events.sort(key=lambda x: (x["event_type"], x["id"], str(x["center_rc"])))

    canonical_rep = {
        "dataset_id": str(dataset_id),
        "terrain_sha256": str(terrain_sha256),
        "start": [start_r, start_c],
        "goal": [goal_r, goal_c],
        "stops": parsed_stops,
        "profile": str(mission_data.get("profile", "conservative")).lower(),
        "vehicle_mode": str(mission_data.get("vehicle_mode", mission_data.get("mode", "crew_eva"))).lower(),
        "speed_multiplier": speed_mult,
        "allow_reorder": allow_reorder,
        "max_distance_m": max_dist,
        "operational_limit_s": max_dur,
        "dwell_time_per_stop_s": dwell_per_stop,
        "contingency_events": canonical_events,
        "model_version": "2.0.0",
        "assumptions_version": "1.0.0",
    }

    raw_bytes = json.dumps(canonical_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_bundle_execution_digest(
    baseline_route: Dict[str, Any],
    reachability_and_feasibility: Dict[str, Any],
    scenario_result: Optional[Dict[str, Any]] = None,
    comparison_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute a deterministic SHA-256 cryptographic digest of the complete computed
    output state of a mission run (baseline path geometry, distance, duration,
    reachability flags, contingency revised route, and comparison deltas).

    Provides a deterministic SHA-256 integrity fingerprint for detecting divergence
    or post-execution changes in reported results or route geometries (an integrity
    fingerprint for validation, rather than independent proof against out-of-band tampering).
    """
    b_path = baseline_route.get("path_rc", [])
    b_path_bytes = json.dumps(b_path, separators=(",", ":")).encode("utf-8")
    b_path_hash = hashlib.sha256(b_path_bytes).hexdigest()

    b_dist = round(float(baseline_route.get("distance_m", 0.0)), 2)
    b_dur = round(float(baseline_route.get("travel_time_s", baseline_route.get("duration_s", 0.0))), 1)
    b_cost = round(float(baseline_route.get("cost", 0.0)), 2) if (baseline_route.get("cost") is not None and not math.isinf(float(baseline_route.get("cost", 0.0)))) else None
    b_wps = list(baseline_route.get("visited_waypoint_ids", []))

    s_data = None
    if scenario_result:
        s_route = scenario_result.get("revised_route") or scenario_result.get("scenario_route") or {}
        s_path = s_route.get("path_rc", [])
        s_path_bytes = json.dumps(s_path, separators=(",", ":")).encode("utf-8")
        s_path_hash = hashlib.sha256(s_path_bytes).hexdigest()
        s_dist = round(float(s_route.get("distance_m", 0.0)), 2) if s_route.get("distance_m") is not None else None
        s_cost = round(float(s_route.get("cost", 0.0)), 2) if (s_route.get("cost") is not None and not math.isinf(float(s_route.get("cost", 0.0)))) else None

        c_metrics = comparison_metrics or {}
        s_data = {
            "path_hash": s_path_hash,
            "distance_m": s_dist,
            "cost": s_cost,
            "delta_distance_m": round(float(c_metrics.get("delta_distance_m", 0.0)), 2) if c_metrics.get("delta_distance_m") is not None else None,
            "delta_travel_time_s": round(float(c_metrics.get("delta_travel_time_s", 0.0)), 1) if c_metrics.get("delta_travel_time_s") is not None else None,
            "is_scenario_reachable": bool(c_metrics.get("is_scenario_reachable", True)),
            "is_scenario_budget_feasible": bool(c_metrics.get("is_scenario_budget_feasible", True)),
        }

    canonical_rep = {
        "baseline": {
            "path_hash": b_path_hash,
            "distance_m": b_dist,
            "duration_s": b_dur,
            "cost": b_cost,
            "visited_waypoint_ids": b_wps,
            "is_reachable": bool(baseline_route.get("is_reachable", True)),
            "is_budget_feasible": bool(baseline_route.get("is_budget_feasible", True)),
        },
        "reachability_and_feasibility": {
            "is_baseline_reachable": bool(reachability_and_feasibility.get("is_baseline_reachable", True)),
            "is_baseline_budget_feasible": bool(reachability_and_feasibility.get("is_baseline_budget_feasible", True)),
            "is_scenario_reachable": reachability_and_feasibility.get("is_scenario_reachable"),
            "is_scenario_budget_feasible": reachability_and_feasibility.get("is_scenario_budget_feasible"),
            "overall_status": str(reachability_and_feasibility.get("overall_status", "nominal")),
        },
        "scenario": s_data,
    }

    raw_bytes = json.dumps(canonical_rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def build_canonical_mission_run_bundle(
    mission_input: Dict[str, Any],
    baseline_route: Dict[str, Any],
    terrain: TerrainGrid,
    scenario_result: Optional[Dict[str, Any]] = None,
    comparison_metrics: Optional[Dict[str, Any]] = None,
    contingency_input: Optional[Dict[str, Any]] = None,
    bundle_id: Optional[str] = None,
    created_at: Optional[str] = None,
    terrain_sha256: str = TERRAIN_SHA256,
) -> Dict[str, Any]:
    """
    Construct a complete, canonical mission run bundle validating against
    mission-run-bundle.schema.json.
    """
    import datetime
    now_iso = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
    clean_bundle_id = bundle_id or (
        f"run_bundle_contingency_{hashlib.sha256(now_iso.encode()).hexdigest()[:8]}"
        if scenario_result
        else f"run_bundle_baseline_{hashlib.sha256(now_iso.encode()).hexdigest()[:8]}"
    )

    raw_events = (
        (contingency_input.get("events") if contingency_input else None)
        or mission_input.get("custom_events")
        or mission_input.get("events")
        or []
    )
    comp_fp = compute_bundle_fingerprint(
        mission_input,
        contingency_events=raw_events,
        dataset_id=TERRAIN_DATASET_ID,
        terrain_sha256=terrain_sha256,
    )
    base_fp = baseline_route.get("input_fingerprint") or compute_input_fingerprint(
        mission_input, dataset_id=TERRAIN_DATASET_ID
    )

    # Terrain provenance
    terrain_prov = {
        "dataset_id": TERRAIN_DATASET_ID,
        "source": "USGS Astrogeology Science Center MRO CTX DTM",
        "resolution_m": 20.0,
        "dimensions": {
            "height": int(terrain.height),
            "width": int(terrain.width),
        },
        "coordinate_reference": "IAU Mars 2000 Planetocentric Sphere",
        "sha256_hash": terrain_sha256,
        "file_size_bytes": 252206,
    }

    # Reachability & feasibility
    is_base_reach = bool(baseline_route.get("is_reachable", True))
    is_base_budget = bool(baseline_route.get("is_budget_feasible", True))
    is_scen_reach = bool(scenario_result.get("is_scenario_reachable", scenario_result.get("is_reachable", True))) if scenario_result else None
    is_scen_budget = bool(scenario_result.get("is_scenario_budget_feasible", scenario_result.get("is_budget_feasible", True))) if scenario_result else None

    if is_scen_reach is not None:
        if not is_scen_reach:
            overall_status = "scenario_unreachable"
        elif not is_scen_budget:
            overall_status = "budget_exceeded"
        else:
            overall_status = "feasible"
    elif not is_base_reach:
        overall_status = "baseline_unreachable"
    elif not is_base_budget:
        overall_status = "budget_exceeded"
    else:
        overall_status = "nominal"

    reach_feas = {
        "is_baseline_reachable": is_base_reach,
        "is_baseline_budget_feasible": is_base_budget,
        "is_scenario_reachable": is_scen_reach,
        "is_scenario_budget_feasible": is_scen_budget,
        "overall_status": overall_status,
    }

    # Engine metadata
    from marswalk.core.planner import ENGINEERING_ASSUMPTIONS
    engine_meta = {
        "model_version": "2.0.0",
        "assumptions_version": "1.0.0",
        "planner_algorithm": "A* with Generalized Octile Heuristic & Asymmetric Minetti Terrain Cost",
        "assumptions": dict(ENGINEERING_ASSUMPTIONS),
    }

    disclosures = [
        "RESEARCH PROTOTYPE DISCLAIMER: MarsWalk 2.0 is an interactive scientific research and mission rehearsal prototype developed for space exploration planning.",
        "NOT FLIGHT CERTIFIED: Modeled paths, estimated travel durations, and disruption contingencies represent mathematical approximations on remote-sensing models and do not guarantee physical safety for astronaut EVA operations.",
        "PROVENANCE DISCLOSURE: Planetary topography is derived from USGS MRO CTX DTM at 20 m/pixel. Velocities represent Apollo lunar terrestrial analogues (Crew EVA) and Mars 2020 tactical telemetry (Robotic Rover).",
    ]

    exec_digest = compute_bundle_execution_digest(
        baseline_route=baseline_route,
        reachability_and_feasibility=reach_feas,
        scenario_result=scenario_result,
        comparison_metrics=comparison_metrics,
    )

    bundle = {
        "schema_version": "1.0.0",
        "bundle_id": clean_bundle_id,
        "created_at": now_iso,
        "computation_fingerprint": comp_fp,
        "execution_digest": exec_digest,
        "baseline_fingerprint": base_fp,
        "mission_input": mission_input,
        "contingency_input": contingency_input,
        "terrain_provenance": terrain_prov,
        "baseline_route": baseline_route,
        "scenario_result": scenario_result,
        "comparison_metrics": comparison_metrics,
        "reachability_and_feasibility": reach_feas,
        "engine_metadata": engine_meta,
        "disclosures": disclosures,
    }

    clean_bundle = sanitize_for_json(bundle)
    validate_contract(clean_bundle, "mission-run-bundle", raise_on_error=True)
    return clean_bundle


def validate_campaign_scenario_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a campaign what-if simulation scenario record against campaign-scenario.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-scenario", raise_on_error=True)


def validate_campaign_coordination_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a multi-unit campaign coordination record against campaign-coordination.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-coordination", raise_on_error=True)


def validate_campaign_simulation_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a campaign digital twin execution simulation record against campaign-simulation.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-simulation", raise_on_error=True)


def validate_campaign_analytics_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a campaign performance analytics record against campaign-analytics.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-analytics", raise_on_error=True)


def validate_campaign_design_space_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a campaign design space exploration and Pareto record against campaign-design-space.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-design-space", raise_on_error=True)


def validate_campaign_benchmark_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a campaign benchmark suite result record against campaign-benchmark.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-benchmark", raise_on_error=True)


def validate_mission_robustness_experiment(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a Mission Robustness Lab experiment record against mission-robustness-experiment.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "mission-robustness-experiment", raise_on_error=True)


def validate_mission_rehearsal_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a Mission Rehearsal record against mission-rehearsal.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "mission-rehearsal", raise_on_error=True)


def validate_mission_experiment_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates an orchestrated Mission Experiment record against mission-experiment.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "mission-experiment", raise_on_error=True)


def validate_campaign_operations_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a Campaign Operations state record against campaign-operations.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-operations", raise_on_error=True)


def validate_campaign_operations_event_record(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates a Campaign Operations event record against campaign-operations-event.schema.json.
    """
    clean_data = sanitize_for_json(data)
    return validate_contract(clean_data, "campaign-operations-event", raise_on_error=True)







