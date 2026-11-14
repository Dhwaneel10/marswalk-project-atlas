"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Temporal Environmental Scenario Engine.

Provides deterministic, reproducible environmental stress scenarios (ENV-A through ENV-E)
for mission validation, risk analysis, and plan stress testing without manufacturing unscientific probabilities.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


class ScenarioCode(str, enum.Enum):
    """Standard calibrated environmental stress scenarios."""
    BASELINE_NOMINAL = "BASELINE_NOMINAL"
    ENV_A_REDUCED_ILLUMINATION = "ENV_A_REDUCED_ILLUMINATION"
    ENV_B_ELEVATED_THERMAL_STRESS = "ENV_B_ELEVATED_THERMAL_STRESS"
    ENV_C_DUST_STORM_OPACITY = "ENV_C_DUST_STORM_OPACITY"
    ENV_D_ATMOSPHERIC_WIND_PERTURBATION = "ENV_D_ATMOSPHERIC_WIND_PERTURBATION"
    ENV_E_COMPOUND_DISTURBANCE = "ENV_E_COMPOUND_DISTURBANCE"


@dataclass(frozen=True)
class EnvironmentalScenarioDefinition:
    """Formal parameter perturbations defining an environmental scenario."""
    scenario_code: ScenarioCode
    title: str
    description: str
    solar_flux_factor: float = 1.0        # Multiplier on direct solar flux (e.g. 0.6 for reduced)
    thermal_anomaly_c: float = 0.0        # Additive temperature delta in °C
    dust_tau_override: Optional[float] = None  # Fixed optical depth override
    wind_anomaly_m_s: float = 0.0         # Additive wind speed delta in m/s
    shadow_sensitivity_boost: float = 0.0 # Virtual horizon angle elevation in degrees
    affected_subsystems: List[str] = field(default_factory=list)
    scientific_disclaimer: str = (
        "Deterministic test scenario fixture. Evaluated results represent stress-testing "
        "performance across explicit fixtures, NOT physical empirical probability of occurrence."
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scenario_code"] = self.scenario_code.value
        return d


class EnvironmentalScenarioEngine:
    """Manages catalog of standard environmental scenarios and applies deterministic perturbations."""

    def __init__(self) -> None:
        self._scenarios: Dict[ScenarioCode, EnvironmentalScenarioDefinition] = {}
        self._register_default_scenarios()

    def _register_default_scenarios(self) -> None:
        # Baseline
        self._scenarios[ScenarioCode.BASELINE_NOMINAL] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.BASELINE_NOMINAL,
            title="Nominal Jezero Spring Conditions",
            description="Clear skies (tau=0.45), typical diurnal temperature swings (-85°C to -15°C), gentle morning winds.",
            solar_flux_factor=1.0,
            thermal_anomaly_c=0.0,
            dust_tau_override=0.45,
            wind_anomaly_m_s=0.0,
            affected_subsystems=[],
        )

        # ENV-A: Reduced Illumination
        self._scenarios[ScenarioCode.ENV_A_REDUCED_ILLUMINATION] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.ENV_A_REDUCED_ILLUMINATION,
            title="ENV-A: Reduced Illumination & Low Sun",
            description="Winter low solar elevation (Ls=270°), long terrain shadows from Jezero delta scarp, direct solar flux reduced by 35%.",
            solar_flux_factor=0.65,
            thermal_anomaly_c=-3.0,
            dust_tau_override=0.55,
            wind_anomaly_m_s=1.0,
            shadow_sensitivity_boost=2.5,
            affected_subsystems=["MASTCAM_Z", "SUPERCAM", "SOLAR_POWER"],
        )

        # ENV-B: Elevated Thermal Stress
        self._scenarios[ScenarioCode.ENV_B_ELEVATED_THERMAL_STRESS] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.ENV_B_ELEVATED_THERMAL_STRESS,
            title="ENV-B: Elevated Thermal Stress (Extreme Cold)",
            description="Deep nocturnal thermal drop (-92°C ground, -86°C air). Requires survival pre-heating before morning arm deployments.",
            solar_flux_factor=1.0,
            thermal_anomaly_c=-10.0,
            dust_tau_override=0.45,
            wind_anomaly_m_s=2.0,
            affected_subsystems=["PIXL", "SHERLOC", "MOBILITY_ACTUATORS"],
        )

        # ENV-C: Dust Storm Opacity
        self._scenarios[ScenarioCode.ENV_C_DUST_STORM_OPACITY] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.ENV_C_DUST_STORM_OPACITY,
            title="ENV-C: Regional Dust Storm Opacity",
            description="Elevated atmospheric optical depth tau=2.40. Severe optical contrast degradation (~90%), Mastcam-Z and SuperCam prohibited.",
            solar_flux_factor=0.30,
            thermal_anomaly_c=+4.0,  # Dust storms trap infrared, warmer nights
            dust_tau_override=2.40,
            wind_anomaly_m_s=6.0,
            affected_subsystems=["MASTCAM_Z", "SUPERCAM", "SOLAR_ARRAY"],
        )

        # ENV-D: Atmospheric Wind Perturbation
        self._scenarios[ScenarioCode.ENV_D_ATMOSPHERIC_WIND_PERTURBATION] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.ENV_D_ATMOSPHERIC_WIND_PERTURBATION,
            title="ENV-D: Afternoon Convective Wind & Dust Devil",
            description="Convective wind gusts reaching 25.0 m/s in early afternoon. Threatens robotic arm positioning and mast pointing stability.",
            solar_flux_factor=0.90,
            thermal_anomaly_c=+1.0,
            dust_tau_override=0.85,
            wind_anomaly_m_s=12.0,
            affected_subsystems=["ROBOTIC_ARM", "HIGH_GAIN_ANTENNA", "MAST_HEAD"],
        )

        # ENV-E: Compound Disturbance
        self._scenarios[ScenarioCode.ENV_E_COMPOUND_DISTURBANCE] = EnvironmentalScenarioDefinition(
            scenario_code=ScenarioCode.ENV_E_COMPOUND_DISTURBANCE,
            title="ENV-E: Compound Planetary Disturbance",
            description="Concurrent dust loading (tau=1.90), severe morning freeze (-8°C anomaly), and late afternoon gusts (21.5 m/s).",
            solar_flux_factor=0.45,
            thermal_anomaly_c=-8.0,
            dust_tau_override=1.90,
            wind_anomaly_m_s=9.5,
            shadow_sensitivity_boost=1.5,
            affected_subsystems=["ALL_INSTRUMENTS", "MOBILITY", "COMMUNICATIONS"],
        )

    def get_scenario(self, code: ScenarioCode) -> EnvironmentalScenarioDefinition:
        """Retrieve definition for scenario code."""
        return self._scenarios.get(code, self._scenarios[ScenarioCode.BASELINE_NOMINAL])

    def list_scenarios(self) -> List[EnvironmentalScenarioDefinition]:
        """List all registered deterministic scenarios."""
        return list(self._scenarios.values())
