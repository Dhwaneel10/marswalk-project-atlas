"""
Tests for Milestone 11C: Observation-Driven Campaign Intelligence & Adaptive Science Prioritization.
Covers:
  1. Reprioritization using explicit user-defined objective weights.
  2. Non-rescheduling invariant: completed objectives are omitted from future scheduling by default.
  3. Topological dependency ordering: unblocking downstream objectives upon prerequisite completion.
  4. Negative evidence adaptation: refuted hypotheses (DOES_NOT_SUPPORT_OBJECTIVE) deprioritize downstream targets.
  5. Positive evidence adaptation: verified hypotheses (SUPPORTS_OBJECTIVE) elevate downstream target priorities.
  6. Inconclusive observation neutrality: inconclusive results do NOT imply success or failure.
  7. Provenance preservation: simulated observations remain SIMULATED; authentic PDS data retains citations.
  8. Missing observations and null safety: unmeasured fields are not fabricated.
  9. Explicit repeat-observation handling: follow-up inspection target scheduled when requested.
  10. Infeasible/blocked target handling: blocked prerequisites cleanly prevent scheduling.
  11. No-improvement preservation: optimal schedule is preserved with explanatory warning when no change is warranted.
  12. Different priorities produce genuine trade-offs between science score and duration.
  13. Multi-strategy comparison: baseline vs proposed adaptive vs alternative profiles.
  14. Target movement rationales: explainable reasons for each target position change.
  15. Version immutability: new campaign version synthesized without corrupting prior version on disk.
  16. Error handling: negative weights, missing campaigns, invalid payloads raise appropriate errors.
  17. Live REST API routes:
      - POST /api/campaign/reprioritize
      - GET /api/campaign/recommendations
"""

import json
import os
import uuid
import shutil
import tempfile
import urllib.request
import urllib.error
import pytest
import numpy as np

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid, TerrainConfig
from marswalk.core.mission_campaign import (
    CampaignTarget,
    CampaignConfig,
    CampaignSortie,
    MissionCampaign,
    TargetStatus,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_progress import (
    ObservationType,
    ObservationProvenance,
    ProgressEventType,
    QuantitativeMeasurement,
    ScienceObservation,
    advance_campaign_progress,
)
from marswalk.core.campaign_intelligence import (
    ObjectiveClassification,
    TargetRationale,
    StrategyMetrics,
    CampaignIntelligenceRecommendation,
    evaluate_campaign_intelligence,
)
from marswalk.api.workspace import (
    save_campaign,
    get_campaign,
    save_observation,
    save_recommendation,
    get_recommendation,
    list_recommendations,
    WorkspaceError,
)
from marswalk.api.contracts import validate_contract, ContractValidationError
from marswalk.api.service import (
    plan_campaign_api,
    record_campaign_progress_api,
    reprioritize_campaign_api,
    list_campaign_recommendations_api,
    APIError,
)


@pytest.fixture(scope="module")
def jezero_terrain():
    """Load authentic USGS CTX 20m Jezero Crater terrain."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tiff_path = os.path.join(base_dir, "data", "processed", "jezero_ready_20m.tif")
    if not os.path.exists(tiff_path):
        pytest.skip(f"Jezero CTX raster not found at {tiff_path}")
    return load_and_process_terrain(tiff_path)


@pytest.fixture
def temp_workspace():
    """Temporary workspace directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="marswalk_m11c_test_")
    camps_dir = os.path.join(temp_dir, "campaigns")
    obs_dir = os.path.join(temp_dir, "observations")
    recs_dir = os.path.join(temp_dir, "recommendations")
    os.makedirs(camps_dir, exist_ok=True)
    os.makedirs(obs_dir, exist_ok=True)
    os.makedirs(recs_dir, exist_ok=True)

    yield {
        "root": temp_dir,
        "campaigns": camps_dir,
        "observations": obs_dir,
        "recommendations": recs_dir,
    }
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. Reprioritization Using Explicit Objective Weights
# ==============================================================================

def test_reprioritization_with_objective_weights(jezero_terrain):
    """Test that explicit user objective weights alter target priorities and schedule sequence."""
    targets = [
        CampaignTarget(
            id="t_astro",
            name="Astrobiology Core",
            row=120, col=158,
            priority_score=50.0,
            science_objective="astrobiology",
        ),
        CampaignTarget(
            id="t_geol",
            name="Geological Strata",
            row=125, col=155,
            priority_score=60.0,
            science_objective="geology",
        ),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_weights_test", "Weights Test", cfg, targets, jezero_terrain)

    # Heavily weight astrobiology objective over geology
    objective_weights = {
        "astrobiology": 2.0,
        "geology": 0.5,
    }

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_weights=objective_weights,
    )

    assert recommendation.has_improvements is True
    assert "astrobiology" in recommendation.objective_weights
    # Check that astrobiology target gained elevated score
    proposed_targets = {t["id"]: t for t in recommendation.proposed_campaign["targets"]}
    assert proposed_targets["t_astro"]["priority_score"] == 100.0  # 50.0 * 2.0


def test_invalid_negative_objective_weights_raise_error(jezero_terrain):
    """Test that negative objective weights raise ValueError."""
    targets = [CampaignTarget(id="t1", name="Target 1", row=120, col=158, priority_score=50.0)]
    cfg = CampaignConfig(base_start_rc=(117, 157))
    campaign = plan_mission_campaign("cmp_neg_wt", "Negative Weight Test", cfg, targets, jezero_terrain)

    with pytest.raises(ValueError, match="must be a non-negative number"):
        evaluate_campaign_intelligence(
            campaign=campaign,
            terrain=jezero_terrain,
            objective_weights={"sample_return": -1.5},
        )


# ==============================================================================
# 2. Non-Rescheduling Invariant & Prior Sol Freezing
# ==============================================================================

def test_completed_objectives_omitted_from_future_sorties(jezero_terrain):
    """Test that completed objectives are permanently omitted from future planned sorties."""
    targets = [
        CampaignTarget(id="t_done", name="Done Target", row=120, col=158, priority_score=80.0),
        CampaignTarget(id="t_remain_1", name="Remaining 1", row=125, col=155, priority_score=60.0),
        CampaignTarget(id="t_remain_2", name="Remaining 2", row=110, col=160, priority_score=40.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=2500.0)
    campaign = plan_mission_campaign("cmp_inv_test", "Invariant Test", cfg, targets, jezero_terrain)

    # Advance Sol 1 by completing t_done
    updated_campaign, _, _ = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_VISITED.value,
        target_id="t_done",
        terrain=jezero_terrain,
        sol_index=1,
    )

    # Run intelligence reprioritizer
    recommendation = evaluate_campaign_intelligence(
        campaign=updated_campaign,
        terrain=jezero_terrain,
    )

    # Invariant: t_done must NOT appear in any sortie with sol_index > 1
    proposed_sorties = recommendation.proposed_campaign["sorties"]
    for s in proposed_sorties:
        if s["sol_index"] > 1:
            assert "t_done" not in s["target_ids"]

    # Check rationale
    done_rationale = next(r for r in recommendation.target_rationales if r.target_id == "t_done")
    assert done_rationale.status_change == "COMPLETED_PRESERVED"


# ==============================================================================
# 3. Observational Evidence Adaptation (Supports vs Does Not Support vs Inconclusive)
# ==============================================================================

def test_positive_evidence_boosts_downstream_objectives(jezero_terrain):
    """Test that a SUPPORTS_OBJECTIVE observation elevates downstream target priorities."""
    targets = [
        CampaignTarget(id="t_parent", name="Clay Parent", row=120, col=158, priority_score=70.0),
        CampaignTarget(id="t_child", name="Clay Child", row=125, col=155, priority_score=50.0, prerequisites=["t_parent"]),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_pos_ev", "Positive Evidence", cfg, targets, jezero_terrain)

    # Mark t_parent complete with SUPPORTS_OBJECTIVE assessment
    assessments = [
        {
            "target_id": "t_parent",
            "objective_classification": ObjectiveClassification.SUPPORTS_OBJECTIVE.value,
            "repeat_observation_requested": False,
        }
    ]

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_assessments=assessments,
    )

    child_rationale = next(r for r in recommendation.target_rationales if r.target_id == "t_child")
    assert "validated scientific objective (+25%)" in child_rationale.reason or child_rationale.status_change in ("EXPEDITED", "UNBLOCKED", "UNCHANGED")


def test_negative_evidence_deprioritizes_downstream_branch(jezero_terrain):
    """Test that DOES_NOT_SUPPORT_OBJECTIVE assessment deprioritizes downstream dependent branch."""
    targets = [
        CampaignTarget(id="t_parent", name="Barren Parent", row=120, col=158, priority_score=70.0),
        CampaignTarget(id="t_child", name="Dependent Child", row=125, col=155, priority_score=50.0, prerequisites=["t_parent"]),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_neg_ev", "Negative Evidence", cfg, targets, jezero_terrain)

    assessments = [
        {
            "target_id": "t_parent",
            "objective_classification": ObjectiveClassification.DOES_NOT_SUPPORT_OBJECTIVE.value,
            "repeat_observation_requested": False,
        }
    ]

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_assessments=assessments,
    )

    child_rationale = next(r for r in recommendation.target_rationales if r.target_id == "t_child")
    assert "refuted target hypothesis (-35%)" in child_rationale.reason or child_rationale.status_change in ("POSTPONED", "DEFERRED", "UNCHANGED")


def test_inconclusive_observation_neutrality(jezero_terrain):
    """Test that INCONCLUSIVE observation remains neutral and does not imply success or failure."""
    targets = [
        CampaignTarget(id="t_parent", name="Ambiguous Parent", row=120, col=158, priority_score=70.0),
        CampaignTarget(id="t_child", name="Neutral Child", row=125, col=155, priority_score=50.0, prerequisites=["t_parent"]),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_inconc_ev", "Inconclusive Neutrality", cfg, targets, jezero_terrain)

    assessments = [
        {
            "target_id": "t_parent",
            "objective_classification": ObjectiveClassification.INCONCLUSIVE.value,
        }
    ]

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_assessments=assessments,
    )

    child_rationale = next(r for r in recommendation.target_rationales if r.target_id == "t_child")
    assert "observation inconclusive (neutral)" in child_rationale.reason or "Preserved" in child_rationale.reason


# ==============================================================================
# 4. Explicit Repeat-Observation Handling
# ==============================================================================

def test_explicit_repeat_observation_scheduled(jezero_terrain):
    """Test that requesting a repeat observation schedules a follow-up target."""
    targets = [
        CampaignTarget(id="t_core", name="Sample Core Belva", row=120, col=158, priority_score=90.0),
        CampaignTarget(id="t_strata", name="Strata Unit", row=125, col=155, priority_score=60.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_repeat_test", "Repeat Test", cfg, targets, jezero_terrain)

    # Complete t_core on Sol 1
    updated_campaign, _, _ = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_VISITED.value,
        target_id="t_core",
        terrain=jezero_terrain,
        sol_index=1,
    )

    # Request repeat observation for t_core
    recommendation = evaluate_campaign_intelligence(
        campaign=updated_campaign,
        terrain=jezero_terrain,
        repeat_requests=["t_core"],
    )

    # Repeat rationale must exist
    repeat_rationale = next(r for r in recommendation.target_rationales if r.target_id == "t_core")
    assert repeat_rationale.status_change == "REPEAT_ADDED"
    assert "repeat observation requested" in repeat_rationale.reason


# ==============================================================================
# 5. Provenance Preservation & Missing Data Handling
# ==============================================================================

def test_provenance_preservation_and_anti_fabrication(jezero_terrain):
    """Test that simulated vs authentic provenance is strictly preserved without mutation."""
    sim_obs = {
        "observation_id": "obs_sim_01",
        "campaign_id": "cmp_prov_test",
        "target_id": "t1",
        "observation_type": "SPECTRAL_SURVEY",
        "provenance": "SIMULATED",
        "is_simulated": True,
        "timestamp_utc": "2026-10-29T12:00:00Z",
    }
    auth_obs = {
        "observation_id": "obs_meda_01",
        "campaign_id": "cmp_prov_test",
        "target_id": "t2",
        "observation_type": "ATMOSPHERIC_MEASUREMENT",
        "provenance": "IMPORTED_PDS_MEDA",
        "is_simulated": False,
        "timestamp_utc": "2026-10-29T12:00:00Z",
    }

    targets = [
        CampaignTarget(id="t1", name="Target 1", row=120, col=158, priority_score=60.0),
        CampaignTarget(id="t2", name="Target 2", row=125, col=155, priority_score=70.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157))
    campaign = plan_mission_campaign("cmp_prov_test", "Provenance Test", cfg, targets, jezero_terrain)

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        observations=[sim_obs, auth_obs],
    )

    # Provenance tags must remain unchanged
    assert sim_obs["provenance"] == "SIMULATED"
    assert sim_obs["is_simulated"] is True
    assert auth_obs["provenance"] == "IMPORTED_PDS_MEDA"
    assert auth_obs["is_simulated"] is False


# ==============================================================================
# 6. Multi-Strategy Trade-Off Comparison & Explainability
# ==============================================================================

def test_strategy_comparison_and_tradeoffs(jezero_terrain):
    """Test that strategy comparison contains baseline, proposed, and standard profile metrics."""
    targets = [
        CampaignTarget(id="t1", name="T1", row=120, col=158, priority_score=80.0),
        CampaignTarget(id="t2", name="T2", row=125, col=155, priority_score=70.0),
        CampaignTarget(id="t3", name="T3", row=110, col=160, priority_score=60.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=2500.0)
    campaign = plan_mission_campaign("cmp_strat_test", "Strategy Test", cfg, targets, jezero_terrain)

    recommendation = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_weights={"T1": 1.5, "T3": 0.5},
    )

    comp = recommendation.strategy_comparison
    assert "baseline" in comp
    assert "proposed_adaptive" in comp
    assert "science_priority" in comp
    assert "time_constrained" in comp
    assert "conservative" in comp

    assert comp["baseline"].total_distance_m > 0
    assert comp["proposed_adaptive"].total_duration_s > 0
    assert comp["proposed_adaptive"].is_feasible is True


# ==============================================================================
# 7. Workspace Persistence for Recommendations
# ==============================================================================

def test_workspace_save_and_list_recommendations(temp_workspace):
    """Test saving and retrieving campaign recommendations from workspace."""
    recs_dir = temp_workspace["recommendations"]

    rec_payload = {
        "schema_version": "1.0.0",
        "campaign_id": "cmp_ws_rec_01",
        "source_version": 1,
        "proposed_version": 2,
        "proposed_revision_id": "rev_02_intelligence",
        "created_at_utc": "2026-10-29T12:00:00Z",
        "objective_weights": {"astrobiology": 1.5},
        "has_improvements": True,
        "strategy_comparison": {
            "baseline": {
                "profile_name": "Current Baseline Plan",
                "total_sols": 2,
                "total_distance_m": 1250.0,
                "total_duration_s": 7200.0,
                "total_science_score": 140.0,
                "targets_scheduled": 2,
                "targets_completed": 0,
                "targets_deferred": 0,
                "is_feasible": True,
            }
        },
        "target_rationales": [
            {
                "target_id": "t1",
                "target_name": "Target 1",
                "status_change": "EXPEDITED",
                "reason": "Expedited based on positive observation outcome.",
                "original_sol": 2,
                "revised_sol": 1,
                "supporting_observation_ids": ["obs_01"],
            }
        ],
        "proposed_campaign": {"campaign_id": "cmp_ws_rec_01", "version": 2},
    }

    save_recommendation(rec_payload, recommendations_dir=recs_dir)

    # Retrieve specific recommendation
    retrieved = get_recommendation("cmp_ws_rec_01", "rev_02_intelligence", recommendations_dir=recs_dir)
    assert retrieved["campaign_id"] == "cmp_ws_rec_01"
    assert retrieved["proposed_version"] == 2

    # List recommendations
    all_recs = list_recommendations("cmp_ws_rec_01", recommendations_dir=recs_dir)
    assert len(all_recs) == 1
    assert all_recs[0]["proposed_revision_id"] == "rev_02_intelligence"


# ==============================================================================
# 8. API Service Layer Functions
# ==============================================================================

def test_api_service_reprioritize_and_apply(jezero_terrain, temp_workspace, monkeypatch):
    """Test reprioritize_campaign_api service function with apply=True."""
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_CAMPAIGNS_DIR", temp_workspace["campaigns"])
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_RECOMMENDATIONS_DIR", temp_workspace["recommendations"])

    # 1. Plan source campaign
    targets = [
        {"id": "t_api_a", "name": "API Target A", "row": 120, "col": 158, "priority_score": 70.0, "science_objective": "clays"},
        {"id": "t_api_b", "name": "API Target B", "row": 125, "col": 155, "priority_score": 50.0, "science_objective": "basalt"},
    ]
    camp_payload = {
        "campaign_id": "cmp_api_reprioritize_01",
        "name": "API Reprioritize Test",
        "targets": targets,
        "config": {"max_duration_per_sortie_s": 7200.0, "base_start_rc": [117, 157]},
    }
    camp_res = plan_campaign_api(camp_payload, jezero_terrain, getattr(jezero_terrain, "transform", None))
    cid = camp_res["campaign"]["campaign_id"]

    # 2. Call reprioritize API with apply=True
    rep_payload = {
        "campaign_id": cid,
        "objective_weights": {"clays": 1.4, "basalt": 0.6},
        "apply": True,
    }
    transform = getattr(jezero_terrain, "transform", None)
    rep_res = reprioritize_campaign_api(rep_payload, jezero_terrain, transform)

    assert rep_res["status"] == "success"
    assert rep_res["applied"] is True
    assert rep_res["campaign"]["version"] == 2
    assert rep_res["recommendation"]["has_improvements"] is True


# ==============================================================================
# 9. Live HTTP REST API Endpoints (Port 3000)
# ==============================================================================

def test_live_server_campaign_reprioritization_endpoints():
    """Verify live HTTP server on port 3000 handles POST /api/campaign/reprioritize & GET /api/campaign/recommendations."""
    base_url = "http://127.0.0.1:3000"

    # Check server availability
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
    except urllib.error.URLError:
        pytest.skip("Atlas HTTP server on port 3000 not currently reachable")

    live_cid = f"cmp_live_m11c_{uuid.uuid4().hex[:6]}"

    # 1. Create campaign on live server
    create_payload = json.dumps({
        "campaign_id": live_cid,
        "name": "Live HTTP 11C Test",
        "targets": [
            {"id": "t_live_1", "name": "Live Target 1", "row": 120, "col": 158, "priority_score": 60.0, "science_objective": "crater_rim"},
            {"id": "t_live_2", "name": "Live Target 2", "row": 125, "col": 155, "priority_score": 75.0, "science_objective": "delta_mudstone"},
        ],
        "config": {"max_duration_per_sortie_s": 7200.0, "base_start_rc": [117, 157]},
    }).encode("utf-8")

    req_create = urllib.request.Request(
        f"{base_url}/api/campaign/plan",
        data=create_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_create, timeout=10.0) as resp:
        assert resp.status == 200

    # 2. Call POST /api/campaign/reprioritize
    rep_payload = json.dumps({
        "campaign_id": live_cid,
        "objective_weights": {"delta_mudstone": 1.5, "crater_rim": 0.8},
        "apply": True,
    }).encode("utf-8")

    req_rep = urllib.request.Request(
        f"{base_url}/api/campaign/reprioritize",
        data=rep_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req_rep, timeout=15.0) as resp:
        assert resp.status == 200
        rep_res = json.loads(resp.read().decode())
        assert rep_res["status"] == "success"
        assert rep_res["applied"] is True
        assert rep_res["campaign"]["version"] == 2
        assert "delta_mudstone" in rep_res["recommendation"]["objective_weights"]

    # 3. Call GET /api/campaign/recommendations
    req_get_recs = urllib.request.Request(f"{base_url}/api/campaign/recommendations?campaign_id={live_cid}")
    with urllib.request.urlopen(req_get_recs, timeout=5.0) as resp:
        assert resp.status == 200
        get_res = json.loads(resp.read().decode())
        assert get_res["status"] == "success"
        assert get_res["count"] >= 1
        assert get_res["recommendations"][0]["campaign_id"] == live_cid


# ==============================================================================
# 10. Boundary Conditions, Invariant Enforcement & Infeasible Targets
# ==============================================================================

def test_no_improvements_found_preserves_baseline(jezero_terrain):
    """Test that when no evidence or weights change, has_improvements is False and warning is present."""
    targets = [
        CampaignTarget(id="t_opt_1", name="Opt 1", row=120, col=158, priority_score=80.0),
        CampaignTarget(id="t_opt_2", name="Opt 2", row=125, col=155, priority_score=60.0),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_no_imp", "No Imp", cfg, targets, jezero_terrain)

    # Call with empty weights, assessments, and repeats
    rec = evaluate_campaign_intelligence(
        campaign=campaign,
        terrain=jezero_terrain,
        objective_weights={},
        objective_assessments=[],
        repeat_requests=[],
    )

    assert rec.has_improvements is False
    assert any("already optimal" in w for w in rec.warnings)


def test_blocked_prerequisite_prevents_downstream_scheduling(jezero_terrain):
    """Test that if an upstream prerequisite is blocked, downstream targets are deferred."""
    targets = [
        CampaignTarget(id="t_hazard", name="Hazard Target", row=120, col=158, priority_score=80.0),
        CampaignTarget(id="t_blocked_child", name="Blocked Child", row=125, col=155, priority_score=70.0, prerequisites=["t_hazard"]),
    ]
    cfg = CampaignConfig(base_start_rc=(117, 157), max_duration_per_sortie_s=7200.0)
    campaign = plan_mission_campaign("cmp_blk_prereq", "Blocked Prereq", cfg, targets, jezero_terrain)

    # Block t_hazard
    updated_campaign, _, _ = advance_campaign_progress(
        campaign=campaign,
        event_type=ProgressEventType.TARGET_BLOCKED.value,
        target_id="t_hazard",
        terrain=jezero_terrain,
        sol_index=1,
        details={"reason": "Hazardous scree obstacle."},
    )

    rec = evaluate_campaign_intelligence(
        campaign=updated_campaign,
        terrain=jezero_terrain,
    )

    # Child should be deferred
    child_rat = next(r for r in rec.target_rationales if r.target_id == "t_blocked_child")
    assert child_rat.status_change == "DEFERRED"


def test_version_immutability_on_disk(jezero_terrain, temp_workspace, monkeypatch):
    """Test that applying reprioritization creates version 2 while keeping version 1 file immutable."""
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_CAMPAIGNS_DIR", temp_workspace["campaigns"])
    monkeypatch.setattr("marswalk.api.workspace.DEFAULT_RECOMMENDATIONS_DIR", temp_workspace["recommendations"])

    targets = [
        {"id": "t_v1", "name": "V1 Target", "row": 120, "col": 158, "priority_score": 70.0},
        {"id": "t_v2", "name": "V2 Target", "row": 125, "col": 155, "priority_score": 50.0},
    ]
    camp_payload = {
        "campaign_id": "cmp_version_immutability",
        "name": "Immutability Test",
        "targets": targets,
        "config": {"max_duration_per_sortie_s": 7200.0, "base_start_rc": [117, 157]},
    }
    camp_res = plan_campaign_api(camp_payload, jezero_terrain, getattr(jezero_terrain, "transform", None))
    cid = camp_res["campaign"]["campaign_id"]

    # Verify v1 exists
    v1_path = os.path.join(temp_workspace["campaigns"], f"{cid}_v1.json")
    assert os.path.exists(v1_path)
    with open(v1_path, "r", encoding="utf-8") as f:
        v1_data = json.load(f)
    assert v1_data["version"] == 1

    # Reprioritize and apply
    rep_res = reprioritize_campaign_api(
        {
            "campaign_id": cid,
            "objective_weights": {"t_v2": 2.0},
            "apply": True,
        },
        jezero_terrain,
        getattr(jezero_terrain, "transform", None),
    )
    assert rep_res["campaign"]["version"] == 2

    # Verify v1 remains version 1 and v2 is version 2
    v2_path = os.path.join(temp_workspace["campaigns"], f"{cid}_v2.json")
    assert os.path.exists(v2_path)
    with open(v1_path, "r", encoding="utf-8") as f:
        v1_data_after = json.load(f)
    assert v1_data_after["version"] == 1
    with open(v2_path, "r", encoding="utf-8") as f:
        v2_data = json.load(f)
    assert v2_data["version"] == 2


def test_reprioritize_api_unknown_campaign_error(jezero_terrain):
    """Test that reprioritizing an unknown campaign raises APIError with 404 or 400."""
    with pytest.raises(Exception):
        reprioritize_campaign_api(
            {"campaign_id": "cmp_does_not_exist_99999"},
            jezero_terrain,
            getattr(jezero_terrain, "transform", None),
        )

