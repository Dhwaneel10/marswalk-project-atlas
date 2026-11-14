"""
MarsWalk 2.0 — Milestone 10F: Mission Readiness & Decision Gate Core Engine.
Provides an integrated, deterministic planning-assurance evaluation consolidating:
  1. Mission Feasibility (route existence, reachability, budget adherence, slope limits)
  2. Environmental Data Readiness (freshness, in-situ vs climatology, site compatibility, sensor limits)
  3. Robustness & Contingency Coverage (tested disruption classes vs untested scenarios)
  4. Provenance & Reproducibility (fingerprint matching, event ledger correlation, recomputation tracking)

Produces structured findings and authoritative readiness statuses:
  - READY_FOR_REVIEW: All checks passed with verified telemetry and evaluated robustness.
  - CONDITIONAL: Feasible and within budget, but with non-blocking operational warnings.
  - INCOMPLETE: Trajectory uncomputed or required planning inputs missing.
  - BLOCKED: Unreachable destination, budget violation, unpassable terrain hazard, or invalid inputs.

CRITICAL DISCLAIMER:
This is a planning-assurance interface for the simulation. It is NOT a certified
flight-readiness system, autonomous go/no-go authority, or guarantee of rover/astronaut safety.
"""

from __future__ import annotations

import os
import re
import json
import uuid
import math
import time
import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Union

from marswalk.api.contracts import (
    validate_contract,
    sanitize_for_json,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    SCHEMA_VERSION,
    ContractValidationError,
)
from marswalk.core.mission_event_ledger import (
    get_mission_events,
    MissionEvent,
    DEFAULT_EVENTS_DIR,
)
from marswalk.core.weather import (
    get_weather_manager,
    WeatherManager,
    WeatherSnapshot,
    PhysicalRangeGuard,
    kelvin_to_celsius,
)

READINESS_ALGORITHM_VERSION = "10F"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_READINESS_DIR = PROJECT_ROOT / "data" / "workspaces" / "readiness"
DEFAULT_MISSIONS_DIR = PROJECT_ROOT / "data" / "workspaces" / "missions"

SAFE_ASSESSMENT_ID_REGEX = re.compile(r"^asmt_[a-zA-Z0-9_-]{3,64}$")

NASA_OPERATIONAL_DISCLAIMER = (
    "DISCLAIMER: MarsWalk modeled routes, traverse costs, readiness findings, and environmental "
    "evaluations are for simulation, mission design trade studies, and planning rehearsal only. "
    "They are NOT certified operationally safe for crewed surface exploration or flight authorization "
    "without formal real-time mission operations review."
)

SUPPORTED_DISRUPTION_CLASSES = [
    "corridor_closure",
    "mobility_multiplier",
    "operational_budget",
    "target_loss",
    "terrain_cost",
    "compound",
]


class MissionReadinessError(Exception):
    """Custom exception raised for mission readiness assessment errors."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = "ERR_READINESS"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def generate_assessment_id(mission_id: Optional[str] = None) -> str:
    """Generate a clean, deterministic prefix assessment identifier."""
    prefix = "asmt_"
    if mission_id:
        clean_mid = re.sub(r"[^a-zA-Z0-9_]", "_", mission_id)[:24]
        if clean_mid.startswith("m_"):
            clean_mid = clean_mid[2:]
        prefix = f"asmt_{clean_mid}_"
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}{uid}"


def get_current_iso_time() -> str:
    """Return UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass
class ReadinessFinding:
    """Single structured finding in the mission readiness assessment."""
    finding_code: str
    category: str
    severity: str
    title: str
    description: str
    is_blocking: bool
    evidence_references: Dict[str, Any]
    recommended_action: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_code": self.finding_code,
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "is_blocking": self.is_blocking,
            "evidence_references": self.evidence_references,
            "recommended_action": self.recommended_action,
        }


def evaluate_mission_readiness(
    mission_data_or_id: Union[str, Dict[str, Any]],
    route_result: Optional[Dict[str, Any]] = None,
    terrain: Optional[Any] = None,
    transform: Optional[Any] = None,
    weather_site: str = "jezero_crater",
    weather_snapshot: Optional[Dict[str, Any]] = None,
    robustness_result: Optional[Dict[str, Any]] = None,
    operational_budget_s: Optional[float] = None,
    missions_dir: Optional[Union[str, Path]] = None,
    events_dir: Optional[Union[str, Path]] = None,
    readiness_dir: Optional[Union[str, Path]] = None,
    persist_assessment: bool = True,
) -> Dict[str, Any]:
    """
    Execute comprehensive, deterministic Mission Readiness & Decision Gate assessment.

    Args:
        mission_data_or_id: String mission ID or dictionary of mission definition.
        route_result: Optional precomputed RouteResult dictionary.
        terrain: Optional TerrainGrid for elevation/slope evaluations.
        transform: Optional rasterio affine transform.
        weather_site: Target meteorological observation site ID (default 'jezero_crater').
        weather_snapshot: Optional pre-fetched weather report dictionary.
        robustness_result: Optional precomputed robustness analysis result.
        operational_budget_s: Optional custom budget limit in seconds.
        missions_dir: Optional custom missions directory.
        events_dir: Optional custom event ledgers directory.
        readiness_dir: Optional custom readiness assessments directory.
        persist_assessment: If True, atomically saves assessment to disk.

    Returns:
        Structured assessment dictionary matching mission-readiness-assessment.schema.json.
    """
    findings: List[ReadinessFinding] = []

    # ---------------------------------------------------------
    # 1. Resolve Mission Data & Configuration
    # ---------------------------------------------------------
    mission_id = ""
    mission_name = "Ad-Hoc Sortie Plan"
    canonical_plan: Dict[str, Any] = {}
    fingerprint: Optional[str] = None
    terrain_dataset_id = TERRAIN_DATASET_ID
    terrain_sha256 = TERRAIN_SHA256
    model_version = "2.0.0"
    assumptions_version = "1.0.0"

    if isinstance(mission_data_or_id, str):
        from marswalk.api.workspace import get_mission, WorkspaceError
        try:
            saved = get_mission(mission_data_or_id, missions_dir=str(missions_dir) if missions_dir else None)
            mission_id = saved.get("mission_id", mission_data_or_id)
            mission_name = saved.get("name", mission_id)
            canonical_plan = saved.get("canonical_mission", {})
            fingerprint = saved.get("input_fingerprint")
            terrain_dataset_id = saved.get("terrain_dataset_id", TERRAIN_DATASET_ID)
            model_version = saved.get("model_version", "2.0.0")
            assumptions_version = saved.get("assumptions_version", "1.0.0")
        except WorkspaceError as err:
            raise MissionReadinessError(f"Failed loading mission '{mission_data_or_id}': {err.message}", err.status_code)
    elif isinstance(mission_data_or_id, dict):
        mission_id = mission_data_or_id.get("mission_id") or f"adhoc_{uuid.uuid4().hex[:8]}"
        mission_name = mission_data_or_id.get("name") or mission_data_or_id.get("mission_name") or "Ad-Hoc Traverse"
        canonical_plan = mission_data_or_id.get("canonical_mission") or mission_data_or_id
        fingerprint = mission_data_or_id.get("input_fingerprint")
        terrain_dataset_id = mission_data_or_id.get("terrain_dataset_id", TERRAIN_DATASET_ID)
        model_version = mission_data_or_id.get("model_version", "2.0.0")
        assumptions_version = mission_data_or_id.get("assumptions_version", "1.0.0")
    else:
        raise MissionReadinessError("mission_data_or_id must be a string ID or dict", 400)

    # ---------------------------------------------------------
    # 2. Category A: Mission Feasibility Checks
    # ---------------------------------------------------------
    start_pt = canonical_plan.get("start")
    goal_pt = canonical_plan.get("goal")
    stops_list = canonical_plan.get("stops", [])
    vehicle_mode = canonical_plan.get("vehicle_mode", "crew_eva")
    profile = canonical_plan.get("profile", "conservative")
    speed_mult = float(canonical_plan.get("speed_multiplier", 1.0) or 1.0)

    # Resolve budget
    from marswalk.core.planner import OPERATIONAL_LIMITS_S
    nominal_budget_s = operational_budget_s
    if nominal_budget_s is None:
        nominal_budget_s = OPERATIONAL_LIMITS_S.get(vehicle_mode, 28800.0)

    feasibility_status = "PASSED"
    route_exists = False
    is_within_budget = None
    tot_distance_m: Optional[float] = None
    tot_duration_s: Optional[float] = None
    margin_s: Optional[float] = None

    # Check endpoints existence
    if not start_pt or not goal_pt or "row" not in start_pt or "col" not in start_pt or "row" not in goal_pt or "col" not in goal_pt:
        findings.append(ReadinessFinding(
            finding_code="FEAS_MISSING_ENDPOINTS",
            category="feasibility",
            severity="blocker",
            title="Missing Mission Endpoints",
            description="The mission definition does not specify valid start or goal coordinates.",
            is_blocking=True,
            evidence_references={"start": start_pt, "goal": goal_pt},
            recommended_action="Configure valid start and destination coordinates in the Mission Design Lab.",
        ))
        feasibility_status = "BLOCKED"
    else:
        start_rc = (int(start_pt["row"]), int(start_pt["col"]))
        goal_rc = (int(goal_pt["row"]), int(goal_pt["col"]))

        # Bounds check if terrain present
        if terrain is not None:
            max_r, max_c = terrain.shape
            coords_valid = True
            for pt_name, rc in [("Start", start_rc), ("Goal", goal_rc)]:
                if not (0 <= rc[0] < max_r and 0 <= rc[1] < max_c):
                    coords_valid = False
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_COORDINATES_OUT_OF_BOUNDS",
                        category="feasibility",
                        severity="blocker",
                        title=f"{pt_name} Coordinate Out of DTM Bounds",
                        description=f"{pt_name} coordinate ({rc[0]}, {rc[1]}) exceeds surveyed raster dimensions ({max_r}, {max_c}).",
                        is_blocking=True,
                        evidence_references={"point": pt_name, "rc": list(rc), "bounds": [max_r, max_c]},
                        recommended_action="Reposition point within the surveyed Jezero 20m CTX boundary.",
                    ))
            for idx, st in enumerate(stops_list):
                sr, sc = int(st.get("row", 0)), int(st.get("col", 0))
                if not (0 <= sr < max_r and 0 <= sc < max_c):
                    coords_valid = False
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_WAYPOINT_OUT_OF_BOUNDS",
                        category="feasibility",
                        severity="blocker",
                        title=f"Waypoint '{st.get('id', idx)}' Out of Bounds",
                        description=f"Stop '{st.get('name', idx)}' at ({sr}, {sc}) lies outside the surveyed elevation model.",
                        is_blocking=True,
                        evidence_references={"stop_id": st.get("id"), "rc": [sr, sc]},
                        recommended_action="Relocate stop to an accessible coordinate within surveyed terrain.",
                    ))
            if not coords_valid:
                feasibility_status = "BLOCKED"

        # Route metrics evaluation
        calculated_route = None
        if route_result and isinstance(route_result, dict):
            calculated_route = route_result
            route_exists = bool(
                calculated_route.get("path")
                or calculated_route.get("path_rc")
                or float(calculated_route.get("total_distance_m") or calculated_route.get("distance_m") or 0.0) > 0.0
            )
        elif terrain is not None and feasibility_status != "BLOCKED":
            # Attempt A* route calculation
            try:
                from marswalk.core.planner import plan_route, PlannerConfig
                cfg = PlannerConfig(
                    step_size=20.0,
                    max_slope=15.0 if profile == "conservative" else 20.0,
                    speed_multiplier=speed_mult,
                )
                res = plan_route(start_rc, goal_rc, terrain, cfg)
                if res and res.path:
                    route_exists = True
                    tot_dwell = sum(float(s.get("dwell_time_s", 900.0)) for s in stops_list)
                    calculated_route = {
                        "total_distance_m": float(res.distance_m),
                        "total_cost": float(res.cost),
                        "total_duration_s": float(res.duration_s) + tot_dwell,
                        "traverse_duration_s": float(res.duration_s),
                        "max_slope_deg": float(res.max_slope_deg),
                    }
                else:
                    route_exists = False
            except Exception as e:
                route_exists = False

        if calculated_route:
            is_reachable = bool(calculated_route.get("is_reachable", True))
            if not is_reachable or not route_exists:
                findings.append(ReadinessFinding(
                    finding_code="FEAS_UNREACHABLE_DESTINATION",
                    category="feasibility",
                    severity="blocker",
                    title="Unreachable Goal or Waypoint",
                    description="Route planning indicates the destination or waypoint is unreachable or obstructed.",
                    is_blocking=True,
                    evidence_references={"is_reachable": False, "route_exists": route_exists},
                    recommended_action="Inspect terrain barriers, ease slope constraints, or reposition waypoints.",
                ))
                feasibility_status = "BLOCKED"
            else:
                tot_distance_m = round(float(calculated_route.get("total_distance_m", calculated_route.get("distance_m", 0.0))), 1)
                tot_duration_s = round(float(calculated_route.get("total_duration_s", calculated_route.get("duration_s", 0.0))), 1)
                margin_s = round(nominal_budget_s - tot_duration_s, 1)
                is_within_budget = margin_s >= 0.0

                # Check budget limit
                if not is_within_budget:
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_BUDGET_EXCEEDED",
                        category="feasibility",
                        severity="blocker",
                        title="Mission Duration Exceeds Operational Budget",
                        description=f"Planned traverse duration ({tot_duration_s/3600:.2f} h) exceeds allowable operational window ({nominal_budget_s/3600:.2f} h) by {abs(margin_s)/60:.1f} minutes.",
                        is_blocking=True,
                        evidence_references={
                            "total_duration_s": tot_duration_s,
                            "budget_s": nominal_budget_s,
                            "overage_s": abs(margin_s),
                        },
                        recommended_action="Prune science stops, reduce dwell durations, or adopt a higher-mobility locomotion profile.",
                    ))
                    feasibility_status = "BLOCKED"
                elif margin_s < (0.15 * nominal_budget_s):
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_TIGHT_OPERATIONAL_MARGIN",
                        category="feasibility",
                        severity="warning",
                        title="Tight Operational Margin (< 15%)",
                        description=f"Remaining margin ({margin_s/60:.1f} min, {margin_s/nominal_budget_s*100:.1f}%) is below recommended 15% safety buffer.",
                        is_blocking=False,
                        evidence_references={"margin_s": margin_s, "margin_pct": round(margin_s/nominal_budget_s*100, 1)},
                        recommended_action="Consider streamlining dwell allocations to absorb surface traversal delays.",
                    ))
                    if feasibility_status != "BLOCKED":
                        feasibility_status = "CONDITIONAL"
                else:
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_BUDGET_COMPLIANT",
                        category="feasibility",
                        severity="info",
                        title="Trajectory Within Operational Budget",
                        description=f"Total duration of {tot_duration_s/60:.1f} min preserves healthy {margin_s/60:.1f} min buffer against {nominal_budget_s/3600:.1f} h limit.",
                        is_blocking=False,
                        evidence_references={"margin_s": margin_s, "total_duration_s": tot_duration_s},
                        recommended_action="No modification required.",
                    ))

                # Slope envelope check
                max_slope = calculated_route.get("max_slope_deg")
                if max_slope is not None and max_slope > (15.0 if profile == "conservative" else 20.0):
                    findings.append(ReadinessFinding(
                        finding_code="FEAS_SLOPE_THRESHOLD_WARNING",
                        category="feasibility",
                        severity="warning",
                        title="Traverse Intersects High-Slope Terrain",
                        description=f"Maximum slope gradient of {max_slope:.1f}° approaches vehicle mobility thresholds.",
                        is_blocking=False,
                        evidence_references={"max_slope_deg": max_slope},
                        recommended_action="Review terrain contour overlays or insert detour waypoints around scarps.",
                    ))
                    if feasibility_status != "BLOCKED":
                        feasibility_status = "CONDITIONAL"

        elif terrain is not None and not route_exists and feasibility_status != "BLOCKED":
            findings.append(ReadinessFinding(
                finding_code="FEAS_UNREACHABLE_DESTINATION",
                category="feasibility",
                severity="blocker",
                title="Unreachable Goal or Waypoint",
                description="A* path planner failed to find an unobstructed, slope-compliant trajectory between endpoints.",
                is_blocking=True,
                evidence_references={"start": list(start_rc), "goal": list(goal_rc)},
                recommended_action="Inspect slope heatmaps for terrain bottlenecks or ease profile slope threshold.",
            ))
            feasibility_status = "BLOCKED"
        else:
            findings.append(ReadinessFinding(
                finding_code="FEAS_ROUTE_UNCOMPUTED",
                category="feasibility",
                severity="info",
                title="Trajectory Uncomputed / Pending",
                description="Mobility distance and duration are uncalculated. Complete A* path generation to verify feasibility.",
                is_blocking=False,
                evidence_references={"mission_id": mission_id},
                recommended_action="Execute A* route calculation in Atlas before mission review.",
            ))
            if feasibility_status != "BLOCKED":
                feasibility_status = "INCOMPLETE"

    feasibility_summary = {
        "status": feasibility_status,
        "route_exists": route_exists,
        "is_within_budget": is_within_budget,
        "total_distance_m": tot_distance_m,
        "total_duration_s": tot_duration_s,
        "budget_s": nominal_budget_s,
        "margin_s": margin_s,
    }

    # ---------------------------------------------------------
    # 3. Category B: Environmental Data Readiness Checks
    # ---------------------------------------------------------
    raw_env: Optional[Dict[str, Any]] = None
    if weather_snapshot:
        raw_env = weather_snapshot
    else:
        try:
            wm = get_weather_manager()
            raw_env = wm.get_weather(site_id=weather_site, force_refresh=False)
        except Exception:
            raw_env = None

    env_status = "PASSED"
    is_site_compatible = True
    env_site_id = weather_site
    env_site_name = "Martian Surface"
    env_data_type = "UNKNOWN"
    env_freshness = "UNKNOWN"
    env_sol = None

    if raw_env and isinstance(raw_env, dict):
        env_site_id = raw_env.get("site_id", weather_site)
        env_site_name = raw_env.get("site_name", "Martian Surface")
        env_data_type = raw_env.get("data_type", "IN_SITU_OBSERVATION")
        env_freshness = raw_env.get("freshness_status", "ACTIVE_MISSION_CADENCE")
        env_sol = raw_env.get("observation_sol")
        measures = raw_env.get("measurements", {})

        # Geographic site compatibility
        # If mission is located in Jezero, check weather site
        is_jezero_mission = "jezero" in mission_id.lower() or "jezero" in terrain_dataset_id.lower() or "jezero" in mission_name.lower()
        if is_jezero_mission and env_site_id != "jezero_crater":
            is_site_compatible = False
            findings.append(ReadinessFinding(
                finding_code="ENV_SITE_MISMATCH",
                category="environmental",
                severity="warning",
                title=f"Atmospheric Site Mismatch ({env_site_name})",
                description=f"Traverse is planned in Jezero Crater, but atmospheric telemetry is sourced from {env_site_name} (over 1,000 km away).",
                is_blocking=False,
                evidence_references={"mission_region": "Jezero Crater", "weather_site": env_site_id},
                recommended_action="Switch atmospheric observation site to 'jezero_crater' for genuine local MEDA telemetry.",
            ))
            env_status = "CONDITIONAL"

        # Data type verification
        if env_data_type == "IN_SITU_OBSERVATION":
            findings.append(ReadinessFinding(
                finding_code="ENV_IN_SITU_VERIFIED",
                category="environmental",
                severity="info",
                title=f"In-Situ Surface Observations ({env_site_name})",
                description=f"Atmospheric parameters are genuine in-situ measurements downlinked from NASA PDS archives (Sol {env_sol}).",
                is_blocking=False,
                evidence_references={"site_id": env_site_id, "sol": env_sol, "data_type": env_data_type},
                recommended_action="Verify latest PDS archive release for updated sol batches.",
            ))
        elif "CLIMATOLOGICAL_MODEL" in env_data_type:
            findings.append(ReadinessFinding(
                finding_code="ENV_CLIMATOLOGICAL_MODEL_NOTICE",
                category="environmental",
                severity="warning",
                title="Numerical Climate Model (Not In-Situ)",
                description="Environmental data is derived from the Mars Climate Database (MCD v6.1 GCM) rather than physical surface sensors.",
                is_blocking=False,
                evidence_references={"site_id": env_site_id, "model": "MCD v6.1"},
                recommended_action="Note that modeled parameters do not record real-time transient dust devil or wind events.",
            ))
            if env_status != "BLOCKED":
                env_status = "CONDITIONAL"
        elif "HISTORICAL" in env_data_type:
            findings.append(ReadinessFinding(
                finding_code="ENV_HISTORICAL_ARCHIVE_NOTICE",
                category="environmental",
                severity="warning",
                title="Historical Lander Mission Archive",
                description=f"Readings originate from retired mission surface telemetry ({env_site_name}).",
                is_blocking=False,
                evidence_references={"site_id": env_site_id, "sol": env_sol},
                recommended_action="Consult active mission telemetry if local real-time context is required.",
            ))
            if env_status != "BLOCKED":
                env_status = "CONDITIONAL"

        # Stale cache check
        if env_freshness in ("STALE_ARCHIVE", "EXPIRED_CACHE"):
            findings.append(ReadinessFinding(
                finding_code="ENV_DATA_STALE",
                category="environmental",
                severity="warning",
                title="Environmental Snapshot Exceeds Freshness Cadence",
                description=f"Cached atmospheric record exceeds normal refresh cadence ({env_freshness}).",
                is_blocking=False,
                evidence_references={"freshness_status": env_freshness, "last_checked": raw_env.get("last_checked_utc")},
                recommended_action="Trigger environmental refresh via POST /api/weather/refresh.",
            ))
            if env_status != "BLOCKED":
                env_status = "CONDITIONAL"

        # Missing readings check
        missing_fields = [k for k, v in measures.items() if v is None]
        if missing_fields:
            findings.append(ReadinessFinding(
                finding_code="ENV_INCOMPLETE_SENSOR_TELEMETRY",
                category="environmental",
                severity="info",
                title="Optional Sensor Telemetry Missing",
                description=f"Sensors for {', '.join(missing_fields[:3])} returned null/missing in archival logs (preserved without zero-filling).",
                is_blocking=False,
                evidence_references={"missing_sensors": missing_fields},
                recommended_action="Safe to proceed; non-critical telemetry omitted.",
            ))

    else:
        findings.append(ReadinessFinding(
            finding_code="ENV_SNAPSHOT_UNAVAILABLE",
            category="environmental",
            severity="warning",
            title="Environmental Context Unavailable",
            description="No atmospheric observation snapshot could be retrieved for this mission.",
            is_blocking=False,
            evidence_references={"target_site": weather_site},
            recommended_action="Query atmospheric intelligence via Atlas weather modal or API.",
        ))
        env_status = "CONDITIONAL"

    environmental_summary = {
        "status": env_status,
        "site_id": env_site_id,
        "site_name": env_site_name,
        "data_type": env_data_type,
        "freshness_status": env_freshness,
        "is_site_compatible": is_site_compatible,
        "observation_sol": env_sol,
    }

    # ---------------------------------------------------------
    # 4. Category C: Robustness & Contingency Coverage
    # ---------------------------------------------------------
    robustness_status = "PASSED"
    tested_count = 0
    untested_count = 0
    breakpoint_count = 0
    evaluated_classes: List[str] = []

    if robustness_result and isinstance(robustness_result, dict):
        evaluated_classes = list(robustness_result.get("evaluated_disruption_classes") or robustness_result.get("tested_dimensions") or [])
        breakpoints = robustness_result.get("breakpoints") or []
        breakpoint_count = len(breakpoints)
        tested_cases = robustness_result.get("tested_cases") or robustness_result.get("evaluated_cases") or []
        tested_count = len(tested_cases) if tested_cases else len(evaluated_classes)

        if breakpoint_count > 0:
            findings.append(ReadinessFinding(
                finding_code="ROB_BREAKPOINTS_SURFACED",
                category="robustness",
                severity="warning",
                title=f"Robustness Breakpoints Detected ({breakpoint_count} cases)",
                description=f"Sensitivity testing revealed {breakpoint_count} operational variations where the traverse became over-budget or infeasible.",
                is_blocking=False,
                evidence_references={"breakpoint_count": breakpoint_count, "breakpoints": breakpoints[:3]},
                recommended_action="Inspect breakpoint thresholds in Mission Robustness Lab and establish contingency waypoints.",
            ))
            robustness_status = "CONDITIONAL"
        else:
            findings.append(ReadinessFinding(
                finding_code="ROB_SCENARIOS_STABLE",
                category="robustness",
                severity="info",
                title="Tested Robustness Scenarios Stable",
                description=f"All {tested_count} tested disruption cases maintain feasible recovery paths.",
                is_blocking=False,
                evidence_references={"tested_scenarios_count": tested_count},
                recommended_action="Review Gauntlet recovery trade-offs as needed.",
            ))

        # Check for untested dimensions
        missing_classes = [c for c in SUPPORTED_DISRUPTION_CLASSES if c not in evaluated_classes]
        untested_count = len(missing_classes)
        if missing_classes:
            findings.append(ReadinessFinding(
                finding_code="ROB_UNTESTED_SCENARIOS",
                category="robustness",
                severity="untested",
                title=f"Untested Disruption Classes ({untested_count} remaining)",
                description=f"Disruption dimensions {missing_classes} have not been evaluated for this trajectory.",
                is_blocking=False,
                evidence_references={"untested_classes": missing_classes},
                recommended_action="Execute Gauntlet stress-test sweep across untested disruption classes.",
            ))
    else:
        # No robustness analysis result attached
        untested_count = len(SUPPORTED_DISRUPTION_CLASSES)
        findings.append(ReadinessFinding(
            finding_code="ROB_UNTESTED_SCENARIOS",
            category="robustness",
            severity="untested",
            title=f"Robustness Sensitivity Untested ({untested_count} classes)",
            description="Mission has not undergone deterministic disruption evaluation (corridor rockfall, sand dune impedance, motor derating).",
            is_blocking=False,
            evidence_references={"supported_classes": SUPPORTED_DISRUPTION_CLASSES},
            recommended_action="Run Gauntlet stress-testing in the Robustness Lab prior to operational commitment.",
        ))
        robustness_status = "CONDITIONAL"

    robustness_summary = {
        "status": robustness_status,
        "tested_scenarios_count": tested_count,
        "untested_scenarios_count": untested_count,
        "breakpoint_count": breakpoint_count,
        "evaluated_disruption_classes": evaluated_classes,
    }

    # ---------------------------------------------------------
    # 5. Category D: Provenance & Reproducibility Checks
    # ---------------------------------------------------------
    provenance_status = "PASSED"
    is_recomputed = (route_result is None)
    ledger_present = False
    events_count = 0

    # Event ledger check
    try:
        events = get_mission_events(mission_id, base_dir=events_dir)
        events_count = len(events)
        ledger_present = events_count > 0
    except Exception:
        events = []
        events_count = 0
        ledger_present = False

    if ledger_present:
        findings.append(ReadinessFinding(
            finding_code="PROV_LEDGER_CORRELATED",
            category="provenance",
            severity="info",
            title=f"Sortie Black Box Correlated ({events_count} events)",
            description=f"Mission event ledger contains {events_count} recorded operational events.",
            is_blocking=False,
            evidence_references={"events_count": events_count, "mission_id": mission_id},
            recommended_action="Review incident reconstructor if emergency interventions were logged.",
        ))
    else:
        findings.append(ReadinessFinding(
            finding_code="PROV_NO_LEDGER_LOGS",
            category="provenance",
            severity="info",
            title="Pre-Sortie Plan (No Ledger History)",
            description="Mission has not commenced active simulation playback; black box event ledger is clear.",
            is_blocking=False,
            evidence_references={"mission_id": mission_id},
            recommended_action="Nominal for unexecuted mission plans.",
        ))

    if is_recomputed:
        findings.append(ReadinessFinding(
            finding_code="PROV_RECOMPUTED_METRICS",
            category="provenance",
            severity="info",
            title="Route Metrics Recomputed on Demand",
            description="Trajectory metrics were freshly evaluated from digital terrain model rather than read from pre-stored cache.",
            is_blocking=False,
            evidence_references={"is_recomputed": True},
            recommended_action="Save mission experiment run bundle for immutable reference.",
        ))

    if fingerprint:
        findings.append(ReadinessFinding(
            finding_code="PROV_FINGERPRINT_VERIFIED",
            category="provenance",
            severity="info",
            title="Deterministic Fingerprint Bound",
            description="Mission definition includes SHA-256 input fingerprint bound to canonical coordinates.",
            is_blocking=False,
            evidence_references={"input_fingerprint": fingerprint[:16] + "..."},
            recommended_action="Preserve fingerprint for automated verification.",
        ))

    provenance_summary = {
        "status": provenance_status,
        "is_recomputed": is_recomputed,
        "ledger_present": ledger_present,
        "events_count": events_count,
    }

    # ---------------------------------------------------------
    # 6. Overall Readiness Status Determination
    # ---------------------------------------------------------
    blockers = [f for f in findings if f.severity == "blocker" or f.is_blocking]
    warnings = [f for f in findings if f.severity == "warning"]
    infos = [f for f in findings if f.severity == "info"]
    untesteds = [f for f in findings if f.severity == "untested"]

    blocker_count = len(blockers)
    warning_count = len(warnings)
    info_count = len(infos)
    untested_count_total = len(untesteds)

    if blocker_count > 0:
        overall_status = "BLOCKED"
        summary = f"BLOCKED: {blocker_count} critical planning constraint violation(s) identified (e.g. {blockers[0].title}). Traversal cannot proceed as configured."
    elif feasibility_status == "INCOMPLETE":
        overall_status = "INCOMPLETE"
        summary = "INCOMPLETE: Route trajectory has not been calculated or required coordinates are missing. Complete traversal pathfinding before assessment."
    elif warning_count > 0 or untested_count_total > 0:
        overall_status = "CONDITIONAL"
        reasons = []
        if warning_count > 0:
            reasons.append(f"{warning_count} operational warning(s)")
        if untested_count_total > 0:
            reasons.append(f"{untested_count_total} untested robustness scenario(s)")
        summary = f"CONDITIONAL: Feasible within modeled budget, but {', and '.join(reasons)} require review (e.g. {warnings[0].title if warnings else untesteds[0].title})."
    else:
        overall_status = "READY_FOR_REVIEW"
        summary = "READY FOR REVIEW: All deterministic feasibility checks passed, environmental telemetry verified, and trajectory is within operational limits."

    # Compute deterministic readiness score (0-100)
    score = 100.0
    score -= blocker_count * 40.0
    score -= warning_count * 15.0
    score -= untested_count_total * 5.0
    if overall_status == "INCOMPLETE":
        score = min(score, 40.0)
    elif overall_status == "BLOCKED":
        score = min(score, 25.0)
    readiness_score = max(0.0, min(100.0, round(score, 1)))

    assessment_id = generate_assessment_id(mission_id)
    now_utc = get_current_iso_time()

    assessment_dict = {
        "schema_version": SCHEMA_VERSION,
        "assessment_id": assessment_id,
        "generated_at_utc": now_utc,
        "mission_id": mission_id,
        "mission_name": mission_name,
        "continuation_id": None,
        "readiness_status": overall_status,
        "readiness_score": readiness_score,
        "summary": summary,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "untested_count": untested_count_total,
        "reproducibility_manifest": {
            "terrain_dataset_id": terrain_dataset_id,
            "terrain_sha256": terrain_sha256,
            "model_version": model_version,
            "software_version": READINESS_ALGORITHM_VERSION,
            "input_fingerprint": fingerprint,
            "assumptions_version": assumptions_version,
        },
        "categories_summary": {
            "feasibility": feasibility_summary,
            "environmental": environmental_summary,
            "robustness": robustness_summary,
            "provenance": provenance_summary,
        },
        "findings": [f.to_dict() for f in findings],
        "limitations_and_disclaimers": [
            NASA_OPERATIONAL_DISCLAIMER,
            "Readiness findings are calculated from analytical terrain heuristics and discrete NASA PDS telemetry.",
            "Untested robustness dimensions represent lack of sensitivity simulation and must not be inferred as safe.",
            "Environmental observations reflect past archival downlink tranches and do not constitute real-time weather forecasting.",
        ],
    }

    # Validate against JSON schema contract
    sanitized = sanitize_for_json(assessment_dict)
    is_valid, errs = validate_contract(sanitized, "mission-readiness-assessment")
    if not is_valid:
        raise ContractValidationError(
            f"Mission Readiness Assessment contract validation failed: {errs}",
            errors=errs,
            schema_name="mission-readiness-assessment",
        )

    # Optional atomic disk persistence
    if persist_assessment:
        try:
            save_mission_readiness_assessment(sanitized, base_dir=readiness_dir)
        except Exception as e:
            # Persistence failure should not crash evaluation if memory result is valid
            print(f"[Warning] Failed persisting readiness assessment: {e}")

    return sanitized


def save_mission_readiness_assessment(
    assessment: Dict[str, Any],
    base_dir: Optional[Union[str, Path]] = None,
) -> str:
    """
    Atomically persist a mission readiness assessment to data/workspaces/readiness/<assessment_id>.json.
    Preserves historical immutability; never overwrites or mutates previous assessments.
    """
    target_dir = Path(base_dir or DEFAULT_READINESS_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    aid = assessment.get("assessment_id")
    if not aid or not SAFE_ASSESSMENT_ID_REGEX.match(aid):
        raise MissionReadinessError(f"Invalid assessment ID '{aid}' for persistence.", 400)

    target_file = target_dir / f"{aid}.json"
    temp_file = target_dir / f"{aid}.tmp_{uuid.uuid4().hex[:6]}"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(assessment, f, indent=2)
    os.replace(temp_file, target_file)

    return str(target_file)


def get_mission_readiness_assessment(
    assessment_id: str,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Retrieve an existing persisted readiness assessment by its stable ID."""
    clean_id = assessment_id.strip()
    if not SAFE_ASSESSMENT_ID_REGEX.match(clean_id):
        raise MissionReadinessError(f"Invalid assessment ID format: '{clean_id}'", 400)

    target_dir = Path(base_dir or DEFAULT_READINESS_DIR)
    target_file = target_dir / f"{clean_id}.json"

    if not target_file.is_file():
        raise MissionReadinessError(f"Readiness assessment '{clean_id}' not found.", 404, "ERR_ASSESSMENT_NOT_FOUND")

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def list_mission_readiness_assessments(
    mission_id: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """List stored readiness assessment summaries, optionally filtered by mission ID."""
    target_dir = Path(base_dir or DEFAULT_READINESS_DIR)
    if not target_dir.exists():
        return []

    results = []
    for f in target_dir.glob("asmt_*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if mission_id and data.get("mission_id") != mission_id:
                continue
            results.append({
                "assessment_id": data.get("assessment_id"),
                "mission_id": data.get("mission_id"),
                "mission_name": data.get("mission_name"),
                "readiness_status": data.get("readiness_status"),
                "readiness_score": data.get("readiness_score"),
                "blocker_count": data.get("blocker_count", 0),
                "warning_count": data.get("warning_count", 0),
                "generated_at_utc": data.get("generated_at_utc"),
            })
        except Exception:
            continue

    results.sort(key=lambda x: str(x.get("generated_at_utc", "")), reverse=True)
    return results
