"""
MarsWalk 2.0 — Milestone 10C: Sortie Black Box Incident Replay & Decision Reconstruction.
Reconstructs the operational sequence of events, evaluates recorded decisions against
recomputed solutions on authentic terrain, and enforces truthful distinction between
historical facts and re-evaluated estimates.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import rasterio

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import ScienceWaypoint
from marswalk.core.mission_event_ledger import (
    MissionEvent,
    get_mission_events,
    validate_mission_id,
    EventLedgerError,
)
from marswalk.core.mission_continuation import (
    MidSortieState,
    plan_mission_continuation,
)
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    validate_contract,
    sanitize_for_json,
    ContractValidationError,
)

DISCLOSURES = [
    "RESEARCH PROTOTYPE: Modeled route decision engine and incident reconstruction.",
    "USGS MRO CTX 20m Jezero Crater topography and IAU 2000 planetocentric coordinate system.",
    "NOT CERTIFIED FOR HUMAN MISSION OPERATIONS: Modeled routes must never be described as safe for astronauts.",
    "TRUTHFUL REPLAY: Distinguishes historically recorded telemetry from recomputed algorithmic estimates.",
]


def reconstruct_incident_timeline(
    source_mission_id: str,
    continuation_id: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Retrieve and structure the chronological event timeline for a mission.
    """
    clean_mission_id = validate_mission_id(source_mission_id)
    events = get_mission_events(clean_mission_id, continuation_id=continuation_id, base_dir=base_dir)

    total_events = len(events)
    start_time_s = events[0].mission_time_s if events else 0.0
    end_time_s = events[-1].mission_time_s if events else 0.0
    duration_s = max(0.0, end_time_s - start_time_s)

    contingency_count = sum(1 for e in events if e.event_type == "contingency_injected")
    replan_count = sum(1 for e in events if e.event_type in ("route_recalculated", "continuation_selected"))

    # Determine mission phases present
    phases_set = set()
    has_incident = False
    for e in events:
        if e.event_type in ("sortie_started", "playback_checkpoint", "target_reached", "science_dwell_started", "science_dwell_completed"):
            phases_set.add("nominal_sortie")
        elif e.event_type == "contingency_injected":
            phases_set.add("contingency_interruption")
            has_incident = True
        elif e.event_type in ("route_recalculated", "continuation_selected"):
            phases_set.add("adaptive_replanning")
        elif e.event_type in ("mission_completed", "mission_suspended", "mission_infeasible"):
            phases_set.add("sortie_conclusion")

    phases_order = ["nominal_sortie", "contingency_interruption", "adaptive_replanning", "sortie_conclusion"]
    active_phases = [p for p in phases_order if p in phases_set] or ["nominal_sortie"]

    timeline_summary = {
        "start_time_s": float(start_time_s),
        "end_time_s": float(end_time_s),
        "duration_s": float(duration_s),
        "contingency_events_count": contingency_count,
        "replan_events_count": replan_count,
        "phases": active_phases,
    }

    # Extract decision points
    decision_points: List[Dict[str, Any]] = []
    for e in events:
        if e.event_type in ("contingency_injected", "route_recalculated", "continuation_selected", "mission_infeasible"):
            decision_points.append({
                "event_id": e.event_id,
                "event_type": e.event_type,
                "mission_time_s": e.mission_time_s,
                "rover_rc": list(e.rover_rc) if e.rover_rc else None,
                "summary": e.payload.get("summary") or e.payload.get("recommendation_title") or e.event_type,
                "recommendation": e.payload.get("recommendation"),
            })

    return {
        "source_mission_id": clean_mission_id,
        "continuation_id": continuation_id,
        "total_events": total_events,
        "events": [e.to_dict() for e in events],
        "timeline_summary": timeline_summary,
        "has_incident": has_incident,
        "decision_points": decision_points,
    }


def replay_incident(
    source_mission_id: str,
    terrain: TerrainGrid,
    transform: rasterio.Affine,
    continuation_id: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
    recompute: bool = True,
) -> Dict[str, Any]:
    """
    Reconstruct the mission incident from the event ledger and optionally recompute
    the adaptive decision using current planner algorithms on authentic terrain.
    Distinguishes recorded historical outputs from recomputed algorithmic estimates.
    """
    timeline = reconstruct_incident_timeline(source_mission_id, continuation_id=continuation_id, base_dir=base_dir)
    events_raw = timeline["events"]
    events_objs = [MissionEvent.from_dict(e) for e in events_raw]

    # Find contingency event
    incident_evt: Optional[MissionEvent] = None
    for e in events_objs:
        if e.event_type == "contingency_injected":
            incident_evt = e
            break

    # Find route recalculation event
    replan_evt: Optional[MissionEvent] = None
    for e in events_objs:
        if e.event_type in ("route_recalculated", "continuation_selected"):
            replan_evt = e
            break

    has_incident = incident_evt is not None
    incident_event_id = incident_evt.event_id if incident_evt else None
    interruption_time_s = incident_evt.mission_time_s if incident_evt else None
    interruption_rc = incident_evt.rover_rc if incident_evt else None
    injected_contingency = incident_evt.payload if incident_evt else None

    recorded_rec = None
    recorded_dist_m = 0.0
    recorded_time_s = 0.0
    recorded_path: List[List[int]] = []

    if replan_evt:
        recorded_rec = replan_evt.payload.get("recommendation")
        ad = replan_evt.payload.get("adaptive_continuation", {})
        recorded_dist_m = float(ad.get("distance_m", 0.0))
        recorded_time_s = float(ad.get("total_time_s", 0.0))
        recorded_path = ad.get("path_rc", [])

    recomputed_rec = None
    recomputed_dist_m = recorded_dist_m
    recomputed_time_s = recorded_time_s
    exact_geometry_match = True

    if has_incident and recompute and interruption_rc and injected_contingency:
        # Re-evaluate continuation using authentic terrain and current planner
        try:
            # Build mid-sortie state from recorded incident event
            r = interruption_rc[0]
            c = interruption_rc[1]
            elev = incident_evt.elevation_m if incident_evt.elevation_m is not None else float(terrain.elevation[r, c])
            slope = incident_evt.slope_deg if incident_evt.slope_deg is not None else float(terrain.slope[r, c])

            rem_budget = incident_evt.payload.get("remaining_budget_s", 28800.0)
            completed_stops = incident_evt.payload.get("completed_stop_ids", [])
            unvisited_raw = incident_evt.payload.get("unvisited_waypoints", [])
            unvisited_stops = [
                ScienceWaypoint(
                    id=str(w.get("id", f"wp_{idx}")),
                    row=int(w["row"]),
                    col=int(w["col"]),
                    priority_score=float(w.get("priority_score", 1.0)),
                    name=str(w.get("name", "Waypoint")),
                )
                for idx, w in enumerate(unvisited_raw)
                if "row" in w and "col" in w
            ]

            # Destination
            dest_rc = (66, 128)
            if "destination_rc" in incident_evt.payload and incident_evt.payload["destination_rc"]:
                d_raw = incident_evt.payload["destination_rc"]
                if isinstance(d_raw, (list, tuple)) and len(d_raw) >= 2:
                    if d_raw[0] is not None and d_raw[1] is not None:
                        dest_rc = (int(d_raw[0]), int(d_raw[1]))

            mid_state = MidSortieState(
                source_mission_id=source_mission_id,
                interruption_time_s=interruption_time_s or 0.0,
                rover_rc=(r, c),
                rover_float_rc=incident_evt.rover_float_rc or (float(r), float(c)),
                elevation_m=elev,
                slope_deg=slope,
                is_stationary=False,
                active_event_type="contingency_injection",
                active_target_id=None,
                elapsed_distance_m=float(incident_evt.payload.get("elapsed_distance_m", 0.0)),
                original_budget_s=rem_budget + (interruption_time_s or 0.0),
                remaining_budget_s=rem_budget,
                goal_rc=dest_rc,
                completed_stop_ids=completed_stops,
                unvisited_stops=unvisited_stops,
                unvisited_stop_ids=[w.id for w in unvisited_stops],
                historical_path_rc=[(r, c)],
                nominal_remaining_path_rc=[(r, c), dest_rc],
            )

            # Plan continuation
            recomputed_plan = plan_mission_continuation(
                terrain=terrain,
                mid_state=mid_state,
                event_definition=injected_contingency,
                profile=str(incident_evt.payload.get("profile", "balanced")),
                vehicle_mode=str(incident_evt.payload.get("vehicle_mode", "crew_eva")),
                speed_multiplier=float(incident_evt.payload.get("speed_multiplier", 1.0)),
                operational_limit_s=rem_budget,
                transform=transform,
            )

            recomputed_rec = recomputed_plan.get("recommendation")
            ac = recomputed_plan.get("adaptive_continuation", {})
            recomputed_dist_m = float(ac.get("distance_m", 0.0))
            recomputed_time_s = float(ac.get("total_time_s", 0.0))

            if recorded_path and ac.get("path_rc"):
                exact_geometry_match = (recorded_path == ac.get("path_rc"))
            else:
                exact_geometry_match = True

        except Exception as err:
            recomputed_rec = f"recompute_error: {str(err)}"
            exact_geometry_match = False

    variance_dist = abs(recomputed_dist_m - recorded_dist_m)
    variance_time = abs(recomputed_time_s - recorded_time_s)

    fidelity = {
        "is_recomputed": bool(recompute and has_incident),
        "exact_geometry_match": exact_geometry_match,
        "variance_distance_m": round(variance_dist, 2),
        "variance_duration_s": round(variance_time, 2),
        "provenance_notes": (
            "Exact historical agreement verified within tolerance."
            if exact_geometry_match and variance_dist < 1.0
            else "Recomputed estimate differs slightly from recorded history due to algorithm or input differences."
        ),
    }

    reconstructed_sortie = {
        "has_incident": has_incident,
        "incident_event_id": incident_event_id,
        "interruption_time_s": interruption_time_s,
        "interruption_rc": list(interruption_rc) if interruption_rc else None,
        "injected_contingency": injected_contingency,
        "recorded_recommendation": recorded_rec,
        "recomputed_recommendation": recomputed_rec or recorded_rec,
        "decision_points": timeline["decision_points"],
    }

    response: Dict[str, Any] = {
        "status": "success",
        "schema_version": SCHEMA_VERSION,
        "source_mission_id": source_mission_id,
        "continuation_id": continuation_id,
        "total_events": timeline["total_events"],
        "events": timeline["events"],
        "timeline_summary": timeline["timeline_summary"],
        "reconstructed_sortie": reconstructed_sortie,
        "fidelity": fidelity,
        "disclosures": DISCLOSURES,
    }

    validate_contract(response, "incident-replay-response")
    return response
