"""
Milestone 13AF — Independent Benchmark: Receiver System Noise & CMB Brightness.

Standalone reference calculation:
- Planck vs Rayleigh-Jeans brightness temperature departure across microwave and optical spectrum.
- Antenna beam pattern integration across 5 operational Martian viewing geometries.
- Exact reference plane invariance proof between Plane A (Antenna Terminals) and Plane B (LNA Input).
- Verification without importing Atlas production modules.
"""

import math
from typing import Dict, Any, List

PLANCK_CONSTANT = 6.62607015e-34
BOLTZMANN_CONSTANT = 1.380649e-23
SPEED_OF_LIGHT = 299792458.0
T_CMB_THERMODYNAMIC = 2.725


def planck_rayleigh_jeans_brightness_temp(freq_hz: float, t_phys: float = T_CMB_THERMODYNAMIC) -> float:
    """Computes exact Rayleigh-Jeans equivalent brightness temperature from Planck function."""
    h_nu_over_k = (PLANCK_CONSTANT * freq_hz) / BOLTZMANN_CONSTANT
    x = h_nu_over_k / t_phys
    if x > 100.0:
        return 0.0  # High-frequency cutoff
    return h_nu_over_k / (math.exp(x) - 1.0)


def evaluate_beam_weighted_antenna_temp(
    main_beam_efficiency: float,
    t_main_brightness: float,
    t_spillover_brightness: float,
) -> float:
    """T_A = eta_M * T_main + (1 - eta_M) * T_spillover"""
    return main_beam_efficiency * t_main_brightness + (1.0 - main_beam_efficiency) * t_spillover_brightness


def evaluate_reference_plane_invariance(
    p_ant_watts: float,
    t_ant_k: float,
    feed_loss_db: float,
    t_phys_feed_k: float,
    rx_noise_figure_db: float,
) -> Dict[str, Any]:
    """
    Computes (C / N_0) at Plane A (Antenna Terminals) vs Plane B (LNA Input).
    Proves mathematical and numerical invariance.
    """
    l_feed = 10.0 ** (feed_loss_db / 10.0)
    t_rx = (10.0 ** (rx_noise_figure_db / 10.0) - 1.0) * 290.0

    # Plane A (Antenna Terminals, Input-Referred)
    t_feed_a = (l_feed - 1.0) * t_phys_feed_k
    t_sys_a = t_ant_k + t_feed_a + l_feed * t_rx
    n0_a = BOLTZMANN_CONSTANT * t_sys_a
    c_n0_a = p_ant_watts / n0_a
    c_n0_a_dbhz = 10.0 * math.log10(c_n0_a)

    # Plane B (LNA Input, Output-Referred)
    p_rx_b = p_ant_watts / l_feed
    t_sys_b = (t_ant_k / l_feed) + (1.0 - 1.0 / l_feed) * t_phys_feed_k + t_rx
    n0_b = BOLTZMANN_CONSTANT * t_sys_b
    c_n0_b = p_rx_b / n0_b
    c_n0_b_dbhz = 10.0 * math.log10(c_n0_b)

    delta_c_n0_db = abs(c_n0_a_dbhz - c_n0_b_dbhz)

    return {
        "plane_a_t_sys_k": round(t_sys_a, 4),
        "plane_b_t_sys_k": round(t_sys_b, 4),
        "t_sys_ratio": round(t_sys_a / t_sys_b, 6),
        "l_feed": round(l_feed, 6),
        "c_n0_plane_a_dbhz": round(c_n0_a_dbhz, 6),
        "c_n0_plane_b_dbhz": round(c_n0_b_dbhz, 6),
        "delta_db": round(delta_c_n0_db, 12),
        "is_invariant": delta_c_n0_db < 1e-9,
    }


def run_benchmark() -> Dict[str, Any]:
    # 1. Planck vs RJ departures
    freqs = {
        "UHF_401_5MHz": 401.5e6,
        "S_BAND_2_2GHz": 2.2e9,
        "X_BAND_8_4GHz": 8.4e9,
        "KA_BAND_32GHz": 32.0e9,
        "OPTICAL_1550nm": SPEED_OF_LIGHT / 1550e-9,
    }

    rj_departures = {}
    for name, freq in freqs.items():
        t_rj = planck_rayleigh_jeans_brightness_temp(freq, T_CMB_THERMODYNAMIC)
        delta_k = t_rj - T_CMB_THERMODYNAMIC
        rel_err_pct = (delta_k / T_CMB_THERMODYNAMIC) * 100.0
        rj_departures[name] = {
            "freq_hz": freq,
            "t_rj_k": round(t_rj, 4),
            "delta_k": round(delta_k, 4),
            "rel_err_pct": round(rel_err_pct, 2),
        }

    # 2. Geometric beam integration cases
    geometries = [
        {"case": "GEO-01_Deep_Space_Dish", "eta": 0.95, "t_main": 3.0, "t_spill": 210.0, "expected_ta": 13.35},
        {"case": "GEO-02_Nadir_Orbiter_Dish", "eta": 0.97, "t_main": 210.0, "t_spill": 2.7, "expected_ta": 203.78},
        {"case": "GEO-03_Rover_Surface_Monopole", "eta": 0.50, "t_main": 10.0, "t_spill": 210.0, "expected_ta": 110.0},
        {"case": "GEO-04_Ground_Horizon_Grazing", "eta": 0.60, "t_main": 50.0, "t_spill": 210.0, "expected_ta": 114.0},
        {"case": "GEO-05_Ideal_Cold_Space_Probe", "eta": 1.00, "t_main": 2.725, "t_spill": 2.725, "expected_ta": 2.725},
    ]

    geom_results = []
    for g in geometries:
        ta = evaluate_beam_weighted_antenna_temp(g["eta"], g["t_main"], g["t_spill"])
        geom_results.append({
            "case": g["case"],
            "calculated_ta_k": round(ta, 3),
            "expected_ta_k": g["expected_ta"],
        })

    # 3. Reference plane invariance test
    invariance_res = evaluate_reference_plane_invariance(
        p_ant_watts=1e-12,
        t_ant_k=150.0,
        feed_loss_db=1.5,
        t_phys_feed_k=250.0,
        rx_noise_figure_db=2.0,
    )

    return {
        "benchmark_name": "Receiver System Noise & CMB Brightness",
        "t_cmb_thermodynamic_k": T_CMB_THERMODYNAMIC,
        "rayleigh_jeans_departures": rj_departures,
        "ka_band_t_rj_k": rj_departures["KA_BAND_32GHz"]["t_rj_k"],
        "ka_band_departure_k": rj_departures["KA_BAND_32GHz"]["delta_k"],
        "geometry_beam_integration": geom_results,
        "reference_plane_invariance": invariance_res,
        "status": "PASS" if invariance_res["is_invariant"] else "FAIL",
    }


if __name__ == "__main__":
    res = run_benchmark()
    print(f"=== {res['benchmark_name']} ===")
    print(f"Status: {res['status']}")
    print(f"Ka-band (32 GHz) RJ Equivalent: {res['ka_band_t_rj_k']} K (Delta: {res['ka_band_departure_k']} K)")
    print(f"Reference Plane Invariance Delta: {res['reference_plane_invariance']['delta_db']} dB")
