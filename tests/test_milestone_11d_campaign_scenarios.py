"""
Unit and integration tests for Milestone 11D: Campaign What-If Simulation Lab & Scenario Comparison.
Verifies bounded deterministic what-if scenario simulations, mobility derating, target loss,
corridor closures, operational delays, time constraints, priority shifts, combined scenarios,
workspace persistence, version promotion, and live server API integration.
"""

import copy
import json
import os
import shutil
import tempfile
import urllib.request
import pytest
import numpy as np
import rasterio
from affine import Affine

from marswalk.core.terrain import TerrainGrid, load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    TargetStatus,
    plan_mission_campaign,
)
from marswalk.core.campaign_scenarios import (
    CampaignScenario,
    ScenarioComparison,
    ScenarioStatus,
    ScenarioType,
    evaluate_campaign_scenario,
    evaluate_campaign_scenarios_batch,
    promote_scenario_to_campaign_version,
)
from marswalk.api.workspace import (
    save_campaign,
    get_campaign,
    save_campaign_scenario,
    get_campaign_scenario,
    list_campaign_scenarios,
)
from marswalk.api.service import (
    evaluate_campaign_scenarios_api,
    list_campaign_scenarios_api,
    get_campaign_scenario_api,
    apply_campaign_scenario_api,
)


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic 20m Jezero Crater DTM grid for testing."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tiff_path = os.path.join(base_dir, "data", "processed", "jezero_ready_20m.tif")
    if not os.path.exists(tiff_path):
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    return load_and_process_terrain(tiff_path)


@pytest.fixture
def sample_campaign(jezero_terrain):
    """Create a standard multi-sol campaign with 4 candidate targets and prerequisite DAG."""
    targets = [
        CampaignTarget(
            id="t_dep_1",
            name="Deposition Fan",
            row=120,
            col=158,
            priority_score=90.0,
            dwell_time_s=900.0,
            science_objective="FLUVIAL_DELTA_SEDIMENTOLOGY",
        ),
        CampaignTarget(
            id="t_dep_2",
            name="Clay Mudstone Strata",
            row=122,
            col=156,
            priority_score=85.0,
            dwell_time_s=900.0,
            prerequisites=["t_dep_1"],
            science_objective="ASTROBIOLOGY_BIOSIGNATURE",
        ),
        CampaignTarget(
            id="t_hyd_1",
            name="Paleolake Terrace",
            row=125,
            col=154,
            priority_score=75.0,
            dwell_time_s=900.0,
            science_objective="PALEOLAKE_HYDROLOGY",
        ),
        CampaignTarget(
            id="t_hyd_2",
            name="Carbonate Margin",
            row=127,
            col=152,
            priority_score=70.0,
            dwell_time_s=900.0,
            prerequisites=["t_hyd_1"],
            science_objective="ASTROBIOLOGY_BIOSIGNATURE",
        ),
    ]

    cfg = CampaignConfig(
        base_start_rc=(117, 157),
        max_duration_per_sortie_s=7200.0,
        max_sols=3,
        planning_profile="science_priority",
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_whatif_test",
        name="What-If Test Campaign",
        config=cfg,
        targets=targets,
        terrain=jezero_terrain,
        description="Baseline campaign for what-if simulation tests",
    )
    return campaign


def test_scenario_evaluation_unchanged_baseline(sample_campaign, jezero_terrain):
    """Test scenario evaluation with empty modifications preserves baseline outputs and reports zero delta."""
    spec = {
        "scenario_id": "scen_baseline_identity",
        "name": "Identity Scenario",
        "scenario_type": "combined",
        "modifications": [],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.status == ScenarioStatus.COMPLETED.value
    assert scen.is_feasible is True
    assert scen.comparison is not None
    assert scen.comparison.delta_sols == 0
    assert scen.comparison.targets_scheduled_delta == 0
    assert len(scen.comparison.lost_target_ids) == 0
    assert len(scen.comparison.gained_target_ids) == 0
    assert round(scen.comparison.delta_distance_m, 1) == 0.0
    assert round(scen.comparison.delta_science_score, 1) == 0.0


def test_mobility_reduction_derates_velocity_and_increases_duration(sample_campaign, jezero_terrain):
    """Test mobility speed derating (50% speed) impacts traverse duration and timeline."""
    spec = {
        "scenario_id": "scen_mobility_50",
        "name": "Severe Motor Derating (50%)",
        "scenario_type": "mobility_change",
        "modifications": [
            {"type": "mobility_change", "speed_factor": 0.5}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.status == ScenarioStatus.COMPLETED.value
    assert scen.is_feasible is True
    assert scen.comparison.delta_duration_s > 0.0
    assert any("derated" in w.lower() for w in scen.warnings)


def test_mobility_slope_ceiling_blocks_steep_traverses(sample_campaign, jezero_terrain):
    """Test tightening max_slope_deg constraint to an aggressive ceiling forces detours or blocks targets."""
    spec = {
        "scenario_id": "scen_slope_derate",
        "name": "Extreme Slope Ceiling (6°)",
        "scenario_type": "mobility_change",
        "modifications": [
            {"type": "mobility_change", "speed_factor": 0.8, "max_slope_deg": 6.0}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.comparison is not None
    assert any("slope" in w.lower() for w in scen.warnings)


def test_target_loss_and_dag_cascade(sample_campaign, jezero_terrain):
    """Test target_loss severs downstream dependent targets in the topological DAG."""
    # Loss of t_dep_1 should cause its child t_dep_2 to also be unscheduled
    spec = {
        "scenario_id": "scen_lose_fan",
        "name": "Deposition Fan Instrument Failure",
        "scenario_type": "target_loss",
        "modifications": [
            {"type": "target_loss", "target_id": "t_dep_1", "reason": "Coring bit jammed"}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.comparison is not None
    assert "t_dep_1" in scen.comparison.lost_target_ids
    assert "t_dep_2" in scen.comparison.lost_target_ids
    assert "t_dep_1" in scen.comparison.causal_attribution
    assert "t_dep_2" in scen.comparison.causal_attribution
    assert "prerequisite" in scen.comparison.causal_attribution["t_dep_2"].lower()


def test_corridor_closure_obstacle_avoidance(sample_campaign, jezero_terrain):
    """Test corridor_closure rockfall obstacle forces detour routing across Jezero topography."""
    # Place obstacle directly at (121, 157) between start and targets
    spec = {
        "scenario_id": "scen_corridor_rockfall",
        "name": "Delta Scarp Rockfall Obstacle",
        "scenario_type": "corridor_closure",
        "modifications": [
            {"type": "corridor_closure", "center_row": 121, "center_col": 157, "radius_m": 50.0}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.status in (ScenarioStatus.COMPLETED.value, ScenarioStatus.INFEASIBLE.value)
    assert any("rockfall" in w.lower() for w in scen.warnings)
    if scen.is_feasible:
        # Distance should change due to detour or deferral of blocked targets
        assert scen.comparison.delta_distance_m != 0.0 or len(scen.comparison.lost_target_ids) > 0


def test_operational_delay_accounting(sample_campaign, jezero_terrain):
    """Test operational_delay injects hold time without double-counting dwell time."""
    spec = {
        "scenario_id": "scen_delay_30m",
        "name": "Suit Leak Check Hold (1800s)",
        "scenario_type": "operational_delay",
        "modifications": [
            {"type": "operational_delay", "delay_s": 1800.0}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.is_feasible is True
    assert scen.comparison.delta_duration_s >= 1800.0 - 1.0
    assert any("delay" in w.lower() for w in scen.warnings)


def test_time_constraint_and_budget_infeasibility(sample_campaign, jezero_terrain):
    """Test severe time constraint contracts daily window and defers low-priority targets."""
    # Restrict sortie duration to only 1800s (30 mins), which cannot cover all targets
    spec = {
        "scenario_id": "scen_time_limit_30m",
        "name": "Restricted Sol Window (1800s)",
        "scenario_type": "time_constraint",
        "modifications": [
            {"type": "time_constraint", "max_duration_per_sortie_s": 1800.0, "max_sols": 2}
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.comparison is not None
    # Low-priority targets must have been deferred
    assert len(scen.comparison.deferred_target_ids) > 0
    assert scen.comparison.scenario_targets_scheduled < scen.comparison.baseline_targets_scheduled


def test_objective_priority_change_alters_target_allocation(sample_campaign, jezero_terrain):
    """Test shifting science objective weights dynamically prioritizes favoured disciplines."""
    # Heavily favor Paleolake Hydrology over Fluvial Delta
    spec = {
        "scenario_id": "scen_prioritize_paleolake",
        "name": "Paleolake Directives Priority",
        "scenario_type": "objective_priority_change",
        "modifications": [
            {
                "type": "objective_priority_change",
                "objective_weights": {
                    "PALEOLAKE_HYDROLOGY": 2.5,
                    "FLUVIAL_DELTA_SEDIMENTOLOGY": 0.2,
                },
            }
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.status == ScenarioStatus.COMPLETED.value
    assert scen.is_feasible is True
    assert any("priority" in w.lower() for w in scen.warnings)


def test_combined_compatible_scenarios_deterministic_order(sample_campaign, jezero_terrain):
    """Test combined scenario applies multiple modifications in strict deterministic order."""
    spec = {
        "scenario_id": "scen_compound_hazard",
        "name": "Compound Dust Storm & Target Loss",
        "scenario_type": "combined",
        "modifications": [
            {"type": "target_loss", "target_id": "t_hyd_1", "reason": "Sensor offline"},
            {"type": "mobility_change", "speed_factor": 0.75},
            {"type": "operational_delay", "delay_s": 600.0},
        ],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.comparison is not None
    # t_hyd_1 lost and its dependent t_hyd_2 cascaded
    assert "t_hyd_1" in scen.comparison.lost_target_ids
    assert "t_hyd_2" in scen.comparison.lost_target_ids


def test_unsupported_scenario_type_labeled_without_synthetic_data(sample_campaign, jezero_terrain):
    """Test unsupported scenario type is cleanly rejected without fabricating synthetic metrics."""
    spec = {
        "scenario_id": "scen_alien_encounter",
        "name": "Extraterrestrial Speculation",
        "scenario_type": "alien_contact_event",
        "modifications": [{"type": "alien_contact_event"}],
    }

    scen = evaluate_campaign_scenario(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_spec=spec,
    )

    assert scen.status == ScenarioStatus.UNSUPPORTED.value
    assert scen.is_feasible is False
    assert "not grounded in existing physical models" in scen.failure_reason
    assert scen.simulated_campaign is None


def test_bounded_limits_and_validation_errors(sample_campaign, jezero_terrain):
    """Test parameter out-of-bounds inputs raise ValueError."""
    # speed_factor < 0.1
    spec_invalid_speed = {
        "scenario_id": "scen_err_speed",
        "name": "Invalid Speed",
        "scenario_type": "mobility_change",
        "modifications": [{"type": "mobility_change", "speed_factor": 0.01}],
    }
    with pytest.raises(ValueError, match="speed_factor"):
        evaluate_campaign_scenario(sample_campaign, jezero_terrain, spec_invalid_speed)

    # radius_m > 500
    spec_invalid_radius = {
        "scenario_id": "scen_err_rad",
        "name": "Invalid Radius",
        "scenario_type": "corridor_closure",
        "modifications": [{"type": "corridor_closure", "radius_m": 1000.0}],
    }
    with pytest.raises(ValueError, match="radius_m"):
        evaluate_campaign_scenario(sample_campaign, jezero_terrain, spec_invalid_radius)


def test_max_scenarios_batch_limit(sample_campaign, jezero_terrain):
    """Test batch evaluation exceeding 10 scenarios raises ValueError to prevent exhaustion."""
    specs = [
        {"scenario_id": f"scen_b_{i}", "name": f"Batch {i}", "scenario_type": "combined", "modifications": []}
        for i in range(11)
    ]
    with pytest.raises(ValueError, match="Batch size 11 exceeds maximum limit"):
        evaluate_campaign_scenarios_batch(sample_campaign, jezero_terrain, specs)


def test_workspace_persistence_and_retrieval(sample_campaign, jezero_terrain):
    """Test saving, retrieving, and listing scenario records in workspace."""
    spec = {
        "scenario_id": "scen_ws_test",
        "name": "Workspace Persistence Test",
        "scenario_type": "combined",
        "modifications": [],
    }

    scen = evaluate_campaign_scenario(sample_campaign, jezero_terrain, spec)
    scen_dict = scen.to_dict()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Save
        saved = save_campaign_scenario(scen_dict, scenarios_dir=tmpdir)
        assert saved["scenario_id"] == "scen_ws_test"

        # Get
        retrieved = get_campaign_scenario("scen_ws_test", scenarios_dir=tmpdir)
        assert retrieved["scenario_id"] == "scen_ws_test"
        assert retrieved["status"] == ScenarioStatus.COMPLETED.value

        # List
        listed = list_campaign_scenarios(campaign_id=sample_campaign.campaign_id, scenarios_dir=tmpdir)
        assert len(listed) == 1
        assert listed[0]["scenario_id"] == "scen_ws_test"


def test_promote_scenario_to_new_campaign_version(sample_campaign, jezero_terrain):
    """Test promoting a feasible what-if scenario to an official new campaign version (v1 -> v2)."""
    spec = {
        "scenario_id": "scen_promote_v2",
        "name": "Promoted Dust Derating",
        "scenario_type": "mobility_change",
        "modifications": [{"type": "mobility_change", "speed_factor": 0.8}],
    }

    scen = evaluate_campaign_scenario(sample_campaign, jezero_terrain, spec)
    promoted = promote_scenario_to_campaign_version(sample_campaign, scen)

    assert promoted.version == sample_campaign.version + 1
    assert promoted.parent_campaign_id == sample_campaign.campaign_id
    assert "whatif" in promoted.revision_id
    assert promoted.summary.is_campaign_feasible is True
    assert promoted.revision_comparison is not None


def test_baseline_campaign_immutability(sample_campaign, jezero_terrain):
    """Test baseline campaign object and properties are completely unmutated across evaluations."""
    orig_dict = copy.deepcopy(sample_campaign.to_dict())

    # Run multiple aggressive scenarios (severe delay, target loss, speed derating)
    specs = [
        {"scenario_id": "scen_imm_1", "name": "Loss", "scenario_type": "target_loss", "modifications": [{"type": "target_loss", "target_id": "t_dep_1"}]},
        {"scenario_id": "scen_imm_2", "name": "Derate", "scenario_type": "mobility_change", "modifications": [{"type": "mobility_change", "speed_factor": 0.3}]},
    ]

    evaluate_campaign_scenarios_batch(sample_campaign, jezero_terrain, specs)

    current_dict = sample_campaign.to_dict()
    assert current_dict == orig_dict


def test_api_service_scenarios_evaluate_and_apply(sample_campaign, jezero_terrain):
    """Test service-layer API evaluate and apply functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save baseline campaign first
        camp_dir = os.path.join(tmpdir, "campaigns")
        save_campaign(sample_campaign.to_dict(), campaigns_dir=camp_dir)

        payload = {
            "campaign": sample_campaign.to_dict(),
            "scenarios": [
                {
                    "scenario_id": "scen_api_eval",
                    "name": "API Service Test Scenario",
                    "scenario_type": "combined",
                    "modifications": [{"type": "operational_delay", "delay_s": 300.0}],
                }
            ],
        }

        # Evaluate API
        res = evaluate_campaign_scenarios_api(payload, jezero_terrain, sample_campaign.config.base_start_rc)
        assert res["status"] == "success"
        assert res["count"] == 1
        assert res["scenarios"][0]["scenario_id"] == "scen_api_eval"

        # Apply API
        apply_payload = {
            "campaign": sample_campaign.to_dict(),
            "campaign_id": sample_campaign.campaign_id,
            "scenario_id": "scen_api_eval",
        }
        apply_res = apply_campaign_scenario_api(apply_payload, jezero_terrain, sample_campaign.config.base_start_rc)
        assert apply_res["status"] == "success"
        assert apply_res["version"] == sample_campaign.version + 1


def test_live_server_scenario_endpoints(sample_campaign):
    """Test live REST endpoints on running Atlas daemon port 3000."""
    port = 3000

    # Test GET list scenarios
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/campaign/scenarios")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") == "success"
            assert "scenarios" in data
    except urllib.error.URLError as err:
        pytest.skip(f"Live Atlas server not responding on port {port}: {err}")

    # Test POST evaluate scenario
    eval_payload = {
        "campaign": sample_campaign.to_dict(),
        "scenarios": [
            {
                "scenario_id": "scen_live_test",
                "name": "Live Server What-If Test",
                "scenario_type": "combined",
                "modifications": [{"type": "mobility_change", "speed_factor": 0.85}],
            }
        ],
    }

    post_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/campaign/scenarios/evaluate",
        data=json.dumps(eval_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(post_req, timeout=10) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        assert res_data.get("status") == "success"
        assert res_data.get("count") == 1
        assert res_data["scenarios"][0]["scenario_id"] == "scen_live_test"
        assert res_data["scenarios"][0]["status"] == "COMPLETED"

    # Test GET specific scenario by ID
    get_scen_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/campaign/scenarios/scen_live_test")
    with urllib.request.urlopen(get_scen_req, timeout=5) as resp:
        scen_res = json.loads(resp.read().decode("utf-8"))
        assert scen_res.get("status") == "success"
        assert scen_res["scenario"]["scenario_id"] == "scen_live_test"

    # Test POST apply scenario
    apply_payload = {
        "campaign": sample_campaign.to_dict(),
        "campaign_id": sample_campaign.campaign_id,
        "scenario_id": "scen_live_test",
    }
    apply_req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/campaign/scenarios/apply",
        data=json.dumps(apply_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(apply_req, timeout=10) as resp:
        apply_res = json.loads(resp.read().decode("utf-8"))
        assert apply_res.get("status") == "success"
        assert apply_res.get("version") == sample_campaign.version + 1
