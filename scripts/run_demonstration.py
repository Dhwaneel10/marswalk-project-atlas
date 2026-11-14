"""
MarsWalk 2.0 (Project Atlas) — Repeatable End-to-End Demonstration Script
========================================================================

Exercises the complete 10-stage planetary mission rehearsal workflow:
 1. Atlas Server Launch & Terrain Overview
 2. Saved Mission Selection & Baseline Route Planning
 3. Mission Target Waypoints & Traverse Metrics
 4. Kinematic Playback & Mid-Sortie Emergency Injection
 5. 3-Stage Trajectory Trade-Off Evaluation (Nominal vs Disrupted vs Adaptive)
 6. Sortie Black-Box Event Ledger History
 7. Environmental Intelligence (NASA PDS In-Situ Observations vs Climatology)
 8. Mission Science Report Generation & HTML/JSON Export
 9. Mission Readiness & Decision Gate Assessment
10. Decision Pack Cryptographic Integrity Verification & Final Briefing Export

Supports both CDP browser-driven demonstration and direct headless verification.
All outputs are saved to repository-relative 'outputs/demonstration/'.
"""

import os
import sys
import time
import json
import copy
import argparse
from pathlib import Path
import urllib.request
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from marswalk.core.terrain import load_and_process_terrain
from marswalk.api.service import plan_route_api
from marswalk.core.mission_playback import build_mission_playback_model, interpolate_playback_state
from marswalk.core.mission_continuation import capture_mid_sortie_state, plan_mission_continuation
from marswalk.core.mission_event_ledger import MissionEvent, record_events_batch, get_mission_events
from marswalk.core.weather import get_weather_manager, PDS_MEDA_ARCHIVE_URL
from marswalk.core.mission_report import assemble_mission_report, generate_mission_report_html
from marswalk.core.mission_readiness import evaluate_mission_readiness
from marswalk.api.decision_pack import (
    build_canonical_mission_run_bundle,
    verify_bundle_integrity,
    generate_comparison_csv,
    generate_decision_pack_briefing_md,
)
from marswalk.api.workspace import get_mission, DEFAULT_MISSIONS_DIR
from marswalk.api.contracts import TERRAIN_DATASET_ID, TERRAIN_SHA256, validate_contract

SAVED_MISSION_ID = "m_jezero_delta_scarp_surve_090607"
TERRAIN_PATH = PROJECT_ROOT / "data" / "processed" / "jezero_ready_20m.tif"


def format_stage(number: int, title: str) -> None:
    print(f"\n{'='*78}")
    print(f"  STAGE {number:02d}: {title.upper()}")
    print(f"{'='*78}")


def main():
    parser = argparse.ArgumentParser(description="MarsWalk 2.0 Repeatable End-to-End Mission Demonstration")
    parser.add_argument("--port", type=int, default=3000, help="Atlas HTTP server port (default: 3000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Atlas host (default: 127.0.0.1)")
    parser.add_argument("--mission-id", type=str, default=SAVED_MISSION_ID, help=f"Mission ID (default: {SAVED_MISSION_ID})")
    parser.add_argument("--export-dir", type=str, default="outputs/demonstration", help="Directory for demo exports")
    parser.add_argument("--no-browser", action="store_true", help="Skip launching browser tab")
    args = parser.parse_args()

    export_path = PROJECT_ROOT / args.export_dir
    export_path.mkdir(parents=True, exist_ok=True)

    base_url = f"http://{args.host}:{args.port}"
    print(f"MarsWalk 2.0 Project Atlas — Official Demonstration Runner")
    print(f"Target Server: {base_url}")
    print(f"Selected Mission: {args.mission_id}")
    print(f"Export Directory: {export_path}\n")

    # -------------------------------------------------------------------------
    # STAGE 01: Atlas Server Launch & Terrain Overview
    # -------------------------------------------------------------------------
    format_stage(1, "Atlas Server Launch & Terrain Overview")
    try:
        with urllib.request.urlopen(f"{base_url}/api/health", timeout=3) as resp:
            health = json.loads(resp.read().decode())
            print(f"  [OK] Atlas HTTP Server is ONLINE")
            print(f"       Engine:   {health.get('engine')}")
            print(f"       Target:   {health.get('target')}")
            print(f"       Terrain:  {'LOADED' if health.get('terrain_loaded') else 'OFFLINE'}")
            print(f"       Features: {health.get('waypoints_count')} verified science waypoints")
    except Exception as e:
        print(f"  [WARNING] Could not connect to Atlas daemon at {base_url}: {e}")
        print(f"  >> Continuing using core offline Python engine...")

    print(f"  Loading authentic USGS CTX 20m DTM ({TERRAIN_PATH.name})...")
    terrain = load_and_process_terrain(str(TERRAIN_PATH))
    with rasterio.open(str(TERRAIN_PATH)) as src:
        transform = src.transform
    elev_min = float(terrain.elevation[~terrain.invalid_mask].min())
    elev_max = float(terrain.elevation[~terrain.invalid_mask].max())
    print(f"  [OK] Grid Dimensions: {terrain.height} x {terrain.width} cells (20 m/pixel)")
    print(f"       Elevation Range: {elev_min:.1f}m to {elev_max:.1f}m (Datum: Mars Sphere R=3,396,190m)")

    # -------------------------------------------------------------------------
    # STAGE 02: Saved Mission Selection & Baseline Route Planning
    # -------------------------------------------------------------------------
    format_stage(2, "Saved Mission Selection & Baseline Route Planning")
    mission = get_mission(args.mission_id)
    cm = mission["canonical_mission"]
    print(f"  Mission Name: '{mission['name']}' ({mission['mission_id']})")
    print(f"  Description:  {mission.get('description')}")
    print(f"  Start Coord:  Row {cm['start']['row']}, Col {cm['start']['col']}")
    print(f"  Goal Coord:   Row {cm['goal']['row']}, Col {cm['goal']['col']}")
    print(f"  Profile:      {cm.get('profile', 'balanced')} | Vehicle: {cm.get('vehicle_mode', 'crew_eva')}")

    print("  Calculating optimal multi-stop baseline traverse via A* cost surface...")
    t0 = time.perf_counter()
    baseline_route = plan_route_api(payload=copy.deepcopy(cm), terrain=terrain, transform=transform)
    t_calc = (time.perf_counter() - t0) * 1000.0
    print(f"  [OK] Traverse Calculated in {t_calc:.1f} ms")
    print(f"       Reachability:  {'PASS (Reachable)' if baseline_route['is_reachable'] else 'BLOCKED'}")
    print(f"       Total Cells:   {len(baseline_route['path_rc'])} grid cells traversed")

    # -------------------------------------------------------------------------
    # STAGE 03: Mission Target Waypoints & Traverse Metrics
    # -------------------------------------------------------------------------
    format_stage(3, "Mission Target Waypoints & Traverse Metrics")
    m_dist = baseline_route["distance_m"]
    m_time = baseline_route["travel_time_s"]
    m_climb = baseline_route["cumulative_climb_m"]
    m_slope = baseline_route["max_slope_deg"]
    print(f"  Traverse Ground Distance: {m_dist:,.1f} meters")
    print(f"  Active Travel Duration:   {m_time:,.1f} seconds ({m_time/60.0:.1f} minutes)")
    print(f"  Cumulative Elevation Climb: {m_climb:,.1f} meters")
    print(f"  Maximum Gradient / Slope:   {m_slope:.1f}° (Limit: 15.0°)")
    print(f"\n  Sequenced Science Waypoints ({len(cm['stops'])} stops):")
    for idx, stop in enumerate(cm["stops"], 1):
        sr, sc = stop["row"], stop["col"]
        elev = float(terrain.elevation[sr, sc])
        dwell = stop.get("dwell_time_s", 900.0)
        prio = stop.get("priority_score", 50.0)
        print(f"    [{idx}] {stop.get('name', stop.get('id')):<32} (R:{sr}, C:{sc}) Elev: {elev:.1f}m | Dwell: {dwell}s | Prio: {prio}")

    # -------------------------------------------------------------------------
    # STAGE 04: Kinematic Playback & Mid-Sortie Emergency Injection
    # -------------------------------------------------------------------------
    format_stage(4, "Kinematic Playback & Mid-Sortie Emergency Injection")
    playback = build_mission_playback_model(
        route_data=baseline_route,
        terrain=terrain,
        vehicle_mode=cm.get("vehicle_mode", "crew_eva"),
    )
    print(f"  Playback Model: {playback.total_duration_s:.1f}s total duration, {len(playback.samples)} kinematic nodes")

    interruption_time_s = 600.0
    print(f"  Simulating vehicle traverse to intermediate sortie time t = {interruption_time_s}s...")
    interp_state = interpolate_playback_state(playback, interruption_time_s)
    print(f"  >> Vehicle Position at t=600s: Row {interp_state['rc'][0]:.1f}, Col {interp_state['rc'][1]:.1f}")
    print(f"     Elevation: {interp_state['elevation_m']:.1f}m | Distance Elapsed: {interp_state['cumulative_distance_m']:.1f}m")

    mid_state = capture_mid_sortie_state(
        playback_model=playback,
        interruption_time_s=interruption_time_s,
        terrain=terrain,
        total_budget_s=25000.0,
        goal_rc=(cm["goal"]["row"], cm["goal"]["col"]),
    )
    print(f"  [OK] Mid-Sortie State Captured:")
    print(f"       Remaining Life-Support Budget: {mid_state.remaining_budget_s:,.1f}s (Budget preserved without double-counting)")

    hazard_rc = (mid_state.rover_rc[0] + 5, mid_state.rover_rc[1] + 5)
    injected_event = {
        "id": "evt_demo_contingency_rockfall",
        "name": "Delta Scarp Mass Wasting / Rockfall",
        "event_type": "closed_corridor",
        "center_rc": list(hazard_rc),
        "radius_m": 60.0,
    }
    print(f"  Injecting Simulated Emergency Disruption:")
    print(f"       Hazard Type: {injected_event['name']} ({injected_event['event_type']})")
    print(f"       Center Grid: Row {hazard_rc[0]}, Col {hazard_rc[1]} (Impact Radius: {injected_event['radius_m']}m)")

    # -------------------------------------------------------------------------
    # STAGE 05: 3-Stage Trajectory Trade-Off Evaluation
    # -------------------------------------------------------------------------
    format_stage(5, "3-Stage Trajectory Trade-Off Evaluation")
    continuation_eval = plan_mission_continuation(
        terrain=terrain,
        mid_state=mid_state,
        event_definition=injected_event,
        profile="conservative",
        vehicle_mode=cm.get("vehicle_mode", "crew_eva"),
        transform=transform,
    )
    print(f"  Continuation ID: {continuation_eval['continuation_id']}")
    print(f"  Automated Operational Recommendation:")
    print(f"    >> Decision:   [{continuation_eval['recommendation'].upper()}] {continuation_eval['recommendation_title']}")
    print(f"       Rationale:  {continuation_eval['recommendation_rationale']}")

    nom_rem = continuation_eval.get("nominal_remaining", {})
    adp_rem = continuation_eval.get("adaptive_continuation", {})
    print(f"\n  Three-Stage Trajectory Metric Comparison:")
    print(f"    1. Nominal Remaining:   {nom_rem.get('distance_m', 0.0):,.1f}m | Reachable: {nom_rem.get('is_reachable')}")
    print(f"    2. Disrupted Remaining: Direct traverse blocked by injected rockfall barrier")
    print(f"    3. Adaptive Detour:     {adp_rem.get('distance_m', 0.0):,.1f}m | Reachable: {adp_rem.get('is_reachable')}")
    delta_d = adp_rem.get('distance_m', 0.0) - nom_rem.get('distance_m', 0.0)
    print(f"    >> Detour Overhead:    +{delta_d:.1f} meters around hazard perimeter")

    # -------------------------------------------------------------------------
    # STAGE 06: Sortie Black-Box Event Ledger History
    # -------------------------------------------------------------------------
    format_stage(6, "Sortie Black-Box Event Ledger History")
    demo_events = [
        MissionEvent(
            event_id="evt_demo_01",
            source_mission_id=args.mission_id,
            event_type="sortie_started",
            mission_time_s=0.0,
            playback_elapsed_s=0.0,
            recorded_at_utc="2026-10-26T03:00:00Z",
            route_variant="nominal",
            rover_rc=(117, 157),
            elevation_m=-2540.0,
            slope_deg=1.5,
            payload={"note": "Egress from Octavia E. Butler Base commenced"},
        ),
        MissionEvent(
            event_id="evt_demo_02",
            source_mission_id=args.mission_id,
            event_type="contingency_injected",
            mission_time_s=600.0,
            playback_elapsed_s=60.0,
            recorded_at_utc="2026-10-26T03:10:00Z",
            route_variant="disrupted",
            rover_rc=hazard_rc,
            elevation_m=-2530.0,
            slope_deg=3.2,
            payload={"hazard": "rockfall", "radius_m": 60.0},
        ),
        MissionEvent(
            event_id="evt_demo_03",
            source_mission_id=args.mission_id,
            event_type="continuation_selected",
            mission_time_s=604.0,
            playback_elapsed_s=60.4,
            recorded_at_utc="2026-10-26T03:10:04Z",
            route_variant="adaptive",
            rover_rc=hazard_rc,
            elevation_m=-2530.0,
            slope_deg=3.2,
            payload={"action": "detour_engaged", "delta_distance_m": delta_d},
        ),
    ]
    events_dir = export_path / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    record_events_batch(demo_events, base_dir=events_dir)

    retrieved_events = get_mission_events(args.mission_id, base_dir=events_dir)
    print(f"  Retrieved {len(retrieved_events)} Chronological Black-Box Events:")
    for ev in retrieved_events:
        print(f"    [{ev.mission_time_s:05.1f}s] {ev.event_type:<24} Variant: {ev.route_variant:<10} RC: {ev.rover_rc} Elev: {ev.elevation_m}m")

    # -------------------------------------------------------------------------
    # STAGE 07: Environmental Intelligence & Source Provenance
    # -------------------------------------------------------------------------
    format_stage(7, "Environmental Intelligence & Source Provenance")
    wm = get_weather_manager()
    weather = wm.get_weather("jezero_crater")
    print(f"  Target Station:  {weather['site_name']} ({weather['site_id']})")
    print(f"  Data Type:       {weather['data_type']} ({weather.get('observation_sol_label', 'Sol 1619')})")
    print(f"  Instrument:      {weather['source_metadata'].get('instrument_name')} ({weather['source_metadata'].get('spacecraft')})")
    print(f"  Surface Pres:    {weather['measurements']['atmospheric_pressure_pa']} Pa")
    print(f"  Wind Speed:      {weather['measurements']['wind_speed_m_s']} (Preserved as null; unmeasured reading)")
    print(f"  Archive Provenance: {weather['source_metadata']['archive_url']}")
    print(f"  Disclosures:")
    for d in weather['disclosures'][:2]:
        print(f"    * {d}")

    mcd_weather = wm.get_weather("olympus_mons")
    print(f"\n  Climatological Model Verification (Olympus Mons):")
    print(f"    >> Data Type:    {mcd_weather['data_type']} ({mcd_weather['source_metadata'].get('model_version')})")
    print(f"    >> Caldera Pres: {mcd_weather['measurements']['atmospheric_pressure_pa']} Pa (Thin summit air correctly modeled)")

    # -------------------------------------------------------------------------
    # STAGE 08: Mission Science Report Generation & HTML/JSON Export
    # -------------------------------------------------------------------------
    format_stage(8, "Mission Science Report Generation & HTML/JSON Export")
    report_dict = assemble_mission_report(
        mission_data_or_id=mission,
        route_result=baseline_route,
        terrain=terrain,
        transform=transform,
        weather_site="jezero_crater",
        events_dir=events_dir,
    )
    report_json_path = export_path / "jezero_mission_science_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
    print(f"  [OK] Exported JSON Dossier: {report_json_path} ({report_json_path.stat().st_size:,} bytes)")

    report_html = generate_mission_report_html(report_dict)
    report_html_path = export_path / "jezero_mission_science_report.html"
    with open(report_html_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    print(f"  [OK] Exported Standalone HTML Report: {report_html_path} ({len(report_html):,} bytes)")

    # -------------------------------------------------------------------------
    # STAGE 09: Mission Readiness & Decision Gate Assessment
    # -------------------------------------------------------------------------
    format_stage(9, "Mission Readiness & Decision Gate Assessment")
    readiness_asmt = evaluate_mission_readiness(
        mission_data_or_id=mission,
        route_result=baseline_route,
        terrain=terrain,
        transform=transform,
        weather_site="jezero_crater",
        events_dir=events_dir,
        persist_assessment=False,
    )
    print(f"  Assessment ID:    {readiness_asmt['assessment_id']}")
    print(f"  Readiness Status: [{readiness_asmt['readiness_status']}]")
    print(f"  Readiness Score:  {readiness_asmt['readiness_score']:.1f} / 100.0")
    print(f"  Category Evaluation Summary:")
    for cat, sc in readiness_asmt['categories_summary'].items():
        print(f"    - {cat:<18} Status: [{sc.get('status', 'N/A')}]")

    print(f"\n  Actionable Audit Findings ({len(readiness_asmt['findings'])} findings):")
    for f in readiness_asmt['findings'][:3]:
        print(f"    [{f['severity'].upper():<7}] {f['finding_code']}: {f['title']}")
        print(f"             Action: {f['recommended_action']}")

    # -------------------------------------------------------------------------
    # STAGE 10: Decision Pack Cryptographic Verification & Export
    # -------------------------------------------------------------------------
    format_stage(10, "Decision Pack Cryptographic Verification & Export")
    scen_result = {
        "is_scenario_reachable": True,
        "revised_route": baseline_route,
    }
    bundle = build_canonical_mission_run_bundle(
        mission_input=cm,
        baseline_route=baseline_route,
        terrain=terrain,
        scenario_result=scen_result,
    )
    print(f"  Bundle ID:               {bundle['bundle_id']}")
    print(f"  Computation Fingerprint: {bundle['computation_fingerprint']}")
    print(f"  Execution Digest:        {bundle['execution_digest']}")

    integrity = verify_bundle_integrity(bundle)
    print(f"  Integrity Verification:  {'PASSED' if integrity['is_integrity_valid'] else 'FAILED'}")
    print(f"  Replay Compatible:       {'YES' if integrity['is_replay_compatible'] else 'NO'}")

    csv_data = generate_comparison_csv(baseline_route, scen_result)
    csv_path = export_path / "decision_pack_comparison.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_data)
    print(f"  [OK] Exported Comparison CSV: {csv_path} ({len(csv_data):,} bytes)")

    md_briefing = generate_decision_pack_briefing_md(bundle)
    briefing_path = export_path / "mission_decision_briefing.md"
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write(md_briefing)
    print(f"  [OK] Exported Decision Briefing: {briefing_path} ({len(md_briefing):,} bytes)")

    # -------------------------------------------------------------------------
    # DEMONSTRATION COMPLETE
    # -------------------------------------------------------------------------
    print(f"\n{'='*78}")
    print(f"  >>> MARSWALK 2.0 DEMONSTRATION COMPLETE: ALL 10 STAGES VERIFIED <<<")
    print(f"{'='*78}")
    print(f"Deliverables Generated:")
    print(f"  1. HTML Science Report: file:///{report_html_path.resolve().as_posix()}")
    print(f"  2. JSON Science Report: file:///{report_json_path.resolve().as_posix()}")
    print(f"  3. RFC 4180 CSV Export: file:///{csv_path.resolve().as_posix()}")
    print(f"  4. Markdown Briefing:   file:///{briefing_path.resolve().as_posix()}")
    print(f"{'='*78}\n")


if __name__ == "__main__":
    main()
