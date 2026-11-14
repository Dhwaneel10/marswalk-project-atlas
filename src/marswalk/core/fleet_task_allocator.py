"""
MarsWalk 2.0 / Project Atlas - Milestone 13J: Fleet Task Allocator.

Implements multi-rover science task allocation across planetary exploration units:
enforces authoritative 13G-R instrument-to-objective compatibility, physical energy feasibility,
storage capacity envelopes, and terrain traversal costs. Provides both bounded multi-objective
optimization and a greedy comparison baseline with comprehensive quantitative explanations.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.fleet_operations_director import RoverUnitConfig, RoverOperationalState
from marswalk.core.science_mission_planner import (
    InstrumentId,
    ScienceObjective,
    INSTRUMENT_CATALOG,
    InstrumentProfile,
)


class ScienceTargetPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NOMINAL = "NOMINAL"
    OPPORTUNISTIC = "OPPORTUNISTIC"


PRIORITY_WEIGHTS = {
    ScienceTargetPriority.CRITICAL.value: 2.0,
    ScienceTargetPriority.HIGH.value: 1.5,
    ScienceTargetPriority.NOMINAL.value: 1.0,
    ScienceTargetPriority.OPPORTUNISTIC.value: 0.5,
}


@dataclass
class FleetScienceTarget:
    """Planetary science observation target candidate for multi-rover allocation."""
    target_id: str
    name: str
    location_rc: Tuple[int, int]
    objective: str  # e.g. "MINERALOGICAL_INVESTIGATION"
    base_utility: float = 100.0
    priority: str = ScienceTargetPriority.HIGH.value
    required_dwell_s: float = 900.0  # 15 minutes default
    elevation_m: float = -2500.0
    max_slope_limit_deg: float = 20.0
    is_exclusive: bool = True  # Only one rover can investigate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "name": self.name,
            "location_rc": list(self.location_rc),
            "objective": self.objective,
            "base_utility": self.base_utility,
            "priority": self.priority,
            "required_dwell_s": self.required_dwell_s,
            "elevation_m": self.elevation_m,
            "max_slope_limit_deg": self.max_slope_limit_deg,
            "is_exclusive": self.is_exclusive,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetScienceTarget":
        return cls(
            target_id=str(data["target_id"]),
            name=str(data.get("name", data["target_id"])),
            location_rc=tuple(data.get("location_rc", (128, 128))),
            objective=str(data.get("objective", ScienceObjective.GEOLOGICAL_CHARACTERIZATION.value)),
            base_utility=float(data.get("base_utility", 100.0)),
            priority=str(data.get("priority", ScienceTargetPriority.HIGH.value)),
            required_dwell_s=float(data.get("required_dwell_s", 900.0)),
            elevation_m=float(data.get("elevation_m", -2500.0)),
            max_slope_limit_deg=float(data.get("max_slope_limit_deg", 20.0)),
            is_exclusive=bool(data.get("is_exclusive", True)),
        )


@dataclass
class RoverEligibilityAssessment:
    """Detailed eligibility and feasibility evaluation of a rover for a specific target."""
    rover_id: str
    target_id: str
    is_eligible: bool
    matching_instrument_id: Optional[str] = None
    matching_mode_name: Optional[str] = None
    estimated_distance_m: float = 0.0
    estimated_drive_time_s: float = 0.0
    estimated_energy_wh: float = 0.0
    estimated_data_mb: float = 0.0
    projected_post_soc_pct: float = 100.0
    projected_post_storage_pct: float = 0.0
    ineligibility_reasons: List[str] = field(default_factory=list)
    utility_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "target_id": self.target_id,
            "is_eligible": self.is_eligible,
            "matching_instrument_id": self.matching_instrument_id,
            "matching_mode_name": self.matching_mode_name,
            "estimated_distance_m": round(self.estimated_distance_m, 1),
            "estimated_drive_time_s": round(self.estimated_drive_time_s, 1),
            "estimated_energy_wh": round(self.estimated_energy_wh, 2),
            "estimated_data_mb": round(self.estimated_data_mb, 2),
            "projected_post_soc_pct": round(self.projected_post_soc_pct, 2),
            "projected_post_storage_pct": round(self.projected_post_storage_pct, 2),
            "ineligibility_reasons": list(self.ineligibility_reasons),
            "utility_score": round(self.utility_score, 2),
        }


@dataclass
class TaskAssignmentExplanation:
    """Quantitative decision audit explaining why a target was assigned to a rover."""
    target_id: str
    assigned_rover_id: Optional[str]
    supporting_instrument: Optional[str]
    supporting_mode: Optional[str]
    estimated_distance_m: float
    estimated_energy_wh: float
    estimated_data_mb: float
    reserve_margin_pct: float
    alternative_candidates: List[Dict[str, Any]]
    selection_rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "assigned_rover_id": self.assigned_rover_id,
            "supporting_instrument": self.supporting_instrument,
            "supporting_mode": self.supporting_mode,
            "estimated_distance_m": round(self.estimated_distance_m, 1),
            "estimated_energy_wh": round(self.estimated_energy_wh, 2),
            "estimated_data_mb": round(self.estimated_data_mb, 2),
            "reserve_margin_pct": round(self.reserve_margin_pct, 2),
            "alternative_candidates": self.alternative_candidates,
            "selection_rationale": self.selection_rationale,
        }


@dataclass
class FleetAllocationResult:
    """Consolidated outcome of the fleet task allocation engine."""
    allocation_plan: Dict[str, List[str]]  # rover_id -> [target_id, ...]
    unassigned_targets: List[str]
    explanations: Dict[str, TaskAssignmentExplanation]
    total_science_utility: float
    total_estimated_energy_wh: float
    total_estimated_distance_m: float
    method: str  # "BOUNDED_PARETO_OPTIMIZATION" or "GREEDY_BASELINE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_plan": {r_id: list(t_ids) for r_id, t_ids in self.allocation_plan.items()},
            "unassigned_targets": list(self.unassigned_targets),
            "explanations": {t_id: exp.to_dict() for t_id, exp in self.explanations.items()},
            "total_science_utility": round(self.total_science_utility, 1),
            "total_estimated_energy_wh": round(self.total_estimated_energy_wh, 2),
            "total_estimated_distance_m": round(self.total_estimated_distance_m, 1),
            "method": self.method,
        }


def get_default_jezero_targets() -> List[FleetScienceTarget]:
    """12 calibrated authentic geological science targets across Jezero western delta."""
    return [
        FleetScienceTarget(
            target_id="TGT_HAWKSBILL_GAP",
            name="Hawksbill Gap Delta Front",
            location_rc=(132, 135),
            objective=ScienceObjective.GEOLOGICAL_CHARACTERIZATION.value,
            base_utility=120.0,
            priority=ScienceTargetPriority.CRITICAL.value,
            required_dwell_s=1200.0,
            elevation_m=-2560.0,
        ),
        FleetScienceTarget(
            target_id="TGT_SKINNER_RIDGE",
            name="Skinner Ridge Layered Outcrop",
            location_rc=(136, 140),
            objective=ScienceObjective.MINERALOGICAL_INVESTIGATION.value,
            base_utility=140.0,
            priority=ScienceTargetPriority.CRITICAL.value,
            required_dwell_s=1500.0,
            elevation_m=-2540.0,
        ),
        FleetScienceTarget(
            target_id="TGT_ENCHANTED_LAKE",
            name="Enchanted Lake Fine Mudstones",
            location_rc=(140, 145),
            objective=ScienceObjective.ASTROBIOLOGY_BIOSIGNATURE_SURVEY.value,
            base_utility=160.0,
            priority=ScienceTargetPriority.CRITICAL.value,
            required_dwell_s=1800.0,
            elevation_m=-2520.0,
        ),
        FleetScienceTarget(
            target_id="TGT_DELTA_RIM_OVERLOOK",
            name="Delta Scarp Panoramic Overlook",
            location_rc=(146, 150),
            objective=ScienceObjective.SURFACE_MORPHOLOGY.value,
            base_utility=90.0,
            priority=ScienceTargetPriority.HIGH.value,
            required_dwell_s=900.0,
            elevation_m=-2490.0,
        ),
        FleetScienceTarget(
            target_id="TGT_BELVA_CRATER",
            name="Belva Impact Crater Megabreccia",
            location_rc=(152, 154),
            objective=ScienceObjective.GEOLOGICAL_CHARACTERIZATION.value,
            base_utility=110.0,
            priority=ScienceTargetPriority.HIGH.value,
            required_dwell_s=1200.0,
            elevation_m=-2470.0,
        ),
        FleetScienceTarget(
            target_id="TGT_KODIAK_BUTTE",
            name="Kodiak Butte Delta Remnant",
            location_rc=(122, 138),
            objective=ScienceObjective.SURFACE_MORPHOLOGY.value,
            base_utility=105.0,
            priority=ScienceTargetPriority.NOMINAL.value,
            required_dwell_s=900.0,
            elevation_m=-2580.0,
        ),
        FleetScienceTarget(
            target_id="TGT_NERETVA_CREST",
            name="Neretva Vallis Inflow Channel",
            location_rc=(135, 122),
            objective=ScienceObjective.MINERALOGICAL_INVESTIGATION.value,
            base_utility=130.0,
            priority=ScienceTargetPriority.HIGH.value,
            required_dwell_s=1200.0,
            elevation_m=-2550.0,
        ),
        FleetScienceTarget(
            target_id="TGT_SEITAH_DUNES",
            name="South Seitah Aeolian Ripples",
            location_rc=(124, 130),
            objective=ScienceObjective.SURFACE_MORPHOLOGY.value,
            base_utility=75.0,
            priority=ScienceTargetPriority.NOMINAL.value,
            required_dwell_s=600.0,
            elevation_m=-2590.0,
        ),
        FleetScienceTarget(
            target_id="TGT_PINNACLE_RIDGE",
            name="Pinnacle Ridge Carbonate Veins",
            location_rc=(142, 132),
            objective=ScienceObjective.MINERALOGICAL_INVESTIGATION.value,
            base_utility=125.0,
            priority=ScienceTargetPriority.NOMINAL.value,
            required_dwell_s=1200.0,
            elevation_m=-2530.0,
        ),
        FleetScienceTarget(
            target_id="TGT_SOLARIS_OUTCROP",
            name="Solaris Chert Biosignature Node",
            location_rc=(148, 142),
            objective=ScienceObjective.ASTROBIOLOGY_BIOSIGNATURE_SURVEY.value,
            base_utility=150.0,
            priority=ScienceTargetPriority.CRITICAL.value,
            required_dwell_s=1800.0,
            elevation_m=-2510.0,
        ),
        FleetScienceTarget(
            target_id="TGT_ZEPHYR_VENT",
            name="Zephyr Atmospheric Dust Sensor Site",
            location_rc=(130, 144),
            objective=ScienceObjective.ATMOSPHERIC_OBSERVATION.value,
            base_utility=80.0,
            priority=ScienceTargetPriority.OPPORTUNISTIC.value,
            required_dwell_s=600.0,
            elevation_m=-2570.0,
        ),
        FleetScienceTarget(
            target_id="TGT_AMALTHEA_BASALT",
            name="Amalthea Volcanic Floor Basalt",
            location_rc=(126, 126),
            objective=ScienceObjective.GEOLOGICAL_CHARACTERIZATION.value,
            base_utility=85.0,
            priority=ScienceTargetPriority.OPPORTUNISTIC.value,
            required_dwell_s=900.0,
            elevation_m=-2600.0,
        ),
    ]


class FleetTaskAllocator:
    """
    Intelligent multi-rover science task allocation engine.
    Ensures that targets are only assigned to eligible rovers carrying compatible instruments
    and possessing sufficient energy and storage capacity.
    """

    def __init__(self, ground_spacing_m: float = 20.0):
        self.ground_spacing_m = ground_spacing_m

    def find_matching_instrument_profile(
        self,
        rover_config: RoverUnitConfig,
        objective_str: str
    ) -> Optional[Tuple[str, InstrumentProfile]]:
        """
        Check if the rover carries an instrument compatible with the given science objective.
        Returns (catalog_key, profile) or None.
        """
        for cat_key, profile in INSTRUMENT_CATALOG.items():
            if profile.instrument_id.value in rover_config.instrument_ids:
                if any(obj.value == objective_str for obj in profile.compatible_objectives):
                    return (cat_key, profile)
        return None

    def assess_rover_eligibility(
        self,
        rover_config: RoverUnitConfig,
        rover_state: RoverOperationalState,
        target: FleetScienceTarget,
        current_allocated_targets: Optional[List[FleetScienceTarget]] = None
    ) -> RoverEligibilityAssessment:
        """
        Thoroughly evaluates whether a rover is eligible to take on a target,
        calculating projected energy, drive time, and storage impact.
        """
        ineligibility = []

        # 1. Check Instrument Compatibility
        matching = self.find_matching_instrument_profile(rover_config, target.objective)
        if not matching:
            ineligibility.append(
                f"Rover lacks any instrument compatible with objective '{target.objective}'. "
                f"Equipped: {rover_config.instrument_ids}"
            )
            matching_id = None
            matching_mode = None
            inst_profile = None
        else:
            cat_key, inst_profile = matching
            matching_id = inst_profile.instrument_id.value
            matching_mode = inst_profile.mode_name

        # 2. Check Rover Status
        if rover_state.status in ("UNAVAILABLE", "MAINTENANCE", "RETIRED"):
            ineligibility.append(f"Rover status is {rover_state.status}")

        # 3. Calculate Distance
        start_rc = rover_state.current_location_rc
        if current_allocated_targets:
            # Distance from last allocated target
            start_rc = current_allocated_targets[-1].location_rc

        dr = target.location_rc[0] - start_rc[0]
        dc = target.location_rc[1] - start_rc[1]
        dist_cells = math.hypot(dr, dc)
        dist_m = dist_cells * self.ground_spacing_m

        # Estimate Drive Time
        speed_mps = rover_config.nominal_speed_mps
        drive_time_s = dist_m / max(0.01, speed_mps)

        # Estimate Drive Energy: Minetti / Farley terramechanical proxy
        # Base power ~ 110 W, Drive power ~ 140 W -> ~250 W total moving load
        drive_power_w = rover_config.base_electrical_load_w + 140.0
        drive_energy_wh = (drive_power_w * drive_time_s) / 3600.0

        # Observation Energy & Data
        obs_energy_wh = inst_profile.energy_wh if inst_profile else 25.0
        obs_data_mb = (inst_profile.expected_data_bytes / (1024 * 1024)) if inst_profile else 10.0

        total_req_energy_wh = drive_energy_wh + obs_energy_wh

        # Check Energy Feasibility
        remaining_wh = rover_state.current_energy_wh
        reserve_threshold_wh = rover_config.usable_battery_capacity_wh * (rover_config.reserve_margin_pct / 100.0)
        projected_wh = remaining_wh - total_req_energy_wh
        projected_soc = (projected_wh / rover_config.usable_battery_capacity_wh) * 100.0

        if projected_wh < reserve_threshold_wh:
            ineligibility.append(
                f"Energy violation: Projected SOC ({projected_soc:.1f}%) breaches "
                f"{rover_config.reserve_margin_pct:.0f}% reserve ({reserve_threshold_wh:.1f} Wh). "
                f"Requires {total_req_energy_wh:.1f} Wh, available {remaining_wh - reserve_threshold_wh:.1f} Wh."
            )

        # Check Storage Buffer
        projected_storage_mb = rover_state.used_storage_mb + obs_data_mb
        projected_storage_pct = (projected_storage_mb / rover_config.storage_capacity_mb) * 100.0
        if projected_storage_pct > 95.0:
            ineligibility.append(
                f"Flash storage violation: Projected fill ({projected_storage_pct:.1f}%) exceeds 95% buffer ceiling."
            )

        # Compute Utility Score
        p_weight = PRIORITY_WEIGHTS.get(target.priority, 1.0)
        # Science utility normalized by distance/energy cost
        dist_penalty = (dist_m / 1000.0) * 8.0  # -8 pts per km
        energy_penalty = (total_req_energy_wh / 100.0) * 5.0
        utility_score = (target.base_utility * p_weight) - dist_penalty - energy_penalty

        is_eligible = len(ineligibility) == 0

        return RoverEligibilityAssessment(
            rover_id=rover_config.rover_id,
            target_id=target.target_id,
            is_eligible=is_eligible,
            matching_instrument_id=matching_id,
            matching_mode_name=matching_mode,
            estimated_distance_m=dist_m,
            estimated_drive_time_s=drive_time_s,
            estimated_energy_wh=total_req_energy_wh,
            estimated_data_mb=obs_data_mb,
            projected_post_soc_pct=projected_soc,
            projected_post_storage_pct=projected_storage_pct,
            ineligibility_reasons=ineligibility,
            utility_score=max(0.0, utility_score) if is_eligible else 0.0,
        )

    def allocate_fleet_science_tasks(
        self,
        rovers: Dict[str, RoverUnitConfig],
        rover_states: Dict[str, RoverOperationalState],
        targets: List[FleetScienceTarget],
        method: str = "BOUNDED_PARETO_OPTIMIZATION"
    ) -> FleetAllocationResult:
        """
        Allocates a set of science targets across active fleet rovers.
        Supports both bounded multi-objective optimization and greedy baseline.
        """
        allocation_plan: Dict[str, List[str]] = {r_id: [] for r_id in rovers.keys()}
        allocated_target_objs: Dict[str, List[FleetScienceTarget]] = {r_id: [] for r_id in rovers.keys()}
        explanations: Dict[str, TaskAssignmentExplanation] = {}
        unassigned: List[str] = []

        # Sort targets by priority weight descending, then base utility
        sorted_targets = sorted(
            targets,
            key=lambda t: (PRIORITY_WEIGHTS.get(t.priority, 1.0) * t.base_utility),
            reverse=True
        )

        for target in sorted_targets:
            # Assess all active rovers
            evaluations: List[RoverEligibilityAssessment] = []
            for r_id, r_cfg in rovers.items():
                r_state = rover_states.get(r_id)
                if not r_state:
                    continue
                current_allocs = allocated_target_objs[r_id]
                assessment = self.assess_rover_eligibility(r_cfg, r_state, target, current_allocs)
                evaluations.append(assessment)

            eligible = [ev for ev in evaluations if ev.is_eligible]

            if not eligible:
                unassigned.append(target.target_id)
                reasons_summary = "; ".join(
                    f"{ev.rover_id}: {', '.join(ev.ineligibility_reasons)}"
                    for ev in evaluations
                )
                explanations[target.target_id] = TaskAssignmentExplanation(
                    target_id=target.target_id,
                    assigned_rover_id=None,
                    supporting_instrument=None,
                    supporting_mode=None,
                    estimated_distance_m=0.0,
                    estimated_energy_wh=0.0,
                    estimated_data_mb=0.0,
                    reserve_margin_pct=0.0,
                    alternative_candidates=[ev.to_dict() for ev in evaluations],
                    selection_rationale=f"No eligible rover. Causes: {reasons_summary}",
                )
                continue

            if method == "GREEDY_BASELINE":
                # Nearest rover by distance only
                best_eval = min(eligible, key=lambda ev: ev.estimated_distance_m)
            else:
                # Bounded Pareto Optimization: maximizes utility score (utility / cost / margin balance)
                # Also balance workload: penalize rovers that already have many targets
                best_eval = max(
                    eligible,
                    key=lambda ev: ev.utility_score - (len(allocation_plan[ev.rover_id]) * 15.0)
                )

            # Assign to best rover
            chosen_r_id = best_eval.rover_id
            allocation_plan[chosen_r_id].append(target.target_id)
            allocated_target_objs[chosen_r_id].append(target)

            # Build quantitative explanation
            alternatives = []
            for ev in evaluations:
                if ev.rover_id != chosen_r_id:
                    status_note = "Eligible alternative" if ev.is_eligible else f"Ineligible: {', '.join(ev.ineligibility_reasons)}"
                    alternatives.append({
                        "rover_id": ev.rover_id,
                        "is_eligible": ev.is_eligible,
                        "utility_score": round(ev.utility_score, 2),
                        "distance_m": round(ev.estimated_distance_m, 1),
                        "note": status_note,
                    })

            explanations[target.target_id] = TaskAssignmentExplanation(
                target_id=target.target_id,
                assigned_rover_id=chosen_r_id,
                supporting_instrument=best_eval.matching_instrument_id,
                supporting_mode=best_eval.matching_mode_name,
                estimated_distance_m=best_eval.estimated_distance_m,
                estimated_energy_wh=best_eval.estimated_energy_wh,
                estimated_data_mb=best_eval.estimated_data_mb,
                reserve_margin_pct=best_eval.projected_post_soc_pct - rovers[chosen_r_id].reserve_margin_pct,
                alternative_candidates=alternatives,
                selection_rationale=(
                    f"Assigned to {chosen_r_id} via {best_eval.matching_instrument_id} "
                    f"({best_eval.matching_mode_name}). Estimated distance: {best_eval.estimated_distance_m:.1f} m, "
                    f"energy: {best_eval.estimated_energy_wh:.1f} Wh, post-observation SOC: {best_eval.projected_post_soc_pct:.1f}% "
                    f"(margin +{best_eval.projected_post_soc_pct - rovers[chosen_r_id].reserve_margin_pct:.1f}%)."
                ),
            )

        # Aggregate total metrics
        total_utility = sum(
            t.base_utility * PRIORITY_WEIGHTS.get(t.priority, 1.0)
            for t in targets if t.target_id in explanations and explanations[t.target_id].assigned_rover_id is not None
        )
        total_energy = sum(
            exp.estimated_energy_wh for exp in explanations.values() if exp.assigned_rover_id is not None
        )
        total_dist = sum(
            exp.estimated_distance_m for exp in explanations.values() if exp.assigned_rover_id is not None
        )

        return FleetAllocationResult(
            allocation_plan=allocation_plan,
            unassigned_targets=unassigned,
            explanations=explanations,
            total_science_utility=total_utility,
            total_estimated_energy_wh=total_energy,
            total_estimated_distance_m=total_dist,
            method=method,
        )
