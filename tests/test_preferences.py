"""
Automated unit and integration tests for MarsWalk Mission Commander AI (Milestone 6).
Covers TC-01 through TC-16 specified in Milestone 6 instructions.
"""

import math
import os
import tempfile
import pytest
import numpy as np

from marswalk.core.terrain import TerrainConfig, derive_terrain_from_array, load_and_process_terrain
from marswalk.core.planner import PlannerConfig, ScienceWaypoint, RouteResult, plan_route
from marswalk.core.stress_test import (
    DisruptionType,
    ScenarioDefinition,
    run_scenario,
)
from marswalk.core.preferences import (
    FEATURE_NAMES,
    MIN_FEEDBACK_THRESHOLD,
    LearningState,
    RouteFeatures,
    CandidateOption,
    PreferenceObservation,
    RankedRoute,
    PreferenceModel,
    extract_route_features,
    create_choice_id,
    load_preference_model,
    save_preference_model,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


# ==============================================================================
# TC-01: Valid and Invalid Route-Feature Inputs
# ==============================================================================
def test_tc_01_feature_extraction_and_bounds():
    """
    TC-01: Extract features from valid and empty/unreachable route results.
    Verify non-negative, finite numbers and graceful handling.
    """
    valid_route = RouteResult(
        profile="science_first",
        start_rc=(10, 10),
        goal_rc=(20, 20),
        path=[(10, 10), (15, 15), (20, 20)],
        distance_m=1450.5,
        cost=1820.0,
        science_score=120.0,
        visited_waypoint_ids=["w1", "w2"],
        num_cells=3,
        num_steps=2,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=5000.0,
        status_message="ok",
    )

    elev = np.zeros((30, 30), dtype=np.float32)
    elev[15, 15] = 50.0
    elev[20, 20] = 75.0
    grid = derive_terrain_from_array(elev, TerrainConfig())

    feats = extract_route_features(valid_route, terrain=grid)
    assert feats.distance_m == 1450.5
    assert feats.cost == 1820.0
    assert feats.science_score == 120.0
    assert feats.elevation_gain_m == 75.0  # (0 -> 50) + (50 -> 75)

    # Empty / Unreachable Route
    unreachable = RouteResult(
        profile="conservative",
        start_rc=(0, 0),
        goal_rc=(10, 10),
        path=[],
        distance_m=0.0,
        cost=float("inf"),
        science_score=0.0,
        visited_waypoint_ids=[],
        num_cells=0,
        num_steps=0,
        is_reachable=False,
        is_budget_feasible=False,
        max_distance_m=None,
        status_message="unreachable",
    )
    feats_unreach = extract_route_features(unreachable, terrain=grid)
    assert feats_unreach.distance_m == 0.0
    assert feats_unreach.cost == 0.0
    assert feats_unreach.science_score == 0.0
    assert feats_unreach.elevation_gain_m == 0.0


# ==============================================================================
# TC-02: Feature Normalization and Numerical Stability
# ==============================================================================
def test_tc_02_feature_normalization():
    """
    TC-02: Verify normalized vectors remain strictly bounded within [0.0, 2.0]
    even with extreme inputs or zero reference denominators.
    """
    extreme_feats = RouteFeatures(
        distance_m=999999.0,
        cost=999999.0,
        science_score=999999.0,
        elevation_gain_m=999999.0,
    )
    norm = extreme_feats.to_normalized_vector()
    assert np.all(norm <= 2.0)
    assert np.all(norm >= 0.0)

    # Zero/negative edge cases
    zero_feats = RouteFeatures(
        distance_m=-10.0,
        cost=0.0,
        science_score=0.0,
        elevation_gain_m=-5.0,
    )
    norm_zero = zero_feats.to_normalized_vector(d_scale=0.0, c_scale=-10.0)
    assert np.all(norm_zero >= 0.0)
    assert np.all(np.isfinite(norm_zero))


# ==============================================================================
# TC-03: Training on Controlled Synthetic Pairwise Preferences
# ==============================================================================
def test_tc_03_synthetic_pairwise_training():
    """
    TC-03: Train on controlled synthetic observations where Route A (high science)
    is repeatedly preferred over Route B (low science, shorter distance).
    Verify that learned science weight becomes strictly positive.
    """
    model = PreferenceModel(l2_reg=0.1)

    opt_sci = CandidateOption(
        profile="science_first",
        features=RouteFeatures(distance_m=4000.0, cost=5000.0, science_score=200.0, elevation_gain_m=100.0),
    )
    opt_cons = CandidateOption(
        profile="conservative",
        features=RouteFeatures(distance_m=2000.0, cost=2200.0, science_score=0.0, elevation_gain_m=30.0),
    )

    for i in range(4):
        obs = PreferenceObservation(
            choice_id=f"synth_{i}",
            timestamp="2026-10-17T00:00:00Z",
            selected_profile=opt_sci.profile,
            selected_features=opt_sci.features,
            rejected_candidates=[opt_cons],
        )
        assert model.add_observation(obs) is True

    assert model.get_state() == LearningState.PERSONALIZED
    w = model.weights
    # Feature 2 is norm_science
    assert w[2] > 0.1, f"Science weight should be positive, got {w[2]}"


# ==============================================================================
# TC-04: Distance Aversion Preference Ordering
# ==============================================================================
def test_tc_04_distance_aversion_preference():
    """
    TC-04: Train on observations where Conservative (short distance) is repeatedly
    preferred over Science-First (long detour).
    Verify that predicted utility for Conservative exceeds Science-First.
    """
    model = PreferenceModel(l2_reg=0.2)

    feat_short = RouteFeatures(distance_m=1500.0, cost=1600.0, science_score=20.0, elevation_gain_m=10.0)
    feat_long = RouteFeatures(distance_m=6000.0, cost=8000.0, science_score=150.0, elevation_gain_m=120.0)

    for i in range(3):
        obs = PreferenceObservation(
            choice_id=f"short_pref_{i}",
            timestamp="2026-10-17T00:00:00Z",
            selected_profile="conservative",
            selected_features=feat_short,
            rejected_candidates=[CandidateOption(profile="science_first", features=feat_long)],
        )
        model.add_observation(obs)

    u_short = model.predict_utility(feat_short)
    u_long = model.predict_utility(feat_long)
    assert u_short > u_long, f"Expected short utility ({u_short}) > long utility ({u_long})"


# ==============================================================================
# TC-05: Insufficient-Data Lifecycle States
# ==============================================================================
def test_tc_05_learning_lifecycle_states():
    """
    TC-05: Verify exact state transitions:
    0 choices -> UNTRAINED
    1..2 choices -> COLLECTING_INITIAL
    >= 3 choices -> PERSONALIZED
    """
    model = PreferenceModel()
    assert model.get_state() == LearningState.UNTRAINED

    f1 = RouteFeatures(1000.0, 1000.0, 50.0, 10.0)
    f2 = RouteFeatures(2000.0, 2000.0, 100.0, 20.0)

    obs1 = PreferenceObservation("c1", "t", "p1", f1, [CandidateOption("p2", f2)])
    model.add_observation(obs1)
    assert model.get_state() == LearningState.COLLECTING_INITIAL

    obs2 = PreferenceObservation("c2", "t", "p1", f1, [CandidateOption("p2", f2)])
    model.add_observation(obs2)
    assert model.get_state() == LearningState.COLLECTING_INITIAL

    obs3 = PreferenceObservation("c3", "t", "p1", f1, [CandidateOption("p2", f2)])
    model.add_observation(obs3)
    assert model.get_state() == LearningState.PERSONALIZED


# ==============================================================================
# TC-06: Persistence and Reproducible Restoration
# ==============================================================================
def test_tc_06_persistence_and_restoration():
    """
    TC-06: Save model with observations and weights to JSON, load it back,
    and verify bitwise identical weights, observations, and predicted utility.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "user_preferences.json")

        model = PreferenceModel()
        f1 = RouteFeatures(1500.0, 1800.0, 75.0, 25.0)
        f2 = RouteFeatures(3500.0, 4200.0, 150.0, 80.0)

        for i in range(3):
            model.add_observation(
                PreferenceObservation(
                    choice_id=f"choice_{i}",
                    timestamp="2026-10-17T01:00:00Z",
                    selected_profile="balanced",
                    selected_features=f1,
                    rejected_candidates=[CandidateOption(profile="science_first", features=f2)],
                )
            )

        weights_before = model.weights.copy()
        u_before = model.predict_utility(f1)

        assert save_preference_model(model, json_path) is True
        assert os.path.exists(json_path)

        loaded = load_preference_model(json_path)
        assert loaded.get_state() == LearningState.PERSONALIZED
        assert len(loaded.observations) == 3
        np.testing.assert_allclose(loaded.weights, weights_before, rtol=1e-5)
        assert pytest.approx(loaded.predict_utility(f1), abs=1e-5) == u_before


# ==============================================================================
# TC-07: Corrupted or Incompatible File Handling
# ==============================================================================
def test_tc_07_corrupted_file_handling():
    """
    TC-07: Verify load_preference_model falls back to an empty UNTRAINED model
    when encountering missing, malformed, or invalid schema JSON files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_json = os.path.join(tmpdir, "corrupted.json")
        with open(bad_json, "w") as f:
            f.write("{{bad json:::")

        fallback = load_preference_model(bad_json)
        assert isinstance(fallback, PreferenceModel)
        assert fallback.get_state() == LearningState.UNTRAINED
        assert len(fallback.observations) == 0

        # Non-existent path
        missing = load_preference_model(os.path.join(tmpdir, "does_not_exist.json"))
        assert missing.get_state() == LearningState.UNTRAINED


# ==============================================================================
# TC-08: Explicit Reset / Delete Behavior
# ==============================================================================
def test_tc_08_reset_behavior():
    """
    TC-08: Resetting the model purges all observations and learned weights,
    setting state to RESET.
    """
    model = PreferenceModel()
    f1 = RouteFeatures(1000.0, 1000.0, 50.0, 10.0)
    for i in range(4):
        model.add_observation(PreferenceObservation(f"id_{i}", "t", "p", f1, []))

    assert len(model.observations) == 4
    model.reset()

    assert len(model.observations) == 0
    assert np.all(model.weights == 0.0)
    assert model.get_state() == LearningState.RESET
    assert model.predict_utility(f1) == 0.0


# ==============================================================================
# TC-09: Duplicate-Feedback Prevention
# ==============================================================================
def test_tc_09_duplicate_prevention():
    """
    TC-09: Adding an observation with the same choice_id must be rejected (returns False)
    and not duplicate training samples.
    """
    model = PreferenceModel()
    f1 = RouteFeatures(1000.0, 1000.0, 50.0, 10.0)
    f2 = RouteFeatures(2000.0, 2000.0, 100.0, 20.0)

    obs = PreferenceObservation("dup_id", "2026-10-17T00:00:00Z", "p1", f1, [CandidateOption("p2", f2)])
    assert model.add_observation(obs) is True
    assert len(model.observations) == 1

    # Attempt duplicate
    assert model.add_observation(obs) is False
    assert len(model.observations) == 1


# ==============================================================================
# TC-10: Different Feedback Produces Explainable Differences
# ==============================================================================
def test_tc_10_divergent_feedback_profiles():
    """
    TC-10: Train Model A with Science preferences and Model B with Conservative preferences.
    Verify they rank the same candidate options oppositely.
    """
    f_cons = RouteFeatures(1500.0, 1600.0, 0.0, 10.0)
    f_sci = RouteFeatures(4500.0, 6000.0, 180.0, 80.0)

    # Model A: Science Lover
    model_a = PreferenceModel()
    for i in range(4):
        model_a.add_observation(
            PreferenceObservation(f"a_{i}", "t", "sci", f_sci, [CandidateOption("cons", f_cons)])
        )

    # Model B: Safety / Short Distance Lover
    model_b = PreferenceModel()
    for i in range(4):
        model_b.add_observation(
            PreferenceObservation(f"b_{i}", "t", "cons", f_cons, [CandidateOption("sci", f_sci)])
        )

    # Model A prefers f_sci over f_cons
    assert model_a.predict_utility(f_sci) > model_a.predict_utility(f_cons)
    # Model B prefers f_cons over f_sci
    assert model_b.predict_utility(f_cons) > model_b.predict_utility(f_sci)


# ==============================================================================
# TC-11 & TC-12: Hard Constraints Enforced, No Fabricated Recommendations
# ==============================================================================
def test_tc_11_12_hard_constraints_and_no_feasible_routes():
    """
    TC-11 & TC-12: An unreachable or budget-exceeded route must NEVER be ranked,
    regardless of how high its potential utility or science score is.
    If all routes are infeasible, rank_routes() must return an empty list.
    """
    model = PreferenceModel()
    # High science weights
    model.weights = np.array([0.0, 0.0, 5.0, 0.0])
    model.state = LearningState.PERSONALIZED

    # Route with massive science (250 pts), but budget-infeasible!
    infeasible_route = RouteResult(
        profile="science_first",
        start_rc=(0, 0),
        goal_rc=(10, 10),
        path=[(0, 0), (10, 10)],
        distance_m=8000.0,
        cost=9000.0,
        science_score=250.0,
        visited_waypoint_ids=["w1", "w2"],
        num_cells=2,
        num_steps=1,
        is_reachable=True,
        is_budget_feasible=False,  # EXCEEDED BUDGET!
        max_distance_m=5000.0,
        status_message="Budget Exceeded",
    )

    unreachable_route = RouteResult(
        profile="conservative",
        start_rc=(0, 0),
        goal_rc=(10, 10),
        path=[],
        distance_m=0.0,
        cost=float("inf"),
        science_score=0.0,
        visited_waypoint_ids=[],
        num_cells=0,
        num_steps=0,
        is_reachable=False,  # UNREACHABLE!
        is_budget_feasible=False,
        max_distance_m=5000.0,
        status_message="Blocked",
    )

    candidates = {
        "science_first": infeasible_route,
        "conservative": unreachable_route,
    }

    ranked = model.rank_routes(candidates)
    assert len(ranked) == 0  # No feasible routes can be ranked


# ==============================================================================
# TC-13: Ranking Works with Fewer Than Three Feasible Routes
# ==============================================================================
def test_tc_13_ranking_with_subset_of_feasible_routes():
    """
    TC-13: When only 1 or 2 routes are feasible, rank_routes() correctly ranks
    and tags the top candidate as recommended.
    """
    model = PreferenceModel()
    model.weights = np.array([-1.0, 0.0, 2.0, 0.0])
    model.state = LearningState.PERSONALIZED

    r_bal = RouteResult(
        profile="balanced",
        start_rc=(0, 0),
        goal_rc=(10, 10),
        path=[(0, 0), (5, 5), (10, 10)],
        distance_m=2500.0,
        cost=2800.0,
        science_score=80.0,
        visited_waypoint_ids=["w1"],
        num_cells=3,
        num_steps=2,
        is_reachable=True,
        is_budget_feasible=True,
        max_distance_m=5000.0,
        status_message="ok",
    )

    ranked_one = model.rank_routes({"balanced": r_bal})
    assert len(ranked_one) == 1
    assert ranked_one[0].profile == "balanced"
    assert ranked_one[0].is_recommended is True
    assert ranked_one[0].rank == 1


# ==============================================================================
# TC-14: ML Does Not Mutate Deterministic Route Planner Results
# ==============================================================================
def test_tc_14_planner_determinism_unaffected():
    """
    TC-14: Running preference models before and after route planning does not alter
    the deterministic path coordinates, distances, or costs returned by plan_route.
    """
    elev = np.zeros((25, 25), dtype=np.float32)
    grid = derive_terrain_from_array(elev, TerrainConfig())
    start = (2, 2)
    goal = (20, 20)
    p_cfg = PlannerConfig(profile="conservative")

    route_raw = plan_route(start, goal, grid, config=p_cfg)

    # Initialize model
    model = PreferenceModel()
    for i in range(5):
        model.add_observation(
            PreferenceObservation(
                f"c_{i}", "t", "conservative", RouteFeatures(100.0, 100.0, 0.0, 0.0), []
            )
        )

    route_after = plan_route(start, goal, grid, config=p_cfg)

    assert route_raw.path == route_after.path
    assert route_raw.distance_m == route_after.distance_m
    assert route_raw.cost == route_after.cost


# ==============================================================================
# TC-15: Voice Modes Do Not Change Learned Weights
# ==============================================================================
def test_tc_15_voice_modes_preserve_weights():
    """
    TC-15: Toggling between professional and dry humour voice modes alters the narrative
    text but leaves learned weights and numerical metrics strictly identical.
    """
    model = PreferenceModel()
    f1 = RouteFeatures(1000.0, 1000.0, 100.0, 10.0)
    for i in range(4):
        model.add_observation(PreferenceObservation(f"v_{i}", "t", "sci", f1, []))

    weights_before = model.weights.copy()
    narr_pro = model.get_preference_summary(voice_mode="professional")
    narr_dry = model.get_preference_summary(voice_mode="dry_humour")

    np.testing.assert_array_equal(model.weights, weights_before)
    assert narr_pro["headline"] != narr_dry["headline"]
    assert narr_pro["detail"] != narr_dry["detail"]
    assert narr_pro["weights"] == narr_dry["weights"]


# ==============================================================================
# TC-16: Integration with Real Jezero CTX Raster & The Gauntlet
# ==============================================================================
def test_tc_16_real_jezero_gauntlet_ml_integration():
    """
    TC-16: On real USGS Jezero CTX raster, evaluate baseline routes, simulate a Gauntlet
    disruption, and rank remaining feasible detour options using Mission Commander AI.
    """
    if not os.path.exists(PROCESSED_TIFF):
        pytest.skip("Processed Jezero GeoTIFF not found.")

    terrain = load_and_process_terrain(PROCESSED_TIFF)
    start_rc = (156, 179)  # Butler Landing
    goal_rc = (127, 85)   # Belva Crater rim

    wps = [
        ScienceWaypoint(id="hawksbill_gap", name="Hawksbill Gap", rc=(136, 91), priority_score=85.0),
        ScienceWaypoint(id="distal_site", name="Distal Crater Rim", rc=(50, 50), priority_score=60.0),
    ]

    p_cons = plan_route(start_rc, goal_rc, terrain, wps, PlannerConfig(profile="conservative"))
    p_bal = plan_route(start_rc, goal_rc, terrain, wps, PlannerConfig(profile="balanced", science_appetite_gamma=2.0))
    p_sci = plan_route(start_rc, goal_rc, terrain, wps, PlannerConfig(profile="science_first"))

    assert p_cons.science_score == 0.0
    assert p_bal.science_score == 85.0
    assert p_sci.science_score == 145.0

    all_routes = {"conservative": p_cons, "balanced": p_bal, "science_first": p_sci}

    # Commander prefers Science-First over Conservative and Balanced
    model = PreferenceModel()
    f_sci = extract_route_features(p_sci, terrain)
    f_cons = extract_route_features(p_cons, terrain)
    f_bal = extract_route_features(p_bal, terrain)

    for i in range(3):
        model.add_observation(
            PreferenceObservation(
                choice_id=f"jez_{i}",
                timestamp="2026-10-17T02:00:00Z",
                selected_profile="science_first",
                selected_features=f_sci,
                rejected_candidates=[
                    CandidateOption("conservative", f_cons),
                    CandidateOption("balanced", f_bal),
                ],
            )
        )

    assert model.get_state() == LearningState.PERSONALIZED

    # Rank baseline routes: Science-First should be strictly top recommendation
    ranked_baseline = model.rank_routes(all_routes, terrain=terrain)
    assert len(ranked_baseline) == 3
    assert ranked_baseline[0].profile == "science_first"
    assert ranked_baseline[0].is_recommended is True
    assert ranked_baseline[0].utility_score > ranked_baseline[1].utility_score
    assert ranked_baseline[-1].profile == "conservative"

    # Now inject a Gauntlet Disruption: Hawksbill Scarp Rockfall
    scenario = ScenarioDefinition(
        id="hawksbill_block",
        name="Hawksbill Rockfall",
        disruption_type=DisruptionType.CORRIDOR_CLOSURE,
        description="Blocks central ascent corridor",
        blocked_cells=[(r, c) for r in range(134, 139) for c in range(89, 94)],
    )

    comp_bal = run_scenario(p_bal, scenario, start_rc, goal_rc, wps, terrain, PlannerConfig(profile="balanced"))
    comp_cons = run_scenario(p_cons, scenario, start_rc, goal_rc, wps, terrain, PlannerConfig(profile="conservative"))

    scenario_routes = {
        "balanced": comp_bal.scenario_route,
        "conservative": comp_cons.scenario_route,
    }

    # Rank the remaining feasible scenario detours
    ranked_scen = model.rank_routes(scenario_routes, terrain=terrain)
    assert len(ranked_scen) >= 1
    # Check that each ranked detour is marked feasible
    for rk in ranked_scen:
        assert rk.route.is_reachable
        assert rk.route.is_budget_feasible
