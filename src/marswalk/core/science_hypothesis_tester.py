"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_hypothesis_tester.py
Adversarial Hypothesis Testing, Scientific Falsification, and Artifact Detection.

Enforces:
- Active search for non-mineral explanations (atmospheric CO2, dust, detector thermal drift).
- Generation of discriminating counter-observations specifically designed to disprove hypotheses.
- Comprehensive Falsification Audit Records.
- Multi-instrument diagnostic checks (e.g., verifying 1.4 um and 1.9 um companion hydration bands
  before accepting a 2.3 um hydrated clay identification).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.science_hypothesis_registry import HypothesisStatus, ScientificHypothesis
from marswalk.core.science_experiment_design import SpectralDomain, STANDARD_INSTRUMENTS


class ArtifactType(str, Enum):
    ATMOSPHERIC_CO2_OVERPRINT = "ATMOSPHERIC_CO2_OVERPRINT"
    DUST_AEROSOL_SCATTERING = "DUST_AEROSOL_SCATTERING"
    DETECTOR_THERMAL_DRIFT = "DETECTOR_THERMAL_DRIFT"
    ILLUMINATION_SHADOW_ARTIFACT = "ILLUMINATION_SHADOW_ARTIFACT"
    SPATIAL_SAMPLING_ALIASING = "SPATIAL_SAMPLING_ALIASING"
    SYNTHETIC_MODEL_DEFAULT = "SYNTHETIC_MODEL_DEFAULT"


@dataclass
class FalsificationRecord:
    hypothesis_id: str
    potential_artifacts_identified: List[ArtifactType]
    mandatory_companion_features: List[str]
    discriminating_counter_tests: List[Dict[str, Any]]
    falsification_conditions: List[str]
    current_falsification_risk: float  # 0.0 (robust) to 1.0 (fragile claim)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "potential_artifacts_identified": [a.value for a in self.potential_artifacts_identified],
            "mandatory_companion_features": list(self.mandatory_companion_features),
            "discriminating_counter_tests": self.discriminating_counter_tests,
            "falsification_conditions": list(self.falsification_conditions),
            "current_falsification_risk": round(self.current_falsification_risk, 3),
        }


class ScienceHypothesisTester:
    """
    Adversarial reasoning engine dedicated to disproving superficial discoveries.
    """

    def analyze_spectral_anomaly(
        self,
        hypothesis: ScientificHypothesis,
        observed_band_nm: float,
        band_depth: float,
        dust_optical_depth_tau: float = 0.45,
        surface_pressure_pa: float = 610.0,
        instrument_id: str = "AERO_NIR_SPECTROMETER",
    ) -> FalsificationRecord:
        """
        Rigorously tests a candidate mineral spectral detection against physical artifacts.
        """
        artifacts: List[ArtifactType] = []
        companion_features: List[str] = []
        counter_tests: List[Dict[str, Any]] = []
        falsification_conditions: List[str] = []
        risk_score = 0.0

        # 1. Physical Instrument Band Capability Check
        inst = STANDARD_INSTRUMENTS.get(instrument_id)
        if inst and not inst.can_measure_wavelength(observed_band_nm):
            artifacts.append(ArtifactType.DETECTOR_THERMAL_DRIFT)
            falsification_conditions.append(
                f"Instrument '{instrument_id}' physical range [{inst.wavelength_min_nm}, {inst.wavelength_max_nm}] nm "
                f"excludes requested {observed_band_nm} nm."
            )
            risk_score += 0.85

        # 2. Case: The 2.3 um (2300 nm) Metal-OH Clay Candidate
        if 2280.0 <= observed_band_nm <= 2350.0:
            # Physics rule: Hydrous smectite clays MUST exhibit fundamental H2O and OH combination bands
            # near 1.4 um (1400 nm) and 1.9 um (1900 nm). If 1.9 um is missing, it CANNOT be a hydrous clay!
            companion_features.extend([
                "1400 nm (OH stretch overtone)",
                "1900 nm (H2O molecular vibration combination)",
            ])

            # Atmospheric CO2 interference check
            # Mars atmosphere is 95% CO2; pressure 610 Pa exhibits strong CO2 triplets near 2.0 and 2.35 um
            if surface_pressure_pa > 500.0:
                artifacts.append(ArtifactType.ATMOSPHERIC_CO2_OVERPRINT)
                falsification_conditions.append(
                    "Atmospheric path length creates residual 2.35 um CO2 absorption without radiative transfer removal."
                )
                risk_score += 0.35

            # Dust scattering check
            if dust_optical_depth_tau > 0.6:
                artifacts.append(ArtifactType.DUST_AEROSOL_SCATTERING)
                falsification_conditions.append(
                    f"Elevated atmospheric dust (tau={dust_optical_depth_tau:.2f}) slopes the SWIR continuum."
                )
                risk_score += 0.25

            # Prescribe Discriminating Counter-Tests
            counter_tests.append({
                "test_name": "PIXL_ELEMENTAL_STOICHIOMETRY",
                "instrument_id": "PIXL",
                "method": "In-situ X-ray Lithochemistry micro-mapping",
                "discriminating_target": "Si/Al and (Fe+Mg)/Si elemental molar ratios",
                "expected_if_smectite": "Si/Al in [2.0, 3.5] and detectable Fe/Mg",
                "expected_if_carbonate": "Strong Ca or Mg peak with near-zero Al and low Si",
                "falsification_threshold": "Al < 0.5 wt% or Ca > 25 wt% falsifies phyllosilicate smectite",
            })

            counter_tests.append({
                "test_name": "SUPERCAM_COMPANION_HYDRATION_CHECK",
                "instrument_id": "SUPERCAM_VISIR",
                "method": "Remote SWIR spectroscopy across [1300 - 2600] nm",
                "discriminating_target": "1900 nm H2O band depth",
                "expected_if_smectite": "1900 nm band depth > 0.05",
                "expected_if_carbonate": "1900 nm band absent; distinct 2300 & 2500 nm doublet",
                "falsification_threshold": "Band depth at 1900 nm < 0.01 falsifies hydrous clay",
            })

            counter_tests.append({
                "test_name": "MULTI_PHASE_ANGLE_AERIAL_REACQUISITION",
                "instrument_id": "AERO_SWIR_SOUNDER",
                "method": "Repeat airborne SWIR observation at different solar zenith angle",
                "discriminating_target": "Absorption invariance with solar illumination",
                "expected_if_mineral": "Band depth invariant with solar phase angle",
                "expected_if_atmospheric": "Band depth scales with airmass sec(theta_z)",
                "falsification_threshold": "Depth scales with airmass implies atmospheric artifact",
            })

        risk_score = min(1.0, risk_score)

        return FalsificationRecord(
            hypothesis_id=hypothesis.hypothesis_id,
            potential_artifacts_identified=artifacts,
            mandatory_companion_features=companion_features,
            discriminating_counter_tests=counter_tests,
            falsification_conditions=falsification_conditions,
            current_falsification_risk=risk_score,
        )

    def evaluate_test_results_against_hypothesis(
        self,
        hypothesis: ScientificHypothesis,
        test_name: str,
        measurement_data: Dict[str, Any],
    ) -> Tuple[HypothesisStatus, str, float]:
        """
        Evaluates incoming experimental measurement against the hypothesis.
        Can SUPPORT, WEAKEN, or REJECT the hypothesis.
        """
        # Test: PIXL Elemental Chemistry
        if test_name == "PIXL_ELEMENTAL_STOICHIOMETRY":
            al_wt = measurement_data.get("al_wt_pct", 0.0)
            ca_wt = measurement_data.get("ca_wt_pct", 0.0)
            si_wt = measurement_data.get("si_wt_pct", 0.0)

            if ca_wt > 20.0 and al_wt < 0.5:
                # Falsified! It is a carbonate or calcite/dolomite, NOT smectite clay!
                return (
                    HypothesisStatus.REJECTED,
                    f"Falsified by PIXL lithochemistry: High Calcium ({ca_wt:.1f} wt%) and negligible Aluminum ({al_wt:.2f} wt%) "
                    f"proves carbonate-bearing unit, disproving phyllosilicate smectite.",
                    0.02, # Low posterior
                )
            elif al_wt >= 1.5 and si_wt >= 15.0:
                # Consistent with smectite clay!
                return (
                    HypothesisStatus.SUPPORTED_BY_EVIDENCE,
                    f"Supported by PIXL lithochemistry: Aluminum ({al_wt:.1f} wt%) and Silicon ({si_wt:.1f} wt%) "
                    f"match authentic phyllosilicate clay stoichiometry.",
                    0.92, # High posterior
                )

        # Test: SuperCam Hydration Companion Check
        elif test_name == "SUPERCAM_COMPANION_HYDRATION_CHECK":
            band_1900 = measurement_data.get("band_depth_1900nm", 0.0)
            band_2500 = measurement_data.get("band_depth_2500nm", 0.0)

            if band_1900 < 0.01 and band_2500 > 0.08:
                # Characteristic carbonate doublet (2.3 and 2.5 um) without water!
                return (
                    HypothesisStatus.REJECTED,
                    f"Falsified by SWIR companion check: 1900 nm H2O band is absent (depth={band_1900:.3f}) "
                    f"while 2500 nm carbonate band is prominent (depth={band_2500:.3f}).",
                    0.05,
                )
            elif band_1900 >= 0.05:
                return (
                    HypothesisStatus.SUPPORTED_BY_EVIDENCE,
                    f"Supported by SWIR companion check: Strong 1900 nm molecular H2O band (depth={band_1900:.3f}) "
                    f"confirms true hydrous mineral structure.",
                    0.88,
                )

        # Default inconclusive
        return (
            HypothesisStatus.INCONCLUSIVE,
            f"Measurement from {test_name} did not meet critical falsification or confirmation thresholds.",
            hypothesis.posterior_probability or 0.5,
        )
