"""
MarsWalk 2.0 — Milestone 10E: Mission Science Report & Export Dashboard Engine.
Assembles validated, reproducible mission science reports combining:
  1. Mission Plan & Routing Trajectory Metrics
  2. Waypoint & Sampling Target Dwell Times
  3. Sortie Black-Box Event Ledger History
  4. Source-Labelled Martian Environmental Intelligence (In-Situ vs Modelled)
  5. Scientific Provenance & Operational Disclaimers

Outputs self-contained, print-friendly HTML and companion machine-readable JSON
validated against schemas/api/v1/mission-science-report.schema.json.
"""

from __future__ import annotations

import os
import re
import html
import json
import uuid
import math
import datetime
from pathlib import Path
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
    kelvin_to_celsius,
)

REPORT_SOFTWARE_VERSION = "2.0.0"
SAFE_REPORT_ID_REGEX = re.compile(r"^rep_[a-zA-Z0-9_-]{3,64}$")

NASA_OPERATIONAL_DISCLAIMER = (
    "DISCLAIMER: MarsWalk modeled routes, traverse costs, and environmental telemetry are for "
    "engineering analysis, mission trade studies, and simulation purposes only. They are not certified "
    "operationally safe for crewed surface exploration without real-time mission ops verification."
)


class MissionReportError(Exception):
    """Exception raised for report assembly or export errors."""

    def __init__(self, message: str, status_code: int = 400, error_code: str = "ERR_MISSION_REPORT"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def generate_report_id(mission_id: Optional[str] = None) -> str:
    """Generate a clean, reproducible report identifier."""
    prefix = "rep_"
    if mission_id:
        clean_mid = re.sub(r"[^a-zA-Z0-9_]", "_", mission_id)[:24]
        if clean_mid.startswith("m_"):
            clean_mid = clean_mid[2:]
        prefix = f"rep_{clean_mid}_"
    uid = uuid.uuid4().hex[:8]
    return f"{prefix}{uid}"


def get_current_iso_time() -> str:
    """Return UTC timestamp in ISO 8601 format."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def escape_txt(val: Any) -> str:
    """Safely escape text for HTML output, with clean fallback for None/empty."""
    if val is None:
        return "<em>N/A</em>"
    s = str(val)
    if not s.strip():
        return "<em>N/A</em>"
    return html.escape(s)


def assemble_mission_report(
    mission_data_or_id: Union[str, Dict[str, Any]],
    route_result: Optional[Dict[str, Any]] = None,
    terrain: Optional[Any] = None,
    transform: Optional[Any] = None,
    weather_site: str = "jezero_crater",
    weather_snapshot: Optional[Dict[str, Any]] = None,
    events_dir: Optional[Union[str, Path]] = None,
    missions_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Assemble an authoritative, validated Mission Science Report dictionary.

    Args:
        mission_data_or_id: Mission ID string or dictionary containing saved mission definition.
        route_result: Optional precomputed RouteResult dictionary from active simulation or planner.
        terrain: Optional TerrainGrid for elevation and slope lookups.
        transform: Optional rasterio affine transform for coordinate projections.
        weather_site: Target meteorological observation site ID (default 'jezero_crater').
        weather_snapshot: Optional pre-fetched weather report dictionary.
        events_dir: Optional custom directory path for mission event ledgers.
        missions_dir: Optional custom directory path for saved mission definitions.

    Returns:
        Validated report dictionary compliant with mission-science-report.schema.json.
    """
    # 1. Resolve Mission Data
    mission_id = ""
    mission_name = "Ad-Hoc Exploration Traverse"
    mission_desc: Optional[str] = None
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
            mission_desc = saved.get("description")
            canonical_plan = saved.get("canonical_mission", {})
            fingerprint = saved.get("input_fingerprint")
            terrain_dataset_id = saved.get("terrain_dataset_id", TERRAIN_DATASET_ID)
            model_version = saved.get("model_version", "2.0.0")
            assumptions_version = saved.get("assumptions_version", "1.0.0")
        except WorkspaceError as err:
            raise MissionReportError(f"Failed loading mission '{mission_data_or_id}': {err.message}", err.status_code)
    elif isinstance(mission_data_or_id, dict):
        mission_id = mission_data_or_id.get("mission_id") or f"adhoc_{uuid.uuid4().hex[:8]}"
        mission_name = mission_data_or_id.get("name") or mission_data_or_id.get("mission_name") or "Ad-Hoc Sortie"
        mission_desc = mission_data_or_id.get("description")
        canonical_plan = mission_data_or_id.get("canonical_mission") or mission_data_or_id
        fingerprint = mission_data_or_id.get("input_fingerprint")
        terrain_dataset_id = mission_data_or_id.get("terrain_dataset_id", TERRAIN_DATASET_ID)
        model_version = mission_data_or_id.get("model_version", "2.0.0")
        assumptions_version = mission_data_or_id.get("assumptions_version", "1.0.0")
    else:
        raise MissionReportError("mission_data_or_id must be a string ID or dict", 400)

    # 2. Extract and Normalize Plan Summary
    start_pt = canonical_plan.get("start", {})
    goal_pt = canonical_plan.get("goal", {})
    stops_list = canonical_plan.get("stops", [])
    vehicle_mode = canonical_plan.get("vehicle_mode", "crew_eva")
    profile = canonical_plan.get("profile", "conservative")
    speed_mult = canonical_plan.get("speed_multiplier", 1.0)
    optimize_stops = canonical_plan.get("optimize_stops", False)

    start_r = int(start_pt.get("row", 0)) if "row" in start_pt else None
    start_c = int(start_pt.get("col", 0)) if "col" in start_pt else None
    goal_r = int(goal_pt.get("row", 0)) if "row" in goal_pt else None
    goal_c = int(goal_pt.get("col", 0)) if "col" in goal_pt else None

    # Determine elevation if terrain available
    start_elev = None
    goal_elev = None
    if terrain is not None:
        try:
            if start_r is not None and start_c is not None:
                start_elev = round(float(terrain.elevation[start_r, start_c]), 2)
            if goal_r is not None and goal_c is not None:
                goal_elev = round(float(terrain.elevation[goal_r, goal_c]), 2)
        except Exception:
            pass

    plan_summary = {
        "start": {
          "name": start_pt.get("name", "Landing Site / Hab"),
          "row": start_r if start_r is not None else 0,
          "col": start_c if start_c is not None else 0,
          "lat_deg": start_pt.get("lat_deg"),
          "lon_deg": start_pt.get("lon_deg"),
          "elevation_m": start_elev,
        },
        "goal": {
          "name": goal_pt.get("name", "Primary Science Outpost / Egress"),
          "row": goal_r if goal_r is not None else 0,
          "col": goal_c if goal_c is not None else 0,
          "lat_deg": goal_pt.get("lat_deg"),
          "lon_deg": goal_pt.get("lon_deg"),
          "elevation_m": goal_elev,
        },
        "waypoints_count": len(stops_list),
        "vehicle_mode": vehicle_mode,
        "profile": profile,
        "speed_multiplier": float(speed_mult) if speed_mult is not None else 1.0,
        "optimize_stops": bool(optimize_stops),
    }

    # 3. Read Sortie Black-Box Event Ledger
    ledger_events: List[MissionEvent] = []
    has_contingencies = False
    continuation_count = 0
    recent_events_summary: List[Dict[str, Any]] = []

    if mission_id:
        try:
            ledger_events = get_mission_events(mission_id, base_dir=events_dir)
        except Exception:
            ledger_events = []

    ledger_present = len(ledger_events) > 0
    reached_stops: set[str] = set()

    for evt in ledger_events:
        if evt.event_type == "contingency_injected":
            has_contingencies = True
        elif evt.event_type == "continuation_selected":
            continuation_count += 1
        elif evt.event_type in ("target_reached", "science_dwell_completed"):
            stop_ref = evt.payload.get("target_id") or evt.payload.get("stop_id") or evt.payload.get("name")
            if stop_ref:
                reached_stops.add(str(stop_ref))

    for evt in ledger_events[-10:]:
        detail_msg = evt.payload.get("message") or evt.payload.get("description") or evt.payload.get("reason")
        recent_events_summary.append({
            "event_id": evt.event_id,
            "event_type": evt.event_type,
            "mission_time_s": round(float(evt.mission_time_s), 1),
            "playback_elapsed_s": round(float(evt.playback_elapsed_s), 1) if evt.playback_elapsed_s is not None else None,
            "route_variant": evt.route_variant,
            "continuation_id": evt.continuation_id,
            "details": str(detail_msg) if detail_msg else None,
        })

    # Determine mission status
    mission_status = "nominal"
    if has_contingencies:
        mission_status = "continued" if continuation_count > 0 else "disrupted"
    elif any(e.event_type == "mission_completed" for e in ledger_events):
        mission_status = "completed"
    elif any(e.event_type == "mission_infeasible" for e in ledger_events):
        mission_status = "infeasible"
    elif not route_result and not ledger_present:
        mission_status = "incomplete"

    # 4. Resolve Waypoints & Stops
    stop_metrics: List[Dict[str, Any]] = []
    total_dwell_s = 0.0

    for idx, stop in enumerate(stops_list):
        sid = str(stop.get("id") or f"stop_{idx+1}")
        sname = str(stop.get("name") or f"Science Waypoint {idx+1}")
        sr = int(stop.get("row", 0))
        sc = int(stop.get("col", 0))
        sdwell = float(stop.get("dwell_time_s", 900.0))
        total_dwell_s += sdwell

        selev = None
        if terrain is not None:
            try:
                selev = round(float(terrain.elevation[sr, sc]), 2)
            except Exception:
                pass

        status = "planned"
        if sid in reached_stops or sname in reached_stops:
            status = "reached"
        elif any(e.event_type == "science_dwell_started" and (e.payload.get("stop_id") == sid or e.payload.get("target_id") == sid) for e in ledger_events):
            status = "in_progress"

        stop_metrics.append({
            "stop_id": sid,
            "name": sname,
            "row": sr,
            "col": sc,
            "dwell_time_s": sdwell,
            "status": status,
            "elevation_m": selev,
            "arrival_time_s": stop.get("arrival_time_s"),
            "priority_score": stop.get("priority_score"),
        })

    # 5. Extract Mobility Metrics (From precomputed route_result or recalculate if possible)
    mobility: Dict[str, Any] = {
        "total_distance_m": None,
        "total_cost": None,
        "total_duration_s": None,
        "traverse_duration_s": None,
        "total_dwell_s": round(total_dwell_s, 1),
        "min_elevation_m": None,
        "max_elevation_m": None,
        "elevation_gain_m": None,
        "max_slope_deg": None,
        "mean_slope_deg": None,
        "is_computed": False,
    }

    if route_result and isinstance(route_result, dict):
        mobility["total_distance_m"] = round(float(route_result.get("total_distance_m") or route_result.get("distance_m", 0.0)), 2)
        mobility["total_cost"] = round(float(route_result.get("total_cost") or route_result.get("cost", 0.0)), 2)
        
        # Duration separation
        tot_dur = route_result.get("total_duration_s") or route_result.get("duration_s")
        trav_dur = route_result.get("traverse_duration_s")
        if tot_dur is not None:
            mobility["total_duration_s"] = round(float(tot_dur), 1)
        if trav_dur is not None:
            mobility["traverse_duration_s"] = round(float(trav_dur), 1)
        elif tot_dur is not None:
            mobility["traverse_duration_s"] = round(max(0.0, float(tot_dur) - total_dwell_s), 1)

        mobility["min_elevation_m"] = route_result.get("min_elevation_m")
        mobility["max_elevation_m"] = route_result.get("max_elevation_m")
        mobility["elevation_gain_m"] = route_result.get("elevation_gain_m")
        mobility["max_slope_deg"] = route_result.get("max_slope_deg")
        mobility["mean_slope_deg"] = route_result.get("mean_slope_deg")
        mobility["is_computed"] = True
    elif terrain is not None and start_r is not None and start_c is not None and goal_r is not None and goal_c is not None:
        # If route not precomputed but terrain is provided, attempt minimal safe calculation
        try:
            from marswalk.core.planner import plan_route, PlannerConfig
            cfg = PlannerConfig(
                step_size=20.0,
                max_slope=15.0 if profile == "conservative" else 20.0,
                speed_multiplier=float(speed_mult),
            )
            res = plan_route((start_r, start_c), (goal_r, goal_c), terrain, cfg)
            if res and res.path:
                mobility["total_distance_m"] = round(float(res.distance_m), 2)
                mobility["total_cost"] = round(float(res.cost), 2)
                mobility["traverse_duration_s"] = round(float(res.duration_s), 1)
                mobility["total_duration_s"] = round(float(res.duration_s) + total_dwell_s, 1)
                mobility["min_elevation_m"] = round(float(res.min_elevation), 2)
                mobility["max_elevation_m"] = round(float(res.max_elevation), 2)
                mobility["elevation_gain_m"] = round(float(res.elevation_gain), 2)
                mobility["max_slope_deg"] = round(float(res.max_slope_deg), 2)
                mobility["mean_slope_deg"] = round(float(res.mean_slope_deg), 2)
                mobility["is_computed"] = True
        except Exception:
            # Leave as None (safe handling of incomplete calculation)
            mobility["is_computed"] = False

    # 6. Environmental Context Intelligence
    env_context: Optional[Dict[str, Any]] = None
    if weather_snapshot:
        raw_env = weather_snapshot
    else:
        try:
            wm = get_weather_manager()
            raw_env = wm.get_weather(site_id=weather_site, force_refresh=False)
        except Exception:
            raw_env = None

    if raw_env and isinstance(raw_env, dict):
        measures = raw_env.get("measurements", {})
        temp_k = measures.get("air_temperature_k")
        temp_c = measures.get("air_temperature_c")
        if temp_c is None and temp_k is not None:
            temp_c = kelvin_to_celsius(temp_k)

        source_meta = raw_env.get("source_metadata", {})
        env_context = {
            "site_id": raw_env.get("site_id", weather_site),
            "site_name": raw_env.get("site_name", "Martian Surface"),
            "data_type": raw_env.get("data_type", "IN_SITU_OBSERVATION"),
            "freshness_status": raw_env.get("freshness_status", "ACTIVE_MISSION_CADENCE"),
            "observation_sol": raw_env.get("observation_sol"),
            "observation_time_utc": raw_env.get("observation_time_utc"),
            "atmospheric_pressure_pa": measures.get("atmospheric_pressure_pa"),
            "air_temperature_c": temp_c,
            "wind_speed_m_s": measures.get("wind_speed_m_s"),
            "optical_depth_tau": measures.get("optical_depth_tau"),
            "provenance_institution": source_meta.get("institution", "NASA / PDS Atmospheres Node"),
            "provenance_url": source_meta.get("pds_archive_url") or source_meta.get("archive_url") or "https://pds-atmospheres.nmsu.edu",
            "disclosures": raw_env.get("disclosures", []),
        }

    # 7. Provenance & Safety Audit
    data_sources = [
        "USGS Astrogeology Science Center: CTX Digital Terrain Model (20m/px, Jezero Crater)",
        "Mars Orbiter Laser Altimeter (MOLA) IAU 2000 Mars Reference Sphere (R=3396190.0m)",
    ]
    if env_context:
        data_sources.append(f"{env_context['provenance_institution']} ({env_context['data_type']})")

    notes: List[str] = []
    if mobility["is_computed"]:
        notes.append("Mobility distance, traversal durations, and slopes calculated via A* cost surface.")
    else:
        notes.append("Mobility metrics are pending traversal calculation or incomplete.")
    if ledger_present:
        notes.append(f"Black-box event ledger correlated ({len(ledger_events)} operational events recorded).")
    else:
        notes.append("No active telemetry recorded in black-box ledger for this mission.")

    provenance_audit = {
        "is_modeled_estimate": True,
        "recomputed_metrics": not bool(route_result),
        "data_sources": data_sources,
        "planned_vs_observed_notes": notes,
        "disclaimers": [
            NASA_OPERATIONAL_DISCLAIMER,
            "Terrain slope thresholds and mobility limits assume uncrewed or pressurized rover EVA envelopes.",
            "Weather snapshots represent discrete local meteorological readings or climatology models and do not predict convective mesoscale storms.",
        ],
    }

    report_id = generate_report_id(mission_id)
    report_dict: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at_utc": get_current_iso_time(),
        "mission_id": mission_id,
        "mission_name": mission_name,
        "mission_description": mission_desc,
        "mission_status": mission_status,
        "reproducibility_manifest": {
            "terrain_dataset_id": terrain_dataset_id,
            "terrain_sha256": terrain_sha256,
            "model_version": model_version,
            "software_version": REPORT_SOFTWARE_VERSION,
            "input_fingerprint": fingerprint,
            "assumptions_version": assumptions_version,
        },
        "plan_summary": plan_summary,
        "mobility_metrics": mobility,
        "stop_metrics": stop_metrics,
        "sortie_ledger_summary": {
            "total_events_recorded": len(ledger_events),
            "ledger_present": ledger_present,
            "has_contingencies": has_contingencies,
            "continuation_count": continuation_count,
            "recent_events": recent_events_summary,
        },
        "environmental_context": env_context,
        "provenance_audit": provenance_audit,
    }

    # Validate against JSON schema contract
    sanitized = sanitize_for_json(report_dict)
    is_valid, errs = validate_contract(sanitized, "mission-science-report")
    if not is_valid:
        raise ContractValidationError(
            f"Mission Science Report contract validation failed: {errs}",
            errors=errs,
            schema_name="mission-science-report",
        )

    return sanitized


def generate_mission_report_html(report: Dict[str, Any]) -> str:
    """
    Render a self-contained, publication-ready, print-friendly HTML document from a validated report dictionary.
    All user strings are strictly escaped against XSS attacks.
    """
    rep_id = escape_txt(report.get("report_id"))
    gen_time = escape_txt(report.get("generated_at_utc"))
    m_id = escape_txt(report.get("mission_id"))
    m_name = escape_txt(report.get("mission_name"))
    m_desc = escape_txt(report.get("mission_description"))
    m_status = report.get("mission_status", "nominal").upper()

    rep_man = report.get("reproducibility_manifest", {})
    plan = report.get("plan_summary", {})
    start = plan.get("start", {})
    goal = plan.get("goal", {})
    mob = report.get("mobility_metrics", {})
    stops = report.get("stop_metrics", [])
    ledger = report.get("sortie_ledger_summary", {})
    env = report.get("environmental_context") or {}
    prov = report.get("provenance_audit", {})

    status_color = "#3b82f6"  # blue
    if m_status == "COMPLETED":
        status_color = "#10b981"
    elif m_status in ("DISRUPTED", "INFEASIBLE"):
        status_color = "#ef4444"
    elif m_status == "CONTINUED":
        status_color = "#f59e0b"

    # Stops table rows
    stop_rows = []
    for s in stops:
        s_elev = f"{s.get('elevation_m'):.1f} m" if s.get("elevation_m") is not None else "N/A"
        stop_rows.append(f"""
        <tr>
          <td><strong>{escape_txt(s.get('stop_id'))}</strong></td>
          <td>{escape_txt(s.get('name'))}</td>
          <td>({s.get('row', 0)}, {s.get('col', 0)})</td>
          <td>{s.get('dwell_time_s', 0):.0f} s ({s.get('dwell_time_s', 0)/60:.1f} min)</td>
          <td>{s_elev}</td>
          <td><span class="badge badge-{s.get('status', 'planned')}">{s.get('status', 'planned').upper()}</span></td>
        </tr>""")
    stops_html = "".join(stop_rows) if stop_rows else "<tr><td colspan='6' class='text-center text-muted'>No science stops defined in plan.</td></tr>"

    # Ledger table rows
    ledger_rows = []
    for e in ledger.get("recent_events", []):
        dtl = escape_txt(e.get("details")) if e.get("details") else "<em>nominal checkpoint</em>"
        elapsed_val = f"{e.get('playback_elapsed_s'):.1f} s" if e.get("playback_elapsed_s") is not None else "N/A"
        ledger_rows.append(f"""
        <tr>
          <td><code>{escape_txt(e.get('event_id'))}</code></td>
          <td><span class="badge badge-event">{escape_txt(e.get('event_type'))}</span></td>
          <td>T+{e.get('mission_time_s', 0):.1f}s</td>
          <td>{elapsed_val}</td>
          <td>{escape_txt(e.get('route_variant'))}</td>
          <td>{dtl}</td>
        </tr>""")
    ledger_html = "".join(ledger_rows) if ledger_rows else "<tr><td colspan='6' class='text-center text-muted'>No black-box events logged for this sortie.</td></tr>"

    # Weather content
    if env:
        p_val = f"{env.get('atmospheric_pressure_pa'):.2f} Pa" if env.get("atmospheric_pressure_pa") is not None else "N/A"
        t_val = f"{env.get('air_temperature_c'):.1f} °C" if env.get("air_temperature_c") is not None else "N/A"
        w_val = f"{env.get('wind_speed_m_s'):.1f} m/s" if env.get("wind_speed_m_s") is not None else "N/A"
        tau_val = f"{env.get('optical_depth_tau'):.2f}" if env.get("optical_depth_tau") is not None else "N/A"
        sol_val = f"Sol {env.get('observation_sol')}" if env.get("observation_sol") is not None else "N/A"
        env_badge = "badge-insitu" if "IN_SITU" in str(env.get("data_type")) else "badge-climatology"

        disclosures_list = "".join(f"<li>{escape_txt(d)}</li>" for d in env.get("disclosures", []))
        weather_section_html = f"""
        <div class="card weather-card">
          <div class="card-header">
            <h3>Martian Environmental Intelligence</h3>
            <span class="badge {env_badge}">{escape_txt(env.get('data_type'))}</span>
          </div>
          <div class="card-body">
            <div class="grid-4">
              <div class="metric-box">
                <span class="metric-label">Atmospheric Pressure</span>
                <span class="metric-value">{p_val}</span>
                <span class="metric-sub">{sol_val}</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Air Temperature</span>
                <span class="metric-value">{t_val}</span>
                <span class="metric-sub">{escape_txt(env.get('site_name'))}</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Wind Velocity</span>
                <span class="metric-value">{w_val}</span>
                <span class="metric-sub">Surface Boundary Layer</span>
              </div>
              <div class="metric-box">
                <span class="metric-label">Optical Depth (&tau;)</span>
                <span class="metric-value">{tau_val}</span>
                <span class="metric-sub">Atmospheric Column</span>
              </div>
            </div>
            <div class="meta-row">
              <strong>Source Provenance:</strong> {escape_txt(env.get('provenance_institution'))} &mdash;
              <a href="{escape_txt(env.get('provenance_url'))}" target="_blank" rel="noopener">{escape_txt(env.get('provenance_url'))}</a>
              <span class="badge badge-outline">{escape_txt(env.get('freshness_status'))}</span>
            </div>
            {f'<ul class="disclosures-list">{disclosures_list}</ul>' if disclosures_list else ''}
          </div>
        </div>
        """
    else:
        weather_section_html = """
        <div class="card weather-card">
          <div class="card-header">
            <h3>Martian Environmental Intelligence</h3>
            <span class="badge badge-outline">UNAVAILABLE</span>
          </div>
          <div class="card-body">
            <p class="text-muted">No environmental observation snapshot was attached to this mission record.</p>
          </div>
        </div>
        """

    # Mobility values
    dist_val = f"{mob.get('total_distance_m'):,.1f} m" if mob.get("total_distance_m") is not None else "N/A"
    cost_val = f"{mob.get('total_cost'):,.1f}" if mob.get("total_cost") is not None else "N/A"
    tot_dur_val = f"{mob.get('total_duration_s'):,.1f} s ({mob.get('total_duration_s',0)/60:.1f} min)" if mob.get("total_duration_s") is not None else "N/A"
    trav_dur_val = f"{mob.get('traverse_duration_s'):,.1f} s ({mob.get('traverse_duration_s',0)/60:.1f} min)" if mob.get("traverse_duration_s") is not None else "N/A"
    dwell_val = f"{mob.get('total_dwell_s', 0):,.1f} s ({mob.get('total_dwell_s',0)/60:.1f} min)"
    max_slope_val = f"{mob.get('max_slope_deg'):.1f}&deg;" if mob.get("max_slope_deg") is not None else "N/A"
    mean_slope_val = f"{mob.get('mean_slope_deg'):.1f}&deg;" if mob.get("mean_slope_deg") is not None else "N/A"
    elev_gain_val = f"{mob.get('elevation_gain_m'):.1f} m" if mob.get("elevation_gain_m") is not None else "N/A"

    disclaimers_html = "".join(f"<li>{escape_txt(d)}</li>" for d in prov.get("disclaimers", []))
    sources_html = "".join(f"<li>{escape_txt(s)}</li>" for s in prov.get("data_sources", []))
    notes_html = "".join(f"<li>{escape_txt(n)}</li>" for n in prov.get("planned_vs_observed_notes", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MarsWalk Mission Science Report &mdash; {m_name}</title>
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f293d;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #ff4d2e;
      --accent-subtle: rgba(255, 77, 46, 0.15);
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 2rem 1.5rem;
    }}
    .container {{
      max-width: 1100px;
      margin: 0 auto;
    }}
    header.report-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid var(--accent);
      padding-bottom: 1.5rem;
      margin-bottom: 2rem;
    }}
    .header-titles h1 {{
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: #fff;
    }}
    .header-titles .subtitle {{
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }}
    .header-meta {{
      text-align: right;
      font-family: var(--font-mono);
      font-size: 0.85rem;
    }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      font-family: var(--font-mono);
    }}
    .badge-status {{ background: {status_color}; color: #fff; }}
    .badge-insitu {{ background: #059669; color: #fff; }}
    .badge-climatology {{ background: #d97706; color: #fff; }}
    .badge-outline {{ border: 1px solid var(--text-muted); color: var(--text-muted); }}
    .badge-planned {{ background: #374151; color: #d1d5db; }}
    .badge-reached {{ background: #059669; color: #ecfdf5; }}
    .badge-in_progress {{ background: #d97706; color: #fff; }}
    .badge-event {{ background: #1f2937; color: #93c5fd; border: 1px solid #374151; }}
    
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      margin-bottom: 1.5rem;
      overflow: hidden;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(255, 255, 255, 0.02);
      padding: 0.75rem 1.25rem;
      border-bottom: 1px solid var(--card-border);
    }}
    .card-header h3 {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #e5e7eb;
    }}
    .card-body {{ padding: 1.25rem; }}

    .grid-4 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }}
    .metric-box {{
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      padding: 0.85rem;
      display: flex;
      flex-direction: column;
    }}
    .metric-label {{
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}
    .metric-value {{
      font-size: 1.4rem;
      font-weight: 700;
      color: #fff;
      font-family: var(--font-mono);
      margin: 0.25rem 0;
    }}
    .metric-sub {{
      font-size: 0.8rem;
      color: #9ca3af;
    }}

    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      text-align: left;
    }}
    table.data-table th {{
      background: rgba(0, 0, 0, 0.3);
      padding: 0.6rem 0.75rem;
      border-bottom: 2px solid var(--card-border);
      color: var(--text-muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    table.data-table td {{
      padding: 0.65rem 0.75rem;
      border-bottom: 1px solid var(--card-border);
    }}
    table.data-table tr:hover {{
      background: rgba(255, 255, 255, 0.02);
    }}
    .meta-row {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.75rem;
    }}
    .meta-row a {{ color: #60a5fa; text-decoration: none; }}
    .meta-row a:hover {{ text-decoration: underline; }}
    ul.disclosures-list, ul.provenance-list {{
      list-style-type: square;
      padding-left: 1.5rem;
      font-size: 0.85rem;
      color: #d1d5db;
      margin-top: 0.5rem;
    }}
    ul.disclosures-list li, ul.provenance-list li {{ margin-bottom: 0.25rem; }}
    .text-center {{ text-align: center; }}
    .text-muted {{ color: var(--text-muted); }}

    /* Print media query */
    @media print {{
      body {{
        background: #fff !important;
        color: #111 !important;
        padding: 0;
      }}
      .card {{
        background: #fff !important;
        border: 1px solid #ccc !important;
        color: #111 !important;
        break-inside: avoid;
      }}
      .card-header {{
        background: #f3f4f6 !important;
        border-bottom: 1px solid #ccc !important;
      }}
      .card-header h3 {{ color: #111 !important; }}
      .metric-box {{
        background: #f9fafb !important;
        border: 1px solid #ddd !important;
      }}
      .metric-value {{ color: #111 !important; }}
      table.data-table th {{
        background: #f3f4f6 !important;
        border-bottom: 1px solid #999 !important;
        color: #333 !important;
      }}
      table.data-table td {{ border-bottom: 1px solid #ddd !important; }}
      header.report-header {{ border-bottom: 2px solid #111 !important; }}
      .header-titles h1 {{ color: #111 !important; }}
      .badge {{ border: 1px solid #333; }}
      .no-print {{ display: none !important; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="report-header">
      <div class="header-titles">
        <h1>MarsWalk 2.0 &mdash; Mission Science Report</h1>
        <div class="subtitle">{m_name} &bull; Mission ID: <code>{m_id}</code></div>
      </div>
      <div class="header-meta">
        <div><span class="badge badge-status">{m_status}</span></div>
        <div style="margin-top: 0.5rem;">Report ID: <code>{rep_id}</code></div>
        <div>Generated: {gen_time}</div>
      </div>
    </header>

    <!-- Reproducibility & Baseline Overview -->
    <div class="card">
      <div class="card-header">
        <h3>Trajectory Metadata & Reproducibility</h3>
        <span class="badge badge-outline">VERIFIED DTM 20M</span>
      </div>
      <div class="card-body">
        <div class="grid-4">
          <div class="metric-box">
            <span class="metric-label">Start Point</span>
            <span class="metric-value">{escape_txt(start.get('name'))}</span>
            <span class="metric-sub">R:{start.get('row')} C:{start.get('col')} ({start.get('elevation_m', 'N/A')} m)</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Goal Destination</span>
            <span class="metric-value">{escape_txt(goal.get('name'))}</span>
            <span class="metric-sub">R:{goal.get('row')} C:{goal.get('col')} ({goal.get('elevation_m', 'N/A')} m)</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Vehicle Mode & Profile</span>
            <span class="metric-value">{escape_txt(plan.get('vehicle_mode'))}</span>
            <span class="metric-sub">{escape_txt(plan.get('profile'))} ({plan.get('speed_multiplier')}x speed)</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Terrain Dataset & Hash</span>
            <span class="metric-value" style="font-size: 0.95rem;">{escape_txt(rep_man.get('terrain_dataset_id'))}</span>
            <span class="metric-sub">SHA-256: {escape_txt(str(rep_man.get('terrain_sha256'))[:16])}...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Mobility & Trajectory Metrics -->
    <div class="card">
      <div class="card-header">
        <h3>Mobility & Energy Metrics</h3>
        <span class="badge badge-outline">{"A* OPTIMIZED" if mob.get("is_computed") else "UNCOMPUTED"}</span>
      </div>
      <div class="card-body">
        <div class="grid-4">
          <div class="metric-box">
            <span class="metric-label">Total Traversal Distance</span>
            <span class="metric-value">{dist_val}</span>
            <span class="metric-sub">Cost Function Score: {cost_val}</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Total Mission Duration</span>
            <span class="metric-value">{tot_dur_val}</span>
            <span class="metric-sub">Traverse: {trav_dur_val} | Dwell: {dwell_val}</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Elevation Gain / Relief</span>
            <span class="metric-value">{elev_gain_val}</span>
            <span class="metric-sub">Min: {mob.get('min_elevation_m', 'N/A')} m &bull; Max: {mob.get('max_elevation_m', 'N/A')} m</span>
          </div>
          <div class="metric-box">
            <span class="metric-label">Slope Envelope</span>
            <span class="metric-value">{max_slope_val}</span>
            <span class="metric-sub">Mean Gradient: {mean_slope_val}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Science Stops & Dwell Times -->
    <div class="card">
      <div class="card-header">
        <h3>Science Waypoints & Sampling Dwell Sequence</h3>
        <span class="badge badge-outline">{len(stops)} STOPS DEFINED</span>
      </div>
      <div class="card-body" style="padding: 0;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Waypoint ID</th>
              <th>Target Site Name</th>
              <th>DTM Coordinates (Row, Col)</th>
              <th>Planned Dwell</th>
              <th>Elevation</th>
              <th>Execution Status</th>
            </tr>
          </thead>
          <tbody>
            {stops_html}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Martian Environmental Intelligence -->
    {weather_section_html}

    <!-- Black-Box Mission Event Ledger -->
    <div class="card">
      <div class="card-header">
        <h3>Sortie Black-Box Mission Event Ledger</h3>
        <span class="badge badge-outline">{ledger.get('total_events_recorded', 0)} EVENTS RECORDED</span>
      </div>
      <div class="card-body" style="padding: 0;">
        <table class="data-table">
          <thead>
            <tr>
              <th>Event ID</th>
              <th>Event Type</th>
              <th>Mission Time</th>
              <th>Playback Elapsed</th>
              <th>Route Variant</th>
              <th>Telemetry / Notes</th>
            </tr>
          </thead>
          <tbody>
            {ledger_html}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Provenance & Disclaimers -->
    <div class="card">
      <div class="card-header">
        <h3>Scientific Provenance, Verification & Disclaimers</h3>
      </div>
      <div class="card-body">
        <h4>Analytical Data Sources</h4>
        <ul class="provenance-list">{sources_html}</ul>
        
        <h4 style="margin-top: 1rem;">Verification & Observation Notes</h4>
        <ul class="provenance-list">{notes_html}</ul>

        <h4 style="margin-top: 1rem; color: #f87171;">Operational & Safety Disclaimers</h4>
        <ul class="disclosures-list" style="color: #fca5a5;">{disclaimers_html}</ul>
      </div>
    </div>

    <footer style="text-align: center; color: var(--text-muted); font-size: 0.8rem; margin-top: 2rem;">
      MarsWalk 2.0 Project Atlas &bull; Space Apps Challenge &bull; NASA Planetary Data System &bull; Offline Reproducible Report
    </footer>
  </div>
</body>
</html>"""
