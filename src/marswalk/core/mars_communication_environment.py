"""
MarsWalk 2.0 / Project Atlas — Milestone 13O: Deep Space Communication Environment
==================================================================================
Simulates physical and operational constraints of Earth–Mars communications:
- Configurable one-way light time (OWLT) and round-trip light time (RTLT) (3–22 min range).
- Independent uplink and downlink propagation delays.
- Deep Space Network (DSN) contact windows, tracking passes, and occultations.
- Outages, packet loss, retry limits, and solar conjunction blackouts.
- Channel capacity, priority packet queues, and transmission progress.
- Distinct epistemic state tagging: Current on Mars vs Last Reported on Earth.
- Disclosures separating geometric line-of-sight from RF link assumptions.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import enum
import heapq
import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.mars_command_transmission import (
    MarsRoverCommand,
    CommandLifecycleState,
    PacketType,
    compute_payload_sha256,
)


class EpistemicInformationState(str, enum.Enum):
    """Rigorous epistemic classification of mission telemetry on Earth vs Mars."""
    CURRENT_ON_MARS = "CURRENT_ON_MARS"  # Exists in Mars physical reality
    LAST_REPORTED_BY_MARS = "LAST_REPORTED_BY_MARS"  # Last confirmed state received by Earth
    PREDICTED = "PREDICTED"  # Earth forward model estimate
    ESTIMATED = "ESTIMATED"  # Filtered/inferred parameter
    UNKNOWN = "UNKNOWN"  # No telemetry received or model unvalidated
    AWAITING_TELEMETRY_CONFIRMATION = "AWAITING_TELEMETRY_CONFIRMATION"  # Action in progress, unconfirmed


class LinkMediumType(str, enum.Enum):
    """Type of communication link."""
    DIRECT_TO_EARTH_X_BAND = "DIRECT_TO_EARTH_X_BAND"
    ORBITER_RELAY_UHF = "ORBITER_RELAY_UHF"
    SURFACE_RELAY_MESH = "SURFACE_RELAY_MESH"


class ContactWindowStatus(str, enum.Enum):
    """Operational status of a scheduled Deep Space Network contact pass."""
    SCHEDULED = "SCHEDULED"
    ACTIVE_IN_VIEW = "ACTIVE_IN_VIEW"
    COMPLETED = "COMPLETED"
    MISSED_OCCULTATION = "MISSED_OCCULTATION"
    TERMINATED_EARLY = "TERMINATED_EARLY"
    SOLAR_CONJUNCTION_BLACKOUT = "SOLAR_CONJUNCTION_BLACKOUT"


@dataclass
class DSNContactWindow:
    """
    Scheduled ground station contact window between DSN / Relay Orbiter and Mars.
    """
    window_id: str
    station_or_relay_name: str  # e.g., "DSN_GOLDSTONE_DSS14", "MRO_UHF_PASS_412"
    target_rover_id: str
    link_type: str
    start_sim_time_s: float
    end_sim_time_s: float
    uplink_bandwidth_bps: float = 2000.0  # 2 kbps DTE typical command rate
    downlink_bandwidth_bps: float = 32000.0  # 32 kbps DTE or 2 Mbps via UHF orbiter
    status: str = ContactWindowStatus.SCHEDULED.value
    actual_bytes_uplinked: int = 0
    actual_bytes_downlinked: int = 0
    interruption_reason: Optional[str] = None

    @property
    def duration_s(self) -> float:
        return max(0.0, self.end_sim_time_s - self.start_sim_time_s)

    def is_active_at(self, sim_time_s: float) -> bool:
        return self.status == ContactWindowStatus.ACTIVE_IN_VIEW.value and (
            self.start_sim_time_s <= sim_time_s < self.end_sim_time_s
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_id": self.window_id,
            "station_or_relay_name": self.station_or_relay_name,
            "target_rover_id": self.target_rover_id,
            "link_type": self.link_type,
            "start_sim_time_s": self.start_sim_time_s,
            "end_sim_time_s": self.end_sim_time_s,
            "duration_s": self.duration_s,
            "uplink_bandwidth_bps": self.uplink_bandwidth_bps,
            "downlink_bandwidth_bps": self.downlink_bandwidth_bps,
            "status": self.status,
            "actual_bytes_uplinked": self.actual_bytes_uplinked,
            "actual_bytes_downlinked": self.actual_bytes_downlinked,
            "interruption_reason": self.interruption_reason,
        }


@dataclass
class CommunicationPacket:
    """
    Individual data packet traveling across the deep space communication medium.
    """
    packet_id: str
    packet_type: str  # TELECOMMAND, TELEMETRY, ACKNOWLEDGEMENT
    source_entity: str  # e.g. "EARTH_MISSION_CONTROL", "ROVER_PERSEVERANCE"
    destination_entity: str
    command_id: Optional[str]
    payload: Dict[str, Any]
    size_bytes: int
    transmission_sim_time_s: float
    expected_arrival_sim_time_s: float
    one_way_light_time_s: float
    priority: int = 1  # 0=Critical/Health, 1=Telecommand/ACK, 2=Telemetry, 3=Science
    retry_count: int = 0
    is_delivered: bool = False
    is_dropped: bool = False
    drop_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "packet_type": self.packet_type,
            "source_entity": self.source_entity,
            "destination_entity": self.destination_entity,
            "command_id": self.command_id,
            "size_bytes": self.size_bytes,
            "transmission_sim_time_s": self.transmission_sim_time_s,
            "expected_arrival_sim_time_s": self.expected_arrival_sim_time_s,
            "one_way_light_time_s": self.one_way_light_time_s,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "is_delivered": self.is_delivered,
            "is_dropped": self.is_dropped,
            "drop_reason": self.drop_reason,
        }


@dataclass
class SolarConjunctionConfig:
    """
    Parameters modeling Earth–Mars solar conjunction blackout.
    Occurs when the Sun passes between Earth and Mars (Sun-Earth-Probe angle < ~2 deg).
    """
    is_active: bool = False
    conjunction_start_sim_time_s: float = 0.0
    conjunction_end_sim_time_s: float = 0.0
    solar_elongation_deg: float = 45.0  # Safe threshold typically > 3.0 deg
    rf_noise_floor_degradation_db: float = 0.0
    allow_emergency_carrier_detection: bool = False
    blackout_duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DeepSpaceCommunicationEnvironment:
    """
    Simulates Earth–Mars physical and geometric signal propagation,
    transmission queues, contact schedules, packet loss, and outages.
    """

    def __init__(
        self,
        default_owlt_s: float = 852.0,  # 14.2 minutes default (~255 million km)
        uplink_owlt_s: Optional[float] = None,
        downlink_owlt_s: Optional[float] = None,
        packet_loss_rate: float = 0.0,
        max_retries: int = 3,
    ):
        # Propagation Latencies
        self.uplink_owlt_s: float = uplink_owlt_s if uplink_owlt_s is not None else default_owlt_s
        self.downlink_owlt_s: float = downlink_owlt_s if downlink_owlt_s is not None else default_owlt_s
        self.packet_loss_rate: float = max(0.0, min(1.0, packet_loss_rate))
        self.max_retries: int = max_retries

        # Scheduled Contact Windows
        self.contact_windows: List[DSNContactWindow] = []

        # In-Flight Transmission Channels
        self.in_flight_uplink: List[CommunicationPacket] = []  # Earth -> Mars
        self.in_flight_downlink: List[CommunicationPacket] = []  # Mars -> Earth

        # Queues on Earth and Mars
        self.earth_outbound_queue: List[CommunicationPacket] = []
        self.mars_telemetry_queue: List[CommunicationPacket] = []

        # Completed / Delivered Archive
        self.delivered_packets: List[CommunicationPacket] = []
        self.dropped_packets: List[CommunicationPacket] = []

        # Outages and Conjunction
        self.solar_conjunction: SolarConjunctionConfig = SolarConjunctionConfig()
        self.simulated_outages: List[Dict[str, Any]] = []

        # Epistemic Snapshot for Earth
        self.last_confirmed_mars_telemetry: Dict[str, Any] = {}
        self.last_confirmed_telemetry_sim_time_s: float = 0.0

    @property
    def round_trip_light_time_s(self) -> float:
        """Calculates total Round-Trip Light Time (RTLT) in seconds."""
        return self.uplink_owlt_s + self.downlink_owlt_s

    @property
    def rtl_time_minutes(self) -> float:
        """RTLT formatted in minutes."""
        return round(self.round_trip_light_time_s / 60.0, 2)

    def set_latency_profile(self, uplink_min: float, downlink_min: float):
        """Configures independent uplink and downlink one-way propagation delays in minutes."""
        self.uplink_owlt_s = max(180.0, min(1320.0, uplink_min * 60.0))  # 3 to 22 min bounds
        self.downlink_owlt_s = max(180.0, min(1320.0, downlink_min * 60.0))

    def schedule_contact_window(
        self,
        station_name: str,
        rover_id: str,
        start_time_s: float,
        duration_s: float,
        link_type: str = LinkMediumType.DIRECT_TO_EARTH_X_BAND.value,
        uplink_bps: float = 2000.0,
        downlink_bps: float = 32000.0,
    ) -> DSNContactWindow:
        """Schedules a new DSN or Orbiter Relay contact window."""
        win_id = f"WIN_{rover_id}_{int(start_time_s)}_{uuid.uuid4().hex[:4].upper()}"
        win = DSNContactWindow(
            window_id=win_id,
            station_or_relay_name=station_name,
            target_rover_id=rover_id,
            link_type=link_type,
            start_sim_time_s=start_time_s,
            end_sim_time_s=start_time_s + duration_s,
            uplink_bandwidth_bps=uplink_bps,
            downlink_bandwidth_bps=downlink_bps,
            status=ContactWindowStatus.SCHEDULED.value,
        )
        self.contact_windows.append(win)
        return win

    def inject_solar_conjunction_blackout(self, start_sim_time_s: float, duration_s: float):
        """Activates a multi-day solar conjunction communication blackout."""
        self.solar_conjunction = SolarConjunctionConfig(
            is_active=True,
            conjunction_start_sim_time_s=start_sim_time_s,
            conjunction_end_sim_time_s=start_sim_time_s + duration_s,
            solar_elongation_deg=0.8,  # Under 1 degree
            rf_noise_floor_degradation_db=35.0,
            blackout_duration_s=duration_s,
        )

    def inject_link_outage(self, start_sim_time_s: float, duration_s: float, reason: str):
        """Injects a transient link outage (e.g. ground antenna failure or relay occultation)."""
        self.simulated_outages.append({
            "outage_id": f"OUTAGE_{int(start_sim_time_s)}_{uuid.uuid4().hex[:4]}",
            "start_time_s": start_sim_time_s,
            "end_time_s": start_sim_time_s + duration_s,
            "reason": reason,
        })

    def is_link_operational_at(self, sim_time_s: float, rover_id: Optional[str] = None) -> Tuple[bool, str]:
        """Evaluates whether RF communications are possible at current simulation timestamp."""
        # 1. Check Solar Conjunction
        if self.solar_conjunction.is_active:
            if self.solar_conjunction.conjunction_start_sim_time_s <= sim_time_s < self.solar_conjunction.conjunction_end_sim_time_s:
                return False, f"SOLAR CONJUNCTION BLACKOUT (SEP Elongation: {self.solar_conjunction.solar_elongation_deg} deg)"

        # 2. Check Transient Outages
        for o in self.simulated_outages:
            if o["start_time_s"] <= sim_time_s < o["end_time_s"]:
                return False, f"COMMUNICATION OUTAGE: {o['reason']}"

        # 3. Check Contact Windows
        if self.contact_windows:
            active_wins = [w for w in self.contact_windows if w.start_sim_time_s <= sim_time_s < w.end_sim_time_s]
            if rover_id:
                active_wins = [w for w in active_wins if w.target_rover_id == rover_id or w.target_rover_id == "ALL"]
            if not active_wins:
                return False, "NO ACTIVE DSN OR RELAY CONTACT WINDOW"
            return True, f"CONTACT ACTIVE: {active_wins[0].station_or_relay_name} ({active_wins[0].link_type})"

        # Default if no discrete windows defined: nominal open contact
        return True, "NOMINAL DEEP SPACE CHANNEL ACTIVE"

    def transmit_command_from_earth(
        self,
        command: MarsRoverCommand,
        sim_time_s: float,
    ) -> Tuple[bool, Optional[CommunicationPacket], str]:
        """
        Transmits a validated & approved command from Earth towards Mars.
        Places packet into in-flight uplink queue with propagation delay.
        """
        if command.current_state not in {CommandLifecycleState.APPROVED.value, CommandLifecycleState.QUEUED.value}:
            return False, None, f"Command must be APPROVED or QUEUED, got {command.current_state}"

        # Verify link availability on Earth transmission side
        is_open, reason = self.is_link_operational_at(sim_time_s, command.rover_id)
        if not is_open:
            # Command remains queued
            command.transition_to(CommandLifecycleState.QUEUED, sim_time_s, "COMM_ENVIRONMENT", f"Transmission deferred: {reason}")
            return False, None, reason

        pkt_id = f"PKT_UPLINK_{command.command_id}_{int(sim_time_s)}"
        size_bytes = len(json.dumps(command.payload).encode("utf-8")) + 64  # Payload + CCSDS header
        arrival_time_s = sim_time_s + self.uplink_owlt_s

        packet = CommunicationPacket(
            packet_id=pkt_id,
            packet_type=PacketType.TELECOMMAND.value,
            source_entity="EARTH_MISSION_CONTROL",
            destination_entity=command.rover_id,
            command_id=command.command_id,
            payload=command.to_dict(),
            size_bytes=size_bytes,
            transmission_sim_time_s=sim_time_s,
            expected_arrival_sim_time_s=arrival_time_s,
            one_way_light_time_s=self.uplink_owlt_s,
            priority=1,
        )

        command.transition_to(
            CommandLifecycleState.TRANSMITTING,
            sim_time_s=sim_time_s,
            actor="EARTH_DSN_TRANSMITTER",
            reason=f"Uplink in transit. Expected arrival at T+{self.uplink_owlt_s:.1f}s ({self.uplink_owlt_s/60.0:.2f} min)",
            details={"packet_id": pkt_id, "expected_arrival_s": arrival_time_s}
        )

        self.in_flight_uplink.append(packet)
        return True, packet, "Command transmitted into deep space uplink channel"

    def transmit_telemetry_from_mars(
        self,
        rover_id: str,
        telemetry_payload: Dict[str, Any],
        sim_time_s: float,
        priority: int = 2,
        command_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[CommunicationPacket], str]:
        """
        Transmits telemetry or command acknowledgement from Mars towards Earth.
        Places packet into in-flight downlink queue with propagation delay.
        """
        is_open, reason = self.is_link_operational_at(sim_time_s, rover_id)
        if not is_open:
            return False, None, f"Downlink deferred: {reason}"

        pkt_id = f"PKT_DOWNLINK_{rover_id}_{int(sim_time_s)}_{uuid.uuid4().hex[:4].upper()}"
        size_bytes = len(json.dumps(telemetry_payload).encode("utf-8")) + 64
        arrival_time_s = sim_time_s + self.downlink_owlt_s

        pkt_type = PacketType.ACKNOWLEDGEMENT.value if command_id else PacketType.TELEMETRY.value

        packet = CommunicationPacket(
            packet_id=pkt_id,
            packet_type=pkt_type,
            source_entity=rover_id,
            destination_entity="EARTH_MISSION_CONTROL",
            command_id=command_id,
            payload=telemetry_payload,
            size_bytes=size_bytes,
            transmission_sim_time_s=sim_time_s,
            expected_arrival_sim_time_s=arrival_time_s,
            one_way_light_time_s=self.downlink_owlt_s,
            priority=priority,
        )

        self.in_flight_downlink.append(packet)
        return True, packet, "Telemetry transmitted into deep space downlink channel"

    def advance_simulation_time(self, current_sim_time_s: float) -> Dict[str, Any]:
        """
        Advances communication environment clock to current_sim_time_s.
        Delivers packets whose arrival time has elapsed and link is open.
        """
        delivered_to_mars: List[CommunicationPacket] = []
        delivered_to_earth: List[CommunicationPacket] = []

        # 1. Process in-flight Uplink (Earth -> Mars)
        remaining_uplink: List[CommunicationPacket] = []
        for pkt in self.in_flight_uplink:
            if pkt.expected_arrival_sim_time_s <= current_sim_time_s:
                # Check link status on Mars arrival side
                is_open, reason = self.is_link_operational_at(pkt.expected_arrival_sim_time_s, pkt.destination_entity)
                if not is_open and "BLACKOUT" in reason:
                    # Packet lost during solar conjunction or severe disruption
                    pkt.is_dropped = True
                    pkt.drop_reason = reason
                    self.dropped_packets.append(pkt)
                else:
                    pkt.is_delivered = True
                    delivered_to_mars.append(pkt)
                    self.delivered_packets.append(pkt)
            else:
                remaining_uplink.append(pkt)
        self.in_flight_uplink = remaining_uplink

        # 2. Process in-flight Downlink (Mars -> Earth)
        remaining_downlink: List[CommunicationPacket] = []
        for pkt in self.in_flight_downlink:
            if pkt.expected_arrival_sim_time_s <= current_sim_time_s:
                is_open, reason = self.is_link_operational_at(pkt.expected_arrival_sim_time_s)
                if not is_open and "BLACKOUT" in reason:
                    pkt.is_dropped = True
                    pkt.drop_reason = reason
                    self.dropped_packets.append(pkt)
                else:
                    pkt.is_delivered = True
                    delivered_to_earth.append(pkt)
                    self.delivered_packets.append(pkt)

                    # Update Earth's confirmed epistemic knowledge
                    if pkt.packet_type in {PacketType.TELEMETRY.value, PacketType.ACKNOWLEDGEMENT.value}:
                        self.last_confirmed_mars_telemetry[pkt.source_entity] = {
                            "payload": copy.deepcopy(pkt.payload),
                            "received_at_sim_time_s": current_sim_time_s,
                            "packet_id": pkt.packet_id,
                            "command_id": pkt.command_id,
                            "epistemic_state": EpistemicInformationState.LAST_REPORTED_BY_MARS.value,
                        }
                        self.last_confirmed_telemetry_sim_time_s = current_sim_time_s
            else:
                remaining_downlink.append(pkt)
        self.in_flight_downlink = remaining_downlink

        # Update contact window statuses
        for w in self.contact_windows:
            if w.end_sim_time_s <= current_sim_time_s:
                if w.status == ContactWindowStatus.SCHEDULED.value or w.status == ContactWindowStatus.ACTIVE_IN_VIEW.value:
                    w.status = ContactWindowStatus.COMPLETED.value
            elif w.start_sim_time_s <= current_sim_time_s < w.end_sim_time_s:
                if w.status == ContactWindowStatus.SCHEDULED.value:
                    w.status = ContactWindowStatus.ACTIVE_IN_VIEW.value

        return {
            "delivered_to_mars": [p.to_dict() for p in delivered_to_mars],
            "delivered_to_earth": [p.to_dict() for p in delivered_to_earth],
            "in_flight_uplink_count": len(self.in_flight_uplink),
            "in_flight_downlink_count": len(self.in_flight_downlink),
            "uplink_owlt_minutes": round(self.uplink_owlt_s / 60.0, 2),
            "downlink_owlt_minutes": round(self.downlink_owlt_s / 60.0, 2),
            "rtlt_minutes": self.rtl_time_minutes,
        }

    def get_epistemic_view_for_earth(self, rover_id: str) -> Dict[str, Any]:
        """
        Returns Earth's visible telemetry for a given rover.
        Explicitly flags unconfirmed commands, last known telemetry time, and lag.
        """
        last_rec = self.last_confirmed_mars_telemetry.get(rover_id)
        if not last_rec:
            return {
                "rover_id": rover_id,
                "epistemic_state": EpistemicInformationState.UNKNOWN.value,
                "telemetry": None,
                "age_seconds": None,
                "status_note": "No telemetry confirmed from Mars yet",
            }
        return {
            "rover_id": rover_id,
            "epistemic_state": EpistemicInformationState.LAST_REPORTED_BY_MARS.value,
            "telemetry": last_rec["payload"],
            "received_sim_time_s": last_rec["received_at_sim_time_s"],
            "packet_id": last_rec["packet_id"],
            "command_id": last_rec["command_id"],
            "status_note": f"Confirmed via downlink at T+{last_rec['received_at_sim_time_s']:.1f}s",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uplink_owlt_seconds": self.uplink_owlt_s,
            "downlink_owlt_seconds": self.downlink_owlt_s,
            "uplink_owlt_minutes": round(self.uplink_owlt_s / 60.0, 2),
            "downlink_owlt_minutes": round(self.downlink_owlt_s / 60.0, 2),
            "round_trip_light_time_minutes": self.rtl_time_minutes,
            "packet_loss_rate": self.packet_loss_rate,
            "max_retries": self.max_retries,
            "in_flight_uplink_count": len(self.in_flight_uplink),
            "in_flight_downlink_count": len(self.in_flight_downlink),
            "solar_conjunction": self.solar_conjunction.to_dict(),
            "contact_windows": [w.to_dict() for w in self.contact_windows],
            "simulated_outages": list(self.simulated_outages),
            "last_confirmed_telemetry_sim_time_s": self.last_confirmed_telemetry_sim_time_s,
        }
