"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Unified Fleet & Infrastructure Asset Manager.

Manages all heterogeneous planetary assets across rovers, aerial rotorcraft,
communication relays, construction robots, and stationary settlement infrastructure.
Enforces conflict-free task allocation, power budget verification, and health monitoring.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from .atlas_mission_contracts import AssetHealthState, AssetType, MissionAsset


class UnifiedAssetManager:
    """Central registry and resource allocator for all mission robotic and static assets."""

    def __init__(self) -> None:
        self._assets: Dict[str, MissionAsset] = {}
        self._initialize_default_fleet()

    def _initialize_default_fleet(self) -> None:
        """Instantiate the canonical 8-asset planetary expedition fleet in Jezero Crater."""
        assets = [
            MissionAsset(
                asset_id="ATLAS-ROVER-01",
                name="Atlas Heavy Science Rover",
                asset_type=AssetType.GROUND_ROVER,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4447, "lon": 77.4508, "elevation_m": -2530.0},
                battery_charge_pct=98.5,
                power_capacity_kw=4.5,
                current_power_consumption_kw=1.2,
                telemetry={"odometry_m": 0.0, "drill_cycles": 0, "storage_slots_free": 16},
            ),
            MissionAsset(
                asset_id="INGENUITY-ROTOR-01",
                name="Ingenuity Scout Rotorcraft",
                asset_type=AssetType.AERIAL_ROTORCRAFT,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4448, "lon": 77.4509, "elevation_m": -2530.0},
                battery_charge_pct=100.0,
                power_capacity_kw=0.5,
                current_power_consumption_kw=0.05,
                telemetry={"flights_completed": 0, "total_airtime_s": 0.0, "rotor_health_pct": 100.0},
            ),
            MissionAsset(
                asset_id="HEXACOPTER-SURVEYOR-02",
                name="Hexacopter Regional Surveyor",
                asset_type=AssetType.AERIAL_ROTORCRAFT,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4446, "lon": 77.4507, "elevation_m": -2530.0},
                battery_charge_pct=95.0,
                power_capacity_kw=2.2,
                current_power_consumption_kw=0.1,
                telemetry={"flights_completed": 0, "payload_mass_kg": 4.5, "sensor_readiness": "CALIBRATED"},
            ),
            MissionAsset(
                asset_id="CONSTRUCTION-BOT-01",
                name="Autonomous Regolith Excavator & Sinterer",
                asset_type=AssetType.CONSTRUCTION_BOT,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4450, "lon": 77.4512, "elevation_m": -2530.2},
                battery_charge_pct=92.0,
                power_capacity_kw=12.0,
                current_power_consumption_kw=2.0,
                telemetry={"regolith_excavated_kg": 0.0, "blocks_sintered": 0, "tool_wear_pct": 0.0},
            ),
            MissionAsset(
                asset_id="SURFACE-COMM-MAST-01",
                name="High-Gain Surface Comm Mast",
                asset_type=AssetType.SURFACE_MAST,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4440, "lon": 77.4500, "elevation_m": -2528.0},
                battery_charge_pct=100.0,
                power_capacity_kw=1.5,
                current_power_consumption_kw=0.8,
                telemetry={"rf_band": "X_BAND", "uhf_relay_channels": 4, "los_radius_km": 12.5},
            ),
            MissionAsset(
                asset_id="KILOPOWER-REACTOR-01",
                name="Kilopower 120 kWe Fission Reactor",
                asset_type=AssetType.POWER_STATION,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4480, "lon": 77.4540, "elevation_m": -2528.0},
                battery_charge_pct=100.0,
                power_capacity_kw=120.0,
                current_power_consumption_kw=0.0,
                telemetry={"thermal_output_kwth": 400.0, "stirling_cycles": 8, "coolant_temp_k": 923.0},
            ),
            MissionAsset(
                asset_id="ISRU-PLANT-01",
                name="ISRU Atmosphere & Regolith Production Unit",
                asset_type=AssetType.ISRU_PLANT,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4465, "lon": 77.4515, "elevation_m": -2529.8},
                battery_charge_pct=100.0,
                power_capacity_kw=35.0,
                current_power_consumption_kw=5.0,
                telemetry={"soxe_purity_pct": 99.8, "o2_rate_kg_sol": 2.45, "sabatier_active": True},
            ),
            MissionAsset(
                asset_id="HABITAT-CORE-01",
                name="Expedition Habitat Alpha Core",
                asset_type=AssetType.HABITAT_CORE,
                health=AssetHealthState.NOMINAL,
                location={"lat": 18.4455, "lon": 77.4510, "elevation_m": -2530.0},
                battery_charge_pct=100.0,
                power_capacity_kw=40.0,
                current_power_consumption_kw=18.5,
                telemetry={"cabin_pressure_kpa": 101.3, "interior_temp_k": 294.15, "airlock_cycles": 0},
            ),
        ]
        for a in assets:
            self._assets[a.asset_id] = a

    def get_asset(self, asset_id: str) -> Optional[MissionAsset]:
        return self._assets.get(asset_id)

    def list_assets(self) -> List[MissionAsset]:
        return list(self._assets.values())

    def allocate_asset_to_task(self, asset_id: str, task_id: str) -> bool:
        """Assign an asset to a task if it is nominal/healthy and currently free."""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        if asset.health in (AssetHealthState.OFFLINE, AssetHealthState.SAFE_MODE):
            return False
        if asset.current_task_id is not None and asset.current_task_id != task_id:
            return False  # Already booked

        asset.current_task_id = task_id
        return True

    def release_asset(self, asset_id: str) -> None:
        """Release an asset from its active task."""
        asset = self._assets.get(asset_id)
        if asset:
            asset.current_task_id = None

    def update_asset_location(self, asset_id: str, lat: float, lon: float, elevation_m: float, distance_delta_m: float = 0.0) -> None:
        """Update spatial telemetry and accumulate odometry."""
        asset = self._assets.get(asset_id)
        if asset:
            asset.location = {"lat": lat, "lon": lon, "elevation_m": elevation_m}
            asset.cumulative_distance_m += distance_delta_m

    def update_asset_health(self, asset_id: str, health: AssetHealthState, status_note: Optional[str] = None) -> None:
        """Update asset operational health state."""
        asset = self._assets.get(asset_id)
        if asset:
            asset.health = health
            if status_note:
                asset.telemetry["health_note"] = status_note

    def consume_battery(self, asset_id: str, delta_pct: float) -> float:
        """Deduct battery charge safely, bounding at 0%."""
        asset = self._assets.get(asset_id)
        if asset:
            asset.battery_charge_pct = max(0.0, round(asset.battery_charge_pct - delta_pct, 2))
            return asset.battery_charge_pct
        return 0.0

    def recharge_battery(self, asset_id: str, delta_pct: float) -> float:
        """Recharge battery charge, bounding at 100%."""
        asset = self._assets.get(asset_id)
        if asset:
            asset.battery_charge_pct = min(100.0, round(asset.battery_charge_pct + delta_pct, 2))
            return asset.battery_charge_pct
        return 100.0

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in self._assets.items()}
