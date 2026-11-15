#!/usr/bin/env python3
"""
MarsWalk 2.0 — Project Atlas Local Server & Routing API Runner
Serves the isolated web/ 3D planetary application and provides live Python
A* traverse planning, Gauntlet stress-testing, and persistent workspace endpoints on localhost:3000.
"""

import os
import sys

# Auto-reexec inside project virtual environment if dependencies are missing in current python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    try:
        import rasterio
    except ImportError:
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import json
import argparse
import socket
import webbrowser
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import rasterio

# Ensure src/ is on Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from marswalk.data.tile_cache import PlanetaryTileCache, TileCacheError
from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.planner import ScienceWaypoint
from marswalk.api.service import (
    plan_route_api,
    plan_astronaut_eva_api,
    eva_contingency_api,
    gauntlet_api,
    contingency_simulate_api,
    scenario_comparison_api,
    scenario_sensitivity_api,
    export_briefing_api,
    export_decision_pack_api,
    verify_bundle_api,
    replay_bundle_api,
    mission_optimize_api,
    mission_replan_api,
    mission_robustness_api,
    route_explain_api,
    route_terrain_analysis_api,
    mission_playback_api,
    mission_continue_api,
    record_mission_events_api,
    get_mission_events_api,
    replay_mission_incident_api,
    get_weather_current_api,
    get_weather_sites_api,
    refresh_weather_api,
    generate_mission_report_api,
    export_mission_report_html_api,
    evaluate_mission_readiness_api,
    list_mission_readiness_api,
    get_mission_readiness_api,
    plan_campaign_api,
    replan_campaign_api,
    export_campaign_report_api,
    record_campaign_progress_api,
    get_campaign_progress_api,
    record_campaign_observation_api,
    list_campaign_observations_api,
    get_next_eligible_targets_api,
    reprioritize_campaign_api,
    list_campaign_recommendations_api,
    evaluate_campaign_scenarios_api,
    list_campaign_scenarios_api,
    get_campaign_scenario_api,
    apply_campaign_scenario_api,
    coordinate_campaign_api,
    list_campaign_coordinations_api,
    execute_campaign_handoff_api,
    list_campaign_handoffs_api,
    apply_campaign_coordination_api,
    start_campaign_simulation_api,
    advance_campaign_simulation_api,
    step_campaign_simulation_api,
    seek_campaign_simulation_api,
    interrupt_campaign_simulation_api,
    get_campaign_simulation_api,
    get_campaign_simulation_events_api,
    get_campaign_simulation_conflicts_api,
    list_campaign_simulations_api,
    analyze_campaign_api,
    get_campaign_analysis_api,
    list_campaign_analyses_api,
    review_recommendation_api,
    evaluate_campaign_design_space_api,
    get_campaign_design_space_api,
    list_campaign_design_spaces_api,
    promote_design_space_candidate_api,
    inspect_evidence_api,
    list_evidence_topics_api,
    evaluate_mission_robustness_api,
    get_robustness_experiment_api,
    list_robustness_experiments_api,
    promote_resilient_candidate_api,
    execute_rehearsal_api,
    get_rehearsal_api,
    list_rehearsals_api,
    get_rehearsal_disturbances_api,
    get_rehearsal_replay_api,
    get_rehearsal_bundle_api,
    export_rehearsal_bundle_api,
    orchestrate_experiment_api,
    get_experiment_api,
    list_experiments_api,
    get_experiment_matrix_api,
    get_experiment_dossier_api,
    export_experiment_dossier_api,
    relaynet_los_api,
    relaynet_graph_api,
    relaynet_candidates_api,
    relaynet_optimize_api,
    relaynet_timeline_api,
    joint_mission_evaluate_api,
    joint_mission_optimize_api,
    joint_mission_configurations_api,
    joint_mission_compare_api,
    joint_mission_promote_api,
    joint_mission_resource_evaluate_api,
    joint_mission_resource_sensitivity_api,
    science_mission_evaluate_api,
    science_mission_optimize_api,
    science_mission_configurations_api,
    science_mission_transfers_evaluate_api,
    science_mission_compatibility_api,
    science_mission_recovery_lab_api,
    campaign_operations_create_api,
    campaign_operations_list_api,
    campaign_operations_get_api,
    campaign_operations_plan_api,
    campaign_operations_execute_event_api,
    campaign_operations_advance_sol_api,
    campaign_operations_replan_api,
    campaign_operations_scenario_api,
    campaign_operations_timeline_api,
    campaign_operations_analytics_api,
    mission_assurance_evaluate_api,
    campaign_branches_create_api,
    campaign_branches_list_api,
    campaign_branches_get_api,
    campaign_branches_replay_api,
    campaign_branches_scenario_api,
    campaign_branches_compare_api,
    campaign_branches_promote_api,
    campaign_robustness_evaluate_api,
    mission_assurance_dossier_api,
    fleet_create_api,
    fleet_list_api,
    fleet_get_api,
    fleet_register_rover_api,
    fleet_allocate_science_api,
    fleet_plan_routes_api,
    fleet_schedule_api,
    fleet_network_api,
    fleet_resources_api,
    fleet_optimize_api,
    fleet_scenario_api,
    fleet_promote_api,
    fleet_assurance_api,
    mission_intent_sample_api,
    mission_intent_validate_api,
    mission_intent_normalize_api,
    mission_plan_compile_api,
    mission_plan_evaluate_api,
    mission_plan_compare_api,
    mission_plan_get_api,
    mission_plan_debugger_api,
    mission_plan_benchmark_api,
    mission_plan_promote_api,
    environmental_catalog_api,
    environmental_solar_api,
    environmental_point_eval_api,
    environmental_scenarios_api,
    environmental_window_api,
    environmental_raster_api,
    environment_validation_catalog_api,
    environment_validation_collocate_api,
    environment_validation_evaluate_api,
    environment_validation_calibrate_api,
    environment_validation_experiments_api,
    environment_validation_representativeness_api,
    environment_validation_tribunal_api,
    deep_space_status_api,
    deep_space_scenarios_list_api,
    deep_space_scenario_run_api,
    deep_space_command_create_api,
    deep_space_command_transmit_api,
    deep_space_simulation_advance_api,
    deep_space_inject_hazard_api,
    deep_space_reset_simulation_api,
    aerial_status_api,
    aerial_fleet_list_api,
    aerial_aircraft_create_api,
    aerial_performance_evaluate_api,
    aerial_mission_plan_api,
    aerial_rover_cooperation_plan_api,
    aerial_scenarios_list_api,
    aerial_scenario_run_api,
    aerial_observations_list_api,
    aerial_reset_api,
    science_discovery_status_api,
    science_discovery_hypotheses_api,
    science_discovery_hypothesis_create_api,
    science_discovery_evidence_graph_api,
    science_discovery_uncertainty_evaluate_api,
    science_discovery_actions_candidates_api,
    science_discovery_experiments_execute_api,
    science_discovery_benchmarks_api,
    science_discovery_scenarios_list_api,
    science_discovery_scenario_run_api,
    science_discovery_replay_api,
    science_discovery_reset_api,
    resilience_status_api,
    resilience_taxonomy_api,
    resilience_inject_fault_api,
    resilience_diagnose_api,
    resilience_propagation_api,
    resilience_recovery_evaluate_api,
    resilience_fmea_api,
    resilience_scenarios_list_api,
    resilience_scenario_run_api,
    resilience_benchmarks_api,
    resilience_reset_api,
    settlement_status_api,
    settlement_sites_api,
    settlement_architecture_api,
    settlement_power_simulate_api,
    settlement_isru_evaluate_api,
    settlement_consumables_api,
    settlement_habitat_thermal_api,
    settlement_construction_schedule_api,
    settlement_construction_step_api,
    settlement_logistics_trades_api,
    settlement_advance_simulation_api,
    settlement_readiness_review_api,
    settlement_scenarios_list_api,
    settlement_scenario_run_api,
    settlement_resilience_evaluate_api,
    settlement_replay_export_api,
    settlement_reset_api,
    mission_os_status_api,
    mission_os_create_api,
    mission_os_advance_api,
    mission_os_dispatch_command_api,
    mission_os_inject_event_api,
    mission_os_flagship_run_api,
    mission_os_replay_verify_api,
    mission_os_dossier_api,
    review_evidence_api,
    grand_prix_strategies_api,
    grand_prix_tournament_summary_api,
    grand_prix_tournament_run_api,
    grand_prix_compare_api,
    grand_prix_sensitivity_api,
    grand_prix_scenarios_api,
    planetary_network_topology_api,
    planetary_network_contacts_api,
    planetary_network_scenarios_api,
    planetary_network_scenario_run_api,
    planetary_network_grand_prix_run_api,
    planetary_network_dtn_metrics_api,
    planetary_foundry_overview_api,
    planetary_foundry_catalogue_api,
    planetary_foundry_fleet_api,
    planetary_foundry_materials_api,
    planetary_foundry_scenarios_api,
    planetary_foundry_scenario_run_api,
    planetary_foundry_grand_prix_run_api,
    flagship_mars_dark_run_api,
    flagship_mars_dark_status_api,
    flagship_mars_dark_comparison_api,
    flagship_mars_dark_replay_api,
    pillars_terrain_api,
    pillars_terrain_coverage_api,
    pillars_terrain_inspect_api,
    pillars_rover_ground_truth_api,
    pillars_rover_places_query_api,
    pillars_environment_meda_api,
    pillars_environment_meda_calibrate_api,
    pillars_science_targets_api,
    pillars_science_targets_plan_api,
    pillars_manifest_api,
    APIError,
)
from marswalk.api.contracts import create_api_error_response, ContractValidationError
from marswalk.api.workspace import (
    save_mission,
    list_missions,
    get_mission,
    update_mission,
    duplicate_mission,
    delete_mission,
    import_mission_json,
    save_experiment,
    list_experiments,
    get_experiment,
    delete_experiment,
    duplicate_experiment,
    replay_saved_experiment,
    compare_two_experiments,
    save_campaign,
    list_campaigns,
    get_campaign,
    update_campaign,
    delete_campaign,
    save_observation,
    get_observation,
    list_observations,
    save_progress_event,
    list_progress_events,
    save_recommendation,
    get_recommendation,
    list_recommendations,
    DEFAULT_CAMPAIGN_EXPERIMENTS_DIR,
    WorkspaceError,
)
from marswalk.api.preflight import run_preflight_diagnostics


class MarsWalkHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler with CORS, static file serving, live routing API, and workspace persistence endpoints."""

    terrain: Optional[TerrainGrid] = None
    transform: Optional[rasterio.Affine] = None
    waypoints: Optional[List[ScienceWaypoint]] = None
    tile_cache: Optional[PlanetaryTileCache] = None

    @classmethod
    def get_tile_cache(cls) -> PlanetaryTileCache:
        if cls.tile_cache is None:
            cls.tile_cache = PlanetaryTileCache()
        return cls.tile_cache

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "OK")
        self.end_headers()

    def send_json_response(self, data: dict, status_code: int = 200):
        """Helper to send a JSON response."""
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_binary_response(
        self,
        data: bytes,
        content_type: str = "application/octet-stream",
        status_code: int = 200,
        filename: Optional[str] = None,
    ):
        """Helper to send a binary response (e.g. ZIP archive)."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        """Handle GET requests for static files, API status, imagery tiles, and workspace entities."""
        parsed_url = urlparse(self.path)
        clean_path = parsed_url.path
        query_params = parse_qs(parsed_url.query)

        try:
            if clean_path in ("/api/health", "/api/status"):
                status_data = {
                    "status": "online",
                    "engine": "MarsWalk 2.0 Routing Intelligence",
                    "target": "Mars (IAU 2000 Sphere / USGS CTX DTM 20m)",
                    "endpoints": [
                        "/api/plan_route",
                        "/api/gauntlet",
                        "/api/contingency/simulate",
                        "/api/scenario_comparison",
                        "/api/scenario_sensitivity",
                        "/api/export_briefing",
                        "/api/export_decision_pack",
                        "/api/bundle/verify",
                        "/api/bundle/replay",
                        "/api/mission/optimize",
                        "/api/mission/replan",
                        "/api/missions",
                        "/api/experiments",
                        "/api/experiments/compare",
                        "/api/imagery/status",
                        "/api/imagery/tile",
                        "/api/weather/current",
                        "/api/weather/sites",
                        "/api/weather/refresh",
                        "/api/mission/report",
                        "/api/mission/report/html",
                        "/api/mission/readiness",
                        "/api/flagship/when-mars-goes-dark/run",
                        "/api/flagship/when-mars-goes-dark/status",
                        "/api/flagship/when-mars-goes-dark/comparison",
                        "/api/flagship/when-mars-goes-dark/replay",
                        "/api/pillars/terrain",
                        "/api/pillars/rover-ground-truth",
                        "/api/pillars/environment-meda",
                        "/api/pillars/science-targets",
                        "/api/pillars/manifest",
                        "/api/preflight",
                        "/api/health",
                    ],
                    "terrain_loaded": self.terrain is not None,
                    "waypoints_count": len(self.waypoints) if self.waypoints else 0,
                }
                self.send_json_response(status_data, 200)
                return
            elif clean_path == "/api/preflight":
                diag = run_preflight_diagnostics(
                    terrain=self.terrain,
                    transform=self.transform,
                    waypoints=self.waypoints,
                    base_url="http://127.0.0.1:3000",
                )
                self.send_json_response(diag, 200)
                return
            elif clean_path == "/api/imagery/status":
                status = self.get_tile_cache().get_status()
                self.send_json_response(status, 200)
                return
            elif clean_path == "/api/imagery/tile":
                product_id = query_params.get("product_id", [""])[0]
                z_str = query_params.get("z", [""])[0]
                r_str = query_params.get("r", [""])[0]
                c_str = query_params.get("c", [""])[0]

                if not (product_id and z_str and r_str and c_str):
                    err_resp = create_api_error_response(
                        error_code="ERR_MISSING_TILE_PARAM",
                        message="Missing required tile parameters: product_id, z, r, c",
                        status_code=400,
                    )
                    self.send_json_response(err_resp, 400)
                    return

                try:
                    z, r, c = int(z_str), int(r_str), int(c_str)
                except ValueError:
                    err_resp = create_api_error_response(
                        error_code="ERR_INVALID_TILE_COORDS",
                        message="Tile coordinates z, r, c must be integers",
                        status_code=400,
                    )
                    self.send_json_response(err_resp, 400)
                    return

                try:
                    cache = self.get_tile_cache()
                    result = cache.get_tile(product_id, z, r, c)
                    if result is None:
                        err_resp = create_api_error_response(
                            error_code="ERR_TILE_FETCH_FAILED",
                            message=f"Tile {product_id} ({z}/{r}/{c}) could not be retrieved from planetary WMTS source.",
                            status_code=502,
                        )
                        self.send_json_response(err_resp, 502)
                        return

                    tile_bytes, mime_type, is_hit = result
                    self.send_response(200)
                    self.send_header("Content-Type", mime_type)
                    self.send_header("Content-Length", str(len(tile_bytes)))
                    self.send_header("X-MarsWalk-Cache", "HIT" if is_hit else "MISS")
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(tile_bytes)
                    return
                except TileCacheError as tce:
                    err_resp = create_api_error_response(
                        error_code="ERR_INVALID_TILE_REQUEST",
                        message=str(tce),
                        status_code=400,
                    )
                    self.send_json_response(err_resp, 400)
                    return
            elif clean_path == "/api/missions":
                missions = list_missions()
                self.send_json_response({"missions": missions, "count": len(missions)}, 200)
                return
            elif clean_path.startswith("/api/missions/"):
                mission_id = clean_path[len("/api/missions/"):].strip()
                res = get_mission(mission_id)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/experiments":
                experiments = list_experiments()
                self.send_json_response({"experiments": experiments, "count": len(experiments)}, 200)
                return
            elif clean_path.startswith("/api/experiments/"):
                exp_id = clean_path[len("/api/experiments/"):].strip()
                res = get_experiment(exp_id)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/mission/events":
                res = get_mission_events_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/weather/current":
                res = get_weather_current_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/weather/sites":
                res = get_weather_sites_api()
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/mission/readiness/list":
                res = list_mission_readiness_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/mission/readiness/"):
                aid = clean_path[len("/api/mission/readiness/"):].strip()
                res = get_mission_readiness_api(aid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/progress":
                cid = query_params.get("campaign_id", [None])[0]
                if not cid:
                    raise APIError("Missing 'campaign_id' parameter", 400)
                res = get_campaign_progress_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/observations":
                cid = query_params.get("campaign_id", [None])[0]
                tid = query_params.get("target_id", [None])[0]
                res = list_campaign_observations_api(cid, tid)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/observations/"):
                obs_id = clean_path[len("/api/campaign/observations/"):].strip()
                res = get_observation(obs_id)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/next_eligible_targets":
                cid = query_params.get("campaign_id", [None])[0]
                if not cid:
                    raise APIError("Missing 'campaign_id' parameter", 400)
                res = get_next_eligible_targets_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/recommendations":
                cid = query_params.get("campaign_id", [None])[0]
                res = list_campaign_recommendations_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/scenarios":
                cid = query_params.get("campaign_id", [None])[0]
                res = list_campaign_scenarios_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/scenarios/"):
                scen_id = clean_path[len("/api/campaign/scenarios/"):].strip()
                res = get_campaign_scenario_api(scen_id)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/coordination":
                cid = query_params.get("campaign_id", [None])[0]
                res = list_campaign_coordinations_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/handoffs":
                cid = query_params.get("campaign_id", [None])[0]
                res = list_campaign_handoffs_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign/simulations":
                cid = query_params.get("campaign_id", [None])[0]
                res = list_campaign_simulations_api(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/simulation/"):
                subpath = clean_path[len("/api/campaign/simulation/"):].strip()
                if subpath.endswith("/events"):
                    sid = subpath[:-len("/events")].strip()
                    res = get_campaign_simulation_events_api(sid)
                    self.send_json_response(res, 200)
                    return
                elif subpath.endswith("/conflicts"):
                    sid = subpath[:-len("/conflicts")].strip()
                    res = get_campaign_simulation_conflicts_api(sid)
                    self.send_json_response(res, 200)
                    return
                else:
                    sid = subpath
                    res = get_campaign_simulation_api(sid)
                    self.send_json_response(res, 200)
                    return
            elif clean_path in ("/api/campaign/analyses", "/api/campaigns/analyses"):
                res = list_campaign_analyses_api()
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/analyses/"):
                aid = clean_path[len("/api/campaign/analyses/"):].strip()
                res = get_campaign_analysis_api(aid)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/campaign/design-spaces", "/api/campaign/design-space"):
                res = list_campaign_design_spaces_api()
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/design-space/"):
                dsid = clean_path[len("/api/campaign/design-space/"):].strip()
                res = get_campaign_design_space_api(dsid)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/campaigns", "/api/campaign/list"):
                campaigns = list_campaigns()
                self.send_json_response({"campaigns": campaigns, "count": len(campaigns)}, 200)
                return
            elif clean_path.startswith("/api/campaigns/"):
                cid = clean_path[len("/api/campaigns/"):].strip()
                res = get_campaign(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign/"):
                cid = clean_path[len("/api/campaign/"):].strip()
                res = get_campaign(cid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/evidence/topics":
                res = list_evidence_topics_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/evidence/inspect", "/api/evidence"):
                res = inspect_evidence_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/robustness/experiments":
                res = list_robustness_experiments_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/robustness/experiment/"):
                exp_id = clean_path[len("/api/robustness/experiment/"):].strip()
                res = get_robustness_experiment_api(exp_id)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/rehearsal/disturbances", "/api/rehearsals/disturbances"):
                res = get_rehearsal_disturbances_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/rehearsal/list", "/api/rehearsals", "/api/rehearsals/list"):
                res = list_rehearsals_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/rehearsal/"):
                sub = clean_path[len("/api/rehearsal/"):].strip()
                if sub.endswith("/replay"):
                    reh_id = sub[:-len("/replay")].strip("/")
                    res = get_rehearsal_replay_api(reh_id)
                elif sub.endswith("/bundle"):
                    reh_id = sub[:-len("/bundle")].strip("/")
                    res = get_rehearsal_bundle_api(reh_id)
                else:
                    res = get_rehearsal_api(sub)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/experiment/list", "/api/experiments/list", "/api/campaign_experiments"):
                res = list_experiments_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/experiment/") and clean_path.endswith("/dossier/zip"):
                sub = clean_path[len("/api/experiment/"): -len("/dossier/zip")].strip("/")
                zip_path = os.path.join(DEFAULT_CAMPAIGN_EXPERIMENTS_DIR, f"{sub}_evidence_dossier.zip")
                if not os.path.isfile(zip_path):
                    from marswalk.core.mission_experiment import export_experiment_dossier_zip
                    zip_path = export_experiment_dossier_zip(sub)
                with open(zip_path, "rb") as f:
                    zip_bytes = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(zip_path)}"')
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.end_headers()
                self.wfile.write(zip_bytes)
                return
            elif clean_path.startswith("/data/workspaces/campaign_experiments/"):
                fname = clean_path[len("/data/workspaces/campaign_experiments/"):].strip("/")
                fpath = os.path.join(DEFAULT_CAMPAIGN_EXPERIMENTS_DIR, fname)
                if os.path.isfile(fpath):
                    with open(fpath, "rb") as f:
                        f_bytes = f.read()
                    ctype = "application/zip" if fname.endswith(".zip") else "application/json"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                    self.send_header("Content-Length", str(len(f_bytes)))
                    self.end_headers()
                    self.wfile.write(f_bytes)
                    return
                else:
                    self.send_error(404, f"File not found: {fname}")
                    return
            elif clean_path.startswith("/api/experiment/"):
                sub = clean_path[len("/api/experiment/"):].strip()
                if sub.endswith("/matrix"):
                    exp_id = sub[:-len("/matrix")].strip("/")
                    res = get_experiment_matrix_api(exp_id)
                elif sub.endswith("/dossier"):
                    exp_id = sub[:-len("/dossier")].strip("/")
                    res = get_experiment_dossier_api(exp_id)
                else:
                    res = get_experiment_api(sub)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/relaynet/candidates":
                res = relaynet_candidates_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/joint-mission/configurations", "/api/joint-mission/candidates"):
                res = joint_mission_configurations_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/science-mission/configurations":
                res = science_mission_configurations_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/science-mission/compatibility":
                res = science_mission_compatibility_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign-operations/list":
                res = campaign_operations_list_api({}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign-operations/"):
                sub_path = clean_path[len("/api/campaign-operations/"):]
                if sub_path.endswith("/timeline"):
                    cid = sub_path[:-len("/timeline")]
                    res = campaign_operations_timeline_api(cid, self.terrain, self.transform)
                elif sub_path.endswith("/analytics"):
                    cid = sub_path[:-len("/analytics")]
                    res = campaign_operations_analytics_api(cid, self.terrain, self.transform)
                else:
                    res = campaign_operations_get_api(sub_path, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/campaign-branches/list":
                cid = "cmp_ops_default"
                if "query_params" in locals() and "campaign_id" in query_params:
                    cid = query_params["campaign_id"][0]
                res = campaign_branches_list_api({"campaign_id": cid}, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaign-branches/"):
                bid = clean_path[len("/api/campaign-branches/"):]
                cid = "cmp_ops_default"
                res = campaign_branches_get_api(bid, cid, self.terrain, self.transform)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/fleet/list", "/api/fleets"):
                res = fleet_list_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/fleet/") and not clean_path.endswith(("/network", "/resources", "/assurance")):
                fid = clean_path[len("/api/fleet/"):].strip()
                res = fleet_get_api(fid, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/network" or clean_path.endswith("/network"):
                res = fleet_network_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/resources" or clean_path.endswith("/resources"):
                res = fleet_resources_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/fleet/assurance" or clean_path.endswith("/assurance"):
                res = fleet_assurance_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment/catalog", "/api/v1/environment/catalog"):
                res = environmental_catalog_api({})
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment/solar", "/api/v1/environment/solar"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environmental_solar_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment/scenarios", "/api/v1/environment/scenarios"):
                res = environmental_scenarios_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment/raster", "/api/v1/environment/raster"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environmental_raster_api(qp, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment/point", "/api/v1/environment/point"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environmental_point_eval_api(qp, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/catalog", "/api/v1/environment-validation/catalog"):
                res = environment_validation_catalog_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/collocate", "/api/v1/environment-validation/collocate"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_collocate_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/evaluate", "/api/v1/environment-validation/evaluate"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_evaluate_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/experiments", "/api/v1/environment-validation/experiments"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_experiments_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/tribunal", "/api/v1/environment-validation/tribunal"):
                res = environment_validation_tribunal_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/deep-space/status", "/api/v1/deep-space/status"):
                res = deep_space_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/deep-space/scenarios", "/api/v1/deep-space/scenarios"):
                res = deep_space_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/status", "/api/v1/aerial/status"):
                res = aerial_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/fleet", "/api/v1/aerial/fleet"):
                res = aerial_fleet_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/scenarios", "/api/v1/aerial/scenarios"):
                res = aerial_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/aerial/observations", "/api/v1/aerial/observations"):
                res = aerial_observations_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/status", "/api/v1/science-discovery/status"):
                res = science_discovery_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/hypotheses", "/api/v1/science-discovery/hypotheses"):
                cid = query_params.get("campaign_id", [None])[0]
                res = science_discovery_hypotheses_api(campaign_id=cid)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/evidence-graph", "/api/v1/science-discovery/evidence-graph"):
                res = science_discovery_evidence_graph_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/actions/candidates", "/api/v1/science-discovery/actions/candidates"):
                strat = query_params.get("strategy", ["COST_AWARE_DISCOVERY"])[0]
                res = science_discovery_actions_candidates_api(strategy_name=strat)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/benchmarks", "/api/v1/science-discovery/benchmarks"):
                res = science_discovery_benchmarks_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/science-discovery/scenarios", "/api/v1/science-discovery/scenarios"):
                res = science_discovery_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/resilience/status", "/api/v1/resilience/status"):
                res = resilience_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/resilience/taxonomy", "/api/v1/resilience/taxonomy"):
                res = resilience_taxonomy_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/resilience/fmea", "/api/v1/resilience/fmea"):
                res = resilience_fmea_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/resilience/scenarios", "/api/v1/resilience/scenarios"):
                res = resilience_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/resilience/benchmarks", "/api/v1/resilience/benchmarks"):
                res = resilience_benchmarks_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/status", "/api/v1/settlement/status"):
                res = settlement_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/sites", "/api/v1/settlement/sites"):
                res = settlement_sites_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/architecture", "/api/v1/settlement/architecture"):
                res = settlement_architecture_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/construction/schedule", "/api/v1/settlement/construction/schedule"):
                res = settlement_construction_schedule_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/logistics/trades", "/api/v1/settlement/logistics/trades"):
                res = settlement_logistics_trades_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/readiness-review", "/api/v1/settlement/readiness-review"):
                res = settlement_readiness_review_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/scenarios", "/api/v1/settlement/scenarios"):
                res = settlement_scenarios_list_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/settlement/replay", "/api/v1/settlement/replay"):
                res = settlement_replay_export_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/mission-os/status", "/api/v1/mission-os/status"):
                res = mission_os_status_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/mission-os/dossier", "/api/v1/mission-os/dossier"):
                res = mission_os_dossier_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/mission-os/replay", "/api/v1/mission-os/replay"):
                res = mission_os_replay_verify_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/mission-os/flagship/run", "/api/v1/mission-os/flagship/run"):
                res = mission_os_flagship_run_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/flagship/when-mars-goes-dark/run", "/api/v1/flagship/when-mars-goes-dark/run"):
                res = flagship_mars_dark_run_api(self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/flagship/when-mars-goes-dark/status", "/api/v1/flagship/when-mars-goes-dark/status"):
                res = flagship_mars_dark_status_api(self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/flagship/when-mars-goes-dark/comparison", "/api/v1/flagship/when-mars-goes-dark/comparison"):
                res = flagship_mars_dark_comparison_api(self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/flagship/when-mars-goes-dark/replay", "/api/v1/flagship/when-mars-goes-dark/replay"):
                res = flagship_mars_dark_replay_api(self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/terrain", "/api/v1/pillars/terrain"):
                res = pillars_terrain_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/terrain/coverage", "/api/v1/pillars/terrain/coverage"):
                res = pillars_terrain_coverage_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/rover-ground-truth", "/api/v1/pillars/rover-ground-truth"):
                res = pillars_rover_places_query_api(query_params) if query_params else pillars_rover_ground_truth_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/rover-ground-truth/query", "/api/v1/pillars/rover-ground-truth/query"):
                res = pillars_rover_places_query_api(query_params)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/environment-meda", "/api/v1/pillars/environment-meda"):
                res = pillars_environment_meda_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/science-targets", "/api/v1/pillars/science-targets"):
                res = pillars_science_targets_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/pillars/manifest", "/api/v1/pillars/manifest"):
                res = pillars_manifest_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/review-evidence", "/api/v1/review-evidence"):
                res = review_evidence_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/strategies", "/api/v1/grand-prix/strategies"):
                res = grand_prix_strategies_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/tournament/summary", "/api/v1/grand-prix/tournament/summary"):
                res = grand_prix_tournament_summary_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/tournament/run", "/api/v1/grand-prix/tournament/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = grand_prix_tournament_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/compare", "/api/v1/grand-prix/compare"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = grand_prix_compare_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/sensitivity", "/api/v1/grand-prix/sensitivity"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = grand_prix_sensitivity_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in (
                "/api/planetary-network/topology",
                "/api/v1/planetary-network/topology",
                "/api/planetary-network/overview",
                "/api/v1/planetary-network/overview",
            ):
                res = planetary_network_topology_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/contacts", "/api/v1/planetary-network/contacts"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_contacts_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/scenarios", "/api/v1/planetary-network/scenarios"):
                res = planetary_network_scenarios_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/scenarios/run", "/api/v1/planetary-network/scenarios/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_scenario_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/grand-prix/run", "/api/v1/planetary-network/grand-prix/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_network_grand_prix_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/overview", "/api/v1/planetary-foundry/overview"):
                res = planetary_foundry_overview_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/catalogue", "/api/v1/planetary-foundry/catalogue"):
                res = planetary_foundry_catalogue_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/fleet", "/api/v1/planetary-foundry/fleet"):
                res = planetary_foundry_fleet_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/materials", "/api/v1/planetary-foundry/materials"):
                res = planetary_foundry_materials_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/scenarios", "/api/v1/planetary-foundry/scenarios"):
                res = planetary_foundry_scenarios_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/scenarios/run", "/api/v1/planetary-foundry/scenarios/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_foundry_scenario_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-foundry/grand-prix/run", "/api/v1/planetary-foundry/grand-prix/run"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = planetary_foundry_grand_prix_run_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/planetary-network/dtn/metrics", "/api/v1/planetary-network/dtn/metrics"):
                res = planetary_network_dtn_metrics_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/grand-prix/scenarios", "/api/v1/grand-prix/scenarios"):
                qp = {k: v[0] for k, v in query_params.items()} if query_params else {}
                res = grand_prix_scenarios_api(qp)
                self.send_json_response(res, 200)
                return
                res = review_evidence_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/sample-intent", "/api/v1/compiler/sample-intent"):
                res = mission_intent_sample_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/benchmark", "/api/v1/compiler/benchmark"):
                res = mission_plan_benchmark_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/plan", "/api/v1/compiler/plan"):
                res = mission_plan_get_api(query_params, self.terrain)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/compiler/debugger", "/api/v1/compiler/debugger"):
                res = mission_plan_debugger_api({}, self.terrain)
                self.send_json_response(res, 200)
                return
        except APIError as err:
            err_resp = create_api_error_response(
                error_code=err.error_code,
                message=err.message,
                status_code=err.status_code,
                details=err.details,
            )
            self.send_json_response(err_resp, err.status_code)
            return
        except WorkspaceError as err:
            err_resp = create_api_error_response(
                error_code=err.error_code,
                message=err.message,
                status_code=err.status_code,
                details=err.details,
            )
            self.send_json_response(err_resp, err.status_code)
            return
        except Exception as err:
            err_resp = create_api_error_response(
                error_code="ERR_INTERNAL",
                message=f"Internal error: {str(err)}",
                status_code=500,
            )
            self.send_json_response(err_resp, 500)
            return

        super().do_GET()

    def do_PUT(self):
        """Handle PUT requests for updating existing resources."""
        clean_path = self.path.split("?")[0]
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                raise WorkspaceError("Empty request body", status_code=400, error_code="ERR_MALFORMED_JSON")
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))

            if clean_path.startswith("/api/missions/"):
                mission_id = clean_path[len("/api/missions/"):].strip()
                res = update_mission(mission_id, payload)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/experiments/"):
                raise WorkspaceError(
                    "Experiments are immutable historical records and cannot be overwritten via PUT.",
                    status_code=405,
                    error_code="ERR_EXPERIMENT_IMMUTABLE",
                )
            else:
                raise WorkspaceError(f"Endpoint not found: {clean_path}", status_code=404, error_code="ERR_NOT_FOUND")
        except json.JSONDecodeError as err:
            err_resp = create_api_error_response("ERR_MALFORMED_JSON", f"Malformed JSON: {str(err)}", 400)
            self.send_json_response(err_resp, 400)
        except (WorkspaceError, APIError) as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, getattr(err, "details", []))
            self.send_json_response(err_resp, err.status_code)
        except ContractValidationError as err:
            err_resp = create_api_error_response("ERR_VALIDATION_FAILED", err.message, 400, details=err.errors)
            self.send_json_response(err_resp, 400)
        except Exception as err:
            err_resp = create_api_error_response("ERR_INTERNAL", f"Internal error: {str(err)}", 500)
            self.send_json_response(err_resp, 500)

    def do_DELETE(self):
        """Handle DELETE requests for removing records."""
        clean_path = self.path.split("?")[0]
        try:
            if clean_path.startswith("/api/missions/"):
                mission_id = clean_path[len("/api/missions/"):].strip()
                res = delete_mission(mission_id)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/experiments/"):
                exp_id = clean_path[len("/api/experiments/"):].strip()
                res = delete_experiment(exp_id)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/campaigns/"):
                cid = clean_path[len("/api/campaigns/"):].strip()
                res = delete_campaign(cid)
                self.send_json_response({"deleted": res, "campaign_id": cid}, 200)
                return
            elif clean_path.startswith("/api/campaign/"):
                cid = clean_path[len("/api/campaign/"):].strip()
                res = delete_campaign(cid)
                self.send_json_response({"deleted": res, "campaign_id": cid}, 200)
                return
            else:
                raise WorkspaceError(f"Endpoint not found: {clean_path}", status_code=404, error_code="ERR_NOT_FOUND")
        except (WorkspaceError, APIError) as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, getattr(err, "details", []))
            self.send_json_response(err_resp, err.status_code)
        except Exception as err:
            err_resp = create_api_error_response("ERR_INTERNAL", f"Internal error: {str(err)}", 500)
            self.send_json_response(err_resp, 500)

    def do_POST(self):
        """Handle POST requests for live A* planning, Gauntlet, comparison lab, sensitivity, briefing, and workspace entities."""
        clean_path = self.path.split("?")[0]

        # Read JSON body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length <= 0:
                raise APIError("Empty request body; expected JSON payload", 400, error_code="ERR_MALFORMED_JSON")
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as err:
            err_resp = create_api_error_response("ERR_MALFORMED_JSON", f"Malformed JSON: {str(err)}", 400)
            self.send_json_response(err_resp, 400)
            return
        except APIError as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, err.details, err.is_retryable)
            self.send_json_response(err_resp, err.status_code)
            return
        except Exception as err:
            err_resp = create_api_error_response("ERR_MALFORMED_JSON", f"Failed reading request body: {str(err)}", 400)
            self.send_json_response(err_resp, 400)
            return

        # Workspace persistence endpoints (do not require preloaded terrain)
        try:
            if clean_path == "/api/missions":
                res = save_mission(payload)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/missions/import":
                res = import_mission_json(raw_body.decode("utf-8"))
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/missions/") and clean_path.endswith("/update"):
                parts = clean_path.split("/")
                mid = parts[3]
                res = update_mission(mid, payload)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/missions/") and clean_path.endswith("/duplicate"):
                parts = clean_path.split("/")
                mid = parts[3]
                res = duplicate_mission(mid, payload.get("name"), payload.get("new_mission_id"))
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/missions/") and clean_path.endswith("/delete"):
                parts = clean_path.split("/")
                mid = parts[3]
                res = delete_mission(mid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/experiments":
                res = save_experiment(payload)
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/experiments/") and clean_path.endswith("/duplicate"):
                parts = clean_path.split("/")
                eid = parts[3]
                res = duplicate_experiment(eid, payload.get("name"))
                self.send_json_response(res, 200)
                return
            elif clean_path.startswith("/api/experiments/") and clean_path.endswith("/delete"):
                parts = clean_path.split("/")
                eid = parts[3]
                res = delete_experiment(eid)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/experiments/compare":
                res = compare_two_experiments(payload.get("experiment_id_a"), payload.get("experiment_id_b"))
                self.send_json_response(res, 200)
                return
        except APIError as err:
            err_resp = create_api_error_response(
                error_code=err.error_code,
                message=err.message,
                status_code=err.status_code,
                details=err.details,
            )
            self.send_json_response(err_resp, err.status_code)
            return
        except WorkspaceError as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, err.details)
            self.send_json_response(err_resp, err.status_code)
            return
        except ContractValidationError as err:
            err_resp = create_api_error_response("ERR_VALIDATION_FAILED", err.message, 400, details=err.errors)
            self.send_json_response(err_resp, 400)
            return
        except Exception as err:
            err_resp = create_api_error_response("ERR_WORKSPACE", f"Workspace error: {str(err)}", 500)
            self.send_json_response(err_resp, 500)
            return

        # Replay endpoint or routing simulation endpoints (require terrain)
        if self.terrain is None or self.transform is None:
            err_resp = create_api_error_response(
                error_code="ERR_TERRAIN_UNAVAILABLE",
                message="Terrain engine not initialized on server",
                status_code=503,
                is_retryable=True,
            )
            self.send_json_response(err_resp, 503)
            return

        try:
            if clean_path.startswith("/api/experiments/") and clean_path.endswith("/replay"):
                parts = clean_path.split("/")
                eid = parts[3]
                res = replay_saved_experiment(eid, self.terrain, self.transform, self.waypoints)
                self.send_json_response(res, 200)
                return
            elif clean_path == "/api/plan_route":
                result = plan_route_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/eva/plan":
                result = plan_astronaut_eva_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/eva/contingency":
                result = eva_contingency_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/gauntlet":
                result = gauntlet_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/contingency/simulate":
                result = contingency_simulate_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/scenario_comparison":
                result = scenario_comparison_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/scenario_sensitivity":
                result = scenario_sensitivity_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
            elif clean_path == "/api/export_briefing":
                result = export_briefing_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/export_decision_pack":
                zip_bytes, filename, bundle = export_decision_pack_api(
                    payload, self.terrain, self.transform, self.waypoints
                )
                self.send_binary_response(zip_bytes, content_type="application/zip", filename=filename)
                return
            elif clean_path == "/api/bundle/verify":
                result = verify_bundle_api(payload, terrain=self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/bundle/replay":
                result = replay_bundle_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/optimize":
                result = mission_optimize_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/replan":
                result = mission_replan_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/robustness":
                result = mission_robustness_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/route/explain":
                result = route_explain_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/route/terrain-analysis", "/api/route/profile"):
                result = route_terrain_analysis_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/playback":
                result = mission_playback_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/continue":
                result = mission_continue_api(payload, self.terrain, self.transform, self.waypoints)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/events":
                result = record_mission_events_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/incident/replay":
                result = replay_mission_incident_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/weather/refresh":
                result = refresh_weather_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/report":
                result = generate_mission_report_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission/report/html":
                html_bytes, filename = export_mission_report_html_api(payload, self.terrain, self.transform)
                self.send_binary_response(html_bytes, content_type="text/html; charset=utf-8", filename=filename)
                return
            elif clean_path == "/api/mission/readiness":
                result = evaluate_mission_readiness_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/campaign/plan", "/api/campaign/create"):
                result = plan_campaign_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/replan":
                result = replan_campaign_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/export_report":
                result = export_campaign_report_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/progress":
                result = record_campaign_progress_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/observations":
                result = record_campaign_observation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/reprioritize":
                result = reprioritize_campaign_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/scenarios/evaluate":
                result = evaluate_campaign_scenarios_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/scenarios/apply":
                result = apply_campaign_scenario_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/coordinate":
                result = coordinate_campaign_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/handoff":
                result = execute_campaign_handoff_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/coordination/apply":
                result = apply_campaign_coordination_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/simulation/start":
                result = start_campaign_simulation_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/simulation/advance":
                result = advance_campaign_simulation_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/simulation/step":
                result = step_campaign_simulation_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/simulation/seek":
                result = seek_campaign_simulation_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/simulation/interrupt":
                result = interrupt_campaign_simulation_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/analyze":
                result = analyze_campaign_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/recommendations/review":
                result = review_recommendation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/design-space/evaluate":
                result = evaluate_campaign_design_space_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign/design-space/promote":
                result = promote_design_space_candidate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/robustness/evaluate":
                result = evaluate_mission_robustness_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/robustness/promote":
                result = promote_resilient_candidate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/rehearsal/execute", "/api/rehearsal/run"):
                result = execute_rehearsal_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/rehearsal/bundle/export", "/api/rehearsal/export"):
                result = export_rehearsal_bundle_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/experiment/orchestrate", "/api/experiment/run"):
                result = orchestrate_experiment_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/experiment/dossier/export", "/api/experiment/export"):
                result = export_experiment_dossier_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/relaynet/los":
                result = relaynet_los_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/relaynet/graph":
                result = relaynet_graph_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/relaynet/candidates", "/api/relaynet/candidates/screen"):
                result = relaynet_candidates_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/relaynet/optimize":
                result = relaynet_optimize_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/relaynet/timeline":
                result = relaynet_timeline_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/evaluate":
                result = joint_mission_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/optimize":
                result = joint_mission_optimize_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/compare":
                result = joint_mission_compare_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/joint-mission/promote":
                result = joint_mission_promote_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/joint-mission/resource-evaluate", "/api/resource/evaluate"):
                result = joint_mission_resource_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/joint-mission/resource-sensitivity", "/api/resource/sensitivity"):
                result = joint_mission_resource_sensitivity_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/evaluate":
                result = science_mission_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/optimize":
                result = science_mission_optimize_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/configurations":
                result = science_mission_configurations_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/transfers/evaluate":
                result = science_mission_transfers_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/compatibility":
                result = science_mission_compatibility_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/science-mission/recovery-lab":
                result = science_mission_recovery_lab_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/create":
                result = campaign_operations_create_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/plan" or (clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/plan")):
                if clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/plan") and clean_path != "/api/campaign-operations/plan":
                    cid = clean_path[len("/api/campaign-operations/"):-len("/plan")]
                    payload["campaign_id"] = cid
                result = campaign_operations_plan_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/execute-event" or (clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/execute-event")):
                if clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/execute-event") and clean_path != "/api/campaign-operations/execute-event":
                    cid = clean_path[len("/api/campaign-operations/"):-len("/execute-event")]
                    payload["campaign_id"] = cid
                result = campaign_operations_execute_event_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/advance-sol" or (clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/advance-sol")):
                if clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/advance-sol") and clean_path != "/api/campaign-operations/advance-sol":
                    cid = clean_path[len("/api/campaign-operations/"):-len("/advance-sol")]
                    payload["campaign_id"] = cid
                result = campaign_operations_advance_sol_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/replan" or (clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/replan")):
                if clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/replan") and clean_path != "/api/campaign-operations/replan":
                    cid = clean_path[len("/api/campaign-operations/"):-len("/replan")]
                    payload["campaign_id"] = cid
                result = campaign_operations_replan_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-operations/scenario" or (clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/scenario")):
                if clean_path.startswith("/api/campaign-operations/") and clean_path.endswith("/scenario") and clean_path != "/api/campaign-operations/scenario":
                    cid = clean_path[len("/api/campaign-operations/"):-len("/scenario")]
                    payload["campaign_id"] = cid
                result = campaign_operations_scenario_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission-assurance/evaluate":
                result = mission_assurance_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/mission-assurance/dossier":
                result = mission_assurance_dossier_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-branches/create":
                result = campaign_branches_create_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-branches/compare":
                result = campaign_branches_compare_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/campaign-branches/"):
                sub_path = clean_path[len("/api/campaign-branches/"):]
                if sub_path.endswith("/replay"):
                    bid = sub_path[:-len("/replay")]
                    payload["branch_id"] = bid
                    result = campaign_branches_replay_api(payload, self.terrain, self.transform)
                elif sub_path.endswith("/scenario"):
                    bid = sub_path[:-len("/scenario")]
                    payload["branch_id"] = bid
                    result = campaign_branches_scenario_api(payload, self.terrain, self.transform)
                elif sub_path.endswith("/compare"):
                    bid = sub_path[:-len("/compare")]
                    payload["branch_id"] = bid
                    result = campaign_branches_compare_api(payload, self.terrain, self.transform)
                elif sub_path.endswith("/promote"):
                    bid = sub_path[:-len("/promote")]
                    payload["branch_id"] = bid
                    result = campaign_branches_promote_api(payload, self.terrain, self.transform)
                else:
                    result = campaign_branches_create_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/campaign-robustness/evaluate":
                result = campaign_robustness_evaluate_api(payload, self.terrain, self.transform)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/create":
                result = fleet_create_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/register-rover"):
                fid = clean_path[len("/api/fleet/"):-len("/register-rover")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_register_rover_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/register-rover":
                result = fleet_register_rover_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/allocate-science"):
                fid = clean_path[len("/api/fleet/"):-len("/allocate-science")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_allocate_science_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/allocate-science":
                result = fleet_allocate_science_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/plan-routes"):
                fid = clean_path[len("/api/fleet/"):-len("/plan-routes")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_plan_routes_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/plan-routes":
                result = fleet_plan_routes_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/schedule"):
                fid = clean_path[len("/api/fleet/"):-len("/schedule")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_schedule_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/schedule":
                result = fleet_schedule_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/optimize"):
                fid = clean_path[len("/api/fleet/"):-len("/optimize")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_optimize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/optimize":
                result = fleet_optimize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/scenario"):
                fid = clean_path[len("/api/fleet/"):-len("/scenario")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_scenario_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/scenario":
                result = fleet_scenario_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path.startswith("/api/fleet/") and clean_path.endswith("/promote"):
                fid = clean_path[len("/api/fleet/"):-len("/promote")].strip("/")
                payload["fleet_id"] = fid or payload.get("fleet_id", "fleet_jezero_alpha")
                result = fleet_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path == "/api/fleet/promote":
                result = fleet_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment/point", "/api/v1/environment/point"):
                result = environmental_point_eval_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment/windows", "/api/v1/environment/windows", "/api/environment/window"):
                result = environmental_window_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/calibrate", "/api/v1/environment-validation/calibrate"):
                result = environment_validation_calibrate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/representativeness", "/api/v1/environment-validation/representativeness"):
                result = environment_validation_representativeness_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/collocate", "/api/v1/environment-validation/collocate"):
                result = environment_validation_collocate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/evaluate", "/api/v1/environment-validation/evaluate"):
                result = environment_validation_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/scenarios/run", "/api/v1/deep-space/scenarios/run"):
                result = deep_space_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/commands/create", "/api/v1/deep-space/commands/create"):
                result = deep_space_command_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/commands/transmit", "/api/v1/deep-space/commands/transmit"):
                result = deep_space_command_transmit_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/advance", "/api/v1/deep-space/simulation/advance"):
                result = deep_space_simulation_advance_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/inject-hazard", "/api/v1/deep-space/simulation/inject-hazard"):
                result = deep_space_inject_hazard_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/deep-space/simulation/reset", "/api/v1/deep-space/simulation/reset"):
                result = deep_space_reset_simulation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/fleet/create", "/api/v1/aerial/fleet/create"):
                result = aerial_aircraft_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/performance/evaluate", "/api/v1/aerial/performance/evaluate"):
                result = aerial_performance_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/mission/plan", "/api/v1/aerial/mission/plan"):
                result = aerial_mission_plan_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/rover-cooperation/plan", "/api/v1/aerial/rover-cooperation/plan"):
                result = aerial_rover_cooperation_plan_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/scenarios/run", "/api/v1/aerial/scenarios/run"):
                result = aerial_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/aerial/reset", "/api/v1/aerial/reset"):
                result = aerial_reset_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/hypothesis/create", "/api/v1/science-discovery/hypothesis/create"):
                result = science_discovery_hypothesis_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/uncertainty/evaluate", "/api/v1/science-discovery/uncertainty/evaluate"):
                result = science_discovery_uncertainty_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/experiments/execute", "/api/v1/science-discovery/experiments/execute"):
                result = science_discovery_experiments_execute_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/scenarios/run", "/api/v1/science-discovery/scenarios/run"):
                result = science_discovery_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/replay", "/api/v1/science-discovery/replay"):
                result = science_discovery_replay_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/science-discovery/reset", "/api/v1/science-discovery/reset"):
                result = science_discovery_reset_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/faults/inject", "/api/v1/resilience/faults/inject"):
                result = resilience_inject_fault_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/diagnose", "/api/v1/resilience/diagnose"):
                result = resilience_diagnose_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/propagation", "/api/v1/resilience/propagation"):
                result = resilience_propagation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/recovery/evaluate", "/api/v1/resilience/recovery/evaluate"):
                result = resilience_recovery_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/scenarios/run", "/api/v1/resilience/scenarios/run"):
                result = resilience_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/resilience/reset", "/api/v1/resilience/reset"):
                result = resilience_reset_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/advance", "/api/v1/settlement/advance"):
                result = settlement_advance_simulation_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/power/simulate", "/api/v1/settlement/power/simulate"):
                result = settlement_power_simulate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/isru/evaluate", "/api/v1/settlement/isru/evaluate"):
                result = settlement_isru_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/consumables", "/api/v1/settlement/consumables"):
                result = settlement_consumables_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/habitat/thermal", "/api/v1/settlement/habitat/thermal"):
                result = settlement_habitat_thermal_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/construction/step", "/api/v1/settlement/construction/step"):
                result = settlement_construction_step_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/scenarios/run", "/api/v1/settlement/scenarios/run"):
                result = settlement_scenario_run_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/resilience/evaluate", "/api/v1/settlement/resilience/evaluate"):
                result = settlement_resilience_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/settlement/reset", "/api/v1/settlement/reset"):
                result = settlement_reset_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/mission-os/create", "/api/v1/mission-os/create"):
                result = mission_os_create_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/mission-os/advance", "/api/v1/mission-os/advance"):
                result = mission_os_advance_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/mission-os/dispatch-command", "/api/v1/mission-os/dispatch-command"):
                result = mission_os_dispatch_command_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/mission-os/inject-event", "/api/v1/mission-os/inject-event"):
                result = mission_os_inject_event_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/mission-os/flagship/run", "/api/v1/mission-os/flagship/run"):
                result = mission_os_flagship_run_api()
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/flagship/when-mars-goes-dark/run", "/api/v1/flagship/when-mars-goes-dark/run"):
                result = flagship_mars_dark_run_api(self.terrain, payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/pillars/terrain/inspect", "/api/v1/pillars/terrain/inspect"):
                result = pillars_terrain_inspect_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/pillars/environment-meda/calibrate", "/api/v1/pillars/environment-meda/calibrate"):
                result = pillars_environment_meda_calibrate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/pillars/science-targets/plan", "/api/v1/pillars/science-targets/plan"):
                result = pillars_science_targets_plan_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/validate", "/api/v1/compiler/validate"):
                result = mission_intent_validate_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/normalize", "/api/v1/compiler/normalize"):
                result = mission_intent_normalize_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/compile", "/api/v1/compiler/compile"):
                result = mission_plan_compile_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/evaluate", "/api/v1/compiler/evaluate"):
                result = mission_plan_evaluate_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/compare", "/api/v1/compiler/compare"):
                result = mission_plan_compare_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/debug", "/api/v1/compiler/debug"):
                result = mission_plan_debugger_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/compiler/promote", "/api/v1/compiler/promote"):
                result = mission_plan_promote_api(payload, self.terrain)
                self.send_json_response(result, 200)
                return
            else:
                err_resp = create_api_error_response(
                    error_code="ERR_NOT_FOUND",
                    message=f"Endpoint not found: {clean_path}",
                    status_code=404,
                )
                self.send_json_response(err_resp, 404)
                return
        except APIError as err:
            err_resp = create_api_error_response(
                error_code=err.error_code,
                message=err.message,
                status_code=err.status_code,
                details=err.details,
            )
            self.send_json_response(err_resp, err.status_code)
            return
        except WorkspaceError as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, err.details)
            self.send_json_response(err_resp, err.status_code)
        except APIError as err:
            err_resp = create_api_error_response(err.error_code, err.message, err.status_code, err.details, err.is_retryable)
            self.send_json_response(err_resp, err.status_code)
        except ContractValidationError as err:
            err_resp = create_api_error_response("ERR_VALIDATION_FAILED", err.message, 400, details=err.errors)
            self.send_json_response(err_resp, 400)
        except Exception as err:
            err_resp = create_api_error_response("ERR_INTERNAL_ROUTING", f"Internal routing error: {str(err)}", 500)
            self.send_json_response(err_resp, 500)


def find_available_port(start_port: int = 3000, max_attempts: int = 20) -> int:
    """Find an available TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    return start_port


def preload_terrain_and_waypoints(
    geotiff_path: str = "data/processed/jezero_ready_20m.tif",
    waypoints_path: str = "data/waypoints_jezero.json",
):
    """Preload TerrainGrid and waypoints in memory for instantaneous route calculations."""
    print(f"[MarsWalk Atlas] Preloading Jezero terrain from {geotiff_path}...")
    terrain = load_and_process_terrain(geotiff_path)

    with rasterio.open(geotiff_path) as src:
        transform = src.transform

    waypoints: List[ScienceWaypoint] = []
    if os.path.exists(waypoints_path):
        from marswalk.data.ingest import query_elevation_at_lonlat
        with open(waypoints_path, "r", encoding="utf-8") as f:
            wp_data = json.load(f)
        for wp in wp_data.get("waypoints", []):
            try:
                elev, r, c = query_elevation_at_lonlat(geotiff_path, wp["lon_deg"], wp["lat_deg"])
                waypoints.append(
                    ScienceWaypoint(
                        id=wp["id"],
                        name=wp["name"],
                        rc=(r, c),
                        priority_score=float(wp.get("priority_score", 0.0)),
                        geological_context=wp.get("geological_context", ""),
                        crism_signature=wp.get("crism_signature", ""),
                        pds_citation=wp.get("pds_citation", ""),
                    )
                )
            except Exception as e:
                print(f"[MarsWalk Atlas] Warning loading waypoint {wp.get('id')}: {e}")

    print(f"[MarsWalk Atlas] Terrain preloaded ({terrain.height}x{terrain.width}). {len(waypoints)} waypoints ready.")
    return terrain, transform, waypoints


def main():
    parser = argparse.ArgumentParser(description="Launch MarsWalk 2.0 3D Atlas and Live Routing API.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface to bind to (default: 0.0.0.0 for LAN/WSL/Windows access)")
    parser.add_argument("--port", type=int, default=3000, help="Port to serve on (default: 3000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open default web browser")
    parser.add_argument("--export-only", action="store_true", help="Only export mission assets and exit")
    parser.add_argument("--demo", action="store_true", help="Launch browser directly in Conference Demonstration mode (?mode=demo)")
    args = parser.parse_args()

    web_dir = os.path.join(PROJECT_ROOT, "web")
    os.chdir(PROJECT_ROOT)

    # 1. Verify / Export mission assets
    mission_json = os.path.join(web_dir, "data", "jezero_mission_data.json")
    if not os.path.exists(mission_json):
        print("[MarsWalk Atlas] Exporting authentic mission assets from USGS DTM...")
        from scripts.export_mission_assets import export_mission_assets
        export_mission_assets()

    if args.export_only:
        print("[MarsWalk Atlas] Export completed. Exiting.")
        sys.exit(0)

    # 2. Preload terrain in memory
    geotiff = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")
    wps_json = os.path.join(PROJECT_ROOT, "data", "waypoints_jezero.json")
    terrain, transform, waypoints = preload_terrain_and_waypoints(geotiff, wps_json)

    MarsWalkHTTPRequestHandler.terrain = terrain
    MarsWalkHTTPRequestHandler.transform = transform
    MarsWalkHTTPRequestHandler.waypoints = waypoints

    # 3. Start HTTP server in web directory
    port = find_available_port(args.port)
    os.chdir(web_dir)

    def get_primary_lan_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    lan_ip = get_primary_lan_ip()
    server_address = (args.host, port)
    httpd = ThreadingHTTPServer(server_address, MarsWalkHTTPRequestHandler)
    httpd.daemon_threads = True
    base_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{lan_ip}:{port}"
    url = f"{base_url}/?mode=demo" if args.demo else base_url

    print("=" * 72)
    print("  MARSWALK 2.0 — PROJECT ATLAS: 3D PLANETARY WORKSTATION & LIVE API")
    print(f"  Primary Local URL:    {url}")
    print(f"  Network / Windows URL: {lan_url}")
    print(f"  Binding Address:      {args.host}:{port}")
    print(f"  Routing API:          {base_url}/api/plan_route  (POST)")
    print(f"  Gauntlet API:         {base_url}/api/gauntlet    (POST)")
    print(f"  Missions API:         {base_url}/api/missions    (GET, POST)")
    print(f"  Experiments API:      {base_url}/api/experiments (GET, POST)")
    print(f"  Health Status:        {base_url}/api/health      (GET)")
    print("  Target:               Mars (IAU 2000 Sphere / USGS CTX Jezero Crater DTM)")
    print("  Press CTRL+C to terminate the server.")
    print("=" * 72)

    if not args.no_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[MarsWalk Atlas] Server stopped gracefully.")
        httpd.server_close()


if __name__ == "__main__":
    main()
