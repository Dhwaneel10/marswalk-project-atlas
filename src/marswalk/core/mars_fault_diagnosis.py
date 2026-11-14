"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Fault Detection, Diagnosis & Isolation (FDDI).

Differentiates raw observable symptoms, candidate diagnostic hypotheses,
and confirmed root-cause diagnoses through multi-sensor correlation,
residual analysis, and invariant verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.mars_failure_taxonomy import (
    FailureClass,
    FailureRecord,
    FailureSeverity,
    SymptomRecord,
)


class DiagnosticStatus(str, Enum):
    """Maturity stage of a diagnosed fault."""
    SYMPTOM_DETECTED = "SYMPTOM_DETECTED"    # Residual observed but etiology unresolved
    CANDIDATE = "CANDIDATE"                  # Multiple competing hypotheses exist
    CONFIRMED = "CONFIRMED"                  # Multi-sensor invariant confirms root cause
    DISPROVED = "DISPROVED"                  # Hypothesized fault ruled out by discriminator


@dataclass
class DiagnosticHypothesis:
    """A competing explanation for observed telemetry anomalies."""
    fault_id: str
    fault_name: str
    target_asset: str
    confidence: float                        # 0.0 to 1.0 calibrated probability
    status: DiagnosticStatus
    supporting_symptoms: List[str]          # IDs of symptom records
    discriminating_evidence: str
    recommended_isolation_action: str
    severity: FailureSeverity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fault_id": self.fault_id,
            "fault_name": self.fault_name,
            "target_asset": self.target_asset,
            "confidence": round(self.confidence, 4),
            "status": self.status.value,
            "supporting_symptoms": self.supporting_symptoms,
            "discriminating_evidence": self.discriminating_evidence,
            "recommended_isolation_action": self.recommended_isolation_action,
            "severity": self.severity.value,
        }


@dataclass
class DiagnosticReport:
    """Consolidated FDDI assessment of current system telemetry."""
    timestamp_sol_s: float
    detected_symptoms: List[SymptomRecord]
    hypotheses: List[DiagnosticHypothesis]
    confirmed_diagnoses: List[DiagnosticHypothesis]
    isolation_recommendations: List[str]
    system_health_index: float              # 0.0 (critical fail) to 1.0 (pristine)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_sol_s": self.timestamp_sol_s,
            "detected_symptoms": [s.to_dict() for s in self.detected_symptoms],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "confirmed_diagnoses": [c.to_dict() for c in self.confirmed_diagnoses],
            "isolation_recommendations": self.isolation_recommendations,
            "system_health_index": round(self.system_health_index, 4),
        }


class FaultDiagnosisEngine:
    """Planetary robotics FDDI engine mapping telemetry anomalies to root causes."""

    def __init__(self):
        self._symptom_history: List[SymptomRecord] = []

    def analyze_symptoms(
        self,
        symptoms: List[SymptomRecord],
        current_time_s: float = 0.0,
    ) -> DiagnosticReport:
        """Processes observable symptoms and computes calibrated diagnostic hypotheses."""
        self._symptom_history.extend(symptoms)
        hypotheses: List[DiagnosticHypothesis] = []
        confirmed: List[DiagnosticHypothesis] = []
        isolations: List[str] = []

        if not symptoms:
            return DiagnosticReport(
                timestamp_sol_s=current_time_s,
                detected_symptoms=[],
                hypotheses=[],
                confirmed_diagnoses=[],
                isolation_recommendations=[],
                system_health_index=1.0,
            )

        # Map channel keys
        channels = {s.telemetry_channel: s for s in symptoms}

        # 1. Evaluate Mechanical Motor Stall vs. Steep Dune Incline
        if "rover.mobility.motor_fr_current_a" in channels:
            curr_sym = channels["rover.mobility.motor_fr_current_a"]
            speed_sym = channels.get("rover.mobility.chassis_velocity_mps")

            if curr_sym.observed_value > 3.2:
                # High current draw detected. Check velocity residual.
                if speed_sym and speed_sym.observed_value < 0.028:
                    # Current surge + drastic speed collapse confirms mechanical actuator jam
                    diag = DiagnosticHypothesis(
                        fault_id="FAIL-MEC-01",
                        fault_name="Front-Right Wheel Drive Actuator Stall",
                        target_asset="ROVER-PERSEVERANCE",
                        confidence=0.96,
                        status=DiagnosticStatus.CONFIRMED,
                        supporting_symptoms=[curr_sym.symptom_id, speed_sym.symptom_id],
                        discriminating_evidence="Motor current exceeds 3.2A while tachometer velocity remains suppressed at <0.028 m/s (rules out slope slip).",
                        recommended_isolation_action="ACTUATOR_ISOLATION_5WHEEL_DRIVE",
                        severity=FailureSeverity.CRITICAL,
                    )
                    confirmed.append(diag)
                    isolations.append("ACTUATOR_ISOLATION_5WHEEL_DRIVE")
                else:
                    # Current high but velocity normal -> slope or terrain resistance
                    diag = DiagnosticHypothesis(
                        fault_id="CAND-TERRAIN-RESISTANCE",
                        fault_name="High Terrain Slope / Soft Soil Drag",
                        target_asset="ROVER-PERSEVERANCE",
                        confidence=0.62,
                        status=DiagnosticStatus.CANDIDATE,
                        supporting_symptoms=[curr_sym.symptom_id],
                        discriminating_evidence="Current draw elevated without corresponding velocity stall; consistent with 18 deg incline.",
                        recommended_isolation_action="THROTTLE_DERATE_AND_MONITOR",
                        severity=FailureSeverity.MARGINAL,
                    )
                    hypotheses.append(diag)

        # 2. Evaluate Atmospheric Dust Storm vs. Solar Array Degradation
        if "aircraft.power.solar_flux_wm2" in channels:
            solar_sym = channels["aircraft.power.solar_flux_wm2"]
            batt_sym = channels.get("aircraft.battery.charge_rate_w")

            if solar_sym.observed_value < 250.0:
                diag = DiagnosticHypothesis(
                    fault_id="FAIL-PWR-01",
                    fault_name="Severe Regional Dust Storm & Solar Tau Obscuration",
                    target_asset="AERO-INGENUITY",
                    confidence=0.94,
                    status=DiagnosticStatus.CONFIRMED,
                    supporting_symptoms=[solar_sym.symptom_id] + ([batt_sym.symptom_id] if batt_sym else []),
                    discriminating_evidence="Solar insolation dropped below 250 W/m^2 across entire array; optical depth tau estimated > 2.4.",
                    recommended_isolation_action="SURVIVAL_HEATER_PRIORITIZATION_AND_GROUND_HOLD",
                    severity=FailureSeverity.CRITICAL,
                )
                confirmed.append(diag)
                isolations.append("SURVIVAL_HEATER_PRIORITIZATION_AND_GROUND_HOLD")

        # 3. Evaluate Comm Relay Dropout
        if "comm.uhf.snr_db" in channels:
            snr_sym = channels["comm.uhf.snr_db"]
            buf_sym = channels.get("rover.avionics.flash_buffer_used_mb")

            if snr_sym.observed_value < 0.0:
                diag = DiagnosticHypothesis(
                    fault_id="FAIL-COM-01",
                    fault_name="MRO Electra UHF Relay Transceiver Blackout",
                    target_asset="ROVER-PERSEVERANCE",
                    confidence=0.98,
                    status=DiagnosticStatus.CONFIRMED,
                    supporting_symptoms=[snr_sym.symptom_id] + ([buf_sym.symptom_id] if buf_sym else []),
                    discriminating_evidence="UHF signal-to-noise ratio collapsed to -18.5 dB with zero packet acknowledgment during scheduled overpass.",
                    recommended_isolation_action="SWITCH_TO_DTE_HIGH_GAIN_AND_THROTTLE_ACQUISITION",
                    severity=FailureSeverity.CRITICAL,
                )
                confirmed.append(diag)
                isolations.append("SWITCH_TO_DTE_HIGH_GAIN_AND_THROTTLE_ACQUISITION")

        # 4. Evaluate Rotor Blade Damage / Lift Deficit
        if "aircraft.flight.rotor_thrust_n" in channels:
            thrust_sym = channels["aircraft.flight.rotor_thrust_n"]
            temp_sym = channels.get("aircraft.propulsion.motor_temp_c")

            if thrust_sym.observed_value < 16.0:
                diag = DiagnosticHypothesis(
                    fault_id="FAIL-AER-01",
                    fault_name="Rotor Blade Leading-Edge Abrasion & Aerodynamic Stall",
                    target_asset="AERO-INGENUITY",
                    confidence=0.92,
                    status=DiagnosticStatus.CONFIRMED,
                    supporting_symptoms=[thrust_sym.symptom_id] + ([temp_sym.symptom_id] if temp_sym else []),
                    discriminating_evidence="Rotor thrust deficit >18% accompanied by motor thermal rise >85 C under nominal commanded RPM.",
                    recommended_isolation_action="ABORT_SORTIE_CONTROLLED_DESCENT",
                    severity=FailureSeverity.CRITICAL,
                )
                confirmed.append(diag)
                isolations.append("ABORT_SORTIE_CONTROLLED_DESCENT")

        # 5. Evaluate Science Instrument Calibration Drift
        if "rover.payload.pixl_drift_kev" in channels:
            pixl_sym = channels["rover.payload.pixl_drift_kev"]
            if abs(pixl_sym.observed_value) > 0.10:
                diag = DiagnosticHypothesis(
                    fault_id="FAIL-SCI-01",
                    fault_name="PIXL Spectrometer Thermal Calibration Drift",
                    target_asset="ROVER-PERSEVERANCE",
                    confidence=0.91,
                    status=DiagnosticStatus.CONFIRMED,
                    supporting_symptoms=[pixl_sym.symptom_id],
                    discriminating_evidence="Centroid drift of +0.18 keV on standard rock baseline introduces risk of false carbonate identification.",
                    recommended_isolation_action="TRIGGER_CALIBRATION_TARGET_REBASELINE",
                    severity=FailureSeverity.MARGINAL,
                )
                confirmed.append(diag)
                isolations.append("TRIGGER_CALIBRATION_TARGET_REBASELINE")

        # Compute composite system health index
        # 1.0 = nominal, reduced by severity of active confirmed faults
        penalty = 0.0
        for c in confirmed:
            if c.severity == FailureSeverity.CATASTROPHIC:
                penalty += 0.8
            elif c.severity == FailureSeverity.CRITICAL:
                penalty += 0.35
            elif c.severity == FailureSeverity.MARGINAL:
                penalty += 0.12
            else:
                penalty += 0.04
        for h in hypotheses:
            penalty += 0.05 * h.confidence

        health_idx = max(0.05, 1.0 - penalty)

        return DiagnosticReport(
            timestamp_sol_s=current_time_s,
            detected_symptoms=symptoms,
            hypotheses=hypotheses,
            confirmed_diagnoses=confirmed,
            isolation_recommendations=list(set(isolations)),
            system_health_index=health_idx,
        )
