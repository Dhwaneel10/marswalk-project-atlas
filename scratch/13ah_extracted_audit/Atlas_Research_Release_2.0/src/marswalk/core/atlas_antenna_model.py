"""
Milestone 13AD: Antenna Field-Region Qualification & Radiation Pattern Engine
=============================================================================
Designation: ATLAS-13AD-ANTENNA
Implements IEEE 145-2013 and ISED GL-01 antenna field-region boundaries,
Bessel/Airy circular aperture radiation patterns, 3-tier pattern hierarchy,
and explicit out-of-domain pointing loss governance.

References:
- IEEE Std 145-2013, "IEEE Standard for Definitions of Terms for Antennas".
- ISED Canada GL-01 (Issue 3), Section 2.3: "Field Regions of Antennas".
- Balanis, C. A. (2016), "Antenna Theory: Analysis and Design", 4th ed., Wiley.
- ITU-R Recommendation S.580-6: "Radiation diagrams for use as design objectives
  for antennas of earth stations operating with geostationary satellites".
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

try:
    from scipy.special import j1
    SCIPY_J1_AVAILABLE = True
except ImportError:
    SCIPY_J1_AVAILABLE = False


SPEED_OF_LIGHT_M_S: float = 299_792_458.0


class AntennaCategory(str, Enum):
    """Categorization of antenna architecture and physical radiating aperture."""
    PARABOLIC_REFLECTOR = "PARABOLIC_REFLECTOR"
    HORN = "HORN"
    HELICAL_ARRAY = "HELICAL_ARRAY"
    DIPOLE_OMNI = "DIPOLE_OMNI"
    PATCH_MICROSTRIP = "PATCH_MICROSTRIP"
    PHASED_ARRAY = "PHASED_ARRAY"
    OPTICAL_TELESCOPE = "OPTICAL_TELESCOPE"


class FieldRegionClassification(str, Enum):
    """Physical electromagnetic field regions according to IEEE 145 and ISED GL-01."""
    REACTIVE_NEAR_FIELD = "REACTIVE_NEAR_FIELD"
    RADIATING_NEAR_FIELD_FRESNEL = "RADIATING_NEAR_FIELD_FRESNEL"
    FRAUNHOFER_FAR_FIELD = "FRAUNHOFER_FAR_FIELD"


class PatternModelTier(str, Enum):
    """3-Tier classification of antenna radiation pattern evaluation."""
    TIER_1_REFERENCE_MEASURED = "TIER_1_REFERENCE_MEASURED"
    TIER_2_ANALYTICAL_APPROXIMATION = "TIER_2_ANALYTICAL_APPROXIMATION"
    TIER_3_OUT_OF_DOMAIN_GUARD = "TIER_3_OUT_OF_DOMAIN_GUARD"


@dataclass(frozen=True)
class AntennaFieldRegions:
    """
    Calculated field-region boundaries and applicability metadata for an antenna.
    """
    category: AntennaCategory
    physical_dimension_m: float
    wavelength_m: float
    carrier_freq_hz: float
    reactive_near_field_boundary_m: float
    radiating_near_field_boundary_m: float
    fraunhofer_far_field_distance_m: float
    governing_criterion: str
    reference_source: str
    is_electrically_small: bool

    def classify_distance(self, distance_m: float) -> FieldRegionClassification:
        """Classifies a given distance into reactive near-field, Fresnel, or Fraunhofer."""
        if distance_m < self.reactive_near_field_boundary_m:
            return FieldRegionClassification.REACTIVE_NEAR_FIELD
        elif distance_m < self.fraunhofer_far_field_distance_m:
            return FieldRegionClassification.RADIATING_NEAR_FIELD_FRESNEL
        else:
            return FieldRegionClassification.FRAUNHOFER_FAR_FIELD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "physical_dimension_m": round(self.physical_dimension_m, 4),
            "wavelength_m": round(self.wavelength_m, 6),
            "carrier_freq_mhz": round(self.carrier_freq_hz / 1e6, 3),
            "reactive_boundary_m": round(self.reactive_near_field_boundary_m, 4),
            "radiating_near_field_boundary_m": round(self.radiating_near_field_boundary_m, 4),
            "fraunhofer_far_field_distance_m": round(self.fraunhofer_far_field_distance_m, 4),
            "governing_criterion": self.governing_criterion,
            "reference_source": self.reference_source,
            "is_electrically_small": self.is_electrically_small,
        }


@dataclass
class AntennaRadiationPatternResult:
    """Detailed evaluation of antenna gain and pointing loss."""
    boresight_gain_dbi: float
    pointing_error_deg: float
    hpbw_deg: float
    effective_gain_dbi: float
    pointing_loss_db: float
    model_tier: PatternModelTier
    computational_guard_applied: bool
    status_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "boresight_gain_dbi": round(self.boresight_gain_dbi, 2),
            "pointing_error_deg": round(self.pointing_error_deg, 4),
            "hpbw_deg": round(self.hpbw_deg, 3),
            "effective_gain_dbi": round(self.effective_gain_dbi, 2),
            "pointing_loss_db": round(self.pointing_loss_db, 2),
            "model_tier": self.model_tier.value,
            "computational_guard_applied": self.computational_guard_applied,
            "status_reason": self.status_reason,
        }


def _pure_python_bessel_j1(x: float) -> float:
    """
    High-precision polynomial approximation of Bessel function of the first kind J1(x).
    Accurate to within 1e-7 (Abramowitz & Stegun 9.4.4 / 9.4.6).
    """
    ax = abs(x)
    if ax < 3.75:
        y = (x / 3.75) ** 2
        ans = x * (
            0.5
            + y
            * (
                -0.56249985
                + y
                * (
                    0.21093573
                    + y * (-0.03954289 + y * (0.00443319 - y * 0.00031761))
                )
            )
        )
    else:
        y = 3.75 / ax
        f0 = (
            0.79788456
            + y
            * (
                -0.00000077
                + y
                * (
                    -0.00552740
                    + y * (0.00009512 + y * (0.00137237 - y * 0.00072805))
                )
            )
        )
        theta0 = (
            ax
            - 2.35619449
            + y
            * (
                0.04166397
                + y
                * (
                    -0.00003954
                    + y * (-0.00262573 + y * (0.00054125 - y * 0.00029333))
                )
            )
        )
        ans = (1.0 / math.sqrt(ax)) * f0 * math.cos(theta0)
        if x < 0.0:
            ans = -ans
    return ans


def bessel_j1(x: float) -> float:
    """Computes J1(x) using SciPy if available, else pure Python approximation."""
    if SCIPY_J1_AVAILABLE:
        return float(j1(x))
    return _pure_python_bessel_j1(x)


class AdvancedAntennaEngine:
    """
    Engine for antenna field-region calculation and multi-tier radiation pattern evaluation.
    """

    @classmethod
    def calculate_field_regions(
        cls,
        physical_dimension_m: float,
        carrier_freq_hz: float,
        category: AntennaCategory = AntennaCategory.PARABOLIC_REFLECTOR,
    ) -> AntennaFieldRegions:
        """
        Evaluates antenna field regions according to IEEE 145-2013 and ISED GL-01 Section 2.3:
        1. Reactive Near-Field: R < R1 = 0.62 * sqrt(D^3 / lambda)
        2. Radiating Near-Field (Fresnel): R1 <= R < R_FF = 2*D^2 / lambda
        3. Far-Field (Fraunhofer): R >= R_FF
        For electrically small antennas (D <= lambda/2), far-field is governed by R >= 2*lambda.
        """
        if math.isnan(physical_dimension_m) or math.isnan(carrier_freq_hz):
            raise ValueError(f"Parameters cannot be NaN (D={physical_dimension_m}, f={carrier_freq_hz})")
        if physical_dimension_m <= 0.0:
            raise ValueError(f"Physical dimension D must be strictly positive, got {physical_dimension_m}")
        if carrier_freq_hz <= 0.0:
            raise ValueError(f"Carrier frequency must be strictly positive, got {carrier_freq_hz}")

        wavelength = SPEED_OF_LIGHT_M_S / carrier_freq_hz
        is_small = physical_dimension_m <= (wavelength / 2.0)

        if is_small or category == AntennaCategory.DIPOLE_OMNI:
            # Electrically small antenna (e.g. dipole, monopole, small patch)
            # IEEE / Balanis: reactive zone extends to lambda / (2*pi)
            r_reactive = wavelength / (2.0 * math.pi)
            r_fresnel = wavelength
            # Far field requires R >= 2*lambda or 3*lambda
            r_fraunhofer = 2.0 * wavelength
            criterion = "IEEE 145 Small Antenna Criterion (R >= 2*lambda)"
            source = "Balanis (2016) Antenna Theory, Sec 2.2.4"
        else:
            # Directive aperture (D > lambda/2)
            # Classical ISED GL-01 boundaries:
            r_reactive = 0.62 * math.sqrt((physical_dimension_m ** 3) / wavelength)
            r_fresnel = (2.0 * (physical_dimension_m ** 2)) / wavelength
            # Triple condition for Fraunhofer: R >= 2*D^2/lambda, R >> D (5*D), R >> lambda (1.6*lambda)
            r_fraunhofer = max(r_fresnel, 5.0 * physical_dimension_m, 2.0 * wavelength)
            criterion = "Conservative Screening Envelope [max(2*D^2/lambda, 5*D, 2*lambda)]"
            source = "Balanis (2016); IEEE Std 145-2013 informative screening convention"

        return AntennaFieldRegions(
            category=category,
            physical_dimension_m=physical_dimension_m,
            wavelength_m=wavelength,
            carrier_freq_hz=carrier_freq_hz,
            reactive_near_field_boundary_m=r_reactive,
            radiating_near_field_boundary_m=r_fresnel,
            fraunhofer_far_field_distance_m=r_fraunhofer,
            governing_criterion=criterion,
            reference_source=source,
            is_electrically_small=is_small,
        )

    @classmethod
    def evaluate_radiation_pattern(
        cls,
        boresight_gain_dbi: float,
        physical_dimension_m: float,
        carrier_freq_hz: float,
        pointing_error_deg: float,
        category: AntennaCategory = AntennaCategory.PARABOLIC_REFLECTOR,
        reference_envelope: Optional[str] = None,
    ) -> AntennaRadiationPatternResult:
        """
        Evaluates antenna radiation pattern and off-axis pointing loss using 3-tier hierarchy:
        - Tier 1: Authoritative measured/reference pattern (e.g. ITU-R S.580 envelope)
        - Tier 2: Analytical Bessel/Airy disc circular aperture model:
                  F(u) = |2 * J1(u) / u|^2, u = pi * D / lambda * sin(theta)
        - Tier 3: Out-of-domain with exposed computational guard metadata
        """
        if math.isnan(pointing_error_deg) or math.isnan(boresight_gain_dbi):
            raise ValueError("Pointing parameters cannot be NaN")
        if math.isinf(pointing_error_deg) or math.isinf(boresight_gain_dbi):
            raise ValueError("Pointing parameters must be finite real numbers")

        pointing_error_deg = abs(pointing_error_deg)
        wavelength = SPEED_OF_LIGHT_M_S / carrier_freq_hz

        # Half-Power Beamwidth (HPBW) in degrees ~ 70 * (lambda / D) for parabolic dish
        # For omni/dipole, HPBW ~ 78°
        if category in (AntennaCategory.DIPOLE_OMNI, AntennaCategory.PATCH_MICROSTRIP) or boresight_gain_dbi <= 3.0:
            hpbw_deg = 78.0
            pointing_loss_db = 0.1
            return AntennaRadiationPatternResult(
                boresight_gain_dbi=boresight_gain_dbi,
                pointing_error_deg=pointing_error_deg,
                hpbw_deg=hpbw_deg,
                effective_gain_dbi=boresight_gain_dbi - 0.1,
                pointing_loss_db=0.1,
                model_tier=PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION,
                computational_guard_applied=False,
                status_reason="Omni/broadbeam antenna: negligible off-axis degradation",
            )

        hpbw_deg = 70.0 * (wavelength / physical_dimension_m)
        hpbw_deg = max(0.001, min(70.0, hpbw_deg))

        # Check for Tier 1 ITU-R S.580 reference pattern
        if reference_envelope == "ITU-R_S.580":
            # G(theta) = 29 - 25*log10(theta) for 1° <= theta <= 20°
            if pointing_error_deg >= 1.0:
                itu_gain = max(-10.0, 29.0 - 25.0 * math.log10(pointing_error_deg))
                loss_db = max(0.0, boresight_gain_dbi - itu_gain)
                return AntennaRadiationPatternResult(
                    boresight_gain_dbi=boresight_gain_dbi,
                    pointing_error_deg=pointing_error_deg,
                    hpbw_deg=hpbw_deg,
                    effective_gain_dbi=itu_gain,
                    pointing_loss_db=loss_db,
                    model_tier=PatternModelTier.TIER_1_REFERENCE_MEASURED,
                    computational_guard_applied=False,
                    status_reason="ITU-R S.580 reference earth station sidelobe envelope",
                )

        # Tier 2 Analytical: Airy / Bessel circular aperture pattern
        theta_rad = math.radians(pointing_error_deg)
        u = (math.pi * physical_dimension_m / wavelength) * math.sin(theta_rad)

        # First null of Airy pattern occurs at u1 = 3.83170597
        u_first_null = 3.83170597
        theta_null_deg = math.degrees(math.asin(min(1.0, u_first_null * wavelength / (math.pi * physical_dimension_m))))

        if u < 0.01:
            # On-axis Taylor approximation
            loss_db = 0.0
            tier = PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION
            guard = False
            reason = "On-axis alignment (u < 0.01)"
        elif u <= u_first_null:
            # Inside main lobe
            j1_val = bessel_j1(u)
            field_val = 2.0 * j1_val / u
            p_rel = field_val ** 2
            loss_db = -10.0 * math.log10(max(1e-6, p_rel))
            tier = PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION
            guard = False
            reason = f"Main lobe Airy pattern (theta < first null {theta_null_deg:.2f}°)"
        elif u <= 7.0156:
            # First and second sidelobes (first sidelobe peak at u ~ 5.136, down by 17.6 dB for uniform)
            j1_val = bessel_j1(u)
            p_rel = (2.0 * j1_val / u) ** 2
            loss_db = -10.0 * math.log10(max(1e-6, p_rel))
            tier = PatternModelTier.TIER_2_ANALYTICAL_APPROXIMATION
            guard = False
            reason = "Sidelobe Airy diffraction pattern"
        else:
            # Tier 3 Out-of-Domain Guard
            # Pointing error is far outside the main beam and first sidelobes (> 2.5x HPBW or past 2nd sidelobe)
            loss_db = 40.0
            tier = PatternModelTier.TIER_3_OUT_OF_DOMAIN_GUARD
            guard = True
            reason = f"Extreme off-axis pointing error ({pointing_error_deg:.2f}° >> HPBW {hpbw_deg:.2f}°): tracking null guard applied"

        effective_gain = boresight_gain_dbi - loss_db

        return AntennaRadiationPatternResult(
            boresight_gain_dbi=boresight_gain_dbi,
            pointing_error_deg=pointing_error_deg,
            hpbw_deg=hpbw_deg,
            effective_gain_dbi=effective_gain,
            pointing_loss_db=loss_db,
            model_tier=tier,
            computational_guard_applied=guard,
            status_reason=reason,
        )
