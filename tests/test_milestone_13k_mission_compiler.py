"""
MarsWalk 2.0 / Project Atlas — Milestone 13K Test Battery
=========================================================
Tests the Goal-Driven Mission Design Compiler end-to-end:
- Intent specification and cryptographic fingerprinting
- Remote sensing boundary and instrument catalog validation
- Goal decomposition into Directed Acyclic Task Graphs
- Hard vs soft constraint evaluation and conflict core isolation
- Hierarchical multi-level synthesis of 8 Pareto candidates
- 6-dimensional performance evaluation and trade-off comparison
- Forensic failure chain diagnostics and 1-click relaxation
- 6-scenario benchmark suite execution
- JSON Schema Draft 2020-12 contract compliance
- API service integration
"""

import copy
import pytest
from typing import Dict, Any

from marswalk.core.mission_intent import (
    MissionIntent,
    ScienceObjectiveCategory,
    MissionPlanningMode,
    create_sample_jezero_mission_intent,
)
from marswalk.core.mission_intent_validator import (
    MissionIntentValidator,
    ValidationVerdict,
)
from marswalk.core.mission_goal_compiler import (
    MissionGoalCompiler,
    MissionTaskGraph,
    MissionTaskNode,
    MissionTaskType,
    MissionTaskStatus,
)
from marswalk.core.mission_constraint_engine import (
    MissionConstraintEngine,
    ConstraintType,
    ConstraintCategory,
    ConstraintSeverity,
)
from marswalk.core.mission_plan_solver import (
    HierarchicalMissionPlanSolver,
    MissionPlanCandidate,
    MissionCompilationResult,
)
from marswalk.core.mission_plan_evaluator import (
    MissionPlanEvaluator,
    PlanEvaluationMetrics,
)
from marswalk.core.plan_compilation_debugger import (
    PlanCompilationDebugger,
    PlanCompilationDebugReport,
)
from marswalk.core.mission_planning_benchmark import (
    MissionPlanningBenchmarkSuite,
)
from marswalk.api.contracts import validate_contract
from marswalk.api.service import (
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
)


class TestMilestone13KMissionCompiler:
    """Comprehensive test battery for Milestone 13K Compiler capabilities."""

    def test_mission_intent_creation_and_fingerprint(self):
        """Verifies intent creation, determinism of cryptographic fingerprints, and serialization."""
        intent = create_sample_jezero_mission_intent()
        fp1 = intent.compute_fingerprint()
        fp2 = intent.compute_fingerprint()
        assert fp1 == fp2, "Fingerprint must be strictly deterministic"
        assert len(fp1) == 64, "SHA-256 fingerprint must be 64 hex characters"

        as_dict = intent.to_dict()
        assert as_dict["name"] == intent.name
        assert as_dict["fingerprint"] == fp1
        assert len(as_dict["science"]["mandatory_target_ids"]) >= 2

        restored = MissionIntent.from_dict(as_dict)
        assert restored.compute_fingerprint() == fp1
        assert restored.science.minimum_observations_count == intent.science.minimum_observations_count

    def test_mission_intent_validator_valid(self):
        """Verifies that calibrated mission intent passes validation with VALID verdict."""
        intent = create_sample_jezero_mission_intent()
        validator = MissionIntentValidator()
        report = validator.validate_intent(intent)
        assert report.verdict in (ValidationVerdict.VALID.value, ValidationVerdict.VALID_WITH_WARNINGS.value)
        assert report.total_errors == 0
        assert report.normalized_intent is not None

    def test_mission_intent_validator_rejects_impossible(self):
        """Verifies rejection of impossible coordinates, slope bounds, or unknown instruments."""
        intent = create_sample_jezero_mission_intent()
        # Out of bounds coordinates
        intent.geography.starting_location_rc = (999, 999)
        # Impossible slope limit
        intent.geography.maximum_slope_limit_deg = 95.0
        # Unknown instrument
        intent.science.required_instruments = ["NON_EXISTENT_SPECTROMETER_3000"]

        validator = MissionIntentValidator(terrain_shape=(250, 250))
        report = validator.validate_intent(intent)
        assert report.verdict == ValidationVerdict.INVALID.value
        assert report.total_errors >= 2
        issue_codes = [i.issue_code for i in report.issues]
        assert "ERR_OUT_OF_BOUNDS_START_COORDINATES" in issue_codes
        assert "ERR_INVALID_SLOPE_LIMIT" in issue_codes

    def test_mission_goal_compiler_decomposition(self):
        """Decomposes intent into a valid Directed Acyclic Task Graph and verifies critical path."""
        intent = create_sample_jezero_mission_intent()
        compiler = MissionGoalCompiler()
        graph = compiler.decompose_mission_intent(intent)

        assert graph.total_tasks_count > 0
        assert len(graph.edges) > 0
        assert graph.validate_acyclic() is True
        assert len(graph.root_task_ids) > 0
        assert len(graph.terminal_task_ids) > 0

        # Check critical path
        crit_path = graph.get_critical_path()
        assert len(crit_path) > 0
        assert crit_path[0] in graph.tasks
        assert crit_path[-1] in graph.tasks

        # Verify task types present
        task_types = {t.task_type for t in graph.tasks.values()}
        assert MissionTaskType.TRAVERSE.value in task_types
        assert MissionTaskType.OBSERVE.value in task_types
        assert MissionTaskType.CAMPAIGN_CHECKPOINT.value in task_types
        assert MissionTaskType.SIMULATED_DATA_TRANSFER.value in task_types

    def test_mission_goal_compiler_topological_sort_and_cycle_detection(self):
        """Verifies topological sorting and cycle detection exception."""
        graph = MissionTaskGraph(graph_id="test_dag", intent_id="test_intent")
        n1 = MissionTaskNode(task_id="T1", task_type="TRAVERSE", name="T1", parent_goal_id="g1")
        n2 = MissionTaskNode(task_id="T2", task_type="OBSERVE", name="T2", parent_goal_id="g1", prerequisite_task_ids=["T1"])
        graph.add_task(n1)
        graph.add_task(n2)

        topo = graph.topological_sort()
        assert topo == ["T1", "T2"]

        # Introduce cyclic dependency: T1 depends on T2
        graph.edges.append(("T2", "T1"))
        assert graph.validate_acyclic() is False
        with pytest.raises(ValueError, match="cyclic dependencies"):
            graph.topological_sort()

    def test_mission_constraint_engine_hard_vs_soft(self):
        """Verifies hard physical constraints and soft preference evaluations."""
        intent = create_sample_jezero_mission_intent()
        compiler = MissionGoalCompiler()
        graph = compiler.decompose_mission_intent(intent)

        engine = MissionConstraintEngine()
        report = engine.evaluate_task_graph_constraints(intent, graph)
        assert report.is_feasible is True
        assert report.hard_constraints_violated == 0
        assert report.hard_constraints_satisfied >= 5

        # Verify constraint categories
        categories = {c.category for c in report.constraints}
        assert ConstraintCategory.ENERGY.value in categories
        assert ConstraintCategory.STORAGE.value in categories
        assert ConstraintCategory.COMMUNICATIONS.value in categories
        assert ConstraintCategory.DEPENDENCY.value in categories

    def test_mission_constraint_engine_conflict_core_extraction(self):
        """Verifies extraction of Irreducible Inconsistent Subsets (Conflict Cores) on infeasible intent."""
        intent = create_sample_jezero_mission_intent()
        # Set impossible battery reserve
        intent.resources.minimum_battery_reserve_pct = 95.0

        compiler = MissionGoalCompiler()
        graph = compiler.decompose_mission_intent(intent)

        engine = MissionConstraintEngine()
        report = engine.evaluate_task_graph_constraints(intent, graph)
        assert report.is_feasible is False
        assert report.hard_constraints_violated >= 1
        assert len(report.conflict_cores) >= 1

        core = report.conflict_cores[0]
        assert "Battery Reserve" in core.summary
        assert len(core.minimal_relaxation_suggestions) >= 1

    def test_hierarchical_solver_portfolio_synthesis(self):
        """Verifies synthesis of 8 structurally distinct candidates, deduplication, and Pareto extraction."""
        intent = create_sample_jezero_mission_intent()
        solver = HierarchicalMissionPlanSolver()
        result = solver.compile_mission_portfolio(intent)

        assert result.status == "SUCCESS"
        assert len(result.candidates) == 8
        assert result.total_candidates == 8
        assert len(result.pareto_frontier_ids) >= 1
        assert result.recommended_candidate_id in [c.candidate_id for c in result.candidates]

        # Verify unique postures
        postures = {c.posture for c in result.candidates}
        assert MissionPlanningMode.BALANCED.value in postures
        assert MissionPlanningMode.SCIENCE_MAXIMIZING.value in postures
        assert MissionPlanningMode.ENERGY_EFFICIENT.value in postures
        assert MissionPlanningMode.COMMUNICATIONS_FOCUSED.value in postures
        assert MissionPlanningMode.MINIMUM_DURATION.value in postures
        assert MissionPlanningMode.ROBUSTNESS_FOCUSED.value in postures
        assert MissionPlanningMode.MINIMUM_INFRASTRUCTURE.value in postures
        assert MissionPlanningMode.DATA_RETURN_FOCUSED.value in postures

        # Verify fingerprints are distinct
        fingerprints = {c.compute_fingerprint() for c in result.candidates}
        assert len(fingerprints) == 8, "All 8 candidates must have unique fingerprints"

    def test_plan_evaluator_tradeoffs_and_ranking(self):
        """Verifies 6-dimensional candidate evaluation and pairwise comparative matrix."""
        intent = create_sample_jezero_mission_intent()
        solver = HierarchicalMissionPlanSolver()
        result = solver.compile_mission_portfolio(intent)

        evaluator = MissionPlanEvaluator()
        metrics = evaluator.evaluate_candidates(intent, result.candidates)
        assert len(metrics) == 8
        assert metrics[0].rank == 1
        assert metrics[0].weighted_composite_score >= metrics[-1].weighted_composite_score

        # Pairwise comparison
        base = result.candidates[0]
        target = result.candidates[1]
        delta_matrix = evaluator.compare_candidates(base, target)
        assert delta_matrix.base_candidate_id == base.candidate_id
        assert delta_matrix.target_candidate_id == target.candidate_id
        assert isinstance(delta_matrix.tradeoff_summary, str)
        assert len(delta_matrix.tradeoff_summary) > 10

    def test_plan_compilation_debugger_and_relaxation(self):
        """Verifies causal failure chain tracing and 1-click relaxation application."""
        intent = create_sample_jezero_mission_intent()
        intent.resources.minimum_battery_reserve_pct = 95.0

        compiler = MissionGoalCompiler()
        graph = compiler.decompose_mission_intent(intent)
        engine = MissionConstraintEngine()
        report = engine.evaluate_task_graph_constraints(intent, graph)

        debugger = PlanCompilationDebugger()
        debug_report = debugger.diagnose_compilation(intent, report)
        assert debug_report.is_feasible is False
        assert len(debug_report.failure_chain) >= 2
        assert len(debug_report.relaxation_options) >= 1

        # Apply relaxation
        opt = debug_report.relaxation_options[0]
        revised_intent = debugger.apply_relaxation(intent, opt)
        assert revised_intent.version > intent.version
        assert revised_intent.resources.minimum_battery_reserve_pct < 95.0

    def test_planning_benchmark_suite(self):
        """Executes full 6-scenario benchmark suite across Campaigns A through F."""
        bench = MissionPlanningBenchmarkSuite()
        runs, summary = bench.run_benchmark_suite()
        assert len(runs) == 6
        assert summary.total_scenarios == 6
        assert summary.compiler_feasibility_rate_pct > 80.0
        assert summary.total_pareto_candidates_synthesized >= 20
        assert summary.total_conflict_cores_isolated >= 1  # From Scenario F
        assert summary.mean_compiler_latency_ms < 500.0   # Fast sub-second compilation

    def test_draft_2020_12_schema_compliance(self):
        """Verifies all emitted payloads strictly validate against registered Draft 2020-12 schemas."""
        intent = create_sample_jezero_mission_intent()
        val_ok, errors = validate_contract(intent.to_dict(), "mission-intent")
        assert val_ok is True, f"Intent schema errors: {errors}"

        validator = MissionIntentValidator()
        v_rep = validator.validate_intent(intent)
        val_ok, errors = validate_contract(v_rep.to_dict(), "mission-intent-validation")
        assert val_ok is True, f"Validation report errors: {errors}"

        compiler = MissionGoalCompiler()
        graph = compiler.decompose_mission_intent(intent)
        val_ok, errors = validate_contract(graph.to_dict(), "mission-task-graph")
        assert val_ok is True, f"Task graph errors: {errors}"

        solver = HierarchicalMissionPlanSolver()
        comp = solver.compile_mission_portfolio(intent)
        val_ok, errors = validate_contract(comp.to_dict(), "mission-plan-compilation")
        assert val_ok is True, f"Compilation errors: {errors}"

        cand = comp.candidates[0]
        val_ok, errors = validate_contract(cand.to_dict(), "mission-plan-candidate")
        assert val_ok is True, f"Candidate errors: {errors}"

        debugger = PlanCompilationDebugger()
        dbg = debugger.diagnose_compilation(intent, cand.constraint_report)
        val_ok, errors = validate_contract(dbg.to_dict(), "mission-constraint-diagnosis")
        assert val_ok is True, f"Diagnosis errors: {errors}"

    def test_api_service_endpoints(self):
        """Verifies all Milestone 13K API service handlers return expected payloads."""
        # 1. Sample API
        sample = mission_intent_sample_api()
        assert sample["intent_id"] is not None

        # 2. Validate API
        val_res = mission_intent_validate_api({"intent": sample})
        assert val_res["verdict"] in ("VALID", "VALID_WITH_WARNINGS")

        # 3. Normalize API
        norm_res = mission_intent_normalize_api({"intent": sample})
        assert norm_res["status"] == "NORMALIZED"

        # 4. Compile API
        comp_res = mission_plan_compile_api({"intent": sample})
        assert comp_res["status"] == "SUCCESS"
        assert comp_res["total_candidates"] == 8

        # 5. Evaluate API
        eval_res = mission_plan_evaluate_api({"compilation_id": comp_res["compilation_id"]})
        assert eval_res["total_evaluated"] == 8

        # 6. Compare API
        comp_id = comp_res["compilation_id"]
        cands = comp_res["candidates"]
        comp_delta = mission_plan_compare_api({
            "compilation_id": comp_id,
            "base_candidate_id": cands[0]["candidate_id"],
            "target_candidate_id": cands[1]["candidate_id"],
        })
        assert "utility_delta_pts" in comp_delta

        # 7. Get API
        get_res = mission_plan_get_api({"compilation_id": comp_id})
        assert get_res["compilation_id"] == comp_id

        # 8. Debugger API
        dbg_res = mission_plan_debugger_api({"intent": sample})
        assert dbg_res["intent_id"] is not None

        # 9. Benchmark API
        bench_res = mission_plan_benchmark_api()
        assert bench_res["summary"]["total_scenarios"] == 6

        # 10. Promote API
        prom_res = mission_plan_promote_api({
            "compilation_id": comp_id,
            "candidate_id": comp_res["recommended_candidate_id"],
        })
        assert prom_res["status"] == "PROMOTED_TO_CAMPAIGN"
