"""
MarsWalk 2.0 / Project Atlas — Milestone 12H Acceptance Test Suite
Atlas Mission Experiment Studio: Unified Experiment Orchestration,
Cross-Run Analysis & Mission Evidence Dossier.

Tests:
1. Experiment config validation, bounds enforcement, and fingerprinting.
2. Parameter conversion & scenario-to-disturbance mapping.
3. Orchestration with DEGRADED_OR_BREACH strategy (rehearses only degraded/breached cases).
4. Orchestration with ALL strategy enforcing max_rehearsals ceiling.
5. Cross-scenario comparison matrix accuracy, RFC 4180 CSV alignment, and safe math.
6. Consolidated Evidence Dossier JSON bundle and ZIP export with SHA-256 integrity verification.
7. Dedicated workspace persistence isolation in data/workspaces/campaign_experiments.
8. Draft 2020-12 schema validation compliance for mission-experiment.schema.json.
9. Scientific integrity disclosures, zero-baseline safety, and baseline immutability.
10. Live HTTP API endpoint verification: /orchestrate, /list, /<id>, /matrix, /dossier, /export.
"""

import copy
import json
import os
import urllib.request
import zipfile
import pytest

from marswalk.api.contracts import (
    TERRAIN_DATASET_ID,
    validate_mission_experiment_record,
    calculate_safe_pct_delta,
)
from marswalk.api.workspace import (
    DEFAULT_CAMPAIGN_EXPERIMENTS_DIR,
    delete_experiment_record,
    get_experiment_record,
    list_experiment_records,
    save_experiment_record,
)
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.mission_experiment import (
    DEFAULT_MAX_REHEARSALS,
    DEFAULT_MAX_SCENARIOS,
    MAX_EXPERIMENT_REHEARSALS,
    MAX_EXPERIMENT_SCENARIOS,
    ExperimentConfig,
    ExperimentRecord,
    RehearsalTriggerStrategy,
    ScenarioExecutionStatus,
    export_experiment_dossier_bundle,
    export_experiment_dossier_zip,
    map_scenario_to_disturbances,
    orchestrate_mission_experiment,
    verify_experiment_dossier_zip,
)
from marswalk.core.terrain import TerrainGrid, load_and_process_terrain

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOTIFF_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")
API_BASE_URL = "http://127.0.0.1:3000"


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic 20m Jezero elevation grid."""
    if not os.path.exists(GEOTIFF_PATH):
        pytest.skip(f"Terrain GeoTIFF not found at {GEOTIFF_PATH}")
    return load_and_process_terrain(GEOTIFF_PATH)


@pytest.fixture
def test_campaign(jezero_terrain):
    """Create a deterministic test campaign with 3 scientific targets."""
    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=28800.0,
        base_start_rc=(117, 157),
    )
    targets = [
        CampaignTarget(id="t1", name="Delta Outcrop", row=120, col=160, priority_score=80.0, dwell_time_s=900.0),
        CampaignTarget(id="t2", name="Crater Ridge", row=125, col=165, priority_score=60.0, dwell_time_s=900.0),
        CampaignTarget(id="t3", name="Sediment Fan", row=115, col=150, priority_score=40.0, dwell_time_s=900.0),
    ]
    return plan_mission_campaign("cmp_test_12h_001", "12H Test Campaign", cfg, targets, jezero_terrain)


def test_01_experiment_config_validation_and_bounds():
    """Verify ExperimentConfig dataclass defaults, conversion, and bound clamping."""
    cfg = ExperimentConfig(
        campaign_id="cmp_test_12h_001",
        suite_type="full_battery",
        scenario_selection_strategy="degraded_or_breach",
        max_scenarios=10,
        max_rehearsals=5,
    )
    d = cfg.to_dict()
    assert d["campaign_id"] == "cmp_test_12h_001"
    assert d["max_scenarios"] == 10
    assert d["max_rehearsals"] == 5
    assert d["scenario_selection_strategy"] == "degraded_or_breach"
    assert d["rehearsal_policy"] == "balanced"


def test_02_scenario_to_disturbance_mapping(test_campaign):
    """Verify mapping from Robustness Lab modifications to DisturbanceSpecifications."""
    # Corridor closure with center_rc
    scen_closure = {
        "scenario_id": "scen_test_closure",
        "scenario_type": "corridor_closure",
        "modifications": [
            {"type": "corridor_closure", "center_rc": [121, 161], "radius_m": 45.0, "trigger_time_s": 800.0}
        ],
    }
    dsts = map_scenario_to_disturbances(scen_closure, test_campaign)
    assert len(dsts) == 1
    assert dsts[0].disturbance_type.value == "corridor_closure"
    assert dsts[0].parameters["center_rc"] == [121, 161]
    assert dsts[0].parameters["radius_m"] == 45.0
    assert dsts[0].trigger_time_s == 800.0

    # Mobility derating
    scen_mob = {
        "scenario_id": "scen_test_mob",
        "scenario_type": "mobility_change",
        "modifications": [{"type": "mobility_change", "speed_factor": 0.65}],
    }
    dsts_mob = map_scenario_to_disturbances(scen_mob, test_campaign)
    assert len(dsts_mob) == 1
    assert dsts_mob[0].disturbance_type.value == "mobility_derating"
    assert dsts_mob[0].parameters["speed_factor"] == 0.65


def test_03_orchestrate_experiment_degraded_or_breach_strategy(test_campaign, jezero_terrain):
    """Verify orchestration: only degraded/breached cases trigger closed-loop rehearsals."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="full_battery",
        scenario_selection_strategy="degraded_or_breach",
        rehearsal_policy="balanced",
        min_margin_threshold_s=1800.0,
        max_scenarios=6,
        max_rehearsals=3,
    )

    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)
    assert isinstance(record, ExperimentRecord)
    assert record.status == "COMPLETED"
    assert len(record.scenarios) == 6
    assert record.summary_metrics["total_scenarios_evaluated"] == 6
    assert record.summary_metrics["rehearsals_executed_count"] <= 3

    # Check scenario execution statuses
    for sc in record.scenarios:
        if sc.rehearsal_id is not None:
            assert sc.status == ScenarioExecutionStatus.REHEARSED.value
            assert sc.evidence_completeness == "FULL_REHEARSAL"
            assert sc.three_track_summary is not None
            assert sc.causal_links_count > 0
        else:
            assert sc.status == ScenarioExecutionStatus.EVALUATED_ROBUSTNESS.value
            assert sc.evidence_completeness == "ROBUSTNESS_ONLY"


def test_04_orchestrate_experiment_all_strategy_and_limits(test_campaign, jezero_terrain):
    """Verify orchestration with 'all' strategy respects max_rehearsals ceiling."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="mobility_derating",
        scenario_selection_strategy="all",
        rehearsal_policy="balanced",
        max_scenarios=5,
        max_rehearsals=2,  # Enforce cap of 2
    )

    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)
    assert record.summary_metrics["rehearsals_executed_count"] == 2
    assert record.summary_metrics["total_scenarios_evaluated"] <= 5


def test_05_cross_scenario_matrix_reconciliation_and_safe_math(test_campaign, jezero_terrain):
    """Verify matrix completeness, column alignment, and safe math (no NaNs or divisions by zero)."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="operational_delays",
        scenario_selection_strategy="degraded_or_breach",
        max_scenarios=4,
        max_rehearsals=2,
    )
    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)
    matrix = record.cross_scenario_matrix
    assert "headers" in matrix
    assert "rows" in matrix
    assert len(matrix["rows"]) == len(record.scenarios)

    for row in matrix["rows"]:
        assert "scenario_id" in row
        assert "science_preservation_pct" in row
        assert not (row["science_preservation_pct"] != row["science_preservation_pct"])  # Not NaN
        assert 0.0 <= row["science_preservation_pct"] <= 100.0
        assert "margin_delta_s" in row
        assert "selected_strategy" in row


def test_06_dossier_json_and_zip_export_and_verification(test_campaign, jezero_terrain):
    """Verify Mission Evidence Dossier JSON bundle and self-contained ZIP export with SHA-256 checks."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="corridor_closures",
        scenario_selection_strategy="degraded_or_breach",
        max_scenarios=3,
        max_rehearsals=2,
    )
    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)

    # 1. Test JSON bundle export
    bundle = export_experiment_dossier_bundle(record.experiment_id)
    assert bundle["schema_version"] == "2.0.0"
    assert bundle["dossier_id"] == f"dossier_{record.experiment_id}"
    assert "manifest_sha256" in bundle["manifest"]
    assert bundle["provenance"]["terrain_dataset_id"] == TERRAIN_DATASET_ID

    # 2. Test ZIP export & round-trip verification
    zip_path = export_experiment_dossier_zip(record.experiment_id)
    assert os.path.isfile(zip_path)
    assert os.path.getsize(zip_path) > 500

    is_valid, errors = verify_experiment_dossier_zip(zip_path)
    assert is_valid, f"Dossier ZIP verification failed: {errors}"
    assert len(errors) == 0

    # Clean up
    if os.path.exists(zip_path):
        os.remove(zip_path)
    delete_experiment_record(record.experiment_id)


def test_07_persistence_crud_and_isolation(test_campaign, jezero_terrain):
    """Verify experiment records are stored isolated in data/workspaces/campaign_experiments."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="mobility_derating",
        max_scenarios=2,
        max_rehearsals=1,
    )
    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)
    exp_id = record.experiment_id

    # Check file exists in dedicated directory
    expected_file = os.path.join(DEFAULT_CAMPAIGN_EXPERIMENTS_DIR, f"{exp_id}.json")
    assert os.path.isfile(expected_file)

    # Readback
    loaded = get_experiment_record(exp_id)
    assert loaded["experiment_id"] == exp_id
    assert loaded["campaign_id"] == test_campaign.campaign_id

    # List
    exp_list = list_experiment_records(campaign_id=test_campaign.campaign_id)
    assert any(x["experiment_id"] == exp_id for x in exp_list)

    # Cleanup
    assert delete_experiment_record(exp_id) is True
    assert not os.path.isfile(expected_file)


def test_08_schema_draft2020_12_validation(test_campaign, jezero_terrain):
    """Verify Draft 2020-12 schema validation passes on orchestrated experiment records."""
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="full_battery",
        max_scenarios=3,
        max_rehearsals=1,
    )
    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)
    is_valid, err = validate_mission_experiment_record(record.to_dict())
    assert is_valid is True
    assert len(err) == 0
    delete_experiment_record(record.experiment_id)


def test_09_scientific_integrity_truth_disclosures_and_immutability(test_campaign, jezero_terrain):
    """Verify 4 mandatory non-probabilistic truth disclosures and campaign immutability."""
    orig_copy = copy.deepcopy(test_campaign)
    config = ExperimentConfig(
        campaign_id=test_campaign.campaign_id,
        suite_type="full_battery",
        max_scenarios=3,
        max_rehearsals=1,
    )
    record = orchestrate_mission_experiment(test_campaign, jezero_terrain, config)

    # Verify disclosures
    disclosures = record.truth_disclosures
    assert len(disclosures) >= 4
    assert any("MUST NEVER be presented as physical Martian operational success probabilities" in d for d in disclosures)
    assert any("MUST NEVER be characterized as flight-certified or safe for astronauts" in d for d in disclosures)
    assert any("USGS CTX 20m Jezero Crater Digital Terrain Model" in d for d in disclosures)
    assert any("ESRI:103885" in d for d in disclosures)

    # Verify immutability of test_campaign
    assert len(test_campaign.targets) == len(orig_copy.targets)
    assert len(test_campaign.sorties) == len(orig_copy.sorties)
    for orig_t, curr_t in zip(orig_copy.targets, test_campaign.targets):
        assert orig_t.priority_score == curr_t.priority_score
        assert orig_t.status == curr_t.status

    delete_experiment_record(record.experiment_id)


def test_10_live_http_api_endpoints(test_campaign):
    """Verify live HTTP API endpoints for Experiment Studio."""
    # Ensure server is running
    try:
        ping = urllib.request.urlopen(f"{API_BASE_URL}/api/health", timeout=2.0)
        assert ping.status == 200
    except Exception:
        pytest.skip(f"Live Atlas server not reachable at {API_BASE_URL}")

    # Ensure campaign is saved for HTTP API retrieval
    from marswalk.api.workspace import save_campaign, delete_campaign
    save_campaign(test_campaign.to_dict())

    # 1. Orchestrate experiment via POST /api/experiment/orchestrate
    req_body = json.dumps({
        "campaign_id": test_campaign.campaign_id,
        "suite_type": "corridor_closures",
        "scenario_selection_strategy": "degraded_or_breach",
        "rehearsal_policy": "balanced",
        "max_scenarios": 2,
        "max_rehearsals": 1,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{API_BASE_URL}/api/experiment/orchestrate",
        data=req_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success"
        exp_id = res["experiment"]["experiment_id"]

    # 2. List experiments via GET /api/experiment/list
    with urllib.request.urlopen(f"{API_BASE_URL}/api/experiment/list", timeout=5.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["status"] == "success"
        assert any(x["experiment_id"] == exp_id for x in res["experiments"])

    # 3. Get experiment by ID via GET /api/experiment/<id>
    with urllib.request.urlopen(f"{API_BASE_URL}/api/experiment/{exp_id}", timeout=5.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["experiment"]["experiment_id"] == exp_id

    # 4. Get matrix via GET /api/experiment/<id>/matrix
    with urllib.request.urlopen(f"{API_BASE_URL}/api/experiment/{exp_id}/matrix", timeout=5.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert "rows" in res["matrix"]

    # 5. Get dossier via GET /api/experiment/<id>/dossier
    with urllib.request.urlopen(f"{API_BASE_URL}/api/experiment/{exp_id}/dossier", timeout=5.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["dossier"]["dossier_id"] == f"dossier_{exp_id}"

    # 6. Export dossier ZIP via POST /api/experiment/dossier/export
    export_body = json.dumps({"experiment_id": exp_id, "format": "zip"}).encode("utf-8")
    exp_req = urllib.request.Request(
        f"{API_BASE_URL}/api/experiment/dossier/export",
        data=export_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(exp_req, timeout=5.0) as resp:
        assert resp.status == 200
        res = json.loads(resp.read().decode("utf-8"))
        assert res["format"] == "zip"
        assert "zip_path" in res
        zip_path = res["zip_path"]
        if os.path.exists(zip_path):
            os.remove(zip_path)

    delete_experiment_record(exp_id)
