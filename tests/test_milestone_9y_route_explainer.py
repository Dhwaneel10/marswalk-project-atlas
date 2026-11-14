"""
MarsWalk 2.0 — Milestone 9Y Test Suite: Route Decision Intelligence & Cost Attribution.

Verifies:
1. Exact physical step-by-step cost attribution and additive decomposition.
2. Step cost lower bound (cost >= distance).
3. Route segment uniform decomposition and contiguous step coverage.
4. Route cost reconciliation ledger proving sum(segment_distances) == total_distance and sum(segment_costs) == total_cost.
5. Component sums reconciliation to total cost.
6. Non-additive properties explicit disclosure.
7. Top-K highest-cost bottleneck ranking with mitigation hints.
8. Dominant cost factor classification.
9. Terrain difficulty rating thresholds.
10. Multi-stop leg boundary alignment.
11. Contingency multiplier attribution and isolation.
12. Decision rationale generation and hazards avoided.
13. Route comparison deltas and divergence/convergence step tracking.
14. Trivial single-point stay handling without division by zero.
15. JSON Schema Draft 2020-12 compliance for route-explanation-response.
16. Live HTTP /api/route/explain integration test.
"""

import math
import os
import json
import urllib.request
import numpy as np
import pytest

from marswalk.core.terrain import (
    TerrainGrid,
    TerrainConfig,
    calculate_step_distance,
    calculate_edge_cost,
    load_and_process_terrain,
    get_profile_terrain_config,
)
from marswalk.core.planner import (
    RouteResult,
    LegResult,
    plan_route,
    plan_sequential_multistop_route,
    PlannerConfig,
)
from marswalk.core.route_explainer import (
    CostFactor,
    TerrainDifficulty,
    StepAttribution,
    RouteSegmentExplanation,
    HighestCostSegment,
    RouteCostLedger,
    RouteComparisonExplanation,
    RouteExplanationResult,
    compute_step_attributions,
    decompose_route_segments,
    reconcile_route_cost_ledger,
    rank_highest_cost_segments,
    generate_decision_rationale,
    compare_routes_explained,
    explain_route,
)
from marswalk.api.contracts import validate_contract


# Path to real Jezero Crater CTX 20m DTM
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEZERO_DTM_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "jezero_ready_20m.tif")


@pytest.fixture(scope="module")
def terrain_grid():
    """Load authentic Jezero Crater 20m DTM."""
    assert os.path.isfile(JEZERO_DTM_PATH), f"DTM not found at {JEZERO_DTM_PATH}"
    return load_and_process_terrain(JEZERO_DTM_PATH)


class TestRouteStepAttribution:
    """Verifies step-by-step physical calculations and exact additive decomposition."""

    def test_step_attributions_exact_additive_decomposition(self, terrain_grid):
        """Verify that every step's cost decomposes additively into its physical components."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        assert route.is_reachable
        assert len(route.path) >= 5

        steps = compute_step_attributions(
            path=route.path,
            terrain=terrain_grid,
            terrain_config=terrain_grid.config,
        )
        assert len(steps) == len(route.path) - 1

        for s in steps:
            sum_components = (
                s.base_distance_cost_m
                + s.slope_cost_m
                + s.roughness_cost_m
                + s.uphill_cost_m
                + s.contingency_cost_m
            )
            assert math.isclose(sum_components, s.cost_m, rel_tol=1e-6, abs_tol=1e-6), (
                f"Step {s.step_index}: component sum {sum_components} != cost {s.cost_m}"
            )

    def test_step_cost_exceeds_or_equals_distance(self, terrain_grid):
        """Verify that for non-negative penalty weights, step cost is at least step ground distance."""
        route = plan_route(
            start_rc=(110, 110),
            goal_rc=(125, 125),
            terrain=terrain_grid,
            config=PlannerConfig(profile="balanced"),
        )
        assert route.is_reachable

        steps = compute_step_attributions(
            path=route.path,
            terrain=terrain_grid,
            terrain_config=terrain_grid.config,
        )
        for s in steps:
            assert s.cost_m >= s.distance_m - 1e-9, f"Step cost {s.cost_m} < distance {s.distance_m}"


class TestSegmentDecompositionAndLedger:
    """Verifies segment partitioning and exact reconciliation ledger."""

    def test_route_segments_uniform_decomposition(self, terrain_grid):
        """Verify that 10-segment uniform decomposition covers all steps contiguously."""
        route = plan_route(
            start_rc=(100, 100),
            goal_rc=(140, 140),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        assert route.is_reachable
        total_steps = len(route.path) - 1

        steps = compute_step_attributions(route.path, terrain_grid)
        segments = decompose_route_segments(
            path=route.path,
            step_attributions=steps,
            terrain=terrain_grid,
            num_aggregated_segments=10,
        )

        assert len(segments) == min(10, total_steps)
        # Check contiguous slice coverage
        prev_end = 0
        for idx, seg in enumerate(segments):
            assert seg.start_step_index == prev_end
            assert seg.end_step_index > seg.start_step_index
            assert seg.num_steps == (seg.end_step_index - seg.start_step_index)
            prev_end = seg.end_step_index

        assert prev_end == total_steps

    def test_reconciliation_ledger_exact_sums(self, terrain_grid):
        """Verify that segment sums strictly reconcile to total route distance and cost."""
        route = plan_route(
            start_rc=(115, 115),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid, num_aggregated_segments=8)
        ledger = exp.reconciliation_ledger

        assert ledger.is_reconciled is True
        assert ledger.distance_delta_m <= 0.05
        assert ledger.cost_delta_m <= 0.05
        assert ledger.component_delta_m <= 0.05
        assert math.isclose(ledger.sum_segment_distances_m, route.distance_m, rel_tol=1e-5)
        assert math.isclose(ledger.sum_segment_costs_m, route.cost, rel_tol=1e-5)

    def test_component_sums_reconcile_to_total_cost(self, terrain_grid):
        """Verify that base_distance + slope + roughness + uphill + contingency == total_cost."""
        route = plan_route(
            start_rc=(120, 110),
            goal_rc=(140, 130),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid)
        ledger = exp.reconciliation_ledger

        comp_sum = sum(ledger.component_sums_m.values())
        assert math.isclose(comp_sum, ledger.total_cost_m, rel_tol=1e-5)

    def test_non_additive_properties_flagged_in_ledger(self, terrain_grid):
        """Verify that non-additive extrema (max slope, elevation bounds) are reported with clear disclosure."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid)
        non_add = exp.reconciliation_ledger.non_additive_properties

        assert "max_slope_deg" in non_add
        assert "mean_slope_deg" in non_add
        assert "cost_density_ratio" in non_add
        assert "disclosure" in non_add
        assert "non-additive" in non_add["disclosure"].lower()


class TestBottlenecksAndAttributionClassification:
    """Verifies ranking of bottlenecks, dominant factor classification, and difficulty ratings."""

    def test_highest_cost_segments_ranking(self, terrain_grid):
        """Verify top-3 bottleneck ranking orders by cost and includes operational impact."""
        route = plan_route(
            start_rc=(100, 100),
            goal_rc=(140, 140),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid, num_aggregated_segments=10)
        top3 = exp.highest_cost_segments

        assert len(top3) <= 3
        assert len(top3) > 0
        assert top3[0].rank == 1
        # Primary sort is descending cost
        for i in range(len(top3) - 1):
            assert top3[i].cost_m >= top3[i + 1].cost_m

        for h in top3:
            assert len(h.operational_impact) > 10
            assert len(h.mitigation_hint) > 10

    def test_dominant_cost_factor_classification(self, terrain_grid):
        """Verify that segments classify dominant cost factors appropriately."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid)
        valid_factors = {f.value for f in CostFactor}

        for seg in exp.segments:
            assert seg.dominant_cost_factor in valid_factors

    def test_difficulty_rating_thresholds(self, terrain_grid):
        """Verify that difficulty ratings match cost density thresholds."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid)

        for seg in exp.segments:
            if seg.cost_density < 1.3:
                assert seg.terrain_difficulty_rating == TerrainDifficulty.NOMINAL.value
            elif seg.cost_density < 2.0:
                assert seg.terrain_difficulty_rating == TerrainDifficulty.MODERATE.value
            elif seg.cost_density < 3.5:
                assert seg.terrain_difficulty_rating == TerrainDifficulty.CHALLENGING.value
            else:
                assert seg.terrain_difficulty_rating == TerrainDifficulty.SEVERE.value


class TestMultiStopAndContingencyAttribution:
    """Verifies leg boundary alignment and contingency multiplier attribution."""

    def test_multi_stop_leg_boundary_alignment(self, terrain_grid):
        """Verify that multi-stop routes partition segments cleanly along intermediate waypoints."""
        ordered_points = [(120, 120), (125, 128), (135, 135)]
        route = plan_sequential_multistop_route(
            ordered_points=ordered_points,
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        assert route.is_reachable
        assert route.legs is not None
        assert len(route.legs) == 2

        exp = explain_route(route, terrain_grid)
        # Segments must match the 2 legs
        assert len(exp.segments) == 2
        assert "Leg 1" in exp.segments[0].leg_id
        assert "Leg 2" in exp.segments[1].leg_id
        assert exp.reconciliation_ledger.is_reconciled is True

    def test_contingency_cost_multiplier_attribution(self, terrain_grid):
        """Verify that terrain cost multiplier is captured as contingency_cost_m in step attribution."""
        H, W = terrain_grid.shape
        mult_mask = np.ones((H, W), dtype=np.float32)
        # Apply 2.5x multiplier over middle quadrant
        mult_mask[122:128, 122:128] = 2.5

        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            cost_multiplier_mask=mult_mask,
        )
        assert route.is_reachable

        exp = explain_route(
            route=route,
            terrain=terrain_grid,
            cost_multiplier_mask=mult_mask,
        )

        assert exp.reconciliation_ledger.is_reconciled is True
        # If the path traversed through multiplier cells, contingency_multiplier cost > 0
        comp_sums = exp.reconciliation_ledger.component_sums_m
        if any(mult_mask[r, c] > 1.0 for r, c in route.path):
            assert comp_sums["contingency_multiplier"] > 0.0


class TestDecisionRationaleAndComparison:
    """Verifies decision rationale generation and route comparison trade-offs."""

    def test_decision_rationale_avoided_hazards(self, terrain_grid):
        """Verify decision rationale documents slope cutoffs and hazards avoided."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid)
        dr = exp.decision_rationale

        assert "objective_description" in dr
        assert "hazards_avoided" in dr
        assert len(dr["hazards_avoided"]) >= 2
        assert any("slope" in h.lower() for h in dr["hazards_avoided"])

    def test_route_comparison_deltas(self, terrain_grid):
        """Verify comparison of two routes accurately captures deltas, divergence, and convergence."""
        ref_route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )

        # Alternative with obstacle
        H, W = terrain_grid.shape
        blocked = np.zeros((H, W), dtype=bool)
        # Block middle of ref path
        mid_pt = ref_route.path[len(ref_route.path) // 2]
        blocked[mid_pt[0] - 1 : mid_pt[0] + 2, mid_pt[1] - 1 : mid_pt[1] + 2] = True

        alt_route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
            blocked_mask=blocked,
        )
        assert alt_route.is_reachable

        exp = explain_route(
            route=ref_route,
            terrain=terrain_grid,
            alternative_route=alt_route,
            reference_title="Baseline Route",
            alternative_title="Detour Route",
        )

        assert exp.comparison is not None
        comp = exp.comparison
        assert comp.reference_title == "Baseline Route"
        assert comp.alternative_title == "Detour Route"
        assert comp.divergence_step_index is not None
        assert comp.divergence_step_index > 0
        assert len(comp.tradeoff_verdict) > 10

    def test_trivial_single_point_path(self, terrain_grid):
        """Verify single-cell path does not divide by zero and returns a reconciled zero-cost explanation."""
        trivial_route = RouteResult(
            profile="conservative",
            start_rc=(120, 120),
            goal_rc=(120, 120),
            path=[(120, 120)],
            distance_m=0.0,
            cost=0.0,
            science_score=0.0,
            visited_waypoint_ids=[],
            num_cells=1,
            num_steps=0,
            is_reachable=True,
            is_budget_feasible=True,
            max_distance_m=None,
            status_message="Trivial path",
        )
        exp = explain_route(trivial_route, terrain_grid)
        assert exp.total_distance_m == 0.0
        assert exp.total_cost_m == 0.0
        assert exp.cost_density_ratio == 1.0
        assert exp.reconciliation_ledger.is_reconciled is True


class TestContractAndLiveAPI:
    """Verifies Draft 2020-12 schema validation and live HTTP endpoint integration."""

    def test_route_explanation_response_schema_conformance(self, terrain_grid):
        """Verify that explanation output dictionary validates strictly against JSON Schema."""
        route = plan_route(
            start_rc=(120, 120),
            goal_rc=(135, 135),
            terrain=terrain_grid,
            config=PlannerConfig(profile="conservative"),
        )
        exp = explain_route(route, terrain_grid, num_aggregated_segments=5)
        res_dict = exp.to_dict()

        is_valid, errors = validate_contract(res_dict, "route-explanation-response", raise_on_error=False)
        assert is_valid is True, f"Schema validation errors: {errors}"

    def test_live_http_route_explain_api(self):
        """Verify live POST /api/route/explain endpoint on local server."""
        payload = {
            "start": {"row": 120, "col": 120},
            "goal": {"row": 135, "col": 135},
            "profile": "conservative",
            "num_segments": 5,
        }
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:3000/api/route/explain",
            data=req_data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            assert response.status == 200
            data = json.loads(response.read().decode("utf-8"))

        assert data.get("status") == "success"
        assert "total_distance_m" in data
        assert "total_cost_m" in data
        assert len(data.get("segments", [])) == 5
        assert len(data.get("highest_cost_segments", [])) >= 1
        ledger = data.get("reconciliation_ledger", {})
        assert ledger.get("is_reconciled") is True
        assert ledger.get("distance_delta_m") <= 0.05
        assert ledger.get("cost_delta_m") <= 0.05
