# tests/test_milestone_11i_integration_benchmark.py
"""
Test suite for Milestone 11I: V2 Integration, Benchmark Harness & Release Acceptance Gate.

Verifies:
1. All 8 representative benchmark scenarios individually and as a suite.
2. Strict correctness invariants:
   - Mathematical Pareto dominance and non-dominance of genuine trade-offs.
   - Infeasible candidate isolation (cannot dominate feasible candidates).
   - Baseline immutability and version increment on candidate promotion.
   - Rejection of infeasible candidate promotion.
   - Canonical SHA-256 input fingerprint stability.
   - Traceable separation of planned, simulated, and measured quantities.
   - Neutrality of inconclusive observations and undetermined causal attribution.
3. Complete end-to-end planning-to-analysis campaign lifecycle:
   Configuration -> Candidate generation -> A* evaluation -> Pareto classification
   -> Persistence & Retrieval -> Version Promotion (v1 -> v2) -> Multi-Unit Coordination
   -> Digital Twin Simulation -> In-Situ Observation -> Analytics & Lessons Learned.
4. Reproducibility: zero metric drift across repeated benchmark executions.
5. JSON Schema Draft 2020-12 compliance across all produced records.
6. Live HTTP REST API endpoints against Atlas server on port 3000.
"""

import copy
import json
import tempfile
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
from marswalk.core.campaign_benchmark import (
    run_campaign_benchmark_suite,
    execute_scenario_bm_norm_01,
    execute_scenario_bm_durc_02,
    execute_scenario_bm_scip_03,
    execute_scenario_bm_cons_04,
    execute_scenario_bm_infeas_05,
    execute_scenario_bm_pareto_06,
    execute_scenario_bm_multi_07,
    execute_scenario_bm_incomp_08,
    BenchmarkSuiteResult,
    BENCHMARK_SUITE_DISCLAIMER,
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
    explore_campaign_design_space,
)
from marswalk.core.campaign_coordination import (
    create_default_units,
    allocate_campaign_coordination,
)
from marswalk.core.campaign_simulator import (
    CampaignDigitalTwin,
    SimulationStatus,
)
from marswalk.core.campaign_analytics import (
    analyze_campaign_performance,
)
from marswalk.core.campaign_progress import (
    ScienceObservation,
    ObservationProvenance,
    QuantitativeMeasurement,
)
from marswalk.api.contracts import (
    validate_campaign_benchmark_record,
    validate_campaign_design_space_record,
    validate_campaign_analytics_record,
    validate_contract,
    ContractValidationError,
)
from marswalk.api.workspace import (
    save_campaign_benchmark_result,
    get_campaign_benchmark_result,
    list_campaign_benchmark_results,
    save_campaign,
    get_campaign,
    save_design_space_evaluation,
    get_design_space_evaluation,
    promote_design_space_candidate,
    WorkspaceError,
)


@pytest.fixture(scope="module")
def terrain_grid() -> TerrainGrid:
    return load_and_process_terrain("data/processed/jezero_ready_20m.tif")


# =========================================================================
# 1. INDIVIDUAL BENCHMARK SCENARIO VERIFICATION TESTS
# =========================================================================

def test_scenario_bm_norm_01(terrain_grid: TerrainGrid):
    """BM-NORM-01: Nominal multi-target feasible campaign."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_norm_01(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert res.candidates_evaluated > 0
        assert res.feasible_candidates > 0
        assert res.infeasible_candidates == 0
        assert res.pareto_candidates >= 1
        assert "all_candidates_feasible_in_nominal_envelope" in res.invariants_verified
        assert "pareto_frontier_non_empty" in res.invariants_verified
        assert "baseline_immutability_and_version_increment_verified" in res.invariants_verified


def test_scenario_bm_durc_02(terrain_grid: TerrainGrid):
    """BM-DURC-02: Duration-constrained campaign with target deferral."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_durc_02(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "sortie_duration_limits_strictly_respected" in res.invariants_verified
        assert "target_deferral_and_multi_sol_allocation_handled" in res.invariants_verified


def test_scenario_bm_scip_03(terrain_grid: TerrainGrid):
    """BM-SCIP-03: Science-priority prerequisite chain in topological order."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_scip_03(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "prerequisite_dag_strict_topological_ordering" in res.invariants_verified
        assert res.outputs_summary["visited_order"] == ["tgt_alpha", "tgt_beta", "tgt_gamma"]


def test_scenario_bm_cons_04(terrain_grid: TerrainGrid):
    """BM-CONS-04: Conservative high-margin campaign duration verification."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_cons_04(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "conservative_safety_margin_penalties_verified" in res.invariants_verified
        assert res.outputs_summary["conservative_duration_s"] >= res.outputs_summary["science_duration_s"]


def test_scenario_bm_infeas_05(terrain_grid: TerrainGrid):
    """BM-INFEAS-05: Infeasible candidate partitioning, dominance rejection, and promotion blocking."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_infeas_05(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "infeasible_cannot_dominate_feasible_invariant" in res.invariants_verified
        assert "infeasible_partitioning_verified" in res.invariants_verified
        assert "infeasible_candidate_promotion_hard_rejection" in res.invariants_verified


def test_scenario_bm_pareto_06(terrain_grid: TerrainGrid):
    """BM-PARETO-06: Genuine multi-objective Pareto trade-offs and non-dominance."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_pareto_06(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "genuine_tradeoff_mutual_non_dominance" in res.invariants_verified
        assert "frontier_preserves_both_tradeoff_candidates" in res.invariants_verified
        assert "multi_dimensional_objective_vectors_preserved_without_composite_distortion" in res.invariants_verified
        assert res.pareto_candidates == 2


def test_scenario_bm_multi_07(terrain_grid: TerrainGrid):
    """BM-MULTI-07: Multi-unit fleet allocation and timeline execution simulation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_multi_07(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "multi_unit_fleet_task_allocation_verified" in res.invariants_verified
        assert "temporal_execution_timeline_reconstructed" in res.invariants_verified


def test_scenario_bm_incomp_08(terrain_grid: TerrainGrid):
    """BM-INCOMP-08: Incomplete evidence integrity, neutral deltas, and disclaimers."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = execute_scenario_bm_incomp_08(terrain=terrain_grid, workspace_dir=tmp_dir)
        assert res.status == "PASSED"
        assert "mandatory_limitations_disclaimer_present" in res.invariants_verified
        assert "executive_summary_identity_verified" in res.invariants_verified


# =========================================================================
# 2. FULL BENCHMARK SUITE & REPRODUCIBILITY TESTS
# =========================================================================

def test_full_campaign_benchmark_suite_execution(terrain_grid: TerrainGrid):
    """Executes the complete 8-scenario benchmark suite and validates against JSON Schema Draft 2020-12."""
    suite_res = run_campaign_benchmark_suite(terrain=terrain_grid, verify_reproducibility=True)

    assert suite_res.total_scenarios == 8
    assert suite_res.passed_scenarios == 8
    assert suite_res.failed_scenarios == 0
    assert suite_res.total_candidates_evaluated > 0
    assert suite_res.execution_time_s > 0.0
    assert suite_res.reproducibility_verified is True
    assert suite_res.limitations_disclaimer == BENCHMARK_SUITE_DISCLAIMER

    # Validate against schema
    is_valid, err = validate_campaign_benchmark_record(suite_res.to_dict())
    assert is_valid is True
    assert not err


def test_benchmark_reproducibility_repeat_consistency(terrain_grid: TerrainGrid):
    """Verifies repeat executions yield identical metrics with zero non-deterministic drift."""
    suite_a = run_campaign_benchmark_suite(scenarios=["BM-NORM-01", "BM-PARETO-06"], terrain=terrain_grid, verify_reproducibility=False)
    suite_b = run_campaign_benchmark_suite(scenarios=["BM-NORM-01", "BM-PARETO-06"], terrain=terrain_grid, verify_reproducibility=False)

    assert suite_a.total_scenarios == suite_b.total_scenarios
    assert suite_a.total_candidates_evaluated == suite_b.total_candidates_evaluated

    for sa, sb in zip(suite_a.scenarios, suite_b.scenarios):
        assert sa.scenario_id == sb.scenario_id
        assert sa.status == sb.status
        assert sa.candidates_evaluated == sb.candidates_evaluated
        assert sa.pareto_candidates == sb.pareto_candidates
        assert sa.infeasible_candidates == sb.infeasible_candidates


# =========================================================================
# 3. COMPLETE PLANNING-TO-ANALYSIS LIFECYCLE INTEGRATION TEST
# =========================================================================

def test_end_to_end_full_campaign_lifecycle(terrain_grid: TerrainGrid):
    """
    Exercises the complete integration path:
      1. Campaign formulation
      2. Plan baseline campaign v1
      3. Design space exploration & A* route evaluation
      4. Mathematical Pareto classification
      5. Persistence & retrieval
      6. Feasible candidate promotion -> distinct campaign v2
      7. Baseline immutability verification (v1 unchanged)
      8. Multi-unit coordination allocation
      9. Temporal execution simulation with digital twin
      10. Retrospective performance analytics & lessons learned
      11. Strict Draft 2020-12 schema validation across all stages.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1 & 2. Formulate & plan baseline campaign
        targets = [
            CampaignTarget("tgt_w0", "Octavia E. Butler Landing", 117, 157, 100.0, dwell_time_s=600.0),
            CampaignTarget("tgt_w1", "Hawksbill Gap", 119, 159, 85.0, dwell_time_s=900.0, prerequisites=["tgt_w0"]),
            CampaignTarget("tgt_w2", "Skinner Ridge", 120, 160, 75.0, dwell_time_s=900.0, prerequisites=["tgt_w1"]),
        ]
        cfg = CampaignConfig(
            planning_profile=PlanningProfile.SCIENCE_PRIORITY.value,
            max_duration_per_sortie_s=28800.0,
            max_sols=3,
        )
        base_campaign = plan_mission_campaign(
            campaign_id="cmp_lifecycle_001",
            name="Lifecycle Integration Baseline",
            config=cfg,
            targets=targets,
            terrain=terrain_grid,
        )
        base_dict = base_campaign.to_dict()
        save_campaign(base_dict, campaigns_dir=tmp_dir)

        # 3 & 4. Design space exploration and Pareto classification
        ds_res = explore_campaign_design_space(
            campaign=base_dict,
            terrain=terrain_grid,
            search_dimensions={
                "planning_profiles": ["science_priority", "time_constrained"],
                "max_durations_s": [28800.0],
                "max_sols": [3],
            },
            design_space_id="ds_lifecycle_001",
        )
        assert len(ds_res["pareto_candidates"]) >= 1

        # 5. Persist & retrieve design space evaluation
        save_design_space_evaluation(ds_res, workspace_dir=tmp_dir)
        reloaded_ds = get_design_space_evaluation("ds_lifecycle_001", workspace_dir=tmp_dir)
        assert reloaded_ds["design_space_id"] == "ds_lifecycle_001"
        validate_campaign_design_space_record(reloaded_ds)

        # 6. Promote Pareto-efficient candidate to new campaign version
        promoted_candidate = ds_res["pareto_candidates"][0]
        prom_res = promote_design_space_candidate(
            design_space_id="ds_lifecycle_001",
            candidate_id=promoted_candidate["candidate_id"],
            new_campaign_name="Lifecycle Promoted Plan v2",
            workspace_dir=tmp_dir,
        )
        new_cmp_id = prom_res["new_campaign_id"]
        assert prom_res["new_version"] == 2
        assert prom_res["promoted_candidate_id"] == promoted_candidate["candidate_id"]

        # 7. Baseline Immutability Check: v1 must remain strictly intact
        v1_check = get_campaign("cmp_lifecycle_001", campaigns_dir=tmp_dir)
        v2_check = get_campaign(new_cmp_id, campaigns_dir=tmp_dir)
        assert v1_check["version"] == 1
        assert v1_check["campaign_id"] == "cmp_lifecycle_001"
        assert v2_check["version"] == 2
        assert v2_check["parent_campaign_id"] == "cmp_lifecycle_001"

        # 8. Multi-unit coordination allocation on v2
        v2_obj = MissionCampaign.from_dict(v2_check)
        units = create_default_units(v2_obj.config)
        coord_plan = allocate_campaign_coordination(
            campaign=v2_obj,
            terrain=terrain_grid,
            units=units,
            strategy="priority_first",
        )
        assert len(coord_plan.target_allocations) >= 1

        # 9. Temporal simulation with digital twin
        twin = CampaignDigitalTwin(
            simulation_id="sim_lifecycle_001",
            campaign=v2_obj,
            coordination_plan=coord_plan,
            terrain=terrain_grid,
        )
        twin.advance(twin.total_duration_s)
        sim_data = twin.to_dict()
        assert len(sim_data["timeline_intervals"]) > 0

        # 10. Retrospective performance analytics & lessons learned
        analysis = analyze_campaign_performance(
            campaign=v2_obj,
            simulation=sim_data,
            coordination_plan=coord_plan,
        )
        assert analysis["campaign_id"] == new_cmp_id
        assert len(analysis["lessons_learned"]) >= 1
        assert "limitations_disclaimer" in analysis
        validate_campaign_analytics_record(analysis)


# =========================================================================
# 4. HARD SAFETY GATES & INVARIANT AUDIT TESTS
# =========================================================================

def test_canonical_fingerprint_determinism():
    """Verifies identical inputs produce identical fingerprints and deltas produce distinct fingerprints."""
    cfg1 = {"planning_profile": "science_priority", "max_duration_per_sortie_s": 28800.0, "max_sols": 3}
    cfg2 = {"planning_profile": "science_priority", "max_duration_per_sortie_s": 28800.0, "max_sols": 3}
    cfg3 = {"planning_profile": "time_constrained", "max_duration_per_sortie_s": 28800.0, "max_sols": 3}

    fp1 = compute_config_fingerprint(cfg1)
    fp2 = compute_config_fingerprint(cfg2)
    fp3 = compute_config_fingerprint(cfg3)

    assert fp1 == fp2
    assert fp1 != fp3
    assert len(fp1) == 64


def test_infeasible_candidate_promotion_hard_rejection():
    """Verifies that attempting to promote an infeasible candidate raises WorkspaceError."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cand_infeasible = CandidateEvaluation(
            candidate_id="cand_infeas_001",
            fingerprint="0" * 64,
            configuration={"planning_profile": "conservative"},
            status=CandidateStatus.INFEASIBLE.value,
            dominance_status=DominanceStatus.INFEASIBLE.value,
            infeasibility_reasons=["TRAVERSE_BLOCKED: slope > 35 deg"],
            objectives=CandidateObjectives(
                science_coverage_pct=0.0,
                total_duration_s=0.0,
                total_distance_m=0.0,
                unallocated_priority=100.0,
                temporal_conflicts_count=0,
                sortie_count=0,
            ),
        )

        ds_record = {
            "schema_version": "1.0.0",
            "design_space_id": "ds_infeas_test",
            "campaign_id": "cmp_infeas_test",
            "campaign_version": 1,
            "created_at_utc": "2026-10-29T12:00:00Z",
            "search_bounds": SearchBounds().to_dict(),
            "search_completeness": SearchCompleteness().to_dict(),
            "pareto_candidates": [],
            "dominated_candidates": [],
            "infeasible_candidates": [cand_infeasible.to_dict()],
            "recommendations": [],
            "limitations_disclaimer": "Test disclaimer",
        }
        save_design_space_evaluation(ds_record, workspace_dir=tmp_dir)

        with pytest.raises(WorkspaceError) as exc_info:
            promote_design_space_candidate("ds_infeas_test", "cand_infeas_001", workspace_dir=tmp_dir)
        assert exc_info.value.error_code == "ERR_CANDIDATE_INFEASIBLE"


def test_workspace_persistence_and_retrieval_benchmarks():
    """Verifies save, get, and list operations for campaign benchmark records."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dummy_record = {
            "schema_version": "1.0.0",
            "suite_id": "bench_suite_test_123",
            "timestamp_utc": "2026-10-29T12:00:00Z",
            "total_scenarios": 8,
            "passed_scenarios": 8,
            "failed_scenarios": 0,
            "total_candidates_evaluated": 22,
            "execution_time_s": 0.45,
            "scenarios": [],
            "system_environment": {
                "os": "Windows 11",
                "python_version": "3.12.4",
                "terrain_dataset": "USGS_CTX_DTM_JEZERO_20M",
            },
            "reproducibility_verified": True,
            "limitations_disclaimer": "Test disclaimer",
        }

        # Save
        saved = save_campaign_benchmark_result(dummy_record, workspace_dir=tmp_dir)
        assert saved["suite_id"] == "bench_suite_test_123"

        # Get
        retrieved = get_campaign_benchmark_result("bench_suite_test_123", workspace_dir=tmp_dir)
        assert retrieved["total_scenarios"] == 8

        # List
        summaries = list_campaign_benchmark_results(workspace_dir=tmp_dir)
        assert len(summaries) == 1
        assert summaries[0]["suite_id"] == "bench_suite_test_123"


# =========================================================================
# 5. LIVE HTTP REST API INTEGRATION TESTS (PORT 3000)
# =========================================================================

def test_live_server_preflight_and_health():
    """Verifies the live Atlas server is reachable on port 3000 and responds cleanly."""
    req = urllib.request.Request("http://127.0.0.1:3000/api/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert data.get("status") in ["online", "healthy"]
            assert "Mars" in data.get("target", "")
    except urllib.error.URLError:
        pytest.skip("Atlas server not running on port 3000")


def test_live_server_design_spaces_list():
    """Verifies GET /api/campaign/design-spaces endpoint on live Atlas server."""
    req = urllib.request.Request("http://127.0.0.1:3000/api/campaign/design-spaces", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(data, list)
    except urllib.error.URLError:
        pytest.skip("Atlas server not running on port 3000")
