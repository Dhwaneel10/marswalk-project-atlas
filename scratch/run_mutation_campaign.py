import os
import shutil
import subprocess
import sys

target_file = 'src/marswalk/core/atlas_network_link_model.py'
with open(target_file, 'r', encoding='utf-8') as fp:
    original_code = fp.read()

mutations = [
    {
        'id': 'MUT-13AC-01',
        'name': 'Bypass distance validation in calculate_free_space_path_loss',
        'target': """        if range_m < 0:
            raise ValueError(f"Propagation range cannot be negative, got {range_m} m")
        if range_m == 0:
            raise ValueError("Propagation range cannot be zero for far-field free-space link. Collocated nodes require direct local/wired interface.")

        wavelength = SPEED_OF_LIGHT_M_S / freq_hz
        reactive_limit = wavelength / (4.0 * math.pi)
        if range_m < reactive_limit:
            raise ValueError(
                f"Propagation range {range_m:.4f} m is within sub-wavelength reactive near-field "
                f"(R < lambda / (4*pi) = {reactive_limit:.4f} m); Friis free-space formula is invalid (yields negative loss)."
            )""",
        'replacement': """        wavelength = SPEED_OF_LIGHT_M_S / freq_hz
        # MUTATION: Bypassed negative, zero, and sub-wavelength checks""",
        'test_cmd': ['.venv/Scripts/pytest', 'tests/test_milestone_13ac_physics_boundaries.py', '-k', 'sub_wavelength', '-v']
    },
    {
        'id': 'MUT-13AC-02',
        'name': 'Bypass elevation mask check in evaluate_link',
        'target': """        if elevation_deg < rx.elevation_mask_deg:
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
            )""",
        'replacement': """        # MUTATION: Elevation mask check bypassed""",
        'test_cmd': ['.venv/Scripts/pytest', 'tests/test_milestone_13ac_physics_boundaries.py', '-k', 'elevation_occultation_and_mask_boundaries', '-v']
    },
    {
        'id': 'MUT-13AC-03',
        'name': 'Invert pointing loss term (+ pointing_loss_db instead of - pointing_loss_db)',
        'target': """        p_rx_dbw = (
            eirp_dbw
            - fspl_db
            + rx.antenna_gain_dbi
            - pointing_loss_db
            - atm_loss_db
            - rx.implementation_loss_db
        )""",
        'replacement': """        p_rx_dbw = (
            eirp_dbw
            - fspl_db
            + rx.antenna_gain_dbi
            + pointing_loss_db
            - atm_loss_db
            - rx.implementation_loss_db
        )""",
        'test_cmd': ['.venv/Scripts/pytest', 'tests/test_milestone_13ac_physics_boundaries.py', '-k', 'pointing_loss_reduces_received_power', '-v']
    },
    {
        'id': 'MUT-13AC-04',
        'name': 'Force link closure in evaluate_link regardless of margin',
        'target': """        net_budget_db = c_n0_dbhz - rx.req_eb_n0_db - rx.min_link_margin_db
        if net_budget_db <= 0:
            max_rate_bps = 0.0
            operational_rate = 0
            is_closed = False
            margin = net_budget_db
            reason = f"Insufficient link budget: C/N0 ({c_n0_dbhz:.1f} dB-Hz) below threshold"
        else:""",
        'replacement': """        net_budget_db = c_n0_dbhz - rx.req_eb_n0_db - rx.min_link_margin_db
        if net_budget_db <= 0:
            max_rate_bps = 100000.0
            operational_rate = 128000
            is_closed = True  # MUTATION: forced link closed on negative margin
            margin = net_budget_db
            reason = "MUTATION forced closed"
        else:""",
        'test_cmd': ['.venv/Scripts/pytest', 'tests/test_milestone_13ac_physics_boundaries.py', '-k', 'negative_margin_strictly_prevents_link_closure', '-v']
    }
]

def purge_pycache():
    for root, dirs, files in os.walk('src'):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
    for root, dirs, files in os.walk('tests'):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)

results = []

for m in mutations:
    print('='*70)
    print(f"TESTING {m['id']}: {m['name']}")
    if m['target'] not in original_code:
        print(f"ERROR: Target string not found in {target_file}")
        sys.exit(1)

    mutated = original_code.replace(m['target'], m['replacement'])
    with open(target_file, 'w', encoding='utf-8') as fp:
        fp.write(mutated)
    # Touch file to update mtime
    os.utime(target_file, None)
    purge_pycache()

    res = subprocess.run(m['test_cmd'], capture_output=True, text=True)
    detected = (res.returncode != 0)
    print(f"Status: {'MUTATION KILLED (TEST FAILED AS EXPECTED)' if detected else 'MUTATION SURVIVED (FAILURE)'}")
    
    failure_snippet = ""
    if detected:
        fail_lines = [l for l in res.stdout.splitlines() if 'FAILED' in l or 'AssertionError' in l or 'Failed:' in l or 'DID NOT RAISE' in l]
        failure_snippet = "\n".join(fail_lines[:4])
        print("Detection excerpt:\n" + failure_snippet)
    else:
        print("STDOUT:\n" + res.stdout[:400])

    results.append({
        'id': m['id'],
        'name': m['name'],
        'detected': detected,
        'test': " ".join(m['test_cmd']),
        'snippet': failure_snippet
    })

    # Restore
    with open(target_file, 'w', encoding='utf-8') as fp:
        fp.write(original_code)
    os.utime(target_file, None)
    purge_pycache()

print('='*70)
print('ALL MUTATIONS TESTED AND BASELINE RESTORED.')
print('Summary:')
for r in results:
    print(f"[{'PASS' if r['detected'] else 'FAIL'}] {r['id']}: {r['name']}")
