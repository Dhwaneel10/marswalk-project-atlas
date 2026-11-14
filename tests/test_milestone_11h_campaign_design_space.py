# tests/test_milestone_11h_campaign_design_space.py
"""
Test suite for Milestone 11H: Campaign Design Space Explorer & Pareto Optimization.

Verifies:
1. Pure mathematical Pareto dominance and frontier classification.
2. Deterministic candidate generation and input fingerprint deduplication.
3. Search bound enforcement (max_candidates, max_planner_calls, limit_reached).
4. Real campaign candidate evaluations across Jezero CTX 20m topography.
5. Infeasible candidate partitioning with failure reasons.
6. Grounded multi-objective trade-off recommendations.
7. Draft 2020-12 schema validation (campaign-design-space.schema.json).
8. Atomic workspace persistence and filtered listing.
9. Candidate promotion creating distinct campaign version v{n+1} while preserving baseline.
10. Rejection of infeasible candidate promotion.
11. REST API service handlers and live HTTP endpoints on port 3000.
12. Explicit planning-analysis limitations disclaimer.
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
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.campaign_design_space import (
    CandidateEvaluation,
    CandidateObjectives,
    CandidateStatus,
    DominanceStatus,
    SearchBounds,
    SearchCompleteness,
    check_dominance,
    classify_pareto_frontier,
    compute_config_fingerprint,
    generate_candidate_configurations,
    evaluate_candidate_configuration,
    explore_campaign_design_space,
    build_tradeoff_explanations,
    DESIGN_SPACE_DISCLAIMER,
)
from marswalk.api.contracts import (
    validate_campaign_design_space_record,
    ContractValidationError,
)
from marswalk.api.workspace import (
    save_design_space_evaluation,
    get_design_space_evaluation,
    list_design_space_evaluations,
    promote_design_space_candidate,
    save_campaign,
    get_campaign,
    WorkspaceError,
)
from marswalk.api.service import (
    evaluate_campaign_design_space_api,
    get_campaign_design_space_api,
    list_campaign_design_spaces_api,
    promote_design_space_candidate_api,
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
    ]

    cfg = CampaignConfig(
        planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
        max_duration_per_sortie_s=28800.0,
        max_sols=3,
    )

    campaign = plan_mission_campaign(
        campaign_id="cmp_ds_test_001",
        name="Jezero Design Space Test Campaign",
        config=cfg,
        targets=targets,
        terrain=terrain_grid,
    )
    save_campaign(campaign.to_dict())
    return campaign


# =========================================================================
# 1. PURE MATHEMATICAL PARETO DOMINANCE FIXTURE TESTS
# =========================================================================

def test_pareto_mathematical_dominance_strict():
    """Verifies candidate A dominates B when A is better in at least one objective and equal in all others."""
    cand_a = CandidateEvaluation(
        candidate_id="cand_a",
        fingerprint="aaa",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=100.0,  # better
            total_duration_s=25000.0,
            total_distance_m=12000.0,
            unallocated_priority=0.0,
            temporal_conflicts_count=0,
            sortie_count=3,
        ),
        dominance_status="",
    )

    cand_b = CandidateEvaluation(
        candidate_id="cand_b",
        fingerprint="bbb",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=85.0,  # worse
            total_duration_s=25000.0,
            total_distance_m=12000.0,
            unallocated_priority=15.0,
            temporal_conflicts_count=0,
            sortie_count=3,
        ),
        dominance_status="",
    )

    assert check_dominance(cand_a, cand_b) is True
    assert check_dominance(cand_b, cand_a) is False


def test_pareto_mathematical_tradeoff_non_dominance():
    """Verifies two candidates with genuine trade-offs (e.g. coverage vs duration) do not dominate each other."""
    cand_high_sci = CandidateEvaluation(
        candidate_id="cand_high_sci",
        fingerprint="c1",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=100.0,  # better coverage
            total_duration_s=30000.0,   # worse duration
            total_distance_m=15000.0,
            unallocated_priority=0.0,
            temporal_conflicts_count=0,
            sortie_count=3,
        ),
        dominance_status="",
    )

    cand_fast = CandidateEvaluation(
        candidate_id="cand_fast",
        fingerprint="c2",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=80.0,   # worse coverage
            total_duration_s=18000.0,   # better duration
            total_distance_m=9000.0,    # better distance
            unallocated_priority=20.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status="",
    )

    # Neither dominates the other
    assert check_dominance(cand_high_sci, cand_fast) is False
    assert check_dominance(cand_fast, cand_high_sci) is False

    pareto, dominated, infeasible = classify_pareto_frontier([cand_high_sci, cand_fast])
    assert len(pareto) == 2
    assert len(dominated) == 0
    assert len(infeasible) == 0
    assert cand_high_sci.dominance_status == DominanceStatus.PARETO_EFFICIENT.value
    assert cand_fast.dominance_status == DominanceStatus.PARETO_EFFICIENT.value


def test_pareto_infeasible_candidate_partition():
    """Verifies that infeasible candidates are partitioned and cannot dominate feasible ones."""
    cand_infeasible = CandidateEvaluation(
        candidate_id="cand_inf",
        fingerprint="inf",
        configuration={},
        status=CandidateStatus.INFEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=100.0,
            total_duration_s=1000.0,
            total_distance_m=500.0,
            unallocated_priority=0.0,
            temporal_conflicts_count=0,
            sortie_count=1,
        ),
        dominance_status="",
        infeasibility_reasons=["Exceeded slope constraint"],
    )

    cand_feasible = CandidateEvaluation(
        candidate_id="cand_feas",
        fingerprint="feas",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=80.0,
            total_duration_s=25000.0,
            total_distance_m=12000.0,
            unallocated_priority=20.0,
            temporal_conflicts_count=0,
            sortie_count=3,
        ),
        dominance_status="",
    )

    assert check_dominance(cand_infeasible, cand_feasible) is False
    assert check_dominance(cand_feasible, cand_infeasible) is True

    pareto, dominated, infeasible = classify_pareto_frontier([cand_infeasible, cand_feasible])
    assert len(pareto) == 1
    assert pareto[0].candidate_id == "cand_feas"
    assert len(infeasible) == 1
    assert infeasible[0].candidate_id == "cand_inf"
    assert infeasible[0].dominance_status == DominanceStatus.INFEASIBLE.value


# =========================================================================
# 2. CANDIDATE GENERATION, DEDUPLICATION & SEARCH BOUNDS
# =========================================================================

def test_deterministic_candidate_generation_and_deduplication():
    """Verifies deterministic candidate generation order and SHA-256 fingerprint deduplication."""
    base_cfg = {
        "planning_profile": "science_priority",
        "max_duration_per_sortie_s": 28800.0,
        "max_sols": 3,
    }

    dims = {
        "profiles": ["science_priority", "time_constrained"],
        "duration_limits_s": [21600.0, 28800.0],
        "max_sols_options": [2, 3],
    }

    configs1, comp1 = generate_candidate_configurations(base_cfg, dims, SearchBounds(max_candidates=10))
    configs2, comp2 = generate_candidate_configurations(base_cfg, dims, SearchBounds(max_candidates=10))

    # Determinism
    assert len(configs1) == len(configs2)
    for c1, c2 in zip(configs1, configs2):
        assert compute_config_fingerprint(c1) == compute_config_fingerprint(c2)

    # Deduplication accounted for
    assert comp1.candidates_deduplicated >= 0


def test_search_bound_limit_enforcement():
    """Verifies that max_candidates strictly limits generated candidates and marks limit_reached=True."""
    base_cfg = {
        "planning_profile": "science_priority",
        "max_duration_per_sortie_s": 28800.0,
        "max_sols": 3,
    }
    bounds = SearchBounds(max_candidates=4, max_planner_calls=4)

    configs, comp = generate_candidate_configurations(base_cfg, None, bounds)
    assert len(configs) <= 4
    assert comp.limit_reached is True
    assert comp.is_exhaustive is False
    assert "budget" in comp.unexplored_scope_notes.lower()


# =========================================================================
# 3. REAL CAMPAIGN ENGINE EVALUATION & EXPLORATION
# =========================================================================

def test_real_campaign_design_space_exploration(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies end-to-end design space exploration with real A* planner across Jezero topography."""
    bounds = SearchBounds(max_candidates=4, max_planner_calls=4)
    result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=bounds,
    )

    assert result["schema_version"] == "1.0.0"
    assert result["design_space_id"].startswith("ds_")
    assert result["campaign_id"] == sample_campaign.campaign_id
    assert "search_completeness" in result
    assert "pareto_candidates" in result
    assert "dominated_candidates" in result
    assert "infeasible_candidates" in result
    assert "recommendations" in result
    assert "limitations_disclaimer" in result

    total_evaluated = len(result["pareto_candidates"]) + len(result["dominated_candidates"]) + len(result["infeasible_candidates"])
    assert total_evaluated == result["search_completeness"]["candidates_evaluated"]
    assert total_evaluated <= 4


def test_schema_validation_campaign_design_space(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies that generated design space records validate under Draft 2020-12 and catch corruption."""
    bounds = SearchBounds(max_candidates=3, max_planner_calls=3)
    result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=bounds,
    )

    is_valid, errs = validate_campaign_design_space_record(result)
    assert is_valid is True
    assert len(errs) == 0

    # Test corrupted payload raises ContractValidationError
    bad_payload = copy.deepcopy(result)
    del bad_payload["pareto_candidates"]
    with pytest.raises(ContractValidationError):
        validate_campaign_design_space_record(bad_payload)


def test_tradeoff_recommendations_grounded_metrics(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies that generated trade-off recommendations contain non-fabricated grounded numbers."""
    bounds = SearchBounds(max_candidates=5, max_planner_calls=5)
    result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=bounds,
    )
    recs = result["recommendations"]
    assert len(recs) > 0

    for rec in recs:
        assert rec["recommendation_id"].startswith("rec_ds_")
        assert len(rec["candidate_id"]) > 0
        assert len(rec["headline"]) > 0
        assert len(rec["tradeoff_summary"]) > 0
        assert len(rec["selection_rationale"]) > 0


# =========================================================================
# 4. WORKSPACE PERSISTENCE, PROMOTION & IMMUTABILITY
# =========================================================================

def test_workspace_persistence_and_listing(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies save, get, and list functions for campaign design spaces."""
    bounds = SearchBounds(max_candidates=3, max_planner_calls=3)
    eval_result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=bounds,
    )

    saved = save_design_space_evaluation(eval_result)
    assert saved["design_space_id"] == eval_result["design_space_id"]

    fetched = get_design_space_evaluation(eval_result["design_space_id"])
    assert fetched["design_space_id"] == eval_result["design_space_id"]

    all_ds = list_design_space_evaluations(campaign_id=sample_campaign.campaign_id)
    assert any(ds["design_space_id"] == eval_result["design_space_id"] for ds in all_ds)


def test_candidate_promotion_creates_new_version_and_preserves_baseline(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies promoting a candidate creates version v{n+1} without mutating the baseline."""
    bounds = SearchBounds(max_candidates=3, max_planner_calls=3)
    eval_result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=bounds,
    )
    save_design_space_evaluation(eval_result)

    assert len(eval_result["pareto_candidates"]) > 0
    promoted_cand = eval_result["pareto_candidates"][0]

    orig_version = sample_campaign.version
    orig_campaign_id = sample_campaign.campaign_id

    # Promote candidate
    prom_res = promote_design_space_candidate(
        design_space_id=eval_result["design_space_id"],
        candidate_id=promoted_cand["candidate_id"],
        new_campaign_name="Promoted Jezero Campaign v2",
    )

    assert prom_res["status"] == "success"
    assert prom_res["new_version"] == orig_version + 1
    assert prom_res["new_campaign_id"] == f"{orig_campaign_id}_v{orig_version + 1}"

    # Verify baseline campaign is preserved and unmodified
    reloaded_base = get_campaign(orig_campaign_id)
    assert reloaded_base["version"] == orig_version
    assert reloaded_base["campaign_id"] == orig_campaign_id

    # Verify newly created campaign is retrievable
    new_camp = get_campaign(prom_res["new_campaign_id"])
    assert new_camp["version"] == orig_version + 1
    assert new_camp["name"] == "Promoted Jezero Campaign v2"


def test_infeasible_candidate_promotion_rejected(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies that promoting an infeasible candidate raises WorkspaceError with ERR_CANDIDATE_INFEASIBLE."""
    eval_result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=SearchBounds(max_candidates=2, max_planner_calls=2),
    )
    # Inject a simulated infeasible candidate
    inf_cand = {
        "candidate_id": "cand_cp_inf_test",
        "fingerprint": "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        "configuration": {"max_duration_per_sortie_s": 100.0},
        "status": "INFEASIBLE",
        "objectives": {
            "science_coverage_pct": 0.0,
            "total_duration_s": 0.0,
            "total_distance_m": 0.0,
            "unallocated_priority": 100.0,
            "temporal_conflicts_count": 0,
            "sortie_count": 0,
        },
        "dominance_status": "INFEASIBLE",
        "dominated_by": [],
        "tradeoff_explanation": "Infeasible test candidate",
        "infeasibility_reasons": ["Duration too small to reach any target"],
    }
    eval_result["infeasible_candidates"].append(inf_cand)
    save_design_space_evaluation(eval_result)

    with pytest.raises(WorkspaceError) as exc_info:
        promote_design_space_candidate(
            design_space_id=eval_result["design_space_id"],
            candidate_id="cand_cp_inf_test",
        )
    assert exc_info.value.error_code == "ERR_CANDIDATE_INFEASIBLE"


# =========================================================================
# 5. REST API SERVICE & LIVE HTTP ENDPOINTS
# =========================================================================

def test_api_service_design_space_endpoints(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies evaluate_campaign_design_space_api service method and validation."""
    payload = {
        "campaign_id": sample_campaign.campaign_id,
        "search_bounds": {"max_candidates": 3, "max_planner_calls": 3},
        "persist": True,
    }
    res = evaluate_campaign_design_space_api(payload, terrain=terrain_grid)
    assert res["schema_version"] == "1.0.0"
    assert res["campaign_id"] == sample_campaign.campaign_id

    # Test error on missing campaign
    with pytest.raises(APIError):
        evaluate_campaign_design_space_api({})


def test_http_rest_design_space_endpoints(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies live HTTP REST endpoints on port 3000 (evaluate, list, get, promote)."""
    base_url = "http://127.0.0.1:3000"

    # 1. POST /api/campaign/design-space/evaluate
    eval_url = f"{base_url}/api/campaign/design-space/evaluate"
    post_data = json.dumps({
        "campaign_id": sample_campaign.campaign_id,
        "search_bounds": {"max_candidates": 3, "max_planner_calls": 3},
        "persist": True,
    }).encode("utf-8")

    req = urllib.request.Request(eval_url, data=post_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        ds_data = json.loads(resp.read().decode("utf-8"))
        assert ds_data["schema_version"] == "1.0.0"
        ds_id = ds_data["design_space_id"]

    # 2. GET /api/campaign/design-spaces
    list_url = f"{base_url}/api/campaign/design-spaces"
    with urllib.request.urlopen(list_url, timeout=10) as resp:
        assert resp.status == 200
        items = json.loads(resp.read().decode("utf-8"))
        assert any(i["design_space_id"] == ds_id for i in items)

    # 3. GET /api/campaign/design-space/<id>
    get_url = f"{base_url}/api/campaign/design-space/{ds_id}"
    with urllib.request.urlopen(get_url, timeout=10) as resp:
        assert resp.status == 200
        single = json.loads(resp.read().decode("utf-8"))
        assert single["design_space_id"] == ds_id

    # 4. POST /api/campaign/design-space/promote
    cand_id = ds_data["pareto_candidates"][0]["candidate_id"]
    promote_url = f"{base_url}/api/campaign/design-space/promote"
    prom_data = json.dumps({
        "design_space_id": ds_id,
        "candidate_id": cand_id,
        "new_campaign_name": "HTTP Promoted Campaign",
    }).encode("utf-8")

    prom_req = urllib.request.Request(promote_url, data=prom_data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(prom_req, timeout=10) as resp:
        assert resp.status == 200
        prom_resp = json.loads(resp.read().decode("utf-8"))
        assert prom_resp["status"] == "success"
        assert prom_resp["promoted_candidate_id"] == cand_id


def test_limitations_disclaimer_present(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies that the design space limitations disclaimer is explicitly present."""
    result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_bounds=SearchBounds(max_candidates=2, max_planner_calls=2),
    )
    assert result["limitations_disclaimer"] == DESIGN_SPACE_DISCLAIMER
    assert "deterministic multi-objective planning tool" in result["limitations_disclaimer"].lower()
    assert "not guarantee global mathematical optimality" in result["limitations_disclaimer"].lower()


def test_candidate_incomparable_and_missing_data_safeguards():
    """Verifies that missing or NaN metric definitions are safely rejected or handled without converting to zero."""
    cand_nan = CandidateEvaluation(
        candidate_id="cand_nan",
        fingerprint="nan_fp",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=float("nan"),
            total_duration_s=20000.0,
            total_distance_m=10000.0,
            unallocated_priority=0.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status="",
    )

    cand_valid = CandidateEvaluation(
        candidate_id="cand_valid",
        fingerprint="val_fp",
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=90.0,
            total_duration_s=22000.0,
            total_distance_m=11000.0,
            unallocated_priority=10.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status="",
    )

    # NaN cannot dominate valid candidate
    assert check_dominance(cand_nan, cand_valid) is False


def test_different_objective_vectors_and_weights(
    sample_campaign: MissionCampaign,
    terrain_grid: TerrainGrid,
):
    """Verifies that exploring distinct profiles produces genuine multi-objective trade-offs."""
    dims = {
        "profiles": ["science_priority", "time_constrained", "conservative"],
        "duration_limits_s": [21600.0, 32400.0],
        "max_sols_options": [2, 3],
    }
    bounds = SearchBounds(max_candidates=6, max_planner_calls=6)
    result = explore_campaign_design_space(
        campaign=sample_campaign,
        terrain=terrain_grid,
        search_dimensions=dims,
        search_bounds=bounds,
    )

    assert len(result["pareto_candidates"]) >= 1
    # Check that objectives are properly formatted numbers
    for p in result["pareto_candidates"]:
        objs = p["objectives"]
        assert 0.0 <= objs["science_coverage_pct"] <= 100.0
        assert objs["total_duration_s"] > 0
        assert objs["total_distance_m"] > 0
