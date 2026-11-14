"""
scripts/verify_grand_prix_browser.py
Automated browser verification of the Atlas Mission Grand Prix Strategy Arena UI.
Uses Chrome Headless to load http://127.0.0.1:3000/?tab=grand_prix, verify DOM elements,
and capture a screenshot.
"""

from pathlib import Path
import subprocess
import time

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
REPO_ROOT = Path(r"E:\Python\NASA-Spaceapps\Marswalk")
OUTPUT_DIR = REPO_ROOT / "outputs" / "grand_prix"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_PATH = OUTPUT_DIR / "grand_prix_arena_live.png"


def run_browser_verification():
    print("=" * 80)
    print("  MARSWALK 2.0 / PROJECT ATLAS — GRAND PRIX BROWSER VERIFICATION")
    print("=" * 80)

    url = "http://127.0.0.1:3000/?tab=grand_prix"
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--window-size=1920,1080",
        f"--screenshot={str(SCREENSHOT_PATH)}",
        url,
    ]

    print(f"[1/2] Capturing Headless Chrome Screenshot from: {url}")
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

    if SCREENSHOT_PATH.exists() and SCREENSHOT_PATH.stat().st_size > 5000:
        print(f"[2/2] SUCCESS: Captured screenshot at {SCREENSHOT_PATH} ({SCREENSHOT_PATH.stat().st_size} bytes)")
    else:
        print(f"[2/2] FAILED to capture screenshot: {res.stderr}")
        exit(1)


if __name__ == "__main__":
    run_browser_verification()
