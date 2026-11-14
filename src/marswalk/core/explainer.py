"""
MarsWalk Mission Explainer and Co-Pilot Voice Engine.
Generates deterministic, scientifically grounded trade-off narratives
and comparative debriefings in either Professional or Dry Humour modes.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from marswalk.core.planner import RouteResult, ScienceWaypoint


@dataclass(frozen=True)
class VoiceConfig:
    """
    Configuration for mission control debrief voice mode.
    """
    mode: str = "professional"  # "professional" or "dry_humour"

    def __post_init__(self):
        if self.mode not in ("professional", "dry_humour"):
            raise ValueError(f"Unknown voice mode '{self.mode}'. Must be 'professional' or 'dry_humour'")


def generate_route_tradeoff_summary(
    primary_route: RouteResult,
    conservative_route: RouteResult,
    science_first_route: Optional[RouteResult] = None,
    waypoints: Optional[List[ScienceWaypoint]] = None,
    voice_mode: str = "professional",
) -> Dict[str, str]:
    """
    Produce structured, deterministic debrief narratives comparing the selected
    route against conservative baseline and maximum-science alternatives.
    """
    is_humour = (voice_mode == "dry_humour")
    wps_by_id = {w.id: w for w in (waypoints or [])}

    # 1. Unreachable destination handling
    if not primary_route.is_reachable:
        if is_humour:
            headline = "Navigation Disconnect: The laws of physics remain undefeated."
            detail = (
                "Our routing algorithm has thoroughly investigated every possible path to the destination "
                "and concluded that walking through a sheer Martian cliff is inadvisable. Destination unreachable."
            )
        else:
            headline = "Mission Traversal Alert: Destination Unreachable."
            detail = (
                "No feasible traverse exists between the designated coordinates under the configured "
                "slope cutoff (25.0°) and terrain boundary constraints."
            )
        return {
            "headline": headline,
            "detail": detail,
            "efficiency_note": "Traversal cost is infinite.",
            "budget_note": "Budget clearance: N/A.",
        }

    # 2. Budget evaluation
    dist_m = primary_route.distance_m
    max_d = primary_route.max_distance_m
    budget_ok = primary_route.is_budget_feasible

    if max_d is not None:
        if budget_ok:
            margin = max_d - dist_m
            budget_note = (
                f"Within walking budget ({dist_m:.0f} m / {max_d:.0f} m, {margin:.0f} m reserve margin)."
                if not is_humour
                else f"Walking budget cleared with {margin:.0f} m of oxygen breathing room. Try not to sprint."
            )
        else:
            overage = dist_m - max_d
            budget_note = (
                f"BUDGET EXCEEDED: Route requires {dist_m:.0f} m against a {max_d:.0f} m ceiling (+{overage:.0f} m)."
                if not is_humour
                else f"Curiosity: unlimited. Walking budget: unfortunately, not. Exceeded by {overage:.0f} m."
            )
    else:
        budget_note = f"Physical traverse length: {dist_m:.0f} m (no distance ceiling configured)."

    # 3. Profile-specific narratives
    prof = primary_route.profile.lower()
    base_dist = conservative_route.distance_m
    base_cost = conservative_route.cost

    delta_dist = dist_m - base_dist
    delta_cost = primary_route.cost - base_cost
    pct_dist = (delta_dist / base_dist * 100.0) if base_dist > 0 else 0.0
    pct_cost = (delta_cost / base_cost * 100.0) if base_cost > 0 else 0.0

    visited_names = [
        wps_by_id[wid].name for wid in primary_route.visited_waypoint_ids if wid in wps_by_id
    ]

    if prof == "conservative":
        if is_humour:
            headline = "Conservative Traverse: Safe, prompt, and completely uninterested in rocks."
            detail = (
                f"The plan tracks the lowest-slope path available ({dist_m:.0f} m, cost {primary_route.cost:.0f}). "
                "Zero detours taken. Zero science harvested. The geologists back at Houston are quietly weeping into their coffee."
            )
        else:
            headline = "Conservative Traverse: Baseline Least-Terrain-Cost Route."
            detail = (
                f"Direct traverse from start to goal minimizing modeled terrain cost ({primary_route.cost:.0f} flat-meters equivalent). "
                f"Skirts steep delta scarps to maintain low energy exertion. Science stops: 0."
            )
        eff_note = "Baseline reference efficiency (zero exploration overhead)."

    elif prof == "science_first":
        num_targets = len(visited_names)
        if is_humour:
            headline = f"Science-First Traverse: Maximum discovery, maximum lactic acid."
            detail = (
                f"Visiting {num_targets} targets adds {delta_dist:.0f} m (+{pct_dist:.1f}%) and +{pct_cost:.1f}% terrain effort. "
                "The scientific return is immense. Your spacesuit life-support pack will have strong opinions about this."
            )
        else:
            headline = f"Science-First Traverse: Optimized {primary_route.science_score:.0f}-Point Itinerary."
            detail = (
                f"Visits {num_targets} prioritized targets ({', '.join(visited_names) if visited_names else 'none'}). "
                f"Traverse distance increases by {delta_dist:.0f} m (+{pct_dist:.1f}%) and modeled terrain cost by +{pct_cost:.1f}% "
                f"relative to the conservative baseline."
            )
        eff_note = f"Captures 100% of selectable target priority ({primary_route.science_score:.0f} pts)."

    elif prof == "balanced":
        num_targets = len(visited_names)
        all_count = len(waypoints or [])
        dropped_count = all_count - num_targets

        if is_humour:
            if dropped_count > 0:
                headline = "Balanced Traverse: Ruthlessly pragmatic planetary exploration."
                detail = (
                    f"Selected {num_targets} targets and politely declined {dropped_count} others to save {delta_cost:.0f} terrain effort. "
                    "A calculated compromise: enough rocks to win a promotion, enough oxygen to survive the walk back."
                )
            else:
                headline = "Balanced Traverse: All targets captured within acceptable trade-off margins."
                detail = (
                    f"Every selected target ({num_targets}) justified its detour effort under current appetite weights. "
                    "Proceed with cautious optimism."
                )
        else:
            headline = f"Balanced Traverse: Multi-Objective Trade-Off ({primary_route.science_score:.0f} Science Points)."
            detail = (
                f"Captures {num_targets} high-yield targets ({', '.join(visited_names) if visited_names else 'none'}) "
                f"while requiring +{delta_dist:.0f} m (+{pct_dist:.1f}%) distance and +{pct_cost:.1f}% terrain cost over baseline."
            )
        eff_note = f"Harmonic trade-off score: {primary_route.science_score:.0f} pts at {primary_route.cost:.0f} cost units."

    else:
        headline = f"Traverse Profile: {primary_route.profile}."
        detail = f"Distance: {dist_m:.0f} m, Cost: {primary_route.cost:.0f}."
        eff_note = "Custom planning profile."

    return {
        "headline": headline,
        "detail": detail,
        "efficiency_note": eff_note,
        "budget_note": budget_note,
    }


def get_blind_spot_disclaimer(voice_mode: str = "professional") -> Dict[str, str]:
    """
    Return explicit data provenance and resolution limitation notices.
    Always serious, truthful, and unambiguous regardless of voice mode.
    """
    return {
        "provenance": (
            "Dataset: Mars 2020 Terrain Relative Navigation CTX DTM Mosaic (USGS Astrogeology Science Center). "
            "Authors: Fergason et al. (2020), DOI: 10.5066/P906QQT8. Vertical datum: MOLA DeltaGeoid."
        ),
        "resolution_limit": (
            "Spatial Resolution: Nominal 20 m/pixel orbital raster grid. At Jezero Crater's mapped latitude (~18.38°N), "
            "calibrated ground spacing is approximately 18.97 m East–West (dx) and 20.00 m North–South (dy) per cell (~379.4 m² footprint). "
            "Macro-slope derivatives are computed via calibrated 3x3 Horn finite differences."
        ),
        "unmodeled_hazards": (
            "MANDATORY SCIENTIFIC HONESTY DISCLAIMER: Orbital 20 m/pixel topography cannot resolve meter-scale "
            "angular boulders, overhangs, crevasse fractures, or unconsolidated aeolian drift (sand traps). "
            "Routes represent 'Low Modeled Macro-Slope Effort' and must NEVER be certified as operationally safe for crew."
        ),
    }
