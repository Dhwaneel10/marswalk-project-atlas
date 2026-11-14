"""MarsWalk 2.0 / Project Atlas  Milestone 13R: Failure Taxonomy Framework.

Defines formal planetary robotics failure classes, severity criteria,
fault profiles, observable symptoms, and failure record schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FailureClass(str, Enum):
    """Seven core planetary robotics failure domains."""
    MECHANICAL = "MECHANICAL"            # Drive motors, steering actuators, drill chuck, mast gimbal
    POWER = "POWER"                      # Solar array dust coverage, battery cell impedance, PDU bus trip, MMRTG
    COMMUNICATIONS = "COMMUNICATIONS"    # UHF transceiver loss, X-band HGA limit, relay orbiter blackout
    ENVIRONMENTAL = "ENVIRONMENTAL"      # Dust storm tau spike, thermal plunge, atmospheric density collapse
    NAVIGATION = "NAVIGATION"            # Visual odometry slippage, IMU drift, hazcam dust obscuration
    SCIENCE_PAYLOAD = "SCIENCE_PAYLOAD"  # PIXL detector drift, SHERLOC laser loss, filter wheel jam
    SOFTWARE_SYSTEM = "SOFTWARE_SYSTEM"  # Watchdog timeout, memory leak, sequence deadlock, buffer overflow


class FailureSeverity(str, Enum):
    """MIL-STD-882E adapted planetary severity classification."""
    NEGLIGIBLE = "NEGLIGIBLE"      # Minimal telemetry anomaly; full function preserved
    MARGINAL = "MARGINAL"          # Subsystem degraded; redundancy or fallback available
    CRITICAL = "CRITICAL"          # Primary subsystem offline; mission objectives at imminent risk
    CATASTROPHIC = "CATASTROPHIC"  # Potential loss of rover/aircraft or permanent campaign termination


class FaultProfileType(str, Enum):
    """Temporal and dynamic profile of fault manifestation."""
    IMMEDIATE = "IMMEDIATE"        # Step-function onset at t0
    DELAYED = "DELAYED"            # Arms at t0, triggers after specified time delta
    PROGRESSIVE = "PROGRESSIVE"    # Continuous wear or decay over time
    INTERMITTENT = "INTERMITTENT"  # Oscillates between failed and nominal states
    PERSISTENT = "PERSISTENT"      # Static permanent fault until mitigative intervention
    RECOVERABLE = "RECOVERABLE"    # Can be cleared by reset, thermal cooldown, or power cycle
    IRREVERSIBLE = "IRREVERSIBLE"  # Permanent physical degradation that cannot be restored


@dataclass
class SymptomRecord:
    """Observable telemetry residual indicating an anomaly."""
    symptom_id: str
    telemetry_channel: str
    observed_value: float
    expected_nominal_range: Tuple[float, float]
    residual: float
    unit: str
    timestamp_sol_s: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_out_of_bounds(self) -> bool:
        low, high = self.expected_nominal_range
        return self.observed_value < low or self.observed_value > high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symptom_id": self.symptom_id,
            "telemetry_channel": self.telemetry_channel,
            "observed_value": round(self.observed_value, 4),
            "expected_nominal_range": list(self.expected_nominal_range),
            "residual": round(self.residual, 4),
            "unit": self.unit,
            "timestamp_sol_s": self.timestamp_sol_s,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SymptomRecord:
        return cls(
            symptom_id=data["symptom_id"],
            telemetry_channel=data["telemetry_channel"],
            observed_value=float(data["observed_value"]),
            expected_nominal_range=tuple(data["expected_nominal_range"]),
            residual=float(data["residual"]),
            unit=data["unit"],
            timestamp_sol_s=float(data["timestamp_sol_s"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class FailureRecord:
    """Rigorous structured definition of a planetary mission failure mode."""
    failure_id: str
    name: str
    failure_class: FailureClass
    severity: FailureSeverity
    profile_type: FaultProfileType
    target_asset: str                     # e.g., 'ROVER-PERSEVERANCE', 'AERO-INGENUITY', 'AERO-MAPPER'
    affected_subsystem: str               # e.g., 'MOBILITY_DRIVE_FL', 'POWER_BATTERY', 'AVIONICS_IMU'
    containment_boundary: str             # e.g., 'ISOLATE_FL_MOTOR', 'SAFE_MODE_COMM', 'EMERGENCY_LANDING'
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    symptoms: List[SymptomRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "name": self.name,
            "failure_class": self.failure_class.value,
            "severity": self.severity.value,
            "profile_type": self.profile_type.value,
            "target_asset": self.target_asset,
            "affected_subsystem": self.affected_subsystem,
            "containment_boundary": self.containment_boundary,
            "description": self.description,
            "parameters": self.parameters,
            "symptoms": [s.to_dict() for s in self.symptoms],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FailureRecord:
        return cls(
            failure_id=data["failure_id"],
            name=data["name"],
            failure_class=FailureClass(data["failure_class"]),
            severity=FailureSeverity(data["severity"]),
            profile_type=FaultProfileType(data["profile_type"]),
            target_asset=data["target_asset"],
            affected_subsystem=data["affected_subsystem"],
            containment_boundary=data["containment_boundary"],
            description=data["description"],
            parameters=data.get("parameters", {}),
            symptoms=[SymptomRecord.from_dict(s) for s in data.get("symptoms", [])],
        )


class FailureTaxonomyRegistry:
    """Pre-curated repository of benchmark Martian mission failure modes."""

    @staticmethod
    def get_standard_catalog() -> List[FailureRecord]:
        return [
            # 1. MECHANICAL: Wheel Drive Motor Jam
            FailureRecord(
                failure_id="FAIL-MEC-01",
                name="Front-Right Wheel Drive Actuator Stall",
                failure_class=FailureClass.MECHANICAL,
                severity=FailureSeverity.CRITICAL,
                profile_type=FaultProfileType.IRREVERSIBLE,
                target_asset="ROVER-PERSEVERANCE",
                affected_subsystem="MOBILITY_DRIVE_FR",
                containment_boundary="ACTUATOR_ISOLATION_5WHEEL_DRIVE",
                description="Mechanical drive motor stator gear lock caused by terrain rock ingress or mechanical fracture.",
                parameters={"speed_penalty_pct": 45.0, "power_draw_surge_w": 65.0, "steering_bias_deg": 4.2},
            ),
            # 2. POWER: Severe Regional Dust Storm Solar Obscuration
            FailureRecord(
                failure_id="FAIL-PWR-01",
                name="Atmospheric Dust Tau Surge & Solar Array Deposition",
                failure_class=FailureClass.POWER,
                severity=FailureSeverity.CRITICAL,
                profile_type=FaultProfileType.PROGRESSIVE,
                target_asset="AERO-INGENUITY",
                affected_subsystem="POWER_SOLAR_ARRAY",
                containment_boundary="SURVIVAL_HEATER_PRIORITIZATION",
                description="Rapid atmospheric tau increase from 0.4 to 2.8 leading to 78% reduction in solar array energy yield.",
                parameters={"tau_initial": 0.45, "tau_peak": 2.85, "solar_loss_pct": 78.5, "rate_per_sol": 0.6},
            ),
            # 3. COMMUNICATIONS: UHF Primary Relay Blackout
            FailureRecord(
                failure_id="FAIL-COM-01",
                name="MRO Electra UHF Relay Transceiver Drop",
                failure_class=FailureClass.COMMUNICATIONS,
                severity=FailureSeverity.CRITICAL,
                profile_type=FaultProfileType.PERSISTENT,
                target_asset="ROVER-PERSEVERANCE",
                affected_subsystem="COMM_UHF_ELECTRA",
                containment_boundary="FALLBACK_ODYSSEY_DIRECT_TO_EARTH",
                description="Loss of primary high-throughput UHF relay link during MRO overhead pass window.",
                parameters={"uplink_loss_pct": 100.0, "downlink_loss_pct": 100.0, "buffer_overflow_risk_mb": 420.0},
            ),
            # 4. ENVIRONMENTAL: Severe Thermal Plunge & Diurnal Shock
            FailureRecord(
                failure_id="FAIL-ENV-01",
                name="Nighttime Jezero Thermal Shock (-98.5 C)",
                failure_class=FailureClass.ENVIRONMENTAL,
                severity=FailureSeverity.MARGINAL,
                profile_type=FaultProfileType.INTERMITTENT,
                target_asset="ROVER-PERSEVERANCE",
                affected_subsystem="THERMAL_CHASSIS",
                containment_boundary="HEATER_THERMAL_BUS_CLAMP",
                description="Extreme atmospheric cooling exceeding standard thermal loop insulation expectations.",
                parameters={"ambient_temp_c": -98.5, "nominal_temp_c": -74.0, "heater_drain_wh": 140.0},
            ),
            # 5. NAVIGATION: Visual Odometry Slip on Sand Dune Crest
            FailureRecord(
                failure_id="FAIL-NAV-01",
                name="Visual Odometry Severe Sand Slip & Gyro Divergence",
                failure_class=FailureClass.NAVIGATION,
                severity=FailureSeverity.MARGINAL,
                profile_type=FaultProfileType.IMMEDIATE,
                target_asset="ROVER-PERSEVERANCE",
                affected_subsystem="AVIONICS_ODOMETRY",
                containment_boundary="STOP_AND_ASSESS_AUTO_CORRECTION",
                description="Unmodeled soil slippage on 18-degree rippled sand crest causing 35% wheel slip and position uncertainty growth.",
                parameters={"slip_ratio": 0.38, "heading_drift_deg": 12.4, "covariance_growth_m": 8.5},
            ),
            # 6. SCIENCE: PIXL X-Ray Fluorescence Detector Drift
            FailureRecord(
                failure_id="FAIL-SCI-01",
                name="PIXL Spectrometer Thermal Calibration Drift",
                failure_class=FailureClass.SCIENCE_PAYLOAD,
                severity=FailureSeverity.MARGINAL,
                profile_type=FaultProfileType.RECOVERABLE,
                target_asset="ROVER-PERSEVERANCE",
                affected_subsystem="INSTRUMENT_PIXL",
                containment_boundary="CALIBRATION_TARGET_CYCLE",
                description="Sensor cold-plate thermal drift causing baseline energy shift and invalid peak identification.",
                parameters={"energy_drift_kev": 0.18, "gain_shift_pct": 4.5, "false_detection_risk": 0.65},
            ),
            # 7. SOFTWARE: Flight Computer Memory Allocation Panic
            FailureRecord(
                failure_id="FAIL-SW-01",
                name="Flight Software Memory Heap Fragmentation & Watchdog Pre-trip",
                failure_class=FailureClass.SOFTWARE_SYSTEM,
                severity=FailureSeverity.CRITICAL,
                profile_type=FaultProfileType.RECOVERABLE,
                target_asset="AERO-INGENUITY",
                affected_subsystem="AVIONICS_FSW",
                containment_boundary="SAFE_STATE_SYSTEM_REBOOT",
                description="Flight software image processing queue memory fragmentation approaching watchdog threshold.",
                parameters={"free_memory_mb": 14.2, "nominal_memory_mb": 128.0, "watchdog_margin_s": 1.8},
            ),
            # 8. AIRCRAFT SPECIFIC: Rotor Blade Aerodynamic Imbalance
            FailureRecord(
                failure_id="FAIL-AER-01",
                name="Rotorcraft Lower Blade Micro-Abrasion & Lift Deficit",
                failure_class=FailureClass.MECHANICAL,
                severity=FailureSeverity.CRITICAL,
                profile_type=FaultProfileType.PROGRESSIVE,
                target_asset="AERO-INGENUITY",
                affected_subsystem="PROPULSION_ROTORS",
                containment_boundary="FLIGHT_CEILING_REDUCTION",
                description="Blade leading-edge dust erosion causing aerodynamic stall margin reduction and excessive vibration.",
                parameters={"lift_deficit_pct": 18.5, "vibration_rms_g": 3.8, "motor_power_surge_pct": 24.0},
            ),
        ]
