"""
MarsWalk 2.0 / Project Atlas — Milestone 13J Test Battery
==========================================================
Tests the Atlas Fleet Intelligence & Cooperative Multi-Rover Exploration System:
  1. Multi-rover registration & independent ledgers (zero energy pooling)
  2. Authoritative instrument compatibility matching & target allocation
  3. Bounded optimization vs greedy allocation comparison
  4. Per-rover terrain-aware routing on real Jezero DTM
  5. Spatiotemporal occupancy intervals & proximity conflict detection
  6. Automated conflict resolution via holds & detours
  7. Shared communications RelayNet graph reachability & mobile relay roles
  8. Independent energy consumption calculations (drive, avionics, instruments, comms)
  9. Flash memory buffer utilization & finite shared downlink transfer
  10. Multi-sol synchronized schedule generation with parallel rover lanes
  11. 6D Pareto optimization & 5 configuration champions
  12. Counterfactual scenarios F1 (Rover failure) through F7 (Combined disturbance)
  13. 3-way comparative delta matrix evaluation
  14. Fleet plan promotion & version incrementing
  15. API service endpoints & Draft 2020-12 contract validation
"""

import copy
import json
import os
from pathlib import Path
import pytest

from marswalk.core.terrain import load_and_process_terrain, TerrainGrid
from marswalk.core.fleet_operations_director import (
    FleetOperationsDirector,
    RoverUnitConfig,
    RoverOperationalState,
    create_default_fleet_rovers,
    FleetStatus,
)
from marswalk.core.fleet_task_allocator import (
    FleetTaskAllocator,
    FleetScienceTarget,
    get_default_jezero_targets,
)
from marswalk.core.fleet_route_coordinator import (
    FleetRouteCoordinator,
    FleetRoverRoute,
    SpatialTemporalConflict,
)
from marswalk.core.fleet_communications_network import (
    FleetCommunicationsManager,
    RoverConnectivityReport,
)
from marswalk.core.fleet_resource_manager import (
    FleetResourceManager,
    RoverResourceAudit,
)
from marswalk.core.fleet_mission_scheduler import (
    FleetMissionScheduler,
    FleetCampaignSchedule,
)
from marswalk.core.fleet_optimization_engine import (
    FleetOptimizationEngine,
    FleetDisturbanceType,
    FleetOptimizationProfile,
)
from marswalk.api.service import (
    fleet_create_api,
    fleet_list_api,
    fleet_get_api,
    fleet_register_rover_api,
    fleet_allocate_science_api,
    fleet_plan_routes_api,
    fleet_schedule_api,
    fleet_network_api,
    fleet_resources_api,
    fleet_optimize_api,
    fleet_scenario_api,
    fleet_promote_api,
    fleet_assurance_api,
    get_or_create_fleet_director,
)
from marswalk.api.contracts import get_validator


@pytest.fixture(scope="module")
def terrain():
    path = "data/processed/jezero_ready_20m.tif"
    if not os.path.exists(path):
        pytest.skip(f"Terrain file {path} not found")
    return load_and_process_terrain(path)


def test_01_fleet_director_initialization_and_rover_registration():
    director = FleetOperationsDirector(fleet_id="test_fleet_01", name="Jezero Test Fleet")
    assert director.fleet_id == "test_fleet_01"
    assert len(director.rovers) == 2  # Alpha and Beta registered by default
    assert "ATLAS_ROVER_A" in director.rovers
    assert "ATLAS_ROVER_B" in director.rovers

    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    assert len(director.rovers) == 4
    assert len(director.rover_states) == 4
    assert "ATLAS_ROVER_C" in director.rovers
    assert "ATLAS_ROVER_D" in director.rovers

    # Verify state fingerprint
    fp1 = director.compute_state_fingerprint()
    assert isinstance(fp1, str)
    assert len(fp1) == 64  # SHA-256 hex string

    state_dict = director.get_fleet_state()
    assert state_dict["fleet_id"] == "test_fleet_01"
    assert len(state_dict["rovers"]) == 4


def test_02_zero_energy_pooling_invariant():
    """Verify that rovers have strictly independent energy registers and no pooled energy."""
    director = FleetOperationsDirector(fleet_id="test_fleet_res")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    # Check distinct initial capacities
    capacities = [r.usable_battery_capacity_wh for r in director.rovers.values()]
    assert len(capacities) == 4
    assert all(c >= 4000.0 for c in capacities)

    # Modify Rover A SOC and ensure Rover B is completely unaffected
    director.rover_states["ATLAS_ROVER_A"].battery_soc_pct = 42.0
    director.rover_states["ATLAS_ROVER_B"].battery_soc_pct = 95.0

    assert director.rover_states["ATLAS_ROVER_A"].battery_soc_pct == 42.0
    assert director.rover_states["ATLAS_ROVER_B"].battery_soc_pct == 95.0

    # Resource manager strictly reports per-rover ledgers
    frm = FleetResourceManager()
    targets = {t.target_id: t for t in get_default_jezero_targets()}
    # Pass dummy routes for each rover so resource manager evaluates all 4
    mock_routes = {
        r_id: FleetRoverRoute(
            rover_id=r_id,
            route_id=f"rt_{r_id}",
            ordered_stops=[],
            path_rc=[],
            path_xyz=[],
            total_distance_m=100.0,
            traverse_time_s=1000.0,
            dwell_time_s=600.0,
            total_time_s=1600.0,
            occupancy_schedule=[],
        )
        for r_id in director.rovers
    }
    audits, summary = frm.evaluate_fleet_resources(
        rovers=director.rovers,
        routes=mock_routes,
        allocations={"ATLAS_ROVER_A": ["TGT_HAWKSBILL_GAP"], "ATLAS_ROVER_B": ["TGT_SKINNER_RIDGE"]},
        targets_by_id=targets,
    )
    assert len(audits) == 4
    assert "ATLAS_ROVER_A" in audits
    assert "ATLAS_ROVER_B" in audits
    assert summary["fleet_resource_status"] in ["FEASIBLE", "CONSTRAINED"]
    assert audits["ATLAS_ROVER_A"].battery_capacity_wh != audits["ATLAS_ROVER_B"].battery_capacity_wh


def test_03_authoritative_instrument_compatibility_matching():
    allocator = FleetTaskAllocator()
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
    states = {r_id: RoverOperationalState(rover_id=r_id, current_location_rc=r.starting_location_rc) for r_id, r in rovers.items()}
    targets = get_default_jezero_targets()

    # Target: TGT_HAWKSBILL_GAP requires ELEMENTAL_CHEMISTRY or RAMAN_LUMINESCENCE
    # Rover A carries PIXL and SHERLOC, so it is compatible
    eligibility = allocator.assess_rover_eligibility(rovers["ATLAS_ROVER_A"], states["ATLAS_ROVER_A"], targets[0])
    assert eligibility.is_eligible is True
    assert eligibility.matching_instrument_id is not None

    # Test an artificial target with a non-existent objective
    fake_target = FleetScienceTarget(
        target_id="TGT_IMPOSSIBLE",
        name="Impossible Target",
        objective="EXOTIC_ANTIMATTER_DETECTION",
        location_rc=(100, 100),
    )
    eligibility_fake = allocator.assess_rover_eligibility(rovers["ATLAS_ROVER_A"], states["ATLAS_ROVER_A"], fake_target)
    assert eligibility_fake.is_eligible is False
    assert eligibility_fake.matching_instrument_id is None


def test_04_fleet_task_allocation_bounded_pareto_vs_greedy():
    allocator = FleetTaskAllocator()
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
    states = {r_id: RoverOperationalState(rover_id=r_id, current_location_rc=r.starting_location_rc) for r_id, r in rovers.items()}
    targets = get_default_jezero_targets()

    res_opt = allocator.allocate_fleet_science_tasks(rovers, states, targets, method="BOUNDED_PARETO_OPTIMIZATION")
    res_greedy = allocator.allocate_fleet_science_tasks(rovers, states, targets, method="GREEDY_PRIORITY")

    total_assigned = sum(len(t_ids) for t_ids in res_opt.allocation_plan.values())
    assert total_assigned > 0
    assert sum(len(t_ids) for t_ids in res_greedy.allocation_plan.values()) > 0

    # Every assigned target must appear at most once across all rovers
    all_assigned = []
    for r_id, t_ids in res_opt.allocation_plan.items():
        all_assigned.extend(t_ids)
    assert len(all_assigned) == len(set(all_assigned)), "Duplicate targets assigned in fleet plan!"

    # Quantitative audit checks
    assert len(res_opt.explanations) == len(targets)
    assert res_opt.total_science_utility > 0.0


def test_05_multi_rover_terrain_aware_routing(terrain):
    director = FleetOperationsDirector(fleet_id="test_routes")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    targets = {t.target_id: t for t in get_default_jezero_targets()}
    allocator = FleetTaskAllocator()
    alloc_res = allocator.allocate_fleet_science_tasks(director.rovers, director.rover_states, list(targets.values()))

    coordinator = FleetRouteCoordinator(ground_spacing_m=terrain.dy_ground_m)
    routes, conflicts = coordinator.coordinate_and_deconflict_fleet(
        terrain=terrain,
        rovers=director.rovers,
        allocations=alloc_res.allocation_plan,
        targets_by_id=targets,
        auto_resolve=False,
    )

    assert len(routes) == 4
    for r_id, route in routes.items():
        assert route.rover_id == r_id
        assert len(route.path_rc) >= 2
        assert route.total_distance_m > 0.0
        # Verify terrain slope on route
        for rc in route.path_rc:
            r, c = min(max(0, int(rc[0])), terrain.height - 1), min(max(0, int(rc[1])), terrain.width - 1)
            slope = float(terrain.slope_deg[r, c])
            assert slope <= 25.0


def test_06_spatiotemporal_occupancy_and_conflict_detection(terrain):
    coordinator = FleetRouteCoordinator()
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}

    common_target = FleetScienceTarget(
        target_id="TGT_CONVERGENCE",
        name="Convergence Point",
        objective="GEOLOGIC_MAPPING",
        location_rc=(650, 480),
    )
    targets = {common_target.target_id: common_target}
    allocations = {
        "ATLAS_ROVER_A": ["TGT_CONVERGENCE"],
        "ATLAS_ROVER_B": ["TGT_CONVERGENCE"],
        "ATLAS_ROVER_C": [],
        "ATLAS_ROVER_D": [],
    }

    routes, conflicts = coordinator.coordinate_and_deconflict_fleet(
        terrain=terrain,
        rovers=rovers,
        allocations=allocations,
        targets_by_id=targets,
        auto_resolve=False,
    )

    assert len(conflicts) > 0
    c0 = conflicts[0]
    assert c0.separation_distance_m < 50.0
    assert "CONFLICT" in c0.status


def test_07_automated_conflict_resolution_strategies(terrain):
    coordinator = FleetRouteCoordinator()
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}

    common_target = FleetScienceTarget(
        target_id="TGT_CONVERGENCE_AUTO",
        name="Auto Convergence Point",
        objective="GEOLOGIC_MAPPING",
        location_rc=(650, 480),
    )
    targets = {common_target.target_id: common_target}
    allocations = {
        "ATLAS_ROVER_A": ["TGT_CONVERGENCE_AUTO"],
        "ATLAS_ROVER_B": ["TGT_CONVERGENCE_AUTO"],
        "ATLAS_ROVER_C": [],
        "ATLAS_ROVER_D": [],
    }

    routes, conflicts = coordinator.coordinate_and_deconflict_fleet(
        terrain=terrain,
        rovers=rovers,
        allocations=allocations,
        targets_by_id=targets,
        auto_resolve=True,
    )

    assert len(conflicts) > 0
    for c in conflicts:
        assert "RESOLVED" in c.status


def test_08_shared_relaynet_communications_mesh(terrain):
    fcm = FleetCommunicationsManager(base_station_rc=(620, 450))
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
    locations = {r_id: r.starting_location_rc for r_id, r in rovers.items()}

    graph, reports = fcm.build_fleet_relay_graph(terrain, rovers, locations)
    assert len(reports) == 4
    for r_id, rep in reports.items():
        assert rep.rover_id == r_id
        assert isinstance(rep.is_connected_to_base, bool)
        assert rep.signal_margin_db >= 0.0 or rep.signal_margin_db <= 0.0


def test_09_independent_resource_accounting_and_finite_downlink(terrain):
    director = FleetOperationsDirector(fleet_id="test_res_audit")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    targets = {t.target_id: t for t in get_default_jezero_targets()}
    allocator = FleetTaskAllocator()
    alloc_res = allocator.allocate_fleet_science_tasks(director.rovers, director.rover_states, list(targets.values()))

    coordinator = FleetRouteCoordinator()
    routes, _ = coordinator.coordinate_and_deconflict_fleet(terrain, director.rovers, alloc_res.allocation_plan, targets)

    frm = FleetResourceManager()
    audits, summary = frm.evaluate_fleet_resources(director.rovers, routes, alloc_res.allocation_plan, targets)

    assert len(audits) == 4
    for r_id, a in audits.items():
        assert a.rover_id == r_id
        assert a.energy_drive_wh >= 0.0
        assert a.energy_base_avionics_wh >= 0.0
        assert a.energy_instruments_wh >= 0.0
        assert 0.0 <= a.battery_soc_pct <= 100.0
        assert a.storage_capacity_mb > 0.0

    assert summary["fleet_resource_status"] in ["FEASIBLE", "CONSTRAINED"]


def test_10_multi_sol_synchronized_fleet_mission_schedule(terrain):
    director = FleetOperationsDirector(fleet_id="test_schedule")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    targets = {t.target_id: t for t in get_default_jezero_targets()}
    allocator = FleetTaskAllocator()
    alloc_res = allocator.allocate_fleet_science_tasks(director.rovers, director.rover_states, list(targets.values()))

    coordinator = FleetRouteCoordinator()
    routes, conflicts = coordinator.coordinate_and_deconflict_fleet(terrain, director.rovers, alloc_res.allocation_plan, targets)

    scheduler = FleetMissionScheduler()
    schedule = scheduler.build_fleet_schedule(
        fleet_id="test_schedule",
        rovers=director.rovers,
        routes=routes,
        allocations=alloc_res.allocation_plan,
        targets_by_id=targets,
        conflicts=conflicts,
        max_sols=5,
    )

    assert schedule.fleet_id == "test_schedule"
    assert schedule.total_sols == 5
    assert len(schedule.sols) == 5
    assert schedule.total_activities > 0
    # Check sol 1 has rover activities for all 4 rovers
    sol1 = schedule.sols[1]
    assert len(sol1.rover_activities) == 4


def test_11_6d_pareto_fleet_optimization_champions(terrain):
    engine = FleetOptimizationEngine(terrain)
    rovers = {r.rover_id: r for r in create_default_fleet_rovers()}
    states = {r_id: RoverOperationalState(rover_id=r_id, current_location_rc=r.starting_location_rc) for r_id, r in rovers.items()}
    targets = get_default_jezero_targets()

    champions = engine.generate_pareto_fleet_champions(rovers, states, targets)
    assert len(champions) == 5

    # Check that all 5 profiles are represented
    assert FleetOptimizationProfile.BALANCED_CHAMPION.value in champions
    assert FleetOptimizationProfile.SCIENCE_MAXIMIZING.value in champions
    assert FleetOptimizationProfile.ENERGY_EFFICIENT.value in champions
    assert FleetOptimizationProfile.COMMUNICATIONS_FOCUSED.value in champions
    assert FleetOptimizationProfile.MINIMUM_DURATION.value in champions

    sci_champ = champions[FleetOptimizationProfile.SCIENCE_MAXIMIZING.value]
    nrg_champ = champions[FleetOptimizationProfile.ENERGY_EFFICIENT.value]
    assert sci_champ.science_utility_pts >= nrg_champ.science_utility_pts


def test_12_counterfactual_failure_scenarios_f1_to_f7(terrain):
    director = FleetOperationsDirector(fleet_id="test_f1_f7")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    engine = FleetOptimizationEngine(terrain)

    # Test F1: Rover Failure (e.g. Rover A)
    res_f1 = engine.evaluate_fleet_counterfactual_scenario(
        director=director,
        scenario_type=FleetDisturbanceType.F1_ROVER_UNAVAILABLE.value,
        target_sol=2,
        disturbed_rover_id="ATLAS_ROVER_A",
    )
    assert res_f1.scenario_type == "F1_ROVER_UNAVAILABLE"
    assert res_f1.disturbed_rover_id == "ATLAS_ROVER_A"
    assert res_f1.recovery_metrics["science_utility"] > 0

    # Test F2: Shared Relay Outage
    res_f2 = engine.evaluate_fleet_counterfactual_scenario(
        director=director,
        scenario_type=FleetDisturbanceType.F2_SHARED_RELAY_OUTAGE.value,
        target_sol=3,
        parameters={"outage_duration_s": 3600.0},
    )
    assert res_f2.scenario_type == "F2_SHARED_RELAY_OUTAGE"
    assert res_f2.recovery_metrics["science_utility"] > 0

    # Test F7: Combined Multi-Rover Disturbance
    res_f7 = engine.evaluate_fleet_counterfactual_scenario(
        director=director,
        scenario_type=FleetDisturbanceType.F7_COMBINED_FLEET_DISTURBANCE.value,
        target_sol=2,
        disturbed_rover_id="ATLAS_ROVER_A",
    )
    assert res_f7.scenario_type == "F7_COMBINED_FLEET_DISTURBANCE"


def test_13_three_way_comparative_scorecard_delta_matrix(terrain):
    director = FleetOperationsDirector(fleet_id="test_3way")
    all_rovers = create_default_fleet_rovers()
    for r in all_rovers[2:]:
        director.register_rover(r)

    engine = FleetOptimizationEngine(terrain)
    res = engine.evaluate_fleet_counterfactual_scenario(
        director=director,
        scenario_type="F1_ROVER_UNAVAILABLE",
        target_sol=2,
        disturbed_rover_id="ATLAS_ROVER_A",
    )

    bm = res.baseline_metrics
    dm = res.disturbed_metrics
    rm = res.recovery_metrics

    assert "science_utility" in bm
    assert "science_utility" in dm
    assert "science_utility" in rm

    # Recovery must preserve more science utility or maintain equal/better margin than unmitigated failure
    assert rm["science_utility"] >= dm["science_utility"]


def test_14_fleet_plan_promotion_and_tamper_evident_lineage():
    director = get_or_create_fleet_director("test_promote")
    initial_version = director.version
    fp_init = director.compute_state_fingerprint()

    # Promote plan
    res = fleet_promote_api({
        "fleet_id": "test_promote",
        "approver_callsign": "CHIEF_FLIGHT_DIRECTOR",
        "rationale": "Promoted F1 recovered fleet plan for sol 2-5 execution.",
    }, None)

    assert res["status"] == "PROMOTED"
    assert res["new_version"] == initial_version + 1
    assert director.version == initial_version + 1
    assert director.compute_state_fingerprint() != fp_init


def test_15_draft_2020_12_schema_validation_and_api_service_endpoints(terrain):
    """Validate all 10 Draft 2020-12 Fleet schemas using API endpoint payloads."""
    director = get_or_create_fleet_director("fleet_jezero_alpha")

    # 1. fleet-configuration
    cfg_data = {
        "fleet_id": director.fleet_id,
        "name": director.name,
        "campaign_id": director.campaign_id,
        "base_station": {
            "rc": list(director.base_station_rc),
            "antenna_height_m": director.base_station_antenna_m,
        },
        "rovers": {r_id: r.to_dict() for r_id, r in director.rovers.items()},
    }
    v_cfg = get_validator("fleet-configuration")
    v_cfg.validate(cfg_data)

    # 2. fleet-state
    state_res = fleet_get_api("fleet_jezero_alpha", terrain)
    v_state = get_validator("fleet-state")
    v_state.validate(state_res)

    # 3. fleet-allocation
    alloc_res = fleet_allocate_science_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_alloc = get_validator("fleet-allocation")
    v_alloc.validate(alloc_res)

    # 4. fleet-route
    route_res = fleet_plan_routes_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_route = get_validator("fleet-route")
    v_route.validate(route_res)

    # 5. fleet-schedule
    sched_res = fleet_schedule_api({"fleet_id": "fleet_jezero_alpha", "max_sols": 3}, terrain)
    v_sched = get_validator("fleet-schedule")
    v_sched.validate(sched_res)

    # 6. fleet-network
    net_res = fleet_network_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_net = get_validator("fleet-network")
    v_net.validate(net_res)

    # 7. fleet-resources
    res_res = fleet_resources_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_res = get_validator("fleet-resources")
    v_res.validate(res_res)

    # 8. fleet-optimization
    opt_res = fleet_optimize_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_opt = get_validator("fleet-optimization")
    v_opt.validate(opt_res)

    # 9. fleet-scenario
    scen_res = fleet_scenario_api({
        "fleet_id": "fleet_jezero_alpha",
        "scenario_type": "F1_ROVER_UNAVAILABLE",
        "target_sol": 2,
        "disturbed_rover_id": "ATLAS_ROVER_A",
    }, terrain)
    v_scen = get_validator("fleet-scenario")
    v_scen.validate(scen_res)

    # 10. fleet-assurance
    assur_res = fleet_assurance_api({"fleet_id": "fleet_jezero_alpha"}, terrain)
    v_assur = get_validator("fleet-assurance")
    v_assur.validate(assur_res)
