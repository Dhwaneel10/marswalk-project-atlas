"""
Automated unit tests for Milestone 12C: Terrain Intelligence Engine.
Covers profile extraction, NoData preservation, segment difficulties, slope distributions,
cost decomposition reconciliation, bottleneck detection, and route comparisons.
"""

import math
import os
import pytest
import numpy as np

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    derive_terrain_from_array,
    load_and_process_terrain,
)
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    VehicleMode,
    plan_route,
)
from marswalk.core.terrain_intelligence import (
    TerrainProfileSample,
    TerrainProfile,
    SegmentTerrainDifficulty,
    RouteCostDecomposition,
    RouteTerrainAnalysis,
    extract_route_elevation_profile,
    compute_segment_difficulties,
    compute_slope_distribution,
    decompose_route_cost,
    generate_terrain_decision_explanations,
    analyze_route_terrain,
    compare_route_terrain_analyses,
    TERRAIN_INTELLIGENCE_DISCLAIMER,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_TIFF = os.path.join(REPO_ROOT, "data", "processed", "jezero_ready_20m.tif")


@pytest.fixture
def flat_terrain():
    H, W = 50, 50
    elev = np.full((H, W), -2500.0, dtype=np.float32)
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=1.0,
        alpha_r=1.0,
        alpha_up=1.5,
    )
    return derive_terrain_from_array(elev, config=cfg)


@pytest.fixture
def ramp_terrain():
    """
    Ramp terrain sloping upward from West to East (col 0 to col 49).
    Height rises 10m every cell (col), which is ~10m / 20m = 0.5 grade (~26.5 deg).
    """
    H, W = 50, 50
    elev = np.zeros((H, W), dtype=np.float32)
    for c in range(W):
        elev[:, c] = -2500.0 + c * 5.0  # 5m rise per 20m cell (~14 deg)
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        alpha_s=1.0,
        alpha_r=0.5,
        alpha_up=1.5,
    )
    return derive_terrain_from_array(elev, config=cfg)


@pytest.fixture
def nodata_terrain():
    """
    Terrain with an invalid / NoData hole in the center.
    """
    H, W = 50, 50
    elev = np.full((H, W), -2500.0, dtype=np.float32)
    # Mask out columns 20 to 25
    elev[:, 20:26] = -9999.0
    cfg = TerrainConfig(
        cell_size_m=20.0,
        dx_ground_m=20.0,
        dy_ground_m=20.0,
        nodata_sentinel=-9999.0,
        alpha_s=1.0,
        alpha_r=1.0,
        alpha_up=1.5,
    )
    return derive_terrain_from_array(elev, config=cfg)


# ==============================================================================
# 1. PROFILE EXTRACTION & NODATA PRESERVATION
# ==============================================================================

def test_extract_profile_flat_terrain(flat_terrain):
    path = [(10, c) for c in range(10, 21)]  # 11 points, 10 steps along East-West
    prof = extract_route_elevation_profile(path, flat_terrain)

    assert prof.sample_count == 11
    assert prof.valid_sample_count == 11
    assert prof.missing_sample_count == 0
    assert prof.data_completeness_pct == 100.0
    assert prof.total_distance_m == pytest.approx(200.0, rel=1e-2)
    assert prof.min_elevation_m == pytest.approx(-2500.0, rel=1e-2)
    assert prof.max_elevation_m == pytest.approx(-2500.0, rel=1e-2)
    assert prof.total_elevation_gain_m == pytest.approx(0.0, abs=1e-2)
    assert prof.total_elevation_loss_m == pytest.approx(0.0, abs=1e-2)

    # Check individual samples
    assert len(prof.samples) == 11
    for i, s in enumerate(prof.samples):
        assert s.sample_index == i
        assert s.row == 10
        assert s.col == 10 + i
        assert s.is_valid is True
        assert s.is_nodata is False
        assert s.elevation_m == pytest.approx(-2500.0, rel=1e-2)
        assert s.slope_deg == pytest.approx(0.0, abs=1e-2)


def test_extract_profile_nodata_preservation(nodata_terrain):
    """
    CRITICAL SCIENTIFIC INVARIANT: Missing or invalid raster cells MUST be
    represented as None / is_nodata=True, and NEVER filled with fake 0.0m.
    """
    path = [(15, c) for c in range(18, 28)]  # crosses cols 20..25 (which are invalid/dilated)
    prof = extract_route_elevation_profile(path, nodata_terrain)

    assert prof.sample_count == 10
    assert prof.missing_sample_count > 0
    assert prof.data_completeness_pct < 100.0

    # Ensure no invalid sample has elevation == 0.0
    for s in prof.samples:
        if not s.is_valid or s.is_nodata:
            assert s.elevation_m is None, "NoData sample MUST NOT have numeric elevation"
            assert s.is_nodata is True


def test_extract_profile_edge_cases(flat_terrain):
    # Empty path
    prof_empty = extract_route_elevation_profile([], flat_terrain)
    assert prof_empty.sample_count == 0
    assert prof_empty.total_distance_m == 0.0
    assert prof_empty.min_elevation_m is None

    # Single point
    prof_single = extract_route_elevation_profile([(10, 10)], flat_terrain)
    assert prof_single.sample_count == 1
    assert prof_single.total_distance_m == 0.0
    assert prof_single.valid_sample_count == 1

    # Stationary duplicates
    prof_dup = extract_route_elevation_profile([(10, 10), (10, 10), (10, 11)], flat_terrain)
    assert prof_dup.sample_count == 3
    assert prof_dup.total_distance_m == pytest.approx(20.0, rel=1e-2)

    # Out of bounds points
    prof_oob = extract_route_elevation_profile([(10, 10), (-1, -1), (100, 100)], flat_terrain)
    assert prof_oob.sample_count == 3
    assert prof_oob.missing_sample_count >= 2
    assert prof_oob.samples[1].is_valid is False
    assert prof_oob.samples[1].elevation_m is None


# ==============================================================================
# 2. RAMP TERRAIN, ELEVATION GAIN & SLOPE DISTRIBUTION
# ==============================================================================

def test_extract_profile_ramp_gain(ramp_terrain):
    # Moving East (uphill): from col 10 to 20
    path_uphill = [(20, c) for c in range(10, 21)]
    prof_uphill = extract_route_elevation_profile(path_uphill, ramp_terrain)

    expected_gain = 10 * 5.0  # 50m rise
    assert prof_uphill.total_elevation_gain_m == pytest.approx(expected_gain, rel=1e-2)
    assert prof_uphill.total_elevation_loss_m == pytest.approx(0.0, abs=1e-2)

    # Moving West (downhill): from col 20 to 10
    path_downhill = [(20, c) for c in range(20, 9, -1)]
    prof_downhill = extract_route_elevation_profile(path_downhill, ramp_terrain)
    assert prof_downhill.total_elevation_loss_m == pytest.approx(expected_gain, rel=1e-2)
    assert prof_downhill.total_elevation_gain_m == pytest.approx(0.0, abs=1e-2)


def test_slope_distribution(ramp_terrain):
    path = [(20, c) for c in range(10, 30)]
    prof = extract_route_elevation_profile(path, ramp_terrain)
    slope_dist = compute_slope_distribution(prof)

    assert "bins" in slope_dist
    assert "mean_slope_deg" in slope_dist
    assert "p50_slope_deg" in slope_dist
    assert "p90_slope_deg" in slope_dist
    assert slope_dist["mean_slope_deg"] > 10.0  # ~14 deg ramp
    assert 0.0 <= slope_dist["steep_fraction_pct"] <= 100.0


# ==============================================================================
# 3. SEGMENT DIFFICULTIES & BOTTLENECK CLASSIFICATION
# ==============================================================================

def test_compute_segment_difficulties(ramp_terrain):
    path = [(20, c) for c in range(5, 35)]  # 30 points
    prof = extract_route_elevation_profile(path, ramp_terrain)
    segments = compute_segment_difficulties(prof, segment_target_len=10)

    assert len(segments) >= 2
    for seg in segments:
        assert isinstance(seg, SegmentTerrainDifficulty)
        assert seg.distance_m > 0
        assert seg.p50_slope_deg >= 0
        assert seg.p90_slope_deg >= seg.p50_slope_deg
        assert seg.difficulty_rating in ["MODERATE", "STEEP", "DIFFICULT", "EXTREME", "INCOMPLETE_DATA"]
        d = seg.to_dict()
        assert "start_rc" in d and "end_rc" in d


# ==============================================================================
# 4. STRICT COST DECOMPOSITION RECONCILIATION
# ==============================================================================

def test_cost_decomposition_strict_reconciliation(ramp_terrain):
    path = [(20, c) for c in range(10, 25)]
    prof = extract_route_elevation_profile(path, ramp_terrain)
    decomp = decompose_route_cost(prof)

    assert isinstance(decomp, RouteCostDecomposition)
    assert decomp.is_strictly_reconciled is True
    assert abs(decomp.reconciliation_delta_m) < 0.05
    assert decomp.total_cost_m >= decomp.base_distance_cost_m
    assert decomp.slope_penalty_cost_m >= 0.0
    assert decomp.roughness_penalty_cost_m >= 0.0
    assert decomp.uphill_grade_cost_m >= 0.0

    d = decomp.to_dict()
    assert d["is_strictly_reconciled"] is True
    reconstructed = (
        d["base_distance_cost_m"]
        + d["slope_penalty_cost_m"]
        + d["roughness_penalty_cost_m"]
        + d["uphill_grade_cost_m"]
    )
    assert reconstructed == pytest.approx(d["total_cost_m"], abs=0.2)


# ==============================================================================
# 5. HIGH-LEVEL ROUTE TERRAIN ANALYSIS & EXPLANATIONS
# ==============================================================================

def test_analyze_route_terrain_end_to_end(ramp_terrain):
    path = [(20, c) for c in range(10, 25)]
    analysis = analyze_route_terrain(
        path=path,
        terrain=ramp_terrain,
        profile="conservative",
        vehicle_mode=VehicleMode.CREW_EVA,
        route_id="test-traverse-101",
    )

    assert isinstance(analysis, RouteTerrainAnalysis)
    assert analysis.route_id == "test-traverse-101"
    assert analysis.profile == "conservative"
    assert analysis.vehicle_mode == "crew_eva"
    assert analysis.terrain_profile.valid_sample_count == 15
    assert len(analysis.decision_explanations) > 0
    assert TERRAIN_INTELLIGENCE_DISCLAIMER in analysis.limitations_disclaimer

    # Test serialization to dict
    data = analysis.to_dict()
    assert data["route_id"] == "test-traverse-101"
    assert "cost_decomposition" in data
    assert "slope_distribution" in data
    assert "segments" in data
    assert len(data["segments"]) > 0


# ==============================================================================
# 6. FAIR ROUTE COMPARISON (MULTI-OBJECTIVE TRADEOFFS)
# ==============================================================================

def test_compare_route_terrain_analyses(ramp_terrain):
    # Plan A: gentle horizontal line along row 20
    path_a = [(20, c) for c in range(10, 20)]
    analysis_a = analyze_route_terrain(
        path=path_a,
        terrain=ramp_terrain,
        profile="conservative",
        route_id="route-plan-a",
    )

    # Plan B: longer detour through row 25
    path_b = [(20, 10)] + [(25, c) for c in range(11, 20)] + [(20, 19)]
    analysis_b = analyze_route_terrain(
        path=path_b,
        terrain=ramp_terrain,
        profile="conservative",
        route_id="route-plan-b",
    )

    comp = compare_route_terrain_analyses(
        analysis_a,
        analysis_b,
        title_a="Direct Route",
        title_b="Detour Route",
    )

    assert comp["title_a"] == "Direct Route"
    assert comp["title_b"] == "Detour Route"
    assert "deltas" in comp
    assert "distance_delta_m" in comp["deltas"]
    assert "cost_delta_m" in comp["deltas"]
    assert "elevation_gain_delta_m" in comp["deltas"]
    assert "max_slope_delta_deg" in comp["deltas"]
    assert "metrics_table" in comp
    assert len(comp["tradeoff_narratives"]) > 0


def test_compare_identical_routes(flat_terrain):
    path = [(10, c) for c in range(10, 20)]
    anl = analyze_route_terrain(path=path, terrain=flat_terrain, profile="conservative")
    comp = compare_route_terrain_analyses(anl, anl, title_a="Base", title_b="Duplicate")

    assert comp["deltas"]["distance_delta_m"] == 0.0
    assert comp["deltas"]["cost_delta_m"] == 0.0
    assert comp["deltas"]["elevation_gain_delta_m"] == 0.0
    assert comp["deltas"]["max_slope_delta_deg"] == 0.0
    assert comp["deltas"]["data_completeness_delta_pct"] == 0.0


def test_compare_with_nodata_route(flat_terrain, nodata_terrain):
    path_good = [(15, c) for c in range(10, 20)]
    path_nodata = [(15, c) for c in range(18, 28)]

    anl_good = analyze_route_terrain(path=path_good, terrain=flat_terrain)
    anl_nodata = analyze_route_terrain(path=path_nodata, terrain=nodata_terrain)

    comp = compare_route_terrain_analyses(anl_good, anl_nodata, title_a="Complete", title_b="Gapped")
    assert comp["deltas"]["data_completeness_delta_pct"] < 0.0
    assert any("Data completeness distinction" in n for n in comp["tradeoff_narratives"])


# ==============================================================================
# 7. REAL JEZERO CTX RASTER VALIDATION (IF DATA EXISTS)
# ==============================================================================

@pytest.mark.skipif(not os.path.exists(PROCESSED_TIFF), reason="Jezero CTX geotiff not present")
def test_real_jezero_ctx_terrain_profile():
    terrain = load_and_process_terrain(PROCESSED_TIFF)
    # Plan a short 10-step route inside Jezero crater basin
    # Search for a valid starting point
    H, W = terrain.shape
    start = None
    for r in range(100, 150):
        for c in range(100, 150):
            if not terrain.invalid_mask[r, c]:
                start = (r, c)
                break
        if start:
            break

    assert start is not None, "Could not find valid cell in Jezero terrain"
    path = [start]
    curr = start
    for _ in range(10):
        next_rc = (curr[0], curr[1] + 1)
        if next_rc[1] < W and not terrain.invalid_mask[next_rc[0], next_rc[1]]:
            path.append(next_rc)
            curr = next_rc
        else:
            break

    analysis = analyze_route_terrain(
        path=path,
        terrain=terrain,
        transform=terrain.transform,
        profile="conservative",
        route_id="jezero-ctx-test",
    )

    assert analysis.terrain_profile.data_completeness_pct == 100.0
    assert analysis.terrain_profile.total_distance_m > 0
    # IAU 2000 Mars reference check
    assert analysis.terrain_profile.source_metadata["reference_datum"] == "IAU 2000 Mars Reference Sphere (R=3,396,190m)"
    # Check that lon and lat are georeferenced
    first_sample = analysis.terrain_profile.samples[0]
    assert first_sample.lon_deg is not None
    assert first_sample.lat_deg is not None
    assert 76.0 <= first_sample.lon_deg <= 78.5  # Jezero Crater longitude window
    assert 17.5 <= first_sample.lat_deg <= 19.5  # Jezero Crater latitude window
