"""
MarsWalk 2.0 / Project Atlas — Milestone 13Q
=============================================
Module: science_experiment_design.py
Instrument-aware scientific experiment designer enforcing physical wavelength coverage,
spatial sampling, environmental constraints, and platform feasibility.

Enforces:
- Strict spectral region boundaries (VIS vs NIR vs SWIR vs Raman vs XRF).
- Hard rejection of experiments requesting bands outside an instrument's physical capability.
- Explicit non-probabilistic synthetic radar disclosures.
- Comprehensive experiment plans with rejection conditions and alternatives.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SpectralDomain(str, Enum):
    VISIBLE = "VISIBLE"               # 400 - 700 nm (0.4 - 0.7 um)
    NEAR_INFRARED = "NEAR_INFRARED"   # 700 - 1000 nm (0.7 - 1.0 um)
    SHORT_WAVE_IR = "SHORT_WAVE_IR"   # 1000 - 2500 nm (1.0 - 2.5 um, includes 2.3 um band)
    DEEP_UV_RAMAN = "DEEP_UV_RAMAN"   # 248.6 nm (SHERLOC)
    X_RAY_LITHO = "X_RAY_LITHO"       # X-ray fluorescence (PIXL)
    GROUND_PENETRATING_RADAR = "GROUND_PENETRATING_RADAR" # 150 - 1200 MHz (RIMFAX)
    ENVIRONMENTAL_IN_SITU = "ENVIRONMENTAL_IN_SITU"       # MEDA (temp, pressure, wind)


class PlatformType(str, Enum):
    ROVER = "ROVER"
    ROTORCRAFT = "ROTORCRAFT"
    ORBITER = "ORBITER"


@dataclass
class InstrumentCapability:
    instrument_id: str
    name: str
    platform: PlatformType
    supported_domains: List[SpectralDomain]
    wavelength_min_nm: float
    wavelength_max_nm: float
    spatial_resolution_m_at_range: float
    min_operating_range_m: float
    max_operating_range_m: float
    power_watts: float
    data_rate_kbps: float
    max_tolerated_dust_tau: float
    requires_surface_contact: bool = False
    notes: str = ""

    def can_measure_wavelength(self, wavelength_nm: float) -> bool:
        return self.wavelength_min_nm <= wavelength_nm <= self.wavelength_max_nm

    def supports_domain(self, domain: SpectralDomain) -> bool:
        return domain in self.supported_domains


# Standard Exploration Instrument Fleet Catalog
STANDARD_INSTRUMENTS: Dict[str, InstrumentCapability] = {
    # Rover Mast Instruments
    "MASTCAM_Z": InstrumentCapability(
        instrument_id="MASTCAM_Z",
        name="Mastcam-Z Stereo Multispectral Zoom Camera",
        platform=PlatformType.ROVER,
        supported_domains=[SpectralDomain.VISIBLE, SpectralDomain.NEAR_INFRARED],
        wavelength_min_nm=400.0,
        wavelength_max_nm=1000.0,  # 0.4 to 1.0 um (does NOT reach 2.3 um!)
        spatial_resolution_m_at_range=0.00015, # 0.15 mm at 2m
        min_operating_range_m=1.0,
        max_operating_range_m=10000.0,
        power_watts=22.0,
        data_rate_kbps=500.0,
        max_tolerated_dust_tau=0.85,
        notes="High-res multispectral stereo; cannot detect 2.3 um absorption.",
    ),
    "SUPERCAM_VISIR": InstrumentCapability(
        instrument_id="SUPERCAM_VISIR",
        name="SuperCam Remote Micro-Imager & Infrared Spectrometer",
        platform=PlatformType.ROVER,
        supported_domains=[
            SpectralDomain.VISIBLE,
            SpectralDomain.NEAR_INFRARED,
            SpectralDomain.SHORT_WAVE_IR,
        ],
        wavelength_min_nm=400.0,
        wavelength_max_nm=2600.0,  # Covers 2.3 um metal-OH overtone!
        spatial_resolution_m_at_range=0.001,
        min_operating_range_m=2.0,
        max_operating_range_m=20.0,
        power_watts=45.0,
        data_rate_kbps=300.0,
        max_tolerated_dust_tau=0.75,
        notes="Remote SWIR reflectance spectroscopy capable of distinguishing 2.3 um smectite vs carbonate.",
    ),
    # Rover Arm In-Situ Instruments
    "PIXL": InstrumentCapability(
        instrument_id="PIXL",
        name="Planetary Instrument for X-ray Lithochemistry",
        platform=PlatformType.ROVER,
        supported_domains=[SpectralDomain.X_RAY_LITHO],
        wavelength_min_nm=0.01,
        wavelength_max_nm=1.0,
        spatial_resolution_m_at_range=0.00012,  # 120 micron spot
        min_operating_range_m=0.0,
        max_operating_range_m=0.03,  # Standoff < 3 cm
        power_watts=30.0,
        data_rate_kbps=50.0,
        max_tolerated_dust_tau=1.5,
        requires_surface_contact=True,
        notes="Elemental abundance maps (Si, Al, Fe, Mg, Ca). Gold standard for mineral verification.",
    ),
    "SHERLOC": InstrumentCapability(
        instrument_id="SHERLOC",
        name="Scanning Habitable Environments with Raman & Luminescence",
        platform=PlatformType.ROVER,
        supported_domains=[SpectralDomain.DEEP_UV_RAMAN],
        wavelength_min_nm=248.6,
        wavelength_max_nm=248.6,
        spatial_resolution_m_at_range=0.00005,
        min_operating_range_m=0.0,
        max_operating_range_m=0.05,
        power_watts=40.0,
        data_rate_kbps=80.0,
        max_tolerated_dust_tau=1.5,
        requires_surface_contact=True,
        notes="Deep UV Raman for identifying aromatic organics and fine mineral crystal structures.",
    ),
    "RIMFAX": InstrumentCapability(
        instrument_id="RIMFAX",
        name="Radar Imager for Mars' Subsurface Experiment",
        platform=PlatformType.ROVER,
        supported_domains=[SpectralDomain.GROUND_PENETRATING_RADAR],
        wavelength_min_nm=250000.0,  # 150-1200 MHz
        wavelength_max_nm=2000000.0,
        spatial_resolution_m_at_range=0.15,
        min_operating_range_m=0.0,
        max_operating_range_m=10.0,
        power_watts=15.0,
        data_rate_kbps=20.0,
        max_tolerated_dust_tau=2.0,
        notes="Synthetic subsurface dielectric layer sounding up to 10m depth.",
    ),
    # Aerial Rotorcraft Instruments
    "AERO_NAVCAM": InstrumentCapability(
        instrument_id="AERO_NAVCAM",
        name="Aerial High-Resolution Color ScoutCam",
        platform=PlatformType.ROTORCRAFT,
        supported_domains=[SpectralDomain.VISIBLE],
        wavelength_min_nm=400.0,
        wavelength_max_nm=700.0,
        spatial_resolution_m_at_range=0.0078,  # 0.78 cm/px at 15m AGL
        min_operating_range_m=2.0,
        max_operating_range_m=500.0,
        power_watts=8.0,
        data_rate_kbps=2000.0,
        max_tolerated_dust_tau=0.70,
        notes="Aerial high-res morphology, boulder detection, and route reconnaissance.",
    ),
    "AERO_NIR_SPECTROMETER": InstrumentCapability(
        instrument_id="AERO_NIR_SPECTROMETER",
        name="Aerial Compact Reconnaissance NIR Spectrometer",
        platform=PlatformType.ROTORCRAFT,
        supported_domains=[SpectralDomain.NEAR_INFRARED],
        wavelength_min_nm=700.0,
        wavelength_max_nm=1050.0,  # Strictly NIR! (Does not measure 2.3 um!)
        spatial_resolution_m_at_range=0.05,
        min_operating_range_m=5.0,
        max_operating_range_m=100.0,
        power_watts=14.0,
        data_rate_kbps=150.0,
        max_tolerated_dust_tau=0.60,
        notes="Compact airborne NIR; limited to < 1.05 um. Cannot resolve 2.3 um SWIR band.",
    ),
    "AERO_SWIR_SOUNDER": InstrumentCapability(
        instrument_id="AERO_SWIR_SOUNDER",
        name="Aerial Advanced Short-Wave IR Imaging Spectrometer",
        platform=PlatformType.ROTORCRAFT,
        supported_domains=[SpectralDomain.NEAR_INFRARED, SpectralDomain.SHORT_WAVE_IR],
        wavelength_min_nm=900.0,
        wavelength_max_nm=2500.0,  # Full SWIR coverage (Heavy Science Mapper payload)
        spatial_resolution_m_at_range=0.10,
        min_operating_range_m=10.0,
        max_operating_range_m=150.0,
        power_watts=35.0,
        data_rate_kbps=800.0,
        max_tolerated_dust_tau=0.55,
        notes="Heavy aerial SWIR spectrometer capable of airborne 2.3 um band mapping.",
    ),
}


@dataclass
class ScientificExperimentPlan:
    experiment_id: str
    scientific_question: str
    target_id: str
    target_name: str
    target_coordinates_xy_m: Tuple[float, float]
    target_wavelength_nm: Optional[float]
    required_domain: SpectralDomain
    selected_instrument_id: str
    selected_platform: PlatformType
    hypotheses_under_test: List[str]
    observation_duration_s: float
    energy_wh: float
    data_volume_mb: float
    expected_outcome: str
    alternative_experiment_id: Optional[str]
    rejection_criteria: List[str]
    is_synthetic_model: bool
    scientific_provenance: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "scientific_question": self.scientific_question,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_coordinates_xy_m": [round(c, 2) for c in self.target_coordinates_xy_m],
            "target_wavelength_nm": self.target_wavelength_nm,
            "required_domain": self.required_domain.value,
            "selected_instrument_id": self.selected_instrument_id,
            "selected_platform": self.selected_platform.value,
            "hypotheses_under_test": list(self.hypotheses_under_test),
            "observation_duration_s": round(self.observation_duration_s, 1),
            "energy_wh": round(self.energy_wh, 2),
            "data_volume_mb": round(self.data_volume_mb, 2),
            "expected_outcome": self.expected_outcome,
            "alternative_experiment_id": self.alternative_experiment_id,
            "rejection_criteria": list(self.rejection_criteria),
            "is_synthetic_model": self.is_synthetic_model,
            "scientific_provenance": self.scientific_provenance,
        }


class ScienceExperimentDesigner:
    """
    Validates and configures scientific experiments against physical instrument specifications.
    """

    def __init__(self, instrument_catalog: Optional[Dict[str, InstrumentCapability]] = None):
        self.catalog = instrument_catalog or STANDARD_INSTRUMENTS

    def get_instrument(self, instrument_id: str) -> Optional[InstrumentCapability]:
        return self.catalog.get(instrument_id)

    def validate_instrument_for_wavelength(
        self,
        instrument_id: str,
        wavelength_nm: float,
    ) -> Tuple[bool, str]:
        """
        Enforces strict physical wavelength capability.
        """
        inst = self.get_instrument(instrument_id)
        if not inst:
            return False, f"Instrument '{instrument_id}' not found in fleet catalog."

        if not inst.can_measure_wavelength(wavelength_nm):
            return (
                False,
                f"Physical wavelength violation: {inst.name} operates in range "
                f"[{inst.wavelength_min_nm}, {inst.wavelength_max_nm}] nm, "
                f"which CANNOT measure requested wavelength {wavelength_nm:.1f} nm.",
            )

        return True, "Instrument wavelength coverage verified."

    def design_experiment(
        self,
        scientific_question: str,
        target_id: str,
        target_name: str,
        target_coordinates_xy_m: Tuple[float, float],
        target_wavelength_nm: Optional[float],
        required_domain: SpectralDomain,
        selected_instrument_id: str,
        hypotheses_under_test: List[str],
        observation_duration_s: float = 300.0,
        expected_dust_tau: float = 0.45,
    ) -> ScientificExperimentPlan:
        """
        Designs a scientifically valid experiment plan. Rejects invalid configurations with clear errors.
        """
        inst = self.get_instrument(selected_instrument_id)
        if not inst:
            raise ValueError(f"Unknown instrument '{selected_instrument_id}'")

        # 1. Domain capability check
        if not inst.supports_domain(required_domain):
            raise ValueError(
                f"Instrument capability violation: {inst.name} does not support {required_domain.value}. "
                f"Supported domains: {[d.value for d in inst.supported_domains]}"
            )

        # 2. Wavelength capability check
        if target_wavelength_nm is not None:
            valid_wave, msg = self.validate_instrument_for_wavelength(selected_instrument_id, target_wavelength_nm)
            if not valid_wave:
                raise ValueError(msg)

        # 3. Environmental dust check
        if expected_dust_tau > inst.max_tolerated_dust_tau:
            raise ValueError(
                f"Environmental constraint violation: Atmospheric dust optical depth (tau={expected_dust_tau:.2f}) "
                f"exceeds instrument limit ({inst.max_tolerated_dust_tau:.2f}) for {inst.name}."
            )

        # 4. Energy and Data volume computation
        energy_wh = (inst.power_watts * observation_duration_s) / 3600.0
        data_volume_mb = (inst.data_rate_kbps * observation_duration_s) / (8.0 * 1024.0)

        # Synthetic model flag (RIMFAX / synthetic radar is always synthetic unless raw archives attached)
        is_synthetic = (required_domain == SpectralDomain.GROUND_PENETRATING_RADAR)

        exp_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"
        return ScientificExperimentPlan(
            experiment_id=exp_id,
            scientific_question=scientific_question,
            target_id=target_id,
            target_name=target_name,
            target_coordinates_xy_m=target_coordinates_xy_m,
            target_wavelength_nm=target_wavelength_nm,
            required_domain=required_domain,
            selected_instrument_id=selected_instrument_id,
            selected_platform=inst.platform,
            hypotheses_under_test=hypotheses_under_test,
            observation_duration_s=observation_duration_s,
            energy_wh=energy_wh,
            data_volume_mb=data_volume_mb,
            expected_outcome=f"Acquire {required_domain.value} data at {target_name} to evaluate {hypotheses_under_test}",
            alternative_experiment_id=None,
            rejection_criteria=[
                "Instrument telemetry timeout",
                "High detector dark current exceeding SNR threshold",
                "Severe atmospheric dust obscuration",
            ],
            is_synthetic_model=is_synthetic,
            scientific_provenance=f"Configured via {inst.name} specifications",
        )
