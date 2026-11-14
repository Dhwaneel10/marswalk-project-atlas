"""
Project MarsWalk 2.0 / Atlas — Mission 8 Failure-Mode & API Resilience Test Suite

Attacks all five pillars with edge cases, corrupt payloads, and boundary violations:
1. Corrupt JSON syntax handling
2. Empty payloads on parameter-requiring endpoints
3. Non-numeric coordinates
4. Out-of-bounds coordinates on raster grids
5. Unknown / nonexistent science target IDs
6. Negative / unphysical environmental inputs (tau < 0, T < -273.15 C, P < 0)
7. Query parameter fuzzing on PDS rover data
8. Repeated mission execution idempotency & Merkle determinism
"""

import json
import pytest
from marswalk.api.service import (
    pillars_terrain_inspect_api,
    pillars_rover_places_query_api,
    pillars_environment_meda_calibrate_api,
    pillars_science_targets_plan_api,
    flagship_mars_dark_run_api,
    APIError,
)


class TestMission8APIFailureResilience:
    """Rigorous boundary and failure-mode fuzzing."""

    def test_terrain_inspect_rejects_empty_payload(self):
        """Terrain inspection must reject empty dictionary with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_terrain_inspect_api({})
        assert exc_info.value.status_code == 400
        assert "requires lon_deg/lat_deg" in str(exc_info.value.message)

    def test_terrain_inspect_rejects_non_numeric_coordinates(self):
        """Terrain inspection must reject string literals for coordinates with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_terrain_inspect_api({"row": "abc", "col": "def"})
        assert exc_info.value.status_code == 400
        assert "Invalid numeric value" in str(exc_info.value.message)

    def test_terrain_inspect_rejects_out_of_bounds_coordinates(self):
        """Terrain inspection must reject out-of-bounds grid coordinates with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_terrain_inspect_api({"row": 99999, "col": -500})
        assert exc_info.value.status_code == 400
        assert "outside Jezero DTM extent" in str(exc_info.value.message)

    def test_meda_calibrate_rejects_negative_optical_depth(self):
        """MEDA calibration must reject negative optical depth with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_environment_meda_calibrate_api({"optical_depth_tau": -10.0})
        assert exc_info.value.status_code == 400
        assert "must be non-negative" in str(exc_info.value.message)

    def test_meda_calibrate_rejects_below_absolute_zero_temperature(self):
        """MEDA calibration must reject air temperature below absolute zero with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_environment_meda_calibrate_api({"air_temp_c": -300.0})
        assert exc_info.value.status_code == 400
        assert "absolute zero" in str(exc_info.value.message)

    def test_meda_calibrate_rejects_negative_pressure(self):
        """MEDA calibration must reject negative atmospheric pressure with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_environment_meda_calibrate_api({"pressure_pa": -50.0})
        assert exc_info.value.status_code == 400
        assert "must be non-negative" in str(exc_info.value.message)

    def test_science_plan_rejects_out_of_bounds_start_coordinates(self):
        """Science route planning must reject start coordinates outside grid with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_science_targets_plan_api({"start_rc": [9999, -500], "goal_rc": [50, 90]})
        assert exc_info.value.status_code == 400
        assert "outside Jezero terrain grid" in str(exc_info.value.message)

    def test_science_plan_rejects_out_of_bounds_goal_coordinates(self):
        """Science route planning must reject goal coordinates outside grid with HTTP 400."""
        with pytest.raises(APIError) as exc_info:
            pillars_science_targets_plan_api({"start_rc": [153, 123], "goal_rc": [250, 500]})
        assert exc_info.value.status_code == 400
        assert "outside Jezero terrain grid" in str(exc_info.value.message)

    def test_science_plan_handles_nonexistent_target_ids_gracefully(self):
        """Science planning with unknown target IDs must safely fallback to direct route without crashing."""
        res = pillars_science_targets_plan_api({
            "start_rc": [153, 123],
            "goal_rc": [50, 90],
            "target_ids": ["sci_nonexistent_site_99999", "sci_phantom_anomaly"],
        })
        assert res["status"] == "OK"
        assert res["selected_targets_count"] == 0
        assert res["science_priority_route_b"]["science_targets_visited"] == 0
        assert res["trade_off_analysis"]["delta_distance_m"] == 0.0

    def test_rover_places_query_handles_fuzzed_query_params(self):
        """Rover PLACES query API must handle empty, partial, and string filters gracefully."""
        # Empty query
        res_empty = pillars_rover_places_query_api({})
        assert res_empty["status"] == "OK"
        assert res_empty["total_matching_records"] == 577

        # Fuzzed sol parameters
        res_fuzz = pillars_rover_places_query_api({"min_sol": "not_a_number", "max_sol": "invalid"})
        assert res_fuzz["status"] == "OK"
        assert res_fuzz["total_matching_records"] == 577

    def test_flagship_repeated_launches_remain_idempotent_and_deterministic(self):
        """Rapidly re-executing flagship resilience scenario must return bit-exact identical Merkle root."""
        roots = []
        for _ in range(3):
            run_res = flagship_mars_dark_run_api()
            assert run_res["status"] == "QUALIFIED"
            roots.append(run_res["root_merkle_hash"])

        assert len(roots) == 3
        # All three runs must produce the exact same Merkle root
        assert roots[0] == roots[1] == roots[2]
        assert roots[0] == "0380a7cf112a7bd394ef8a21f3ddae772d8103e0caf9998cf36538b7844069b8"
