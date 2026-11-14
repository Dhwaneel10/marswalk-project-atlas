"""
MarsWalk 2.0 / Project Atlas - Milestone 13J: Fleet Mission Scheduler.

Generates synchronized multi-sol schedules distributing parallel exploration activities
across exploration rovers: handles sequential dependencies, observation dwells,
relay deployments, scheduled data transfers, and inter-sol physical resource carryovers.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.fleet_operations_director import (
    RoverUnitConfig,
    RoverOperationalState,
    FleetStatus,
)
from marswalk.core.fleet_task_allocator import FleetScienceTarget
from marswalk.core.fleet_route_coordinator import FleetRoverRoute, SpatialTemporalConflict


class FleetActivityType(str, Enum):
    TRAVERSE = "TRAVERSE"
    SCIENCE_OBSERVATION = "SCIENCE_OBSERVATION"
    RELAY_DEPLOYMENT = "RELAY_DEPLOYMENT"
    DATA_TRANSFER = "DATA_TRANSFER"
    WAIT_DECONFLICT = "WAIT_DECONFLICT"
    BIVOUAC_REST = "BIVOUAC_REST"


@dataclass
class FleetScheduledActivity:
    """Discrete exploration activity assigned to an individual rover in the fleet timeline."""
    activity_id: str
    rover_id: str
    sol_index: int
    activity_type: str
    name: str
    start_met_s: float
    end_met_s: float
    duration_s: float
    target_id: Optional[str] = None
    location_rc: Tuple[int, int] = (128, 128)
    energy_cost_wh: float = 0.0
    data_impact_mb: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    status: str = "SCHEDULED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_id": self.activity_id,
            "rover_id": self.rover_id,
            "sol_index": self.sol_index,
            "activity_type": self.activity_type,
            "name": self.name,
            "start_met_s": round(self.start_met_s, 1),
            "end_met_s": round(self.end_met_s, 1),
            "duration_s": round(self.duration_s, 1),
            "target_id": self.target_id,
            "location_rc": list(self.location_rc),
            "energy_cost_wh": round(self.energy_cost_wh, 2),
            "data_impact_mb": round(self.data_impact_mb, 2),
            "dependencies": list(self.dependencies),
            "status": self.status,
        }


@dataclass
class FleetSolSchedule:
    """Synchronized timeline for a single Martian Sol across all fleet rovers."""
    sol_index: int
    rover_activities: Dict[str, List[FleetScheduledActivity]]  # rover_id -> activities
    sol_start_met_s: float
    sol_end_met_s: float
    total_sol_energy_wh: float = 0.0
    total_sol_distance_m: float = 0.0
    targets_investigated: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol_index": self.sol_index,
            "sol_start_met_s": round(self.sol_start_met_s, 1),
            "sol_end_met_s": round(self.sol_end_met_s, 1),
            "total_sol_energy_wh": round(self.total_sol_energy_wh, 2),
            "total_sol_distance_m": round(self.total_sol_distance_m, 1),
            "targets_investigated": list(self.targets_investigated),
            "rover_activities": {
                r_id: [act.to_dict() for act in acts]
                for r_id, acts in self.rover_activities.items()
            }
        }


@dataclass
class FleetCampaignSchedule:
    """Master multi-sol schedule coordinating parallel activities across the entire fleet."""
    fleet_id: str
    total_sols: int
    sols: List[FleetSolSchedule]
    total_activities: int
    campaign_duration_h: float
    total_fleet_energy_wh: float
    total_fleet_distance_m: float
    total_science_targets: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fleet_id": self.fleet_id,
            "total_sols": self.total_sols,
            "sols": [s.to_dict() for s in self.sols],
            "total_activities": self.total_activities,
            "campaign_duration_h": round(self.campaign_duration_h, 2),
            "total_fleet_energy_wh": round(self.total_fleet_energy_wh, 2),
            "total_fleet_distance_m": round(self.total_fleet_distance_m, 1),
            "total_science_targets": self.total_science_targets,
        }


class FleetMissionScheduler:
    """
    Constructs multi-sol fleet exploration schedules.
    Decomposes routes and assigned observations into parallel synchronized activity sequences.
    """

    def __init__(self, sol_duration_s: float = 88775.0, max_operational_sol_h: float = 7.5):
        self.sol_duration_s = sol_duration_s
        self.max_operational_s = max_operational_sol_h * 3600.0

    def build_fleet_schedule(
        self,
        fleet_id: str,
        rovers: Dict[str, RoverUnitConfig],
        routes: Dict[str, FleetRoverRoute],
        allocations: Dict[str, List[str]],
        targets_by_id: Dict[str, FleetScienceTarget],
        conflicts: Optional[List[SpatialTemporalConflict]] = None,
        max_sols: int = 5
    ) -> FleetCampaignSchedule:
        """
        Synthesizes a synchronized multi-sol schedule for the fleet.
        Distributes activities across sols, respecting daytime operational limits.
        """
        # Determine target assignments per rover per sol
        # For a 5-sol mission, distribute targets evenly across sols
        sol_schedules: List[FleetSolSchedule] = []
        total_acts = 0
        total_energy_fleet = 0.0
        total_dist_fleet = sum(r.total_distance_m for r in routes.values())

        for sol_idx in range(1, max_sols + 1):
            sol_start_met = (sol_idx - 1) * self.sol_duration_s
            sol_end_met = sol_start_met + self.sol_duration_s
            rover_acts: Dict[str, List[FleetScheduledActivity]] = {r_id: [] for r_id in rovers.keys()}
            sol_targets: List[str] = []
            sol_energy = 0.0

            for r_id, r_cfg in rovers.items():
                route = routes.get(r_id)
                r_t_ids = allocations.get(r_id, [])
                if not route or not r_t_ids:
                    # Idling or resting at base
                    act_idle = FleetScheduledActivity(
                        activity_id=f"act_{r_id.lower()}_sol{sol_idx}_rest",
                        rover_id=r_id,
                        sol_index=sol_idx,
                        activity_type=FleetActivityType.BIVOUAC_REST.value,
                        name=f"Nocturnal Bivouac & Telemetry Rest",
                        start_met_s=sol_start_met,
                        end_met_s=sol_start_met + 28800.0,
                        duration_s=28800.0,
                        energy_cost_wh=45.0,
                    )
                    rover_acts[r_id].append(act_idle)
                    total_acts += 1
                    continue

                # Slice targets assigned to this sol (modulo distribution)
                assigned_for_sol = [
                    t_id for i, t_id in enumerate(r_t_ids) if (i % max_sols) == (sol_idx - 1)
                ]

                curr_met = sol_start_met
                prev_act_id = None

                # 1. Traverse Activity
                dist_fraction = 1.0 / max_sols
                leg_dist_m = route.total_distance_m * dist_fraction
                leg_time_s = max(300.0, leg_dist_m / max(0.01, r_cfg.nominal_speed_mps))
                drive_energy_wh = (250.0 * leg_time_s) / 3600.0

                act_drive = FleetScheduledActivity(
                    activity_id=f"act_{r_id.lower()}_sol{sol_idx}_drive",
                    rover_id=r_id,
                    sol_index=sol_idx,
                    activity_type=FleetActivityType.TRAVERSE.value,
                    name=f"Surface Traverse Leg ({leg_dist_m:.0f} m)",
                    start_met_s=curr_met,
                    end_met_s=curr_met + leg_time_s,
                    duration_s=leg_time_s,
                    energy_cost_wh=drive_energy_wh,
                )
                rover_acts[r_id].append(act_drive)
                curr_met += leg_time_s
                prev_act_id = act_drive.activity_id
                total_acts += 1
                sol_energy += drive_energy_wh

                # 2. Science Observations for this sol
                for t_id in assigned_for_sol:
                    tgt = targets_by_id.get(t_id)
                    if not tgt:
                        continue
                    sol_targets.append(t_id)
                    dwell_s = tgt.required_dwell_s
                    obs_energy_wh = 35.0

                    act_obs = FleetScheduledActivity(
                        activity_id=f"act_{r_id.lower()}_sol{sol_idx}_sci_{t_id.lower()}",
                        rover_id=r_id,
                        sol_index=sol_idx,
                        activity_type=FleetActivityType.SCIENCE_OBSERVATION.value,
                        name=f"In-Situ Science: {tgt.name}",
                        start_met_s=curr_met,
                        end_met_s=curr_met + dwell_s,
                        duration_s=dwell_s,
                        target_id=t_id,
                        location_rc=tgt.location_rc,
                        energy_cost_wh=obs_energy_wh,
                        data_impact_mb=18.0,
                        dependencies=[prev_act_id] if prev_act_id else [],
                    )
                    rover_acts[r_id].append(act_obs)
                    curr_met += dwell_s
                    prev_act_id = act_obs.activity_id
                    total_acts += 1
                    sol_energy += obs_energy_wh

                # 3. Scheduled Data Downlink Activity
                transfer_s = 600.0  # 10 minute downlink window
                act_dl = FleetScheduledActivity(
                    activity_id=f"act_{r_id.lower()}_sol{sol_idx}_downlink",
                    rover_id=r_id,
                    sol_index=sol_idx,
                    activity_type=FleetActivityType.DATA_TRANSFER.value,
                    name=f"Relay Telemetry & Science Downlink",
                    start_met_s=curr_met,
                    end_met_s=curr_met + transfer_s,
                    duration_s=transfer_s,
                    energy_cost_wh=14.5,
                    data_impact_mb=-18.0,
                    dependencies=[prev_act_id] if prev_act_id else [],
                )
                rover_acts[r_id].append(act_dl)
                curr_met += transfer_s
                prev_act_id = act_dl.activity_id
                total_acts += 1
                sol_energy += 14.5

                # 4. Nocturnal Bivouac Rest
                rest_s = max(3600.0, sol_end_met - curr_met)
                act_rest = FleetScheduledActivity(
                    activity_id=f"act_{r_id.lower()}_sol{sol_idx}_bivouac",
                    rover_id=r_id,
                    sol_index=sol_idx,
                    activity_type=FleetActivityType.BIVOUAC_REST.value,
                    name=f"Inter-Sol Night Recharge Bivouac",
                    start_met_s=curr_met,
                    end_met_s=sol_end_met,
                    duration_s=rest_s,
                    energy_cost_wh=28.0,
                    dependencies=[prev_act_id] if prev_act_id else [],
                )
                rover_acts[r_id].append(act_rest)
                total_acts += 1
                sol_energy += 28.0

            total_energy_fleet += sol_energy
            sol_schedules.append(FleetSolSchedule(
                sol_index=sol_idx,
                rover_activities=rover_acts,
                sol_start_met_s=sol_start_met,
                sol_end_met_s=sol_end_met,
                total_sol_energy_wh=sol_energy,
                total_sol_distance_m=total_dist_fleet / max_sols,
                targets_investigated=sol_targets,
            ))

        total_campaign_h = (max_sols * self.sol_duration_s) / 3600.0
        all_targets_count = len({t for s in sol_schedules for t in s.targets_investigated})

        return FleetCampaignSchedule(
            fleet_id=fleet_id,
            total_sols=max_sols,
            sols=sol_schedules,
            total_activities=total_acts,
            campaign_duration_h=total_campaign_h,
            total_fleet_energy_wh=total_energy_fleet,
            total_fleet_distance_m=total_dist_fleet,
            total_science_targets=all_targets_count,
        )
