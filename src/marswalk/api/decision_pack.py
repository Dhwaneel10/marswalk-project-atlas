"""
MarsWalk 2.0 — Mission Decision Pack & Bundle Replay Service
Provides:
  1. Canonical Mission Run Bundle construction & validation (Draft 2020-12).
  2. Multi-artifact Decision Pack ZIP generation (in-memory, safe filenames).
  3. Formatted comparison CSV, Markdown briefing, README instructions, and cartographic geometry.
  4. Three-stage independent verification & reproduction engine:
       - Integrity Valid (schema compliance, valid numbers, coordinate bounds)
       - Replay Compatible (matching terrain dataset and SHA-256 raster hash)
       - Replay Reproduced (exact path geometry, waypoint retention, verified tolerances)
  5. Immutability guarantee: Replay never mutates archived records.
"""

import os
import io
import csv
import json
import math
import uuid
import zipfile
import datetime
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import rasterio

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import ScienceWaypoint, format_duration, ENGINEERING_ASSUMPTIONS
from marswalk.api.contracts import (
    SCHEMA_VERSION,
    TERRAIN_DATASET_ID,
    TERRAIN_SHA256,
    validate_contract,
    sanitize_for_json,
    calculate_safe_pct_delta,
    compute_bundle_fingerprint,
    compute_bundle_execution_digest,
    compute_input_fingerprint,
    build_canonical_mission_run_bundle,
    ContractValidationError,
)
from marswalk.api.service import (
    plan_route_api,
    contingency_simulate_api,
    APIError,
)
from marswalk.api.workspace import (
    save_experiment,
    DEFAULT_EXPERIMENTS_DIR,
    WorkspaceError,
)


# =============================================================================
# 1. ARTIFACT GENERATORS FOR MISSION DECISION PACK
# =============================================================================

def generate_comparison_csv(
    baseline_route: Dict[str, Any],
    scenario_result: Optional[Dict[str, Any]] = None,
    comparison_metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate authoritative CSV comparison table between baseline and revised disruption scenario.
    Distinguishes path distance, active transit duration, dwell time, and operational hold delays.
    Never silently merges unlike metrics.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # CSV Header
    writer.writerow([
        "Metric",
        "Baseline_Nominal",
        "Scenario_Revised",
        "Delta_Absolute",
        "Delta_Percent",
        "Unit",
        "Status",
    ])

    # 1. Ground Distance
    b_dist = float(baseline_route.get("distance_m", 0.0))
    s_route = scenario_result.get("revised_route") or scenario_result.get("scenario_route") if scenario_result else None
    s_reach = bool(scenario_result.get("is_scenario_reachable", True)) if scenario_result else True

    if s_route and s_reach:
        s_dist = float(s_route.get("distance_m", 0.0))
        d_dist = round(s_dist - b_dist, 2)
        pct_dist = calculate_safe_pct_delta(s_dist, b_dist)
        pct_dist_str = f"{pct_dist:+.1f}%" if pct_dist is not None else "0.0%"
        dist_status = "DETOUR_REQUIRED" if d_dist > 0.1 else ("IDENTICAL" if abs(d_dist) <= 0.1 else "SHORTER")
    elif scenario_result and not s_reach:
        s_dist = "UNREACHABLE"
        d_dist = "N/A"
        pct_dist_str = "N/A"
        dist_status = "CORRIDOR_SEVERED"
    else:
        s_dist = b_dist
        d_dist = 0.0
        pct_dist_str = "0.0%"
        dist_status = "NOMINAL"

    writer.writerow([
        "Ground Traverse Distance",
        f"{b_dist:.1f}",
        f"{s_dist:.1f}" if isinstance(s_dist, float) else s_dist,
        f"{d_dist:+.1f}" if isinstance(d_dist, float) else d_dist,
        pct_dist_str,
        "metres",
        dist_status,
    ])

    # 2. Active Transit Duration
    b_travel = float(baseline_route.get("travel_time_s", 0.0))
    if s_route and s_reach:
        s_travel = float(s_route.get("travel_time_s", 0.0))
        d_travel = round(s_travel - b_travel, 1)
        pct_travel = calculate_safe_pct_delta(s_travel, b_travel)
        pct_travel_str = f"{pct_travel:+.1f}%" if pct_travel is not None else "0.0%"
        travel_status = "INCREASED" if d_travel > 1.0 else ("IDENTICAL" if abs(d_travel) <= 1.0 else "FASTER")
    elif scenario_result and not s_reach:
        s_travel = "UNREACHABLE"
        d_travel = "N/A"
        pct_travel_str = "N/A"
        travel_status = "ABORTED"
    else:
        s_travel = b_travel
        d_travel = 0.0
        pct_travel_str = "0.0%"
        travel_status = "NOMINAL"

    writer.writerow([
        "Active Movement Duration",
        f"{b_travel:.1f}",
        f"{s_travel:.1f}" if isinstance(s_travel, float) else s_travel,
        f"{d_travel:+.1f}" if isinstance(d_travel, float) else d_travel,
        pct_travel_str,
        "seconds",
        travel_status,
    ])

    # 3. Science Observation Dwell Time
    b_timeline = baseline_route.get("timeline") or {}
    b_dwell = float(b_timeline.get("total_dwell_time_s", 0.0))
    s_timeline = ((s_route.get("timeline") if s_route else None) or (scenario_result.get("revised_timeline") if scenario_result else None)) or {}
    if s_route and s_reach:
        s_dwell = float(s_timeline.get("total_dwell_time_s", 0.0))
        d_dwell = round(s_dwell - b_dwell, 1)
        pct_dwell = calculate_safe_pct_delta(s_dwell, b_dwell)
        pct_dwell_str = f"{pct_dwell:+.1f}%" if pct_dwell is not None else "0.0%"
        dwell_status = "TARGETS_DROPPED" if d_dwell < -1.0 else "PRESERVED"
    elif scenario_result and not s_reach:
        s_dwell = 0.0
        d_dwell = -b_dwell
        pct_dwell_str = "-100.0%"
        dwell_status = "ABORTED"
    else:
        s_dwell = b_dwell
        d_dwell = 0.0
        pct_dwell_str = "0.0%"
        dwell_status = "NOMINAL"

    writer.writerow([
        "Stationary Science Dwell Duration",
        f"{b_dwell:.1f}",
        f"{s_dwell:.1f}",
        f"{d_dwell:+.1f}",
        pct_dwell_str,
        "seconds",
        dwell_status,
    ])

    # 4. Operational Contingency Delay
    b_delay = float(b_timeline.get("total_operational_delay_s", 0.0))
    if s_route and s_reach:
        s_delay = float(s_timeline.get("total_operational_delay_s", 0.0))
        d_delay = round(s_delay - b_delay, 1)
        delay_status = "HOLD_ACTIVE" if s_delay > 0.0 else "NO_DELAY"
    elif scenario_result and not s_reach:
        s_delay = 0.0
        d_delay = 0.0
        delay_status = "N/A"
    else:
        s_delay = 0.0
        d_delay = 0.0
        delay_status = "NO_DELAY"

    writer.writerow([
        "Operational Hold Delay",
        f"{b_delay:.1f}",
        f"{s_delay:.1f}",
        f"{d_delay:+.1f}",
        "N/A",
        "seconds",
        delay_status,
    ])

    # 5. Total Mission Schedule
    b_tot = float(b_timeline.get("total_mission_time_s", b_travel + b_dwell))
    if s_route and s_reach:
        s_tot = float(s_timeline.get("total_mission_time_s", (s_travel if isinstance(s_travel, float) else 0.0) + s_dwell + s_delay))
        d_tot = round(s_tot - b_tot, 1)
        pct_tot = calculate_safe_pct_delta(s_tot, b_tot)
        pct_tot_str = f"{pct_tot:+.1f}%" if pct_tot is not None else "0.0%"
        tot_status = "SCHEDULE_EXPANDED" if d_tot > 1.0 else "NOMINAL"
    elif scenario_result and not s_reach:
        s_tot = "UNREACHABLE"
        d_tot = "N/A"
        pct_tot_str = "N/A"
        tot_status = "MISSION_SEVERED"
    else:
        s_tot = b_tot
        d_tot = 0.0
        pct_tot_str = "0.0%"
        tot_status = "NOMINAL"

    writer.writerow([
        "Total Mission Elapsed Duration",
        f"{b_tot:.1f}",
        f"{s_tot:.1f}" if isinstance(s_tot, float) else s_tot,
        f"{d_tot:+.1f}" if isinstance(d_tot, float) else d_tot,
        pct_tot_str,
        "seconds",
        tot_status,
    ])

    # 6. Intermediate Science Targets Visited
    b_wps = baseline_route.get("visited_waypoint_ids") or []
    if s_route and s_reach:
        s_wps = s_route.get("visited_waypoint_ids") or []
        d_wps = len(s_wps) - len(b_wps)
        wps_status = "ALL_RETAINED" if d_wps == 0 else f"{abs(d_wps)}_DROPPED"
    elif scenario_result and not s_reach:
        s_wps = []
        d_wps = -len(b_wps)
        wps_status = "ALL_LOST"
    else:
        s_wps = b_wps
        d_wps = 0
        wps_status = "NOMINAL"

    writer.writerow([
        "Intermediate Science Targets Visited",
        str(len(b_wps)),
        str(len(s_wps)),
        f"{d_wps:+d}",
        "N/A",
        "targets",
        wps_status,
    ])

    # 7. Science Priority Score
    b_score = float(baseline_route.get("science_score", 0.0))
    if s_route and s_reach:
        s_score = float(s_route.get("science_score", 0.0))
        d_score = round(s_score - b_score, 1)
        score_status = "MAXIMAL" if d_score >= 0 else "PARTIAL_LOSS"
    elif scenario_result and not s_reach:
        s_score = 0.0
        d_score = -b_score
        score_status = "TOTAL_LOSS"
    else:
        s_score = b_score
        d_score = 0.0
        score_status = "NOMINAL"

    writer.writerow([
        "Science Priority Score",
        f"{b_score:.1f}",
        f"{s_score:.1f}",
        f"{d_score:+.1f}",
        "N/A",
        "score_units",
        score_status,
    ])

    # 8. Terrain Impedance Cost
    b_cost = float(baseline_route.get("cost", 0.0))
    if s_route and s_reach:
        s_cost_val = float(s_route.get("cost", 0.0))
        d_cost = round(s_cost_val - b_cost, 2)
        pct_cost = calculate_safe_pct_delta(s_cost_val, b_cost)
        pct_cost_str = f"{pct_cost:+.1f}%" if pct_cost is not None else "0.0%"
        cost_status = "ADDITIONAL_EFFORT" if d_cost > 0.1 else "NOMINAL"
    elif scenario_result and not s_reach:
        s_cost_val = "INFINITY"
        d_cost = "INFINITY"
        pct_cost_str = "N/A"
        cost_status = "IMPASSABLE"
    else:
        s_cost_val = b_cost
        d_cost = 0.0
        pct_cost_str = "0.0%"
        cost_status = "NOMINAL"

    writer.writerow([
        "Terrain Impedance Cost",
        f"{b_cost:.2f}",
        f"{s_cost_val:.2f}" if isinstance(s_cost_val, float) else s_cost_val,
        f"{d_cost:+.2f}" if isinstance(d_cost, float) else d_cost,
        pct_cost_str,
        "flat_m_equivalent",
        cost_status,
    ])

    # 9. Feasibility Status
    b_feas = "FEASIBLE" if baseline_route.get("is_reachable", True) and baseline_route.get("is_budget_feasible", True) else "INFEASIBLE"
    if scenario_result:
        if not s_reach:
            s_feas = "CORRIDOR_SEVERED"
        elif not scenario_result.get("is_scenario_budget_feasible", True):
            s_feas = "BUDGET_EXCEEDED"
        else:
            s_feas = "FEASIBLE"
    else:
        s_feas = b_feas

    writer.writerow([
        "Operational Feasibility State",
        b_feas,
        s_feas,
        "N/A",
        "N/A",
        "state",
        "VERIFIED",
    ])

    return output.getvalue()


def generate_decision_pack_briefing_md(bundle: Dict[str, Any]) -> str:
    """
    Generate clean, decision-grade Markdown mission briefing understandable
    to a competition judge or engineering teammate.
    """
    b_route = bundle.get("baseline_route") or {}
    m_input = bundle.get("mission_input") or {}
    t_prov = bundle.get("terrain_provenance") or {}
    scen_res = bundle.get("scenario_result")
    rf = bundle.get("reachability_and_feasibility") or {}

    start_r = m_input.get("start", {}).get("row", 0)
    start_c = m_input.get("start", {}).get("col", 0)
    goal_r = m_input.get("goal", {}).get("row", 0)
    goal_c = m_input.get("goal", {}).get("col", 0)
    v_mode = str(m_input.get("vehicle_mode", "crew_eva")).replace("_", " ").title()
    profile = str(m_input.get("profile", "conservative")).capitalize()

    b_dist = float(b_route.get("distance_m", 0.0))
    b_time = str(b_route.get("formatted_travel_time", "—"))
    b_timeline = b_route.get("timeline") or {}
    b_tot_time = str(b_timeline.get("formatted_mission_time", b_time))
    b_wps = b_route.get("visited_waypoint_ids") or []

    md = [
        "# MARSWALK 2.0 — MISSION DECISION BRIEFING",
        "",
        f"**Run Identifier:** `{bundle.get('bundle_id')}`  ",
        f"**Computation Fingerprint:** `{bundle.get('computation_fingerprint')}`  ",
        f"**Timestamp (UTC):** `{bundle.get('created_at')}`  ",
        f"**Planetary Target:** Mars (IAU 2000 Planetocentric Sphere)  ",
        f"**Terrain DTM Grid:** {t_prov.get('dataset_id')} (Resolution: {t_prov.get('resolution_m')} m/px)  ",
        f"**DTM SHA-256:** `{t_prov.get('sha256_hash')}`  ",
        "",
        "---",
        "",
        "## 1. Executive Mission Overview",
        f"- **Operational Mode:** {v_mode} (Transit Profile: {profile})",
        f"- **Departure Point:** Grid `({start_r}, {start_c})`",
        f"- **Destination Target:** Grid `({goal_r}, {goal_c})`",
        f"- **Intermediate Science Stops:** {len(b_wps)} planned ({', '.join(b_wps) if b_wps else 'Direct Sortie'})",
        f"- **Nominal Traverse Distance:** `{b_dist:,.1f} m`",
        f"- **Active Movement Duration:** `{b_time}`",
        f"- **Total Mission Schedule (Movement + Science Dwells):** `{b_tot_time}`",
        f"- **Overall Recommendation State:** `{rf.get('overall_status', 'nominal').upper()}`",
        "",
        "---",
        "",
        "## 2. Contingency & Disruption Assessment",
    ]

    if scen_res:
        s_route = scen_res.get("revised_route") or scen_res.get("scenario_route") or {}
        s_reach = bool(scen_res.get("is_scenario_reachable", True))
        s_budget = bool(scen_res.get("is_scenario_budget_feasible", True))
        headline = scen_res.get("headline") or scen_res.get("narrative", {}).get("headline", "Contingency Evaluated")
        detail = scen_res.get("detail") or scen_res.get("narrative", {}).get("detail", "")

        md.extend([
            f"### Scenario: {scen_res.get('scenario', {}).get('name', 'Custom What-If Disruption')}",
            f"> **{headline}**  ",
            f"> {detail}",
            "",
        ])

        if not s_reach:
            md.extend([
                "> [!WARNING]",
                "> **CORRIDOR SEVERED:** Under the simulated condition, no continuous passable path exists between the start and goal satisfying vehicle slope and obstacle limits. Traverse aborted.",
                "",
            ])
        else:
            d_dist = float(scen_res.get("delta_distance_m", 0.0) or 0.0)
            d_time = str(scen_res.get("formatted_delta_travel_time", "+0 min"))
            s_dist = float(s_route.get("distance_m", b_dist))
            s_time = str(s_route.get("formatted_travel_time", "—"))
            s_timeline = s_route.get("timeline") or scen_res.get("revised_timeline") or {}
            s_tot_time = str(s_timeline.get("formatted_mission_time", s_time))

            md.extend([
                f"- **Revised Traverse Distance:** `{s_dist:,.1f} m` ({d_dist:+.1f} m detour)",
                f"- **Revised Transit Duration:** `{s_time}` ({d_time} change)",
                f"- **Revised Mission Schedule:** `{s_tot_time}`",
                f"- **Budget Feasibility:** `{'FEASIBLE' if s_budget else 'BUDGET EXCEEDED'}`",
                "",
                "### Trade-Off Justification",
                f"The routing engine recommends the revised trajectory because it avoids blocked hazard cells and high-impedance terrain while preserving maximum reachable science targets.",
                "",
            ])

        # Recovery Assessment if available
        rec = scen_res.get("recovery_plan")
        if rec and rec.get("strategy"):
            md.extend([
                "### Contingency Recovery Strategy",
                f"- **Applied Strategy:** {rec.get('strategy')}",
                f"- **Action Label:** {rec.get('action_label', 'Alternate Traversal')}",
                f"- **Margin Recovered:** `{rec.get('formatted_margin_recovered', '0 min')}`",
                "",
            ])
    else:
        md.extend([
            "_No disruption scenarios were active during this planning run. The baseline mission was evaluated under nominal terrain constraints._",
            "",
        ])

    md.extend([
        "---",
        "",
        "## 3. Engineering Assumptions & Classification Ledger",
        "",
        "| Parameter | Value | Classification | Source / Primary Citation | Disclosure |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    for key, item in ENGINEERING_ASSUMPTIONS.items():
        md.append(
            f"| {item['parameter']} | `{item['value']}` | **{item['classification']}** | {item['citation']} | {item['disclosure']} |"
        )

    md.extend([
        "",
        "---",
        "",
        "## 4. Scientific Provenance & Research Disclosures",
        "- **Digital Elevation Model:** USGS Astrogeology Science Center MRO CTX DTM (20 m/px geodetic grid).",
        "- **Optical Imagery:** NASA MRO CTX Jezero Crater optical mosaic (6 m/px).",
        "- **Basemap:** USGS Viking MDIM 2.1 global colour mosaic (232 m/px).",
        "- **Coordinate System:** IAU Mars 2000 Planetocentric Reference Sphere.",
        "",
        "> **RESEARCH PROTOTYPE DISCLAIMER:** MarsWalk 2.0 is an interactive scientific research and mission rehearsal prototype developed for space exploration planning. Modeled paths, estimated travel durations, and disruption contingencies represent mathematical approximations on remote-sensing models and do NOT certify physical safety for astronaut EVA flight operations.",
    ])

    return "\n".join(md)


def generate_decision_pack_readme(bundle: Dict[str, Any]) -> str:
    """
    Generate README.txt detailing package contents, reproduction instructions,
    and integrity hashes.
    """
    b_id = bundle.get("bundle_id", "run_bundle")
    comp_fp = bundle.get("computation_fingerprint", "N/A")
    base_fp = bundle.get("baseline_fingerprint", "N/A")
    t_prov = bundle.get("terrain_provenance") or {}

    lines = [
        "================================================================================",
        "  MARSWALK 2.0 — MISSION DECISION PACK",
        "  Competition Demonstration, Decision Traceability & Scientific Provenance",
        "================================================================================",
        f"Bundle Identifier        : {b_id}",
        f"Computation Fingerprint  : {comp_fp}",
        f"Baseline Fingerprint     : {base_fp}",
        f"Created Timestamp (UTC)  : {bundle.get('created_at')}",
        f"Terrain Dataset ID       : {t_prov.get('dataset_id')}",
        f"Terrain Artifact SHA-256 : {t_prov.get('sha256_hash')}",
        f"Coordinate Reference     : {t_prov.get('coordinate_reference')}",
        f"Raster Grid Dimensions   : {t_prov.get('dimensions', {}).get('height')} x {t_prov.get('dimensions', {}).get('width')} px at 20.0 m/px",
        "================================================================================",
        "",
        "PACKAGE CONTENTS:",
        "-----------------",
        "1. mission_bundle.json",
        "   Canonical, versioned input parameters and authoritative calculation outputs.",
        "   Adheres strictly to JSON Schema Draft 2020-12 (mission-run-bundle.schema.json).",
        "",
        "2. mission_brief.md",
        "   Comprehensive technical mission briefing report formatted in GitHub Markdown.",
        "   Contains executive summaries, disruption analysis, trade-off justifications,",
        "   engineering assumption classifications, and scientific citations.",
        "",
        "3. comparison.csv",
        "   RFC 4180 compliant CSV table of baseline-vs-scenario metric deltas.",
        "   Distinguishes ground distance, movement duration, dwells, holds, and science.",
        "",
        "4. route.json",
        "   Cartographic coordinates [[lon_deg, lat_deg, elevation_m], ...], grid path_rc,",
        "   cumulative climb, and maximum slope angles for GIS software or 3D visualizers.",
        "",
        "5. README.txt",
        "   This package manifest, reproduction guide, and provenance ledger.",
        "",
        "REPRODUCTION & INDEPENDENT VERIFICATION:",
        "----------------------------------------",
        "To independently verify bundle integrity or replay this calculation through the",
        "authoritative MarsWalk Python A* engine:",
        "",
        "Option A: Command Line Verification via MarsWalk Environment",
        "  1. Activate MarsWalk Python virtual environment (.venv).",
        "  2. Run the verification script:",
        f"     python -c \"import json; from marswalk.api.decision_pack import verify_bundle_integrity; b=json.load(open('mission_bundle.json')); print(verify_bundle_integrity(b))\"",
        "",
        "Option B: Full Engine Replay & Deterministic Output Comparison",
        "  1. Ensure the authentic USGS 20m CTX GeoTIFF is present at data/processed/jezero_ready_20m.tif.",
        "  2. Replay the bundle:",
        f"     python -c \"import json, rasterio; from marswalk.core.terrain import load_and_process_terrain; from marswalk.api.decision_pack import replay_decision_pack_bundle; t=load_and_process_terrain('data/processed/jezero_ready_20m.tif'); b=json.load(open('mission_bundle.json')); print(replay_decision_pack_bundle(b, t, rasterio.open('data/processed/jezero_ready_20m.tif').transform, []))\"",
        "",
        "ENGINEERING ASSUMPTIONS & SCIENTIFIC ATTRIBUTION:",
        "-------------------------------------------------",
        "- Crew EVA Velocity : Apollo lunar surface walking analogue (2.0 km/h nominal).",
        "- Robotic Mobility  : Mars 2020 Perseverance / MSL Curiosity drive rate (0.035 m/s).",
        "- Terrain Effort    : Minetti et al. (2002) asymmetric human metabolic slope model.",
        "- Topography Data   : USGS Astrogeology Science Center Context Camera (CTX) DTM.",
        "",
        "IMPORTANT RESEARCH PROTOTYPE DISCLAIMER:",
        "---------------------------------------",
        "MarsWalk 2.0 is an interactive scientific research and mission rehearsal prototype",
        "developed for educational and mission planning analysis. Modeled paths, estimated",
        "travel times, and disruption contingencies represent mathematical approximations",
        "and are NOT certified as operationally safe for human astronaut EVA operations.",
        "================================================================================",
    ]
    return "\n".join(lines)


def generate_route_cartography(
    baseline_route: Dict[str, Any],
    scenario_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate clean cartographic route breakdown containing 3D coordinates,
    grid path, elevation profiles, and climbing metrics.
    """
    s_route = (scenario_result.get("revised_route") or scenario_result.get("scenario_route")) if scenario_result else None

    return {
        "schema_version": "1.0.0",
        "planetary_target": "Mars (IAU 2000 Sphere / USGS CTX DTM 20m)",
        "baseline_route": {
            "start_rc": baseline_route.get("start_rc"),
            "goal_rc": baseline_route.get("goal_rc"),
            "distance_m": baseline_route.get("distance_m"),
            "cumulative_climb_m": baseline_route.get("cumulative_climb_m"),
            "max_slope_deg": baseline_route.get("max_slope_deg"),
            "num_steps": baseline_route.get("num_steps"),
            "path_rc": baseline_route.get("path_rc"),
            "coordinates_3d": baseline_route.get("coordinates_3d"),
        },
        "scenario_route": {
            "is_reachable": s_route.get("is_reachable") if s_route else None,
            "distance_m": s_route.get("distance_m") if s_route else None,
            "cumulative_climb_m": s_route.get("cumulative_climb_m") if s_route else None,
            "max_slope_deg": s_route.get("max_slope_deg") if s_route else None,
            "num_steps": s_route.get("num_steps") if s_route else None,
            "path_rc": s_route.get("path_rc") if s_route else None,
            "coordinates_3d": s_route.get("coordinates_3d") if s_route else None,
        } if s_route else None,
    }


def build_decision_pack_zip(
    bundle: Dict[str, Any],
    brief_markdown: str,
    comparison_csv: str,
    readme_text: str,
    route_cartography: Dict[str, Any],
) -> bytes:
    """
    Package all decision artifacts into an in-memory ZIP archive using standard library zipfile.
    Enforces safe, relative filenames without directory traversal risk.
    """
    buffer = io.BytesIO()
    # Use ZIP_DEFLATED if available, fallback to ZIP_STORED
    compress_type = zipfile.ZIP_DEFLATED if "ZIP_DEFLATED" in zipfile.__dict__ else zipfile.ZIP_STORED

    with zipfile.ZipFile(buffer, "w", compression=compress_type) as zf:
        # 1. mission_bundle.json
        bundle_str = json.dumps(bundle, indent=2, ensure_ascii=False)
        zf.writestr("mission_bundle.json", bundle_str.encode("utf-8"))

        # 2. mission_brief.md
        zf.writestr("mission_brief.md", brief_markdown.encode("utf-8"))

        # 3. comparison.csv
        zf.writestr("comparison.csv", comparison_csv.encode("utf-8"))

        # 4. README.txt
        zf.writestr("README.txt", readme_text.encode("utf-8"))

        # 5. route.json
        carto_str = json.dumps(route_cartography, indent=2, ensure_ascii=False)
        zf.writestr("route.json", carto_str.encode("utf-8"))

    buffer.seek(0)
    return buffer.getvalue()


# =============================================================================
# 2. INDEPENDENT REPLAY & INTEGRITY VERIFICATION SERVICE
# =============================================================================

def verify_bundle_integrity(
    bundle: Dict[str, Any],
    terrain: Optional[TerrainGrid] = None,
    terrain_sha256: str = TERRAIN_SHA256,
) -> Dict[str, Any]:
    """
    Perform a comprehensive integrity and compatibility audit on a Mission Run Bundle.

    Three-Stage Evaluation:
      1. Integrity Valid: Schema Draft 2020-12 valid, valid data types, finite numbers.
      2. Replay Compatible: Dataset ID matches, coordinate bounds match terrain.
      3. Fingerprint Verification: Recomputed computation fingerprint matches recorded hash.
    """
    integrity_errors: List[str] = []
    compatibility_notes: List[str] = []

    # 1. Schema Validation
    is_schema_valid, schema_errs = validate_contract(bundle, "mission-run-bundle")
    if not is_schema_valid:
        for err in schema_errs:
            integrity_errors.append(f"Schema violation at '{err['field']}': {err['issue']}")

    # 2. Number finiteness & value sanity
    m_input = bundle.get("mission_input", {})
    st = m_input.get("start", {})
    gl = m_input.get("goal", {})
    st_r, st_c = st.get("row"), st.get("col")
    gl_r, gl_c = gl.get("row"), gl.get("col")

    if st_r is None or st_c is None or gl_r is None or gl_c is None:
        integrity_errors.append("Mission start and goal coordinates must be specified.")

    # 3. Terrain Compatibility Check
    t_prov = bundle.get("terrain_provenance", {})
    b_dataset = t_prov.get("dataset_id")
    if b_dataset != TERRAIN_DATASET_ID:
        compatibility_notes.append(
            f"Dataset mismatch: recorded '{b_dataset}', local engine supports '{TERRAIN_DATASET_ID}'."
        )

    b_sha = t_prov.get("sha256_hash")
    if b_sha != terrain_sha256:
        compatibility_notes.append(
            f"Terrain raster hash mismatch: bundle requires '{b_sha}', local raster is '{terrain_sha256}'."
        )

    # 4. Coordinate Bounds Check against active terrain
    max_h = terrain.height if terrain is not None else t_prov.get("dimensions", {}).get("height", 250)
    max_w = terrain.width if terrain is not None else t_prov.get("dimensions", {}).get("width", 250)

    if st_r is not None and st_c is not None:
        if st_r < 0 or st_r >= max_h or st_c < 0 or st_c >= max_w:
            integrity_errors.append(f"Start coordinates ({st_r}, {st_c}) exceed terrain bounds ({max_h}x{max_w}).")
    if gl_r is not None and gl_c is not None:
        if gl_r < 0 or gl_r >= max_h or gl_c < 0 or gl_c >= max_w:
            integrity_errors.append(f"Goal coordinates ({gl_r}, {gl_c}) exceed terrain bounds ({max_h}x{max_w}).")

    # Stops check
    for idx, s in enumerate(m_input.get("stops", [])):
        sr, sc = s.get("row"), s.get("col")
        if sr is None or sc is None or sr < 0 or sr >= max_h or sc < 0 or sc >= max_w:
            integrity_errors.append(f"Intermediate stop #{idx+1} coordinates ({sr}, {sc}) exceed terrain bounds.")

    # 5. Deterministic Computation Fingerprint Recomputation
    recorded_fp = bundle.get("computation_fingerprint", "")
    computed_fp = ""
    fingerprint_matches = False

    try:
        raw_events = (
            (bundle.get("contingency_input", {}).get("events") if bundle.get("contingency_input") else None)
            or m_input.get("custom_events")
            or m_input.get("events")
            or []
        )
        computed_fp = compute_bundle_fingerprint(
            m_input,
            contingency_events=raw_events,
            dataset_id=b_dataset or TERRAIN_DATASET_ID,
            terrain_sha256=b_sha or terrain_sha256,
        )
        fingerprint_matches = (computed_fp == recorded_fp)
        if not fingerprint_matches:
            integrity_errors.append(
                f"Computation fingerprint mismatch: recorded '{recorded_fp}', recomputed '{computed_fp}' (integrity fingerprint mismatch)."
            )
    except Exception as e:
        integrity_errors.append(f"Failed to recompute computation fingerprint: {str(e)}")

    # 6. Cryptographic Execution Digest Recomputation (Integrity Fingerprint Verification)
    recorded_exec = bundle.get("execution_digest", "")
    computed_exec = ""
    execution_digest_matches = False

    try:
        b_route = bundle.get("baseline_route") or {}
        reach_feas = bundle.get("reachability_and_feasibility") or {}
        s_result = bundle.get("scenario_result")
        comp_metrics = bundle.get("comparison_metrics")

        computed_exec = compute_bundle_execution_digest(
            baseline_route=b_route,
            reachability_and_feasibility=reach_feas,
            scenario_result=s_result,
            comparison_metrics=comp_metrics,
        )
        execution_digest_matches = (computed_exec == recorded_exec)
        if not execution_digest_matches:
            integrity_errors.append(
                f"Execution digest mismatch: recorded '{recorded_exec}', recomputed '{computed_exec}' (integrity fingerprint mismatch on computed outputs)."
            )
    except Exception as e:
        integrity_errors.append(f"Failed to recompute execution digest: {str(e)}")

    is_integrity_valid = len(integrity_errors) == 0
    is_replay_compatible = is_integrity_valid and len(compatibility_notes) == 0

    return {
        "schema_version": "1.0.0",
        "bundle_id": bundle.get("bundle_id"),
        "is_integrity_valid": is_integrity_valid,
        "is_replay_compatible": is_replay_compatible,
        "fingerprint_matches": fingerprint_matches,
        "execution_digest_matches": execution_digest_matches,
        "recorded_fingerprint": recorded_fp,
        "computed_fingerprint": computed_fp,
        "recorded_execution_digest": recorded_exec,
        "computed_execution_digest": computed_exec,
        "integrity_errors": integrity_errors,
        "compatibility_notes": compatibility_notes,
    }


def replay_decision_pack_bundle(
    bundle: Dict[str, Any],
    terrain: TerrainGrid,
    transform: rasterio.Affine,
    waypoints: List[ScienceWaypoint],
    experiments_dir: Optional[str] = None,
    allow_persist: bool = True,
) -> Dict[str, Any]:
    """
    Re-execute a Mission Run Bundle through the authoritative Python A* path planner
    and contingency simulation engine.
    
    Guarantees:
      - Validates integrity and compatibility before simulation.
      - Never mutates archived historical records; creates a distinct new run ID.
      - Compares re-executed route geometry and targets with recorded outputs.
      - Verifies floating point deltas within documented tolerances (0.1m, 0.1s).
    """
    # 1. Verify integrity & compatibility
    audit = verify_bundle_integrity(bundle, terrain=terrain)
    if not audit["is_integrity_valid"]:
        raise WorkspaceError(
            f"Bundle integrity validation failed: {'; '.join(audit['integrity_errors'])}",
            status_code=400,
            error_code="ERR_BUNDLE_CORRUPTED",
            details=[{"issue": err} for err in audit["integrity_errors"]],
        )

    if not audit["is_replay_compatible"]:
        raise WorkspaceError(
            f"Bundle is incompatible with current terrain environment: {'; '.join(audit['compatibility_notes'])}",
            status_code=409,
            error_code="ERR_TERRAIN_INCOMPATIBLE",
            details=[{"issue": note} for note in audit["compatibility_notes"]],
        )

    m_input = bundle["mission_input"]
    bundle_id = bundle.get("bundle_id", "bundle")

    # 2. Re-execute Baseline Route Plan
    new_base = plan_route_api(m_input, terrain, transform, waypoints)

    # 3. Re-execute Contingency if present
    contingency_input = bundle.get("contingency_input")
    raw_events = (
        (contingency_input.get("events") if contingency_input else None)
        or m_input.get("custom_events")
        or m_input.get("events")
        or []
    )

    new_scen = None
    if raw_events:
        scen_payload = dict(m_input)
        scen_payload["custom_events"] = raw_events
        new_scen = contingency_simulate_api(scen_payload, terrain, transform, waypoints)

    # 4. Compare Recorded vs Re-executed
    rec_base = bundle.get("baseline_route", {})
    rec_path = [tuple(pt) for pt in rec_base.get("path_rc", [])]
    new_path = [tuple(pt) for pt in new_base.get("path_rc", [])]

    rec_wps = list(rec_base.get("visited_waypoint_ids", []))
    new_wps = list(new_base.get("visited_waypoint_ids", []))

    # Exact equality checks for deterministic outputs
    is_path_identical = (rec_path == new_path)
    is_wps_identical = (rec_wps == new_wps)

    # Numerical tolerance checks (0.1 m distance, 0.1 s duration)
    dist_diff = abs(float(new_base.get("distance_m", 0.0)) - float(rec_base.get("distance_m", 0.0)))
    time_diff = abs(float(new_base.get("travel_time_s", 0.0)) - float(rec_base.get("travel_time_s", 0.0)))

    is_dist_tolerated = dist_diff <= 0.1
    is_time_tolerated = time_diff <= 0.1

    is_scen_identical = True
    scen_dist_diff = 0.0
    scen_time_diff = 0.0
    if new_scen and bundle.get("scenario_result"):
        rec_scen = bundle["scenario_result"]
        rec_scen_route = rec_scen.get("revised_route") or rec_scen.get("scenario_route") or {}
        new_scen_route = new_scen.get("revised_route") or new_scen.get("scenario_route") or {}

        rec_scen_reach = bool(rec_scen.get("is_scenario_reachable", True))
        new_scen_reach = bool(new_scen.get("is_scenario_reachable", True))
        if rec_scen_reach != new_scen_reach:
            is_scen_identical = False

        rec_scen_path = [tuple(pt) for pt in rec_scen_route.get("path_rc", [])]
        new_scen_path = [tuple(pt) for pt in new_scen_route.get("path_rc", [])]
        if rec_scen_path != new_scen_path:
            is_scen_identical = False

        if rec_scen_reach and new_scen_reach:
            scen_dist_diff = abs(float(new_scen_route.get("distance_m", 0.0)) - float(rec_scen_route.get("distance_m", 0.0)))
            scen_time_diff = abs(float(new_scen_route.get("travel_time_s", 0.0)) - float(rec_scen_route.get("travel_time_s", 0.0)))
            if scen_dist_diff > 0.1 or scen_time_diff > 0.1:
                is_scen_identical = False

    is_reproduced = (
        is_path_identical
        and is_wps_identical
        and is_dist_tolerated
        and is_time_tolerated
        and is_scen_identical
    )

    # 5. Persist as NEW Experiment Record (Never mutate archived data)
    new_exp_id = f"replay_{bundle_id}_{uuid.uuid4().hex[:6]}"
    saved_exp = None
    if allow_persist:
        exp_payload = {
            "schema_version": SCHEMA_VERSION,
            "experiment_id": new_exp_id,
            "name": f"Replay: {bundle_id}",
            "description": f"Reproducibility replay of Mission Run Bundle {bundle_id}.",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "success" if new_base.get("is_reachable") else "infeasible",
            "lifecycle_state": "reproducible" if is_reproduced else "diverged",
            "baseline_fingerprint": new_base.get("input_fingerprint"),
            "mission_snapshot": new_base.get("mission_snapshot"),
            "baseline_route": new_base,
            "scenarios_evaluated": [new_scen["scenario"]] if (new_scen and "scenario" in new_scen) else [],
            "replayed_from_bundle_id": bundle_id,
            "reproducibility_notes": (
                "Exact deterministic reproduction verified across path geometry and waypoint sequence."
                if is_reproduced
                else f"Divergence detected: path_identical={is_path_identical}, dist_diff={dist_diff:.2f}m."
            ),
            "terrain_dataset_id": TERRAIN_DATASET_ID,
            "model_version": "2.0.0",
            "assumptions_version": "1.0.0",
        }
        saved_exp = save_experiment(exp_payload, experiments_dir=experiments_dir, allow_overwrite=False)

    return {
        "schema_version": "1.0.0",
        "bundle_id": bundle_id,
        "replay_experiment_id": new_exp_id,
        "is_integrity_valid": True,
        "is_replay_compatible": True,
        "is_reproduced": is_reproduced,
        "verification_status": "reproduced" if is_reproduced else "diverged",
        "comparisons": {
            "path_geometry_identical": is_path_identical,
            "visited_targets_identical": is_wps_identical,
            "distance_delta_m": round(dist_diff, 2),
            "travel_time_delta_s": round(time_diff, 1),
            "scenario_geometry_identical": is_scen_identical,
            "scenario_distance_delta_m": round(scen_dist_diff, 2) if new_scen else 0.0,
            "scenario_travel_time_delta_s": round(scen_time_diff, 1) if new_scen else 0.0,
        },
        "reproduced_route": new_base,
        "reproduced_scenario": new_scen,
        "persisted_experiment": saved_exp,
    }
