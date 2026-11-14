"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Unified Mission State Container.

Maintains a 4-tier state representation:
  1. Physical Simulation State (ground truth on Mars)
  2. Earth-Reported State (delayed, packet-buffered telemetry at Earth MCC)
  3. Predicted State (lookahead forecast of power, consumables, and science yield)
  4. Planned State (target schedule and active task allocations)

Provides cryptographic state hashing (SHA-256), state diffing, and monotonic versioning.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .atlas_mission_contracts import StateSnapshot


@dataclass
class PhysicalSimulationState:
    sol: int = 1
    sol_time: str = "06:00:00"
    met_seconds: float = 0.0
    solar_longitude_ls: float = 56.4
    atmospheric_dust_tau: float = 0.45
    surface_temp_k: float = 210.0
    direct_solar_flux_w_m2: float = 480.0
    reactor_power_gross_kwe: float = 120.0
    total_power_demand_kwe: float = 78.5
    battery_bank_soc_pct: float = 94.2
    habitat_core_pressure_kpa: float = 101.3
    habitat_core_temp_k: float = 294.15
    water_storage_kg: float = 3450.0
    oxygen_storage_kg: float = 1250.0
    nitrogen_storage_kg: float = 850.0
    methane_fuel_kg: float = 420.0
    sintered_regolith_blocks: int = 120
    asset_positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    asset_battery_pcts: Dict[str, float] = field(default_factory=dict)
    structural_integrity_pct: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhysicalSimulationState:
        return cls(**data)


@dataclass
class EarthReportedState:
    last_received_sol: int = 1
    last_received_sol_time: str = "05:45:00"
    reception_met_seconds: float = 0.0
    owlt_applied_seconds: float = 852.0
    telemetry_latency_seconds: float = 900.0
    state_signature_hash: str = ""
    reported_positions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    reported_battery_pcts: Dict[str, float] = field(default_factory=dict)
    reported_water_kg: float = 3450.0
    reported_oxygen_kg: float = 1250.0
    reported_power_kwe: float = 120.0
    unacknowledged_uplinks_count: int = 0
    link_status_summary: str = "DIRECT_LOS_ACQUIRED"

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EarthReportedState:
        return cls(**data)


@dataclass
class PredictedState:
    forecast_horizon_sols: int = 10
    predicted_battery_min_pct: float = 82.5
    predicted_water_depletion_sol: float = 345.0
    predicted_oxygen_depletion_sol: float = 412.0
    projected_science_entropy_bits: float = 0.25
    power_margin_kw: float = 41.5
    resilience_margin_index: float = 0.92

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PredictedState:
        return cls(**data)


@dataclass
class PlannedState:
    active_phase_id: str = "PHASE_A_RECONNAISSANCE"
    active_task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    pending_milestones_count: int = 7
    schedule_variance_sols: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlannedState:
        return cls(**data)


class UnifiedMissionStateManager:
    """Manages the lifecycle, synchronization, diffing, and hashing of multi-tiered mission state."""

    def __init__(self, initial_sol: int = 1) -> None:
        self.physical = PhysicalSimulationState(sol=initial_sol)
        self.earth_reported = EarthReportedState(last_received_sol=initial_sol)
        self.predicted = PredictedState()
        self.planned = PlannedState()
        self.step_index: int = 0
        self.history: List[StateSnapshot] = []
        self._current_hash: str = self.compute_state_hash()

    def compute_state_hash(self) -> str:
        """Compute SHA-256 state signature over canonical physical & operational parameters."""
        state_repr = {
            "sol": self.physical.sol,
            "met_seconds": round(self.physical.met_seconds, 2),
            "dust_tau": round(self.physical.atmospheric_dust_tau, 4),
            "temp_k": round(self.physical.surface_temp_k, 2),
            "reactor_kwe": round(self.physical.reactor_power_gross_kwe, 2),
            "water_kg": round(self.physical.water_storage_kg, 2),
            "oxygen_kg": round(self.physical.oxygen_storage_kg, 2),
            "sintered_blocks": self.physical.sintered_regolith_blocks,
            "active_phase": self.planned.active_phase_id,
            "active_tasks": sorted(self.planned.active_task_ids),
        }
        raw_json = json.dumps(state_repr, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    @property
    def current_hash(self) -> str:
        return self._current_hash

    def capture_snapshot(self, active_assets_count: int = 4, health_status: str = "NOMINAL") -> StateSnapshot:
        """Capture an immutable state snapshot and append to history."""
        prev_hash = self.history[-1].state_hash if self.history else "0" * 64
        curr_hash = self.compute_state_hash()
        self._current_hash = curr_hash

        snapshot = StateSnapshot(
            step_index=self.step_index,
            met_seconds=self.physical.met_seconds,
            current_sol=self.physical.sol,
            sol_time_str=self.physical.sol_time,
            solar_longitude_ls=self.physical.solar_longitude_ls,
            state_hash=curr_hash,
            prev_state_hash=prev_hash,
            active_phase_id=self.planned.active_phase_id,
            active_assets_count=active_assets_count,
            health_status=health_status,
        )
        self.history.append(snapshot)
        self.step_index += 1
        return snapshot

    def compute_telemetry_drift(self) -> Dict[str, Any]:
        """Compute observable delta between ground truth on Mars and Earth-reported state."""
        power_drift = abs(self.physical.reactor_power_gross_kwe - self.earth_reported.reported_power_kwe)
        water_drift = abs(self.physical.water_storage_kg - self.earth_reported.reported_water_kg)
        oxygen_drift = abs(self.physical.oxygen_storage_kg - self.earth_reported.reported_oxygen_kg)

        position_drifts: Dict[str, float] = {}
        for asset_id, phys_pos in self.physical.asset_positions.items():
            if asset_id in self.earth_reported.reported_positions:
                earth_pos = self.earth_reported.reported_positions[asset_id]
                dlat = (phys_pos["lat"] - earth_pos["lat"]) * 111319.5
                dlon = (phys_pos["lon"] - earth_pos["lon"]) * 111319.5
                dist_m = (dlat ** 2 + dlon ** 2) ** 0.5
                position_drifts[asset_id] = round(dist_m, 2)

        has_pos_drift = any(d > 0.0 for d in position_drifts.values())
        return {
            "power_drift_kwe": round(power_drift, 3),
            "water_drift_kg": round(water_drift, 3),
            "oxygen_drift_kg": round(oxygen_drift, 3),
            "position_drifts_m": position_drifts,
            "owlt_seconds": self.earth_reported.owlt_applied_seconds,
            "is_synchronized": (power_drift == 0.0 and water_drift == 0.0 and oxygen_drift == 0.0 and not has_pos_drift),
        }

    def sync_earth_reported(self, owlt_seconds: float = 852.0) -> None:
        """Propagate current physical telemetry into Earth-reported state with simulated delay timestamp."""
        self.earth_reported.last_received_sol = self.physical.sol
        self.earth_reported.last_received_sol_time = self.physical.sol_time
        self.earth_reported.reception_met_seconds = self.physical.met_seconds + owlt_seconds
        self.earth_reported.owlt_applied_seconds = owlt_seconds
        self.earth_reported.telemetry_latency_seconds = owlt_seconds
        self.earth_reported.state_signature_hash = self.current_hash
        self.earth_reported.reported_power_kwe = self.physical.reactor_power_gross_kwe
        self.earth_reported.reported_water_kg = self.physical.water_storage_kg
        self.earth_reported.reported_oxygen_kg = self.physical.oxygen_storage_kg
        self.earth_reported.reported_positions = copy.deepcopy(self.physical.asset_positions)
        self.earth_reported.reported_battery_pcts = copy.deepcopy(self.physical.asset_battery_pcts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "current_hash": self.current_hash,
            "physical": self.physical.to_dict(),
            "earth_reported": self.earth_reported.to_dict(),
            "predicted": self.predicted.to_dict(),
            "planned": self.planned.to_dict(),
            "history_count": len(self.history),
        }
