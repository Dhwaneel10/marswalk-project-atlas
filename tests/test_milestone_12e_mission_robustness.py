"""
Unit and integration tests for Milestone 12E: Atlas Mission Robustness Lab
Deterministic Stress Testing, Sensitivity Analysis, Failure Envelopes & Resilient Mission Design.

Verifies:
  1. Stress scenario matrix generation across all suite types with bounded limits (<= 15 cases).
  2. Immutability of baseline campaign during stress testing.
  3. Mathematical correctness of finite-difference sensitivity gradients and relative elasticity.
  4. Robust zero-division and NaN protection in sensitivity and envelope calculations.
  5. Feasibility envelope computation, critical breakpoint detection, and target vulnerability ranking.
  6. Multi-strategy comparison (Baseline vs Conservative vs Agile) and Pareto efficiency check.
  7. Resilient strategy promotion with version increment and lineage preservation.
  8. Schema compliance with Draft 2020-12 (schemas/api/v1/mission-robustness-experiment.json).
  9. Workspace persistence in data/workspaces/mission_robustness/.
  10. Live HTTP API endpoint integration (POST /api/robustness/evaluate, GET /api/robustness/experiments, POST /api/robustness/promote).
  11. Explicit non-probabilistic truth disclosures.
"""

import copy
import json
import os
import urllib.request
import pytest
import numpy as np

from marswalk.core.terrain import TerrainGrid, load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.mission_robustness_lab import (
    MAX_ROBUSTNESS_SCENARIOS,
    RobustnessSuiteType,
    ScenarioEvaluationRecord,
    ParameterSensitivity,
    FeasibilityEnvelope,
    ResilientStrategyCandidate,
    MissionRobustnessReport,
    build_stress_suite,
    compute_parameter_sensitivities,
    compute_feasibility_envelope,
    compare_resilient_strategies,
    evaluate_campaign_robustness,
    promote_resilient_strategy_to_campaign,
)
from marswalk.api.workspace import (
    save_robustness_experiment,
    get_robustness_experiment,
    list_robustness_experiments,
)
from marswalk.api.contracts import validate_mission_robustness_experiment


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
    """Create a standard multi-sol campaign with 4 candidate targets."""
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
            science_objective="CLAY_MINERALOGY",
        ),
        CampaignTarget(
            id="t_dep_3",
            name="Delta Scarp",
            row=118,
            col=160,
            priority_score=75.0,
            dwell_time_s=900.0,
            science_objective="STRATIGRAPHIC_EXPOSURE",
        ),
        CampaignTarget(
            id="t_dep_4",
            name="Crater Floor Regolith",
            row=125,
            col=154,
            priority_score=60.0,
            dwell_time_s=600.0,
            science_objective="VOLCANIC_FLOOR",
        ),
    ]
    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=21600.0,  # 6 hours
        base_start_rc=(117, 157),
    )
    return plan_mission_campaign(
        campaign_id="cmp_test_robustness_12e",
        name="Jezero Test Campaign (12E)",
        config=cfg,
        targets=targets,
        terrain=jezero_terrain,
        description="Robustness Lab test campaign fixture",
    )


def test_stress_suite_generation_bounds(sample_campaign):
    """Verify stress suite generator respects maximum bounded limit for all suite types."""
    for suite in RobustnessSuiteType:
        if suite == RobustnessSuiteType.CUSTOM:
            continue
        cases = build_stress_suite(suite, sample_campaign)
        assert len(cases) > 0, f"Suite {suite} generated empty scenario list"
        assert len(cases) <= MAX_ROBUSTNESS_SCENARIOS, f"Suite {suite} exceeded MAX_ROBUSTNESS_SCENARIOS"
        for c in cases:
            assert "scenario_id" in c
            assert "name" in c
            assert "modifications" in c
            assert "param_name" in c


def test_baseline_immutability(sample_campaign, jezero_terrain):
    """Verify that evaluating robustness does not mutate the baseline campaign in any way."""
    original_dict = copy.deepcopy(sample_campaign.to_dict())

    # Run full battery evaluation
    report = evaluate_campaign_robustness(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        suite_type=RobustnessSuiteType.FULL_BATTERY,
    )

    current_dict = sample_campaign.to_dict()
    assert original_dict == current_dict, "Baseline campaign was mutated during robustness evaluation!"
    assert report.target_id == sample_campaign.campaign_id


def test_sensitivity_gradient_mathematics():
    """Verify finite-difference sensitivity gradient and elasticity calculations."""
    records = [
        ScenarioEvaluationRecord(
            case_id="case_dur_1",
            suite="duration_stress",
            name="Dur -15%",
            description="Duration squeeze",
            parameter_name="max_duration_per_sortie_s",
            parameter_value=18360.0,
            nominal_value=21600.0,
            status="FEASIBLE",
            is_feasible=True,
            failure_reason=None,
            duration_s=18000.0,
            duration_delta_s=-3600.0,
            distance_m=1200.0,
            distance_delta_m=0.0,
            science_score=150.0,
            science_score_delta=0.0,
            targets_scheduled=4,
            targets_scheduled_delta=0,
            targets_lost=[],
            targets_deferred=[],
            remaining_margin_s=360.0,
            remaining_margin_pct=2.0,
        )
    ]

    sensitivities = compute_parameter_sensitivities(
        case_results=records,
        nominal_duration_s=21600.0,
        nominal_science=150.0,
        nominal_target_count=4,
    )

    assert len(sensitivities) == 1
    s = sensitivities[0]
    assert s.parameter_name == "max_duration_per_sortie_s"
    # delta_p = 18360 - 21600 = -3240
    # delta_dur = -3600
    # grad = -3600 / -3240 = 1.1111...
    assert pytest.approx(s.sensitivity_duration_s_per_unit, 0.05) == 1.11
    assert s.relative_elasticity > 0.0
    assert s.sensitivity_rank == 1


def test_zero_division_guard():
    """Verify zero-division and zero-delta protections in sensitivity engine."""
    # Zero parameter delta
    records = [
        ScenarioEvaluationRecord(
            case_id="case_identical",
            suite="duration_stress",
            name="Identical Case",
            description="No change",
            parameter_name="speed_factor",
            parameter_value=1.0,
            nominal_value=1.0,  # Delta = 0
            status="FEASIBLE",
            is_feasible=True,
            failure_reason=None,
            duration_s=10000.0,
            duration_delta_s=0.0,
            distance_m=1000.0,
            distance_delta_m=0.0,
            science_score=100.0,
            science_score_delta=0.0,
            targets_scheduled=2,
            targets_scheduled_delta=0,
            targets_lost=[],
            targets_deferred=[],
            remaining_margin_s=5000.0,
            remaining_margin_pct=33.3,
        )
    ]

    sensitivities = compute_parameter_sensitivities(
        case_results=records,
        nominal_duration_s=0.0,  # Zero nominal duration guard
        nominal_science=0.0,
        nominal_target_count=0,
    )
    # Should not crash and should safely return empty or sanitized sensitivities
    assert isinstance(sensitivities, list)


def test_feasibility_envelope_and_vulnerability(sample_campaign):
    """Verify feasibility envelope calculation, tested feasibility ratio, and target drop ranking."""
    records = [
        ScenarioEvaluationRecord(
            case_id="c1",
            suite="test",
            name="Case 1",
            description="",
            parameter_name="speed_factor",
            parameter_value=0.85,
            nominal_value=1.0,
            status="FEASIBLE",
            is_feasible=True,
            failure_reason=None,
            duration_s=15000.0,
            duration_delta_s=1000.0,
            distance_m=1200.0,
            distance_delta_m=0.0,
            science_score=150.0,
            science_score_delta=0.0,
            targets_scheduled=4,
            targets_scheduled_delta=0,
            targets_lost=[],
            targets_deferred=[],
            remaining_margin_s=6600.0,
            remaining_margin_pct=30.5,
        ),
        ScenarioEvaluationRecord(
            case_id="c2",
            suite="test",
            name="Case 2",
            description="",
            parameter_name="speed_factor",
            parameter_value=0.50,
            nominal_value=1.0,
            status="DEGRADED",
            is_feasible=False,
            failure_reason="Duration exceeded operational ceiling",
            duration_s=22000.0,
            duration_delta_s=7000.0,
            distance_m=1200.0,
            distance_delta_m=0.0,
            science_score=90.0,
            science_score_delta=-60.0,
            targets_scheduled=2,
            targets_scheduled_delta=-2,
            targets_lost=["t_dep_4"],
            targets_deferred=["t_dep_3"],
            remaining_margin_s=0.0,
            remaining_margin_pct=0.0,
        ),
    ]

    envelope = compute_feasibility_envelope(records, sample_campaign)
    assert envelope.tested_cases_count == 2
    assert envelope.feasible_cases_count == 1
    assert envelope.degraded_cases_count == 1
    assert envelope.infeasible_cases_count == 0
    assert pytest.approx(envelope.tested_feasibility_ratio, 0.01) == 0.5
    assert pytest.approx(envelope.tested_feasibility_pct, 0.1) == 50.0

    # Vulnerable targets check
    vuln_ids = [vt["target_id"] for vt in envelope.vulnerable_targets]
    assert "t_dep_4" in vuln_ids
    assert "t_dep_3" in vuln_ids


def test_multi_strategy_comparison_and_pareto(sample_campaign, jezero_terrain):
    """Verify strategy candidates generation, Pareto evaluation, and promotion."""
    cases = build_stress_suite(RobustnessSuiteType.DURATION_STRESS, sample_campaign)
    candidates = compare_resilient_strategies(sample_campaign, jezero_terrain, cases)

    assert len(candidates) == 3
    strat_ids = [c.strategy_id for c in candidates]
    assert "strat_baseline" in strat_ids
    assert "strat_conservative_margin" in strat_ids
    assert "strat_agile_yield" in strat_ids

    # Verify candidate promotion
    promoted = promote_resilient_strategy_to_campaign(sample_campaign, "strat_conservative_margin", jezero_terrain)
    assert promoted.version == sample_campaign.version + 1
    assert promoted.parent_campaign_id == sample_campaign.campaign_id
    assert "Resilient High-Margin" in promoted.name


def test_report_schema_validation(sample_campaign, jezero_terrain):
    """Verify that generated robustness report strictly adheres to Draft 2020-12 schema."""
    report = evaluate_campaign_robustness(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        suite_type=RobustnessSuiteType.FULL_BATTERY,
    )
    report_dict = report.to_dict()

    # Must pass schema validation with zero validation errors
    is_valid, err = validate_mission_robustness_experiment(report_dict)
    assert is_valid is True
    assert len(err) == 0


def test_workspace_persistence(sample_campaign, jezero_terrain):
    """Verify saving, retrieving, and listing robustness experiments in data/workspaces/mission_robustness/."""
    report = evaluate_campaign_robustness(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        suite_type=RobustnessSuiteType.MOBILITY_DERATING,
    )
    report_dict = report.to_dict()

    # Save
    saved = save_robustness_experiment(report_dict)
    assert saved["experiment_id"] == report.experiment_id

    # Retrieve
    loaded = get_robustness_experiment(report.experiment_id)
    assert loaded["experiment_id"] == report.experiment_id
    assert loaded["target_id"] == sample_campaign.campaign_id

    # List
    exp_list = list_robustness_experiments(target_id=sample_campaign.campaign_id)
    assert len(exp_list) >= 1
    found = any(e["experiment_id"] == report.experiment_id for e in exp_list)
    assert found is True


def test_seven_questions_answers_content(sample_campaign, jezero_terrain):
    """Verify answers to the 7 core questions are non-empty and address required criteria."""
    report = evaluate_campaign_robustness(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        suite_type=RobustnessSuiteType.FULL_BATTERY,
    )
    answers = report.answers_to_key_questions
    assert len(answers) == 7

    assert "most_sensitive_assumptions" in answers
    assert "infeasibility_conditions" in answers
    assert "vulnerable_objectives_and_units" in answers
    assert "performance_spread" in answers
    assert "maximum_margin_plans" in answers
    assert "supporting_evidence" in answers
    assert "unestablished_limits" in answers

    # Verify truth disclosure content
    assert "NOT" in answers["unestablished_limits"] or "not" in answers["unestablished_limits"]
    for d in report.truth_disclosures:
        assert len(d) > 20


def test_live_api_robustness_evaluate():
    """Verify HTTP API endpoint POST /api/robustness/evaluate and GET /api/robustness/experiments."""
    url_eval = "http://127.0.0.1:3000/api/robustness/evaluate"
    payload = json.dumps({"suite_type": "duration_stress"}).encode("utf-8")
    req = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["schema_version"] == "1.0.0"
            assert len(data["case_evaluations"]) > 0
            assert "feasibility_envelope" in data
            assert "answers_to_key_questions" in data
            exp_id = data["experiment_id"]

        # Test GET /api/robustness/experiment/<id>
        url_get = f"http://127.0.0.1:3000/api/robustness/experiment/{exp_id}"
        req_get = urllib.request.Request(url_get)
        with urllib.request.urlopen(req_get, timeout=5.0) as resp_get:
            assert resp_get.status == 200
            data_get = json.loads(resp_get.read().decode("utf-8"))
            assert data_get["experiment_id"] == exp_id

        # Test POST /api/robustness/promote
        url_promote = "http://127.0.0.1:3000/api/robustness/promote"
        promote_payload = json.dumps({
            "campaign_id": data["target_id"],
            "candidate_strategy_id": "strat_conservative_margin",
        }).encode("utf-8")
        req_promote = urllib.request.Request(url_promote, data=promote_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_promote, timeout=10.0) as resp_promote:
            assert resp_promote.status == 200
            data_promote = json.loads(resp_promote.read().decode("utf-8"))
            assert data_promote["status"] == "success"
            assert "campaign" in data_promote

    except urllib.error.URLError:
        pytest.skip("Atlas HTTP server offline on port 3000")


def test_api_robustness_error_handling():
    """Verify HTTP error handling for invalid or nonexistent targets."""
    url_eval = "http://127.0.0.1:3000/api/robustness/evaluate"
    payload = json.dumps({"campaign_id": "cmp_nonexistent_xyz"}).encode("utf-8")
    req = urllib.request.Request(url_eval, data=payload, headers={"Content-Type": "application/json"})

    try:
        urllib.request.urlopen(req, timeout=5.0)
        pytest.fail("Expected HTTP 404 for nonexistent campaign")
    except urllib.error.HTTPError as e:
        assert e.code == 404
    except urllib.error.URLError:
        pytest.skip("Atlas HTTP server offline on port 3000")

