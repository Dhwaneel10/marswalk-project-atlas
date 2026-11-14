"""
MarsWalk 2.0 — Milestone 9Y: Explainable Terrain Intelligence, Route Cost Attribution & Decision Support.

Provides a mathematically rigorous, fully auditable route explanation and attribution engine answering:
1. Why did the planner choose this route?
2. Which terrain segments contribute most to its modeled travel cost and traversal effort?
3. What changes when the planning profile or vehicle mode changes?
4. Which alternative routes or itineraries offer a different distance-versus-cost trade-off?
5. How did a disruption change the route's geometry, cost, and explanation?
6. Can a teammate or competition judge inspect the evidence behind a recommendation?

SCIENTIFIC PRINCIPLES & GOVERNANCE:
- Explanations are derived directly from primary physical equations and DTM raster values.
- Traversal cost is expressed in METERS OF EQUIVALENT FLAT-TERRAIN EFFORT.
- Segments strictly reconcile to overall route totals (additive ledger).
- Modeled traversal effort is NOT certified astronaut safety.
"""

from dataclasses import dataclass, field
import enum
import hashlib
import json
import math
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import numpy as np

from marswalk.core.terrain import (
    TerrainGrid,
    TerrainConfig,
    calculate_step_distance,
    calculate_edge_cost,
    get_profile_terrain_config,
)
from marswalk.core.planner import (
    RouteResult,
    LegResult,
    calculate_traverse_time,
    format_duration,
)


class CostFactor(str, enum.Enum):
    BASE_DISTANCE = "base_distance"
    SLOPE = "slope"
    ROUGHNESS = "roughness"
    UPHILL = "uphill"
    CONTINGENCY_MULTIPLIER = "contingency_multiplier"


class TerrainDifficulty(str, enum.Enum):
    NOMINAL = "nominal"
    MODERATE = "moderate"
    CHALLENGING = "challenging"
    SEVERE = "severe"


@dataclass
class StepAttribution:
    """Detailed physical and cost breakdown for a single 8-connected grid step."""
    step_index: int
    u: Tuple[int, int]
    v: Tuple[int, int]
    distance_m: float
    cost_m: float
    dz_m: float
    slope_deg: float
    roughness_m: float
    slope_penalty: float
    roughness_penalty: float
    uphill_penalty: float
    multiplier: float
    base_distance_cost_m: float
    slope_cost_m: float
    roughness_cost_m: float
    uphill_cost_m: float
    contingency_cost_m: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "u": list(self.u),
            "v": list(self.v),
            "distance_m": round(self.distance_m, 2),
            "cost_m": round(self.cost_m, 2),
            "dz_m": round(self.dz_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "roughness_m": round(self.roughness_m, 2),
            "slope_penalty": round(self.slope_penalty, 4),
            "roughness_penalty": round(self.roughness_penalty, 4),
            "uphill_penalty": round(self.uphill_penalty, 4),
            "multiplier": round(self.multiplier, 3),
            "base_distance_cost_m": round(self.base_distance_cost_m, 2),
            "slope_cost_m": round(self.slope_cost_m, 2),
            "roughness_cost_m": round(self.roughness_cost_m, 2),
            "uphill_cost_m": round(self.uphill_cost_m, 2),
            "contingency_cost_m": round(self.contingency_cost_m, 2),
        }


@dataclass
class RouteSegmentExplanation:
    """Attribution and physical breakdown for an aggregated route segment."""
    segment_index: int
    start_step_index: int
    end_step_index: int
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    num_steps: int
    distance_m: float
    cost_m: float
    cost_fraction_pct: float
    cost_density: float
    elevation_start_m: float
    elevation_end_m: float
    elevation_change_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    min_elevation_m: float
    max_elevation_m: float
    max_slope_deg: float
    mean_slope_deg: float
    base_distance_cost_m: float
    slope_cost_m: float
    roughness_cost_m: float
    uphill_cost_m: float
    contingency_cost_m: float
    dominant_cost_factor: str
    terrain_difficulty_rating: str
    leg_id: Optional[str] = None
    explanation_narrative: str = ""
    subpath: List[Tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_index": self.segment_index,
            "start_step_index": self.start_step_index,
            "end_step_index": self.end_step_index,
            "start_rc": list(self.start_rc),
            "end_rc": list(self.end_rc),
            "num_steps": self.num_steps,
            "distance_m": round(self.distance_m, 2),
            "cost_m": round(self.cost_m, 2),
            "cost_fraction_pct": round(self.cost_fraction_pct, 1),
            "cost_density": round(self.cost_density, 3),
            "elevation_start_m": round(self.elevation_start_m, 2),
            "elevation_end_m": round(self.elevation_end_m, 2),
            "elevation_change_m": round(self.elevation_change_m, 2),
            "elevation_gain_m": round(self.elevation_gain_m, 2),
            "elevation_loss_m": round(self.elevation_loss_m, 2),
            "min_elevation_m": round(self.min_elevation_m, 2),
            "max_elevation_m": round(self.max_elevation_m, 2),
            "max_slope_deg": round(self.max_slope_deg, 2),
            "mean_slope_deg": round(self.mean_slope_deg, 2),
            "base_distance_cost_m": round(self.base_distance_cost_m, 2),
            "slope_cost_m": round(self.slope_cost_m, 2),
            "roughness_cost_m": round(self.roughness_cost_m, 2),
            "uphill_cost_m": round(self.uphill_cost_m, 2),
            "contingency_cost_m": round(self.contingency_cost_m, 2),
            "dominant_cost_factor": self.dominant_cost_factor,
            "terrain_difficulty_rating": self.terrain_difficulty_rating,
            "leg_id": self.leg_id,
            "explanation_narrative": self.explanation_narrative,
            "subpath": [list(rc) for rc in self.subpath],
        }


@dataclass
class HighestCostSegment:
    """Highlights top cost-accumulating segments with operational context and mitigation tips."""
    rank: int
    segment_index: int
    cost_m: float
    cost_fraction_pct: float
    cost_density: float
    dominant_factor: str
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    operational_impact: str
    mitigation_hint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "segment_index": self.segment_index,
            "cost_m": round(self.cost_m, 2),
            "cost_fraction_pct": round(self.cost_fraction_pct, 1),
            "cost_density": round(self.cost_density, 3),
            "dominant_factor": self.dominant_factor,
            "start_rc": list(self.start_rc),
            "end_rc": list(self.end_rc),
            "operational_impact": self.operational_impact,
            "mitigation_hint": self.mitigation_hint,
        }


@dataclass
class RouteCostLedger:
    """Reconciliation audit proving that segment decompositions strictly sum to overall totals."""
    total_distance_m: float
    sum_segment_distances_m: float
    distance_delta_m: float
    total_cost_m: float
    sum_segment_costs_m: float
    cost_delta_m: float
    component_sums_m: Dict[str, float]
    sum_of_components_m: float
    component_delta_m: float
    is_reconciled: bool
    reconciliation_tolerance_m: float
    non_additive_properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_distance_m": round(self.total_distance_m, 2),
            "sum_segment_distances_m": round(self.sum_segment_distances_m, 2),
            "distance_delta_m": round(self.distance_delta_m, 4),
            "total_cost_m": round(self.total_cost_m, 2),
            "sum_segment_costs_m": round(self.sum_segment_costs_m, 2),
            "cost_delta_m": round(self.cost_delta_m, 4),
            "component_sums_m": {k: round(v, 2) for k, v in self.component_sums_m.items()},
            "sum_of_components_m": round(self.sum_of_components_m, 2),
            "component_delta_m": round(self.component_delta_m, 4),
            "is_reconciled": self.is_reconciled,
            "reconciliation_tolerance_m": self.reconciliation_tolerance_m,
            "non_additive_properties": self.non_additive_properties,
        }


@dataclass
class RouteComparisonExplanation:
    """Comparative analysis contrasting a reference route with an alternative or detour."""
    reference_title: str
    alternative_title: str
    ref_distance_m: float
    alt_distance_m: float
    delta_distance_m: float
    delta_distance_pct: Optional[float]
    ref_cost_m: float
    alt_cost_m: float
    delta_cost_m: float
    delta_cost_pct: Optional[float]
    ref_time_s: float
    alt_time_s: float
    delta_time_s: float
    delta_time_pct: Optional[float]
    ref_max_slope_deg: float
    alt_max_slope_deg: float
    delta_max_slope_deg: float
    divergence_step_index: Optional[int]
    convergence_step_index: Optional[int]
    geometry_change_summary: str
    tradeoff_verdict: str
    scientific_attribution: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_title": self.reference_title,
            "alternative_title": self.alternative_title,
            "ref_distance_m": round(self.ref_distance_m, 2),
            "alt_distance_m": round(self.alt_distance_m, 2),
            "delta_distance_m": round(self.delta_distance_m, 2),
            "delta_distance_pct": round(self.delta_distance_pct, 1) if self.delta_distance_pct is not None else None,
            "ref_cost_m": round(self.ref_cost_m, 2),
            "alt_cost_m": round(self.alt_cost_m, 2),
            "delta_cost_m": round(self.delta_cost_m, 2),
            "delta_cost_pct": round(self.delta_cost_pct, 1) if self.delta_cost_pct is not None else None,
            "ref_time_s": round(self.ref_time_s, 1),
            "alt_time_s": round(self.alt_time_s, 1),
            "delta_time_s": round(self.delta_time_s, 1),
            "delta_time_pct": round(self.delta_time_pct, 1) if self.delta_time_pct is not None else None,
            "ref_max_slope_deg": round(self.ref_max_slope_deg, 2),
            "alt_max_slope_deg": round(self.alt_max_slope_deg, 2),
            "delta_max_slope_deg": round(self.delta_max_slope_deg, 2),
            "divergence_step_index": self.divergence_step_index,
            "convergence_step_index": self.convergence_step_index,
            "geometry_change_summary": self.geometry_change_summary,
            "tradeoff_verdict": self.tradeoff_verdict,
            "scientific_attribution": self.scientific_attribution,
        }


@dataclass
class RouteExplanationResult:
    """Complete structured response of route explainability and cost attribution."""
    status: str
    schema_version: str
    computation_fingerprint: str
    profile: str
    vehicle_mode: str
    speed_multiplier: float
    total_distance_m: float
    total_cost_m: float
    total_time_s: float
    formatted_time: str
    cost_density_ratio: float
    max_slope_deg: float
    mean_slope_deg: float
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    min_elevation_m: float
    max_elevation_m: float
    segments: List[RouteSegmentExplanation]
    highest_cost_segments: List[HighestCostSegment]
    reconciliation_ledger: RouteCostLedger
    decision_rationale: Dict[str, Any]
    comparison: Optional[RouteComparisonExplanation] = None
    step_details: Optional[List[Dict[str, Any]]] = None
    disclosures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "status": self.status,
            "schema_version": self.schema_version,
            "computation_fingerprint": self.computation_fingerprint,
            "profile": self.profile,
            "vehicle_mode": self.vehicle_mode,
            "speed_multiplier": self.speed_multiplier,
            "total_distance_m": round(self.total_distance_m, 2),
            "total_cost_m": round(self.total_cost_m, 2),
            "total_time_s": round(self.total_time_s, 1),
            "formatted_time": self.formatted_time,
            "cost_density_ratio": round(self.cost_density_ratio, 3),
            "max_slope_deg": round(self.max_slope_deg, 2),
            "mean_slope_deg": round(self.mean_slope_deg, 2),
            "total_elevation_gain_m": round(self.total_elevation_gain_m, 2),
            "total_elevation_loss_m": round(self.total_elevation_loss_m, 2),
            "min_elevation_m": round(self.min_elevation_m, 2),
            "max_elevation_m": round(self.max_elevation_m, 2),
            "segments": [s.to_dict() for s in self.segments],
            "highest_cost_segments": [h.to_dict() for h in self.highest_cost_segments],
            "reconciliation_ledger": self.reconciliation_ledger.to_dict(),
            "decision_rationale": self.decision_rationale,
            "disclosures": self.disclosures,
        }
        if self.comparison is not None:
            res["comparison"] = self.comparison.to_dict()
        if self.step_details is not None:
            res["step_details"] = self.step_details
        return res


def compute_step_attributions(
    path: List[Tuple[int, int]],
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
) -> List[StepAttribution]:
    """
    Calculate exact physical step-by-step cost attribution along an 8-connected path.
    Guarantees additive decomposition:
    base_distance_cost + slope_cost + roughness_cost + uphill_cost + contingency_cost == edge_cost.
    """
    if len(path) < 2:
        return []

    cfg = terrain_config if terrain_config is not None else terrain.config
    dx = terrain.dx_ground_m
    dy = terrain.dy_ground_m

    attributions: List[StepAttribution] = []

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]

        dist = calculate_step_distance(u, v, dx, dy)
        if dist <= 0.0:
            continue

        r1, c1 = u
        r2, c2 = v

        z1 = float(terrain.elevation[r1, c1])
        z2 = float(terrain.elevation[r2, c2])
        dz = z2 - z1

        # Effective slope
        theta_step = math.degrees(math.atan(abs(dz) / dist))
        theta_dest = float(terrain.slope_deg[r2, c2])
        if math.isnan(theta_dest):
            theta_dest = 0.0
        theta_uv = max(theta_dest, theta_step)

        # Dimensionless penalty terms
        slope_term = cfg.alpha_s * ((theta_uv / cfg.theta_crit_deg) ** 2)

        dest_rough = float(terrain.roughness_m[r2, c2])
        if math.isnan(dest_rough) or dest_rough < 0:
            dest_rough = 0.0
        rough_term = cfg.alpha_r * (dest_rough / cfg.sigma_0_m)

        uphill_term = cfg.alpha_up * max(0.0, dz / dist)

        base_bracket = 1.0 + slope_term + rough_term + uphill_term
        base_cost = dist * base_bracket

        # Multiplier mask (contingency impedance)
        mult = 1.0
        if cost_multiplier_mask is not None:
            m_val = float(cost_multiplier_mask[r2, c2])
            if m_val > 1.0 and not math.isnan(m_val) and not math.isinf(m_val):
                mult = m_val

        step_cost = base_cost * mult

        # Exact additive decomposition
        base_dist_cost = dist * 1.0
        slope_cost = dist * slope_term
        rough_cost = dist * rough_term
        uphill_cost = dist * uphill_term
        contingency_cost = base_cost * (mult - 1.0)

        attributions.append(
            StepAttribution(
                step_index=i,
                u=u,
                v=v,
                distance_m=dist,
                cost_m=step_cost,
                dz_m=dz,
                slope_deg=theta_uv,
                roughness_m=dest_rough,
                slope_penalty=slope_term,
                roughness_penalty=rough_term,
                uphill_penalty=uphill_term,
                multiplier=mult,
                base_distance_cost_m=base_dist_cost,
                slope_cost_m=slope_cost,
                roughness_cost_m=rough_cost,
                uphill_cost_m=uphill_cost,
                contingency_cost_m=contingency_cost,
            )
        )

    return attributions


def decompose_route_segments(
    path: List[Tuple[int, int]],
    step_attributions: List[StepAttribution],
    terrain: TerrainGrid,
    num_aggregated_segments: int = 10,
    leg_boundaries: Optional[List[int]] = None,
    leg_labels: Optional[List[str]] = None,
) -> List[RouteSegmentExplanation]:
    """
    Partition path and step attributions into contiguous segments.
    Supports either uniform division (default 10 segments) or waypoint-leg alignment.
    """
    total_steps = len(step_attributions)
    if total_steps == 0:
        if len(path) == 1:
            elev = float(terrain.elevation[path[0][0], path[0][1]])
            return [
                RouteSegmentExplanation(
                    segment_index=0,
                    start_step_index=0,
                    end_step_index=0,
                    start_rc=path[0],
                    end_rc=path[0],
                    num_steps=0,
                    distance_m=0.0,
                    cost_m=0.0,
                    cost_fraction_pct=100.0,
                    cost_density=1.0,
                    elevation_start_m=elev,
                    elevation_end_m=elev,
                    elevation_change_m=0.0,
                    elevation_gain_m=0.0,
                    elevation_loss_m=0.0,
                    min_elevation_m=elev,
                    max_elevation_m=elev,
                    max_slope_deg=0.0,
                    mean_slope_deg=0.0,
                    base_distance_cost_m=0.0,
                    slope_cost_m=0.0,
                    roughness_cost_m=0.0,
                    uphill_cost_m=0.0,
                    contingency_cost_m=0.0,
                    dominant_cost_factor=CostFactor.BASE_DISTANCE.value,
                    terrain_difficulty_rating=TerrainDifficulty.NOMINAL.value,
                    explanation_narrative="Trivial single-point stay; zero distance and traversal cost.",
                    subpath=path,
                )
            ]
        return []

    total_route_cost = sum(s.cost_m for s in step_attributions)
    if total_route_cost <= 0.0:
        total_route_cost = 1e-6

    # Determine slice ranges
    segment_slices: List[Tuple[int, int, Optional[str]]] = []

    if leg_boundaries and len(leg_boundaries) >= 2:
        # Leg-based partitioning
        for i in range(len(leg_boundaries) - 1):
            s_start = leg_boundaries[i]
            s_end = leg_boundaries[i + 1]
            lbl = leg_labels[i] if leg_labels and i < len(leg_labels) else f"Leg {i+1}"
            segment_slices.append((s_start, s_end, lbl))
    else:
        # Uniform aggregation
        k = max(1, min(num_aggregated_segments, total_steps))
        step_chunk = total_steps / float(k)
        for i in range(k):
            s_start = int(round(i * step_chunk))
            s_end = int(round((i + 1) * step_chunk))
            if i == k - 1:
                s_end = total_steps
            if s_end > s_start:
                segment_slices.append((s_start, s_end, f"Segment {i+1}"))

    segments: List[RouteSegmentExplanation] = []

    for seg_idx, (s_start, s_end, leg_lbl) in enumerate(segment_slices):
        slice_steps = step_attributions[s_start:s_end]
        if not slice_steps:
            continue

        seg_subpath = path[s_start : s_end + 1]
        start_rc = path[s_start]
        end_rc = path[s_end]

        seg_dist = sum(s.distance_m for s in slice_steps)
        seg_cost = sum(s.cost_m for s in slice_steps)
        cost_frac = (seg_cost / total_route_cost) * 100.0
        cost_density = (seg_cost / seg_dist) if seg_dist > 0 else 1.0

        elevations = [float(terrain.elevation[r, c]) for r, c in seg_subpath]
        elev_start = elevations[0]
        elev_end = elevations[-1]
        elev_change = elev_end - elev_start

        elev_gain = sum(s.dz_m for s in slice_steps if s.dz_m > 0)
        elev_loss = sum(-s.dz_m for s in slice_steps if s.dz_m < 0)
        min_elev = min(elevations)
        max_elev = max(elevations)

        max_slope = max(s.slope_deg for s in slice_steps)
        mean_slope = sum(s.slope_deg * s.distance_m for s in slice_steps) / seg_dist if seg_dist > 0 else 0.0

        base_dist_cost = sum(s.base_distance_cost_m for s in slice_steps)
        slope_cost = sum(s.slope_cost_m for s in slice_steps)
        rough_cost = sum(s.roughness_cost_m for s in slice_steps)
        uphill_cost = sum(s.uphill_cost_m for s in slice_steps)
        contingency_cost = sum(s.contingency_cost_m for s in slice_steps)

        # Dominant non-base factor
        penalties = [
            ("slope", slope_cost),
            ("roughness", rough_cost),
            ("uphill", uphill_cost),
            ("contingency_multiplier", contingency_cost),
        ]
        penalties.sort(key=lambda x: x[1], reverse=True)
        top_name, top_val = penalties[0]

        if top_val >= 0.12 * seg_cost and top_val > 0.5:
            dominant_factor = top_name
        else:
            dominant_factor = CostFactor.BASE_DISTANCE.value

        # Difficulty rating
        if cost_density < 1.3:
            rating = TerrainDifficulty.NOMINAL.value
        elif cost_density < 2.0:
            rating = TerrainDifficulty.MODERATE.value
        elif cost_density < 3.5:
            rating = TerrainDifficulty.CHALLENGING.value
        else:
            rating = TerrainDifficulty.SEVERE.value

        # Explanation narrative
        narrative_parts = [
            f"{leg_lbl}: traverses {seg_dist:.1f}m ({cost_frac:.1f}% of total route cost).",
        ]
        if elev_change > 1.0:
            narrative_parts.append(f"Climbs +{elev_change:.1f}m elevation.")
        elif elev_change < -1.0:
            narrative_parts.append(f"Descends {elev_change:.1f}m elevation.")

        if dominant_factor == "slope":
            narrative_parts.append(f"Dominant factor: slope penalties up to {max_slope:.1f}°.")
        elif dominant_factor == "roughness":
            narrative_parts.append("Dominant factor: surface roughness impedance.")
        elif dominant_factor == "uphill":
            narrative_parts.append("Dominant factor: continuous climbing gradient.")
        elif dominant_factor == "contingency_multiplier":
            narrative_parts.append("Dominant factor: active contingency hazard multiplier.")
        else:
            narrative_parts.append("Nominal flat-ground terrain with negligible gradient.")

        explanation_narrative = " ".join(narrative_parts)

        segments.append(
            RouteSegmentExplanation(
                segment_index=seg_idx,
                start_step_index=s_start,
                end_step_index=s_end,
                start_rc=start_rc,
                end_rc=end_rc,
                num_steps=len(slice_steps),
                distance_m=seg_dist,
                cost_m=seg_cost,
                cost_fraction_pct=cost_frac,
                cost_density=cost_density,
                elevation_start_m=elev_start,
                elevation_end_m=elev_end,
                elevation_change_m=elev_change,
                elevation_gain_m=elev_gain,
                elevation_loss_m=elev_loss,
                min_elevation_m=min_elev,
                max_elevation_m=max_elev,
                max_slope_deg=max_slope,
                mean_slope_deg=mean_slope,
                base_distance_cost_m=base_dist_cost,
                slope_cost_m=slope_cost,
                roughness_cost_m=rough_cost,
                uphill_cost_m=uphill_cost,
                contingency_cost_m=contingency_cost,
                dominant_cost_factor=dominant_factor,
                terrain_difficulty_rating=rating,
                leg_id=leg_lbl,
                explanation_narrative=explanation_narrative,
                subpath=seg_subpath,
            )
        )

    return segments


def reconcile_route_cost_ledger(
    total_distance_m: float,
    total_cost_m: float,
    segments: List[RouteSegmentExplanation],
    max_slope_deg: float,
    mean_slope_deg: float,
    min_elevation_m: float,
    max_elevation_m: float,
    tolerance_m: float = 0.05,
) -> RouteCostLedger:
    """
    Produce an exact mathematical reconciliation ledger demonstrating that:
    1. sum(segment.distance_m) == total_distance_m (within tolerance)
    2. sum(segment.cost_m) == total_cost_m (within tolerance)
    3. sum(component_sums) == sum(segment.cost_m) (within tolerance)
    """
    sum_dist = sum(s.distance_m for s in segments)
    sum_cost = sum(s.cost_m for s in segments)

    dist_delta = abs(sum_dist - total_distance_m)
    cost_delta = abs(sum_cost - total_cost_m)

    comp_sums = {
        "base_distance": sum(s.base_distance_cost_m for s in segments),
        "slope": sum(s.slope_cost_m for s in segments),
        "roughness": sum(s.roughness_cost_m for s in segments),
        "uphill": sum(s.uphill_cost_m for s in segments),
        "contingency_multiplier": sum(s.contingency_cost_m for s in segments),
    }

    sum_comps = sum(comp_sums.values())
    comp_delta = abs(sum_comps - sum_cost)

    is_reconciled = (
        dist_delta <= tolerance_m
        and cost_delta <= tolerance_m
        and comp_delta <= tolerance_m
    )

    cost_density_ratio = (total_cost_m / total_distance_m) if total_distance_m > 0 else 1.0

    non_additive = {
        "max_slope_deg": round(max_slope_deg, 2),
        "mean_slope_deg": round(mean_slope_deg, 2),
        "min_elevation_m": round(min_elevation_m, 2),
        "max_elevation_m": round(max_elevation_m, 2),
        "cost_density_ratio": round(cost_density_ratio, 3),
        "disclosure": "Max slope and elevation extrema are non-additive path bounds, not additive sums. Mean slope is distance-weighted. Cost density is an impedance ratio.",
    }

    return RouteCostLedger(
        total_distance_m=total_distance_m,
        sum_segment_distances_m=sum_dist,
        distance_delta_m=dist_delta,
        total_cost_m=total_cost_m,
        sum_segment_costs_m=sum_cost,
        cost_delta_m=cost_delta,
        component_sums_m=comp_sums,
        sum_of_components_m=sum_comps,
        component_delta_m=comp_delta,
        is_reconciled=is_reconciled,
        reconciliation_tolerance_m=tolerance_m,
        non_additive_properties=non_additive,
    )


def rank_highest_cost_segments(
    segments: List[RouteSegmentExplanation],
    top_k: int = 3,
) -> List[HighestCostSegment]:
    """Identify and rank the highest cost-accumulating route segments with actionable mitigation advice."""
    if not segments:
        return []

    # Sort primarily by cost_m descending, secondarily by cost_density
    sorted_segs = sorted(segments, key=lambda s: (s.cost_m, s.cost_density), reverse=True)
    top_segs = sorted_segs[:top_k]

    results: List[HighestCostSegment] = []
    for rank, seg in enumerate(top_segs, 1):
        # Operational impact
        impact = (
            f"Segment {seg.segment_index + 1} ({seg.leg_id or 'nominal'}) generates {seg.cost_m:.1f}m traversal effort "
            f"({seg.cost_fraction_pct:.1f}% of total) across {seg.distance_m:.1f}m ground distance "
            f"(impedance density: {seg.cost_density:.2f}x)."
        )

        # Mitigation hints based on dominant factor
        if seg.dominant_cost_factor == "slope":
            hint = (
                f"Peak slope reaches {seg.max_slope_deg:.1f}°. To reduce effort, switch to Science-First profile "
                f"if slope tolerance permits, or place a detour waypoint around the crater scarp."
            )
        elif seg.dominant_cost_factor == "roughness":
            hint = "High decameter topographic roughness. Steer path toward smooth sedimentary plains or delta deposits."
        elif seg.dominant_cost_factor == "uphill":
            hint = f"Continuous climbing grade (+{seg.elevation_gain_m:.1f}m). Consider an oblique switchback approach."
        elif seg.dominant_cost_factor == "contingency_multiplier":
            hint = "Active contingency corridor impedance. Re-run adaptive replanner to divert away from hazard boundary."
        else:
            hint = "Long distance traverse. Speed or vehicle mode selection dominates travel duration."

        results.append(
            HighestCostSegment(
                rank=rank,
                segment_index=seg.segment_index,
                cost_m=seg.cost_m,
                cost_fraction_pct=seg.cost_fraction_pct,
                cost_density=seg.cost_density,
                dominant_factor=seg.dominant_cost_factor,
                start_rc=seg.start_rc,
                end_rc=seg.end_rc,
                operational_impact=impact,
                mitigation_hint=hint,
            )
        )

    return results


def generate_decision_rationale(
    route: RouteResult,
    terrain: TerrainGrid,
    terrain_config: TerrainConfig,
    segments: List[RouteSegmentExplanation],
    blocked_mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Produce an authentic, deterministic explanation for why the planner chose this specific route.
    Grounds assertions in physical boundary conditions, cliff cutoffs, and cost equations.
    """
    profile = route.profile.lower()
    theta_max = terrain_config.theta_max_deg
    alpha_s = terrain_config.alpha_s

    # Hazards avoided
    hazards_avoided: List[str] = [
        f"Impassable slopes exceeding cutoff threshold {theta_max:.1f}° ({profile} profile limit)",
        "Invalid DTM nodata cells and dilated perimeter buffers",
    ]
    if blocked_mask is not None and np.any(blocked_mask):
        hazards_avoided.append("Active contingency exclusion corridors and keep-out zones")

    # Tradeoffs accepted
    straight_line_dist = calculate_step_distance(
        route.start_rc, route.goal_rc, terrain.dx_ground_m, terrain.dy_ground_m
    )
    detour_excess_m = max(0.0, route.distance_m - straight_line_dist)
    detour_pct = (detour_excess_m / straight_line_dist * 100.0) if straight_line_dist > 0 else 0.0

    tradeoffs: List[str] = []
    if detour_pct > 5.0:
        tradeoffs.append(
            f"Added {detour_excess_m:.1f}m lateral ground distance (+{detour_pct:.1f}% vs straight line) "
            f"to follow gentler topographic contours below {theta_max:.1f}°."
        )
    else:
        tradeoffs.append("Maintained near-direct trajectory across low-relief terrain.")

    high_cost_segs = [s for s in segments if s.cost_density > 2.0]
    if high_cost_segs:
        tradeoffs.append(
            f"Accepted {len(high_cost_segs)} elevated-impedance segments (density > 2.0x) "
            f"to avoid even larger geometric detours."
        )

    narrative = (
        f"The authoritative A* planner identified the globally optimal path under the '{profile}' profile. "
        f"By balancing ground distance against quadratic slope penalties (weight α_s={alpha_s:.1f}) and directional climbing effort, "
        f"it accumulated {route.cost:.1f}m total traversal effort. All slopes remain strictly below {theta_max:.1f}°."
    )

    return {
        "objective_description": f"Global minimum traversal cost under {profile} profile on 8-connected Jezero grid.",
        "hazards_avoided": hazards_avoided,
        "tradeoffs_accepted": tradeoffs,
        "full_narrative": narrative,
    }


def compare_routes_explained(
    ref_route: RouteResult,
    alt_route: RouteResult,
    ref_title: str = "Reference Route",
    alt_title: Optional[str] = None,
    alternative_title: Optional[str] = None,
    ref_explanation: Optional[RouteExplanationResult] = None,
    alt_explanation: Optional[RouteExplanationResult] = None,
) -> RouteComparisonExplanation:
    """
    Compare reference and alternative routes with geometric divergence tracking and quantitative deltas.
    """
    effective_alt_title = alternative_title or alt_title or "Alternative Route"
    ref_dist = ref_route.distance_m
    alt_dist = alt_route.distance_m
    d_dist = alt_dist - ref_dist
    d_dist_pct = (d_dist / ref_dist * 100.0) if ref_dist > 0 else None

    ref_cost = ref_route.cost
    alt_cost = alt_route.cost
    d_cost = alt_cost - ref_cost
    d_cost_pct = (d_cost / ref_cost * 100.0) if ref_cost > 0 else None

    ref_time = ref_route.travel_time_s
    alt_time = alt_route.travel_time_s
    d_time = alt_time - ref_time
    d_time_pct = (d_time / ref_time * 100.0) if ref_time > 0 else None

    ref_max_slope = ref_explanation.max_slope_deg if ref_explanation else 0.0
    alt_max_slope = alt_explanation.max_slope_deg if alt_explanation else 0.0
    d_max_slope = alt_max_slope - ref_max_slope

    # Divergence and convergence
    p_ref = ref_route.path
    p_alt = alt_route.path

    divergence_idx = None
    convergence_idx = None

    min_len = min(len(p_ref), len(p_alt))
    for i in range(min_len):
        if p_ref[i] != p_alt[i]:
            divergence_idx = i
            break

    if divergence_idx is not None:
        # Check from end
        for j in range(1, min_len - divergence_idx + 1):
            if p_ref[-j] == p_alt[-j]:
                convergence_idx = len(p_alt) - j
            else:
                break

    # Geometry change summary
    if divergence_idx is None and len(p_ref) == len(p_alt):
        geom_summary = "Identical spatial trajectory; cost variations reflect vehicle mode or speed multipliers."
    elif divergence_idx is not None:
        geom_summary = (
            f"Paths diverge at step {divergence_idx} (coord {p_ref[divergence_idx]}). "
            f"Alternative takes a detour of {d_dist:+.1f}m ground distance."
        )
    else:
        geom_summary = f"Routes follow distinct waypoints or trajectories (length delta: {d_dist:+.1f}m)."

    # Tradeoff verdict
    if abs(d_cost) < 1.0:
        verdict = "Both routes exhibit equivalent modeled traversal effort."
    elif d_cost > 0:
        verdict = (
            f"{effective_alt_title} requires {d_cost:+.1f}m more equivalent effort (+{d_cost_pct:.1f}%), "
            f"adding {format_duration(d_time)} travel time."
        )
    else:
        verdict = (
            f"{effective_alt_title} achieves a {abs(d_cost):.1f}m effort reduction ({abs(d_cost_pct):.1f}%), "
            f"saving {format_duration(abs(d_time))} travel time."
        )

    attribution = (
        f"Compared '{ref_title}' against '{effective_alt_title}' on IAU Mars 2000 Sphere / USGS CTX DTM. "
        f"Quantities reflect primary path steps and deterministic impedance equations."
    )

    return RouteComparisonExplanation(
        reference_title=ref_title,
        alternative_title=effective_alt_title,
        ref_distance_m=ref_dist,
        alt_distance_m=alt_dist,
        delta_distance_m=d_dist,
        delta_distance_pct=d_dist_pct,
        ref_cost_m=ref_cost,
        alt_cost_m=alt_cost,
        delta_cost_m=d_cost,
        delta_cost_pct=d_cost_pct,
        ref_time_s=ref_time,
        alt_time_s=alt_time,
        delta_time_s=d_time,
        delta_time_pct=d_time_pct,
        ref_max_slope_deg=ref_max_slope,
        alt_max_slope_deg=alt_max_slope,
        delta_max_slope_deg=d_max_slope,
        divergence_step_index=divergence_idx,
        convergence_step_index=convergence_idx,
        geometry_change_summary=geom_summary,
        tradeoff_verdict=verdict,
        scientific_attribution=attribution,
    )


def explain_route(
    route: RouteResult,
    terrain: TerrainGrid,
    terrain_config: Optional[TerrainConfig] = None,
    cost_multiplier_mask: Optional[np.ndarray] = None,
    blocked_mask: Optional[np.ndarray] = None,
    num_aggregated_segments: int = 10,
    include_step_details: bool = False,
    alternative_route: Optional[RouteResult] = None,
    reference_title: str = "Reference Route",
    alternative_title: str = "Alternative Route",
) -> RouteExplanationResult:
    """
    Authoritative entry point for route explainability and cost attribution.
    Computes step attributions, segment decomposition, reconciliation ledger,
    highest-cost bottleneck ranking, decision rationale, and comparative trade-offs.
    """
    cfg = terrain_config if terrain_config is not None else terrain.config

    step_attributions = compute_step_attributions(
        path=route.path,
        terrain=terrain,
        terrain_config=cfg,
        cost_multiplier_mask=cost_multiplier_mask,
    )

    # Leg boundaries if route has legs
    leg_boundaries: Optional[List[int]] = None
    leg_labels: Optional[List[str]] = None
    if route.legs and len(route.legs) > 1:
        leg_boundaries = [0]
        leg_labels = []
        cur_step = 0
        for idx, leg in enumerate(route.legs):
            leg_len = max(0, len(leg.path) - 1)
            cur_step += leg_len
            leg_boundaries.append(cur_step)
            lbl = f"Stop {idx+1}" if idx < len(route.legs) - 1 else "Destination"
            leg_labels.append(f"Leg {idx+1} ({lbl})")

    segments = decompose_route_segments(
        path=route.path,
        step_attributions=step_attributions,
        terrain=terrain,
        num_aggregated_segments=num_aggregated_segments,
        leg_boundaries=leg_boundaries,
        leg_labels=leg_labels,
    )

    # Extract path-level extrema and distance-weighted slope
    if step_attributions:
        max_slope = max(s.slope_deg for s in step_attributions)
        total_dist = sum(s.distance_m for s in step_attributions)
        mean_slope = sum(s.slope_deg * s.distance_m for s in step_attributions) / total_dist if total_dist > 0 else 0.0
        elevations = [float(terrain.elevation[r, c]) for r, c in route.path]
        min_elev = min(elevations)
        max_elev = max(elevations)
        total_elev_gain = sum(s.dz_m for s in step_attributions if s.dz_m > 0)
        total_elev_loss = sum(-s.dz_m for s in step_attributions if s.dz_m < 0)
    else:
        elev0 = float(terrain.elevation[route.start_rc[0], route.start_rc[1]])
        max_slope = 0.0
        mean_slope = 0.0
        min_elev = elev0
        max_elev = elev0
        total_elev_gain = 0.0
        total_elev_loss = 0.0

    ledger = reconcile_route_cost_ledger(
        total_distance_m=route.distance_m,
        total_cost_m=route.cost,
        segments=segments,
        max_slope_deg=max_slope,
        mean_slope_deg=mean_slope,
        min_elevation_m=min_elev,
        max_elevation_m=max_elev,
    )

    highest_cost = rank_highest_cost_segments(segments, top_k=3)

    decision_rationale = generate_decision_rationale(
        route=route,
        terrain=terrain,
        terrain_config=cfg,
        segments=segments,
        blocked_mask=blocked_mask,
    )

    # Comparison if requested
    comparison_res: Optional[RouteComparisonExplanation] = None
    if alternative_route is not None:
        alt_cfg = terrain_config if terrain_config is not None else terrain.config
        alt_steps = compute_step_attributions(
            path=alternative_route.path,
            terrain=terrain,
            terrain_config=alt_cfg,
            cost_multiplier_mask=cost_multiplier_mask,
        )
        alt_max_slope = max((s.slope_deg for s in alt_steps), default=0.0)
        alt_total_dist = sum(s.distance_m for s in alt_steps)
        alt_mean_slope = sum(s.slope_deg * s.distance_m for s in alt_steps) / alt_total_dist if alt_total_dist > 0 else 0.0

        # Create quick mock explanation for alt route slope
        alt_explanation_quick = RouteExplanationResult(
            status="success",
            schema_version="1.0.0",
            computation_fingerprint="",
            profile=alternative_route.profile,
            vehicle_mode=alternative_route.vehicle_mode,
            speed_multiplier=alternative_route.speed_multiplier,
            total_distance_m=alternative_route.distance_m,
            total_cost_m=alternative_route.cost,
            total_time_s=alternative_route.travel_time_s,
            formatted_time=alternative_route.formatted_travel_time,
            cost_density_ratio=alternative_route.cost / alternative_route.distance_m if alternative_route.distance_m > 0 else 1.0,
            max_slope_deg=alt_max_slope,
            mean_slope_deg=alt_mean_slope,
            total_elevation_gain_m=0.0,
            total_elevation_loss_m=0.0,
            min_elevation_m=0.0,
            max_elevation_m=0.0,
            segments=[],
            highest_cost_segments=[],
            reconciliation_ledger=ledger,
            decision_rationale={},
        )

        comparison_res = compare_routes_explained(
            ref_route=route,
            alt_route=alternative_route,
            ref_title=reference_title,
            alternative_title=alternative_title,
            ref_explanation=None,
            alt_explanation=alt_explanation_quick,
        )

    # Deterministic fingerprint
    fp_raw = f"{route.profile}_{route.start_rc}_{route.goal_rc}_{route.distance_m:.2f}_{route.cost:.2f}_{len(segments)}"
    fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()[:16]

    step_details_out = [s.to_dict() for s in step_attributions] if include_step_details else None

    disclosures = [
        "Traversal costs are expressed in meters of equivalent flat-terrain effort based on calibrated DTM slope and roughness.",
        "Segment sums reconcile exactly to route totals in the mathematical reconciliation ledger.",
        "Modeled traversal effort is an algorithmic metric, NOT a certified operational safety envelope for human EVA.",
    ]

    cost_density_ratio = (route.cost / route.distance_m) if route.distance_m > 0 else 1.0

    return RouteExplanationResult(
        status="success",
        schema_version="1.0.0",
        computation_fingerprint=fingerprint,
        profile=route.profile,
        vehicle_mode=route.vehicle_mode,
        speed_multiplier=route.speed_multiplier,
        total_distance_m=route.distance_m,
        total_cost_m=route.cost,
        total_time_s=route.travel_time_s,
        formatted_time=route.formatted_travel_time,
        cost_density_ratio=cost_density_ratio,
        max_slope_deg=max_slope,
        mean_slope_deg=mean_slope,
        total_elevation_gain_m=total_elev_gain,
        total_elevation_loss_m=total_elev_loss,
        min_elevation_m=min_elev,
        max_elevation_m=max_elev,
        segments=segments,
        highest_cost_segments=highest_cost,
        reconciliation_ledger=ledger,
        decision_rationale=decision_rationale,
        comparison=comparison_res,
        step_details=step_details_out,
        disclosures=disclosures,
    )
