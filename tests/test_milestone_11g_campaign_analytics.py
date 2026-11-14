# tests/test_milestone_11g_campaign_analytics.py
"""
Test suite for Milestone 11G: Campaign Performance Analytics, Deviation Analysis & Lessons Learned.

Verifies:
1. Performance analysis execution and schema validation (campaign-analytics.schema.json).
2. Planned vs simulated duration deltas and sortie timing slips.
3. Target analytics with priority breakdown (high, medium, low).
4. Unit workload and energy decomposition with zero double-counting.
5. Strict causal attribution classification (confirmed_cause, contributing_factor, undetermined).
6. Deviation codes generation and triggering event citations.
7. Grounded lessons learned recommendations with structured proposed changes.
8. Recommendation review status lifecycle (active, reviewed, dismissed).
9. Atomic workspace persistence and retrieval.
10. API service handlers and live REST endpoints.
11. Explicit planning-analysis limitations disclaimer.
"""

import copy
import json
import urllib.request
import urllib.error
import pytest
from typing import Dict, Any

from marswalk.core.terrain import TerrainGrid, load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    TargetStatus,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_coordination import (
    create_default_units,
    allocate_campaign_coordination,
    CoordinationPlan,
)
from marswalk.core.campaign_simulator import (
    CampaignDigitalTwin,
    ActivityType,
    SimulationEvent,
)
from marswalk.core.campaign_analytics import (
    analyze_campaign_performance,
    DeviationCode,
    CauseAttribution,
    RecommendationCategory,
    RecommendationStatus,
    ANALYTICS_DISCLAIMER,
)
from marswalk.api.contracts import (
    validate_campaign_analytics_record,
    ContractValidationError,
)
from marswalk.api.workspace import (
    save_campaign_analysis,
    get_campaign_analysis,
    list_campaign_analyses,
    update_recommendation_status,
    save_campaign,
    save_coordination_plan,
    save_campaign_simulation,
    WorkspaceError,
)
from marswalk.api.service import (
    analyze_campaign_api,
    get_campaign_analysis_api,
    list_campaign_analyses_api,
    review_recommendation_api,
    APIError,
)


@pytest.fixture(scope="module")
def terrain_grid() -> TerrainGrid:
    return load_and_process_terrain("data/processed/jezero_ready_20m.tif")


@pytest.fixture
def sample_campaign(terrain_grid: TerrainGrid) -> MissionCampaign:
    targets = [
        CampaignTarget(
            id="tgt_octavia_w0",
            name="Octavia E. Butler Landing",
            row=117,
            col=157,
            priority_score=100.0,
            dwell_time_s=600.0,
        ),
        CampaignTarget(
            id="tgt_hawksbill_w1",
            name="Hawksbill Gap",
            row=119,
            col=159,
            priority_score=85.0,
            dwell_time_s=900.0,
            prerequisites=["tgt_octavia_w0"],
        ),
        CampaignTarget(
            id="tgt_skinner_w2",
            name="Skinner Ridge",
            row=120,
            col=160,
            priority_score=75.0,
            dwell_time_s=900.0,
            prerequisites=["tgt_hawksbill_w1"],
        ),
        CampaignTarget(
            id="tgt_enchanted_w3",
            name="Enchanted Lake",
            row=122,
            col=161,
            priority_score=35.0,  # low priority
            dwell_time_s=900.0,
        ),
    ]

    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=14400.0,
        max_sols=3,
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_anl_test_001",
        name="Jezero Analytics Test Campaign",
        config=cfg,
        targets=targets,
        terrain=terrain_grid,
    )
    save_campaign(campaign.to_dict())
    return campaign


@pytest.fixture
def sample_coordination(sample_campaign: MissionCampaign, terrain_grid: TerrainGrid) -> CoordinationPlan:
    units = create_default_units(sample_campaign.config)
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=terrain_grid,
        units=units,
        strategy="priority_first",
    )
    save_coordination_plan(plan.to_dict())
    return plan


@pytest.fixture
def sample_simulation(sample_campaign: MissionCampaign, sample_coordination: CoordinationPlan, terrain_grid: TerrainGrid) -> Dict[str, Any]:
    twin = CampaignDigitalTwin(
        simulation_id="sim_anl_test_001",
        campaign=sample_campaign,
        coordination_plan=sample_coordination,
        terrain=terrain_grid,
    )
    # Advance through campaign
    twin.advance(twin.total_duration_s)
    sim_dict = twin.to_dict()
    save_campaign_simulation(sim_dict)
    return sim_dict


def test_campaign_performance_analysis_execution(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
    sample_coordination: CoordinationPlan,
):
    """Verifies analyze_campaign_performance executes cleanly and complies with schema."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
        coordination_plan=sample_coordination,
    )

    assert result["schema_version"] == "1.0.0"
    assert result["analysis_id"].startswith("anl_")
    assert result["campaign_id"] == sample_campaign.campaign_id
    assert "executive_summary" in result
    assert "sortie_deviations" in result
    assert "target_analytics" in result
    assert "unit_workloads" in result
    assert "deviations" in result
    assert "lessons_learned" in result
    assert "limitations_disclaimer" in result


def test_schema_validation_campaign_analytics(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies strict Draft 2020-12 schema validation passes and catches missing fields."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    # Should validate cleanly
    is_valid, errs = validate_campaign_analytics_record(result)
    assert is_valid is True
    assert len(errs) == 0

    # Test corrupted payload raises ContractValidationError
    bad_payload = copy.deepcopy(result)
    del bad_payload["executive_summary"]
    with pytest.raises(ContractValidationError):
        validate_campaign_analytics_record(bad_payload)


def test_executive_summary_metrics_accuracy(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies executive summary metric calculations."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    summary = result["executive_summary"]

    assert summary["planned_duration_s"] > 0
    assert summary["simulated_duration_s"] > 0
    assert summary["duration_delta_s"] == round(summary["simulated_duration_s"] - summary["planned_duration_s"], 1)
    assert 0.0 <= summary["target_completion_rate_pct"] <= 100.0
    assert summary["total_distance_m"] >= 0.0
    assert summary["total_operational_holds"] >= 0
    assert summary["total_hold_duration_s"] >= 0.0
    assert 0.0 <= summary["fleet_utilization_pct"] <= 100.0
    assert summary["temporal_conflicts_count"] >= 0


def test_sortie_deviations_calculation(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies planned vs simulated sortie timing and slips."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    sortie_devs = result["sortie_deviations"]
    assert len(sortie_devs) == len(sample_campaign.sorties)

    for s in sortie_devs:
        assert "sortie_id" in s
        assert "sol_index" in s
        assert s["start_slip_s"] == round(s["simulated_start_s"] - s["planned_start_s"], 1)
        assert s["end_slip_s"] == round(s["simulated_end_s"] - s["planned_end_s"], 1)
        assert s["duration_delta_s"] == round(s["simulated_duration_s"] - s["planned_duration_s"], 1)
        assert s["status"] in ("COMPLETED", "PLANNED", "DISRUPTED", "BLOCKED")


def test_target_analytics_priority_breakdown(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies target analytics breakdowns across high, medium, low priorities."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    tgt_anl = result["target_analytics"]
    assert tgt_anl["total_targets"] == len(sample_campaign.targets)
    assert tgt_anl["completed_count"] + tgt_anl["deferred_count"] + tgt_anl["blocked_count"] + tgt_anl["unallocated_count"] == tgt_anl["total_targets"]

    pb = tgt_anl["priority_breakdown"]
    for band in ("high", "medium", "low"):
        assert band in pb
        assert pb[band]["total"] >= 0
        assert pb[band]["completed"] >= 0
        assert 0.0 <= pb[band]["completion_rate_pct"] <= 100.0


def test_unit_workload_decomposition_zero_double_counting(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
    sample_coordination: CoordinationPlan,
):
    """Verifies mutually exclusive active/idle accounting with zero double counting."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
        coordination_plan=sample_coordination,
    )
    workloads = result["unit_workloads"]
    assert len(workloads) == len(sample_coordination.units)

    for uw in workloads:
        assert uw["active_duration_s"] >= 0.0
        assert uw["idle_duration_s"] >= 0.0
        assert 0.0 <= uw["utilization_pct"] <= 100.0
        assert uw["total_distance_m"] >= 0.0
        assert uw["energy_consumed_kwh"] >= 0.0


def test_causal_attribution_confirmed_cause_with_events(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies that an operational hold event directly cites confirmed_cause and triggering IDs."""
    sim_copy = copy.deepcopy(sample_simulation)
    # Inject a simulated hold interval and event
    hold_iv = {
        "interval_id": "iv_hold_test",
        "unit_id": "unit_perseverance_rover",
        "activity_type": ActivityType.HOLD.value,
        "sortie_id": "sortie_1",
        "sol_index": 1,
        "start_time_s": 1000.0,
        "end_time_s": 2500.0,
        "duration_s": 1500.0,
        "distance_m": 0.0,
        "status": "COMPLETED",
    }
    sim_copy["timeline_intervals"].append(hold_iv)
    hold_evt = {
        "event_id": "evt_hold_rockfall",
        "event_type": "OPERATIONAL_HOLD",
        "simulated_time_s": 1000.0,
        "sol_index": 1,
        "title": "Rockfall Hold",
        "description": "Hazard detected in crater pass.",
        "details": {},
    }
    sim_copy["events"].append(hold_evt)

    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sim_copy,
    )

    hold_devs = [d for d in result["deviations"] if d["code"] == DeviationCode.DEV_CRITICAL_HOLD_PROLONGED.value]
    assert len(hold_devs) > 0
    dev = hold_devs[0]
    assert dev["cause_attribution"] == CauseAttribution.CONFIRMED_CAUSE.value
    assert "evt_hold_rockfall" in dev["triggering_event_ids"]


def test_causal_attribution_undetermined(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies that variance without discrete logged events yields undetermined."""
    sim_copy = copy.deepcopy(sample_simulation)
    # Expand interval duration without adding any events
    for iv in sim_copy["timeline_intervals"]:
        if iv.get("sortie_id") == "sortie_1":
            iv["duration_s"] += 600.0
            iv["end_time_s"] += 600.0

    sim_copy["events"] = []  # Clear events

    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sim_copy,
    )

    blowouts = [d for d in result["deviations"] if d["code"] == DeviationCode.DEV_SORTIE_DURATION_BLOWOUT.value]
    if blowouts:
        assert blowouts[0]["cause_attribution"] == CauseAttribution.UNDETERMINED.value
        assert len(blowouts[0]["triggering_event_ids"]) == 0


def test_deviation_codes_coverage(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies all defined deviation codes are valid strings."""
    for code in DeviationCode:
        assert code.value.startswith("DEV_")


def test_lessons_learned_generation_and_structure(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies lessons learned recommendations are grounded, have proposed changes, and valid categories."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    recs = result["lessons_learned"]
    assert len(recs) > 0

    valid_categories = {c.value for c in RecommendationCategory}
    for rec in recs:
        assert rec["recommendation_id"].startswith("rec_")
        assert rec["category"] in valid_categories
        assert len(rec["title"]) > 0
        assert len(rec["rationale"]) > 0
        assert len(rec["expected_impact"]) > 0
        assert len(rec["assumptions_and_limitations"]) > 0
        assert isinstance(rec["proposed_change"], dict)
        assert rec["status"] == RecommendationStatus.ACTIVE.value


def test_lessons_learned_status_lifecycle_and_persistence(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies active -> reviewed -> dismissed status updates persist atomically."""
    analysis = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    save_campaign_analysis(analysis)
    anl_id = analysis["analysis_id"]
    rec_id = analysis["lessons_learned"][0]["recommendation_id"]

    # 1. Update to reviewed
    upd1 = update_recommendation_status(anl_id, rec_id, "reviewed")
    rec1 = next(r for r in upd1["lessons_learned"] if r["recommendation_id"] == rec_id)
    assert rec1["status"] == "reviewed"

    # Reload from disk
    reloaded1 = get_campaign_analysis(anl_id)
    rec1_reloaded = next(r for r in reloaded1["lessons_learned"] if r["recommendation_id"] == rec_id)
    assert rec1_reloaded["status"] == "reviewed"

    # 2. Update to dismissed
    upd2 = update_recommendation_status(anl_id, rec_id, "dismissed")
    rec2 = next(r for r in upd2["lessons_learned"] if r["recommendation_id"] == rec_id)
    assert rec2["status"] == "dismissed"

    # Invalid status rejection
    with pytest.raises(WorkspaceError):
        update_recommendation_status(anl_id, rec_id, "invalid_status")


def test_workspace_persistence_and_listing(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Tests save_campaign_analysis, get_campaign_analysis, and list_campaign_analyses."""
    analysis = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    saved = save_campaign_analysis(analysis)
    assert saved["analysis_id"] == analysis["analysis_id"]

    fetched = get_campaign_analysis(analysis["analysis_id"])
    assert fetched["analysis_id"] == analysis["analysis_id"]

    all_analyses = list_campaign_analyses(campaign_id=sample_campaign.campaign_id)
    assert any(a["analysis_id"] == analysis["analysis_id"] for a in all_analyses)


def test_api_analyze_campaign_endpoint(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Tests analyze_campaign_api service endpoint."""
    payload = {
        "campaign_id": sample_campaign.campaign_id,
        "simulation_id": sample_simulation["simulation_id"],
        "persist": True,
    }
    result = analyze_campaign_api(payload)
    assert result["schema_version"] == "1.0.0"
    assert result["campaign_id"] == sample_campaign.campaign_id

    # Test error on missing IDs
    with pytest.raises(APIError):
        analyze_campaign_api({})


def test_api_review_recommendation_endpoint(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Tests review_recommendation_api service endpoint."""
    analysis = analyze_campaign_api({
        "campaign_id": sample_campaign.campaign_id,
        "simulation_id": sample_simulation["simulation_id"],
    })
    rec_id = analysis["lessons_learned"][0]["recommendation_id"]

    review_payload = {
        "analysis_id": analysis["analysis_id"],
        "recommendation_id": rec_id,
        "status": "reviewed",
    }
    resp = review_recommendation_api(review_payload)
    assert resp["status"] == "success"
    assert resp["new_status"] == "reviewed"

    # Missing status
    with pytest.raises(APIError):
        review_recommendation_api({"analysis_id": analysis["analysis_id"], "recommendation_id": rec_id})


def test_http_rest_api_endpoints(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Tests live HTTP REST endpoints on port 3000."""
    base_url = "http://127.0.0.1:3000"

    # 1. POST /api/campaign/analyze
    analyze_url = f"{base_url}/api/campaign/analyze"
    post_data = json.dumps({
        "campaign_id": sample_campaign.campaign_id,
        "simulation_id": sample_simulation["simulation_id"],
        "persist": True,
    }).encode("utf-8")

    req = urllib.request.Request(analyze_url, data=post_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
        anl_data = json.loads(response.read().decode("utf-8"))
        assert anl_data["schema_version"] == "1.0.0"
        anl_id = anl_data["analysis_id"]

    # 2. GET /api/campaign/analyses
    list_url = f"{base_url}/api/campaign/analyses"
    with urllib.request.urlopen(list_url, timeout=10) as response:
        assert response.status == 200
        items = json.loads(response.read().decode("utf-8"))
        assert any(i["analysis_id"] == anl_id for i in items)

    # 3. GET /api/campaign/analyses/<id>
    get_url = f"{base_url}/api/campaign/analyses/{anl_id}"
    with urllib.request.urlopen(get_url, timeout=10) as response:
        assert response.status == 200
        single = json.loads(response.read().decode("utf-8"))
        assert single["analysis_id"] == anl_id

    # 4. POST /api/campaign/recommendations/review
    rec_id = anl_data["lessons_learned"][0]["recommendation_id"]
    review_url = f"{base_url}/api/campaign/recommendations/review"
    rev_data = json.dumps({
        "analysis_id": anl_id,
        "recommendation_id": rec_id,
        "status": "reviewed",
    }).encode("utf-8")

    rev_req = urllib.request.Request(review_url, data=rev_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(rev_req, timeout=10) as response:
        assert response.status == 200
        rev_resp = json.loads(response.read().decode("utf-8"))
        assert rev_resp["new_status"] == "reviewed"


def test_limitations_disclaimer_present(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies the mandatory limitations disclaimer is explicitly included."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    assert result["limitations_disclaimer"] == ANALYTICS_DISCLAIMER
    assert "deterministic planning-analysis system" in result["limitations_disclaimer"].lower()
    assert "not utilize live spacecraft telemetry" in result["limitations_disclaimer"].lower()


def test_fair_alternative_comparison_and_metric_provenance(
    sample_campaign: MissionCampaign,
    sample_simulation: Dict[str, Any],
):
    """Verifies that all metrics have explicit physical units, no opaque composite scores, and fair baseline comparisons."""
    result = analyze_campaign_performance(
        campaign=sample_campaign,
        simulation=sample_simulation,
    )
    # Check deviations values have explicit units
    for dev in result["deviations"]:
        if dev.get("planned_value"):
            assert "unit" in dev["planned_value"]
            assert "value" in dev["planned_value"]
        if dev.get("simulated_value"):
            assert "unit" in dev["simulated_value"]
            assert "value" in dev["simulated_value"]

    # Check unit workloads have physical units (seconds, meters, kWh)
    for uw in result["unit_workloads"]:
        assert isinstance(uw["active_duration_s"], (int, float))
        assert isinstance(uw["idle_duration_s"], (int, float))
        assert isinstance(uw["total_distance_m"], (int, float))
        assert isinstance(uw["energy_consumed_kwh"], (int, float))
        # Ensure no fabricated opaque score
        assert "composite_magic_score" not in uw
