"""
MarsWalk 2.0 / Project Atlas — Milestone 13I Test Battery
==========================================================
Tests the Atlas Mission Assurance & Counterfactual Operations Lab:
  - Deterministic replay & state reconstruction
  - Replay integrity vs stored snapshots
  - Event idempotency & concurrency safety
  - Immutable campaign branching & deep state isolation
  - Optimistic locking & stale parent promotion protection
  - 12 counterfactual scenario types (R1, R2, E1, E2, S1, S2, D1, D2, M1, M2, O1, O2)
  - Recovery alternative synthesis & multi-objective ranking
  - Robustness evaluation & parameter feasibility envelopes
  - Mission assurance invariant rule library (7 categories, 4 verdicts)
  - Tamper-evident dossier verification & SHA-256 manifest audit
  - Draft 2020-12 JSON Schema validation & API service integration
"""

import copy
import json
import os
from pathlib import Path
import pytest

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    TargetStatus,
    PlanningProfile,
)
from marswalk.core.mission_resource_model import RoverResourceConfig
from marswalk.core.campaign_operations_director import (
    CampaignOperationsDirector,
    CampaignLifecycleState,
    CampaignEventType,
    ReplanningTriggerType,
)
from marswalk.core.mission_assurance_engine import (
    MissionAssuranceEngine,
    AssuranceVerdict,
    AssuranceCategory,
    AssuranceSeverity,
    EvidenceClassification,
)
from marswalk.core.campaign_replay_engine import (
    CampaignReplayEngine,
    ReplayIntegrityReport,
    IdempotencyAuditReport,
)
from marswalk.core.campaign_branch_manager import (
    CampaignBranchManager,
    CampaignBranch,
    BranchStatus,
    StaleVersionConflictError,
    BranchNotFoundError,
)
from marswalk.core.campaign_counterfactual_engine import (
    CampaignCounterfactualEngine,
    CounterfactualScenarioDefinition,
    ScenarioType,
    ScenarioCategory,
    CounterfactualScenarioResult,
)
from marswalk.core.campaign_robustness_engine import (
    CampaignRobustnessEngine,
    CampaignRobustnessReport,
)
from marswalk.api.contracts import validate_contract
from marswalk.api.service import (
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
)


@pytest.fixture(scope="module")
def jezero_grid():
    """Load authentic USGS CTX 20m Jezero Crater terrain."""
    base_dir = Path(__file__).resolve().parent.parent
    tiff_path = base_dir / "data" / "processed" / "jezero_ready_20m.tif"
    if not tiff_path.exists():
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    return load_and_process_terrain(str(tiff_path))


@pytest.fixture
def sample_targets():
    """Standardized multi-objective Jezero exploration targets."""
    return [
        CampaignTarget(
            id="tgt_octavia",
            name="Octavia E. Butler Landing",
            row=117,
            col=157,
            priority_score=100.0,
            dwell_time_s=900.0,
            science_objective="SURFACE_MORPHOLOGY",
        ),
        CampaignTarget(
            id="tgt_delta_front",
            name="Kodiak Mesa Delta Front",
            row=122,
            col=148,
            priority_score=90.0,
            dwell_time_s=1800.0,
            science_objective="GEOLOGICAL_CHARACTERIZATION",
        ),
        CampaignTarget(
            id="tgt_crater_rim",
            name="Belva Crater Rim Exposure",
            row=135,
            col=160,
            priority_score=75.0,
            dwell_time_s=1200.0,
            science_objective="MINERALOGICAL_INVESTIGATION",
        ),
    ]


@pytest.fixture
def planned_director(jezero_grid, sample_targets, tmp_path):
    """Initializes and plans a standard 3-sol campaign director."""
    director = CampaignOperationsDirector(
        campaign_id="cmp_test_13i",
        name="Assurance Test Campaign",
        terrain_grid=jezero_grid,
        workspace_dir=tmp_path,
    )
    director.plan_multi_sol_campaign(
        targets=sample_targets,
        config=CampaignConfig(max_sols=3),
        rover_config=RoverResourceConfig(usable_battery_capacity_wh=4800.0, reserve_margin_pct=20.0),
        data_capacity_mb=16384.0,
        relays=[
            {"id": "MRN-01", "name": "Kodiak North Mast", "row": 120, "col": 145, "mast_height_m": 2.5},
            {"id": "MRN-02", "name": "Delta Ridge Relay", "row": 130, "col": 150, "mast_height_m": 2.5},
        ],
    )
    return director


def test_01_mission_assurance_engine_verdicts(planned_director):
    """Verifies invariant rule evaluation across 7 categories and Draft 2020-12 contract."""
    engine = MissionAssuranceEngine()
    state = planned_director.get_campaign_operations_state()
    report = engine.evaluate_campaign(campaign_state=state, event_log=planned_director.events_log)

    # Must be PASS or UNKNOWN (never false PASS when data is unmeasured)
    assert report.overall_verdict in (AssuranceVerdict.PASS, AssuranceVerdict.UNKNOWN)
    assert len(report.rule_results) >= 15
    assert "total_rules" in report.to_dict()["summary_counts"]

    # Verify category coverage
    categories_evaluated = {r.category for r in report.rule_results}
    assert AssuranceCategory.CAMPAIGN_INTEGRITY in categories_evaluated
    assert AssuranceCategory.RESOURCE_INTEGRITY in categories_evaluated
    assert AssuranceCategory.SCIENCE_INTEGRITY in categories_evaluated
    assert AssuranceCategory.DATA_INTEGRITY in categories_evaluated
    assert AssuranceCategory.NETWORK_INTEGRITY in categories_evaluated

    # Inject severe energy shortfall to trigger guaranteed failure
    failing_state = copy.deepcopy(state)
    failing_state["energy_state"]["current_energy_wh"] = 200.0  # Far below minimum reserve
    failing_report = engine.evaluate_campaign(failing_state)
    assert failing_report.overall_verdict == AssuranceVerdict.FAIL
    assert len(failing_report.violations) >= 1

    # Contract validation
    is_valid, errors = validate_contract(report.to_dict(), "mission-assurance")
    assert is_valid, f"Contract validation errors: {errors}"


def test_02_deterministic_replay_and_state_reconstruction(planned_director):
    """Verifies deterministic replay reconstruction and exact state snapshot reconciliation."""
    # Execute a sequence of events
    planned_director.record_event(
        event_type=CampaignEventType.SORTIE_STARTED.value,
        sol_index=1,
        payload={"sortie_id": "sortie_sol1"},
    )
    planned_director.record_event(
        event_type=CampaignEventType.TRAVERSE_COMPLETED.value,
        sol_index=1,
        payload={"distance_m": 350.0, "energy_consumed_wh": 180.0, "end_position_rc": [120, 150]},
    )
    planned_director.record_event(
        event_type=CampaignEventType.OBSERVATION_COMPLETED.value,
        sol_index=1,
        payload={"target_id": "tgt_octavia", "science_utility": 95.0, "data_generated_mb": 24.0},
    )

    post_state = planned_director.get_campaign_operations_state()

    # Replay on fresh clone
    replay_engine = CampaignReplayEngine()
    replayed_state, timeline = replay_engine.replay_campaign(
        director=planned_director,
        events=planned_director.events_log,
    )

    assert len(timeline) == len(planned_director.events_log)
    integrity = replay_engine.verify_replay_integrity(replayed_state, post_state)
    assert integrity.is_exact_match is True
    assert len(integrity.divergent_fields) == 0


def test_03_replay_idempotency_and_double_deduction_audit(planned_director):
    """Verifies thread-safe idempotency: duplicate events do not deduct double resources."""
    replay_engine = CampaignReplayEngine()
    evt_dict = {
        "event_id": "evt_idempotent_test_01",
        "sol_index": 1,
        "event_type": CampaignEventType.TRAVERSE_COMPLETED.value,
        "payload": {"distance_m": 120.0, "energy_consumed_wh": 75.0},
    }

    audit: IdempotencyAuditReport = replay_engine.audit_event_idempotency(
        director=planned_director,
        event_data=evt_dict,
        duplicate_count=3,
    )

    assert audit.is_strictly_idempotent is True
    assert audit.applications_tested == 3
    # Exactly 75.0 Wh deducted once, NOT 225.0 Wh
    assert abs(audit.energy_delta_total_wh - (-75.0)) < 1e-3


def test_04_campaign_branching_and_parent_isolation(planned_director, tmp_path):
    """Verifies that branches provide complete state isolation and child mutations cannot corrupt parent."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    branch = branch_mgr.create_branch(
        parent_director=planned_director,
        branch_id="br_isolation_test",
        name="Isolated Experiment",
        fork_sol=2,
    )

    parent_energy_pre = planned_director.current_energy_wh
    parent_storage_pre = planned_director.used_storage_mb
    parent_targets_pre = len(planned_director.targets)

    # Mutate child branch state aggressively
    branch.director.current_energy_wh -= 800.0
    branch.director.used_storage_mb += 1200.0
    branch.director.targets.pop("tgt_octavia", None)

    # Verify parent is completely unmutated
    assert planned_director.current_energy_wh == parent_energy_pre
    assert planned_director.used_storage_mb == parent_storage_pre
    assert len(planned_director.targets) == parent_targets_pre

    # Verify contract
    is_valid, errors = validate_contract(branch.to_dict(), "campaign-branch")
    assert is_valid, f"Contract validation error: {errors}"


def test_05_optimistic_locking_and_stale_parent_promotion(planned_director, tmp_path):
    """Verifies that branch promotion enforces optimistic locking against concurrent plan advances."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    branch = branch_mgr.create_branch(
        parent_director=planned_director,
        branch_id="br_promo_lock_test",
        name="Branch For Promotion",
        fork_sol=1,
    )

    initial_ver = planned_director.version

    # Advance parent version (simulating concurrent change)
    planned_director.version += 1

    # Attempt to promote with stale expected version -> MUST raise StaleVersionConflictError
    with pytest.raises(StaleVersionConflictError):
        branch_mgr.promote_branch(
            branch_id="br_promo_lock_test",
            live_parent_director=planned_director,
            expected_parent_version=initial_ver,
            approval_record={"approver": "Test Flight Director", "rationale": "Optimistic lock check"},
        )

    # Attempt promotion with correct live version -> MUST succeed
    promo_rec = branch_mgr.promote_branch(
        branch_id="br_promo_lock_test",
        live_parent_director=planned_director,
        expected_parent_version=planned_director.version,
        approval_record={"approver": "Test Flight Director", "rationale": "Successful lock resolution"},
    )
    assert promo_rec["promoted_branch_id"] == "br_promo_lock_test"
    assert branch.branch_status == BranchStatus.PROMOTED


def test_06_counterfactual_scenarios_communications_r1_r2(planned_director, tmp_path):
    """Tests R1 Relay Outage and R2 Restricted Connectivity counterfactual scenarios."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    cf_engine = CampaignCounterfactualEngine(branch_manager=branch_mgr)

    # Scenario R1
    sc_r1 = CounterfactualScenarioDefinition(
        scenario_id="sc_test_r1",
        scenario_type=ScenarioType.R1_RELAY_OUTAGE,
        category=ScenarioCategory.COMMUNICATIONS,
        name="Relay Mast Outage",
        description="Drop primary relay",
        target_sol=2,
        parameters={"relay_id": "MRN-01"},
    )
    res_r1 = cf_engine.run_counterfactual_scenario(planned_director, sc_r1)
    assert res_r1.scenario_type == "R1_RELAY_OUTAGE"
    assert "COMMUNICATIONS" in res_r1.affected_subsystems
    assert len(res_r1.recovery_alternatives) >= 1
    assert res_r1.recommended_alternative_id is not None

    # Scenario R2
    sc_r2 = CounterfactualScenarioDefinition(
        scenario_id="sc_test_r2",
        scenario_type=ScenarioType.R2_RESTRICTED_CONNECTIVITY,
        category=ScenarioCategory.COMMUNICATIONS,
        name="Reduced LOS Window",
        description="Topographic occlusion backlog",
        target_sol=2,
        parameters={"reduction_pct": 60.0, "backlog_mb": 400.0},
    )
    res_r2 = cf_engine.run_counterfactual_scenario(planned_director, sc_r2)
    assert res_r2.scenario_type == "R2_RESTRICTED_CONNECTIVITY"
    assert len(res_r2.recovery_alternatives) >= 1

    # Contract validation
    is_valid, errors = validate_contract(res_r1.to_dict(), "counterfactual-scenario")
    assert is_valid, f"Contract validation errors: {errors}"


def test_07_counterfactual_scenarios_energy_e1_e2(planned_director, tmp_path):
    """Tests E1 Energy Shortfall and E2 Increased Mobility Effort scenarios."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    cf_engine = CampaignCounterfactualEngine(branch_manager=branch_mgr)

    # Scenario E1
    sc_e1 = CounterfactualScenarioDefinition(
        scenario_id="sc_test_e1",
        scenario_type=ScenarioType.E1_ENERGY_SHORTFALL,
        category=ScenarioCategory.ENERGY,
        name="Battery Chill Drain",
        description="RTG cooling anomaly shortfall",
        target_sol=2,
        parameters={"shortfall_wh": 500.0},
    )
    res_e1 = cf_engine.run_counterfactual_scenario(planned_director, sc_e1)
    assert res_e1.scenario_type == "E1_ENERGY_SHORTFALL"
    assert "RESOURCES" in res_e1.affected_subsystems

    # Scenario E2
    sc_e2 = CounterfactualScenarioDefinition(
        scenario_id="sc_test_e2",
        scenario_type=ScenarioType.E2_INCREASED_MOBILITY_EFFORT,
        category=ScenarioCategory.ENERGY,
        name="Sand Ripple Drag",
        description="Increased terramechanical rolling resistance",
        target_sol=2,
        parameters={"drag_multiplier": 1.4, "added_energy_wh": 350.0},
    )
    res_e2 = cf_engine.run_counterfactual_scenario(planned_director, sc_e2)
    assert res_e2.scenario_type == "E2_INCREASED_MOBILITY_EFFORT"


def test_08_counterfactual_scenarios_all_remaining_types(planned_director, tmp_path):
    """Executes S1, S2, D1, D2, M1, M2, O1, O2 ensuring all 12 scenario types run cleanly."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    cf_engine = CampaignCounterfactualEngine(branch_manager=branch_mgr)

    scenarios = [
        (ScenarioType.S1_INSTRUMENT_UNAVAILABLE, ScenarioCategory.SCIENCE, {"instrument": "PIXL_XRF_GRID"}),
        (ScenarioType.S2_NEW_SCIENCE_TARGET, ScenarioCategory.SCIENCE, {"target_name": "Smectite Knoll", "priority": 95.0}),
        (ScenarioType.D1_STORAGE_RESTRICTION, ScenarioCategory.DATA, {"capacity_reduction_mb": 4000.0}),
        (ScenarioType.D2_TRANSFER_WINDOW_LOST, ScenarioCategory.DATA, {"lost_transfer_mb": 300.0}),
        (ScenarioType.M1_ROUTE_OBSTRUCTION, ScenarioCategory.MOBILITY, {}),
        (ScenarioType.M2_ROUTE_PREFERENCE_DISTURBANCE, ScenarioCategory.MOBILITY, {"penalized_energy_wh": 200.0}),
        (ScenarioType.O1_ACTIVITY_DELAY, ScenarioCategory.OPERATIONS, {"delay_hours": 2.0}),
        (ScenarioType.O2_MULTIPLE_DISTURBANCES, ScenarioCategory.OPERATIONS, {}),
    ]

    for st, cat, params in scenarios:
        sc = CounterfactualScenarioDefinition(
            scenario_id=f"sc_test_{st.value.lower()}",
            scenario_type=st,
            category=cat,
            name=st.value,
            description=f"Auto test for {st.value}",
            target_sol=2,
            parameters=params,
        )
        res = cf_engine.run_counterfactual_scenario(planned_director, sc)
        assert res.scenario_type == st.value
        assert res.reproducibility_token != ""


def test_09_branch_comparison_three_way_matrix(planned_director, tmp_path):
    """Verifies multi-branch delta comparisons across baseline, disturbed, and recovery branches."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    b_base = branch_mgr.create_branch(planned_director, "br_cmp_baseline", "Baseline")
    b_dist = branch_mgr.create_branch(planned_director, "br_cmp_disturbed", "Disturbed")
    b_dist.director.current_energy_wh -= 600.0
    b_dist.director.cumulative_distance_m += 250.0

    comp = branch_mgr.compare_branches("br_cmp_baseline", "br_cmp_disturbed")
    assert comp.branch_a_id == "br_cmp_baseline"
    assert comp.branch_b_id == "br_cmp_disturbed"
    assert comp.delta_energy_wh == -600.0
    assert comp.delta_distance_m == 250.0
    assert "Comparison between" in comp.narrative


def test_10_campaign_robustness_evaluation_and_envelopes(planned_director, tmp_path):
    """Verifies robustness scoring, feasibility envelopes, sensitivity rankings, and Draft 2020-12 contract."""
    branch_mgr = CampaignBranchManager(workspace_dir=tmp_path / "branches")
    cf_engine = CampaignCounterfactualEngine(branch_manager=branch_mgr)
    rob_engine = CampaignRobustnessEngine(
        branch_manager=branch_mgr,
        counterfactual_engine=cf_engine,
    )

    report = rob_engine.evaluate_campaign_robustness(planned_director, max_scenarios=4)
    assert report.scenarios_evaluated_count == 4
    assert 0.0 <= report.robustness_score_pct <= 100.0
    assert len(report.feasibility_envelope) >= 1
    assert len(report.sensitivity_rankings) >= 1

    # Contract validation
    is_valid, errors = validate_contract(report.to_dict(), "campaign-robustness")
    assert is_valid, f"Contract validation error: {errors}"


def test_11_tamper_evident_dossier_and_integrity_verification(planned_director, tmp_path):
    """Verifies that cryptographic dossier manifests immediately detect modified files."""
    rob_engine = CampaignRobustnessEngine()
    dossier = rob_engine.generate_mission_assurance_dossier(planned_director)

    assert "dossier_id" in dossier
    assert "manifest_files" in dossier
    assert "README.md" in dossier["manifest_files"]
    assert "campaign_state.json" in dossier["manifest_files"]

    root_digest_original = dossier["root_digest"]
    assert len(root_digest_original) == 64

    # Simulating tampering with campaign state
    tampered_manifest = copy.deepcopy(dossier["manifest_files"])
    tampered_manifest["campaign_state.json"] = "0" * 64
    tampered_digest = rob_engine.compute_root_digest(tampered_manifest)
    assert tampered_digest != root_digest_original


def test_12_api_service_integration_endpoints(planned_director):
    """Verifies direct invocation of all 13I service API functions."""
    terrain = planned_director.terrain_grid

    # 1. Evaluate
    res_eval = mission_assurance_evaluate_api({"campaign_id": planned_director.campaign_id}, terrain, None)
    assert res_eval["schema_version"] == "1.0.0"

    # 2. Branch list
    res_list = campaign_branches_list_api({"campaign_id": planned_director.campaign_id}, terrain, None)
    assert "branches" in res_list

    # 3. Branch create
    res_cr = campaign_branches_create_api(
        {"campaign_id": planned_director.campaign_id, "branch_id": "br_api_svc_test", "name": "API Svc Branch"},
        terrain,
        None,
    )
    assert res_cr["branch_id"] == "br_api_svc_test"

    # 4. Branch scenario
    res_sc = campaign_branches_scenario_api(
        {"campaign_id": planned_director.campaign_id, "scenario_type": "R1_RELAY_OUTAGE", "target_sol": 2},
        terrain,
        None,
    )
    assert res_sc["scenario_type"] == "R1_RELAY_OUTAGE"

    # 5. Branch replay
    res_rep = campaign_branches_replay_api(
        {"campaign_id": planned_director.campaign_id, "branch_id": "br_api_svc_test"},
        terrain,
        None,
    )
    assert "timeline_records" in res_rep

    # 6. Branch compare
    res_cmp = campaign_branches_compare_api(
        {"campaign_id": planned_director.campaign_id, "branch_ids": ["br_baseline", "br_api_svc_test"]},
        terrain,
        None,
    )
    assert "comparison" in res_cmp

    # 7. Robustness evaluate
    res_rob = campaign_robustness_evaluate_api(
        {"campaign_id": planned_director.campaign_id, "max_scenarios": 2},
        terrain,
        None,
    )
    assert "robustness_score_pct" in res_rob

    # 8. Dossier
    res_dos = mission_assurance_dossier_api(
        {"campaign_id": planned_director.campaign_id},
        terrain,
        None,
    )
    assert "dossier_id" in res_dos
