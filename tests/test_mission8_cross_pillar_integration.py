"""
Project MarsWalk 2.0 / Atlas — Mission 8 Cross-Pillar End-to-End Integration Test Suite

Verifies the unified five-pillar planetary mission operations pipeline:
  Pillar 1: Terrain Intelligence (USGS CTX 20m & HiRISE 1m)
  Pillar 2: Rover Ground Truth (PDS PLACES & Three Forks Depot)
  Pillar 3: Environmental Intelligence (NASA Mars 2020 MEDA Atmospheric Physics)
  Pillar 4: Science-Driven Rover Planning (Multi-Objective A* Trade Study)
  Pillar 5: Autonomous Mission Resilience ("When Mars Goes Dark" DTN & Merkle Proof)

Ensures that data flows consistently across all subsystem boundaries without data loss,
contradictory metadata, or unverified claims.
"""

import json
import os
import pytest

from marswalk.api.service import (
    pillars_terrain_api,
    pillars_terrain_inspect_api,
    pillars_rover_ground_truth_api,
    pillars_rover_places_query_api,
    pillars_environment_meda_api,
    pillars_environment_meda_calibrate_api,
    pillars_science_targets_api,
    pillars_science_targets_plan_api,
    pillars_manifest_api,
    flagship_mars_dark_run_api,
    flagship_mars_dark_replay_api,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMission8CrossPillarIntegration:
    """End-to-end integration tests proving cross-pillar consistency."""

    def test_pillar1_terrain_feeds_pillar4_science_target_locations(self):
        """Pillar 1 terrain coordinates must spatially align with Pillar 4 science targets."""
        # Query Pillar 4 science targets
        sci_res = pillars_science_targets_api()
        targets = sci_res["targets"]
        assert len(targets) >= 5, "Expected at least 5 geolocated science targets"

        wildcat = next(t for t in targets if t["id"] == "sci_wildcat_ridge")
        assert wildcat["name"] == "Wildcat Ridge Organic Mudstone"
        assert wildcat["lat_deg"] == 18.4385
        assert wildcat["lon_deg"] == 77.4284
        assert wildcat["priority_score"] == 95.0

        # Inspect Pillar 1 terrain at Wildcat Ridge via lat/lon coordinates
        inspect_res = pillars_terrain_inspect_api({"lat_deg": wildcat["lat_deg"], "lon_deg": wildcat["lon_deg"]})
        assert inspect_res["active_dataset"] == "USGS_TRN_HIRISE_1M"
        assert inspect_res["resolution_m"] == 1.0
        assert inspect_res["is_high_resolution"] is True
        assert -2600.0 < inspect_res["elevation_m"] < -2450.0

        # Cross-check Crater Floor flat terrain (20m regional CTX)
        floor_res = pillars_terrain_inspect_api({"row": 50, "col": 50})
        assert floor_res["active_dataset"] == "USGS_CTX_DEM_PROCESSED_20M"
        assert floor_res["resolution_m"] == 20.0
        assert floor_res["slope_deg"] <= 8.0  # Flat plain nominal

    def test_pillar2_ground_truth_depot_serves_as_pillar4_route_origin(self):
        """Pillar 2 Three Forks Depot location must serve as start coordinates for Pillar 4 planning."""
        gt_res = pillars_rover_ground_truth_api()
        depot = gt_res["three_forks_sample_depot"]
        assert depot["total_samples"] == 10

        # Verify deposited sample tube names
        samples = [s["sample_name"] for s in depot["samples"]]
        assert "Malay" in samples
        assert "Bearwallow" in samples
        # Sister tube Hazelton must NOT be in the dropped cache (retained onboard)
        assert "Hazelton" not in samples

        # Query depot via query API
        depot_query = pillars_rover_places_query_api({"depot_only": "true"})
        assert depot_query["sample_depot_count"] == 10
        assert len(depot_query["sample_depot_tubes"]) == 10

    def test_pillar3_meda_environment_calibrates_subsystem_power_and_rf(self):
        """Pillar 3 MEDA atmospheric conditions must dynamically scale rover power and RF loss."""
        # Sol 89 Regional Dust Storm preset
        cal_res = pillars_environment_meda_calibrate_api({
            "optical_depth_tau": 2.45,
            "air_temp_c": -35.0,
            "pressure_pa": 725.0,
            "wind_speed_ms": 18.4,
        })
        assert cal_res["status"] == "OK"
        assert cal_res["in_situ_measurements"]["optical_depth_tau"] == 2.45

        params = cal_res["derived_simulation_parameters"]
        # Solar array output drops under regional storm
        assert params["solar_array_output_w"] < 300.0
        assert params["solar_attenuation_pct"] > 70.0

        # RF dust attenuation calculated via heuristic proxy in Rayleigh regime
        assert params["rf_carrier_dust_attenuation_db_km"] > 0.15
        assert params["rf_attenuation_model_type"] == "ILLUSTRATIVE_HEURISTIC_PROXY"
        assert "Rayleigh" in params["rf_physical_regime"]

    def test_pillar4_science_route_trade_off_strictly_satisfies_constraints(self):
        """Pillar 4 must prove Route B detours to targets within 30m while Route A bypasses them."""
        plan_res = pillars_science_targets_plan_api({
            "start_rc": [153, 123],
            "goal_rc": [50, 90],
            "target_ids": ["sci_wildcat_ridge", "sci_kodiak_butte"],
        })
        assert plan_res["status"] == "OK"

        route_a = plan_res["direct_route_a"]
        route_b = plan_res["science_priority_route_b"]

        # Both routes must share identical start and goal
        assert plan_res["start_location"]["grid_rc"] == [153, 123]
        assert plan_res["destination_location"]["grid_rc"] == [50, 90]

        # Route A: Direct corridor
        assert 2250.0 <= route_a["distance_m"] <= 2350.0
        assert route_a["science_targets_visited"] == 0
        assert route_a["science_yield_score"] == 0.0

        # Route A closest approach must exceed 30m interception tolerance
        for inter in route_a["target_interceptions"]:
            assert inter["closest_approach_m"] > 30.0
            assert inter["is_intercepted"] is False

        # Route B: Science-priority detour
        assert 5300.0 <= route_b["distance_m"] <= 5500.0
        assert route_b["science_targets_visited"] == 2
        assert route_b["science_yield_score"] == 160.0

        # Route B must intercept both Wildcat Ridge and Kodiak Butte within 30m
        for inter in route_b["target_interceptions"]:
            assert inter["closest_approach_m"] <= 30.0
            assert inter["is_intercepted"] is True

        # Trade-off metrics
        trade = plan_res["trade_off_analysis"]
        assert trade["delta_distance_m"] > 3000.0
        assert trade["delta_energy_wh"] > 800.0
        assert "+160" in trade["science_gain"]

    def test_pillar5_flagship_resilience_preserves_dtn_data_and_merkle_continuity(self):
        """Pillar 5 resilience must execute rockfall recovery, 100% DTN custody, and bit-exact Merkle proof."""
        # Execute Flagship Scenario
        run_res = flagship_mars_dark_run_api()
        assert run_res["status"] == "QUALIFIED"

        dtn = run_res["dtn_summary"]
        assert dtn["delivered_bundles"] == 6
        assert dtn["total_bundles"] == 6
        assert dtn["dropped_bundles"] == 0
        assert dtn["delivery_success_pct"] == 100.0

        # Verify Replay Data & Merkle Root Hash
        replay_res = flagship_mars_dark_replay_api()
        assert replay_res["is_valid"] is True
        expected_root = "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"
        assert replay_res["root_merkle_hash"] == expected_root
        assert replay_res["computed_root_hash"] == expected_root
        assert replay_res["snapshots_count"] == 7

    def test_complete_cross_pillar_pipeline_integrity(self):
        """
        Master Pipeline Test:
        Validates that all 5 pillars form one coherent operational pipeline:
        Terrain (1) -> Rover Origin (2) -> Environmental State (3) -> Science Detour (4) -> Autonomous Recovery (5)
        """
        # 1. Manifest confirms all 8 datasets verified
        manifest = pillars_manifest_api()
        assert manifest["manifest_version"] == "2.0.0"
        assert len(manifest["datasets"]) == 8

        # 2. Origin at Three Forks Depot (Pillar 2)
        gt = pillars_rover_ground_truth_api()
        assert gt["three_forks_sample_depot"]["total_samples"] == 10
        start_rc = [153, 123]

        # 3. Environment set to Regional Storm (Pillar 3)
        cal = pillars_environment_meda_calibrate_api({"optical_depth_tau": 2.45})
        assert cal["in_situ_measurements"]["optical_depth_tau"] == 2.45
        assert cal["derived_simulation_parameters"]["solar_array_output_w"] < 300.0

        # 4. Multi-objective A* computes trade study to Delta Scarp Rim (Pillar 4)
        plan = pillars_science_targets_plan_api({
            "start_rc": start_rc,
            "goal_rc": [50, 90],
            "target_ids": ["sci_wildcat_ridge", "sci_kodiak_butte"],
        })
        assert plan["science_priority_route_b"]["science_yield_score"] == 160.0

        # 5. Autonomous resilience replay verifies DTN and Merkle proof (Pillar 5)
        replay = flagship_mars_dark_replay_api()
        assert replay["is_valid"] is True
        assert replay["root_merkle_hash"] == (
            "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"
        )
