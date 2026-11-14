"""
MarsWalk 2.0 / Project Atlas — Milestone 13Y: Physical Link Budget & Propagation Model
======================================================================================
Rigorous RF and optical link budget engine for planetary, proximity, and deep-space
communications channels. Enforces physics-based free-space path loss (FSPL),
antenna beam patterns, pointing degradation, receiver noise temperature,
carrier-to-noise density (C/N0), achievable Shannon/discrete data rates, and speed-of-light delays.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import enum
import math
from typing import Any, Dict, List, Optional, Tuple

from marswalk.core.atlas_mars_atmospheric_model import (
    MarsAtmosphericEngine,
    MarsAtmosphericProfile,
)
from marswalk.core.atlas_antenna_model import (
    AdvancedAntennaEngine,
    AntennaCategory,
    FieldRegionClassification,
    PatternModelTier,
)

# Universal Physical Constants
SPEED_OF_LIGHT_M_S: float = 299_792_458.0
BOLTZMANN_CONSTANT_J_K: float = 1.380649e-23
ASTRONOMICAL_UNIT_M: float = 149_597_870_700.0


class CommunicationMedium(str, enum.Enum):
    """Physical transport medium of communication channels."""
    LOCAL_BUS = "LOCAL_BUS"                  # SpaceWire, MIL-STD-1553, CAN, Ethernet backplane
    WIRED_CABLE = "WIRED_CABLE"              # Coaxial or fiber-optic umbilical cable
    RF_WIRELESS = "RF_WIRELESS"              # Free-space radio frequency propagation (UHF, S, X, Ka)
    OPTICAL_FREE_SPACE = "OPTICAL_FREE_SPACE"# Free-space laser communication (1550 nm)


class CommunicationBand(str, enum.Enum):
    """Standardized planetary and deep space communication bands."""
    UHF_PROXIMITY = "UHF_PROXIMITY"      # 401.5 MHz (Surface to Orbiter, Proximity-1)
    S_BAND = "S_BAND"                    # 2.2 GHz (Surface local telemetry)
    X_BAND_PROXIMITY = "X_BAND_PROXIMITY"# 8.4 GHz (Orbiter-to-Orbiter crosslink)
    X_BAND_DEEP_SPACE = "X_BAND_DEEP_SPACE" # 8.42 GHz (Orbiter/Settlement to Earth DSN)
    KA_BAND_DEEP_SPACE = "KA_BAND_DEEP_SPACE" # 32.0 GHz (High-rate Orbiter to Earth DSN)
    OPTICAL_LASER = "OPTICAL_LASER"      # 1550 nm (~193.4 THz, Deep Space Optical Comms)


# Standard operational carrier frequencies in Hertz
CARRIER_FREQUENCIES_HZ: Dict[CommunicationBand, float] = {
    CommunicationBand.UHF_PROXIMITY: 401.5e6,
    CommunicationBand.S_BAND: 2.2e9,
    CommunicationBand.X_BAND_PROXIMITY: 8.4e9,
    CommunicationBand.X_BAND_DEEP_SPACE: 8.42e9,
    CommunicationBand.KA_BAND_DEEP_SPACE: 32.0e9,
    CommunicationBand.OPTICAL_LASER: SPEED_OF_LIGHT_M_S / 1550e-9,  # ~1.934145e14 Hz
}

# Discrete operational modulation/coding steps (bps)
STANDARD_DATA_RATES_BPS: List[int] = [
    8_000,
    16_000,
    32_000,
    64_000,
    128_000,
    256_000,
    512_000,
    1_000_000,
    2_000_000,
    4_000_000,
    10_000_000,
    25_000_000,
    50_000_000,
    100_000_000,
    250_000_000,
]


@dataclass(frozen=True)
class TransmitterSpec:
    """RF/Optical transmitter specifications."""
    name: str
    band: CommunicationBand
    power_watts: float
    antenna_gain_dbi: float
    cable_loss_db: float = 1.0
    pointing_error_deg: float = 0.05
    carrier_freq_hz: Optional[float] = None

    def get_frequency_hz(self) -> float:
        if self.carrier_freq_hz is not None:
            if math.isnan(self.carrier_freq_hz) or math.isinf(self.carrier_freq_hz):
                raise ValueError(f"Transmitter carrier_freq_hz must be a finite number, got {self.carrier_freq_hz}")
            if self.carrier_freq_hz <= 0:
                raise ValueError(f"Transmitter carrier_freq_hz must be positive, got {self.carrier_freq_hz}")
            return self.carrier_freq_hz
        return CARRIER_FREQUENCIES_HZ[self.band]

    @property
    def power_dbw(self) -> float:
        if math.isnan(self.power_watts) or math.isinf(self.power_watts):
            raise ValueError(f"Transmitter power_watts must be a finite real number, got {self.power_watts}")
        if self.power_watts <= 0:
            return -999.0
        return 10.0 * math.log10(self.power_watts)

    @property
    def eirp_dbw(self) -> float:
        """Equivalent Isotropically Radiated Power in dBW."""
        if math.isnan(self.antenna_gain_dbi) or math.isinf(self.antenna_gain_dbi):
            raise ValueError(f"Transmitter antenna_gain_dbi must be a finite real number, got {self.antenna_gain_dbi}")
        if math.isnan(self.cable_loss_db) or math.isinf(self.cable_loss_db):
            raise ValueError(f"Transmitter cable_loss_db must be a finite real number, got {self.cable_loss_db}")
        return self.power_dbw + self.antenna_gain_dbi - self.cable_loss_db


@dataclass(frozen=True)
class ReceiverSpec:
    """RF/Optical receiver specifications."""
    name: str
    band: CommunicationBand
    antenna_gain_dbi: float
    sys_noise_temp_k: float = 200.0  # System noise temperature (Kelvin)
    req_eb_n0_db: float = 2.5        # Required Eb/N0 for target BER (e.g. 1e-6 with LDPC)
    min_link_margin_db: float = 3.0  # Operational safety margin
    implementation_loss_db: float = 1.5
    elevation_mask_deg: float = 5.0  # Minimum line-of-sight elevation above local horizon

    @property
    def noise_spectral_density_dbw_hz(self) -> float:
        """N0 = k_B * T_sys in dBW/Hz."""
        if math.isnan(self.sys_noise_temp_k) or math.isinf(self.sys_noise_temp_k):
            raise ValueError(f"Receiver sys_noise_temp_k must be a finite real number, got {self.sys_noise_temp_k}")
        if self.sys_noise_temp_k <= 0:
            raise ValueError(f"Receiver sys_noise_temp_k must be strictly positive (> 0 K), got {self.sys_noise_temp_k}")
        return 10.0 * math.log10(BOLTZMANN_CONSTANT_J_K * self.sys_noise_temp_k)

    @staticmethod
    def calculate_system_noise_temp(
        t_antenna_k: float = 210.0,
        noise_figure_db: float = 2.0,
        cable_loss_db: float = 1.0,
        t_phys_k: float = 250.0,
    ) -> float:
        """
        Calculates total system noise temperature T_sys from antenna, feed cable, and receiver contributions:
        T_sys = T_ant + T_feed + T_rx * L_feed
        where T_feed = (L_feed - 1) * T_phys and T_rx = (10^(NF/10) - 1) * 290.0 K.
        Positivity (T_sys > 0 K) is an operating domain requirement of the Johnson-Nyquist thermal model.
        """
        if math.isnan(t_antenna_k) or math.isnan(noise_figure_db) or math.isnan(cable_loss_db) or math.isnan(t_phys_k):
            raise ValueError("Temperature parameters cannot be NaN")
        if t_antenna_k < 2.7:
            raise ValueError(f"Antenna brightness temperature cannot be below CMB (2.7 K), got {t_antenna_k} K")
        if noise_figure_db < 0.0 or cable_loss_db < 0.0 or t_phys_k <= 0.0:
            raise ValueError("Noise figure and cable loss must be non-negative; physical temperature must be positive")

        l_feed = 10.0 ** (cable_loss_db / 10.0)
        f_lin = 10.0 ** (noise_figure_db / 10.0)
        t_rx = (f_lin - 1.0) * 290.0
        t_feed = (l_feed - 1.0) * t_phys_k
        return t_antenna_k + t_feed + t_rx * l_feed


@dataclass
class LinkBudgetResult:
    """Comprehensive output of a link budget calculation."""
    slant_range_m: float
    elevation_deg: float
    carrier_freq_hz: float
    wavelength_m: float
    fspl_db: float
    eirp_dbw: float
    pointing_loss_db: float
    atmospheric_loss_db: float
    received_power_dbw: float
    noise_spectral_density_dbw_hz: float
    c_n0_dbhz: float
    available_eb_n0_db: float
    link_margin_db: float
    max_theoretical_rate_bps: float
    operational_rate_bps: int
    propagation_delay_s: float
    is_link_closed: bool
    status_reason: str
    is_physically_available: bool = True
    operating_domain: str = "FAR_FIELD_FREE_SPACE"
    validation_status: str = "VALID"
    evidence_class: str = "THEORETICAL_DERIVED"
    communication_medium: CommunicationMedium = CommunicationMedium.RF_WIRELESS
    antenna_category: str = "PARABOLIC_REFLECTOR"
    field_region: str = "FRAUNHOFER_FAR_FIELD"
    pointing_model_tier: str = "TIER_2_ANALYTICAL_APPROXIMATION"
    pointing_guard_applied: bool = False
    spectral_optical_depth: Optional[float] = None

    def calculate_transmission_time_s(self, payload_bytes: int) -> float:
        """Total time required to serialize and transmit payload bytes across the link."""
        if payload_bytes <= 0:
            return 0.0
        if self.operational_rate_bps <= 0 or not self.is_link_closed or not self.is_physically_available:
            return float("inf")
        payload_bits = payload_bytes * 8
        return payload_bits / float(self.operational_rate_bps)

    def calculate_total_delivery_latency_s(self, payload_bytes: int) -> float:
        """Transmission serialization time + speed-of-light propagation latency."""
        tx_time = self.calculate_transmission_time_s(payload_bytes)
        if math.isinf(tx_time):
            return float("inf")
        return tx_time + self.propagation_delay_s

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slant_range_km": round(self.slant_range_m / 1000.0, 3),
            "elevation_deg": round(self.elevation_deg, 2),
            "carrier_freq_mhz": round(self.carrier_freq_hz / 1e6, 3),
            "fspl_db": round(self.fspl_db, 2),
            "eirp_dbw": round(self.eirp_dbw, 2),
            "received_power_dbw": round(self.received_power_dbw, 2),
            "c_n0_dbhz": round(self.c_n0_dbhz, 2),
            "link_margin_db": round(self.link_margin_db, 2),
            "operational_rate_kbps": round(self.operational_rate_bps / 1000.0, 2),
            "propagation_delay_s": round(self.propagation_delay_s, 6),
            "is_link_closed": self.is_link_closed,
            "status_reason": self.status_reason,
            "is_physically_available": self.is_physically_available,
            "operating_domain": self.operating_domain,
            "validation_status": self.validation_status,
            "evidence_class": self.evidence_class,
            "communication_medium": (
                self.communication_medium.value
                if isinstance(self.communication_medium, CommunicationMedium)
                else str(self.communication_medium)
            ),
            "antenna_category": self.antenna_category,
            "field_region": self.field_region,
            "pointing_model_tier": self.pointing_model_tier,
            "pointing_guard_applied": self.pointing_guard_applied,
            "spectral_optical_depth": self.spectral_optical_depth,
        }


class PhysicalLinkBudgetEngine:
    """Deterministic, high-fidelity RF and optical link budget evaluation engine."""

    @staticmethod
    def calculate_antenna_aperture_diameter_m(
        gain_dbi: float,
        freq_hz: float,
        efficiency: float = 0.55,
    ) -> float:
        """
        Calculates effective circular antenna physical aperture diameter (meters) from gain (dBi) and carrier frequency (Hz).
        Formula: Gain = eta * (pi * D / lambda)^2
        D = (lambda / pi) * sqrt(10^(gain_dbi / 10) / eta)
        For low-gain antennas (<= 3 dBi) like dipoles or patches, aperture is approximated as lambda / 2.
        """
        if math.isnan(gain_dbi) or math.isnan(freq_hz):
            raise ValueError(f"Gain ({gain_dbi}) and frequency ({freq_hz}) cannot be NaN")
        if math.isinf(gain_dbi) or math.isinf(freq_hz):
            raise ValueError(f"Gain ({gain_dbi}) and frequency ({freq_hz}) must be finite real numbers")
        if freq_hz <= 0:
            raise ValueError(f"Carrier frequency must be strictly positive (> 0 Hz), got {freq_hz}")

        wavelength_m = SPEED_OF_LIGHT_M_S / freq_hz
        if gain_dbi <= 3.0:
            return max(0.01, wavelength_m / 2.0)

        linear_gain = 10.0 ** (gain_dbi / 10.0)
        eff = max(0.1, min(1.0, efficiency))
        diameter = (wavelength_m / math.pi) * math.sqrt(linear_gain / eff)
        return max(0.01, diameter)

    @staticmethod
    def calculate_fraunhofer_distance_m(
        aperture_diameter_m: float,
        freq_hz: float,
    ) -> float:
        """
        Calculates Fraunhofer far-field boundary distance (meters):
        R_ff = 2 * D^2 / lambda (where lambda = c / f)
        For small antennas where D < lambda, far-field boundary is bounded by 2 * lambda.
        """
        if math.isnan(aperture_diameter_m) or math.isnan(freq_hz):
            raise ValueError(f"Aperture diameter ({aperture_diameter_m}) and frequency ({freq_hz}) cannot be NaN")
        if math.isinf(aperture_diameter_m) or math.isinf(freq_hz):
            raise ValueError(f"Aperture diameter ({aperture_diameter_m}) and frequency ({freq_hz}) must be finite")
        if freq_hz <= 0:
            raise ValueError(f"Carrier frequency must be strictly positive (> 0 Hz), got {freq_hz}")
        if aperture_diameter_m < 0:
            raise ValueError(f"Aperture diameter cannot be negative, got {aperture_diameter_m}")

        wavelength_m = SPEED_OF_LIGHT_M_S / freq_hz
        r_ff = (2.0 * (aperture_diameter_m ** 2)) / wavelength_m
        return max(r_ff, 2.0 * wavelength_m)

    @staticmethod
    def calculate_free_space_path_loss(range_m: float, freq_hz: float) -> float:
        """
        Calculates Free-Space Path Loss (FSPL) in dB:
        FSPL = 20 * log10(4 * pi * R * f / c)

        Physical domain constraints:
        - range_m < 0: strictly invalid physical input (raises ValueError).
        - range_m == 0: collocated limit; free-space spherical wave propagation is
          undefined (raises ValueError). Collocated nodes must be evaluated via direct bus/cable interface.
        - range_m < lambda / (4 * pi): sub-wavelength reactive near field where Friis formula
          yields FSPL < 0 dB (unphysical passive power amplification, violating conservation of energy).
        """
        if math.isnan(range_m) or math.isnan(freq_hz):
            raise ValueError(f"Range ({range_m}) and frequency ({freq_hz}) cannot be NaN")
        if math.isinf(range_m) or math.isinf(freq_hz):
            raise ValueError(f"Range ({range_m}) and frequency ({freq_hz}) must be finite real numbers")
        if freq_hz <= 0:
            raise ValueError(f"Carrier frequency must be strictly positive (> 0 Hz), got {freq_hz}")
        if range_m < 0:
            raise ValueError(f"Propagation range cannot be negative, got {range_m} m")
        if range_m == 0:
            raise ValueError("Propagation range cannot be zero for far-field free-space link. Collocated nodes require direct local/wired interface.")

        wavelength = SPEED_OF_LIGHT_M_S / freq_hz
        reactive_limit = wavelength / (4.0 * math.pi)
        if range_m < reactive_limit:
            raise ValueError(
                f"Propagation range {range_m:.4f} m is within sub-wavelength reactive near-field "
                f"(R < lambda / (4*pi) = {reactive_limit:.4f} m); Friis free-space formula is invalid (yields negative loss)."
            )

        ratio = (4.0 * math.pi * range_m) / wavelength
        return 20.0 * math.log10(ratio)

    @staticmethod
    def calculate_pointing_loss(
        pointing_error_deg: float,
        antenna_gain_dbi: float,
        freq_hz: float,
    ) -> float:
        """
        Calculates off-axis pointing loss in dB for antenna aperture.
        Routes through AdvancedAntennaEngine to evaluate Bessel / Airy diffraction pattern
        F(u) = |2 * J1(u) / u|^2 and provides explicit out-of-domain guard disclosure.
        """
        if math.isnan(pointing_error_deg) or math.isnan(antenna_gain_dbi) or math.isnan(freq_hz):
            raise ValueError("Pointing loss parameters cannot be NaN")
        if math.isinf(pointing_error_deg) or math.isinf(antenna_gain_dbi) or math.isinf(freq_hz):
            raise ValueError("Pointing loss parameters must be finite real numbers")

        d_m = PhysicalLinkBudgetEngine.calculate_antenna_aperture_diameter_m(antenna_gain_dbi, freq_hz)
        category = AntennaCategory.DIPOLE_OMNI if antenna_gain_dbi <= 3.0 else AntennaCategory.PARABOLIC_REFLECTOR
        res = AdvancedAntennaEngine.evaluate_radiation_pattern(
            boresight_gain_dbi=antenna_gain_dbi,
            physical_dimension_m=d_m,
            carrier_freq_hz=freq_hz,
            pointing_error_deg=pointing_error_deg,
            category=category,
        )
        return res.pointing_loss_db

    @staticmethod
    def calculate_atmospheric_loss(
        band: CommunicationBand,
        elevation_deg: float,
        dust_tau: float = 0.5,
    ) -> float:
        """
        Estimates Martian atmospheric attenuation in dB using rigorous spherical radiative transfer.

        Physical domain constraints:
        - elevation_deg <= 0.0: Target is below or on local horizontal horizon (occulted by Mars curvature).
          Atmospheric line-of-sight loss is undefined (raises ValueError).
        - Dust optical depth tau follows Beer-Lambert exponential extinction with Ångström
          spectral scaling for optical wavelengths, and strictly decoupled Rayleigh gas absorption for RF bands.
        """
        if math.isnan(elevation_deg) or math.isnan(dust_tau):
            raise ValueError(f"Atmospheric loss parameters cannot be NaN (elevation={elevation_deg}, dust_tau={dust_tau})")
        if math.isinf(elevation_deg) or math.isinf(dust_tau):
            raise ValueError("Atmospheric loss parameters must be finite real numbers")
        if dust_tau < 0.0:
            raise ValueError(f"Dust optical depth tau cannot be negative, got {dust_tau}")
        if elevation_deg <= 0.0:
            raise ValueError(f"Atmospheric loss undefined for sub-horizon elevation ({elevation_deg:.2f}° <= 0°); target is geometrically occulted.")

        if band == CommunicationBand.OPTICAL_LASER:
            opt_res = MarsAtmosphericEngine.calculate_optical_attenuation_db(
                elevation_deg=elevation_deg,
                wavelength_m=1550e-9,
                tau_880nm=dust_tau,
            )
            return float(opt_res["attenuation_db"])
        else:
            freq_hz = CARRIER_FREQUENCIES_HZ.get(band, 8.4e9)
            airmass_res = MarsAtmosphericEngine.calculate_spherical_airmass(elevation_deg)
            return MarsAtmosphericEngine.calculate_rf_atmospheric_attenuation_db(
                carrier_freq_hz=freq_hz,
                elevation_deg=elevation_deg,
                airmass=airmass_res.spherical_airmass,
                dust_tau=dust_tau,
            )

    @classmethod
    def evaluate_link(
        cls,
        tx: TransmitterSpec,
        rx: ReceiverSpec,
        slant_range_m: float,
        elevation_deg: float = 45.0,
        dust_tau: float = 0.5,
    ) -> LinkBudgetResult:
        """
        Evaluates complete end-to-end link budget between a transmitter and receiver.
        Strictly enforces physical validity boundaries, near-field/far-field domains,
        and elevation masks.
        """
        if math.isnan(slant_range_m) or math.isinf(slant_range_m):
            raise ValueError(f"slant_range_m must be a finite real number, got {slant_range_m}")
        if slant_range_m < 0:
            raise ValueError(f"slant_range_m cannot be negative, got {slant_range_m}")
        if math.isnan(elevation_deg) or math.isinf(elevation_deg):
            raise ValueError(f"elevation_deg must be a finite real number, got {elevation_deg}")
        if math.isnan(dust_tau) or math.isinf(dust_tau):
            raise ValueError(f"dust_tau must be a finite real number, got {dust_tau}")
        if dust_tau < 0.0:
            raise ValueError(f"dust_tau cannot be negative, got {dust_tau}")

        freq_hz = tx.get_frequency_hz()
        wavelength_m = SPEED_OF_LIGHT_M_S / freq_hz
        propagation_delay_s = slant_range_m / SPEED_OF_LIGHT_M_S

        # Determine communication medium and antenna classification
        if slant_range_m == 0.0:
            medium = CommunicationMedium.LOCAL_BUS
            ant_category = AntennaCategory.DIPOLE_OMNI
        elif tx.band == CommunicationBand.OPTICAL_LASER:
            medium = CommunicationMedium.OPTICAL_FREE_SPACE
            ant_category = AntennaCategory.OPTICAL_TELESCOPE
        elif tx.antenna_gain_dbi <= 3.0:
            medium = CommunicationMedium.RF_WIRELESS
            ant_category = AntennaCategory.DIPOLE_OMNI
        else:
            medium = CommunicationMedium.RF_WIRELESS
            ant_category = AntennaCategory.PARABOLIC_REFLECTOR

        d_tx = cls.calculate_antenna_aperture_diameter_m(tx.antenna_gain_dbi, freq_hz)
        d_rx = cls.calculate_antenna_aperture_diameter_m(rx.antenna_gain_dbi, freq_hz)
        d_max = max(d_tx, d_rx)

        # Field region boundary calculation (IEEE 145 & ISED GL-01)
        field_analysis = AdvancedAntennaEngine.calculate_field_regions(
            physical_dimension_m=d_max,
            carrier_freq_hz=freq_hz,
            category=ant_category,
        )
        r_ff = field_analysis.fraunhofer_far_field_distance_m
        field_region_class = (
            FieldRegionClassification.REACTIVE_NEAR_FIELD
            if slant_range_m == 0.0
            else field_analysis.classify_distance(slant_range_m)
        )

        # 1. Collocated nodes boundary (R == 0): direct wired/bus connection
        if slant_range_m == 0.0:
            return LinkBudgetResult(
                slant_range_m=0.0,
                elevation_deg=elevation_deg,
                carrier_freq_hz=freq_hz,
                wavelength_m=wavelength_m,
                fspl_db=0.0,
                eirp_dbw=tx.eirp_dbw,
                pointing_loss_db=0.0,
                atmospheric_loss_db=0.0,
                received_power_dbw=tx.power_dbw,
                noise_spectral_density_dbw_hz=rx.noise_spectral_density_dbw_hz,
                c_n0_dbhz=120.0,
                available_eb_n0_db=30.0,
                link_margin_db=30.0,
                max_theoretical_rate_bps=1_000_000_000.0,
                operational_rate_bps=1_000_000_000,
                propagation_delay_s=0.0,
                is_link_closed=True,
                status_reason="Collocated nodes: direct local/wired bus connection (zero free-space propagation)",
                is_physically_available=True,
                operating_domain="COLLOCATED_LOCAL_INTERFACE",
                validation_status="VALID_LOCAL_DIRECT",
                evidence_class="THEORETICAL_DERIVED",
                communication_medium=CommunicationMedium.LOCAL_BUS,
                antenna_category="DIRECT_BUS_COUPLER",
                field_region="COLLOCATED_INTERFACE",
                pointing_model_tier="NOT_APPLICABLE",
                pointing_guard_applied=False,
                spectral_optical_depth=None,
            )

        # 2. Check if unpowered transmitter
        if tx.power_watts <= 0:
            try:
                fspl_val = cls.calculate_free_space_path_loss(slant_range_m, freq_hz)
            except ValueError:
                fspl_val = 0.0
            return LinkBudgetResult(
                slant_range_m=slant_range_m,
                elevation_deg=elevation_deg,
                carrier_freq_hz=freq_hz,
                wavelength_m=wavelength_m,
                fspl_db=fspl_val,
                eirp_dbw=tx.eirp_dbw,
                pointing_loss_db=0.0,
                atmospheric_loss_db=0.0,
                received_power_dbw=-999.0,
                noise_spectral_density_dbw_hz=rx.noise_spectral_density_dbw_hz,
                c_n0_dbhz=-999.0,
                available_eb_n0_db=-999.0,
                link_margin_db=-999.0,
                max_theoretical_rate_bps=0.0,
                operational_rate_bps=0,
                propagation_delay_s=propagation_delay_s,
                is_link_closed=False,
                status_reason="Transmitter unpowered or power_watts <= 0",
                is_physically_available=False,
                operating_domain="UNPOWERED_TRANSMITTER",
                validation_status="PHYSICALLY_UNAVAILABLE",
                evidence_class="THEORETICAL_DERIVED",
                communication_medium=medium,
                antenna_category=ant_category.value,
                field_region=field_region_class.value,
                pointing_model_tier="NOT_APPLICABLE",
                pointing_guard_applied=False,
                spectral_optical_depth=None,
            )

        # 3. Near-field vs Far-field boundary (Fraunhofer distance)
        if slant_range_m < r_ff:
            return LinkBudgetResult(
                slant_range_m=slant_range_m,
                elevation_deg=elevation_deg,
                carrier_freq_hz=freq_hz,
                wavelength_m=wavelength_m,
                fspl_db=0.0,
                eirp_dbw=tx.eirp_dbw,
                pointing_loss_db=0.0,
                atmospheric_loss_db=0.0,
                received_power_dbw=-999.0,
                noise_spectral_density_dbw_hz=rx.noise_spectral_density_dbw_hz,
                c_n0_dbhz=-999.0,
                available_eb_n0_db=-999.0,
                link_margin_db=-999.0,
                max_theoretical_rate_bps=0.0,
                operational_rate_bps=0,
                propagation_delay_s=propagation_delay_s,
                is_link_closed=False,
                status_reason=f"Near-field propagation range ({slant_range_m:.2f} m < Fraunhofer distance {r_ff:.2f} m): far-field free-space model invalid",
                is_physically_available=False,
                operating_domain="NEAR_FIELD_OUT_OF_DOMAIN",
                validation_status="OUT_OF_DOMAIN",
                evidence_class="THEORETICAL_DERIVED",
                communication_medium=medium,
                antenna_category=ant_category.value,
                field_region=field_region_class.value,
                pointing_model_tier="NOT_APPLICABLE",
                pointing_guard_applied=False,
                spectral_optical_depth=None,
            )

        # 4. Elevation boundary checks: Geometric occultation & elevation mask
        if elevation_deg <= 0.0:
            fspl_val = cls.calculate_free_space_path_loss(slant_range_m, freq_hz)
            return LinkBudgetResult(
                slant_range_m=slant_range_m,
                elevation_deg=elevation_deg,
                carrier_freq_hz=freq_hz,
                wavelength_m=wavelength_m,
                fspl_db=fspl_val,
                eirp_dbw=tx.eirp_dbw,
                pointing_loss_db=0.0,
                atmospheric_loss_db=0.0,
                received_power_dbw=-999.0,
                noise_spectral_density_dbw_hz=rx.noise_spectral_density_dbw_hz,
                c_n0_dbhz=-999.0,
                available_eb_n0_db=-999.0,
                link_margin_db=-999.0,
                max_theoretical_rate_bps=0.0,
                operational_rate_bps=0,
                propagation_delay_s=propagation_delay_s,
                is_link_closed=False,
                status_reason=f"Geometrically occulted below local horizon ({elevation_deg:.2f}° <= 0.0°)",
                is_physically_available=False,
                operating_domain="OCCULTED_BELOW_HORIZON",
                validation_status="PHYSICALLY_UNAVAILABLE",
                evidence_class="THEORETICAL_DERIVED",
                communication_medium=medium,
                antenna_category=ant_category.value,
                field_region=field_region_class.value,
                pointing_model_tier="NOT_APPLICABLE",
                pointing_guard_applied=False,
                spectral_optical_depth=None,
            )

        if elevation_deg < rx.elevation_mask_deg:
            fspl_val = cls.calculate_free_space_path_loss(slant_range_m, freq_hz)
            return LinkBudgetResult(
                slant_range_m=slant_range_m,
                elevation_deg=elevation_deg,
                carrier_freq_hz=freq_hz,
                wavelength_m=wavelength_m,
                fspl_db=fspl_val,
                eirp_dbw=tx.eirp_dbw,
                pointing_loss_db=0.0,
                atmospheric_loss_db=0.0,
                received_power_dbw=-999.0,
                noise_spectral_density_dbw_hz=rx.noise_spectral_density_dbw_hz,
                c_n0_dbhz=-999.0,
                available_eb_n0_db=-999.0,
                link_margin_db=-999.0,
                max_theoretical_rate_bps=0.0,
                operational_rate_bps=0,
                propagation_delay_s=propagation_delay_s,
                is_link_closed=False,
                status_reason=f"Below elevation mask ({elevation_deg:.1f}° < {rx.elevation_mask_deg:.1f}°)",
                is_physically_available=False,
                operating_domain="BELOW_ELEVATION_MASK",
                validation_status="PHYSICALLY_UNAVAILABLE",
                evidence_class="THEORETICAL_DERIVED",
                communication_medium=medium,
                antenna_category=ant_category.value,
                field_region=field_region_class.value,
                pointing_model_tier="NOT_APPLICABLE",
                pointing_guard_applied=False,
                spectral_optical_depth=None,
            )

        # 5. Free space path loss (far-field valid regime)
        fspl_db = cls.calculate_free_space_path_loss(slant_range_m, freq_hz)
        eirp_dbw = tx.eirp_dbw

        # Antenna Radiation Pattern and Pointing Evaluation
        pattern_res = AdvancedAntennaEngine.evaluate_radiation_pattern(
            boresight_gain_dbi=tx.antenna_gain_dbi,
            physical_dimension_m=d_tx,
            carrier_freq_hz=freq_hz,
            pointing_error_deg=tx.pointing_error_deg,
            category=ant_category,
        )
        pointing_loss_db = pattern_res.pointing_loss_db
        atm_loss_db = cls.calculate_atmospheric_loss(tx.band, elevation_deg, dust_tau)

        # Spectral Optical Depth (Ångström power-law scaled for 1550 nm: alpha = -0.082 per Fernandez-Rodriguez 2024)
        spectral_tau = None
        if tx.band == CommunicationBand.OPTICAL_LASER:
            spectral_tau = dust_tau * ((1550.0 / 880.0) ** 0.082)

        # Received Power Prx (dBW)
        p_rx_dbw = (
            eirp_dbw
            - fspl_db
            + rx.antenna_gain_dbi
            - pointing_loss_db
            - atm_loss_db
            - rx.implementation_loss_db
        )

        n0_dbw_hz = rx.noise_spectral_density_dbw_hz
        c_n0_dbhz = p_rx_dbw - n0_dbw_hz

        # Required C/N0 for target rate: C/N0_req = (Eb/N0)_req + 10*log10(R) + Margin
        # Maximum rate where Margin >= min_link_margin_db:
        net_budget_db = c_n0_dbhz - rx.req_eb_n0_db - rx.min_link_margin_db
        if net_budget_db <= 0:
            max_rate_bps = 0.0
            operational_rate = 0
            is_closed = False
            margin = net_budget_db
            reason = f"Insufficient link budget: C/N0 ({c_n0_dbhz:.1f} dB-Hz) below threshold"
        else:
            safe_exp = min(net_budget_db / 10.0, 30.0)
            max_rate_bps = 10.0 ** safe_exp
            eligible = [r for r in STANDARD_DATA_RATES_BPS if r <= max_rate_bps]
            if eligible:
                operational_rate = eligible[-1]
                actual_eb_n0 = c_n0_dbhz - 10.0 * math.log10(operational_rate)
                margin = actual_eb_n0 - rx.req_eb_n0_db
                is_closed = margin >= rx.min_link_margin_db
                reason = "Link closed with positive operational margin"
            else:
                operational_rate = 0
                is_closed = False
                margin = net_budget_db
                reason = "Achievable bit rate below minimum supported standard (8 kbps)"

        available_eb_n0 = (
            c_n0_dbhz - 10.0 * math.log10(operational_rate)
            if operational_rate > 0
            else -999.0
        )

        operating_domain = (
            "INTERPLANETARY_DEEP_SPACE"
            if slant_range_m > 100_000_000_000.0
            else "FAR_FIELD_FREE_SPACE"
        )

        return LinkBudgetResult(
            slant_range_m=slant_range_m,
            elevation_deg=elevation_deg,
            carrier_freq_hz=freq_hz,
            wavelength_m=wavelength_m,
            fspl_db=fspl_db,
            eirp_dbw=eirp_dbw,
            pointing_loss_db=pointing_loss_db,
            atmospheric_loss_db=atm_loss_db,
            received_power_dbw=p_rx_dbw,
            noise_spectral_density_dbw_hz=n0_dbw_hz,
            c_n0_dbhz=c_n0_dbhz,
            available_eb_n0_db=available_eb_n0,
            link_margin_db=margin,
            max_theoretical_rate_bps=max_rate_bps,
            operational_rate_bps=operational_rate,
            propagation_delay_s=propagation_delay_s,
            is_link_closed=is_closed,
            status_reason=reason,
            is_physically_available=True,
            operating_domain=operating_domain,
            validation_status="VALID",
            evidence_class="THEORETICAL_DERIVED",
            communication_medium=medium,
            antenna_category=ant_category.value,
            field_region=field_region_class.value,
            pointing_model_tier=pattern_res.model_tier.value,
            pointing_guard_applied=pattern_res.computational_guard_applied,
            spectral_optical_depth=spectral_tau,
        )
