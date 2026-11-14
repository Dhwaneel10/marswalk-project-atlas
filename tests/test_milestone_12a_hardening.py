"""
MarsWalk 2.0 / Project Atlas — Milestone 12A Hardening & Resilience Test Suite.
Verifies edge cases, boundary invariants, scientific provenance safeguards,
contract validations, and resilience under invalid / adversarial payloads.
"""

import copy
import json
import pytest
import numpy as np

from marswalk.api.contracts import (
    SCHEMA_VERSION,
    validate_contract,
    validate_campaign_design_space_record,
    validate_campaign_benchmark_record,
    validate_campaign_analytics_record,
)
from marswalk.core.terrain import (
    TerrainGrid,
    load_and_process_terrain,
    calculate_edge_cost,
)
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    PlanningProfile,
    plan_mission_campaign,
)
from marswalk.core.weather import (
    get_weather_manager,
    PhysicalRangeGuard,
)
from marswalk.core.campaign_design_space import (
    SearchBounds,
    CandidateStatus,
    DominanceStatus,
    CandidateObjectives,
    CandidateEvaluation,
    check_dominance,
    classify_pareto_frontier,
    explore_campaign_design_space,
    DESIGN_SPACE_DISCLAIMER,
)
from marswalk.core.campaign_coordination import (
    create_default_units,
    allocate_campaign_coordination,
    ExplorationUnit,
    UnitType,
    CoordinationStrategy,
)
from marswalk.core.campaign_simulator import (
    CampaignDigitalTwin,
    SimulationStatus,
    TimelineInterval,
    ActivityType,
)
from marswalk.core.campaign_analytics import (
    analyze_campaign_performance,
    CauseAttribution,
    ANALYTICS_DISCLAIMER,
)
from marswalk.api.workspace import (
    save_campaign,
    get_campaign,
    save_design_space_evaluation,
    get_design_space_evaluation,
    promote_design_space_candidate,
    WorkspaceError,
)
from marswalk.api.service import (
    promote_design_space_candidate_api,
    evaluate_campaign_design_space_api,
    APIError,
)


@pytest.fixture(scope="module")
def terrain_grid() -> TerrainGrid:
    return load_and_process_terrain("data/processed/jezero_ready_20m.tif")


@pytest.fixture
def baseline_campaign(terrain_grid: TerrainGrid) -> MissionCampaign:
    targets = [
        CampaignTarget(
            id="tgt_h1_landing",
            name="Octavia Landing",
            row=117,
            col=157,
            priority_score=100.0,
            dwell_time_s=600.0,
        ),
        CampaignTarget(
            id="tgt_h1_delta",
            name="Delta Front",
            row=130,
            col=135,
            priority_score=85.0,
            dwell_time_s=900.0,
        ),
    ]
    cfg = CampaignConfig(
        max_sols=2,
        max_duration_per_sortie_s=28800.0,
        planning_profile=PlanningProfile.SCIENCE_PRIORITY,
    )
    return plan_mission_campaign(
        campaign_id="cmp_hardening_base",
        name="Hardening Base Campaign",
        config=cfg,
        targets=targets,
        terrain=terrain_grid,
    )


# =============================================================================
# 1. CANDIDATE PROMOTION HARDENING & IMMUTABILITY
# =============================================================================

def test_promote_candidate_not_found(baseline_campaign: MissionCampaign, terrain_grid: TerrainGrid):
    """Verifies that promoting a non-existent candidate raises WorkspaceError with 404."""
    ds_res = explore_campaign_design_space(
        campaign=baseline_campaign,
        terrain=terrain_grid,
        search_bounds=SearchBounds(max_candidates=2, max_planner_calls=2),
    )
    save_design_space_evaluation(ds_res)

    with pytest.raises(WorkspaceError) as exc_info:
        promote_design_space_candidate(
            design_space_id=ds_res["design_space_id"],
            candidate_id="cand_cp_nonexistent_999",
        )
    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "ERR_CANDIDATE_NOT_FOUND"


def test_promote_candidate_infeasible_rejected(baseline_campaign: MissionCampaign):
    """Verifies that an infeasible candidate cannot be promoted into a campaign plan."""
    infeasible_cand = {
        "candidate_id": "cand_cp_infeas_01",
        "fingerprint": "a" * 64,
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
        "tradeoff_explanation": "Infeasible",
        "infeasibility_reasons": ["Duration limit insufficient for any sortie"],
    }
    fake_ds = {
        "schema_version": "1.0.0",
        "design_space_id": "ds_hardening_infeas_test",
        "campaign_id": baseline_campaign.campaign_id,
        "campaign_version": 1,
        "created_at_utc": "2026-10-29T12:00:00Z",
        "search_bounds": {"max_candidates": 2, "max_planner_calls": 2},
        "search_completeness": {
            "candidates_considered": 2,
            "candidates_deduplicated": 0,
            "candidates_evaluated": 2,
            "candidates_rejected": 1,
            "is_exhaustive": True,
            "limit_reached": False,
            "unexplored_scope_notes": "None",
        },
        "pareto_candidates": [],
        "dominated_candidates": [],
        "infeasible_candidates": [infeasible_cand],
        "recommendations": [],
        "limitations_disclaimer": DESIGN_SPACE_DISCLAIMER,
    }
    save_campaign(baseline_campaign.to_dict())
    save_design_space_evaluation(fake_ds)

    with pytest.raises(WorkspaceError) as exc_info:
        promote_design_space_candidate(
            design_space_id="ds_hardening_infeas_test",
            candidate_id="cand_cp_infeas_01",
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "ERR_CANDIDATE_INFEASIBLE"


def test_baseline_campaign_immutability(baseline_campaign: MissionCampaign, terrain_grid: TerrainGrid):
    """Verifies that candidate promotion never modifies the original baseline campaign."""
    save_campaign(baseline_campaign.to_dict())
    orig_dict = get_campaign(baseline_campaign.campaign_id)
    orig_version = orig_dict["version"]

    ds_res = explore_campaign_design_space(
        campaign=baseline_campaign,
        terrain=terrain_grid,
        search_bounds=SearchBounds(max_candidates=3, max_planner_calls=3),
    )
    save_design_space_evaluation(ds_res)

    pareto_cand = ds_res["pareto_candidates"][0]
    prom_res = promote_design_space_candidate(
        design_space_id=ds_res["design_space_id"],
        candidate_id=pareto_cand["candidate_id"],
        new_campaign_name="Promoted Hardening Campaign v2",
    )
    assert prom_res["new_version"] == orig_version + 1

    # Audit baseline remains untouched
    reloaded_base = get_campaign(baseline_campaign.campaign_id)
    assert reloaded_base["version"] == orig_version
    assert reloaded_base["name"] == orig_dict["name"]
    assert reloaded_base["sorties"] == orig_dict["sorties"]


# =============================================================================
# 2. TERRAIN BOUNDARY & OUT-OF-BOUNDS INVARIANTS
# =============================================================================

def test_terrain_out_of_bounds_coordinates(terrain_grid: TerrainGrid):
    """Verifies out-of-bounds coordinates are recognized as impassable / invalid."""
    assert calculate_edge_cost((0, 0), (-1, 0), terrain_grid) == float("inf")
    assert calculate_edge_cost((0, 0), (0, -1), terrain_grid) == float("inf")
    assert calculate_edge_cost((0, 0), (terrain_grid.shape[0], 0), terrain_grid) == float("inf")
    assert calculate_edge_cost((0, 0), (0, terrain_grid.shape[1]), terrain_grid) == float("inf")


def test_terrain_elevation_range_physically_bounded(terrain_grid: TerrainGrid):
    """Verifies Jezero DTM elevation range matches published USGS CTX range."""
    valid_elev = terrain_grid.elevation[~terrain_grid.invalid_mask]
    assert valid_elev.size > 0
    min_elev = float(np.min(valid_elev))
    max_elev = float(np.max(valid_elev))
    # Jezero Crater floor is known to sit around -2650m to -2400m relative to Mars MOLA datum
    assert -2700.0 <= min_elev <= -2500.0
    assert -2500.0 <= max_elev <= -2300.0


# =============================================================================
# 3. ENVIRONMENTAL INTELLIGENCE & SITE ISOLATION
# =============================================================================

def test_weather_site_isolation_jezero_vs_gale():
    """Verifies that Jezero Crater and Gale Crater weather queries return distinct instrument data."""
    wm = get_weather_manager()
    sites = wm.get_supported_sites()
    site_ids = [s["site_id"] for s in sites]
    assert "jezero_crater" in site_ids
    assert "gale_crater" in site_ids

    jezero_weather = wm.get_weather("jezero_crater")
    gale_weather = wm.get_weather("gale_crater")

    # Jezero must cite MEDA instrument and Perseverance platform
    assert "MEDA" in jezero_weather["source_metadata"]["instrument"]
    assert "Perseverance" in jezero_weather["source_metadata"]["platform"]

    # Gale must cite REMS instrument and Curiosity platform
    assert "REMS" in gale_weather["source_metadata"]["instrument"]
    assert "Curiosity" in gale_weather["source_metadata"]["platform"]

    # Both must explicitly disclose site isolation and archives
    assert "SITE ISOLATION ENFORCED" in " ".join(gale_weather.get("disclosures", []))


def test_weather_physical_range_guard():
    """Verifies physical range guard detects impossible Martian atmospheric readings."""
    guard = PhysicalRangeGuard()
    # Normal reading produces no warnings
    normal_meas = {
        "atmospheric_pressure_pa": 600.0,
        "air_temperature_k": 210.0,
        "ground_temperature_k": 215.0,
        "wind_speed_m_s": 5.0,
    }
    warnings_normal = guard.validate(normal_meas)
    assert len(warnings_normal) == 0

    # Impossible readings produce warnings
    extreme_meas = {
        "atmospheric_pressure_pa": 101325.0,  # Earth sea-level pressure
        "air_temperature_k": 373.15,          # 100 C boiling
        "wind_speed_m_s": 250.0,              # Impossible wind
    }
    warnings_extreme = guard.validate(extreme_meas)
    assert len(warnings_extreme) >= 2

    # Hard vacuum pressure produces warning
    low_p_meas = {"atmospheric_pressure_pa": 5.0}
    warnings_low_p = guard.validate(low_p_meas)
    assert len(warnings_low_p) >= 1


# =============================================================================
# 4. PARETO OPTIMIZATION MATHEMATICAL PROPERTIES
# =============================================================================

def test_pareto_dominance_transitivity():
    """
    Verifies Pareto dominance transitivity: If A dominates B and B dominates C,
    then A must dominate C.
    """
    cand_a = CandidateEvaluation(
        candidate_id="cand_a",
        fingerprint="a" * 64,
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=90.0,
            total_duration_s=20000.0,
            total_distance_m=3000.0,
            unallocated_priority=10.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status=DominanceStatus.PARETO_EFFICIENT.value,
    )
    cand_b = CandidateEvaluation(
        candidate_id="cand_b",
        fingerprint="b" * 64,
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=80.0,
            total_duration_s=22000.0,
            total_distance_m=3500.0,
            unallocated_priority=20.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status=DominanceStatus.DOMINATED.value,
    )
    cand_c = CandidateEvaluation(
        candidate_id="cand_c",
        fingerprint="c" * 64,
        configuration={},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=70.0,
            total_duration_s=25000.0,
            total_distance_m=4000.0,
            unallocated_priority=30.0,
            temporal_conflicts_count=1,
            sortie_count=2,
        ),
        dominance_status=DominanceStatus.DOMINATED.value,
    )

    assert check_dominance(cand_a, cand_b)
    assert check_dominance(cand_b, cand_c)
    assert check_dominance(cand_a, cand_c)  # Transitivity holds


def test_pareto_tied_candidates_coexist():
    """Verifies that identical candidate objective profiles do not dominate each other."""
    cand_1 = CandidateEvaluation(
        candidate_id="cand_1",
        fingerprint="1" * 64,
        configuration={"max_sols": 2},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=85.0,
            total_duration_s=21000.0,
            total_distance_m=3200.0,
            unallocated_priority=15.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status=DominanceStatus.PARETO_EFFICIENT.value,
    )
    cand_2 = CandidateEvaluation(
        candidate_id="cand_2",
        fingerprint="2" * 64,
        configuration={"max_sols": 3},
        status=CandidateStatus.FEASIBLE.value,
        objectives=CandidateObjectives(
            science_coverage_pct=85.0,
            total_duration_s=21000.0,
            total_distance_m=3200.0,
            unallocated_priority=15.0,
            temporal_conflicts_count=0,
            sortie_count=2,
        ),
        dominance_status=DominanceStatus.PARETO_EFFICIENT.value,
    )

    # Neither strictly dominates the other
    assert not check_dominance(cand_1, cand_2)
    assert not check_dominance(cand_2, cand_1)

    pareto, dominated, infeasible = classify_pareto_frontier([cand_1, cand_2])
    assert len(pareto) == 2
    assert len(dominated) == 0


# =============================================================================
# 5. CAUSAL ATTRIBUTION & ANALYTICS INTEGRITY
# =============================================================================

def test_causal_attribution_requires_triggering_event(baseline_campaign: MissionCampaign):
    """Verifies that confirmed cause requires triggering events; uncorroborated delay is undetermined."""
    # Create synthetic simulation with one blowout sortie without events
    sim_dict = {
        "simulation_id": "sim_hardening_test",
        "campaign_id": baseline_campaign.campaign_id,
        "coordination_id": "coord_test",
        "created_at_utc": "2026-10-29T12:00:00Z",
        "status": "COMPLETED",
        "total_duration_s": 35000.0,
        "current_time_s": 35000.0,
        "timeline_intervals": [
            {
                "interval_id": "iv_1",
                "unit_id": "unit_rover_1",
                "sortie_id": baseline_campaign.sorties[0].sortie_id,
                "sol_index": 1,
                "activity_type": ActivityType.TRANSIT.value,
                "status": "COMPLETED",
                "start_time_s": 0.0,
                "end_time_s": 32000.0,  # 32000s vs 28800s planned (+3200s blowout)
                "duration_s": 32000.0,
                "distance_m": 2500.0,
            }
        ],
        "events": [],  # No disruption events recorded
        "conflicts": [],
        "units": [u.to_dict() for u in create_default_units()],
        "statistics": {},
        "limitations_disclaimer": "Simulated",
    }

    analytics = analyze_campaign_performance(
        campaign=baseline_campaign,
        simulation=sim_dict,
    )

    validate_campaign_analytics_record(analytics)
    deviations = analytics.get("deviations", [])
    assert len(deviations) > 0

    blowout_dev = next((d for d in deviations if d["code"] == "DEV_SORTIE_DURATION_BLOWOUT"), None)
    assert blowout_dev is not None
    # Because no discrete events occurred, causality must be UNDETERMINED
    assert blowout_dev["cause_attribution"] == CauseAttribution.UNDETERMINED.value
    assert len(blowout_dev["triggering_event_ids"]) == 0


# =============================================================================
# 6. DIGITAL TWIN STEPPING & TIME BOUNDS
# =============================================================================

def test_digital_twin_stepping_and_boundary_safety(baseline_campaign: MissionCampaign, terrain_grid: TerrainGrid):
    """Verifies that stepping or seeking past the timeline end does not cause index errors."""
    twin = CampaignDigitalTwin(
        simulation_id="sim_twin_hardening",
        campaign=baseline_campaign,
        terrain=terrain_grid,
    )
    assert twin.status == SimulationStatus.IDLE.value

    # Seek pauses at end time
    end_time = twin.total_duration_s
    twin.seek(end_time + 10000.0)
    assert twin.current_time_s == end_time
    assert twin.status == SimulationStatus.PAUSED.value

    # Advance past end transitions to completed
    twin.advance(end_time + 10000.0)
    assert twin.status == SimulationStatus.COMPLETED.value

    # Additional steps beyond end should yield empty events and maintain completed status
    events = twin.step(5)
    assert len(events) == 0
    assert twin.status == SimulationStatus.COMPLETED.value

    # Reset returns to idle
    twin.reset()
    assert twin.current_time_s == 0.0
    assert twin.status == SimulationStatus.IDLE.value
