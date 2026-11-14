"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Environmental Mission Windows Optimizer.

Analyzes diurnal solar geometry, terrain shadowing, thermal bounds, and atmospheric opacity
to synthesize optimal, hazard-free observation windows for multi-rover science campaigns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from marswalk.core.mars_solar_environment import (
    MarsSolarGeometryEngine,
    SolarEphemeris,
    TerrainIlluminationResult,
)
from marswalk.core.mars_thermal_environment import (
    MarsThermalEnvironmentEngine,
    ThermalEvaluationResult,
)
from marswalk.core.mars_dust_environment import (
    MarsDustEnvironmentEngine,
    DustEvaluationResult,
)
from marswalk.core.mars_atmospheric_environment import (
    MarsAtmosphericEnvironmentEngine,
    AtmosphericStateResult,
)
from marswalk.core.environmental_hazard_model import (
    EnvironmentalHazardEngine,
    EnvironmentalAssessmentReport,
    HazardSeverity,
)
from marswalk.core.environment_scenario_engine import (
    EnvironmentalScenarioDefinition,
    ScenarioCode,
)


@dataclass(frozen=True)
class EnvironmentalOpportunityWindow:
    """A feasible, hazard-vetted temporal window for executing a science observation."""
    target_id: str
    instrument_name: str
    sol: int
    start_ltst: float
    end_ltst: float
    duration_hours: float
    is_valid: bool
    quality_score: float  # 0.0 to 1.0
    mean_solar_elevation_deg: float
    mean_direct_flux_w_m2: float
    min_air_temperature_c: float
    max_air_temperature_c: float
    mean_optical_depth_tau: float
    shadow_fraction: float
    peak_wind_gust_m_s: float
    violation_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "instrument_name": self.instrument_name,
            "sol": self.sol,
            "start_ltst": round(self.start_ltst, 2),
            "end_ltst": round(self.end_ltst, 2),
            "duration_hours": round(self.duration_hours, 2),
            "is_valid": self.is_valid,
            "quality_score": round(self.quality_score, 3),
            "mean_solar_elevation_deg": round(self.mean_solar_elevation_deg, 1),
            "mean_direct_flux_w_m2": round(self.mean_direct_flux_w_m2, 1),
            "min_air_temperature_c": round(self.min_air_temperature_c, 1),
            "max_air_temperature_c": round(self.max_air_temperature_c, 1),
            "mean_optical_depth_tau": round(self.mean_optical_depth_tau, 2),
            "shadow_fraction": round(self.shadow_fraction, 2),
            "peak_wind_gust_m_s": round(self.peak_wind_gust_m_s, 1),
            "violation_reasons": list(self.violation_reasons),
        }


class EnvironmentalMissionWindowOptimizer:
    """Synthesizes and ranks viable mission observation windows across Jezero Crater."""

    def __init__(
        self,
        elevation_grid: Optional[np.ndarray] = None,
        slope_grid: Optional[np.ndarray] = None,
    ) -> None:
        self.solar_engine = MarsSolarGeometryEngine()
        self.thermal_engine = MarsThermalEnvironmentEngine()
        self.dust_engine = MarsDustEnvironmentEngine()
        self.atmo_engine = MarsAtmosphericEnvironmentEngine()

        if elevation_grid is not None:
            self.elevation_grid = elevation_grid
        else:
            # Default fallback 250x250 plane at -2500m
            self.elevation_grid = np.full((250, 250), -2500.0, dtype=np.float32)

        if slope_grid is not None:
            self.slope_grid = slope_grid
        else:
            self.slope_grid = np.zeros((250, 250), dtype=np.float32)

    def find_optimal_observation_window(
        self,
        target_id: str,
        target_row: float,
        target_col: float,
        instrument_name: str,
        sol: int = 1,
        required_duration_hours: float = 1.0,
        scenario: Optional[EnvironmentalScenarioDefinition] = None,
    ) -> EnvironmentalOpportunityWindow:
        """
        Evaluate full diurnal sweep (06:00 to 18:00 LTST) to locate the best observation window.
        """
        # Step through daylight hours in 0.25h (15 minute) steps
        time_steps = np.arange(6.0, 18.0 + 0.01, 0.25)
        step_evals: List[Dict[str, Any]] = []

        flux_factor = scenario.solar_flux_factor if scenario else 1.0
        thermal_anomaly = scenario.thermal_anomaly_c if scenario else 0.0
        tau_override = scenario.dust_tau_override if scenario else None
        wind_anomaly = scenario.wind_anomaly_m_s if scenario else 0.0

        target_r_int = min(max(int(round(target_row)), 0), self.elevation_grid.shape[0] - 1)
        target_c_int = min(max(int(round(target_col)), 0), self.elevation_grid.shape[1] - 1)
        target_z = float(self.elevation_grid[target_r_int, target_c_int])
        target_slope = float(self.slope_grid[target_r_int, target_c_int])

        for t in time_steps:
            ephem = self.solar_engine.compute_solar_ephemeris(sol, float(t))
            illum = self.solar_engine.evaluate_point_illumination(
                row=target_row,
                col=target_col,
                elevation_grid=self.elevation_grid,
                slope_grid=self.slope_grid,
                ephemeris=ephem,
            )
            thermal = self.thermal_engine.evaluate_instrument_thermal_state(
                sol=sol,
                ltst_hours=float(t),
                instrument_name=instrument_name,
                elevation_m=target_z,
                thermal_anomaly_c=thermal_anomaly,
            )
            dust = self.dust_engine.evaluate_instrument_dust_suitability(
                sol=sol,
                ltst_hours=float(t),
                instrument_name=instrument_name,
                current_tau=tau_override,
            )
            atmo = self.atmo_engine.evaluate_atmospheric_state(
                sol=sol,
                ltst_hours=float(t),
                elevation_m=target_z,
                temperature_c=thermal.air_temperature_c,
                slope_deg=target_slope,
                wind_anomaly_m_s=wind_anomaly,
            )
            hazard_report = EnvironmentalHazardEngine.evaluate_observation_safety(
                sol=sol,
                ltst_hours=float(t),
                target_id=target_id,
                instrument_name=instrument_name,
                is_illuminated=illum.is_illuminated,
                is_terrain_shadowed=illum.is_terrain_shadowed,
                is_daylight=illum.is_daylight,
                air_temperature_c=thermal.air_temperature_c,
                optical_depth_tau=dust.optical_depth_tau,
                wind_gust_m_s=atmo.wind_gust_m_s,
                slope_deg=target_slope,
            )

            step_evals.append({
                "ltst": float(t),
                "is_permissible": hazard_report.is_operation_permissible,
                "solar_elevation_deg": ephem.solar_elevation_deg,
                "direct_flux_w_m2": illum.direct_flux_w_m2 * flux_factor,
                "air_temp_c": thermal.air_temperature_c,
                "optical_depth_tau": dust.optical_depth_tau,
                "is_shadowed": illum.is_terrain_shadowed or illum.is_self_shadowed,
                "wind_gust_m_s": atmo.wind_gust_m_s,
                "score": hazard_report.overall_environmental_score,
                "hazards": [h.description for h in hazard_report.hazards if h.severity == HazardSeverity.CRITICAL],
            })

        # Scan for candidate contiguous windows of length >= required_duration_hours
        steps_needed = int(math.ceil(required_duration_hours / 0.25))
        best_window: Optional[EnvironmentalOpportunityWindow] = None
        best_score = -1.0

        for i in range(len(step_evals) - steps_needed + 1):
            window_slice = step_evals[i : i + steps_needed]
            is_valid = all(s["is_permissible"] for s in window_slice)
            avg_score = float(np.mean([s["score"] for s in window_slice]))

            # Bonus for solar noon illumination (peak flux)
            mean_flux = float(np.mean([s["direct_flux_w_m2"] for s in window_slice]))
            flux_norm = min(1.0, mean_flux / 500.0)
            combined_quality = (0.6 * avg_score) + (0.4 * flux_norm)

            if is_valid and combined_quality > best_score:
                best_score = combined_quality
                best_window = EnvironmentalOpportunityWindow(
                    target_id=target_id,
                    instrument_name=instrument_name,
                    sol=sol,
                    start_ltst=window_slice[0]["ltst"],
                    end_ltst=window_slice[-1]["ltst"] + 0.25,
                    duration_hours=required_duration_hours,
                    is_valid=True,
                    quality_score=combined_quality,
                    mean_solar_elevation_deg=float(np.mean([s["solar_elevation_deg"] for s in window_slice])),
                    mean_direct_flux_w_m2=mean_flux,
                    min_air_temperature_c=float(np.min([s["air_temp_c"] for s in window_slice])),
                    max_air_temperature_c=float(np.max([s["air_temp_c"] for s in window_slice])),
                    mean_optical_depth_tau=float(np.mean([s["optical_depth_tau"] for s in window_slice])),
                    shadow_fraction=float(np.mean([1.0 if s["is_shadowed"] else 0.0 for s in window_slice])),
                    peak_wind_gust_m_s=float(np.max([s["wind_gust_m_s"] for s in window_slice])),
                    violation_reasons=[],
                )

        if best_window is not None:
            return best_window

        # If no strictly valid contiguous window was found, return the least constrained window with violation reasons
        mid_idx = len(step_evals) // 2
        slice_fallback = step_evals[max(0, mid_idx - steps_needed // 2) : min(len(step_evals), mid_idx + steps_needed // 2 + 1)]
        reasons: List[str] = []
        for s in slice_fallback:
            reasons.extend(s["hazards"])
        unique_reasons = sorted(list(set(reasons))) or ["Insufficient unshadowed daylight window or thermal envelope violation."]

        return EnvironmentalOpportunityWindow(
            target_id=target_id,
            instrument_name=instrument_name,
            sol=sol,
            start_ltst=slice_fallback[0]["ltst"] if slice_fallback else 11.0,
            end_ltst=(slice_fallback[-1]["ltst"] + 0.25) if slice_fallback else 12.0,
            duration_hours=required_duration_hours,
            is_valid=False,
            quality_score=0.1,
            mean_solar_elevation_deg=float(np.mean([s["solar_elevation_deg"] for s in slice_fallback])) if slice_fallback else 30.0,
            mean_direct_flux_w_m2=float(np.mean([s["direct_flux_w_m2"] for s in slice_fallback])) if slice_fallback else 0.0,
            min_air_temperature_c=float(np.min([s["air_temp_c"] for s in slice_fallback])) if slice_fallback else -60.0,
            max_air_temperature_c=float(np.max([s["air_temp_c"] for s in slice_fallback])) if slice_fallback else -30.0,
            mean_optical_depth_tau=float(np.mean([s["optical_depth_tau"] for s in slice_fallback])) if slice_fallback else 0.45,
            shadow_fraction=1.0,
            peak_wind_gust_m_s=float(np.max([s["wind_gust_m_s"] for s in slice_fallback])) if slice_fallback else 15.0,
            violation_reasons=unique_reasons,
        )
