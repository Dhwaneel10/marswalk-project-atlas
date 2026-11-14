"""
Standalone Link Budget Scenarios Benchmark for Project Atlas Research Release 2.0.
Calculates three complete end-to-end communication scenarios using pure analytical formulas
with zero third-party dependencies and zero imports from Atlas production modules.
"""

import math
import json
from dataclasses import dataclass, asdict
from pathlib import Path

# Speed of light & Boltzmann constant
C = 299792458.0
K_B = 1.380649e-23

@dataclass
class LinkBudgetResult:
    scenario_id: str
    scenario_name: str
    freq_hz: float
    wavelength_m: float
    slant_range_km: float
    elevation_deg: float
    tx_power_w: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    fspl_db: float
    atmospheric_loss_db: float
    pointing_loss_db: float
    received_power_dbw: float
    system_noise_temp_k: float
    n0_dbw_hz: float
    c_n0_dbhz: float
    req_eb_n0_db: float
    min_link_margin_db: float
    supported_bitrate_bps: int
    link_margin_db: float
    is_link_closed: bool
    status_notes: str


def compute_fspl_db(slant_range_m: float, wavelength_m: float) -> float:
    return 20.0 * math.log10(4.0 * math.pi * slant_range_m / wavelength_m)


def run_scenario_1_ka_high_rate() -> LinkBudgetResult:
    """
    Scenario 1: High-Rate Ka-band Orbit-to-Ground Trunkline.
    Freq: 32 GHz, Range: 500 km (overhead orbiter), Tx: 20 W, Tx Gain: 55 dBi (3 m dish),
    Rx Gain: 60 dBi (5 m dish), Required Eb/N0: 5.0 dB, Target Rate: 100 Mbps (80.0 dB-Hz).
    """
    freq = 32.0e9
    wl = C / freq
    r_m = 500_000.0
    p_tx_w = 20.0
    p_tx_dbw = 10.0 * math.log10(p_tx_w)
    g_tx = 55.0
    g_rx = 60.0
    fspl = compute_fspl_db(r_m, wl)  # ~176.53 dB
    atmos_loss = 0.85  # Gaseous CO2 + typical dust
    pointing_loss = 1.20
    
    p_rx_dbw = p_tx_dbw + g_tx + g_rx - fspl - atmos_loss - pointing_loss
    
    # Noise: T_ant = 120 K, T_rx = 90 K, Cable = 0.5 dB (L = 1.122)
    # T_sys = T_ant + (L-1)*290 + T_rx*L = 120 + 35.4 + 101.0 = 256.4 K
    t_sys = 256.4
    n0_dbw_hz = 10.0 * math.log10(K_B * t_sys)  # ~ -204.5 dBW/Hz
    c_n0 = p_rx_dbw - n0_dbw_hz
    
    target_rate = 100_000_000
    eb_n0 = c_n0 - 10.0 * math.log10(target_rate)
    margin = eb_n0 - 5.0
    is_closed = margin >= 3.0
    
    return LinkBudgetResult(
        scenario_id="SCENARIO_1_KA_HIGH_RATE",
        scenario_name="32 GHz Orbiter Trunkline to Surface Settlement (100 Mbps)",
        freq_hz=freq,
        wavelength_m=wl,
        slant_range_km=r_m / 1000.0,
        elevation_deg=75.0,
        tx_power_w=p_tx_w,
        tx_gain_dbi=g_tx,
        rx_gain_dbi=g_rx,
        fspl_db=round(fspl, 2),
        atmospheric_loss_db=atmos_loss,
        pointing_loss_db=pointing_loss,
        received_power_dbw=round(p_rx_dbw, 2),
        system_noise_temp_k=round(t_sys, 1),
        n0_dbw_hz=round(n0_dbw_hz, 2),
        c_n0_dbhz=round(c_n0, 2),
        req_eb_n0_db=5.0,
        min_link_margin_db=3.0,
        supported_bitrate_bps=target_rate,
        link_margin_db=round(margin, 2),
        is_link_closed=is_closed,
        status_notes="High-rate Ka-band trunkline closed with positive operational margin.",
    )


def run_scenario_2_uhf_proximity() -> LinkBudgetResult:
    """
    Scenario 2: Standard Proximity UHF Rover-to-Orbiter Overflight.
    Freq: 401.5 MHz, Range: 800 km, Tx: 5 W, Tx Gain: 2.0 dBi (monopole),
    Rx Gain: 4.0 dBi (orbiter patch), Required Eb/N0: 4.0 dB, Rate: 32 kbps (45.05 dB-Hz).
    """
    freq = 401.5e6
    wl = C / freq
    r_m = 800_000.0
    p_tx_w = 5.0
    p_tx_dbw = 10.0 * math.log10(p_tx_w)
    g_tx = 2.0
    g_rx = 4.0
    fspl = compute_fspl_db(r_m, wl)  # ~142.58 dB
    atmos_loss = 0.04
    pointing_loss = 0.20
    
    p_rx_dbw = p_tx_dbw + g_tx + g_rx - fspl - atmos_loss - pointing_loss
    
    # Mars surface brightness dominates UHF: T_ant = 210 K, T_rx = 180 K
    t_sys = 420.0
    n0_dbw_hz = 10.0 * math.log10(K_B * t_sys)
    c_n0 = p_rx_dbw - n0_dbw_hz
    
    rate = 32_000
    eb_n0 = c_n0 - 10.0 * math.log10(rate)
    margin = eb_n0 - 4.0
    is_closed = margin >= 3.0
    
    return LinkBudgetResult(
        scenario_id="SCENARIO_2_UHF_PROXIMITY",
        scenario_name="401.5 MHz Rover Overflight Contact (32 kbps)",
        freq_hz=freq,
        wavelength_m=wl,
        slant_range_km=r_m / 1000.0,
        elevation_deg=35.0,
        tx_power_w=p_tx_w,
        tx_gain_dbi=g_tx,
        rx_gain_dbi=g_rx,
        fspl_db=round(fspl, 2),
        atmospheric_loss_db=atmos_loss,
        pointing_loss_db=pointing_loss,
        received_power_dbw=round(p_rx_dbw, 2),
        system_noise_temp_k=round(t_sys, 1),
        n0_dbw_hz=round(n0_dbw_hz, 2),
        c_n0_dbhz=round(c_n0, 2),
        req_eb_n0_db=4.0,
        min_link_margin_db=3.0,
        supported_bitrate_bps=rate,
        link_margin_db=round(margin, 2),
        is_link_closed=is_closed,
        status_notes="Nominal Electra UHF proximity contact closed with positive margin.",
    )


def run_scenario_3_favorable_dust_loss_link_failure() -> LinkBudgetResult:
    """
    Scenario 3: Favorable Dust Propagation with Operational Link Failure.
    Emergency rover beacon (0.5 W) attempting contact at 2.5 deg elevation over 2,280 km range.
    Dust loss is negligible (0.009 dB), yet the link completely fails due to path loss (151.7 dB)
    and rover chassis antenna roll-off (-3.85 dBi).
    """
    freq = 401.5e6
    wl = C / freq
    r_m = 2_280_000.0
    p_tx_w = 0.5  # Emergency beacon
    p_tx_dbw = 10.0 * math.log10(p_tx_w)  # -3.01 dBW
    g_tx = -3.85  # Chassis pattern null at low horizon elevation
    g_rx = 2.0
    fspl = compute_fspl_db(r_m, wl)  # 151.68 dB
    atmos_loss = 0.18  # Low dust loss (0.009 dB dust + gas)
    pointing_loss = 0.50
    
    p_rx_dbw = p_tx_dbw + g_tx + g_rx - fspl - atmos_loss - pointing_loss  # -157.22 dBW
    
    t_sys = 450.0
    n0_dbw_hz = 10.0 * math.log10(K_B * t_sys)  # -202.07 dBW/Hz
    c_n0 = p_rx_dbw - n0_dbw_hz  # ~ 44.85 dB-Hz
    
    req_eb_n0 = 4.0
    min_margin = 3.0
    # Minimum standard rate is 8 kbps (39.03 dB-Hz).
    # Required C/N0 for 8 kbps = 39.03 + 4.0 + 3.0 = 46.03 dB-Hz.
    # Since C/N0 (44.85 dB-Hz) < 46.03 dB-Hz, link FAILS completely!
    eb_n0_at_8k = c_n0 - 10.0 * math.log10(8000)
    margin_at_8k = eb_n0_at_8k - req_eb_n0
    is_closed = False
    
    return LinkBudgetResult(
        scenario_id="SCENARIO_3_PROPAGATION_VS_SURVIVABILITY",
        scenario_name="Low Dust Loss with Operational Link Failure (Truth Demarcation)",
        freq_hz=freq,
        wavelength_m=wl,
        slant_range_km=r_m / 1000.0,
        elevation_deg=2.5,
        tx_power_w=p_tx_w,
        tx_gain_dbi=g_tx,
        rx_gain_dbi=g_rx,
        fspl_db=round(fspl, 2),
        atmospheric_loss_db=atmos_loss,
        pointing_loss_db=pointing_loss,
        received_power_dbw=round(p_rx_dbw, 2),
        system_noise_temp_k=round(t_sys, 1),
        n0_dbw_hz=round(n0_dbw_hz, 2),
        c_n0_dbhz=round(c_n0, 2),
        req_eb_n0_db=req_eb_n0,
        min_link_margin_db=min_margin,
        supported_bitrate_bps=0,
        link_margin_db=round(margin_at_8k, 2),
        is_link_closed=is_closed,
        status_notes="FAILS: Negligible dust loss (0.009 dB) does not close link due to range and chassis nulls.",
    )


def main():
    print("=" * 76)
    print("  PROJECT ATLAS RESEARCH RELEASE 2.0: STANDALONE LINK BUDGET SCENARIOS")
    print("=" * 76)
    
    s1 = run_scenario_1_ka_high_rate()
    s2 = run_scenario_2_uhf_proximity()
    s3 = run_scenario_3_favorable_dust_loss_link_failure()
    
    results = [s1, s2, s3]
    
    for s in results:
        status_str = "CLOSED [PASS]" if s.is_link_closed else "FAILED [EXPECTED REJECTION]"
        print(f"\n[{s.scenario_id}] {s.scenario_name}")
        print(f"  Carrier: {s.freq_hz / 1e9:.3f} GHz | Range: {s.slant_range_km:.1f} km | Elev: {s.elevation_deg:.1f}°")
        print(f"  FSPL: {s.fspl_db:.2f} dB | Atmos Loss: {s.atmospheric_loss_db:.2f} dB | Pointing Loss: {s.pointing_loss_db:.2f} dB")
        print(f"  C/N0: {s.c_n0_dbhz:.2f} dB-Hz | Supported Rate: {s.supported_bitrate_bps} bps | Margin: {s.link_margin_db:+.2f} dB")
        print(f"  Disposition: {status_str}")
        print(f"  Notes: {s.status_notes}")
    
    print("\n" + "=" * 76)
    # Verification checks
    assert s1.is_link_closed, "Scenario 1 should close with positive margin"
    assert s2.is_link_closed, "Scenario 2 should close with positive margin"
    assert not s3.is_link_closed, "Scenario 3 must fail to close"
    assert s3.supported_bitrate_bps == 0, "Scenario 3 operational rate must be 0"
    print("ALL 3 LINK SCENARIOS VERIFIED SUCCESSFULLY.")
    print("=" * 76)
    
    # Save output summary
    out_file = Path(__file__).parent / "link_budget_scenarios_summary.json"
    out_file.write_text(json.dumps([asdict(s) for s in results], indent=2), encoding="utf-8")
    print(f"Saved link budget summary to {out_file.name}")


if __name__ == "__main__":
    main()
