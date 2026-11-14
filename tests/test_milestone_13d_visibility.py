"""
Unit tests for Milestone 13D Terrain Visibility Engine (Line-of-Sight).
Covers analytical fixtures (flat, ridge, grazing, asymmetric, NoData, degenerate, out of range)
and authentic Jezero Crater DTM waypoints.
"""

import math
import numpy as np
import pytest

from marswalk.core.terrain_visibility import (
    calculate_line_of_sight,
    sample_bilinear_elevation,
    LineOfSightResult,
    ObstructionPoint,
    DEFAULT_DX_M,
    DEFAULT_DY_M,
)


class TestAnalyticalLOSFixtures:
    """Test suite for analytical geometric line-of-sight test fixtures."""

    def test_flat_terrain_unobstructed(self):
        """Flat terrain with positive antenna heights should always be VISIBLE."""
        grid = np.zeros((50, 50), dtype=np.float32)
        res = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=2.0,
            antenna_h_b=2.0,
            dx_m=20.0,
            dy_m=20.0,
        )
        assert res.status == "VISIBLE"
        assert res.is_visible is True
        assert res.is_terrain_blocked is False
        assert res.first_obstruction is None
        assert math.isclose(res.min_clearance_m, 2.0, abs_tol=1e-4)
        assert math.isclose(res.ground_distance_m, 400.0, abs_tol=1e-3)

    def test_raised_ridge_midpoint_blocked(self):
        """A raised ridge in the middle of two low antennas should be BLOCKED."""
        grid = np.zeros((50, 50), dtype=np.float32)
        grid[:, 20] = 10.0  # 10m ridge at column 20

        res = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=2.0,
            antenna_h_b=2.0,
            dx_m=20.0,
            dy_m=20.0,
        )
        assert res.status == "BLOCKED"
        assert res.is_visible is False
        assert res.is_terrain_blocked is True
        assert res.first_obstruction is not None
        assert 0.45 <= res.first_obstruction.t <= 0.52
        assert res.min_clearance_m <= -8.0  # Peak is 10m, ray height is 2m -> clearance -8m

    def test_grazing_line_of_sight(self):
        """Grazing ray tangent to ridge crest: blocked when h <= ridge, clear when h > ridge."""
        grid = np.zeros((50, 50), dtype=np.float32)
        grid[:, 20] = 5.0  # 5m ridge

        # Grazing tangent (h=5.0): clearance at peak is 0.0 -> BLOCKED (clearance <= margin)
        res_grazing = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=5.0,
            antenna_h_b=5.0,
            dx_m=20.0,
            dy_m=20.0,
            clearance_margin_m=0.0,
        )
        assert res_grazing.status == "BLOCKED"
        assert res_grazing.is_terrain_blocked is True
        assert math.isclose(res_grazing.min_clearance_m, 0.0, abs_tol=1e-4)

        # Grazing elevated (h=5.2m): clearance at peak is 0.2m > 0 -> VISIBLE
        res_clear = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=5.2,
            antenna_h_b=5.2,
            dx_m=20.0,
            dy_m=20.0,
            clearance_margin_m=0.0,
        )
        assert res_clear.status == "VISIBLE"
        assert res_clear.is_visible is True
        assert math.isclose(res_clear.min_clearance_m, 0.2, abs_tol=1e-4)

    def test_asymmetric_elevations(self):
        """Plateau at A (100m) descending to base at B (0m) over intermediate hill (50m vs 80m)."""
        grid = np.zeros((50, 50), dtype=np.float32)
        grid[10, 10] = 100.0
        grid[:, 15] = 50.0  # At t=0.25, ray altitude is 102 - 0.25*100 = 77m > 50m

        res_clear = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=2.0,
            antenna_h_b=2.0,
            dx_m=20.0,
            dy_m=20.0,
        )
        assert res_clear.status == "VISIBLE"

        # Raise hill to 85m at col 15 (t=0.25, ray is 77m -> blocked by 8m)
        grid[:, 15] = 85.0
        res_blocked = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=2.0,
            antenna_h_b=2.0,
            dx_m=20.0,
            dy_m=20.0,
        )
        assert res_blocked.status == "BLOCKED"
        assert res_blocked.first_obstruction is not None
        assert math.isclose(res_blocked.first_obstruction.col, 15.0, abs_tol=1.0)

    def test_nodata_detection_returns_unknown(self):
        """Any sample encountering NoData sentinel must yield UNKNOWN status."""
        grid = np.zeros((50, 50), dtype=np.float32)
        grid[10, 20] = -32768.0  # Sentinel NoData in path

        res = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 30.0),
            antenna_h_a=2.0,
            antenna_h_b=2.0,
        )
        assert res.status == "UNKNOWN"
        assert res.is_visible is False
        assert "NoData" in (res.reason or "")

    def test_degenerate_identical_endpoints(self):
        """Zero ground distance path should return VISIBLE with clearance min(hA, hB)."""
        grid = np.zeros((50, 50), dtype=np.float32)
        res = calculate_line_of_sight(
            grid,
            point_a=(15.0, 15.0),
            point_b=(15.0, 15.0),
            antenna_h_a=2.5,
            antenna_h_b=10.0,
        )
        assert res.status == "VISIBLE"
        assert res.ground_distance_m == 0.0
        assert math.isclose(res.min_clearance_m, 2.5, abs_tol=1e-4)

    def test_range_limit_boundary(self):
        """Distance exceeding max_range_m flags OUT_OF_RANGE independently of LOS."""
        grid = np.zeros((50, 50), dtype=np.float32)
        # Distance is 200m
        res_in_range = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 20.0),
            dx_m=20.0,
            dy_m=20.0,
            max_range_m=250.0,
        )
        assert res_in_range.status == "VISIBLE"
        assert res_in_range.is_out_of_range is False

        res_out_of_range = calculate_line_of_sight(
            grid,
            point_a=(10.0, 10.0),
            point_b=(10.0, 20.0),
            dx_m=20.0,
            dy_m=20.0,
            max_range_m=150.0,
        )
        assert res_out_of_range.status == "OUT_OF_RANGE"
        assert res_out_of_range.is_out_of_range is True
        assert res_out_of_range.is_terrain_blocked is False

    def test_out_of_bounds_input(self):
        """Coordinates outside raster domain should return UNKNOWN or INVALID_INPUT."""
        grid = np.zeros((50, 50), dtype=np.float32)
        res = calculate_line_of_sight(
            grid,
            point_a=(-5.0, 10.0),
            point_b=(10.0, 60.0),
        )
        assert res.status in ["UNKNOWN", "INVALID_INPUT"]
        assert res.is_visible is False


class TestJezeroCraterLineOfSight:
    """Test suite using authentic USGS Jezero Crater 20m elevation data."""

    @pytest.fixture
    def jezero_grid(self):
        import json
        with open("web/data/jezero_mission_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return np.array(data["elevation_samples"], dtype=np.float32)

    def test_jezero_landing_to_artuby_visible(self, jezero_grid):
        """Landing site (117, 157) to Artuby Ridge (132, 152) has unobstructed line of sight."""
        res = calculate_line_of_sight(
            jezero_grid,
            point_a=(117.0, 157.0),
            point_b=(132.0, 152.0),
            antenna_h_a=2.0,
            antenna_h_b=5.0,
            dx_m=DEFAULT_DX_M,
            dy_m=DEFAULT_DY_M,
            max_range_m=3000.0,
        )
        assert res.status == "VISIBLE"
        assert res.is_visible is True
        assert res.is_terrain_blocked is False
        assert res.ground_distance_m < 400.0

    def test_jezero_landing_to_three_forks_blocked(self, jezero_grid):
        """Landing site (117, 157) to Three Forks (138, 114) is blocked by intermediate relief."""
        res = calculate_line_of_sight(
            jezero_grid,
            point_a=(117.0, 157.0),
            point_b=(138.0, 114.0),
            antenna_h_a=2.0,
            antenna_h_b=5.0,
            dx_m=DEFAULT_DX_M,
            dy_m=DEFAULT_DY_M,
            max_range_m=3000.0,
        )
        assert res.status == "BLOCKED"
        assert res.is_terrain_blocked is True
        assert res.first_obstruction is not None
        assert res.min_clearance_m < 0.0

    def test_serialization_to_dict(self, jezero_grid):
        """Test to_dict produces valid JSON-compatible structure with scientific disclosures."""
        res = calculate_line_of_sight(
            jezero_grid,
            point_a=(117.0, 157.0),
            point_b=(138.0, 114.0),
            antenna_h_a=2.0,
            antenna_h_b=10.0,
        )
        d = res.to_dict()
        assert d["endpoint_a_id"] == "node_a"
        assert d["status"] in ["VISIBLE", "BLOCKED"]
        assert "USGS" in d["source_attribution"]
        assert "scientific_disclaimer" in d
        assert isinstance(d["ground_distance_m"], float)
