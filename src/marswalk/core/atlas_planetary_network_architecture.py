"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Planetary Network Architecture
============================================================================
Data structures, node definitions, antenna configurations, and network topology
graph for multi-settlement, mobile, orbital, and Earth gateway nodes.
"""

from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from marswalk.core.atlas_network_link_model import (
    CommunicationBand,
    TransmitterSpec,
    ReceiverSpec,
    CARRIER_FREQUENCIES_HZ,
)


class PlanetaryNodeType(str, enum.Enum):
    """Classification of communication nodes in the Martian network ecosystem."""
    SETTLEMENT_HUB = "SETTLEMENT_HUB"          # Mars Base Alpha (Jezero Crater)
    SCIENCE_OUTPOST = "SCIENCE_OUTPOST"        # Regional Science Outpost Beta (Nili Fossae)
    RESOURCE_OUTPOST = "RESOURCE_OUTPOST"      # Resource Outpost Gamma (Syrtis Major)
    MOBILE_ROVER = "MOBILE_ROVER"              # Surface rovers (Perseverance-class, Scout)
    MOBILE_AERIAL = "MOBILE_AERIAL"            # Aerial exploration hexacopters
    FIXED_SURFACE_RELAY = "FIXED_SURFACE_RELAY"# Surface radio towers / repeaters
    ORBITAL_RELAY = "ORBITAL_RELAY"            # LMO, elliptical, and areostationary orbiters
    EARTH_GATEWAY = "EARTH_GATEWAY"            # Earth Deep Space Network ground complexes


@dataclass
class PlanetaryNode:
    """A communication node operating within the Martian planetary network."""
    node_id: str
    name: str
    node_type: PlanetaryNodeType
    latitude_deg: float
    longitude_deg: float
    altitude_m: float                          # Height relative to Martian datum (or orbital altitude)
    buffer_capacity_bytes: int                 # Finite DTN non-volatile storage limit (bytes)
    transmitters: Dict[CommunicationBand, TransmitterSpec] = field(default_factory=dict)
    receivers: Dict[CommunicationBand, ReceiverSpec] = field(default_factory=dict)
    buffer_used_bytes: int = 0
    is_active: bool = True
    battery_level_pct: float = 100.0
    solar_exposure_pct: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def buffer_available_bytes(self) -> int:
        return max(0, self.buffer_capacity_bytes - self.buffer_used_bytes)

    @property
    def buffer_utilization_pct(self) -> float:
        if self.buffer_capacity_bytes <= 0:
            return 100.0
        return min(100.0, (self.buffer_used_bytes / float(self.buffer_capacity_bytes)) * 100.0)

    @property
    def is_orbital(self) -> bool:
        return self.node_type == PlanetaryNodeType.ORBITAL_RELAY

    @property
    def is_earth(self) -> bool:
        return self.node_type == PlanetaryNodeType.EARTH_GATEWAY

    @property
    def is_surface(self) -> bool:
        return not (self.is_orbital or self.is_earth)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "latitude_deg": round(self.latitude_deg, 4),
            "longitude_deg": round(self.longitude_deg, 4),
            "altitude_m": round(self.altitude_m, 1),
            "buffer_capacity_mb": round(self.buffer_capacity_bytes / 1e6, 2),
            "buffer_used_mb": round(self.buffer_used_bytes / 1e6, 2),
            "buffer_utilization_pct": round(self.buffer_utilization_pct, 1),
            "is_active": self.is_active,
            "battery_level_pct": round(self.battery_level_pct, 1),
            "supported_bands": [b.value for b in self.transmitters.keys()],
        }


def create_standard_planetary_network() -> PlanetaryNetworkTopology:
    """
    Constructs the canonical 13Y Martian planetary network topology:
    - 3 Surface Settlements (Alpha, Beta, Gamma)
    - 3 Mobile Assets (Rover-01, Scout-02, Hexacopter-01)
    - 2 Fixed Surface Relays (Tower-Alpha, Tower-Beta)
    - 4 Orbital Relay Spacecraft (Ares-SunSync, Hellas-Polar, Areo-Stationary, Odyssey-UHF)
    - 3 Earth Deep Space Network Gateways (Goldstone, Madrid, Canberra)
    """
    net = PlanetaryNetworkTopology()

    # 1. Mars Base Alpha (Jezero Crater - 18.38°N, 77.58°E, -2500m elevation)
    alpha = PlanetaryNode(
        node_id="SETTLEMENT-ALPHA",
        name="Mars Base Alpha (Jezero)",
        node_type=PlanetaryNodeType.SETTLEMENT_HUB,
        latitude_deg=18.38,
        longitude_deg=77.58,
        altitude_m=-2500.0,
        buffer_capacity_bytes=100 * 1024 * 1024 * 1024,  # 100 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Alpha-S-Mast", band=CommunicationBand.S_BAND, power_watts=50.0, antenna_gain_dbi=18.0
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Alpha-UHF-Relay", band=CommunicationBand.UHF_PROXIMITY, power_watts=20.0, antenna_gain_dbi=8.0
            ),
            CommunicationBand.X_BAND_DEEP_SPACE: TransmitterSpec(
                name="Alpha-X-Direct", band=CommunicationBand.X_BAND_DEEP_SPACE, power_watts=100.0, antenna_gain_dbi=42.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="Alpha-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=18.0),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Alpha-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=8.0),
            CommunicationBand.X_BAND_DEEP_SPACE: ReceiverSpec(name="Alpha-X-Rx", band=CommunicationBand.X_BAND_DEEP_SPACE, antenna_gain_dbi=42.0),
        },
    )
    net.add_node(alpha)

    # 2. Regional Science Outpost Beta (Nili Fossae - 21.0°N, 74.0°E, -1200m elevation)
    beta = PlanetaryNode(
        node_id="OUTPOST-BETA",
        name="Science Outpost Beta (Nili)",
        node_type=PlanetaryNodeType.SCIENCE_OUTPOST,
        latitude_deg=21.00,
        longitude_deg=74.00,
        altitude_m=-1200.0,
        buffer_capacity_bytes=25 * 1024 * 1024 * 1024,  # 25 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Beta-S-Mast", band=CommunicationBand.S_BAND, power_watts=30.0, antenna_gain_dbi=15.0
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Beta-UHF-Proximity", band=CommunicationBand.UHF_PROXIMITY, power_watts=15.0, antenna_gain_dbi=6.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="Beta-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=15.0),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Beta-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=6.0),
        },
    )
    net.add_node(beta)

    # 3. Resource Outpost Gamma (Syrtis Major - 12.0°N, 70.0°E, 1100m elevation)
    gamma = PlanetaryNode(
        node_id="OUTPOST-GAMMA",
        name="Resource Outpost Gamma (Syrtis)",
        node_type=PlanetaryNodeType.RESOURCE_OUTPOST,
        latitude_deg=12.00,
        longitude_deg=70.00,
        altitude_m=1100.0,
        buffer_capacity_bytes=50 * 1024 * 1024 * 1024,  # 50 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Gamma-S-Mast", band=CommunicationBand.S_BAND, power_watts=35.0, antenna_gain_dbi=16.0
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Gamma-UHF-Proximity", band=CommunicationBand.UHF_PROXIMITY, power_watts=15.0, antenna_gain_dbi=6.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="Gamma-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=16.0),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Gamma-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=6.0),
        },
    )
    net.add_node(gamma)

    # 4. Mobile Rover Alpha-01 (In Jezero - 18.42°N, 77.62°E)
    rover1 = PlanetaryNode(
        node_id="ROVER-ALPHA-01",
        name="Heavy Science Rover Atlas-1",
        node_type=PlanetaryNodeType.MOBILE_ROVER,
        latitude_deg=18.42,
        longitude_deg=77.62,
        altitude_m=-2480.0,
        buffer_capacity_bytes=1024 * 1024 * 1024,  # 1 GB
        transmitters={
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Rover1-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=10.0, antenna_gain_dbi=4.0
            ),
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Rover1-S", band=CommunicationBand.S_BAND, power_watts=5.0, antenna_gain_dbi=3.0
            ),
        },
        receivers={
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Rover1-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=4.0),
            CommunicationBand.S_BAND: ReceiverSpec(name="Rover1-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=3.0),
        },
    )
    net.add_node(rover1)

    # 5. Mobile Scout Beta-02 (Near Outpost Beta - 21.05°N, 74.08°E)
    scout2 = PlanetaryNode(
        node_id="SCOUT-BETA-02",
        name="Fast Scout Rover Explorer-2",
        node_type=PlanetaryNodeType.MOBILE_ROVER,
        latitude_deg=21.05,
        longitude_deg=74.08,
        altitude_m=-1180.0,
        buffer_capacity_bytes=512 * 1024 * 1024,  # 512 MB
        transmitters={
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Scout2-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=5.0, antenna_gain_dbi=3.0
            ),
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Scout2-S", band=CommunicationBand.S_BAND, power_watts=3.0, antenna_gain_dbi=2.5
            ),
        },
        receivers={
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Scout2-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=3.0),
            CommunicationBand.S_BAND: ReceiverSpec(name="Scout2-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=2.5),
        },
    )
    net.add_node(scout2)

    # 6. Aerial Hexacopter-01 (Airborne Jezero - 18.40°N, 77.60°E, altitude 100m AGL)
    aero1 = PlanetaryNode(
        node_id="HEXACOPTER-AERO-01",
        name="Martian Aerial Scout Hexacopter-1",
        node_type=PlanetaryNodeType.MOBILE_AERIAL,
        latitude_deg=18.40,
        longitude_deg=77.60,
        altitude_m=-2400.0,
        buffer_capacity_bytes=256 * 1024 * 1024,  # 256 MB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Hex-S", band=CommunicationBand.S_BAND, power_watts=4.0, antenna_gain_dbi=2.5
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Hex-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=5.0, antenna_gain_dbi=2.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="Hex-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=2.5),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Hex-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=2.0),
        },
    )
    net.add_node(aero1)

    # 7. Fixed Surface Relay Tower Alpha-North (18.60°N, 77.40°E, Crater Rim +150m)
    tower1 = PlanetaryNode(
        node_id="RELAY-TOWER-ALPHA",
        name="Jezero North Rim Relay Tower",
        node_type=PlanetaryNodeType.FIXED_SURFACE_RELAY,
        latitude_deg=18.60,
        longitude_deg=77.40,
        altitude_m=-2100.0,
        buffer_capacity_bytes=8 * 1024 * 1024 * 1024,  # 8 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="TowerAlpha-S", band=CommunicationBand.S_BAND, power_watts=25.0, antenna_gain_dbi=20.0
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="TowerAlpha-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=15.0, antenna_gain_dbi=10.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="TowerAlpha-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=20.0),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="TowerAlpha-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=10.0),
        },
    )
    net.add_node(tower1)

    # 8. Fixed Surface Relay Tower Beta-Ridge (19.80°N, 75.80°E, Midpoint Relay)
    tower2 = PlanetaryNode(
        node_id="RELAY-TOWER-BETA",
        name="Nili-Jezero Midpoint Relay Tower",
        node_type=PlanetaryNodeType.FIXED_SURFACE_RELAY,
        latitude_deg=19.80,
        longitude_deg=75.80,
        altitude_m=-1500.0,
        buffer_capacity_bytes=8 * 1024 * 1024 * 1024,  # 8 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="TowerBeta-S", band=CommunicationBand.S_BAND, power_watts=25.0, antenna_gain_dbi=20.0
            ),
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="TowerBeta-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=15.0, antenna_gain_dbi=10.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="TowerBeta-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=20.0),
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="TowerBeta-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=10.0),
        },
    )
    net.add_node(tower2)

    # 9. ATLAS-ORB-01: Ares-SunSync (MRO/TGO Proxy - Circular 400 km, 93.0° inclination)
    orb1 = PlanetaryNode(
        node_id="ATLAS-ORB-01",
        name="Atlas Orbiter 1 (Ares Sun-Sync Polar)",
        node_type=PlanetaryNodeType.ORBITAL_RELAY,
        latitude_deg=0.0,
        longitude_deg=0.0,
        altitude_m=400_000.0,
        buffer_capacity_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
        transmitters={
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Orb1-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=20.0, antenna_gain_dbi=6.0
            ),
            CommunicationBand.X_BAND_PROXIMITY: TransmitterSpec(
                name="Orb1-X-Crosslink", band=CommunicationBand.X_BAND_PROXIMITY, power_watts=35.0, antenna_gain_dbi=28.0
            ),
            CommunicationBand.X_BAND_DEEP_SPACE: TransmitterSpec(
                name="Orb1-X-Earth", band=CommunicationBand.X_BAND_DEEP_SPACE, power_watts=100.0, antenna_gain_dbi=44.0
            ),
            CommunicationBand.KA_BAND_DEEP_SPACE: TransmitterSpec(
                name="Orb1-Ka-Earth", band=CommunicationBand.KA_BAND_DEEP_SPACE, power_watts=50.0, antenna_gain_dbi=48.0
            ),
        },
        receivers={
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Orb1-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=6.0),
            CommunicationBand.X_BAND_PROXIMITY: ReceiverSpec(name="Orb1-X-Rx", band=CommunicationBand.X_BAND_PROXIMITY, antenna_gain_dbi=28.0),
            CommunicationBand.X_BAND_DEEP_SPACE: ReceiverSpec(name="Orb1-X-Earth-Rx", band=CommunicationBand.X_BAND_DEEP_SPACE, antenna_gain_dbi=44.0),
        },
        metadata={"orbit_type": "CIRCULAR_POLAR", "semi_major_axis_km": 3796.19, "inclination_deg": 93.0},
    )
    net.add_node(orb1)

    # 10. ATLAS-ORB-02: Hellas-Polar (Science & Relay - Elliptical 400x1600 km, 63.4° critical inclination)
    orb2 = PlanetaryNode(
        node_id="ATLAS-ORB-02",
        name="Atlas Orbiter 2 (Hellas Elliptical Science/Relay)",
        node_type=PlanetaryNodeType.ORBITAL_RELAY,
        latitude_deg=0.0,
        longitude_deg=0.0,
        altitude_m=800_000.0,
        buffer_capacity_bytes=16 * 1024 * 1024 * 1024,  # 16 GB
        transmitters={
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Orb2-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=20.0, antenna_gain_dbi=6.0
            ),
            CommunicationBand.X_BAND_PROXIMITY: TransmitterSpec(
                name="Orb2-X-Crosslink", band=CommunicationBand.X_BAND_PROXIMITY, power_watts=35.0, antenna_gain_dbi=28.0
            ),
            CommunicationBand.X_BAND_DEEP_SPACE: TransmitterSpec(
                name="Orb2-X-Earth", band=CommunicationBand.X_BAND_DEEP_SPACE, power_watts=100.0, antenna_gain_dbi=44.0
            ),
        },
        receivers={
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Orb2-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=6.0),
            CommunicationBand.X_BAND_PROXIMITY: ReceiverSpec(name="Orb2-X-Rx", band=CommunicationBand.X_BAND_PROXIMITY, antenna_gain_dbi=28.0),
            CommunicationBand.X_BAND_DEEP_SPACE: ReceiverSpec(name="Orb2-X-Earth-Rx", band=CommunicationBand.X_BAND_DEEP_SPACE, antenna_gain_dbi=44.0),
        },
        metadata={"orbit_type": "ELLIPTICAL", "semi_major_axis_km": 4396.19, "eccentricity": 0.136, "inclination_deg": 63.4},
    )
    net.add_node(orb2)

    # 11. ATLAS-ORB-03: Areo-Stationary (High Altitude Equatorial - 17,032 km altitude, 0.0° inclination)
    orb3 = PlanetaryNode(
        node_id="ATLAS-ORB-03",
        name="Atlas Orbiter 3 (Areostationary High Relay)",
        node_type=PlanetaryNodeType.ORBITAL_RELAY,
        latitude_deg=0.0,
        longitude_deg=75.0,  # Positioned above Eastern Hemisphere / Jezero longitude
        altitude_m=17_032_000.0,
        buffer_capacity_bytes=32 * 1024 * 1024 * 1024,  # 32 GB
        transmitters={
            CommunicationBand.S_BAND: TransmitterSpec(
                name="Orb3-S-High", band=CommunicationBand.S_BAND, power_watts=100.0, antenna_gain_dbi=32.0
            ),
            CommunicationBand.X_BAND_PROXIMITY: TransmitterSpec(
                name="Orb3-X-Crosslink", band=CommunicationBand.X_BAND_PROXIMITY, power_watts=50.0, antenna_gain_dbi=30.0
            ),
            CommunicationBand.KA_BAND_DEEP_SPACE: TransmitterSpec(
                name="Orb3-Ka-Earth", band=CommunicationBand.KA_BAND_DEEP_SPACE, power_watts=80.0, antenna_gain_dbi=50.0
            ),
            CommunicationBand.OPTICAL_LASER: TransmitterSpec(
                name="Orb3-Laser", band=CommunicationBand.OPTICAL_LASER, power_watts=10.0, antenna_gain_dbi=95.0
            ),
        },
        receivers={
            CommunicationBand.S_BAND: ReceiverSpec(name="Orb3-S-Rx", band=CommunicationBand.S_BAND, antenna_gain_dbi=32.0),
            CommunicationBand.X_BAND_PROXIMITY: ReceiverSpec(name="Orb3-X-Rx", band=CommunicationBand.X_BAND_PROXIMITY, antenna_gain_dbi=30.0),
            CommunicationBand.KA_BAND_DEEP_SPACE: ReceiverSpec(name="Orb3-Ka-Rx", band=CommunicationBand.KA_BAND_DEEP_SPACE, antenna_gain_dbi=50.0),
            CommunicationBand.OPTICAL_LASER: ReceiverSpec(name="Orb3-Laser-Rx", band=CommunicationBand.OPTICAL_LASER, antenna_gain_dbi=95.0),
        },
        metadata={"orbit_type": "AREOSTATIONARY", "semi_major_axis_km": 20428.19, "inclination_deg": 0.0},
    )
    net.add_node(orb3)

    # 12. ATLAS-ORB-04: Odyssey-UHF (Circular 390 km, dedicated proximity relay)
    orb4 = PlanetaryNode(
        node_id="ATLAS-ORB-04",
        name="Atlas Orbiter 4 (Odyssey-Class Dedicated Proximity Relay)",
        node_type=PlanetaryNodeType.ORBITAL_RELAY,
        latitude_deg=0.0,
        longitude_deg=0.0,
        altitude_m=390_000.0,
        buffer_capacity_bytes=8 * 1024 * 1024 * 1024,  # 8 GB
        transmitters={
            CommunicationBand.UHF_PROXIMITY: TransmitterSpec(
                name="Orb4-UHF", band=CommunicationBand.UHF_PROXIMITY, power_watts=25.0, antenna_gain_dbi=8.0
            ),
            CommunicationBand.X_BAND_DEEP_SPACE: TransmitterSpec(
                name="Orb4-X-Earth", band=CommunicationBand.X_BAND_DEEP_SPACE, power_watts=50.0, antenna_gain_dbi=40.0
            ),
        },
        receivers={
            CommunicationBand.UHF_PROXIMITY: ReceiverSpec(name="Orb4-UHF-Rx", band=CommunicationBand.UHF_PROXIMITY, antenna_gain_dbi=8.0),
            CommunicationBand.X_BAND_DEEP_SPACE: ReceiverSpec(name="Orb4-X-Rx", band=CommunicationBand.X_BAND_DEEP_SPACE, antenna_gain_dbi=40.0),
        },
        metadata={"orbit_type": "CIRCULAR_POLAR", "semi_major_axis_km": 3786.19, "inclination_deg": 93.5},
    )
    net.add_node(orb4)

    # 13. Earth Deep Space Network (DSN Unified Gateway)
    earth = PlanetaryNode(
        node_id="EARTH-DSN-GATEWAY",
        name="Earth Deep Space Network (Goldstone/Madrid/Canberra)",
        node_type=PlanetaryNodeType.EARTH_GATEWAY,
        latitude_deg=35.42,
        longitude_deg=-116.89,
        altitude_m=1000.0,
        buffer_capacity_bytes=1000 * 1024 * 1024 * 1024 * 1024,  # 1 Petabyte
        transmitters={
            CommunicationBand.X_BAND_DEEP_SPACE: TransmitterSpec(
                name="DSN-70m-X-Tx", band=CommunicationBand.X_BAND_DEEP_SPACE, power_watts=20_000.0, antenna_gain_dbi=74.0
            ),
            CommunicationBand.KA_BAND_DEEP_SPACE: TransmitterSpec(
                name="DSN-34m-Ka-Tx", band=CommunicationBand.KA_BAND_DEEP_SPACE, power_watts=1_000.0, antenna_gain_dbi=78.0
            ),
            CommunicationBand.OPTICAL_LASER: TransmitterSpec(
                name="Earth-Optical-Tx", band=CommunicationBand.OPTICAL_LASER, power_watts=5_000.0, antenna_gain_dbi=120.0
            ),
        },
        receivers={
            CommunicationBand.X_BAND_DEEP_SPACE: ReceiverSpec(
                name="DSN-70m-X-Rx", band=CommunicationBand.X_BAND_DEEP_SPACE, antenna_gain_dbi=74.0, sys_noise_temp_k=20.0
            ),
            CommunicationBand.KA_BAND_DEEP_SPACE: ReceiverSpec(
                name="DSN-34m-Ka-Rx", band=CommunicationBand.KA_BAND_DEEP_SPACE, antenna_gain_dbi=78.0, sys_noise_temp_k=25.0
            ),
            CommunicationBand.OPTICAL_LASER: ReceiverSpec(
                name="Earth-Optical-Rx", band=CommunicationBand.OPTICAL_LASER, antenna_gain_dbi=120.0, sys_noise_temp_k=290.0
            ),
        },
        metadata={"dsn_complexes": ["Goldstone", "Madrid", "Canberra"], "aperture_m": 70.0},
    )
    net.add_node(earth)

    return net


class PlanetaryNetworkTopology:
    """Graph structure managing nodes, topology, and cross-node communication links."""

    def __init__(self) -> None:
        self.nodes: Dict[str, PlanetaryNode] = {}
        self.static_surface_edges: Set[Tuple[str, str]] = set()
        self._initialize_static_surface_links()

    def add_node(self, node: PlanetaryNode) -> None:
        self.nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[PlanetaryNode]:
        return self.nodes.get(node_id)

    def get_all_nodes(self) -> List[PlanetaryNode]:
        return list(self.nodes.values())

    def get_settlements(self) -> List[PlanetaryNode]:
        return [
            n for n in self.nodes.values()
            if n.node_type in (PlanetaryNodeType.SETTLEMENT_HUB, PlanetaryNodeType.SCIENCE_OUTPOST, PlanetaryNodeType.RESOURCE_OUTPOST)
        ]

    def get_mobile_assets(self) -> List[PlanetaryNode]:
        return [
            n for n in self.nodes.values()
            if n.node_type in (PlanetaryNodeType.MOBILE_ROVER, PlanetaryNodeType.MOBILE_AERIAL)
        ]

    def get_orbital_relays(self) -> List[PlanetaryNode]:
        return [n for n in self.nodes.values() if n.node_type == PlanetaryNodeType.ORBITAL_RELAY]

    def get_earth_gateways(self) -> List[PlanetaryNode]:
        return [n for n in self.nodes.values() if n.node_type == PlanetaryNodeType.EARTH_GATEWAY]

    def _initialize_static_surface_links(self) -> None:
        """
        Defines terrestrial line-of-sight and microwave/radio hops between surface settlements,
        relay towers, and local mobile assets.
        """
        edges = [
            # Jezero Local Terrestrial Mesh
            ("SETTLEMENT-ALPHA", "RELAY-TOWER-ALPHA"),
            ("RELAY-TOWER-ALPHA", "SETTLEMENT-ALPHA"),
            ("SETTLEMENT-ALPHA", "ROVER-ALPHA-01"),
            ("ROVER-ALPHA-01", "SETTLEMENT-ALPHA"),
            ("SETTLEMENT-ALPHA", "HEXACOPTER-AERO-01"),
            ("HEXACOPTER-AERO-01", "SETTLEMENT-ALPHA"),
            ("RELAY-TOWER-ALPHA", "HEXACOPTER-AERO-01"),
            ("HEXACOPTER-AERO-01", "RELAY-TOWER-ALPHA"),
            # Inter-Settlement Surface Backbone via Midpoint Tower
            ("RELAY-TOWER-ALPHA", "RELAY-TOWER-BETA"),
            ("RELAY-TOWER-BETA", "RELAY-TOWER-ALPHA"),
            ("RELAY-TOWER-BETA", "OUTPOST-BETA"),
            ("OUTPOST-BETA", "RELAY-TOWER-BETA"),
            # Beta Local Mesh
            ("OUTPOST-BETA", "SCOUT-BETA-02"),
            ("SCOUT-BETA-02", "OUTPOST-BETA"),
        ]
        for src, dst in edges:
            self.static_surface_edges.add((src, dst))

    def has_static_surface_link(self, src_id: str, dst_id: str) -> bool:
        return (src_id, dst_id) in self.static_surface_edges

    def get_shared_communication_bands(
        self, src_id: str, dst_id: str
    ) -> List[CommunicationBand]:
        """Returns list of communication bands where src has transmitter and dst has receiver."""
        src = self.get_node(src_id)
        dst = self.get_node(dst_id)
        if not src or not dst or not src.is_active or not dst.is_active:
            return []
        common = set(src.transmitters.keys()).intersection(dst.receivers.keys())
        return sorted(list(common), key=lambda b: b.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "settlements": len(self.get_settlements()),
            "mobile_assets": len(self.get_mobile_assets()),
            "orbital_relays": len(self.get_orbital_relays()),
            "earth_gateways": len(self.get_earth_gateways()),
            "static_surface_links": len(self.static_surface_edges),
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
        }
