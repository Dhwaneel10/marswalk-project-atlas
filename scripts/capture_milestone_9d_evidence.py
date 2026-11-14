"""
Automated Visual Evidence Capture for MarsWalk 2.0 Project Atlas (Milestone 9D).
Captures 7 high-resolution 1366x768 viewport screenshots using headless Chrome:
  1. m9d_01_idle_orbit_calm_labels.png: Calm Orbit View (idle-orbit mode, ~5-8 iconic landmarks, AUTO-ROTATE: ON)
  2. m9d_02_orbit_paused_interaction.png: Paused Orbit View (AUTO-ROTATE: OFF, stationary globe)
  3. m9d_03_deliberate_search_mode.png: Deliberate Search in Progress (searching state, autocomplete dropdown open)
  4. m9d_04_regional_exploration_arrival.png: Focused Regional Exploration (Gale Crater arrival, Dossier Card open)
  5. m9d_05_jezero_workstation_ctx_mesh.png: High-Fidelity Jezero 3D Workstation (NASA CTX orthomosaic draped on USGS DTM)
  6. m9d_06_jezero_waypoint_screen_labels.png: Jezero 3D Cartographic Waypoint Labels (screen-aligned waypoint badges)
  7. m9d_07_jezero_live_planning_slope_hazard.png: Live Planning Traverse & Tactical Slope Hazard Overlay
"""

import os
import subprocess
import time
from pathlib import Path

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUTPUT_DIR = Path("outputs")
BASE_URL = "http://localhost:3000"


def capture_screenshot(url: str, output_path: Path, wait_ms: int = 5000):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    abs_out = str(output_path.resolve())

    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--window-size=1366,768",
        f"--virtual-time-budget={wait_ms}",
        f"--screenshot={abs_out}",
        url,
    ]

    print(f"[Capture] Capturing: {url} -> {output_path}...")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    if res.returncode != 0:
        print(f"[Capture Error] Return code {res.returncode}: {res.stderr}")
        return False

    if output_path.exists():
        size_kb = output_path.stat().st_size / 1024
        print(f"[Capture Success] Saved {output_path} ({size_kb:.1f} KB)")
        return True
    else:
        print(f"[Capture Error] File not found after run: {output_path}")
        return False


def main():
    shots = [
        # 1. Calm Orbit View (idle-orbit mode)
        (
            f"{BASE_URL}/?diag=1",
            OUTPUT_DIR / "m9d_01_idle_orbit_calm_labels.png",
            6000,
        ),
        # 2. Paused Orbit View (AUTO-ROTATE: OFF)
        (
            f"{BASE_URL}/?autorotate=0&diag=1",
            OUTPUT_DIR / "m9d_02_orbit_paused_interaction.png",
            6000,
        ),
        # 3. Deliberate Search Mode with Autocomplete
        (
            f"{BASE_URL}/?q=Gale&diag=1",
            OUTPUT_DIR / "m9d_03_deliberate_search_mode.png",
            6000,
        ),
        # 4. Focused Regional Exploration Arrival (Gale Crater & Dossier Card)
        (
            f"{BASE_URL}/?place=iau_2071&diag=1",
            OUTPUT_DIR / "m9d_04_regional_exploration_arrival.png",
            7000,
        ),
        # 5. High-Fidelity Jezero 3D Workstation (Authentic NASA CTX Orthomosaic)
        (
            f"{BASE_URL}/?fly=jezero&texture=ctx&route=balanced&diag=1",
            OUTPUT_DIR / "m9d_05_jezero_workstation_ctx_mesh.png",
            7000,
        ),
        # 6. Jezero 3D Cartographic Waypoint Labels
        (
            f"{BASE_URL}/?fly=jezero&waypoint=hawksbill_gap&diag=1",
            OUTPUT_DIR / "m9d_06_jezero_waypoint_screen_labels.png",
            7000,
        ),
        # 7. Live Planning Traverse & Slope Hazard Overlay
        (
            f"{BASE_URL}/?fly=jezero&texture=slope&route=science_first&action=plan&diag=1",
            OUTPUT_DIR / "m9d_07_jezero_live_planning_slope_hazard.png",
            8000,
        ),
    ]

    results = []
    for url, out_path, delay in shots:
        success = capture_screenshot(url, out_path, delay)
        results.append((out_path.name, success))
        time.sleep(1)

    print("\n--- Visual Evidence Summary ---")
    all_ok = True
    for name, success in results:
        status_txt = "OK" if success else "FAILED"
        print(f"  {name}: {status_txt}")
        if not success:
            all_ok = False

    assert all_ok, "One or more screenshot captures failed."
    print("\n[MarsWalk Atlas] All 7 milestone evidence screenshots captured successfully.")


if __name__ == "__main__":
    main()
