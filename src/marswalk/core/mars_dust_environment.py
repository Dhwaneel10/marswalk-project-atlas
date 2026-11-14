"""
MarsWalk 2.0 / Project Atlas — Milestone 13L: Mars Dust & Atmospheric Visibility Model.

Models atmospheric optical depth (tau), dust storm loading, and instrument-specific
suitability degradation for optical and remote-sensing instruments across Jezero Crater.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any

# Maximum tolerable atmospheric optical depth (tau) per science instrument
INSTRUMENT_MAX_TAU_LIMITS: Dict[str, float] = {
    "MASTCAM_Z": 1.8,   # High-resolution multispectral stereo imaging
    "SUPERCAM": 1.5,    # Remote LIBS and Raman spectroscopy
    "SHERLOC": 2.0,     # Deep UV fluorescence (proximity arm)
    "PIXL": 2.5,        # Micro-focus X-ray fluorescence (proximity arm)
    "RIMFAX": 6.0,      # Ground-penetrating radar (unaffected by dust)
    "MEDA": 8.0,        # In-situ meteorological station (monitors dust)
}


@dataclass(frozen=True)
class DustEvaluationResult:
    """Atmospheric opacity and optical suitability result for a given instrument."""
    sol: int
    ltst_hours: float
    optical_depth_tau: float
    visibility_status: str  # "NOMINAL_CLEAR", "MODERATE_HAZE", "DUST_STORM", "GLOBAL_STORM"
    instrument_name: Optional[str]
    is_instrument_suitable: bool
    tau_margin: Optional[float]
    optical_degradation_pct: float
    dust_violation_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sol": self.sol,
            "ltst_hours": round(self.ltst_hours, 3),
            "optical_depth_tau": round(self.optical_depth_tau, 2),
            "visibility_status": self.visibility_status,
            "instrument_name": self.instrument_name,
            "is_instrument_suitable": self.is_instrument_suitable,
            "tau_margin": round(self.tau_margin, 2) if self.tau_margin is not None else None,
            "optical_degradation_pct": round(self.optical_degradation_pct, 1),
            "dust_violation_reason": self.dust_violation_reason,
        }


class MarsDustEnvironmentEngine:
    """
    Computes atmospheric dust extinction, visibility states, and instrument operational suitability.
    """

    BASELINE_TAU = 0.45  # Typical background clear atmospheric opacity at Jezero Crater

    def __init__(self, base_tau: float = BASELINE_TAU) -> None:
        self.base_tau = base_tau

    def get_visibility_category(self, tau: float) -> str:
        """Classify atmospheric dust opacity into operational categories."""
        if tau < 0.6:
            return "NOMINAL_CLEAR"
        elif tau < 1.4:
            return "MODERATE_HAZE"
        elif tau < 3.0:
            return "DUST_STORM"
        else:
            return "GLOBAL_STORM"

    def compute_optical_degradation_pct(self, tau: float) -> float:
        """
        Estimate optical image SNR / contrast degradation percentage based on tau.
        At baseline tau 0.45, degradation is 0%. At tau >= 2.0, degradation approaches 100%.
        """
        if tau <= self.base_tau:
            return 0.0
        # Exponential contrast reduction proxy
        loss = (1.0 - math.exp(-1.2 * (tau - self.base_tau))) * 100.0
        return min(max(loss, 0.0), 100.0)

    def evaluate_instrument_dust_suitability(
        self,
        sol: int,
        ltst_hours: float,
        instrument_name: str,
        current_tau: Optional[float] = None,
        tau_anomaly: float = 0.0,
    ) -> DustEvaluationResult:
        """
        Evaluate if atmospheric dust opacity permits reliable science observations for an instrument.
        """
        tau = current_tau if current_tau is not None else self.base_tau
        tau = max(0.1, tau + tau_anomaly)

        vis_status = self.get_visibility_category(tau)
        deg_pct = self.compute_optical_degradation_pct(tau)

        max_limit = INSTRUMENT_MAX_TAU_LIMITS.get(instrument_name.upper())
        if max_limit is None:
            # Unknown instrument: default suitable
            return DustEvaluationResult(
                sol=sol,
                ltst_hours=ltst_hours,
                optical_depth_tau=tau,
                visibility_status=vis_status,
                instrument_name=instrument_name,
                is_instrument_suitable=True,
                tau_margin=None,
                optical_degradation_pct=deg_pct,
                dust_violation_reason=None,
            )

        margin = max_limit - tau
        is_suitable = tau <= max_limit
        reason = None
        if not is_suitable:
            reason = (
                f"Atmospheric optical depth tau={tau:.2f} exceeds instrument limit "
                f"({max_limit:.1f}) for {instrument_name} ({vis_status})"
            )

        return DustEvaluationResult(
            sol=sol,
            ltst_hours=ltst_hours,
            optical_depth_tau=tau,
            visibility_status=vis_status,
            instrument_name=instrument_name,
            is_instrument_suitable=is_suitable,
            tau_margin=margin,
            optical_degradation_pct=deg_pct,
            dust_violation_reason=reason,
        )
