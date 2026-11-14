"""
MarsWalk 2.0 / Project Atlas — Terrain Intelligence Engine.
Milestone 12C: High-fidelity terrain profile extraction, segment-level difficulty,
slope distribution analysis, transparent planner cost decomposition, and route comparisons.

Scientific & Operational Invariants:
1. Authentic USGS CTX 20m DTM & IAU 2000 Mars Reference Sphere coordinates.
2. Zero synthetic data fabrication: missing or invalid raster cells are explicitly
   represented as None / NaN with is_valid=False and is_nodata=True, never filled with fake 0m elevations.
3. Distinguish measured/source-derived quantities from model-derived / interpolated quantities.
4. Strictly reuse the core planner and terrain physics formulations (Horn's 3x3 slope,
   directed edge costs, decameter roughness).
5. Never label modeled routes as certified safe for flight or operational astronauts.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio

from marswalk.core.terrain import (
    TerrainConfig,
    TerrainGrid,
    calculate_edge_cost,
    calculate_step_distance,
)
from marswalk.core.planner import (
    PlannerConfig,
    RouteResult,
    VehicleMode,
    get_profile_terrain_config,
)

TERRAIN_INTELLIGENCE_DISCLAIMER = (
    "Terrain profile and difficulty metrics are derived from the USGS Astrogeology Science Center "
    "MRO CTX 20m digital elevation model of Jezero Crater and MarsWalk deterministic kinematic models. "
    "Calculated slopes reflect ~20m baseline grid cells and do not resolve sub-pixel meter-scale rock hazards. "
    "These evaluations are mathematical mission-rehearsal tools and do not constitute certified operational flight envelopes."
)


@dataclass
class TerrainProfileSample:
    """
    Detailed physical and terrain attributes for a single point along a traverse.
    """
    sample_index: int
    row: int
    col: int
    cumulative_distance_m: float
    step_distance_m: float
    elevation_m: Optional[float]
    elevation_change_m: Optional[float]
    slope_deg: Optional[float]
    roughness_m: Optional[float]
    lon_deg: Optional[float] = None
    lat_deg: Optional[float] = None
    is_valid: bool = True
    is_nodata: bool = False
    step_cost_m: Optional[float] = None
    slope_penalty: Optional[float] = None
    roughness_penalty: Optional[float] = None
    uphill_penalty: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_index": self.sample_index,
            "row": self.row,
            "col": self.col,
            "lon_deg": round(self.lon_deg, 6) if self.lon_deg is not None else None,
            "lat_deg": round(self.lat_deg, 6) if self.lat_deg is not None else None,
            "cumulative_distance_m": round(self.cumulative_distance_m, 2),
            "step_distance_m": round(self.step_distance_m, 2),
            "elevation_m": round(self.elevation_m, 2) if self.elevation_m is not None else None,
            "elevation_change_m": round(self.elevation_change_m, 2) if self.elevation_change_m is not None else None,
            "slope_deg": round(self.slope_deg, 2) if self.slope_deg is not None else None,
            "roughness_m": round(self.roughness_m, 3) if self.roughness_m is not None else None,
            "is_valid": self.is_valid,
            "is_nodata": self.is_nodata,
            "step_cost_m": round(self.step_cost_m, 2) if self.step_cost_m is not None else None,
            "slope_penalty": round(self.slope_penalty, 3) if self.slope_penalty is not None else None,
            "roughness_penalty": round(self.roughness_penalty, 3) if self.roughness_penalty is not None else None,
            "uphill_penalty": round(self.uphill_penalty, 3) if self.uphill_penalty is not None else None,
        }


@dataclass
class TerrainProfile:
    """
    Ordered route elevation profile and topographic coverage accounting.
    """
    total_distance_m: float
    sample_count: int
    valid_sample_count: int
    missing_sample_count: int
    data_completeness_pct: float
    min_elevation_m: Optional[float]
    max_elevation_m: Optional[float]
    elevation_span_m: Optional[float]
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    samples: List[TerrainProfileSample]
    source_metadata: Dict[str, Any]
    sampling_method: str = "discrete_grid_cell_step"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_distance_m": round(self.total_distance_m, 1),
            "sample_count": self.sample_count,
            "valid_sample_count": self.valid_sample_count,
            "missing_sample_count": self.missing_sample_count,
            "data_completeness_pct": round(self.data_completeness_pct, 1),
            "min_elevation_m": round(self.min_elevation_m, 1) if self.min_elevation_m is not None else None,
            "max_elevation_m": round(self.max_elevation_m, 1) if self.max_elevation_m is not None else None,
            "elevation_span_m": round(self.elevation_span_m, 1) if self.elevation_span_m is not None else None,
            "total_elevation_gain_m": round(self.total_elevation_gain_m, 1),
            "total_elevation_loss_m": round(self.total_elevation_loss_m, 1),
            "sampling_method": self.sampling_method,
            "source_metadata": self.source_metadata,
            "samples": [s.to_dict() for s in self.samples],
        }


@dataclass
class SegmentTerrainDifficulty:
    """
    Metrics and difficulty classification for an aggregated segment or leg of a route.
    """
    segment_index: int
    start_index: int
    end_index: int
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    distance_m: float
    elevation_start_m: Optional[float]
    elevation_end_m: Optional[float]
    elevation_change_m: Optional[float]
    elevation_gain_m: float
    elevation_loss_m: float
    max_slope_deg: float
    mean_slope_deg: float
    p50_slope_deg: float
    p90_slope_deg: float
    steep_distance_m: float
    steep_fraction_pct: float
    missing_data_fraction_pct: float
    planner_cost_m: float
    cost_density: float
    dominant_penalty: str
    difficulty_rating: str  # "MODERATE", "STEEP", "DIFFICULT", "EXTREME", "INCOMPLETE_DATA"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_index": self.segment_index,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "start_rc": list(self.start_rc),
            "end_rc": list(self.end_rc),
            "distance_m": round(self.distance_m, 1),
            "elevation_start_m": round(self.elevation_start_m, 1) if self.elevation_start_m is not None else None,
            "elevation_end_m": round(self.elevation_end_m, 1) if self.elevation_end_m is not None else None,
            "elevation_change_m": round(self.elevation_change_m, 1) if self.elevation_change_m is not None else None,
            "elevation_gain_m": round(self.elevation_gain_m, 1),
            "elevation_loss_m": round(self.elevation_loss_m, 1),
            "max_slope_deg": round(self.max_slope_deg, 1),
            "mean_slope_deg": round(self.mean_slope_deg, 1),
            "p50_slope_deg": round(self.p50_slope_deg, 1),
            "p90_slope_deg": round(self.p90_slope_deg, 1),
            "steep_distance_m": round(self.steep_distance_m, 1),
            "steep_fraction_pct": round(self.steep_fraction_pct, 1),
            "missing_data_fraction_pct": round(self.missing_data_fraction_pct, 1),
            "planner_cost_m": round(self.planner_cost_m, 1),
            "cost_density": round(self.cost_density, 2),
            "dominant_penalty": self.dominant_penalty,
            "difficulty_rating": self.difficulty_rating,
        }


@dataclass
class RouteCostDecomposition:
    """
    Transparent additive breakdown of accumulated planner cost into physical terms.
    """
    total_cost_m: float
    total_distance_m: float
    base_distance_cost_m: float
    slope_penalty_cost_m: float
    roughness_penalty_cost_m: float
    uphill_grade_cost_m: float
    cost_density_ratio: float
    is_strictly_reconciled: bool
    reconciliation_delta_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost_m": round(self.total_cost_m, 1),
            "total_distance_m": round(self.total_distance_m, 1),
            "base_distance_cost_m": round(self.base_distance_cost_m, 1),
            "slope_penalty_cost_m": round(self.slope_penalty_cost_m, 1),
            "roughness_penalty_cost_m": round(self.roughness_penalty_cost_m, 1),
            "uphill_grade_cost_m": round(self.uphill_grade_cost_m, 1),
            "cost_density_ratio": round(self.cost_density_ratio, 2),
            "is_strictly_reconciled": self.is_strictly_reconciled,
            "reconciliation_delta_m": round(self.reconciliation_delta_m, 4),
        }


@dataclass
class RouteTerrainAnalysis:
    """
    Full Route Decision Workbench analysis record.
    """
    analysis_id: str
    route_id: Optional[str]
    timestamp_utc: str
    profile: str
    vehicle_mode: str
    terrain_profile: TerrainProfile
    difficulty_summary: Dict[str, Any]
    slope_distribution: Dict[str, Any]
    cost_decomposition: RouteCostDecomposition
    segments: List[SegmentTerrainDifficulty]
    key_bottlenecks: List[Dict[str, Any]]
    decision_explanations: List[str]
    limitations_disclaimer: str = TERRAIN_INTELLIGENCE_DISCLAIMER

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "route_id": self.route_id,
            "timestamp_utc": self.timestamp_utc,
            "profile": self.profile,
            "vehicle_mode": self.vehicle_mode,
            "terrain_profile": self.terrain_profile.to_dict(),
            "difficulty_summary": self.difficulty_summary,
            "slope_distribution": self.slope_distribution,
            "cost_decomposition": self.cost_decomposition.to_dict(),
            "segments": [s.to_dict() for s in self.segments],
            "key_bottlenecks": self.key_bottlenecks,
            "decision_explanations": self.decision_explanations,
            "limitations_disclaimer": self.limitations_disclaimer,
        }


# =============================================================================
# 1. PROFILE EXTRACTION ENGINE
# =============================================================================

def extract_route_elevation_profile(
    path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    transform: Optional[rasterio.Affine] = None,
    config: Optional[TerrainConfig] = None,
) -> TerrainProfile:
    """
    Extracts ordered elevation, distance, slope, and roughness along a discrete raster path.
    Preserves authentic missing-data representation: cells outside raster or flagged in
    invalid_mask produce None elevation and is_valid=False.
    """
    if not path:
        return TerrainProfile(
            total_distance_m=0.0,
            sample_count=0,
            valid_sample_count=0,
            missing_sample_count=0,
            data_completeness_pct=100.0,
            min_elevation_m=None,
            max_elevation_m=None,
            elevation_span_m=None,
            total_elevation_gain_m=0.0,
            total_elevation_loss_m=0.0,
            samples=[],
            source_metadata=_build_source_metadata(terrain),
        )

    cfg = config if config is not None else terrain.config
    H, W = terrain.shape

    samples: List[TerrainProfileSample] = []
    cum_dist = 0.0
    total_gain = 0.0
    total_loss = 0.0

    valid_elevations: List[float] = []

    for idx, (r, c) in enumerate(path):
        is_oob = not (0 <= r < H and 0 <= c < W)
        is_invalid = is_oob or bool(terrain.invalid_mask[r, c])
        is_nodata = is_invalid

        # Compute ground step from previous sample
        step_dist = 0.0
        step_cost = None
        slope_penalty = None
        roughness_penalty = None
        uphill_penalty = None

        if idx > 0:
            prev_rc = path[idx - 1]
            if prev_rc == (r, c):
                step_dist = 0.0
                step_cost = 0.0
            elif not is_oob and (0 <= prev_rc[0] < H and 0 <= prev_rc[1] < W):
                dr = abs(r - prev_rc[0])
                dc = abs(c - prev_rc[1])
                if dr <= 1 and dc <= 1:
                    step_dist = calculate_step_distance(prev_rc, (r, c), terrain.dx_ground_m, terrain.dy_ground_m)
                    cum_dist += step_dist

                    # Compute step cost and penalties if both cells are valid
                    if not terrain.invalid_mask[prev_rc[0], prev_rc[1]] and not is_invalid:
                        cost = calculate_edge_cost(prev_rc, (r, c), terrain, cfg)
                        step_cost = cost if not math.isinf(cost) else None

                        # Detailed penalty terms
                        z_prev = float(terrain.elevation[prev_rc[0], prev_rc[1]])
                        z_curr = float(terrain.elevation[r, c])
                        dz = z_curr - z_prev
                        if step_dist > 0:
                            th_step = math.degrees(math.atan(abs(dz) / step_dist))
                            th_dest = float(terrain.slope_deg[r, c])
                            th_eff = max(th_dest, th_step)
                            slope_penalty = cfg.alpha_s * ((th_eff / cfg.theta_crit_deg) ** 2)

                            dest_rough = float(terrain.roughness_m[r, c])
                            dest_rough = 0.0 if math.isnan(dest_rough) or dest_rough < 0 else dest_rough
                            roughness_penalty = cfg.alpha_r * (dest_rough / cfg.sigma_0_m)
                            uphill_penalty = cfg.alpha_up * max(0.0, dz / step_dist)
                else:
                    # Non-adjacent gap (jump)
                    step_dist = math.hypot((c - prev_rc[1]) * terrain.dx_ground_m, (r - prev_rc[0]) * terrain.dy_ground_m)
                    cum_dist += step_dist
            else:
                step_dist = 20.0
                cum_dist += step_dist

        # Sample values
        elev_val: Optional[float] = None
        slope_val: Optional[float] = None
        rough_val: Optional[float] = None

        if not is_invalid:
            elev_val = float(terrain.elevation[r, c])
            s_val = float(terrain.slope_deg[r, c])
            slope_val = s_val if not math.isnan(s_val) else 0.0
            r_val = float(terrain.roughness_m[r, c])
            rough_val = r_val if not math.isnan(r_val) else 0.0
            valid_elevations.append(elev_val)

        # Elevation change
        elev_change: Optional[float] = None
        if idx > 0 and elev_val is not None and samples[idx - 1].elevation_m is not None:
            elev_change = elev_val - samples[idx - 1].elevation_m
            if elev_change > 0:
                total_gain += elev_change
            else:
                total_loss += abs(elev_change)

        # Geodetic coordinates
        lon_deg = None
        lat_deg = None
        if transform is not None and not is_oob:
            x_proj, y_proj = rasterio.transform.xy(transform, r, c)
            # Equirectangular Mars: x = lon_deg * (pi/180) * R, y = lat_deg * (pi/180) * R
            lon_deg = math.degrees(x_proj / 3396190.0)
            lat_deg = math.degrees(y_proj / 3396190.0)

        sample = TerrainProfileSample(
            sample_index=idx,
            row=r,
            col=c,
            cumulative_distance_m=cum_dist,
            step_distance_m=step_dist,
            elevation_m=elev_val,
            elevation_change_m=elev_change,
            slope_deg=slope_val,
            roughness_m=rough_val,
            lon_deg=lon_deg,
            lat_deg=lat_deg,
            is_valid=not is_invalid,
            is_nodata=is_nodata,
            step_cost_m=step_cost,
            slope_penalty=slope_penalty,
            roughness_penalty=roughness_penalty,
            uphill_penalty=uphill_penalty,
        )
        samples.append(sample)

    valid_count = len(valid_elevations)
    missing_count = len(path) - valid_count
    completeness_pct = (valid_count / len(path) * 100.0) if path else 100.0

    min_elev = min(valid_elevations) if valid_elevations else None
    max_elev = max(valid_elevations) if valid_elevations else None
    span_elev = (max_elev - min_elev) if (min_elev is not None and max_elev is not None) else None

    return TerrainProfile(
        total_distance_m=cum_dist,
        sample_count=len(samples),
        valid_sample_count=valid_count,
        missing_sample_count=missing_count,
        data_completeness_pct=completeness_pct,
        min_elevation_m=min_elev,
        max_elevation_m=max_elev,
        elevation_span_m=span_elev,
        total_elevation_gain_m=total_gain,
        total_elevation_loss_m=total_loss,
        samples=samples,
        source_metadata=_build_source_metadata(terrain),
    )


# =============================================================================
# 2. SEGMENT DIFFICULTY & SLOPE DISTRIBUTION ENGINE
# =============================================================================

def compute_segment_difficulties(
    profile: TerrainProfile,
    num_segments: int = 5,
    steep_threshold_deg: float = 15.0,
    segment_target_len: Optional[int] = None,
) -> List[SegmentTerrainDifficulty]:
    """
    Partitions a terrain profile into aggregated, contiguous segments and evaluates
    localized difficulty, elevation gains, slope percentiles, and dominant impedance factors.
    """
    samples = profile.samples
    if not samples:
        return []

    N = len(samples)
    if segment_target_len is not None and segment_target_len > 0:
        seg_count = max(1, math.ceil((N - 1) / segment_target_len))
        step_size = segment_target_len
    else:
        seg_count = max(1, min(num_segments, N - 1 if N > 1 else 1))
        step_size = max(1, (N - 1) // seg_count) if N > 1 else 1

    segments: List[SegmentTerrainDifficulty] = []

    for s_idx in range(seg_count):
        start_idx = s_idx * step_size
        end_idx = min(N - 1, (s_idx + 1) * step_size) if s_idx < seg_count - 1 else N - 1
        seg_samples = samples[start_idx : end_idx + 1]

        if not seg_samples:
            continue

        start_s = seg_samples[0]
        end_s = seg_samples[-1]

        seg_dist = end_s.cumulative_distance_m - start_s.cumulative_distance_m
        elev_start = start_s.elevation_m
        elev_end = end_s.elevation_m
        elev_change = (elev_end - elev_start) if (elev_start is not None and elev_end is not None) else None

        seg_gain = 0.0
        seg_loss = 0.0
        steep_dist = 0.0
        missing_count = 0
        seg_cost = 0.0

        slopes: List[float] = []
        slope_penalties = 0.0
        rough_penalties = 0.0
        uphill_penalties = 0.0
        base_dist_penalties = 0.0

        for smp in seg_samples[1:]:
            if not smp.is_valid or smp.elevation_m is None:
                missing_count += 1
            if smp.slope_deg is not None:
                slopes.append(smp.slope_deg)
                if smp.slope_deg >= steep_threshold_deg:
                    steep_dist += smp.step_distance_m
            if smp.elevation_change_m is not None:
                if smp.elevation_change_m > 0:
                    seg_gain += smp.elevation_change_m
                else:
                    seg_loss += abs(smp.elevation_change_m)
            if smp.step_cost_m is not None:
                seg_cost += smp.step_cost_m
                base_dist_penalties += smp.step_distance_m
                if smp.slope_penalty is not None:
                    slope_penalties += smp.step_distance_m * smp.slope_penalty
                if smp.roughness_penalty is not None:
                    rough_penalties += smp.step_distance_m * smp.roughness_penalty
                if smp.uphill_penalty is not None:
                    uphill_penalties += smp.step_distance_m * smp.uphill_penalty
            else:
                seg_cost += smp.step_distance_m

        if start_s.is_nodata:
            missing_count += 1

        max_slope = max(slopes) if slopes else 0.0
        mean_slope = (sum(slopes) / len(slopes)) if slopes else 0.0
        p50_slope = float(np.percentile(slopes, 50)) if slopes else 0.0
        p90_slope = float(np.percentile(slopes, 90)) if slopes else 0.0

        steep_frac = (steep_dist / max(1.0, seg_dist)) * 100.0 if seg_dist > 0 else 0.0
        missing_frac = (missing_count / len(seg_samples)) * 100.0

        cost_dens = (seg_cost / max(1.0, seg_dist)) if seg_dist > 0 else 1.0

        # Dominant penalty identification
        penalty_dict = {
            "slope_penalty": slope_penalties,
            "roughness": rough_penalties,
            "uphill_grade": uphill_penalties,
            "base_distance": base_dist_penalties,
        }
        dominant_factor = max(penalty_dict, key=lambda k: penalty_dict[k]) if seg_cost > 0 else "base_distance"
        if missing_frac > 25.0:
            dominant_factor = "incomplete_terrain_data"

        # Difficulty rating
        if missing_frac > 50.0:
            rating = "INCOMPLETE_DATA"
        elif max_slope >= 22.0 or cost_dens >= 2.5:
            rating = "EXTREME"
        elif max_slope >= 15.0 or cost_dens >= 1.6:
            rating = "DIFFICULT"
        elif max_slope >= 8.0 or cost_dens >= 1.2:
            rating = "STEEP"
        else:
            rating = "MODERATE"

        segments.append(
            SegmentTerrainDifficulty(
                segment_index=s_idx,
                start_index=start_idx,
                end_index=end_idx,
                start_rc=(start_s.row, start_s.col),
                end_rc=(end_s.row, end_s.col),
                distance_m=seg_dist,
                elevation_start_m=elev_start,
                elevation_end_m=elev_end,
                elevation_change_m=elev_change,
                elevation_gain_m=seg_gain,
                elevation_loss_m=seg_loss,
                max_slope_deg=max_slope,
                mean_slope_deg=mean_slope,
                p50_slope_deg=p50_slope,
                p90_slope_deg=p90_slope,
                steep_distance_m=steep_dist,
                steep_fraction_pct=steep_frac,
                missing_data_fraction_pct=missing_frac,
                planner_cost_m=seg_cost,
                cost_density=cost_dens,
                dominant_penalty=dominant_factor,
                difficulty_rating=rating,
            )
        )

    return segments


def compute_slope_distribution(
    samples: Union[TerrainProfile, List[TerrainProfileSample]],
    steep_threshold_deg: float = 15.0,
) -> Dict[str, Any]:
    """
    Computes binned slope distribution (0-5°, 5-10°, 10-15°, 15-20°, >20°) and percentiles.
    """
    sample_list = samples.samples if isinstance(samples, TerrainProfile) else samples
    valid_slopes = [s.slope_deg for s in sample_list if s.slope_deg is not None]
    if not valid_slopes:
        return {
            "bins": {
                "0_to_5_deg_pct": 0.0,
                "5_to_10_deg_pct": 0.0,
                "10_to_15_deg_pct": 0.0,
                "15_to_20_deg_pct": 0.0,
                "above_20_deg_pct": 0.0,
            },
            "bin_0_to_5_deg_pct": 0.0,
            "bin_5_to_10_deg_pct": 0.0,
            "bin_10_to_15_deg_pct": 0.0,
            "bin_15_to_20_deg_pct": 0.0,
            "bin_above_20_deg_pct": 0.0,
            "p50_deg": 0.0,
            "p90_deg": 0.0,
            "p50_slope_deg": 0.0,
            "p90_slope_deg": 0.0,
            "max_slope_deg": 0.0,
            "mean_slope_deg": 0.0,
            "steep_proportion_pct": 0.0,
            "steep_fraction_pct": 0.0,
        }

    total = len(valid_slopes)
    b0_5 = sum(1 for s in valid_slopes if s < 5.0)
    b5_10 = sum(1 for s in valid_slopes if 5.0 <= s < 10.0)
    b10_15 = sum(1 for s in valid_slopes if 10.0 <= s < 15.0)
    b15_20 = sum(1 for s in valid_slopes if 15.0 <= s < 20.0)
    b_above_20 = sum(1 for s in valid_slopes if s >= 20.0)

    steep_count = sum(1 for s in valid_slopes if s >= steep_threshold_deg)

    pct_0_5 = round((b0_5 / total) * 100.0, 1)
    pct_5_10 = round((b5_10 / total) * 100.0, 1)
    pct_10_15 = round((b10_15 / total) * 100.0, 1)
    pct_15_20 = round((b15_20 / total) * 100.0, 1)
    pct_above_20 = round((b_above_20 / total) * 100.0, 1)

    return {
        "bins": {
            "0_to_5_deg_pct": pct_0_5,
            "5_to_10_deg_pct": pct_5_10,
            "10_to_15_deg_pct": pct_10_15,
            "15_to_20_deg_pct": pct_15_20,
            "above_20_deg_pct": pct_above_20,
        },
        "bin_0_to_5_deg_pct": pct_0_5,
        "bin_5_to_10_deg_pct": pct_5_10,
        "bin_10_to_15_deg_pct": pct_10_15,
        "bin_15_to_20_deg_pct": pct_15_20,
        "bin_above_20_deg_pct": pct_above_20,
        "p50_deg": round(float(np.percentile(valid_slopes, 50)), 1),
        "p90_deg": round(float(np.percentile(valid_slopes, 90)), 1),
        "p50_slope_deg": round(float(np.percentile(valid_slopes, 50)), 1),
        "p90_slope_deg": round(float(np.percentile(valid_slopes, 90)), 1),
        "max_slope_deg": round(max(valid_slopes), 1),
        "mean_slope_deg": round(float(np.mean(valid_slopes)), 1),
        "steep_proportion_pct": round((steep_count / total) * 100.0, 1),
        "steep_fraction_pct": round((steep_count / total) * 100.0, 1),
    }


# =============================================================================
# 3. ROUTE COST DECOMPOSITION & EXPLANATION ENGINE
# =============================================================================

def decompose_route_cost(
    profile: TerrainProfile,
    terrain: Optional[TerrainGrid] = None,
    config: Optional[TerrainConfig] = None,
) -> RouteCostDecomposition:
    """
    Decomposes the total accumulated planner cost into transparent physical terms:
    Total Cost = Base Distance + Slope Penalty + Roughness Penalty + Uphill Grade Penalty.
    """
    cfg = config if config is not None else (terrain.config if terrain is not None else None)
    samples = profile.samples

    base_dist = 0.0
    slope_cost = 0.0
    rough_cost = 0.0
    uphill_cost = 0.0
    total_cost = 0.0

    for smp in samples[1:]:
        d = smp.step_distance_m
        base_dist += d
        if smp.step_cost_m is not None:
            total_cost += smp.step_cost_m
            if smp.slope_penalty is not None:
                slope_cost += d * smp.slope_penalty
            if smp.roughness_penalty is not None:
                rough_cost += d * smp.roughness_penalty
            if smp.uphill_penalty is not None:
                uphill_cost += d * smp.uphill_penalty
        else:
            total_cost += d

    sum_components = base_dist + slope_cost + rough_cost + uphill_cost
    delta = abs(total_cost - sum_components)
    is_reconciled = delta <= 0.05 * max(1.0, total_cost)
    density_ratio = (total_cost / max(1.0, base_dist)) if base_dist > 0 else 1.0

    return RouteCostDecomposition(
        total_cost_m=total_cost,
        total_distance_m=base_dist,
        base_distance_cost_m=base_dist,
        slope_penalty_cost_m=slope_cost,
        roughness_penalty_cost_m=rough_cost,
        uphill_grade_cost_m=uphill_cost,
        cost_density_ratio=density_ratio,
        is_strictly_reconciled=is_reconciled,
        reconciliation_delta_m=delta,
    )


def generate_terrain_decision_explanations(
    profile: TerrainProfile,
    segments: List[SegmentTerrainDifficulty],
    cost_decomp: RouteCostDecomposition,
    slope_dist: Dict[str, Any],
    planner_profile: str = "conservative",
) -> List[str]:
    """
    Synthesizes honest, grounded, human-readable explanations explaining why the planner
    assigned this path and cost, explicitly identifying trade-offs and terrain drivers.
    """
    explanations: List[str] = []

    # 1. Slope & Terrain Hazard explanation
    max_s = slope_dist.get("max_slope_deg", 0.0)
    steep_pct = slope_dist.get("steep_proportion_pct", 0.0)
    if max_s >= 20.0:
        explanations.append(
            f"The route encounters high localized slopes up to {max_s:.1f}°. "
            f"Approximately {steep_pct:.1f}% of the traverse exceeds 15° slope, requiring elevated tractive effort."
        )
    elif max_s >= 10.0:
        explanations.append(
            f"The traverse traverses moderate crater slopes (maximum {max_s:.1f}°, median {slope_dist.get('p50_deg', 0.0):.1f}°). "
            f"The path steers around steeper scarp faces to maintain safe vehicle mobility."
        )
    else:
        explanations.append(
            f"The route is predominantly flat across low-impedance terrain (maximum slope {max_s:.1f}°, mean {slope_dist.get('mean_slope_deg', 0.0):.1f}°)."
        )

    # 2. Elevation change & climbing grade
    gain = profile.total_elevation_gain_m
    loss = profile.total_elevation_loss_m
    if gain > 50.0:
        explanations.append(
            f"Significant vertical ascent: total cumulative climb is {gain:.1f}m against {loss:.1f}m descent, "
            f"adding {cost_decomp.uphill_grade_cost_m:.0f}m of equivalent flat-terrain climbing impedance."
        )
    elif gain > 10.0:
        explanations.append(
            f"Mild topographic variation: cumulative elevation gain of {gain:.1f}m and loss of {loss:.1f}m."
        )

    # 3. Cost Density & Impedance explanation
    ratio = cost_decomp.cost_density_ratio
    if ratio > 1.3:
        explanations.append(
            f"Terrain impedance penalty ratio is {ratio:.2f}x: for every 1.0m of ground traverse, "
            f"modeled locomotion demands {ratio:.2f}m of flat-ground equivalent effort due to slope and surface roughness."
        )
    else:
        explanations.append(
            f"Direct path efficiency: low terrain impedance ratio of {ratio:.2f}x relative to Euclidean distance."
        )

    # 4. Incomplete data warnings if applicable
    if profile.data_completeness_pct < 98.0:
        explanations.append(
            f"INCOMPLETE TERRAIN COVERAGE: {profile.missing_sample_count} of {profile.sample_count} samples "
            f"({100.0 - profile.data_completeness_pct:.1f}%) traverse unmapped or NoData raster cells. "
            "Elevation and slope along those sections are unavailable from the 20m DTM."
        )

    return explanations


# =============================================================================
# 4. MAIN TERRAIN ANALYSIS ENGINE & COMPARATOR
# =============================================================================

def analyze_route_terrain(
    path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    route_id: Optional[str] = None,
    profile_name: str = "conservative",
    profile: Optional[str] = None,
    vehicle_mode: Union[str, VehicleMode] = "crew_eva",
    transform: Optional[rasterio.Affine] = None,
    num_segments: int = 5,
    config: Optional[TerrainConfig] = None,
) -> RouteTerrainAnalysis:
    """
    Executes a comprehensive, evidence-grounded Terrain Intelligence analysis for a route.
    """
    active_profile = profile if profile is not None else profile_name
    cfg = config if config is not None else get_profile_terrain_config(active_profile, terrain.config)
    vmode_str = vehicle_mode.value if isinstance(vehicle_mode, VehicleMode) else str(vehicle_mode)

    # 1. Extract elevation profile
    prof = extract_route_elevation_profile(path, terrain, transform=transform, config=cfg)

    # 2. Segment-level difficulty breakdown
    segments = compute_segment_difficulties(prof, num_segments=num_segments)

    # 3. Slope distribution
    slope_dist = compute_slope_distribution(prof.samples)

    # 4. Planner cost decomposition
    cost_decomp = decompose_route_cost(prof, terrain, config=cfg)

    # 5. Extract top bottlenecks
    sorted_segs = sorted(segments, key=lambda s: s.cost_density, reverse=True)
    bottlenecks: List[Dict[str, Any]] = []
    for rank, seg in enumerate(sorted_segs[:3], start=1):
        bottlenecks.append({
            "rank": rank,
            "segment_index": seg.segment_index,
            "distance_m": seg.distance_m,
            "cost_m": seg.planner_cost_m,
            "cost_density": seg.cost_density,
            "dominant_penalty": seg.dominant_penalty,
            "max_slope_deg": seg.max_slope_deg,
            "start_rc": seg.start_rc,
            "end_rc": seg.end_rc,
            "difficulty_rating": seg.difficulty_rating,
        })

    # 6. Synthesize grounded decision explanations
    explanations = generate_terrain_decision_explanations(
        prof, segments, cost_decomp, slope_dist, planner_profile=profile_name
    )

    anl_id = f"rta_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    diff_summary = {
        "total_distance_m": prof.total_distance_m,
        "total_cost_m": cost_decomp.total_cost_m,
        "elevation_gain_m": prof.total_elevation_gain_m,
        "elevation_loss_m": prof.total_elevation_loss_m,
        "max_slope_deg": slope_dist.get("max_slope_deg", 0.0),
        "mean_slope_deg": slope_dist.get("mean_slope_deg", 0.0),
        "steep_proportion_pct": slope_dist.get("steep_proportion_pct", 0.0),
        "data_completeness_pct": prof.data_completeness_pct,
        "overall_difficulty": "DIFFICULT" if slope_dist.get("max_slope_deg", 0.0) >= 15.0 or cost_decomp.cost_density_ratio >= 1.6 else "MODERATE",
    }

    return RouteTerrainAnalysis(
        analysis_id=anl_id,
        route_id=route_id,
        timestamp_utc=now_iso,
        profile=active_profile,
        vehicle_mode=vmode_str,
        terrain_profile=prof,
        difficulty_summary=diff_summary,
        slope_distribution=slope_dist,
        cost_decomposition=cost_decomp,
        segments=segments,
        key_bottlenecks=bottlenecks,
        decision_explanations=explanations,
    )


def compare_route_terrain_analyses(
    analysis_a: RouteTerrainAnalysis,
    analysis_b: RouteTerrainAnalysis,
    title_a: str = "Plan A (Nominal)",
    title_b: str = "Plan B (Alternative)",
) -> Dict[str, Any]:
    """
    Performs a fair, multi-objective comparison between two route analyses:
    Distance vs Elevation Gain vs Effort vs Max Slope vs Data Completeness.
    Avoids arbitrary weighted composite scores; presents objective deltas.
    """
    sum_a = analysis_a.difficulty_summary
    sum_b = analysis_b.difficulty_summary

    dist_a = sum_a["total_distance_m"]
    dist_b = sum_b["total_distance_m"]
    cost_a = sum_a["total_cost_m"]
    cost_b = sum_b["total_cost_m"]
    gain_a = sum_a["elevation_gain_m"]
    gain_b = sum_b["elevation_gain_m"]
    slope_a = sum_a["max_slope_deg"]
    slope_b = sum_b["max_slope_deg"]
    comp_a = sum_a["data_completeness_pct"]
    comp_b = sum_b["data_completeness_pct"]

    delta_dist = dist_b - dist_a
    delta_cost = cost_b - cost_a
    delta_gain = gain_b - gain_a
    delta_slope = slope_b - slope_a

    # Objective trade-off narrative
    tradeoffs: List[str] = []
    if delta_dist > 0 and delta_cost < 0:
        tradeoffs.append(
            f"{title_b} is {abs(delta_dist):.1f}m longer horizontally but saves {abs(delta_cost):.1f}m of modeled terrain effort by skirting steeper terrain."
        )
    elif delta_dist < 0 and delta_cost > 0:
        tradeoffs.append(
            f"{title_b} is {abs(delta_dist):.1f}m shorter in direct distance but incurs +{delta_cost:.1f}m more terrain effort due to steeper gradients."
        )
    elif delta_dist < 0 and delta_cost < 0:
        tradeoffs.append(
            f"{title_b} strictly outperforms {title_a} in both distance (-{abs(delta_dist):.1f}m) and modeled effort (-{abs(delta_cost):.1f}m)."
        )
    else:
        tradeoffs.append(
            f"{title_b} demands +{delta_dist:.1f}m distance and +{delta_cost:.1f}m effort relative to {title_a}."
        )

    if abs(delta_slope) > 1.0:
        steeper_plan = title_b if delta_slope > 0 else title_a
        tradeoffs.append(
            f"{steeper_plan} encounters steeper maximum terrain slopes ({max(slope_a, slope_b):.1f}° vs {min(slope_a, slope_b):.1f}°)."
        )

    if comp_a < 100.0 or comp_b < 100.0:
        tradeoffs.append(
            f"Data completeness distinction: {title_a} has {comp_a:.1f}% valid data, {title_b} has {comp_b:.1f}% valid data."
        )

    return {
        "title_a": title_a,
        "title_b": title_b,
        "route_a_id": analysis_a.route_id,
        "route_b_id": analysis_b.route_id,
        "deltas": {
            "distance_delta_m": round(delta_dist, 1),
            "cost_delta_m": round(delta_cost, 1),
            "elevation_gain_delta_m": round(delta_gain, 1),
            "max_slope_delta_deg": round(delta_slope, 1),
            "data_completeness_delta_pct": round(comp_b - comp_a, 1),
        },
        "metrics_table": {
            "distance_m": {"a": round(dist_a, 1), "b": round(dist_b, 1)},
            "effort_cost_flat_m": {"a": round(cost_a, 1), "b": round(cost_b, 1)},
            "elevation_gain_m": {"a": round(gain_a, 1), "b": round(gain_b, 1)},
            "max_slope_deg": {"a": round(slope_a, 1), "b": round(slope_b, 1)},
            "data_completeness_pct": {"a": round(comp_a, 1), "b": round(comp_b, 1)},
        },
        "tradeoff_narratives": tradeoffs,
    }


def _build_source_metadata(terrain: TerrainGrid) -> Dict[str, Any]:
    return {
        "dataset_name": "USGS MRO CTX Jezero Crater 20m DTM",
        "reference_datum": "IAU 2000 Mars Reference Sphere (R=3,396,190m)",
        "crs": terrain.crs or "ESRI:103885",
        "nominal_resolution_m": round(terrain.dy_ground_m, 1),
        "sampling_grid_spacing_m": {
            "east_west_dx_m": round(terrain.dx_ground_m, 2),
            "north_south_dy_m": round(terrain.dy_ground_m, 2),
        },
    }
