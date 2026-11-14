"""
Milestone 13AF — Independent Benchmark: Optical Dust Spectral Extinction.

Standalone reference calculation:
- Independent Ångström power-law function: tau(lambda) = tau(lambda_0) * (lambda / lambda_0)^(-alpha)
- Independent spherical Chapman airmass integration via numerical quadrature.
- Multi-study literature sensitivity table (Lemmon 2014, Fernandez-Rodriguez 2024, Wolff 2009).
- Comparison with Atlas production targets without importing Atlas production modules.
"""

import math
from typing import Dict, Any, List
from scipy.integrate import quad

SPEED_OF_LIGHT = 299792458.0
MARS_RADIUS_M = 3389.5e3
DEFAULT_SCALE_HEIGHT_M = 11100.0


def standalone_angstrom_tau(tau_0: float, lambda_m: float, lambda_0_m: float, alpha: float) -> float:
    """Computes spectral optical depth from power law: tau(lambda) = tau_0 * (lambda / lambda_0)^(-alpha)"""
    return tau_0 * ((lambda_m / lambda_0_m) ** (-alpha))


def standalone_beer_lambert_db(tau: float, airmass: float) -> float:
    """Beer-Lambert decibel path loss: A_dB = 10 * log10(e) * tau * X"""
    return 10.0 * math.log10(math.e) * tau * airmass


def standalone_spherical_chapman_airmass(elevation_deg: float, H_m: float = DEFAULT_SCALE_HEIGHT_M, R_m: float = MARS_RADIUS_M) -> float:
    """
    Independent numerical quadrature of Chapman path integral through an exponential atmosphere:
    s(theta, r) along slant path from surface (R + z0) to infinity.
    """
    if elevation_deg <= 0.0:
        return float("inf")
    el_rad = math.radians(elevation_deg)
    r0 = R_m

    def integrand(s: float) -> float:
        r = math.sqrt(r0**2 + s**2 + 2.0 * r0 * s * math.sin(el_rad))
        z = r - R_m
        return math.exp(-z / H_m)

    s_max = 20.0 * H_m / max(0.05, math.sin(el_rad))
    val, _ = quad(integrand, 0.0, s_max, epsabs=1e-7, epsrel=1e-7)
    return val / H_m


def run_benchmark() -> Dict[str, Any]:
    lambda_0 = 880e-9
    lambda_target = 1550e-9

    cases = [
        {
            "id": "CONF-OPT-01",
            "name": "Lemmon et al. 2014 Upper Bound (Severe Dust)",
            "alpha": -0.160,
            "evidence_class": "EMPIRICAL_IN_SITU_BOUND",
            "source": "Lemmon et al. (2014) Icarus 251, 96-111",
        },
        {
            "id": "CONF-OPT-02",
            "name": "Fernandez-Rodriguez et al. 2024 (Atlas Reference)",
            "alpha": -0.082,
            "evidence_class": "PUBLISHED_MODELING_EXTRAPOLATION",
            "source": "Fernandez-Rodriguez et al. (2024) arXiv:2404.16955 / 2504.16955",
        },
        {
            "id": "CONF-OPT-03",
            "name": "Wolff et al. 2009 CRISM Mean",
            "alpha": -0.047,
            "evidence_class": "EMPIRICAL_RETRIEVAL_FIT",
            "source": "Wolff et al. (2009) J. Geophys. Res. 114, E00D04",
        },
        {
            "id": "CONF-OPT-04",
            "name": "Lemmon et al. 2014 Lower Bound (Clear Haze)",
            "alpha": -0.036,
            "evidence_class": "EMPIRICAL_IN_SITU_BOUND",
            "source": "Lemmon et al. (2014) Icarus 251, 96-111",
        },
        {
            "id": "CONF-OPT-05",
            "name": "Terrestrial Fine Aerosol (13AD Discredited)",
            "alpha": +0.350,
            "evidence_class": "DISCREDITED_TERRESTRIAL_ASSUMPTION",
            "source": "Urban aerosol model; unphysical for coarse Mars dust",
        },
    ]

    results = []
    # Test opacities: 0.5 (typical), 1.5 (regional storm), 3.0 (severe storm)
    tau_test_values = [0.5, 1.5, 3.0]
    airmass_zenith = standalone_spherical_chapman_airmass(90.0)
    airmass_10deg = standalone_spherical_chapman_airmass(10.0)

    for c in cases:
        alpha = c["alpha"]
        ratio_1550_880 = (lambda_target / lambda_0) ** (-alpha)

        scenario_data = {}
        for tau_0 in tau_test_values:
            tau_1550 = standalone_angstrom_tau(tau_0, lambda_target, lambda_0, alpha)
            loss_zenith = standalone_beer_lambert_db(tau_1550, airmass_zenith)
            loss_10deg = standalone_beer_lambert_db(tau_1550, airmass_10deg)
            scenario_data[f"tau_{tau_0}"] = {
                "tau_1550": round(tau_1550, 4),
                "zenith_loss_db": round(loss_zenith, 3),
                "slant_10deg_loss_db": round(loss_10deg, 3),
            }

        results.append({
            "id": c["id"],
            "name": c["name"],
            "alpha": alpha,
            "ratio_1550_880": round(ratio_1550_880, 4),
            "evidence_class": c["evidence_class"],
            "source": c["source"],
            "scenarios": scenario_data,
        })

    # Expected flagship validation check:
    # At alpha = -0.082, tau_880 = 0.5: tau_1550 = 0.5238, zenith loss = 2.275 dB
    flagship = next(r for r in results if r["id"] == "CONF-OPT-02")
    expected_flagship_loss = 2.275
    actual_flagship_loss = flagship["scenarios"]["tau_0.5"]["zenith_loss_db"]
    delta_db = abs(actual_flagship_loss - expected_flagship_loss)

    return {
        "benchmark_name": "Optical Dust Spectral Extinction",
        "reference_wavelength_nm": 880.0,
        "target_wavelength_nm": 1550.0,
        "is_extrapolated_wavelength": True,
        "flagship_configuration": "CONF-OPT-02 (alpha = -0.082)",
        "expected_flagship_loss_db": expected_flagship_loss,
        "actual_flagship_loss_db": actual_flagship_loss,
        "delta_db": round(delta_db, 4),
        "status": "PASS" if delta_db < 0.01 else "FAIL",
        "evaluated_configurations": results,
    }


if __name__ == "__main__":
    res = run_benchmark()
    print(f"=== {res['benchmark_name']} ===")
    print(f"Status: {res['status']} (Delta: {res['delta_db']:.4f} dB)")
    for conf in res["evaluated_configurations"]:
        print(f"[{conf['id']}] alpha = {conf['alpha']:+.3f} | ratio = {conf['ratio_1550_880']:.4f} | loss@tau0.5: {conf['scenarios']['tau_0.5']['zenith_loss_db']} dB")
