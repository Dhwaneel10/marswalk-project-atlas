"""
MarsWalk Core Mission Energy and Resource Intelligence Engine (Milestone 13F).

Provides transparent, deterministic, terrain-aware energy budgeting, electrical load accounting,
communications infrastructure power modeling, mission scheduling, and resource feasibility analysis.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

# Physical & Astronomical Constants
MARS_GRAVITY_MPS2: float = 3.71       # Surface gravitational acceleration (m/s^2)
JOULES_PER_WH: float = 3600.0         # 1 Watt-hour = 3600 Joules
WH_PER_JOULE: float = 1.0 / 3600.0


class ResourceFeasibilityClassification(str, Enum):
    """Rigorous classification of operational energy and time feasibility."""
    FEASIBLE_WITHIN_CONFIGURED_BUDGET = "FEASIBLE_WITHIN_CONFIGURED_BUDGET"
    FEASIBLE_WITH_LOW_RESERVE = "FEASIBLE_WITH_LOW_RESERVE"
    ENERGY_CONSTRAINT_VIOLATION = "ENERGY_CONSTRAINT_VIOLATION"
    TIME_CONSTRAINT_VIOLATION = "TIME_CONSTRAINT_VIOLATION"
    MULTIPLE_CONSTRAINT_VIOLATIONS = "MULTIPLE_CONSTRAINT_VIOLATIONS"
    UNKNOWN_RESOURCE_FEASIBILITY = "UNKNOWN_RESOURCE_FEASIBILITY"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


def joules_to_wh(j: float) -> float:
    """Convert Joules to Watt-hours."""
    return float(j) * WH_PER_JOULE


def wh_to_joules(wh: float) -> float:
    """Convert Watt-hours to Joules."""
    return float(wh) * JOULES_PER_WH


def format_energy_si(j: float) -> str:
    """Format energy in SI Joules and Watt-hours for human-readable reporting."""
    if not math.isfinite(j):
        return "UNKNOWN"
    wh = joules_to_wh(j)
    if abs(j) >= 1e6:
        return f"{j / 1e6:.2f} MJ ({wh:.1f} Wh)"
    elif abs(j) >= 1e3:
        return f"{j / 1e3:.1f} kJ ({wh:.1f} Wh)"
    return f"{j:.1f} J ({wh:.2f} Wh)"


def format_power_si(w: float) -> str:
    """Format power in SI Watts."""
    if not math.isfinite(w):
        return "UNKNOWN"
    if abs(w) >= 1e3:
        return f"{w / 1e3:.2f} kW"
    return f"{w:.1f} W"


@dataclass
class RoverResourceConfig:
    """
    Configurable engineering parameters for a surface exploration rover or vehicle.
    All calculations use SI units internally.
    """
    rover_mass_kg: float = 1025.0                 # Perseverance rover dry+wet baseline
    payload_mass_kg: float = 50.0                 # Added science sample/caching payload
    usable_battery_capacity_wh: float = 4800.0    # Usable energy envelope (4.8 kWh = 17.28 MJ)
    reserve_margin_pct: float = 20.0              # Reserve margin threshold (0-100%)
    rolling_resistance_crr: float = 0.08          # Dimensionless rolling resistance on regolith
    drivetrain_efficiency: float = 0.72           # Electrical-to-mechanical drive efficiency (eta)
    nominal_drive_speed_mps: float = 0.38         # Average driving speed (m/s)
    base_electrical_load_w: float = 110.0         # Continuous avionics, computing, thermal control
    instrument_standby_w: float = 15.0            # Sensors idling during movement
    instrument_active_w: float = 120.0            # Active science drilling/spectroscopy load
    instrument_duty_cycle: float = 0.25           # Active duty cycle fraction during observations
    comm_standby_w: float = 20.0                  # Listening/beacon monitoring power
    comm_active_w: float = 85.0                   # High-gain transmit / relay uplink power
    science_dwell_s: float = 900.0                # Science stop observation dwell time (15 min)
    relay_deployment_s: float = 1200.0            # Field relay deployment dwell time (20 min)
    operational_delay_s: float = 0.0              # Unscheduled operational latency / pause
    max_mission_duration_s: float = 88775.0       # 1 Sol planning window
    allow_regenerative_braking: bool = False      # Default strict: no unmodeled regen

    def __post_init__(self):
        # Validate all parameters: reject non-finite, negative or invalid numbers
        for name, val in [
            ("rover_mass_kg", self.rover_mass_kg),
            ("payload_mass_kg", self.payload_mass_kg),
            ("usable_battery_capacity_wh", self.usable_battery_capacity_wh),
            ("rolling_resistance_crr", self.rolling_resistance_crr),
            ("nominal_drive_speed_mps", self.nominal_drive_speed_mps),
            ("base_electrical_load_w", self.base_electrical_load_w),
            ("instrument_standby_w", self.instrument_standby_w),
            ("instrument_active_w", self.instrument_active_w),
            ("comm_standby_w", self.comm_standby_w),
            ("comm_active_w", self.comm_active_w),
            ("science_dwell_s", self.science_dwell_s),
            ("relay_deployment_s", self.relay_deployment_s),
            ("operational_delay_s", self.operational_delay_s),
            ("max_mission_duration_s", self.max_mission_duration_s),
        ]:
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"RoverResourceConfig '{name}' must be finite and non-negative, got {val}")

        if not math.isfinite(self.drivetrain_efficiency) or not (0.0 < self.drivetrain_efficiency <= 1.0):
            raise ValueError(f"drivetrain_efficiency must be in (0, 1], got {self.drivetrain_efficiency}")

        if not math.isfinite(self.reserve_margin_pct) or not (0.0 <= self.reserve_margin_pct <= 100.0):
            raise ValueError(f"reserve_margin_pct must be between 0 and 100, got {self.reserve_margin_pct}")

        if not math.isfinite(self.instrument_duty_cycle) or not (0.0 <= self.instrument_duty_cycle <= 1.0):
            raise ValueError(f"instrument_duty_cycle must be in [0, 1], got {self.instrument_duty_cycle}")

        if self.nominal_drive_speed_mps <= 0.0:
            raise ValueError("nominal_drive_speed_mps must be strictly positive")

    @property
    def total_mass_kg(self) -> float:
        return self.rover_mass_kg + self.payload_mass_kg

    @property
    def usable_battery_capacity_j(self) -> float:
        return wh_to_joules(self.usable_battery_capacity_wh)

    @property
    def reserve_threshold_j(self) -> float:
        return self.usable_battery_capacity_j * (self.reserve_margin_pct / 100.0)

    @property
    def reserve_threshold_wh(self) -> float:
        return self.usable_battery_capacity_wh * (self.reserve_margin_pct / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_mass_kg": self.rover_mass_kg,
            "payload_mass_kg": self.payload_mass_kg,
            "total_mass_kg": self.total_mass_kg,
            "usable_battery_capacity_wh": self.usable_battery_capacity_wh,
            "usable_battery_capacity_j": self.usable_battery_capacity_j,
            "reserve_margin_pct": self.reserve_margin_pct,
            "reserve_threshold_wh": self.reserve_threshold_wh,
            "reserve_threshold_j": self.reserve_threshold_j,
            "rolling_resistance_crr": self.rolling_resistance_crr,
            "drivetrain_efficiency": self.drivetrain_efficiency,
            "nominal_drive_speed_mps": self.nominal_drive_speed_mps,
            "base_electrical_load_w": self.base_electrical_load_w,
            "instrument_standby_w": self.instrument_standby_w,
            "instrument_active_w": self.instrument_active_w,
            "instrument_duty_cycle": self.instrument_duty_cycle,
            "comm_standby_w": self.comm_standby_w,
            "comm_active_w": self.comm_active_w,
            "science_dwell_s": self.science_dwell_s,
            "relay_deployment_s": self.relay_deployment_s,
            "operational_delay_s": self.operational_delay_s,
            "max_mission_duration_s": self.max_mission_duration_s,
            "allow_regenerative_braking": self.allow_regenerative_braking,
        }


@dataclass
class RelayResourceConfig:
    """
    Configurable parameters for deployed surface relay towers (Mars RelayNet).
    """
    usable_battery_capacity_wh: float = 400.0     # 400 Wh = 1.44 MJ per deployed mast
    reserve_margin_pct: float = 15.0              # 15% reserve threshold
    standby_power_w: float = 8.0                  # Idle RF receiver power
    active_tx_power_w: float = 35.0               # High-power transceiver active relaying

    def __post_init__(self):
        for name, val in [
            ("usable_battery_capacity_wh", self.usable_battery_capacity_wh),
            ("standby_power_w", self.standby_power_w),
            ("active_tx_power_w", self.active_tx_power_w),
        ]:
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"RelayResourceConfig '{name}' must be finite and non-negative, got {val}")

        if not math.isfinite(self.reserve_margin_pct) or not (0.0 <= self.reserve_margin_pct <= 100.0):
            raise ValueError(f"reserve_margin_pct must be between 0 and 100, got {self.reserve_margin_pct}")

    @property
    def usable_battery_capacity_j(self) -> float:
        return wh_to_joules(self.usable_battery_capacity_wh)

    @property
    def reserve_threshold_j(self) -> float:
        return self.usable_battery_capacity_j * (self.reserve_margin_pct / 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usable_battery_capacity_wh": self.usable_battery_capacity_wh,
            "usable_battery_capacity_j": self.usable_battery_capacity_j,
            "reserve_margin_pct": self.reserve_margin_pct,
            "reserve_threshold_j": self.reserve_threshold_j,
            "standby_power_w": self.standby_power_w,
            "active_tx_power_w": self.active_tx_power_w,
        }


@dataclass
class SegmentResourceRecord:
    """Detailed resource breakdown for a single discrete traverse cell transition."""
    step_idx: int
    start_rc: Tuple[int, int]
    end_rc: Tuple[int, int]
    distance_m: float
    elevation_change_m: float
    slope_deg: float
    duration_s: float
    rolling_work_j: float
    gravitational_work_j: float
    mechanical_work_j: float
    mobility_energy_j: float
    electrical_load_energy_j: float
    total_energy_consumed_j: float
    energy_remaining_j: float
    battery_soc_pct: float
    is_reserve_violated: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_idx": self.step_idx,
            "start_rc": list(self.start_rc),
            "end_rc": list(self.end_rc),
            "distance_m": round(self.distance_m, 2),
            "elevation_change_m": round(self.elevation_change_m, 2),
            "slope_deg": round(self.slope_deg, 2),
            "duration_s": round(self.duration_s, 2),
            "rolling_work_j": round(self.rolling_work_j, 1),
            "gravitational_work_j": round(self.gravitational_work_j, 1),
            "mechanical_work_j": round(self.mechanical_work_j, 1),
            "mobility_energy_j": round(self.mobility_energy_j, 1),
            "electrical_load_energy_j": round(self.electrical_load_energy_j, 1),
            "total_energy_consumed_j": round(self.total_energy_consumed_j, 1),
            "energy_remaining_j": round(self.energy_remaining_j, 1),
            "battery_soc_pct": round(self.battery_soc_pct, 2),
            "is_reserve_violated": self.is_reserve_violated,
        }


@dataclass
class MissionActivityEvent:
    """Discrete operational event in the chronological mission schedule."""
    event_id: str
    event_type: str        # "traverse_step", "science_dwell", "relay_deployment", "operational_delay"
    label: str
    start_time_s: float
    end_time_s: float
    duration_s: float
    average_power_w: float
    energy_consumed_j: float
    cumulative_energy_consumed_j: float
    energy_remaining_j: float
    battery_soc_pct: float
    location_rc: Optional[Tuple[int, int]] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "label": self.label,
            "start_time_s": round(self.start_time_s, 2),
            "end_time_s": round(self.end_time_s, 2),
            "duration_s": round(self.duration_s, 2),
            "average_power_w": round(self.average_power_w, 1),
            "energy_consumed_j": round(self.energy_consumed_j, 1),
            "cumulative_energy_consumed_j": round(self.cumulative_energy_consumed_j, 1),
            "energy_remaining_j": round(self.energy_remaining_j, 1),
            "battery_soc_pct": round(self.battery_soc_pct, 2),
            "location_rc": list(self.location_rc) if self.location_rc else None,
            "notes": self.notes,
        }


@dataclass
class MissionResourceLedger:
    """Comprehensive resource budget and energy ledger for an entire mission configuration."""
    total_distance_m: float
    total_duration_s: float
    traverse_duration_s: float
    activity_duration_s: float
    total_rolling_work_j: float
    total_gravitational_work_j: float
    total_mechanical_work_j: float
    total_mobility_energy_j: float
    total_electrical_energy_j: float
    total_mission_energy_j: float
    total_relay_energy_j: float
    peak_instantaneous_power_w: float
    energy_per_km_wh: float
    final_energy_remaining_j: float
    min_energy_remaining_j: float
    final_battery_soc_pct: float
    min_battery_soc_pct: float
    reserve_threshold_j: float
    reserve_margin_wh: float
    is_reserve_violated: bool
    is_time_violated: bool
    feasibility_classification: ResourceFeasibilityClassification
    constraint_violations: List[str]
    segment_records: List[SegmentResourceRecord] = field(default_factory=list)
    timeline_events: List[MissionActivityEvent] = field(default_factory=list)
    relay_breakdown: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_mission_energy_wh(self) -> float:
        return joules_to_wh(self.total_mission_energy_j)

    @property
    def total_mobility_energy_wh(self) -> float:
        return joules_to_wh(self.total_mobility_energy_j)

    @property
    def total_electrical_energy_wh(self) -> float:
        return joules_to_wh(self.total_electrical_energy_j)

    @property
    def total_relay_energy_wh(self) -> float:
        return joules_to_wh(self.total_relay_energy_j)

    @property
    def final_energy_remaining_wh(self) -> float:
        return joules_to_wh(self.final_energy_remaining_j)

    @property
    def min_energy_remaining_wh(self) -> float:
        return joules_to_wh(self.min_energy_remaining_j)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_distance_m": round(self.total_distance_m, 2),
                "total_duration_s": round(self.total_duration_s, 1),
                "traverse_duration_s": round(self.traverse_duration_s, 1),
                "activity_duration_s": round(self.activity_duration_s, 1),
                "total_mechanical_work_j": round(self.total_mechanical_work_j, 1),
                "total_mobility_energy_j": round(self.total_mobility_energy_j, 1),
                "total_mobility_energy_wh": round(self.total_mobility_energy_wh, 2),
                "total_electrical_energy_j": round(self.total_electrical_energy_j, 1),
                "total_electrical_energy_wh": round(self.total_electrical_energy_wh, 2),
                "total_mission_energy_j": round(self.total_mission_energy_j, 1),
                "total_mission_energy_wh": round(self.total_mission_energy_wh, 2),
                "total_relay_energy_j": round(self.total_relay_energy_j, 1),
                "total_relay_energy_wh": round(self.total_relay_energy_wh, 2),
                "peak_instantaneous_power_w": round(self.peak_instantaneous_power_w, 1),
                "energy_per_km_wh": round(self.energy_per_km_wh, 2),
                "final_energy_remaining_j": round(self.final_energy_remaining_j, 1),
                "final_energy_remaining_wh": round(self.final_energy_remaining_wh, 2),
                "min_energy_remaining_j": round(self.min_energy_remaining_j, 1),
                "min_energy_remaining_wh": round(self.min_energy_remaining_wh, 2),
                "final_battery_soc_pct": round(self.final_battery_soc_pct, 2),
                "min_battery_soc_pct": round(self.min_battery_soc_pct, 2),
                "reserve_threshold_j": round(self.reserve_threshold_j, 1),
                "reserve_margin_wh": round(self.reserve_margin_wh, 2),
                "is_reserve_violated": self.is_reserve_violated,
                "is_time_violated": self.is_time_violated,
                "feasibility_classification": self.feasibility_classification.value,
                "constraint_violations": self.constraint_violations,
            },
            "segment_records_count": len(self.segment_records),
            "timeline_events_count": len(self.timeline_events),
            "timeline_events": [e.to_dict() for e in self.timeline_events],
            "relay_breakdown": self.relay_breakdown,
        }


@dataclass
class ResourceSensitivityResult:
    """Results of deterministic parameter perturbation sensitivity analysis."""
    baseline_energy_j: float
    baseline_energy_wh: float
    baseline_margin_wh: float
    parameter_sweeps: Dict[str, Dict[str, Any]]
    sensitivity_ranking: List[Dict[str, Any]]
    consumption_range_wh: Tuple[float, float]
    remaining_energy_range_wh: Tuple[float, float]
    constraint_crossing_parameters: List[str]
    provenance_statement: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_energy_wh": round(self.baseline_energy_wh, 2),
            "baseline_margin_wh": round(self.baseline_margin_wh, 2),
            "parameter_sweeps": self.parameter_sweeps,
            "sensitivity_ranking": self.sensitivity_ranking,
            "consumption_range_wh": [round(self.consumption_range_wh[0], 2), round(self.consumption_range_wh[1], 2)],
            "remaining_energy_range_wh": [round(self.remaining_energy_range_wh[0], 2), round(self.remaining_energy_range_wh[1], 2)],
            "constraint_crossing_parameters": self.constraint_crossing_parameters,
            "provenance_statement": self.provenance_statement,
        }


# ==============================================================================
# Core Engineering Equations & Evaluation Functions
# ==============================================================================

def calculate_segment_mobility_energy(
    distance_m: float,
    elevation_change_m: float,
    slope_deg: float,
    config: RoverResourceConfig,
) -> Tuple[float, float, float, float, float]:
    """
    Computes first-order mechanical work and electrical energy for a discrete traverse step.
    Returns: (rolling_work_j, gravitational_work_j, mechanical_work_j, mobility_energy_j, duration_s)
    """
    if not math.isfinite(distance_m) or distance_m < 0.0:
        raise ValueError(f"Invalid distance_m: {distance_m}")
    if not math.isfinite(elevation_change_m):
        raise ValueError(f"Invalid elevation_change_m: {elevation_change_m}")
    if not math.isfinite(slope_deg) or slope_deg < 0.0:
        raise ValueError(f"Invalid slope_deg: {slope_deg}")

    # Slope angle in radians (bounded to [0, pi/2])
    theta_rad = math.radians(min(slope_deg, 89.9))

    # Rolling resistance work: W_r = C_rr * m * g * cos(theta) * d
    # Uses local surface normal force reduction: N = m * g * cos(theta)
    normal_force = config.total_mass_kg * MARS_GRAVITY_MPS2 * math.cos(theta_rad)
    rolling_work_j = config.rolling_resistance_crr * normal_force * distance_m

    # Gravitational work: W_g = m * g * Delta_h
    gravitational_work_j = config.total_mass_kg * MARS_GRAVITY_MPS2 * elevation_change_m

    # Mechanical work: distinguish uphill from downhill
    if config.allow_regenerative_braking:
        # Bounded net work with regeneration: cannot produce more energy than rolling resistance allows
        mechanical_work_j = max(0.0, rolling_work_j + gravitational_work_j)
    else:
        # Strict classical standard: no downhill energy generation
        # On downhill (gravitational_work_j < 0), max(0, W_g) = 0, so wheels must still overcome rolling friction!
        mechanical_work_j = rolling_work_j + max(0.0, gravitational_work_j)

    # Electrical mobility energy: E_m = W_m / eta
    mobility_energy_j = mechanical_work_j / config.drivetrain_efficiency

    # Step duration: Delta_t = d / v
    duration_s = distance_m / config.nominal_drive_speed_mps

    return rolling_work_j, gravitational_work_j, mechanical_work_j, mobility_energy_j, duration_s


def evaluate_mission_resource_ledger(
    path_rc: List[Tuple[int, int]],
    elevation_grid: np.ndarray,
    slope_grid: np.ndarray,
    invalid_mask: np.ndarray,
    ground_dx_m: float,
    ground_dy_m: float,
    rover_config: RoverResourceConfig,
    relay_config: Optional[RelayResourceConfig] = None,
    relays_deployed: Optional[List[Dict[str, Any]]] = None,
    intermediate_waypoints: Optional[List[Dict[str, Any]]] = None,
    active_relay_tx_times_s: Optional[Dict[str, float]] = None,
) -> MissionResourceLedger:
    """
    Builds the unified segment-by-segment resource ledger and chronological event schedule.
    Enforces strict energy conservation and detects constraint violations.
    """
    if relay_config is None:
        relay_config = RelayResourceConfig()
    if relays_deployed is None:
        relays_deployed = []
    if intermediate_waypoints is None:
        intermediate_waypoints = []
    if active_relay_tx_times_s is None:
        active_relay_tx_times_s = {}

    rows, cols = elevation_grid.shape
    constraint_violations: List[str] = []

    # 1. Input Validation & Degenerate Checks
    if not path_rc or len(path_rc) < 2:
        return MissionResourceLedger(
            total_distance_m=0.0,
            total_duration_s=0.0,
            traverse_duration_s=0.0,
            activity_duration_s=0.0,
            total_rolling_work_j=0.0,
            total_gravitational_work_j=0.0,
            total_mechanical_work_j=0.0,
            total_mobility_energy_j=0.0,
            total_electrical_energy_j=0.0,
            total_mission_energy_j=0.0,
            total_relay_energy_j=0.0,
            peak_instantaneous_power_w=0.0,
            energy_per_km_wh=0.0,
            final_energy_remaining_j=rover_config.usable_battery_capacity_j,
            min_energy_remaining_j=rover_config.usable_battery_capacity_j,
            final_battery_soc_pct=100.0,
            min_battery_soc_pct=100.0,
            reserve_threshold_j=rover_config.reserve_threshold_j,
            reserve_margin_wh=rover_config.usable_battery_capacity_wh - rover_config.reserve_threshold_wh,
            is_reserve_violated=False,
            is_time_violated=False,
            feasibility_classification=ResourceFeasibilityClassification.INVALID_CONFIGURATION,
            constraint_violations=["Path has fewer than 2 coordinates."],
        )

    # 2. Check for NoData / invalid terrain samples along path
    for r, c in path_rc:
        if r < 0 or r >= rows or c < 0 or c >= cols or invalid_mask[r, c] or not math.isfinite(elevation_grid[r, c]):
            return MissionResourceLedger(
                total_distance_m=0.0,
                total_duration_s=0.0,
                traverse_duration_s=0.0,
                activity_duration_s=0.0,
                total_rolling_work_j=0.0,
                total_gravitational_work_j=0.0,
                total_mechanical_work_j=0.0,
                total_mobility_energy_j=0.0,
                total_electrical_energy_j=0.0,
                total_mission_energy_j=0.0,
                total_relay_energy_j=0.0,
                peak_instantaneous_power_w=0.0,
                energy_per_km_wh=0.0,
                final_energy_remaining_j=0.0,
                min_energy_remaining_j=0.0,
                final_battery_soc_pct=0.0,
                min_battery_soc_pct=0.0,
                reserve_threshold_j=rover_config.reserve_threshold_j,
                reserve_margin_wh=0.0,
                is_reserve_violated=True,
                is_time_violated=False,
                feasibility_classification=ResourceFeasibilityClassification.UNKNOWN_RESOURCE_FEASIBILITY,
                constraint_violations=[f"Path traverses NoData or out-of-bounds terrain cell at ({r}, {c})."],
            )

    # 3. Step-by-Step Traverse Integration
    segment_records: List[SegmentResourceRecord] = []
    timeline_events: List[MissionActivityEvent] = []

    cumulative_energy_consumed_j: float = 0.0
    energy_remaining_j: float = rover_config.usable_battery_capacity_j
    min_energy_remaining_j: float = energy_remaining_j

    total_dist_m: float = 0.0
    total_rolling_j: float = 0.0
    total_grav_j: float = 0.0
    total_mech_j: float = 0.0
    total_mob_j: float = 0.0
    total_elec_j: float = 0.0

    current_time_s: float = 0.0
    peak_power_w: float = 0.0
    is_reserve_violated: bool = False

    # Electrical power while moving: base + comm standby + instrument standby
    drive_elec_power_w = (
        rover_config.base_electrical_load_w
        + rover_config.comm_standby_w
        + rover_config.instrument_standby_w
    )

    for i in range(len(path_rc) - 1):
        r1, c1 = path_rc[i]
        r2, c2 = path_rc[i + 1]

        # Geometric ground distance
        dr = (r2 - r1) * ground_dy_m
        dc = (c2 - c1) * ground_dx_m
        seg_dist = math.hypot(dr, dc)
        total_dist_m += seg_dist

        # Elevation & Slope
        z1 = float(elevation_grid[r1, c1])
        z2 = float(elevation_grid[r2, c2])
        delta_h = z2 - z1
        seg_slope = float(slope_grid[r2, c2])

        # Mobility Work & Energy
        (
            rolling_w,
            grav_w,
            mech_w,
            mob_e,
            seg_dt,
        ) = calculate_segment_mobility_energy(seg_dist, delta_h, seg_slope, rover_config)

        # Electrical Load Energy
        elec_e = drive_elec_power_w * seg_dt
        seg_total_e = mob_e + elec_e

        # Peak instantaneous power during movement: mechanical electrical drive power + electrical loads
        step_drive_power_w = (mech_w / rover_config.drivetrain_efficiency) / max(seg_dt, 1e-4)
        step_total_power_w = step_drive_power_w + drive_elec_power_w
        if step_total_power_w > peak_power_w:
            peak_power_w = step_total_power_w

        # Energy conservation step
        cumulative_energy_consumed_j += seg_total_e
        energy_remaining_j -= seg_total_e
        if energy_remaining_j < min_energy_remaining_j:
            min_energy_remaining_j = energy_remaining_j

        total_rolling_j += rolling_w
        total_grav_j += grav_w
        total_mech_j += mech_w
        total_mob_j += mob_e
        total_elec_j += elec_e

        soc_pct = max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
        step_reserve_violated = energy_remaining_j < rover_config.reserve_threshold_j
        if step_reserve_violated:
            is_reserve_violated = True

        rec = SegmentResourceRecord(
            step_idx=i,
            start_rc=(r1, c1),
            end_rc=(r2, c2),
            distance_m=seg_dist,
            elevation_change_m=delta_h,
            slope_deg=seg_slope,
            duration_s=seg_dt,
            rolling_work_j=rolling_w,
            gravitational_work_j=grav_w,
            mechanical_work_j=mech_w,
            mobility_energy_j=mob_e,
            electrical_load_energy_j=elec_e,
            total_energy_consumed_j=seg_total_e,
            energy_remaining_j=energy_remaining_j,
            battery_soc_pct=soc_pct,
            is_reserve_violated=step_reserve_violated,
        )
        segment_records.append(rec)

        current_time_s += seg_dt

    traverse_duration_s = current_time_s

    # Add Traverse Phase Event
    timeline_events.append(
        MissionActivityEvent(
            event_id="EVT_TRAVERSE_NOMINAL",
            event_type="traverse_step",
            label="Surface Traverse Locomotion",
            start_time_s=0.0,
            end_time_s=traverse_duration_s,
            duration_s=traverse_duration_s,
            average_power_w=(total_mob_j + total_elec_j) / max(traverse_duration_s, 1e-4),
            energy_consumed_j=total_mob_j + total_elec_j,
            cumulative_energy_consumed_j=cumulative_energy_consumed_j,
            energy_remaining_j=energy_remaining_j,
            battery_soc_pct=max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0),
            location_rc=path_rc[-1],
            notes=f"Traversed {total_dist_m:.1f}m across {len(path_rc)} grid cells.",
        )
    )

    # 4. Activity Scheduling: Science Waypoint Dwells
    activity_duration_s: float = 0.0

    # Dwell power calculation: base + active instrument + active comms
    dwell_power_w = (
        rover_config.base_electrical_load_w
        + (rover_config.instrument_active_w * rover_config.instrument_duty_cycle)
        + (rover_config.instrument_standby_w * (1.0 - rover_config.instrument_duty_cycle))
        + rover_config.comm_active_w
    )
    if dwell_power_w > peak_power_w:
        peak_power_w = dwell_power_w

    for idx, wp in enumerate(intermediate_waypoints):
        wp_name = wp.get("name", f"Science Site {idx + 1}")
        wp_rc = wp.get("rc", path_rc[-1])
        dwell_t = rover_config.science_dwell_s
        dwell_e = dwell_power_w * dwell_t

        cumulative_energy_consumed_j += dwell_e
        energy_remaining_j -= dwell_e
        if energy_remaining_j < min_energy_remaining_j:
            min_energy_remaining_j = energy_remaining_j
        total_elec_j += dwell_e
        activity_duration_s += dwell_t

        soc_pct = max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
        if energy_remaining_j < rover_config.reserve_threshold_j:
            is_reserve_violated = True

        timeline_events.append(
            MissionActivityEvent(
                event_id=f"EVT_SCIENCE_DWELL_{idx + 1}",
                event_type="science_dwell",
                label=f"In-Situ Science Sampling: {wp_name}",
                start_time_s=current_time_s,
                end_time_s=current_time_s + dwell_t,
                duration_s=dwell_t,
                average_power_w=dwell_power_w,
                energy_consumed_j=dwell_e,
                cumulative_energy_consumed_j=cumulative_energy_consumed_j,
                energy_remaining_j=energy_remaining_j,
                battery_soc_pct=soc_pct,
                location_rc=tuple(wp_rc) if wp_rc else None,
                notes=f"Contact instruments active at {rover_config.instrument_duty_cycle * 100:.0f}% duty cycle.",
            )
        )
        current_time_s += dwell_t

    # 5. Activity Scheduling: Relay Deployment Stops
    # Actuator power while deploying relay tower: base + deployment mechanical drive
    deploy_power_w = rover_config.base_electrical_load_w + 45.0
    if deploy_power_w > peak_power_w:
        peak_power_w = deploy_power_w

    for idx, relay in enumerate(relays_deployed):
        r_id = relay.get("node_id", f"MRN-{idx + 1}")
        r_rc = relay.get("rc", path_rc[0])
        deploy_t = rover_config.relay_deployment_s
        deploy_e = deploy_power_w * deploy_t

        cumulative_energy_consumed_j += deploy_e
        energy_remaining_j -= deploy_e
        if energy_remaining_j < min_energy_remaining_j:
            min_energy_remaining_j = energy_remaining_j
        total_elec_j += deploy_e
        activity_duration_s += deploy_t

        soc_pct = max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
        if energy_remaining_j < rover_config.reserve_threshold_j:
            is_reserve_violated = True

        timeline_events.append(
            MissionActivityEvent(
                event_id=f"EVT_RELAY_DEPLOY_{r_id}",
                event_type="relay_deployment",
                label=f"Surface Relay Deployment: {r_id}",
                start_time_s=current_time_s,
                end_time_s=current_time_s + deploy_t,
                duration_s=deploy_t,
                average_power_w=deploy_power_w,
                energy_consumed_j=deploy_e,
                cumulative_energy_consumed_j=cumulative_energy_consumed_j,
                energy_remaining_j=energy_remaining_j,
                battery_soc_pct=soc_pct,
                location_rc=tuple(r_rc) if r_rc else None,
                notes="Mast anchoring, parabolic dish erection, and BITE test.",
            )
        )
        current_time_s += deploy_t

    # 6. Operational Delay (if configured)
    if rover_config.operational_delay_s > 0.0:
        delay_t = rover_config.operational_delay_s
        delay_power_w = rover_config.base_electrical_load_w + rover_config.comm_standby_w
        delay_e = delay_power_w * delay_t

        cumulative_energy_consumed_j += delay_e
        energy_remaining_j -= delay_e
        if energy_remaining_j < min_energy_remaining_j:
            min_energy_remaining_j = energy_remaining_j
        total_elec_j += delay_e
        activity_duration_s += delay_t

        soc_pct = max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
        if energy_remaining_j < rover_config.reserve_threshold_j:
            is_reserve_violated = True

        timeline_events.append(
            MissionActivityEvent(
                event_id="EVT_OPERATIONAL_DELAY",
                event_type="operational_delay",
                label="Tactical Operational Standby / Latency",
                start_time_s=current_time_s,
                end_time_s=current_time_s + delay_t,
                duration_s=delay_t,
                average_power_w=delay_power_w,
                energy_consumed_j=delay_e,
                cumulative_energy_consumed_j=cumulative_energy_consumed_j,
                energy_remaining_j=energy_remaining_j,
                battery_soc_pct=soc_pct,
                location_rc=path_rc[-1],
                notes="Configured tactical delay buffer.",
            )
        )
        current_time_s += delay_t

    total_mission_time_s = current_time_s

    # 7. Relay Network Infrastructure Energy Accounting
    total_relay_energy_j: float = 0.0
    relay_breakdown: List[Dict[str, Any]] = []

    for relay in relays_deployed:
        r_id = relay.get("node_id", "MRN_UNKNOWN")
        active_tx_t = active_relay_tx_times_s.get(r_id, total_mission_time_s * 0.15)
        # Ensure active TX does not exceed mission time
        active_tx_t = min(active_tx_t, total_mission_time_s)
        standby_t = max(0.0, total_mission_time_s - active_tx_t)

        relay_e_j = (
            (relay_config.standby_power_w * standby_t)
            + (relay_config.active_tx_power_w * active_tx_t)
        )
        total_relay_energy_j += relay_e_j

        r_rem_j = max(0.0, relay_config.usable_battery_capacity_j - relay_e_j)
        r_soc_pct = (r_rem_j / relay_config.usable_battery_capacity_j) * 100.0
        r_reserve_viol = r_rem_j < relay_config.reserve_threshold_j

        if r_reserve_viol:
            constraint_violations.append(f"Relay {r_id} battery reserve threshold violated ({joules_to_wh(r_rem_j):.1f} Wh remaining).")
        if r_rem_j <= 0.0:
            constraint_violations.append(f"Relay {r_id} battery completely exhausted.")

        relay_breakdown.append({
            "node_id": r_id,
            "standby_duration_s": round(standby_t, 1),
            "active_duration_s": round(active_tx_t, 1),
            "energy_consumed_j": round(relay_e_j, 1),
            "energy_consumed_wh": round(joules_to_wh(relay_e_j), 2),
            "energy_remaining_wh": round(joules_to_wh(r_rem_j), 2),
            "battery_soc_pct": round(r_soc_pct, 2),
            "is_reserve_violated": r_reserve_viol,
        })

    # 8. Constraint Verification & Feasibility Classification
    total_mission_energy_j = total_mob_j + total_elec_j
    is_time_violated = total_mission_time_s > rover_config.max_mission_duration_s
    if is_time_violated:
        constraint_violations.append(
            f"Mission duration ({total_mission_time_s:.0f}s / {total_mission_time_s / 3600.0:.1f}h) exceeds maximum limit ({rover_config.max_mission_duration_s:.0f}s)."
        )

    is_energy_exhausted = min_energy_remaining_j <= 0.0
    if is_energy_exhausted:
        constraint_violations.append(
            f"Rover battery depleted ({joules_to_wh(total_mission_energy_j):.1f} Wh consumed > {rover_config.usable_battery_capacity_wh:.1f} Wh capacity)."
        )
    elif is_reserve_violated:
        constraint_violations.append(
            f"Rover battery reserve threshold violated (Min SOC: {(min_energy_remaining_j / rover_config.usable_battery_capacity_j) * 100:.1f}% < {rover_config.reserve_margin_pct:.0f}%)."
        )

    # Classify feasibility
    if is_energy_exhausted and is_time_violated:
        feasibility = ResourceFeasibilityClassification.MULTIPLE_CONSTRAINT_VIOLATIONS
    elif is_energy_exhausted:
        feasibility = ResourceFeasibilityClassification.ENERGY_CONSTRAINT_VIOLATION
    elif is_time_violated:
        feasibility = ResourceFeasibilityClassification.TIME_CONSTRAINT_VIOLATION
    elif is_reserve_violated:
        feasibility = ResourceFeasibilityClassification.FEASIBLE_WITH_LOW_RESERVE
    else:
        feasibility = ResourceFeasibilityClassification.FEASIBLE_WITHIN_CONFIGURED_BUDGET

    # Energy per km
    km_travelled = total_dist_m / 1000.0
    energy_per_km_wh = joules_to_wh(total_mission_energy_j) / max(km_travelled, 1e-4)

    final_soc_pct = max(0.0, (energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
    min_soc_pct = max(0.0, (min_energy_remaining_j / rover_config.usable_battery_capacity_j) * 100.0)
    reserve_margin_wh = joules_to_wh(min_energy_remaining_j - rover_config.reserve_threshold_j)

    return MissionResourceLedger(
        total_distance_m=total_dist_m,
        total_duration_s=total_mission_time_s,
        traverse_duration_s=traverse_duration_s,
        activity_duration_s=activity_duration_s,
        total_rolling_work_j=total_rolling_j,
        total_gravitational_work_j=total_grav_j,
        total_mechanical_work_j=total_mech_j,
        total_mobility_energy_j=total_mob_j,
        total_electrical_energy_j=total_elec_j,
        total_mission_energy_j=total_mission_energy_j,
        total_relay_energy_j=total_relay_energy_j,
        peak_instantaneous_power_w=peak_power_w,
        energy_per_km_wh=energy_per_km_wh,
        final_energy_remaining_j=energy_remaining_j,
        min_energy_remaining_j=min_energy_remaining_j,
        final_battery_soc_pct=final_soc_pct,
        min_battery_soc_pct=min_soc_pct,
        reserve_threshold_j=rover_config.reserve_threshold_j,
        reserve_margin_wh=reserve_margin_wh,
        is_reserve_violated=is_reserve_violated,
        is_time_violated=is_time_violated,
        feasibility_classification=feasibility,
        constraint_violations=constraint_violations,
        segment_records=segment_records,
        timeline_events=timeline_events,
        relay_breakdown=relay_breakdown,
    )


def evaluate_resource_sensitivity(
    path_rc: List[Tuple[int, int]],
    elevation_grid: np.ndarray,
    slope_grid: np.ndarray,
    invalid_mask: np.ndarray,
    ground_dx_m: float,
    ground_dy_m: float,
    base_rover_config: Optional[RoverResourceConfig] = None,
    base_relay_config: Optional[RelayResourceConfig] = None,
    relays_deployed: Optional[List[Dict[str, Any]]] = None,
    intermediate_waypoints: Optional[List[Dict[str, Any]]] = None,
    rover_config: Optional[RoverResourceConfig] = None,
    relay_config: Optional[RelayResourceConfig] = None,
    sweep_factors: Optional[Dict[str, List[float]]] = None,
) -> ResourceSensitivityResult:
    """
    Executes a deterministic, bounded sensitivity sweep across critical engineering parameters.
    Measures parameter dominance, min/max consumption range, and constraint boundary crossings.
    """
    if base_rover_config is None:
        base_rover_config = rover_config if rover_config is not None else RoverResourceConfig()
    if base_relay_config is None:
        base_relay_config = relay_config if relay_config is not None else RelayResourceConfig()

    # 1. Baseline Evaluation
    base_ledger = evaluate_mission_resource_ledger(
        path_rc=path_rc,
        elevation_grid=elevation_grid,
        slope_grid=slope_grid,
        invalid_mask=invalid_mask,
        ground_dx_m=ground_dx_m,
        ground_dy_m=ground_dy_m,
        rover_config=base_rover_config,
        relay_config=base_relay_config,
        relays_deployed=relays_deployed,
        intermediate_waypoints=intermediate_waypoints,
    )
    base_e_j = base_ledger.total_mission_energy_j
    base_e_wh = base_ledger.total_mission_energy_wh
    base_margin_wh = base_ledger.reserve_margin_wh

    # 2. Perturbation Definition (Param name, relative deltas)
    # Bounded parameter variations
    variations = {
        "rover_mass": ("rover_mass_kg", [-0.15, +0.15]),
        "rolling_resistance": ("rolling_resistance_crr", [-0.25, +0.25]),
        "drivetrain_efficiency": ("drivetrain_efficiency", [-0.15, +0.15]),
        "drive_speed": ("nominal_drive_speed_mps", [-0.20, +0.20]),
        "base_electrical_load": ("base_electrical_load_w", [-0.20, +0.20]),
        "battery_capacity": ("usable_battery_capacity_wh", [-0.20, +0.20]),
    }

    sweeps: Dict[str, Dict[str, Any]] = {}
    sensitivity_rankings: List[Dict[str, Any]] = []
    min_consumed_wh = base_e_wh
    max_consumed_wh = base_e_wh
    min_remaining_wh = base_ledger.min_energy_remaining_wh
    max_remaining_wh = base_ledger.min_energy_remaining_wh
    constraint_crossings: List[str] = []

    for param_label, (attr_name, deltas) in variations.items():
        base_val = getattr(base_rover_config, attr_name)
        param_sweep_cases = []
        max_delta_e_pct = 0.0

        for delta in deltas:
            perturbed_val = base_val * (1.0 + delta)
            # Boundary protections
            if attr_name == "drivetrain_efficiency":
                perturbed_val = min(0.95, max(0.40, perturbed_val))
            elif attr_name == "nominal_drive_speed_mps":
                perturbed_val = max(0.05, perturbed_val)

            # Create perturbed config
            perturbed_kwargs = {attr_name: perturbed_val}
            test_config = RoverResourceConfig(
                rover_mass_kg=perturbed_kwargs.get("rover_mass_kg", base_rover_config.rover_mass_kg),
                payload_mass_kg=base_rover_config.payload_mass_kg,
                usable_battery_capacity_wh=perturbed_kwargs.get("usable_battery_capacity_wh", base_rover_config.usable_battery_capacity_wh),
                reserve_margin_pct=base_rover_config.reserve_margin_pct,
                rolling_resistance_crr=perturbed_kwargs.get("rolling_resistance_crr", base_rover_config.rolling_resistance_crr),
                drivetrain_efficiency=perturbed_kwargs.get("drivetrain_efficiency", base_rover_config.drivetrain_efficiency),
                nominal_drive_speed_mps=perturbed_kwargs.get("nominal_drive_speed_mps", base_rover_config.nominal_drive_speed_mps),
                base_electrical_load_w=perturbed_kwargs.get("base_electrical_load_w", base_rover_config.base_electrical_load_w),
                instrument_standby_w=base_rover_config.instrument_standby_w,
                instrument_active_w=base_rover_config.instrument_active_w,
                instrument_duty_cycle=base_rover_config.instrument_duty_cycle,
                comm_standby_w=base_rover_config.comm_standby_w,
                comm_active_w=base_rover_config.comm_active_w,
                science_dwell_s=base_rover_config.science_dwell_s,
                relay_deployment_s=base_rover_config.relay_deployment_s,
                operational_delay_s=base_rover_config.operational_delay_s,
                max_mission_duration_s=base_rover_config.max_mission_duration_s,
                allow_regenerative_braking=base_rover_config.allow_regenerative_braking,
            )

            p_ledger = evaluate_mission_resource_ledger(
                path_rc=path_rc,
                elevation_grid=elevation_grid,
                slope_grid=slope_grid,
                invalid_mask=invalid_mask,
                ground_dx_m=ground_dx_m,
                ground_dy_m=ground_dy_m,
                rover_config=test_config,
                relay_config=base_relay_config,
                relays_deployed=relays_deployed,
                intermediate_waypoints=intermediate_waypoints,
            )

            p_e_wh = p_ledger.total_mission_energy_wh
            p_rem_wh = p_ledger.min_energy_remaining_wh

            if p_e_wh < min_consumed_wh:
                min_consumed_wh = p_e_wh
            if p_e_wh > max_consumed_wh:
                max_consumed_wh = p_e_wh
            if p_rem_wh < min_remaining_wh:
                min_remaining_wh = p_rem_wh
            if p_rem_wh > max_remaining_wh:
                max_remaining_wh = p_rem_wh

            delta_e_pct = ((p_e_wh - base_e_wh) / max(base_e_wh, 1e-4)) * 100.0
            if abs(delta_e_pct) > max_delta_e_pct:
                max_delta_e_pct = abs(delta_e_pct)

            if p_ledger.is_reserve_violated and not base_ledger.is_reserve_violated:
                crossing = f"{param_label} ({delta:+0.0%}): triggers reserve margin violation."
                if crossing not in constraint_crossings:
                    constraint_crossings.append(crossing)
            if p_ledger.feasibility_classification == ResourceFeasibilityClassification.ENERGY_CONSTRAINT_VIOLATION:
                crossing = f"{param_label} ({delta:+0.0%}): triggers complete battery depletion."
                if crossing not in constraint_crossings:
                    constraint_crossings.append(crossing)

            param_sweep_cases.append({
                "perturbation_pct": round(delta * 100.0, 1),
                "parameter_value": round(perturbed_val, 4),
                "energy_consumed_wh": round(p_e_wh, 2),
                "energy_delta_wh": round(p_e_wh - base_e_wh, 2),
                "energy_delta_pct": round(delta_e_pct, 2),
                "remaining_energy_wh": round(p_rem_wh, 2),
                "feasibility": p_ledger.feasibility_classification.value,
            })

        # Calculate normalized sensitivity index (Elasticity: % change in energy / % change in parameter)
        elasticity = max_delta_e_pct / (max(abs(deltas[0]), abs(deltas[1])) * 100.0)

        sweeps[param_label] = {
            "parameter_name": attr_name,
            "baseline_value": round(base_val, 4),
            "max_impact_pct": round(max_delta_e_pct, 2),
            "elasticity": round(elasticity, 3),
            "cases": param_sweep_cases,
        }

        sensitivity_rankings.append({
            "parameter": param_label,
            "elasticity": round(elasticity, 3),
            "max_impact_pct": round(max_delta_e_pct, 2),
        })

    # Sort rankings descending by elasticity
    sensitivity_rankings.sort(key=lambda x: x["elasticity"], reverse=True)

    return ResourceSensitivityResult(
        baseline_energy_j=base_e_j,
        baseline_energy_wh=base_e_wh,
        baseline_margin_wh=base_margin_wh,
        parameter_sweeps=sweeps,
        sensitivity_ranking=sensitivity_rankings,
        consumption_range_wh=(min_consumed_wh, max_consumed_wh),
        remaining_energy_range_wh=(min_remaining_wh, max_remaining_wh),
        constraint_crossing_parameters=constraint_crossings,
        provenance_statement=(
            "These results represent sensitivity to configured engineering assumptions. "
            "They are deterministic scenario evaluations and are not validated predictions of actual Mars rover performance."
        ),
    )
