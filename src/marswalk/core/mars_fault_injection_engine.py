"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Deterministic Fault Injection Engine.

Provides deterministic, time-parameterized fault injection with counterfactual
isolation, multi-profile dynamics (immediate, delayed, progressive, intermittent),
and rigorous telemetry residual generation.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from marswalk.core.mars_failure_taxonomy import (
    FailureClass,
    FailureRecord,
    FailureSeverity,
    FaultProfileType,
    SymptomRecord,
)


class FaultState(str, Enum):
    """Execution lifecycle of an injected fault."""
    PENDING = "PENDING"          # Scheduled but trigger time not yet reached
    ACTIVE = "ACTIVE"            # Actively perturbing telemetry and system dynamics
    CONTAINED = "CONTAINED"      # Isolated by containment boundary; downstream blocked
    MITIGATED = "MITIGATED"      # Successfully counteracted by autonomous recovery plan
    RECOVERED = "RECOVERED"      # Cleared naturally or via reset (for recoverable faults)


@dataclass
class InjectedFaultInstance:
    """An instantiated fault on a simulation timeline."""
    instance_id: str
    record: FailureRecord
    trigger_sol: int
    trigger_time_s: float
    duration_s: Optional[float] = None
    state: FaultState = FaultState.PENDING
    current_intensity: float = 0.0   # 0.0 (nominal) to 1.0 (full effect)
    active_symptoms: List[SymptomRecord] = field(default_factory=list)
    branch_id: str = "master"        # Counterfactual branch identifier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "record": self.record.to_dict(),
            "trigger_sol": self.trigger_sol,
            "trigger_time_s": self.trigger_time_s,
            "duration_s": self.duration_s,
            "state": self.state.value,
            "current_intensity": round(self.current_intensity, 4),
            "active_symptoms": [s.to_dict() for s in self.active_symptoms],
            "branch_id": self.branch_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InjectedFaultInstance:
        inst = cls(
            instance_id=data["instance_id"],
            record=FailureRecord.from_dict(data["record"]),
            trigger_sol=int(data["trigger_sol"]),
            trigger_time_s=float(data["trigger_time_s"]),
            duration_s=data.get("duration_s"),
            state=FaultState(data.get("state", "PENDING")),
            current_intensity=float(data.get("current_intensity", 0.0)),
            branch_id=data.get("branch_id", "master"),
        )
        inst.active_symptoms = [SymptomRecord.from_dict(s) for s in data.get("active_symptoms", [])]
        return inst


class FaultInjectionEngine:
    """Deterministic fault injector supporting counterfactual simulation branches."""

    def __init__(self, branch_id: str = "master"):
        self.branch_id: str = branch_id
        self._injected_faults: Dict[str, InjectedFaultInstance] = {}
        self._execution_history: List[Dict[str, Any]] = []

    def schedule_fault(
        self,
        record: FailureRecord,
        trigger_sol: int = 1,
        trigger_time_s: float = 0.0,
        duration_s: Optional[float] = None,
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> InjectedFaultInstance:
        """Schedules a fault into this branch's injection pipeline."""
        instance_id = f"INJ-{len(self._injected_faults) + 1:03d}-{record.failure_id}"
        rec = copy.deepcopy(record)
        if custom_params:
            rec.parameters.update(custom_params)

        instance = InjectedFaultInstance(
            instance_id=instance_id,
            record=rec,
            trigger_sol=trigger_sol,
            trigger_time_s=trigger_time_s,
            duration_s=duration_s,
            state=FaultState.PENDING,
            current_intensity=0.0,
            branch_id=self.branch_id,
        )
        self._injected_faults[instance_id] = instance
        return instance

    def branch(self, new_branch_id: str) -> FaultInjectionEngine:
        """Creates an isolated counterfactual branch without mutating the parent."""
        cloned = FaultInjectionEngine(branch_id=new_branch_id)
        for k, v in self._injected_faults.items():
            cloned_instance = copy.deepcopy(v)
            cloned_instance.branch_id = new_branch_id
            cloned._injected_faults[k] = cloned_instance
        cloned._execution_history = copy.deepcopy(self._execution_history)
        return cloned

    def evaluate_at(self, sol: int, time_s: float) -> List[InjectedFaultInstance]:
        """Evaluates all scheduled faults at the given sol and simulation second."""
        active_instances: List[InjectedFaultInstance] = []

        for inst in self._injected_faults.values():
            if inst.state in (FaultState.CONTAINED, FaultState.MITIGATED):
                continue

            # Check if triggered
            if sol < inst.trigger_sol or (sol == inst.trigger_sol and time_s < inst.trigger_time_s):
                inst.state = FaultState.PENDING
                inst.current_intensity = 0.0
                inst.active_symptoms = []
                continue

            elapsed = (sol - inst.trigger_sol) * 88775.0 + (time_s - inst.trigger_time_s)

            # Check duration expiration for non-persistent
            if inst.duration_s is not None and elapsed > inst.duration_s:
                if inst.record.profile_type == FaultProfileType.IRREVERSIBLE:
                    # Irreversible physical damage persists even after injection transient ends
                    inst.state = FaultState.ACTIVE
                    inst.current_intensity = 1.0
                else:
                    inst.state = FaultState.RECOVERED
                    inst.current_intensity = 0.0
                    inst.active_symptoms = []
                    continue
            else:
                inst.state = FaultState.ACTIVE

            # Calculate intensity profile
            prof = inst.record.profile_type
            if prof == FaultProfileType.IMMEDIATE or prof == FaultProfileType.PERSISTENT or prof == FaultProfileType.IRREVERSIBLE:
                intensity = 1.0
            elif prof == FaultProfileType.DELAYED:
                delay = float(inst.record.parameters.get("delay_s", 60.0))
                intensity = 1.0 if elapsed >= delay else (elapsed / delay)
            elif prof == FaultProfileType.PROGRESSIVE:
                ramp_duration = float(inst.record.parameters.get("ramp_duration_s", 600.0))
                intensity = min(1.0, elapsed / max(1.0, ramp_duration))
            elif prof == FaultProfileType.INTERMITTENT:
                period = float(inst.record.parameters.get("period_s", 120.0))
                duty = float(inst.record.parameters.get("duty_cycle", 0.5))
                phase = (elapsed % period) / period
                intensity = 1.0 if phase < duty else 0.0
            elif prof == FaultProfileType.RECOVERABLE:
                intensity = 1.0
            else:
                intensity = 1.0

            inst.current_intensity = intensity

            # Generate synthetic physical telemetry symptoms based on active fault
            if intensity > 0.0:
                inst.active_symptoms = self._generate_symptoms(inst, sol, time_s, intensity)
                active_instances.append(inst)
            else:
                inst.active_symptoms = []

        return active_instances

    def _generate_symptoms(
        self,
        inst: InjectedFaultInstance,
        sol: int,
        time_s: float,
        intensity: float,
    ) -> List[SymptomRecord]:
        """Synthesizes high-fidelity observable telemetry symptoms from fault physics."""
        symptoms: List[SymptomRecord] = []
        fid = inst.record.failure_id
        params = inst.record.parameters

        if "MEC" in fid:
            # Mechanical stall / actuator jam
            current_surge = params.get("power_draw_surge_w", 60.0) * intensity
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel="rover.mobility.motor_fr_current_a",
                observed_value=2.4 + (current_surge / 28.0),
                expected_nominal_range=(1.8, 2.8),
                residual=current_surge / 28.0,
                unit="A",
                timestamp_sol_s=time_s,
            ))
            speed_penalty = params.get("speed_penalty_pct", 40.0) * intensity
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-02",
                telemetry_channel="rover.mobility.chassis_velocity_mps",
                observed_value=max(0.01, 0.042 * (1.0 - speed_penalty / 100.0)),
                expected_nominal_range=(0.038, 0.046),
                residual=-0.042 * (speed_penalty / 100.0),
                unit="m/s",
                timestamp_sol_s=time_s,
            ))

        elif "PWR" in fid:
            # Solar tau surge / power loss
            loss_pct = params.get("solar_loss_pct", 75.0) * intensity
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel="aircraft.power.solar_flux_wm2",
                observed_value=590.0 * (1.0 - loss_pct / 100.0),
                expected_nominal_range=(550.0, 620.0),
                residual=-590.0 * (loss_pct / 100.0),
                unit="W/m^2",
                timestamp_sol_s=time_s,
            ))
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-02",
                telemetry_channel="aircraft.battery.charge_rate_w",
                observed_value=32.0 * (1.0 - loss_pct / 100.0),
                expected_nominal_range=(28.0, 36.0),
                residual=-32.0 * (loss_pct / 100.0),
                unit="W",
                timestamp_sol_s=time_s,
            ))

        elif "COM" in fid:
            # Comm blackout / buffer fill
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel="comm.uhf.snr_db",
                observed_value=-18.5,
                expected_nominal_range=(12.0, 24.0),
                residual=-34.5,
                unit="dB",
                timestamp_sol_s=time_s,
            ))
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-02",
                telemetry_channel="rover.avionics.flash_buffer_used_mb",
                observed_value=params.get("buffer_overflow_risk_mb", 350.0) * intensity,
                expected_nominal_range=(20.0, 150.0),
                residual=250.0 * intensity,
                unit="MB",
                timestamp_sol_s=time_s,
            ))

        elif "AER" in fid:
            # Rotorcraft lift deficit & motor surge
            lift_deficit = params.get("lift_deficit_pct", 20.0) * intensity
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel="aircraft.flight.rotor_thrust_n",
                observed_value=18.0 * (1.0 - lift_deficit / 100.0),
                expected_nominal_range=(17.5, 22.0),
                residual=-18.0 * (lift_deficit / 100.0),
                unit="N",
                timestamp_sol_s=time_s,
            ))
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-02",
                telemetry_channel="aircraft.propulsion.motor_temp_c",
                observed_value=58.0 + (35.0 * intensity),
                expected_nominal_range=(10.0, 55.0),
                residual=35.0 * intensity,
                unit="degC",
                timestamp_sol_s=time_s,
            ))

        elif "SCI" in fid:
            # Instrument calibration drift
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel="rover.payload.pixl_drift_kev",
                observed_value=params.get("energy_drift_kev", 0.18) * intensity,
                expected_nominal_range=(-0.02, 0.02),
                residual=params.get("energy_drift_kev", 0.18) * intensity,
                unit="keV",
                timestamp_sol_s=time_s,
            ))

        else:
            # Generic telemetry deviation
            symptoms.append(SymptomRecord(
                symptom_id=f"SYM-{inst.instance_id}-01",
                telemetry_channel=f"{inst.record.target_asset.lower()}.subsystem_status",
                observed_value=0.0,
                expected_nominal_range=(1.0, 1.0),
                residual=-1.0 * intensity,
                unit="state",
                timestamp_sol_s=time_s,
            ))

        return symptoms

    def get_all_faults(self) -> List[InjectedFaultInstance]:
        return list(self._injected_faults.values())

    def clear(self) -> None:
        self._injected_faults.clear()
        self._execution_history.clear()
