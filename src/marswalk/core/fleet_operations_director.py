"""
MarsWalk 2.0 / Project Atlas - Milestone 13J: Fleet Operations Director.

Coordinates multi-rover planetary exploration fleets across the Jezero crater:
manages fleet configuration, rover registration, independent physical resource ledgers
(zero energy pooling, individual flash buffers), fleet simulation clock, and persistent snapshots.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Physical constants
MARS_GRAVITY_MPS2: float = 3.71
JOULES_PER_WH: float = 3600.0
WH_PER_JOULE: float = 1.0 / 3600.0


class FleetStatus(str, Enum):
    """Operational state of the multi-rover fleet."""
    AVAILABLE = "AVAILABLE"
    PLANNED = "PLANNED"
    EXECUTING_SIMULATION = "EXECUTING_SIMULATION"
    PAUSED = "PAUSED"
    RETURNING = "RETURNING"
    RESOURCE_CONSTRAINED = "RESOURCE_CONSTRAINED"
    UNAVAILABLE = "UNAVAILABLE"
    REQUIRES_REPLANNING = "REQUIRES_REPLANNING"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


class RoverConnectivityStatus(str, Enum):
    """Real-time geometric communication status of a rover node."""
    CONNECTED_DIRECT = "CONNECTED_DIRECT"
    CONNECTED_RELAY = "CONNECTED_RELAY"
    CONNECTED_MULTI_HOP = "CONNECTED_MULTI_HOP"
    BLACKOUT = "BLACKOUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class RoverUnitConfig:
    """
    Physical engineering specification and payload configuration of an exploration rover.
    Each rover operates on its own dedicated physical ledger.
    """
    rover_id: str
    name: str
    unit_type: str = "robotic_rover"
    starting_location_rc: Tuple[int, int] = (128, 128)
    antenna_height_m: float = 2.0
    usable_battery_capacity_wh: float = 4800.0
    reserve_margin_pct: float = 20.0
    nominal_speed_mps: float = 0.10
    storage_capacity_mb: float = 65536.0  # 64 GB
    instrument_ids: List[str] = field(default_factory=lambda: [
        "MASTCAM_Z", "SUPERCAM", "MEDA"
    ])
    can_act_as_mobile_relay: bool = False
    color_hex: str = "#38bdf8"  # Cyan default
    rover_mass_kg: float = 1025.0
    base_electrical_load_w: float = 110.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "name": self.name,
            "unit_type": self.unit_type,
            "starting_location_rc": list(self.starting_location_rc),
            "antenna_height_m": self.antenna_height_m,
            "usable_battery_capacity_wh": self.usable_battery_capacity_wh,
            "reserve_margin_pct": self.reserve_margin_pct,
            "nominal_speed_mps": self.nominal_speed_mps,
            "storage_capacity_mb": self.storage_capacity_mb,
            "instrument_ids": list(self.instrument_ids),
            "can_act_as_mobile_relay": self.can_act_as_mobile_relay,
            "color_hex": self.color_hex,
            "rover_mass_kg": self.rover_mass_kg,
            "base_electrical_load_w": self.base_electrical_load_w,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoverUnitConfig":
        return cls(
            rover_id=str(data["rover_id"]),
            name=str(data.get("name", data["rover_id"])),
            unit_type=str(data.get("unit_type", "robotic_rover")),
            starting_location_rc=tuple(data.get("starting_location_rc", (128, 128))),
            antenna_height_m=float(data.get("antenna_height_m", 2.0)),
            usable_battery_capacity_wh=float(data.get("usable_battery_capacity_wh", 4800.0)),
            reserve_margin_pct=float(data.get("reserve_margin_pct", 20.0)),
            nominal_speed_mps=float(data.get("nominal_speed_mps", 0.10)),
            storage_capacity_mb=float(data.get("storage_capacity_mb", 65536.0)),
            instrument_ids=list(data.get("instrument_ids", ["MASTCAM_Z", "SUPERCAM", "MEDA"])),
            can_act_as_mobile_relay=bool(data.get("can_act_as_mobile_relay", False)),
            color_hex=str(data.get("color_hex", "#38bdf8")),
            rover_mass_kg=float(data.get("rover_mass_kg", 1025.0)),
            base_electrical_load_w=float(data.get("base_electrical_load_w", 110.0)),
        )


@dataclass
class RoverOperationalState:
    """
    Live telemetry and resource register state for an individual rover unit.
    STRICT PRINCIPLE: No pooling of energy or memory between rover instances.
    """
    rover_id: str
    status: str = FleetStatus.AVAILABLE.value
    current_location_rc: Tuple[int, int] = (128, 128)
    current_heading_deg: float = 0.0
    current_sol: int = 1
    met_seconds: float = 0.0
    battery_soc_pct: float = 100.0
    current_energy_wh: float = 4800.0
    consumed_energy_wh: float = 0.0
    used_storage_mb: float = 0.0
    data_backlog_mb: float = 0.0
    data_products_count: int = 0
    active_activity_id: Optional[str] = None
    assigned_target_ids: List[str] = field(default_factory=list)
    completed_target_ids: List[str] = field(default_factory=list)
    connectivity_status: str = RoverConnectivityStatus.CONNECTED_DIRECT.value
    current_path_index: int = 0
    active_route_id: Optional[str] = None
    accumulated_distance_m: float = 0.0
    accumulated_science_utility: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "status": self.status,
            "current_location_rc": list(self.current_location_rc),
            "current_heading_deg": round(self.current_heading_deg, 1),
            "current_sol": self.current_sol,
            "met_seconds": round(self.met_seconds, 1),
            "battery_soc_pct": round(self.battery_soc_pct, 2),
            "current_energy_wh": round(self.current_energy_wh, 2),
            "consumed_energy_wh": round(self.consumed_energy_wh, 2),
            "used_storage_mb": round(self.used_storage_mb, 2),
            "data_backlog_mb": round(self.data_backlog_mb, 2),
            "data_products_count": self.data_products_count,
            "active_activity_id": self.active_activity_id,
            "assigned_target_ids": list(self.assigned_target_ids),
            "completed_target_ids": list(self.completed_target_ids),
            "connectivity_status": self.connectivity_status,
            "current_path_index": self.current_path_index,
            "active_route_id": self.active_route_id,
            "accumulated_distance_m": round(self.accumulated_distance_m, 2),
            "accumulated_science_utility": round(self.accumulated_science_utility, 1),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoverOperationalState":
        return cls(
            rover_id=str(data["rover_id"]),
            status=str(data.get("status", FleetStatus.AVAILABLE.value)),
            current_location_rc=tuple(data.get("current_location_rc", (128, 128))),
            current_heading_deg=float(data.get("current_heading_deg", 0.0)),
            current_sol=int(data.get("current_sol", 1)),
            met_seconds=float(data.get("met_seconds", 0.0)),
            battery_soc_pct=float(data.get("battery_soc_pct", 100.0)),
            current_energy_wh=float(data.get("current_energy_wh", 4800.0)),
            consumed_energy_wh=float(data.get("consumed_energy_wh", 0.0)),
            used_storage_mb=float(data.get("used_storage_mb", 0.0)),
            data_backlog_mb=float(data.get("data_backlog_mb", 0.0)),
            data_products_count=int(data.get("data_products_count", 0)),
            active_activity_id=data.get("active_activity_id"),
            assigned_target_ids=list(data.get("assigned_target_ids", [])),
            completed_target_ids=list(data.get("completed_target_ids", [])),
            connectivity_status=str(data.get("connectivity_status", RoverConnectivityStatus.CONNECTED_DIRECT.value)),
            current_path_index=int(data.get("current_path_index", 0)),
            active_route_id=data.get("active_route_id"),
            accumulated_distance_m=float(data.get("accumulated_distance_m", 0.0)),
            accumulated_science_utility=float(data.get("accumulated_science_utility", 0.0)),
        )


def create_default_fleet_rovers() -> List[RoverUnitConfig]:
    """
    Standard default 4-rover fleet configuration for Jezero Western Delta:
    - Rover A (Cyan): Primary Science Lead (Remote & Contact spectrometers)
    - Rover B (Emerald): Surveyor & Subsurface Radar (High mobility & RIMFAX)
    - Rover C (Purple): Coring & Sample Caching Scout (High torque & arm turret)
    - Rover D (Amber): Communications & Environmental Sentinel (High mast & MEDA)
    """
    return [
        RoverUnitConfig(
            rover_id="ATLAS_ROVER_A",
            name="Rover Alpha (Science Lead)",
            unit_type="robotic_rover",
            starting_location_rc=(128, 128),
            antenna_height_m=2.2,
            usable_battery_capacity_wh=5000.0,
            reserve_margin_pct=20.0,
            nominal_speed_mps=0.10,
            storage_capacity_mb=65536.0,
            instrument_ids=["MASTCAM_Z", "SUPERCAM", "PIXL", "MEDA"],
            can_act_as_mobile_relay=False,
            color_hex="#38bdf8",  # Sky Cyan
        ),
        RoverUnitConfig(
            rover_id="ATLAS_ROVER_B",
            name="Rover Beta (Geophysical Surveyor)",
            unit_type="robotic_rover",
            starting_location_rc=(128, 128),
            antenna_height_m=2.0,
            usable_battery_capacity_wh=4800.0,
            reserve_margin_pct=20.0,
            nominal_speed_mps=0.12,
            storage_capacity_mb=65536.0,
            instrument_ids=["MASTCAM_Z", "RIMFAX", "MEDA"],
            can_act_as_mobile_relay=False,
            color_hex="#10b981",  # Emerald Green
        ),
        RoverUnitConfig(
            rover_id="ATLAS_ROVER_C",
            name="Rover Gamma (Coring Specialist)",
            unit_type="robotic_rover",
            starting_location_rc=(128, 128),
            antenna_height_m=2.0,
            usable_battery_capacity_wh=5200.0,
            reserve_margin_pct=20.0,
            nominal_speed_mps=0.08,
            storage_capacity_mb=65536.0,
            instrument_ids=["SHERLOC", "CORING_TOOL", "MASTCAM_Z"],
            can_act_as_mobile_relay=False,
            color_hex="#a855f7",  # Purple
        ),
        RoverUnitConfig(
            rover_id="ATLAS_ROVER_D",
            name="Rover Delta (Relay & Environmental Sentinel)",
            unit_type="scout_rover",
            starting_location_rc=(128, 128),
            antenna_height_m=3.5,  # Extended mast
            usable_battery_capacity_wh=4400.0,
            reserve_margin_pct=25.0,
            nominal_speed_mps=0.14,
            storage_capacity_mb=32768.0,
            instrument_ids=["MASTCAM_Z", "MEDA"],
            can_act_as_mobile_relay=True,  # Mobile Relay enabled
            color_hex="#f59e0b",  # Amber
        ),
    ]


class FleetOperationsDirector:
    """
    Central orchestration engine for cooperative multi-rover planetary missions.
    Coordinates independent rover states, science task allocation, terrain routing,
    shared relay network connectivity, and fleet-scale recovery operations.
    """

    def __init__(
        self,
        fleet_id: str = "fleet_jezero_alpha",
        name: str = "Jezero Western Delta Multi-Rover Fleet",
        campaign_id: str = "cmp_jezero_delta_5sol",
        base_station_rc: Tuple[int, int] = (128, 128),
        base_station_antenna_m: float = 5.0,
        workspace_dir: Optional[Union[str, Path]] = None,
    ):
        self.fleet_id = fleet_id
        self.name = name
        self.campaign_id = campaign_id
        self.base_station_rc = base_station_rc
        self.base_station_antenna_m = base_station_antenna_m
        self.workspace_dir = Path(workspace_dir) if workspace_dir else Path(f"data/workspaces/fleets/{fleet_id}")
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        self.version = 1
        self.fleet_status = FleetStatus.AVAILABLE.value
        self.simulated_met_s: float = 0.0
        self.current_sol: int = 1
        self.max_sols: int = 5

        self.rovers: Dict[str, RoverUnitConfig] = {}
        self.rover_states: Dict[str, RoverOperationalState] = {}
        self.shared_relay_ids: List[str] = ["relay_octavia_mast", "relay_delta_crest"]
        self.science_target_ids: List[str] = []
        self.events_log: List[Dict[str, Any]] = []

        # Initialize with standard default rovers
        for r_cfg in create_default_fleet_rovers()[:2]:  # Default 2-rover active baseline
            self.register_rover(r_cfg)

    def register_rover(self, config: RoverUnitConfig) -> RoverOperationalState:
        """Register a new exploration rover with an independent resource ledger."""
        self.rovers[config.rover_id] = config
        state = RoverOperationalState(
            rover_id=config.rover_id,
            status=FleetStatus.AVAILABLE.value,
            current_location_rc=config.starting_location_rc,
            current_sol=self.current_sol,
            met_seconds=self.simulated_met_s,
            battery_soc_pct=100.0,
            current_energy_wh=config.usable_battery_capacity_wh,
            consumed_energy_wh=0.0,
            used_storage_mb=0.0,
            data_backlog_mb=0.0,
        )
        self.rover_states[config.rover_id] = state
        self.record_fleet_event(
            event_type="ROVER_REGISTERED",
            rover_id=config.rover_id,
            payload={"config": config.to_dict()}
        )
        return state

    def unregister_rover(self, rover_id: str):
        """Unregister or retire a rover from active fleet participation."""
        if rover_id in self.rovers:
            self.rovers.pop(rover_id)
            self.rover_states.pop(rover_id, None)
            self.record_fleet_event(
                event_type="ROVER_UNREGISTERED",
                rover_id=rover_id,
                payload={"rover_id": rover_id}
            )

    def set_rover_status(self, rover_id: str, status: Union[str, FleetStatus]):
        """Update rover status (e.g. UNAVAILABLE upon hardware anomaly)."""
        stat_val = status.value if isinstance(status, FleetStatus) else str(status)
        if rover_id in self.rover_states:
            self.rover_states[rover_id].status = stat_val
            self.record_fleet_event(
                event_type="ROVER_STATUS_CHANGED",
                rover_id=rover_id,
                payload={"status": stat_val}
            )
            if stat_val in (FleetStatus.UNAVAILABLE.value, FleetStatus.RESOURCE_CONSTRAINED.value):
                self.fleet_status = FleetStatus.REQUIRES_REPLANNING.value

    def get_rover_state(self, rover_id: str) -> Optional[RoverOperationalState]:
        return self.rover_states.get(rover_id)

    def record_fleet_event(
        self,
        event_type: str,
        rover_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """Record an immutable, chronologically sequenced fleet event."""
        seq = len(self.events_log) + 1
        event = {
            "sequence_number": seq,
            "event_id": f"fevt_{self.fleet_id}_{seq:05d}",
            "event_type": event_type,
            "rover_id": rover_id,
            "sol_index": self.current_sol,
            "met_seconds": round(timestamp if timestamp is not None else self.simulated_met_s, 2),
            "payload": payload or {},
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self.events_log.append(event)
        return event

    def compute_state_fingerprint(self) -> str:
        """Deterministic SHA-256 digest of aggregated fleet configuration and state."""
        digest_dict = {
            "fleet_id": self.fleet_id,
            "version": self.version,
            "fleet_status": self.fleet_status,
            "current_sol": self.current_sol,
            "met_seconds": round(self.simulated_met_s, 2),
            "rovers": {
                r_id: {
                    "status": s.status,
                    "loc": list(s.current_location_rc),
                    "soc": round(s.battery_soc_pct, 2),
                    "energy_wh": round(s.current_energy_wh, 2),
                    "storage_mb": round(s.used_storage_mb, 2),
                    "completed": sorted(list(s.completed_target_ids)),
                }
                for r_id, s in sorted(self.rover_states.items())
            },
            "events_count": len(self.events_log)
        }
        raw_bytes = json.dumps(digest_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def get_fleet_kpis(self) -> Dict[str, Any]:
        """Consolidate fleet metrics without merging or pooling independent records."""
        total_dist = sum(s.accumulated_distance_m for s in self.rover_states.values())
        total_energy_consumed = sum(s.consumed_energy_wh for s in self.rover_states.values())
        min_soc = min((s.battery_soc_pct for s in self.rover_states.values()), default=100.0)
        total_sci = sum(s.accumulated_science_utility for s in self.rover_states.values())
        total_completed = len({t for s in self.rover_states.values() for t in s.completed_target_ids})
        total_storage_used = sum(s.used_storage_mb for s in self.rover_states.values())
        total_backlog = sum(s.data_backlog_mb for s in self.rover_states.values())
        active_rovers = sum(1 for s in self.rover_states.values() if s.status == FleetStatus.AVAILABLE.value)

        # Average connectivity
        conn_count = sum(1 for s in self.rover_states.values() if s.connectivity_status in (
            RoverConnectivityStatus.CONNECTED_DIRECT.value,
            RoverConnectivityStatus.CONNECTED_RELAY.value,
            RoverConnectivityStatus.CONNECTED_MULTI_HOP.value,
        ))
        conn_pct = (conn_count / max(1, len(self.rover_states))) * 100.0

        return {
            "active_rovers": active_rovers,
            "total_rovers": len(self.rover_states),
            "total_distance_m": round(total_dist, 2),
            "total_distance_km": round(total_dist / 1000.0, 3),
            "total_energy_consumed_wh": round(total_energy_consumed, 2),
            "min_rover_soc_pct": round(min_soc, 2),
            "total_science_utility": round(total_sci, 1),
            "targets_completed": total_completed,
            "total_storage_used_mb": round(total_storage_used, 2),
            "total_data_backlog_mb": round(total_backlog, 2),
            "fleet_connectivity_pct": round(conn_pct, 1),
            "active_relays_count": len(self.shared_relay_ids),
            "current_sol": self.current_sol,
            "simulated_met_s": round(self.simulated_met_s, 1),
            "fleet_status": self.fleet_status,
        }

    def get_fleet_state(self) -> Dict[str, Any]:
        """Full serializable snapshot of the fleet operations system."""
        return {
            "fleet_id": self.fleet_id,
            "name": self.name,
            "campaign_id": self.campaign_id,
            "version": self.version,
            "fleet_status": self.fleet_status,
            "base_station": {
                "rc": list(self.base_station_rc),
                "antenna_height_m": self.base_station_antenna_m
            },
            "kpis": self.get_fleet_kpis(),
            "rovers": {r_id: cfg.to_dict() for r_id, cfg in self.rovers.items()},
            "rover_states": {r_id: s.to_dict() for r_id, s in self.rover_states.items()},
            "shared_relay_ids": list(self.shared_relay_ids),
            "science_target_ids": list(self.science_target_ids),
            "fingerprint": self.compute_state_fingerprint(),
            "events_count": len(self.events_log),
        }

    def save_snapshot(self, path: Optional[Union[str, Path]] = None) -> Path:
        """Persist versioned fleet snapshot JSON to workspace."""
        out_path = Path(path) if path else (self.workspace_dir / f"fleet_state_v{self.version}.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.get_fleet_state()
        data["events_log"] = self.events_log
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return out_path

    @classmethod
    def load_snapshot(cls, path: Union[str, Path]) -> "FleetOperationsDirector":
        """Load fleet snapshot from disk."""
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        director = cls(
            fleet_id=data["fleet_id"],
            name=data["name"],
            campaign_id=data["campaign_id"],
            base_station_rc=tuple(data["base_station"]["rc"]),
            base_station_antenna_m=float(data["base_station"]["antenna_height_m"]),
            workspace_dir=p.parent,
        )
        director.version = int(data.get("version", 1))
        director.fleet_status = str(data.get("fleet_status", FleetStatus.AVAILABLE.value))
        director.shared_relay_ids = list(data.get("shared_relay_ids", []))
        director.science_target_ids = list(data.get("science_target_ids", []))
        director.events_log = list(data.get("events_log", []))

        # Clear default rovers and restore from snapshot
        director.rovers.clear()
        director.rover_states.clear()
        for r_id, r_data in data.get("rovers", {}).items():
            director.rovers[r_id] = RoverUnitConfig.from_dict(r_data)
        for r_id, s_data in data.get("rover_states", {}).items():
            director.rover_states[r_id] = RoverOperationalState.from_dict(s_data)

        return director
