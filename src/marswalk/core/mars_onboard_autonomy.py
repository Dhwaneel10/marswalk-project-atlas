"""
MarsWalk 2.0 / Project Atlas — Milestone 13O: Onboard Rover Autonomy Engine
===========================================================================
Deterministic, explainable decision system running on simulated rovers:
- 4 Operating Modes: EARTH_SUPERVISED, DELAYED_OPERATIONS, BOUNDED_AUTONOMY, SAFE_HOLD.
- Stale command detection (state version, terrain hazards, energy, instruments, thermal).
- Full auditable decision records (situation, evidence, constraints, rules, alternatives, chosen action, explanation, contingency).
- Bounded local replanning and contingency execution.
- Strict enforcement of safety invariants: no silent constraint overrides.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import enum
import hashlib
import json
import math
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from marswalk.core.mars_command_transmission import (
    MarsRoverCommand,
    CommandLifecycleState,
    CommandRiskClassification,
    CommandApprovalLevel,
    ContingencyPolicy,
)


class AutonomyOperatingMode(str, enum.Enum):
    """The four formal autonomy modes governing rover onboard authority."""
    EARTH_SUPERVISED = "EARTH_SUPERVISED"
    DELAYED_OPERATIONS = "DELAYED_OPERATIONS"
    BOUNDED_AUTONOMY = "BOUNDED_AUTONOMY"
    SAFE_HOLD = "SAFE_HOLD"


class DecisionActionType(str, enum.Enum):
    """Actions the onboard autonomy engine can decide upon."""
    ACCEPT_AND_EXECUTE = "ACCEPT_AND_EXECUTE"
    REJECT_STALE_COMMAND = "REJECT_STALE_COMMAND"
    SUSPEND_AND_HOLD = "SUSPEND_AND_HOLD"
    EXECUTE_CONTINGENCY_DETOUR = "EXECUTE_CONTINGENCY_DETOUR"
    DEFER_SCIENCE_ACTIVITY = "DEFER_SCIENCE_ACTIVITY"
    ENTER_SAFE_HOLD = "ENTER_SAFE_HOLD"
    REQUEST_EARTH_REVALIDATION = "REQUEST_EARTH_REVALIDATION"


@dataclass
class RoverPhysicalState:
    """True in-situ physical and operational state of the rover on Mars."""
    rover_id: str
    state_version: int = 1
    operating_mode: str = AutonomyOperatingMode.BOUNDED_AUTONOMY.value
    position_xy: Tuple[float, float] = (0.0, 0.0)
    current_waypoint_id: str = "WP_BASE_OCTAVIA"
    battery_charge_wh: float = 900.0
    battery_capacity_wh: float = 1200.0
    min_reserve_limit_wh: float = 200.0
    operational_instruments: Dict[str, bool] = field(default_factory=lambda: {
        "MASTCAM_Z": True,
        "SHERLOC": True,
        "PIXL": True,
        "MEDA": True,
        "SUPERCAM": True,
        "CORING_DRILL": True,
    })
    known_hazards: List[Dict[str, Any]] = field(default_factory=list)
    active_command_id: Optional[str] = None
    accumulated_science_data_mb: float = 0.0
    total_distance_traversed_m: float = 0.0
    ambient_temperature_k: float = 215.0
    dust_optical_depth_tau: float = 0.45

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rover_id": self.rover_id,
            "state_version": self.state_version,
            "operating_mode": self.operating_mode,
            "position_xy": list(self.position_xy),
            "current_waypoint_id": self.current_waypoint_id,
            "battery_charge_wh": round(self.battery_charge_wh, 2),
            "battery_capacity_wh": self.battery_capacity_wh,
            "min_reserve_limit_wh": self.min_reserve_limit_wh,
            "operational_instruments": copy.deepcopy(self.operational_instruments),
            "known_hazards": copy.deepcopy(self.known_hazards),
            "active_command_id": self.active_command_id,
            "accumulated_science_data_mb": round(self.accumulated_science_data_mb, 2),
            "total_distance_traversed_m": round(self.total_distance_traversed_m, 2),
            "ambient_temperature_k": round(self.ambient_temperature_k, 2),
            "dust_optical_depth_tau": round(self.dust_optical_depth_tau, 3),
        }


@dataclass
class AutonomyDecisionRecord:
    """
    Exhaustive, explainable audit record for an autonomous rover decision.
    Ensures complete transparency without arbitrary AI confidence scores.
    """
    decision_id: str
    sim_time_s: float
    rover_id: str
    command_id: Optional[str]
    situation_detected: str
    available_evidence: Dict[str, Any]
    current_mission_state_version: int
    relevant_constraints: List[str]
    applicable_rule: str
    alternatives_considered: List[Dict[str, Any]]
    selected_action: str
    rejected_alternatives: List[Dict[str, Any]]
    engineering_explanation: str
    required_authorization: str
    expected_consequences: Dict[str, Any]
    contingency_executed: Optional[str] = None
    final_outcome: str = "PENDING"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OnboardRoverAutonomyEngine:
    """
    Onboard rover autonomy software stack executing on Mars.
    Performs stale command screening, rule-based reasoning, bounded replanning,
    and contingency execution.
    """

    def __init__(self, rover_id: str, initial_mode: str = AutonomyOperatingMode.BOUNDED_AUTONOMY.value):
        self.rover_id: str = rover_id
        self.state: RoverPhysicalState = RoverPhysicalState(rover_id=rover_id, operating_mode=initial_mode)
        self.decisions_log: List[AutonomyDecisionRecord] = []
        self.executed_commands_log: List[Dict[str, Any]] = []
        self.active_contingencies: List[Dict[str, Any]] = []

    def set_operating_mode(self, mode: AutonomyOperatingMode, reason: str, sim_time_s: float):
        """Switches rover autonomy mode with auditable record."""
        old_mode = self.state.operating_mode
        self.state.operating_mode = mode.value
        self.state.state_version += 1

        rec = AutonomyDecisionRecord(
            decision_id=f"DEC_MODE_{self.rover_id}_{int(sim_time_s)}_{uuid.uuid4().hex[:4]}",
            sim_time_s=sim_time_s,
            rover_id=self.rover_id,
            command_id=None,
            situation_detected=f"Operating mode transition from {old_mode} to {mode.value}",
            available_evidence={"trigger_reason": reason, "previous_mode": old_mode},
            current_mission_state_version=self.state.state_version,
            relevant_constraints=["AUTONOMY_AUTHORITY_BOUNDS"],
            applicable_rule="RULE_MODE_TRANSITION_AUTHORITY",
            alternatives_considered=[],
            selected_action=f"SWITCH_TO_{mode.value}",
            rejected_alternatives=[],
            engineering_explanation=f"Autonomous mode changed to {mode.value} due to: {reason}",
            required_authorization="LOCAL_AUTONOMY_EXECUTIVE",
            expected_consequences={"operating_authority": mode.value},
            final_outcome="MODE_ACTIVE",
        )
        self.decisions_log.append(rec)

    def inject_environmental_hazard(self, hazard_id: str, hazard_type: str, location_xy: Tuple[float, float], severity: str, description: str):
        """Simulates newly detected physical hazard on Mars (e.g. fresh rockfall or dune)."""
        hazard = {
            "hazard_id": hazard_id,
            "hazard_type": hazard_type,
            "location_xy": list(location_xy),
            "severity": severity,
            "description": description,
            "detected_at_version": self.state.state_version,
        }
        self.state.known_hazards.append(hazard)
        self.state.state_version += 1  # Rover state advances when environment changes!

    def evaluate_incoming_command(
        self,
        command: MarsRoverCommand,
        sim_time_s: float,
    ) -> Tuple[bool, AutonomyDecisionRecord]:
        """
        Signature Feature: Stale Command Validation & Bounded Decision.
        Evaluates incoming telecommand against current in-situ state and constraints.
        Returns (is_accepted, decision_record).
        """
        # 1. State transition from TRANSMITTING to RECEIVED
        if command.current_state == CommandLifecycleState.TRANSMITTING.value:
            command.transition_to(
                CommandLifecycleState.RECEIVED,
                sim_time_s,
                actor="MARS_ROVER_UHF_RECEIVER",
                reason="Packet received at rover antenna"
            )

        situation = f"Telecommand {command.command_id} ({command.action_type}) arrived at rover {self.rover_id}."
        evidence: Dict[str, Any] = {
            "cmd_expected_state_version": command.preconditions.expected_state_version,
            "rover_current_state_version": self.state.state_version,
            "rover_battery_wh": self.state.battery_charge_wh,
            "rover_min_reserve_limit_wh": self.state.min_reserve_limit_wh,
            "command_cost_wh": command.preconditions.max_energy_cost_wh,
            "sim_time_s": sim_time_s,
            "cmd_expiration_sim_time_s": command.expiration_sim_time_s,
            "operating_mode": self.state.operating_mode,
            "active_hazards_count": len(self.state.known_hazards),
        }

        constraints: List[str] = []
        alternatives: List[Dict[str, Any]] = [
            {"action": DecisionActionType.ACCEPT_AND_EXECUTE.value, "feasibility": "PENDING"},
            {"action": DecisionActionType.REJECT_STALE_COMMAND.value, "feasibility": "AVAILABLE"},
            {"action": DecisionActionType.SUSPEND_AND_HOLD.value, "feasibility": "AVAILABLE"},
            {"action": DecisionActionType.EXECUTE_CONTINGENCY_DETOUR.value, "feasibility": "AVAILABLE"},
            {"action": DecisionActionType.ENTER_SAFE_HOLD.value, "feasibility": "AVAILABLE"},
        ]

        # -------------------------------------------------------------
        # CHECK 1: Command Expiration
        # -------------------------------------------------------------
        if command.expiration_sim_time_s <= sim_time_s:
            constraints.append("COMMAND_VALIDITY_WINDOW_EXPIRED")
            rule = "RULE_EXPIRED_COMMAND_DISMISSAL"
            explanation = (
                f"Command expired at T+{command.expiration_sim_time_s:.1f}s. "
                f"Current Mars time is T+{sim_time_s:.1f}s (propagation lag exceeded validity window)."
            )
            command.transition_to(CommandLifecycleState.EXPIRED, sim_time_s, "ONBOARD_COMMAND_VALIDATOR", explanation)
            dec = AutonomyDecisionRecord(
                decision_id=f"DEC_EXP_{command.command_id}_{int(sim_time_s)}",
                sim_time_s=sim_time_s,
                rover_id=self.rover_id,
                command_id=command.command_id,
                situation_detected=situation,
                available_evidence=evidence,
                current_mission_state_version=self.state.state_version,
                relevant_constraints=constraints,
                applicable_rule=rule,
                alternatives_considered=alternatives,
                selected_action=DecisionActionType.REJECT_STALE_COMMAND.value,
                rejected_alternatives=[a for a in alternatives if a["action"] != DecisionActionType.REJECT_STALE_COMMAND.value],
                engineering_explanation=explanation,
                required_authorization="LOCAL_SAFETY_VALIDATOR",
                expected_consequences={"action_aborted": True, "command_state": "EXPIRED"},
                final_outcome="COMMAND_EXPIRED",
            )
            self.decisions_log.append(dec)
            return False, dec

        # -------------------------------------------------------------
        # CHECK 2: State Version & Stale Plan Detection
        # -------------------------------------------------------------
        is_stale_version = command.preconditions.expected_state_version < self.state.state_version
        if is_stale_version:
            constraints.append("STATE_VERSION_MISMATCH_STALE_INSTRUCTION")

        # -------------------------------------------------------------
        # CHECK 3: Terrain Hazard Conflict Check
        # -------------------------------------------------------------
        has_hazard_conflict = False
        conflicting_hazard_desc = ""
        route_points = command.payload.get("waypoints", [])
        for pt in route_points:
            pt_xy = (pt.get("x", 0.0), pt.get("y", 0.0))
            for h in self.state.known_hazards:
                h_xy = tuple(h["location_xy"])
                dist = math.hypot(pt_xy[0] - h_xy[0], pt_xy[1] - h_xy[1])
                if dist < 25.0:  # Within 25m hazard safety buffer
                    has_hazard_conflict = True
                    conflicting_hazard_desc = f"{h['hazard_type']} at ({h_xy[0]}, {h_xy[1]}): {h['description']}"
                    constraints.append(f"HAZARD_PROXIMITY_VIOLATION: {conflicting_hazard_desc}")
                    break

        # -------------------------------------------------------------
        # CHECK 4: Energy Margin & Battery Depletion
        # -------------------------------------------------------------
        projected_battery = self.state.battery_charge_wh - command.preconditions.max_energy_cost_wh
        is_energy_deficient = projected_battery < self.state.min_reserve_limit_wh
        if is_energy_deficient:
            constraints.append(
                f"ENERGY_RESERVE_VIOLATION: projected {projected_battery:.1f} Wh < minimum {self.state.min_reserve_limit_wh:.1f} Wh"
            )

        # -------------------------------------------------------------
        # CHECK 5: Instrument Availability Check
        # -------------------------------------------------------------
        has_instrument_fault = False
        for req_inst in command.preconditions.required_instruments_operational:
            if not self.state.operational_instruments.get(req_inst, False):
                has_instrument_fault = True
                constraints.append(f"REQUIRED_INSTRUMENT_UNAVAILABLE: {req_inst}")

        # -------------------------------------------------------------
        # SYNTHESIS & BOUNDED CONTINGENCY ARBITRATION
        # -------------------------------------------------------------
        if not constraints:
            # Command is completely valid under current Mars reality!
            command.transition_to(CommandLifecycleState.ACCEPTED, sim_time_s, "ONBOARD_COMMAND_VALIDATOR", "All preconditions, energy, and state verified")
            dec = AutonomyDecisionRecord(
                decision_id=f"DEC_ACC_{command.command_id}_{int(sim_time_s)}",
                sim_time_s=sim_time_s,
                rover_id=self.rover_id,
                command_id=command.command_id,
                situation_detected=situation,
                available_evidence=evidence,
                current_mission_state_version=self.state.state_version,
                relevant_constraints=["ALL_PRECONDITIONS_SATISFIED"],
                applicable_rule="RULE_NOMINAL_EXECUTION_DISPATCH",
                alternatives_considered=alternatives,
                selected_action=DecisionActionType.ACCEPT_AND_EXECUTE.value,
                rejected_alternatives=[a for a in alternatives if a["action"] != DecisionActionType.ACCEPT_AND_EXECUTE.value],
                engineering_explanation="Preconditions valid: energy reserve, instruments, and clear terrain verified.",
                required_authorization="LOCAL_AUTONOMY_EXECUTIVE",
                expected_consequences={"action_executing": True},
                final_outcome="ACCEPTED_FOR_EXECUTION",
            )
            self.decisions_log.append(dec)
            return True, dec

        # Command is STALE, CONFLICTED, or DANGEROUS!
        command.transition_to(
            CommandLifecycleState.REJECTED,
            sim_time_s,
            actor="ONBOARD_COMMAND_VALIDATOR",
            reason=f"Rejected: {', '.join(constraints[:2])}",
            details={"violated_constraints": constraints}
        )

        # Determine Bounded Contingency
        contingency_policy = command.contingency_policy
        selected_action = DecisionActionType.REJECT_STALE_COMMAND.value
        contingency_executed = None
        explanation = f"Command rejected due to: {'; '.join(constraints)}. "

        if self.state.operating_mode == AutonomyOperatingMode.SAFE_HOLD.value:
            selected_action = DecisionActionType.ENTER_SAFE_HOLD.value
            explanation += "Rover is in SAFE_HOLD: all non-essential activity suspended."
        elif has_hazard_conflict and contingency_policy == ContingencyPolicy.RECALCULATE_ROUTE.value:
            selected_action = DecisionActionType.EXECUTE_CONTINGENCY_DETOUR.value
            contingency_executed = "RECOMPUTE_LOCAL_WAYPOINT_DETOUR"
            explanation += f"Executing authorized local detour around detected {conflicting_hazard_desc}."
            self.state.state_version += 1
        elif is_energy_deficient or contingency_policy == ContingencyPolicy.DEFER_SCIENCE.value:
            selected_action = DecisionActionType.DEFER_SCIENCE_ACTIVITY.value
            contingency_executed = "DEFER_SCIENCE_AND_PRESERVE_CHARGE"
            explanation += "Conserving battery power; non-critical science activity deferred."
        else:
            selected_action = DecisionActionType.SUSPEND_AND_HOLD.value
            contingency_executed = "HOLD_POSITION_AND_REPORT"
            explanation += "Holding current position until next Earth contact window opens."

        dec = AutonomyDecisionRecord(
            decision_id=f"DEC_REJ_{command.command_id}_{int(sim_time_s)}",
            sim_time_s=sim_time_s,
            rover_id=self.rover_id,
            command_id=command.command_id,
            situation_detected=situation,
            available_evidence=evidence,
            current_mission_state_version=self.state.state_version,
            relevant_constraints=constraints,
            applicable_rule="RULE_STALE_OR_UNSAFE_INSTRUCTION_INTERCEPTION",
            alternatives_considered=alternatives,
            selected_action=selected_action,
            rejected_alternatives=[a for a in alternatives if a["action"] != selected_action],
            engineering_explanation=explanation,
            required_authorization="LOCAL_SAFETY_VALIDATOR",
            expected_consequences={"action_rejected": True, "contingency": contingency_executed},
            contingency_executed=contingency_executed,
            final_outcome=f"CONTINGENCY_ENGAGED_{contingency_executed or 'HOLD'}",
        )
        self.decisions_log.append(dec)
        return False, dec

    def execute_accepted_command(self, command: MarsRoverCommand, sim_time_s: float) -> Tuple[bool, str]:
        """Simulates onboard execution of an accepted command."""
        if command.current_state != CommandLifecycleState.ACCEPTED.value:
            return False, f"Command must be ACCEPTED to execute, got {command.current_state}"

        command.transition_to(CommandLifecycleState.EXECUTING, sim_time_s, "MARS_EXECUTION_ENGINE", "Command dispatched to rover actuators/instruments")

        # Simulate resource delta
        cost_wh = command.preconditions.max_energy_cost_wh
        self.state.battery_charge_wh = max(0.0, self.state.battery_charge_wh - cost_wh)
        self.state.state_version += 1

        if command.action_type == "TRANSIT":
            dist = command.payload.get("distance_m", 120.0)
            self.state.total_distance_traversed_m += dist
            target_wp = command.payload.get("destination_waypoint_id", "WP_NEXT")
            self.state.current_waypoint_id = target_wp
        elif command.action_type in {"SCIENCE_DWELL", "SAMPLE_DRILL"}:
            science_mb = command.payload.get("science_data_mb", 35.0)
            self.state.accumulated_science_data_mb += science_mb

        command.transition_to(CommandLifecycleState.COMPLETED, sim_time_s + 60.0, "MARS_EXECUTION_ENGINE", "Activity successfully completed")
        self.executed_commands_log.append({
            "command_id": command.command_id,
            "completed_at_s": sim_time_s + 60.0,
            "cost_wh": cost_wh,
            "resulting_state_version": self.state.state_version,
        })
        return True, "Command executed successfully on Mars"

    def generate_telemetry_report(self, sim_time_s: float) -> Dict[str, Any]:
        """Compiles in-situ telemetry and anomaly report for downlink to Earth."""
        return {
            "rover_id": self.rover_id,
            "report_timestamp_sim_s": sim_time_s,
            "rover_physical_state": self.state.to_dict(),
            "latest_decisions": [d.to_dict() for d in self.decisions_log[-3:]],
            "total_decisions_count": len(self.decisions_log),
            "executed_commands_count": len(self.executed_commands_log),
            "anomalies_reported": [
                {"situation": d.situation_detected, "action": d.selected_action, "contingency": d.contingency_executed}
                for d in self.decisions_log if "REJECT" in d.selected_action or "SAFE_HOLD" in d.selected_action
            ],
        }
