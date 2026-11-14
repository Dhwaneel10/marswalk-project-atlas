"""
Automated Visual Evidence Capture for MarsWalk 2.0 Project Atlas (Milestone 9C).
Captures high-resolution 1366x768 viewport screenshots using headless Chrome:
  1. Global Orbit View with Dynamic Cartographic Labels
  2. Location Dossier Card View (Olympus Mons)
  3. Jezero 3D Surface Workstation Transition View
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
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
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
        # 1. Global View with Cartographic Labels & HUD Diagnostics
        (
            f"{BASE_URL}/?diag=1",
            OUTPUT_DIR / "marswalk_atlas_global_labels_1366x768.png",
            6000,
        ),
        # 2. Location Dossier Card (Olympus Mons)
        (
            f"{BASE_URL}/?place=iau_4453&diag=1",
            OUTPUT_DIR / "marswalk_atlas_location_card_1366x768.png",
            7000,
        ),
        # 3. Jezero Surface Workstation Transition
        (
            f"{BASE_URL}/?fly=jezero&route=balanced",
            OUTPUT_DIR / "marswalk_atlas_jezero_transition_1366x768.png",
            7000,
        ),
    ]

    for url, out_path, delay in shots:
        success = capture_screenshot(url, out_path, delay)
        assert success, f"Failed to capture {out_path}"
        time.sleep(1)

    print("\n[MarsWalk Atlas] All 3 milestone evidence screenshots captured successfully.")


if __name__ == "__main__":
    main()
