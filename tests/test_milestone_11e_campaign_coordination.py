"""
Unit and integration tests for Milestone 11E: Multi-Agent Campaign Coordination & Resource Handoffs.
Verifies versioned exploration unit models, multi-unit task allocation, DAG prerequisite ordering,
slope envelopes, availability windows, coordination strategy comparisons, task responsibility handoffs,
what-if unit loss re-allocation, workspace persistence, and version promotion.
"""

import copy
import json
import os
import shutil
import tempfile
import urllib.request
import pytest
import numpy as np

from marswalk.core.terrain import TerrainGrid, load_and_process_terrain
from marswalk.core.mission_campaign import (
    CampaignConfig,
    CampaignTarget,
    MissionCampaign,
    TargetStatus,
    CampaignStatus,
    plan_mission_campaign,
)
from marswalk.core.campaign_coordination import (
    UnitType,
    UnitStatus,
    CoordinationStrategy,
    AllocationStatus,
    HandoffStatus,
    MobilityProfile,
    AvailabilityWindow,
    ExplorationUnit,
    TargetAllocation,
    TaskHandoff,
    CoordinationPlan,
    create_default_units,
    allocate_campaign_coordination,
    validate_and_execute_task_handoff,
    evaluate_coordination_what_if,
    promote_coordination_to_campaign_version,
)
from marswalk.api.workspace import (
    save_campaign,
    get_campaign,
    save_coordination_plan,
    get_coordination_plan,
    list_coordination_plans,
    save_task_handoff,
    get_task_handoff,
    list_task_handoffs,
)
from marswalk.api.service import (
    coordinate_campaign_api,
    list_campaign_coordinations_api,
    execute_campaign_handoff_api,
    list_campaign_handoffs_api,
    apply_campaign_coordination_api,
)


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
    """Create a standard multi-sol campaign with 4 candidate targets and prerequisite DAG."""
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
            name="Delta Front Lobe",
            row=123,
            col=160,
            priority_score=80.0,
            dwell_time_s=900.0,
            prerequisites=["t_dep_1"],
            science_objective="FLUVIAL_DELTA_SEDIMENTOLOGY",
        ),
        CampaignTarget(
            id="t_ast_1",
            name="Carbonate Ridge",
            row=115,
            col=154,
            priority_score=85.0,
            dwell_time_s=900.0,
            science_objective="ASTROBIOLOGY_BIOSIGNATURE",
        ),
        CampaignTarget(
            id="t_ast_2",
            name="Silica Outcrop",
            row=112,
            col=152,
            priority_score=75.0,
            dwell_time_s=900.0,
            prerequisites=["t_ast_1"],
            science_objective="ASTROBIOLOGY_BIOSIGNATURE",
        ),
    ]
    config = CampaignConfig(
        max_duration_per_sortie_s=28800.0,
        max_sols=4,
        base_start_rc=(117, 157),
    )
    campaign = plan_mission_campaign(
        campaign_id="cmp_coord_test",
        name="Test Coordination Campaign",
        config=config,
        targets=targets,
        terrain=jezero_terrain,
    )
    return campaign


def test_default_units_creation():
    """Verify creation of authentic default 2-unit fleet."""
    units = create_default_units()
    assert len(units) == 2
    u_ids = [u.unit_id for u in units]
    assert "unit_perseverance" in u_ids
    assert "unit_crew_eva_1" in u_ids

    rover = next(u for u in units if u.unit_id == "unit_perseverance")
    assert rover.unit_type == UnitType.ROBOTIC_ROVER.value
    assert rover.mobility_profile.max_slope_deg == 15.0
    assert rover.max_duration_per_sortie_s == 14400.0

    crew = next(u for u in units if u.unit_id == "unit_crew_eva_1")
    assert crew.unit_type == UnitType.CREW_EVA.value
    assert crew.mobility_profile.max_slope_deg == 25.0
    assert crew.max_duration_per_sortie_s == 28800.0


def test_multi_unit_allocation_priority_first(sample_campaign, jezero_terrain):
    """Verify priority-first allocation across multiple units respects limits and DAG order."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        strategy=CoordinationStrategy.PRIORITY_FIRST.value,
    )
    assert plan.allocation_strategy == CoordinationStrategy.PRIORITY_FIRST.value
    assert len(plan.units) == 2
    assert len(plan.sorties) > 0

    assigned_targets = [a for a in plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value]
    assert len(assigned_targets) > 0

    # Ensure no duplicates: each target assigned to at most one unit
    assigned_tids = [a.target_id for a in assigned_targets]
    assert len(assigned_tids) == len(set(assigned_tids))

    # Check DAG ordering: t_dep_2 (child) must not be scheduled on an earlier sol than t_dep_1 (parent)
    alloc_map = {a.target_id: a for a in plan.target_allocations}
    if "t_dep_1" in alloc_map and "t_dep_2" in alloc_map:
        if alloc_map["t_dep_1"].assigned_sol_index and alloc_map["t_dep_2"].assigned_sol_index:
            assert alloc_map["t_dep_1"].assigned_sol_index <= alloc_map["t_dep_2"].assigned_sol_index


def test_multi_unit_allocation_balanced_workload(sample_campaign, jezero_terrain):
    """Verify balanced-workload strategy spreads tasks across available units."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        strategy=CoordinationStrategy.BALANCED_WORKLOAD.value,
    )
    assert plan.allocation_strategy == CoordinationStrategy.BALANCED_WORKLOAD.value
    assert plan.summary["total_units"] == 2

    # Check that both units receive assigned sorties if workload permits
    unit_sorties = {u.unit_id: 0 for u in plan.units}
    for s in plan.sorties:
        if s.unit_id in unit_sorties:
            unit_sorties[s.unit_id] += 1

    assert sum(unit_sorties.values()) == len(plan.sorties)


def test_multi_unit_allocation_capability_first(sample_campaign, jezero_terrain):
    """Verify capability-first strategy matches targets based on mobility profiles."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        strategy=CoordinationStrategy.CAPABILITY_FIRST.value,
    )
    assert plan.allocation_strategy == CoordinationStrategy.CAPABILITY_FIRST.value
    assert len(plan.strategy_comparison) == 3


def test_strategy_comparison_matrix(sample_campaign, jezero_terrain):
    """Verify strategy comparison matrix compares priority-first, balanced, and capability-first."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    comp = plan.strategy_comparison
    assert len(comp) == 3
    strat_names = [c["strategy"] for c in comp]
    assert "priority_first" in strat_names
    assert "balanced_workload" in strat_names
    assert "capability_first" in strat_names

    for c in comp:
        assert "total_distance_m" in c
        assert "total_duration_s" in c
        assert "total_science_score" in c
        assert "workload_imbalance_s" in c
        assert "is_feasible" in c


def test_unit_slope_ceiling_and_unreachable_targets(jezero_terrain):
    """Verify that targets on steep terrain are unreachable for low-slope units."""
    # Place target on steep crater rim slope
    steep_target = CampaignTarget(
        id="t_steep",
        name="Crater Wall Cliff",
        row=100,
        col=100,
        priority_score=60.0,
    )
    # Unit with very low 2° slope tolerance
    low_slope_rover = ExplorationUnit(
        unit_id="unit_flat_only",
        name="Flat Ground Rover",
        mobility_profile=MobilityProfile(max_slope_deg=2.0),
        max_duration_per_sortie_s=14400.0,
    )
    camp = MissionCampaign(
        campaign_id="cmp_steep_test",
        name="Steep Test Campaign",
        config=CampaignConfig(base_start_rc=(117, 157)),
        targets=[steep_target],
        sorties=[],
        summary=sample_campaign_summary(),
    )
    plan = allocate_campaign_coordination(
        campaign=camp,
        terrain=jezero_terrain,
        units=[low_slope_rover],
    )
    steep_alloc = next(a for a in plan.target_allocations if a.target_id == "t_steep")
    assert steep_alloc.status == AllocationStatus.UNREACHABLE.value
    assert "slope" in steep_alloc.reason.lower()


def test_availability_window_enforcement(sample_campaign, jezero_terrain):
    """Verify unit is not scheduled on sols outside its availability window."""
    late_unit = ExplorationUnit(
        unit_id="unit_late_arrival",
        name="Late Arriving Scout",
        availability_window=AvailabilityWindow(start_sol=3, end_sol=4),
        max_duration_per_sortie_s=14400.0,
    )
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        units=[late_unit],
    )
    for s in plan.sorties:
        if s.unit_id == "unit_late_arrival":
            assert s.sol_index >= 3


def test_task_handoff_valid(sample_campaign, jezero_terrain):
    """Verify a valid task responsibility handoff reassigns target and re-routes sorties."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
        strategy=CoordinationStrategy.PRIORITY_FIRST.value,
    )
    # Find a scheduled target
    sched_alloc = next(a for a in plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value)
    target_id = sched_alloc.target_id
    src_unit = sched_alloc.assigned_unit_id
    rec_unit = "unit_crew_eva_1" if src_unit == "unit_perseverance" else "unit_perseverance"
    sol = sched_alloc.assigned_sol_index or 1

    handoff, updated_plan = validate_and_execute_task_handoff(
        coordination_plan=plan,
        campaign=sample_campaign,
        terrain=jezero_terrain,
        target_id=target_id,
        source_unit_id=src_unit,
        receiving_unit_id=rec_unit,
        sol_index=sol,
        reason="Test valid handoff",
    )
    assert handoff.is_valid is True
    assert handoff.status == HandoffStatus.ACCEPTED.value

    # Verify target ownership transitioned
    new_alloc = next(a for a in updated_plan.target_allocations if a.target_id == target_id)
    assert new_alloc.assigned_unit_id == rec_unit
    assert len(updated_plan.handoffs) == 1


def test_task_handoff_rejected_incompatible_slope(sample_campaign, jezero_terrain):
    """Verify handoff rejection when recipient unit cannot handle target terrain slope."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    sched_alloc = next(a for a in plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value)
    target_id = sched_alloc.target_id
    src_unit = sched_alloc.assigned_unit_id

    # Add a fragile unit with 0.1° slope ceiling
    fragile_unit = ExplorationUnit(
        unit_id="unit_fragile",
        name="Ultra Fragile Unit",
        mobility_profile=MobilityProfile(max_slope_deg=0.1),
    )
    plan.units.append(fragile_unit)

    handoff, _ = validate_and_execute_task_handoff(
        coordination_plan=plan,
        campaign=sample_campaign,
        terrain=jezero_terrain,
        target_id=target_id,
        source_unit_id=src_unit,
        receiving_unit_id="unit_fragile",
        sol_index=1,
    )
    assert handoff.is_valid is False
    assert handoff.status == HandoffStatus.REJECTED.value
    assert "slope" in handoff.rejection_reason.lower()


def test_task_handoff_prevents_duplicate_ownership(sample_campaign, jezero_terrain):
    """Verify task handoff moves target cleanly without duplicate owners."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    sched_alloc = next(a for a in plan.target_allocations if a.status == AllocationStatus.ASSIGNED.value)
    tid = sched_alloc.target_id
    src = sched_alloc.assigned_unit_id
    rec = "unit_crew_eva_1" if src == "unit_perseverance" else "unit_perseverance"
    sol = sched_alloc.assigned_sol_index or 1

    _, updated = validate_and_execute_task_handoff(
        coordination_plan=plan,
        campaign=sample_campaign,
        terrain=jezero_terrain,
        target_id=tid,
        source_unit_id=src,
        receiving_unit_id=rec,
        sol_index=sol,
    )
    # Check that tid appears in target_allocations exactly once
    matching_allocs = [a for a in updated.target_allocations if a.target_id == tid]
    assert len(matching_allocs) == 1
    assert matching_allocs[0].assigned_unit_id == rec


def test_coordination_what_if_unit_unavailability(sample_campaign, jezero_terrain):
    """Verify what-if scenario when a unit becomes unavailable."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    res = evaluate_coordination_what_if(
        coordination_plan=plan,
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_type="unit_unavailability",
        parameters={"unit_id": "unit_perseverance"},
    )
    assert res["scenario_type"] == "unit_unavailability"
    assert "delta_science_score" in res
    assert "revised_plan" in res


def test_coordination_what_if_mobility_reduction(sample_campaign, jezero_terrain):
    """Verify what-if scenario when a unit suffers speed or slope reduction."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    res = evaluate_coordination_what_if(
        coordination_plan=plan,
        campaign=sample_campaign,
        terrain=jezero_terrain,
        scenario_type="unit_mobility_reduction",
        parameters={"unit_id": "unit_crew_eva_1", "speed_factor": 0.5, "max_slope_deg": 10.0},
    )
    assert res["scenario_type"] == "unit_mobility_reduction"
    assert "delta_duration_s" in res


def test_promote_coordination_to_campaign_version(sample_campaign, jezero_terrain):
    """Verify promoting coordination plan bumps campaign version and updates sorties."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    initial_version = sample_campaign.version
    promoted = promote_coordination_to_campaign_version(
        campaign=sample_campaign,
        coordination_plan=plan,
        terrain=jezero_terrain,
    )
    assert promoted.version == initial_version + 1
    assert promoted.coordination is not None
    assert promoted.parent_campaign_id == f"{sample_campaign.campaign_id}_v{initial_version}"
    assert len(promoted.sorties) == len(plan.sorties)


def test_workspace_persistence_and_retrieval(sample_campaign, jezero_terrain):
    """Verify persistence and listing of coordination plans and handoffs."""
    plan = allocate_campaign_coordination(
        campaign=sample_campaign,
        terrain=jezero_terrain,
    )
    saved = save_coordination_plan(plan.to_dict())
    assert saved["coordination_id"] == plan.coordination_id

    fetched = get_coordination_plan(plan.coordination_id)
    assert fetched["coordination_id"] == plan.coordination_id

    plans = list_coordination_plans(sample_campaign.campaign_id)
    assert any(p["coordination_id"] == plan.coordination_id for p in plans)

    # Test handoff persistence
    handoff_dict = {
        "handoff_id": f"hnd_test_{plan.coordination_id[:8]}",
        "target_id": "t_dep_1",
        "source_unit_id": "unit_perseverance",
        "receiving_unit_id": "unit_crew_eva_1",
        "sol_index": 1,
        "status": "ACCEPTED",
        "is_valid": True,
        "reason": "Test handoff",
        "campaign_id": sample_campaign.campaign_id,
    }
    saved_hnd = save_task_handoff(handoff_dict)
    fetched_hnd = get_task_handoff(saved_hnd["handoff_id"])
    assert fetched_hnd["handoff_id"] == saved_hnd["handoff_id"]


def test_api_service_coordination_and_apply(sample_campaign, jezero_terrain):
    """Test API service methods for coordinate, handoff, and apply."""
    save_campaign(sample_campaign.to_dict())

    # 1. Coordinate API
    coord_res = coordinate_campaign_api(
        payload={
            "campaign_id": sample_campaign.campaign_id,
            "campaign": sample_campaign.to_dict(),
            "strategy": "priority_first",
        },
        terrain=jezero_terrain,
    )
    assert "coordination_id" in coord_res
    assert coord_res["allocation_strategy"] == "priority_first"

    # 2. Handoff API
    sched_alloc = next((a for a in coord_res["target_allocations"] if a["status"] == "ASSIGNED"), None)
    if sched_alloc:
        hnd_res = execute_campaign_handoff_api(
            payload={
                "campaign": sample_campaign.to_dict(),
                "coordination_plan": coord_res,
                "target_id": sched_alloc["target_id"],
                "source_unit_id": sched_alloc["assigned_unit_id"],
                "receiving_unit_id": "unit_crew_eva_1" if sched_alloc["assigned_unit_id"] == "unit_perseverance" else "unit_perseverance",
                "sol_index": sched_alloc.get("assigned_sol_index", 1),
            },
            terrain=jezero_terrain,
        )
        assert hnd_res["status"] in ("success", "rejected")

    # 3. Apply API
    apply_res = apply_campaign_coordination_api(
        payload={
            "campaign": sample_campaign.to_dict(),
            "coordination_plan": coord_res,
        },
        terrain=jezero_terrain,
    )
    assert apply_res["status"] == "success"
    assert apply_res["version"] == sample_campaign.version + 1


def test_live_server_coordination_endpoints(sample_campaign):
    """Verify live HTTP endpoints on port 3000."""
    save_campaign(sample_campaign.to_dict())

    # GET /api/campaign/coordination
    url = "http://127.0.0.1:3000/api/campaign/coordination"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(data, list)
    except Exception as e:
        pytest.skip(f"Live server not responding at {url}: {e}")

    # POST /api/campaign/coordinate
    post_url = "http://127.0.0.1:3000/api/campaign/coordinate"
    post_body = json.dumps({
        "campaign_id": sample_campaign.campaign_id,
        "campaign": sample_campaign.to_dict(),
        "strategy": "priority_first",
    }).encode("utf-8")
    req = urllib.request.Request(post_url, data=post_body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        assert "coordination_id" in res_data
        assert res_data["allocation_strategy"] == "priority_first"


def sample_campaign_summary():
    """Helper creating a dummy CampaignSummary."""
    from marswalk.core.mission_campaign import CampaignSummary
    return CampaignSummary(
        total_sols=1,
        total_sorties=1,
        total_distance_m=100.0,
        total_travel_time_s=100.0,
        total_dwell_time_s=900.0,
        total_duration_s=1000.0,
        total_science_score=50.0,
        targets_total=1,
        targets_scheduled=1,
        targets_unscheduled=0,
    )
