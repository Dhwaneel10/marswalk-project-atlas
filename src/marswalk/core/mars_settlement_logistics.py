"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Settlement Logistics & Cargo Architecture.

Plans interplanetary cargo manifests, lander payload sequencing, packaging tare
fractions, critical spare parts lead times (780-day synodic launch window), and
evaluates modular vs monolithic architecture mass trade-offs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CargoCriticality(str, Enum):
    """Logistics criticality classification for mission assurance."""
    CRITICAL_SURVIVAL = "CRITICAL_SURVIVAL"      # Immediate loss of settlement viability if missing
    MISSION_ESSENTIAL = "MISSION_ESSENTIAL"      # Key science/ISRU objectives delayed
    SUSTAINMENT_SPARES = "SUSTAINMENT_SPARES"    # Scheduled replacement components
    EXPANSION_CAPACITY = "EXPANSION_CAPACITY"    # Growth infrastructure for future phases


@dataclass
class CargoManifestItem:
    """An individual shipped item on an Earth-Mars landing manifest."""
    item_id: str
    name: str
    delivery_phase: str                      # "LANDER_01", "LANDER_02", "LANDER_03", "LANDER_04"
    net_payload_mass_kg: float
    packaging_tare_mass_kg: float
    volume_m3: float
    criticality: CargoCriticality
    destination_subsystem: str
    replacement_lead_time_sols: int = 780    # Standard Earth-Mars synodic launch window

    @property
    def gross_mass_kg(self) -> float:
        return self.net_payload_mass_kg + self.packaging_tare_mass_kg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "delivery_phase": self.delivery_phase,
            "net_payload_mass_kg": round(self.net_payload_mass_kg, 1),
            "packaging_tare_mass_kg": round(self.packaging_tare_mass_kg, 1),
            "gross_mass_kg": round(self.gross_mass_kg, 1),
            "volume_m3": round(self.volume_m3, 2),
            "criticality": self.criticality.value,
            "destination_subsystem": self.destination_subsystem,
            "replacement_lead_time_sols": self.replacement_lead_time_sols,
        }


@dataclass
class LogisticsTradeComparison:
    """Trade-study comparing monolithic vs modular vs ISRU-centric logistics."""
    strategy_name: str
    total_imported_mass_kg: float
    lander_flights_required: int
    surface_construction_sols: int
    local_isru_mass_produced_kg: float
    mass_leverage_ratio: float               # (ISRU Mass Produced) / (Imported Plant Mass)
    unresolved_bottlenecks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "total_imported_mass_kg": round(self.total_imported_mass_kg, 1),
            "lander_flights_required": self.lander_flights_required,
            "surface_construction_sols": self.surface_construction_sols,
            "local_isru_mass_produced_kg": round(self.local_isru_mass_produced_kg, 1),
            "mass_leverage_ratio": round(self.mass_leverage_ratio, 2),
            "unresolved_bottlenecks": self.unresolved_bottlenecks,
        }


class SettlementLogisticsPlanner:
    """Generates lander manifests, cargo allocations, and architectural mass trade studies."""

    def __init__(self):
        self._manifest: List[CargoManifestItem] = self._build_canonical_manifest()

    def get_manifest(self) -> List[CargoManifestItem]:
        return list(self._manifest)

    def evaluate_trade_studies(self) -> List[LogisticsTradeComparison]:
        """Compares four representative infrastructure logistics architectures."""
        return [
            LogisticsTradeComparison(
                strategy_name="Monolithic Pre-Integrated Modules (Heavy Lift)",
                total_imported_mass_kg=145000.0,
                lander_flights_required=6,
                surface_construction_sols=35,
                local_isru_mass_produced_kg=15000.0,
                mass_leverage_ratio=1.4,
                unresolved_bottlenecks=[
                    "Requires 35-tonne single-payload landing capability on Mars surface.",
                    "High launch costs; zero reliance on local construction materials.",
                ],
            ),
            LogisticsTradeComparison(
                strategy_name="Modular Expandable Shells with In-Situ Regolith Vaults",
                total_imported_mass_kg=82000.0,
                lander_flights_required=4,
                surface_construction_sols=120,
                local_isru_mass_produced_kg=65000.0,
                mass_leverage_ratio=4.8,
                unresolved_bottlenecks=[
                    "Heavy dependence on autonomous robotic excavation and block sintering reliability.",
                ],
            ),
            LogisticsTradeComparison(
                strategy_name="ISRU-Maximized Architecture (Mars Base Alpha Reference)",
                total_imported_mass_kg=68000.0,
                lander_flights_required=3,
                surface_construction_sols=180,
                local_isru_mass_produced_kg=120000.0, # Water, oxygen, methane, and sintered structures
                mass_leverage_ratio=8.5,
                unresolved_bottlenecks=[
                    "Requires 100 kWe continuous nuclear power online before propellant synthesis begins.",
                ],
            ),
            LogisticsTradeComparison(
                strategy_name="Robotic Redundancy Reserve (High Autonomous Assurance)",
                total_imported_mass_kg=76000.0,
                lander_flights_required=4,
                surface_construction_sols=95,
                local_isru_mass_produced_kg=110000.0,
                mass_leverage_ratio=7.2,
                unresolved_bottlenecks=[
                    "Adds 8,000 kg of spare robotic mobility actuators and manipulators.",
                ],
            ),
        ]

    def _build_canonical_manifest(self) -> List[CargoManifestItem]:
        return [
            # Lander 1: Power, Comms & Precursor Robots
            CargoManifestItem(
                item_id="CRG-01-REACTOR",
                name="100 kWe Fission Surface Power Unit",
                delivery_phase="LANDER_01",
                net_payload_mass_kg=4800.0,
                packaging_tare_mass_kg=720.0,
                volume_m3=24.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="POWER_SURFACE_GRID",
            ),
            CargoManifestItem(
                item_id="CRG-02-EXCAVATOR",
                name="Autonomous Bucket-Wheel Excavation Rover",
                delivery_phase="LANDER_01",
                net_payload_mass_kg=1850.0,
                packaging_tare_mass_kg=280.0,
                volume_m3=12.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="FLEET_ROBOTICS",
            ),
            CargoManifestItem(
                item_id="CRG-03-COMM-MAST",
                name="Telecom Mast & High-Gain X-Band Transceiver",
                delivery_phase="LANDER_01",
                net_payload_mass_kg=350.0,
                packaging_tare_mass_kg=65.0,
                volume_m3=4.5,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="TELECOMMUNICATIONS",
            ),
            # Lander 2: Heavy Construction & Habitat Shell
            CargoManifestItem(
                item_id="CRG-04-HAB-SHELL",
                name="Primary Inflatable Crew Habitat Pressure Bladder",
                delivery_phase="LANDER_02",
                net_payload_mass_kg=12500.0,
                packaging_tare_mass_kg=1450.0,
                volume_m3=48.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="HABITATION_NODE_1",
            ),
            CargoManifestItem(
                item_id="CRG-05-CRANE-ROBOT",
                name="Mobile Gantry Crane & Structural Rigging Robot",
                delivery_phase="LANDER_02",
                net_payload_mass_kg=2400.0,
                packaging_tare_mass_kg=350.0,
                volume_m3=16.0,
                criticality=CargoCriticality.MISSION_ESSENTIAL,
                destination_subsystem="CONSTRUCTION_FLEET",
            ),
            # Lander 3: ISRU & Life Support
            CargoManifestItem(
                item_id="CRG-06-ISRU-WATER",
                name="Subsurface Thermal Auger Water Extraction Plant",
                delivery_phase="LANDER_03",
                net_payload_mass_kg=3200.0,
                packaging_tare_mass_kg=480.0,
                volume_m3=18.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="ISRU_FACILITY",
            ),
            CargoManifestItem(
                item_id="CRG-07-ECLSS-SUITE",
                name="ECLSS Atmospheric Revitalizer & Sorbent Beds",
                delivery_phase="LANDER_03",
                net_payload_mass_kg=2900.0,
                packaging_tare_mass_kg=380.0,
                volume_m3=14.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="LIFE_SUPPORT",
            ),
            # Lander 4: Spares, Consumables & Laboratory
            CargoManifestItem(
                item_id="CRG-08-SPARES-BOX",
                name="High-Criticality Actuator & Valve Replacement Kit",
                delivery_phase="LANDER_04",
                net_payload_mass_kg=1800.0,
                packaging_tare_mass_kg=220.0,
                volume_m3=8.5,
                criticality=CargoCriticality.SUSTAINMENT_SPARES,
                destination_subsystem="MAINTENANCE_DEPOT",
            ),
            CargoManifestItem(
                item_id="CRG-09-RATIONS-500D",
                name="500-Sol Dry Caloric Rations Pack (8-Person)",
                delivery_phase="LANDER_04",
                net_payload_mass_kg=2800.0,
                packaging_tare_mass_kg=320.0,
                volume_m3=12.0,
                criticality=CargoCriticality.CRITICAL_SURVIVAL,
                destination_subsystem="LOGISTICS_STOWAGE",
            ),
        ]
