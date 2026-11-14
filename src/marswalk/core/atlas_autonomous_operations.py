"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Deep-Space Autonomy & Asynchronous Communication Loop.

Models interplanetary one-way light-time (OWLT 3–22 minutes), command uplink
buffers, downlink telemetry lag, and cryptographic state-hash verification to prevent
stale-command execution on Mars.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .atlas_mission_contracts import CommandPacket, CommandState, CommLinkStatus

SPEED_OF_LIGHT_KM_S = 299792.458
AU_TO_KM = 149597870.7


def calculate_owlt_seconds(distance_au: float) -> float:
    """Calculate exact one-way light-time in seconds from Earth-Mars orbital distance."""
    distance_km = distance_au * AU_TO_KM
    return round(distance_km / SPEED_OF_LIGHT_KM_S, 2)


class DeepSpaceAutonomyManager:
    """Coordinates interplanetary command buffering, light-time delays, and onboard validation."""

    def __init__(self, earth_mars_distance_au: float = 1.708) -> None:
        self.distance_au = earth_mars_distance_au
        self.owlt_seconds = calculate_owlt_seconds(earth_mars_distance_au)  # ~852.0 s (14.2 min)
        self.uplink_buffer: List[CommandPacket] = []
        self.executed_commands: List[CommandPacket] = []
        self.rejected_commands: List[CommandPacket] = []

    def queue_earth_command(
        self,
        command_id: str,
        target_asset_id: str,
        action: str,
        parameters: Dict[str, Any],
        expected_state_hash: str,
        created_met_seconds: float,
        dispatch_sol: int = 1,
    ) -> CommandPacket:
        """Queue a command packet at Earth Mission Control with the currently known state signature."""
        cmd = CommandPacket(
            command_id=command_id,
            target_asset_id=target_asset_id,
            command_action=action,
            parameters=parameters,
            created_met_seconds=created_met_seconds,
            expected_state_hash=expected_state_hash,
            state=CommandState.UPLINK_QUEUED,
            one_way_light_time_seconds=self.owlt_seconds,
            dispatch_timestamp_sol=dispatch_sol,
        )
        self.uplink_buffer.append(cmd)
        return cmd

    def process_uplinks_on_mars(
        self,
        current_mars_met_seconds: float,
        current_mars_state_hash: str,
    ) -> List[CommandPacket]:
        """Evaluate in-transit commands arriving at Mars. Validate state hash before execution."""
        processed: List[CommandPacket] = []
        remaining_buffer: List[CommandPacket] = []

        for cmd in self.uplink_buffer:
            arrival_met = cmd.created_met_seconds + self.owlt_seconds
            if current_mars_met_seconds >= arrival_met:
                # Command has reached Mars surface receiver
                if cmd.expected_state_hash == current_mars_state_hash:
                    # Validated: State matches what Earth planned against
                    cmd.state = CommandState.EXECUTED
                    cmd.execution_result = "SUCCESS_ONBOARD_VALIDATED"
                    self.executed_commands.append(cmd)
                else:
                    # Stale state rejection: Mars conditions drifted during the 14.2 min transit
                    cmd.state = CommandState.REJECTED_STALE_HASH
                    cmd.execution_result = (
                        f"REJECTED: Expected hash '{cmd.expected_state_hash[:8]}...' "
                        f"does not match live Mars state hash '{current_mars_state_hash[:8]}...'."
                    )
                    self.rejected_commands.append(cmd)
                processed.append(cmd)
            else:
                cmd.state = CommandState.IN_TRANSIT
                remaining_buffer.append(cmd)

        self.uplink_buffer = remaining_buffer
        return processed

    def get_comm_link_status(self, source_id: str = "EARTH_MCC", target_id: str = "SURFACE-COMM-MAST-01") -> CommLinkStatus:
        """Query real-time RF link parameters across the interplanetary void."""
        return CommLinkStatus(
            link_id=f"LINK-{source_id}-{target_id}",
            source_id=source_id,
            target_id=target_id,
            is_line_of_sight=True,
            elevation_angle_deg=42.5,
            signal_to_noise_ratio_db=18.4,
            bandwidth_kbps=2500.0,
            owlt_seconds=self.owlt_seconds,
            active_relay_id="MRO-ORBITER",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "earth_mars_distance_au": self.distance_au,
            "owlt_seconds": self.owlt_seconds,
            "owlt_minutes": round(self.owlt_seconds / 60.0, 2),
            "pending_uplinks_count": len(self.uplink_buffer),
            "executed_count": len(self.executed_commands),
            "rejected_count": len(self.rejected_commands),
        }
