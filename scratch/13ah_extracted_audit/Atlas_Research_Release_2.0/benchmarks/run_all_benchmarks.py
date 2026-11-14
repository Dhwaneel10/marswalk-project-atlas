"""
Milestone 13AF — Master Benchmark Runner.
Executes the four independent reference benchmarks, compiles results, verifies tolerances, and outputs summary JSON.
"""

import json
from pathlib import Path

import benchmark_optical_dust
import benchmark_rf_dust
import benchmark_receiver_noise
import benchmark_antenna_patterns


def main():
    print("============================================================================")
    print("  PROJECT ATLAS — MILESTONE 13AF INDEPENDENT BENCHMARK SUITE")
    print("============================================================================")

    res_opt = benchmark_optical_dust.run_benchmark()
    print(f"[BENCHMARK 1] Optical Dust Spectral Extinction: {res_opt['status']}")
    print(f"             Flagship Loss (alpha = -0.082, tau=0.5): {res_opt['actual_flagship_loss_db']} dB (Expected: {res_opt['expected_flagship_loss_db']} dB)")

    res_rf = benchmark_rf_dust.run_benchmark()
    print(f"[BENCHMARK 2] RF Dust Attenuation: {res_rf['status']}")
    print(f"             Typical Ka Zenith: {res_rf['typical_ka_zenith_loss_db']} dB | Severe Ka Zenith: {res_rf['severe_ka_zenith_loss_db']} dB")
    print(f"             Model A vs Model B Difference: {res_rf['model_a_vs_model_b_diff_pct']}% | Rayleigh size param check: {res_rf['rayleigh_validity_confirmed']}")

    res_noise = benchmark_receiver_noise.run_benchmark()
    print(f"[BENCHMARK 3] Receiver System Noise & CMB Brightness: {res_noise['status']}")
    print(f"             Ka-Band RJ Equivalent: {res_noise['ka_band_t_rj_k']} K (Departure: {res_noise['ka_band_departure_k']} K)")
    print(f"             Plane A vs Plane B Invariance Delta: {res_noise['reference_plane_invariance']['delta_db']} dB")

    res_ant = benchmark_antenna_patterns.run_benchmark()
    print(f"[BENCHMARK 4] Antenna Diffraction & Field Regions: {res_ant['status']}")
    print(f"             Airy First Sidelobe: -{res_ant['first_sidelobe_level_db']} dB (Expected: -17.57 dB)")
    print(f"             Small Monopole Fraunhofer: {res_ant['small_monopole_fraunhofer']['r_fraunhofer_m']} m ({res_ant['small_monopole_fraunhofer']['governing_condition']})")
    print(f"             Large Dish Fraunhofer: {res_ant['large_dish_fraunhofer']['r_fraunhofer_m']} m ({res_ant['large_dish_fraunhofer']['governing_condition']})")

    all_passed = (
        res_opt["status"] == "PASS"
        and res_rf["status"] == "PASS"
        and res_noise["status"] == "PASS"
        and res_ant["status"] == "PASS"
    )

    overall_status = "ALL_BENCHMARKS_PASSED" if all_passed else "BENCHMARK_FAILURE"
    print("----------------------------------------------------------------------------")
    print(f"OVERALL BENCHMARK STATUS: {overall_status}")
    print("============================================================================")

    master_summary = {
        "milestone": "13AF",
        "benchmark_suite_status": overall_status,
        "optical_dust": res_opt,
        "rf_dust": res_rf,
        "receiver_noise_and_cmb": res_noise,
        "antenna_patterns": res_ant,
    }

    out_file = Path(__file__).parent / "benchmark_results_summary.json"
    out_file.write_text(json.dumps(master_summary, indent=2), encoding="utf-8")
    print(f"Summary JSON saved to {out_file}")


if __name__ == "__main__":
    main()
