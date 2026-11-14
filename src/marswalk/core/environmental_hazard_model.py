"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Environmental Hazard & Operational Context Engine.

Evaluates operational constraints, rule-based environmental hazards, and instrument
safety boundaries for planetary rover activities across Jezero Crater.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


class HazardSeverity(str, enum.Enum):
    """Operational hazard severity classification."""
    CRITICAL = "CRITICAL"    # Operation prohibited; instrument damage or mission failure
    WARNING = "WARNING"      # Operational penalty; degraded science return or elevated risk
    ADVISORY = "ADVISORY"    # Informational notice; suboptimal conditions


class HazardType(str, enum.Enum):
    """Catalog of formalized environmental hazard types."""
    ILLUMINATION_UNAVAILABLE = "ILLUMINATION_UNAVAILABLE"
    TERRAIN_SHADOW_OBSTRUCTION = "TERRAIN_SHADOW_OBSTRUCTION"
    THERMAL_ENVELOPE_EXCEEDED = "THERMAL_ENVELOPE_EXCEEDED"
    DUST_OPACITY_HIGH = "DUST_OPACITY_HIGH"
    HIGH_WIND_GUST = "HIGH_WIND_GUST"
    SLOPE_HAZARD = "SLOPE_HAZARD"
    MISSING_ENVIRONMENTAL_DATA = "MISSING_ENVIRONMENTAL_DATA"


@dataclass(frozen=True)
class EnvironmentalHazard:
    """Individual detected operational hazard record."""
    hazard_type: HazardType
    severity: HazardSeverity
    description: str
    parameter_name: str
    observed_value: Any
    threshold_value: Any
    mitigation_suggestion: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["hazard_type"] = self.hazard_type.value
        d["severity"] = self.severity.value
        return d


@dataclass
class EnvironmentalAssessmentReport:
    """Consolidated environmental hazard and operational feasibility assessment."""
    sol: int
    ltst_hours: float
    target_id: Optional[str]
    instrument_name: Optional[str]
    is_operation_permissible: bool
    hazards: List[EnvironmentalHazard] = field(default_factory=list)
    overall_environmental_score: float = 1.0  # 0.0 (infeasible) to 1.0 (ideal)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "ltst_hours": round(self.ltst_hours, 3),
            "target_id": self.target_id,
            "instrument_name": self.instrument_name,
            "is_operation_permissible": self.is_operation_permissible,
            "total_hazards": len(self.hazards),
            "critical_count": sum(1 for h in self.hazards if h.severity == HazardSeverity.CRITICAL),
            "warning_count": sum(1 for h in self.hazards if h.severity == HazardSeverity.WARNING),
            "advisory_count": sum(1 for h in self.hazards if h.severity == HazardSeverity.ADVISORY),
            "overall_environmental_score": round(self.overall_environmental_score, 3),
            "hazards": [h.to_dict() for h in self.hazards],
        }


class EnvironmentalHazardEngine:
    """Rule engine evaluating all environmental factors against operational safety gates."""

    @classmethod
    def evaluate_observation_safety(
        cls,
        sol: int,
        ltst_hours: float,
        target_id: str,
        instrument_name: str,
        is_illuminated: bool,
        is_terrain_shadowed: bool,
        is_daylight: bool,
        air_temperature_c: float,
        optical_depth_tau: float,
        wind_gust_m_s: float,
        slope_deg: float = 0.0,
        requires_direct_sun: bool = True,
    ) -> EnvironmentalAssessmentReport:
        """
        Evaluate full multi-parameter environmental safety for a science observation activity.
        """
        hazards: List[EnvironmentalHazard] = []
        score = 1.0

        # 1. Illumination Checks (for optical instruments)
        inst_upper = instrument_name.upper()
        is_optical = inst_upper in ("MASTCAM_Z", "SUPERCAM")

        if is_optical or requires_direct_sun:
            if not is_daylight:
                hazards.append(
                    EnvironmentalHazard(
                        hazard_type=HazardType.ILLUMINATION_UNAVAILABLE,
                        severity=HazardSeverity.CRITICAL,
                        description="Solar elevation below horizon (nighttime observation impossible for optical payload)",
                        parameter_name="solar_elevation_deg",
                        observed_value="< 0.0",
                        threshold_value="> 0.0",
                        mitigation_suggestion="Reschedule observation to diurnal daylight hours (10:00 - 16:00 LTST)",
                    )
                )
                score -= 0.6
            elif is_terrain_shadowed:
                hazards.append(
                    EnvironmentalHazard(
                        hazard_type=HazardType.TERRAIN_SHADOW_OBSTRUCTION,
                        severity=HazardSeverity.WARNING,
                        description="Target is located in a geometric terrain cast shadow (crater wall or scarp)",
                        parameter_name="is_terrain_shadowed",
                        observed_value=True,
                        threshold_value=False,
                        mitigation_suggestion="Shift observation window when solar azimuth/elevation bypasses terrain horizon obstacle",
                    )
                )
                score -= 0.35

        # 2. Thermal Limits Check
        from marswalk.core.mars_thermal_environment import INSTRUMENT_THERMAL_LIMITS_C
        limits = INSTRUMENT_THERMAL_LIMITS_C.get(inst_upper)
        if limits is not None:
            min_t, max_t = limits
            if air_temperature_c < min_t:
                hazards.append(
                    EnvironmentalHazard(
                        hazard_type=HazardType.THERMAL_ENVELOPE_EXCEEDED,
                        severity=HazardSeverity.CRITICAL,
                        description=f"Ambient air temperature ({air_temperature_c:.1f}°C) below minimum operating envelope ({min_t:.1f}°C)",
                        parameter_name="air_temperature_c",
                        observed_value=air_temperature_c,
                        threshold_value=min_t,
                        mitigation_suggestion="Engage instrument survival/pre-heating heaters or defer to warmer afternoon sol hours",
                    )
                )
                score -= 0.5
            elif air_temperature_c > max_t:
                hazards.append(
                    EnvironmentalHazard(
                        hazard_type=HazardType.THERMAL_ENVELOPE_EXCEEDED,
                        severity=HazardSeverity.CRITICAL,
                        description=f"Ambient air temperature ({air_temperature_c:.1f}°C) exceeds maximum operating envelope ({max_t:.1f}°C)",
                        parameter_name="air_temperature_c",
                        observed_value=air_temperature_c,
                        threshold_value=max_t,
                        mitigation_suggestion="Postpone observation to early morning cooler conditions",
                    )
                )
                score -= 0.5

        # 3. Dust Opacity Check
        from marswalk.core.mars_dust_environment import INSTRUMENT_MAX_TAU_LIMITS
        max_tau = INSTRUMENT_MAX_TAU_LIMITS.get(inst_upper, 5.0)
        if optical_depth_tau > max_tau:
            hazards.append(
                EnvironmentalHazard(
                    hazard_type=HazardType.DUST_OPACITY_HIGH,
                    severity=HazardSeverity.WARNING if max_tau >= 2.0 else HazardSeverity.CRITICAL,
                    description=f"Atmospheric optical depth tau={optical_depth_tau:.2f} exceeds tolerance limit ({max_tau:.1f}) for {instrument_name}",
                    parameter_name="optical_depth_tau",
                    observed_value=optical_depth_tau,
                    threshold_value=max_tau,
                    mitigation_suggestion="Subsitute with ground-penetrating radar (RIMFAX) or defer optical imaging until dust clears",
                )
            )
            score -= 0.3

        # 4. Wind Hazard Check
        if wind_gust_m_s > 22.0:
            hazards.append(
                EnvironmentalHazard(
                    hazard_type=HazardType.HIGH_WIND_GUST,
                    severity=HazardSeverity.WARNING,
                    description=f"Atmospheric wind gust ({wind_gust_m_s:.1f} m/s) poses stability risk for mast/arm deployment",
                    parameter_name="wind_gust_m_s",
                    observed_value=wind_gust_m_s,
                    threshold_value=22.0,
                    mitigation_suggestion="Stow robotic arm and mast until convective wind gusts subside",
                )
            )
            score -= 0.25

        score = max(0.0, score)
        has_critical = any(h.severity == HazardSeverity.CRITICAL for h in hazards)
        is_permissible = not has_critical

        return EnvironmentalAssessmentReport(
            sol=sol,
            ltst_hours=ltst_hours,
            target_id=target_id,
            instrument_name=instrument_name,
            is_operation_permissible=is_permissible,
            hazards=hazards,
            overall_environmental_score=score,
        )
