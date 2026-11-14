"""
MarsWalk 2.0 / Project Atlas — Milestone 13P: Rover–Aircraft Cooperative Mission Engine
======================================================================================
Coordinates joint planetary exploration between surface rovers and aerial rotorcraft:
- Aerial Reconnaissance: Scout surveys ahead of the rover over unmapped terrain.
- Route Refinement: Evaluates rover-only blind path vs aerial-assisted path, quantifying:
  * Route uncertainty reduction (%)
  * Newly discovered terrain hazards and rockfall slumps
  * Rover traverse distance and energy savings from avoiding entrapment / dead-ends
- Science Target Discovery: Aerial scouting identifies candidate astrobiology targets.
- Dynamic Tradeoff Analysis: Formally determines whether launching an aerial sortie produces
  net mission value or should be rejected due to battery/operational overhead.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.mars_aircraft_fleet import AircraftState
from marswalk.core.mars_aerial_science import AerialObservation


@dataclass
class CooperativeReconnaissancePlan:
    """Joint mission plan coupling a surface rover with an aerial scout."""
    cooperation_id: str
    rover_id: str
    aircraft_id: str
    target_region_name: str
    scouting_corridor_origin_xy_m: List[float]
    scouting_corridor_target_xy_m: List[float]
    baseline_rover_path_distance_m: float
    baseline_rover_uncertainty_pct: float
    baseline_rover_energy_wh: float
    aerial_scout_distance_m: float
    aerial_scout_energy_wh: float
    refined_rover_path_distance_m: float
    refined_rover_uncertainty_pct: float
    refined_rover_energy_wh: float
    obstacles_discovered_count: int
    net_rover_distance_delta_m: float
    net_mission_energy_delta_wh: float
    uncertainty_reduction_pct: float
    cooperation_recommended: bool
    decision_rationale: str
    discovered_hazards: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cooperation_id": self.cooperation_id,
            "rover_id": self.rover_id,
            "aircraft_id": self.aircraft_id,
            "target_region_name": self.target_region_name,
            "baseline_rover_path_distance_m": round(self.baseline_rover_path_distance_m, 1),
            "baseline_rover_uncertainty_pct": round(self.baseline_rover_uncertainty_pct, 1),
            "baseline_rover_energy_wh": round(self.baseline_rover_energy_wh, 1),
            "aerial_scout_distance_m": round(self.aerial_scout_distance_m, 1),
            "aerial_scout_energy_wh": round(self.aerial_scout_energy_wh, 1),
            "refined_rover_path_distance_m": round(self.refined_rover_path_distance_m, 1),
            "refined_rover_uncertainty_pct": round(self.refined_rover_uncertainty_pct, 1),
            "refined_rover_energy_wh": round(self.refined_rover_energy_wh, 1),
            "obstacles_discovered_count": self.obstacles_discovered_count,
            "net_rover_distance_delta_m": round(self.net_rover_distance_delta_m, 1),
            "net_mission_energy_delta_wh": round(self.net_mission_energy_delta_wh, 1),
            "uncertainty_reduction_pct": round(self.uncertainty_reduction_pct, 1),
            "cooperation_recommended": self.cooperation_recommended,
            "decision_rationale": self.decision_rationale,
            "discovered_hazards": self.discovered_hazards,
        }


class MarsAerialRoverCoordinator:
    """
    Evaluates, optimizes, and coordinates joint ground-aerial exploration campaigns.
    """

    def __init__(self):
        self._cooperative_plans: Dict[str, CooperativeReconnaissancePlan] = {}

    def plan_joint_reconnaissance(
        self,
        rover_id: str,
        aircraft_id: str,
        target_region_name: str,
        rover_current_xy_m: List[float],
        science_target_xy_m: List[float],
        orbital_obstacle_present_in_corridor: bool = True,
    ) -> CooperativeReconnaissancePlan:
        """
        Synthesizes a joint reconnaissance mission.
        Evaluates rover-only blind path vs aerial-scouted refined path.
        """
        coop_id = f"COOP-{uuid.uuid4().hex[:8].upper()}"

        # 1. Baseline Rover-Only Traverse Metrics
        direct_dist = math.sqrt(
            (science_target_xy_m[0] - rover_current_xy_m[0]) ** 2 +
            (science_target_xy_m[1] - rover_current_xy_m[1]) ** 2
        )
        # Without aerial scout, rover must take cautious, blind route with risk of backtracking
        if orbital_obstacle_present_in_corridor:
            # Blind rover encounters unmapped boulder field mid-traverse, must backtrack 45m
            baseline_rover_dist = direct_dist * 1.45 + 45.0
            baseline_uncertainty = 68.0  # % terrain risk
            discovered_hazards = [
                {
                    "hazard_id": "HAZ-CRATER-RIM-BOULDERS",
                    "type": "IMPACT_EJECTA_FIELD",
                    "coordinates_xy_m": [
                        rover_current_xy_m[0] + 0.5 * (science_target_xy_m[0] - rover_current_xy_m[0]),
                        rover_current_xy_m[1] + 0.5 * (science_target_xy_m[1] - rover_current_xy_m[1]),
                    ],
                    "radius_m": 12.0,
                    "max_slope_deg": 19.5,
                    "belly_clearance_violation": True,
                }
            ]
            obstacles_found = len(discovered_hazards)
        else:
            baseline_rover_dist = direct_dist * 1.15
            baseline_uncertainty = 35.0
            discovered_hazards = []
            obstacles_found = 0

        # Rover energy consumption model: ~3.2 Wh per meter of rough terrain traverse
        rover_specific_energy_wh_m = 3.2
        baseline_rover_energy = baseline_rover_dist * rover_specific_energy_wh_m

        # 2. Aerial Scout Reconnaissance Flight Metrics
        # Aircraft flies directly over terrain at 15m altitude, unconstrained by surface rocks
        aerial_flight_dist = direct_dist * 1.05 + 30.0  # including vertical climb/descent
        # Aircraft power: ~380W at 7 m/s speed => ~15.1 Wh per 100m
        aerial_energy = (aerial_flight_dist / 7.0) * (380.0 / 3600.0)

        # 3. Refined Rover Path (Informed by Aerial Scout Map)
        if orbital_obstacle_present_in_corridor:
            # Aerial scout spots the boulder field from above!
            # Rover takes smooth, pre-planned detour around the hazard without backtracking
            refined_rover_dist = direct_dist * 1.18
            refined_uncertainty = 8.5  # Down to 8.5%
        else:
            refined_rover_dist = direct_dist * 1.08
            refined_uncertainty = 5.0

        refined_rover_energy = refined_rover_dist * rover_specific_energy_wh_m

        # 4. Net Mission Deltas & Tradeoff Analysis
        dist_saved = baseline_rover_dist - refined_rover_dist
        rover_energy_saved = baseline_rover_energy - refined_rover_energy
        net_mission_energy_delta = rover_energy_saved - aerial_energy
        uncertainty_reduction = baseline_uncertainty - refined_uncertainty

        # Recommendation: recommend only if rover saves significant distance/uncertainty
        cooperation_recommended = (dist_saved > 20.0 or uncertainty_reduction > 30.0) and (net_mission_energy_delta > 0.0)

        if cooperation_recommended:
            rationale = (
                f"RECOMMENDED: Aerial scout deployment identifies {obstacles_found} impassable obstacle(s), "
                f"reducing rover traverse by {dist_saved:.1f}m and saving {net_mission_energy_delta:.1f} Wh net energy "
                f"while slashing route uncertainty from {baseline_uncertainty:.1f}% to {refined_uncertainty:.1f}%."
            )
        else:
            rationale = (
                "NOT RECOMMENDED: Terrain path is benign. Aerial flight battery expenditure "
                f"({aerial_energy:.1f} Wh) exceeds expected rover traverse savings."
            )

        plan = CooperativeReconnaissancePlan(
            cooperation_id=coop_id,
            rover_id=rover_id,
            aircraft_id=aircraft_id,
            target_region_name=target_region_name,
            scouting_corridor_origin_xy_m=list(rover_current_xy_m),
            scouting_corridor_target_xy_m=list(science_target_xy_m),
            baseline_rover_path_distance_m=baseline_rover_dist,
            baseline_rover_uncertainty_pct=baseline_uncertainty,
            baseline_rover_energy_wh=baseline_rover_energy,
            aerial_scout_distance_m=aerial_flight_dist,
            aerial_scout_energy_wh=aerial_energy,
            refined_rover_path_distance_m=refined_rover_dist,
            refined_rover_uncertainty_pct=refined_uncertainty,
            refined_rover_energy_wh=refined_rover_energy,
            obstacles_discovered_count=obstacles_found,
            net_rover_distance_delta_m=dist_saved,
            net_mission_energy_delta_wh=net_mission_energy_delta,
            uncertainty_reduction_pct=uncertainty_reduction,
            cooperation_recommended=cooperation_recommended,
            decision_rationale=rationale,
            discovered_hazards=discovered_hazards,
        )

        self._cooperative_plans[coop_id] = plan
        return plan

    def get_plan(self, cooperation_id: str) -> Optional[CooperativeReconnaissancePlan]:
        return self._cooperative_plans.get(cooperation_id)
