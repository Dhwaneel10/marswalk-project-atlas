"""
MarsWalk 2.0 - Milestone 9P Browser Baseline Audit Script
Connects to headless Chrome, records all console events, exceptions, and network calls.
"""

import asyncio
import subprocess
import tempfile
import json
import urllib.request
import websockets

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:3000"
DEBUG_PORT = 9499


async def audit_browser():
    tmp_profile = tempfile.mkdtemp(prefix="chrome_audit_")
    proc = subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={tmp_profile}",
        "--headless=new",
        "--disable-gpu",
        "about:blank"
    ])
    await asyncio.sleep(1.5)
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{DEBUG_PORT}/json")
        with urllib.request.urlopen(req, timeout=3) as resp:
            targets = json.loads(resp.read().decode("utf-8"))
        ws_url = targets[0]["webSocketDebuggerUrl"]
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
            await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 3, "method": "Network.enable"}))
            await ws.send(json.dumps({"id": 4, "method": "Log.enable"}))
            await ws.send(json.dumps({"id": 5, "method": "Page.navigate", "params": {"url": f"{BASE_URL}/index.html"}}))

            console_msgs = []
            exceptions = []
            network_fails = []

            # Listen for 6 seconds while Atlas initializes
            end_time = asyncio.get_event_loop().time() + 6.0
            while asyncio.get_event_loop().time() < end_time:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg = json.loads(raw)
                    method = msg.get("method")
                    if method == "Runtime.consoleAPICalled":
                        p = msg["params"]
                        text = " ".join(str(a.get("value", "")) for a in p.get("args", []))
                        console_msgs.append(f"[{p.get('type')}] {text}")
                    elif method == "Log.entryAdded":
                        entry = msg["params"]["entry"]
                        console_msgs.append(f"[{entry.get('level')}] {entry.get('text')}")
                    elif method == "Runtime.exceptionThrown":
                        details = msg["params"].get("exceptionDetails", {})
                        exceptions.append(f"EXCEPTION: {details.get('text')} - {details.get('exception', {}).get('description')}")
                    elif method == "Network.loadingFailed":
                        network_fails.append(msg["params"])
                except asyncio.TimeoutError:
                    pass

            # Evaluate Atlas state
            await ws.send(json.dumps({
                "id": 99,
                "method": "Runtime.evaluate",
                "params": {"expression": "JSON.stringify({ booted: window.__atlas ? window.__atlas.isBooted() : false, landing: window.__atlas ? window.__atlas.isLandingPageActive() : null, waypoints: window.__atlas ? window.__atlas.getWaypointVisibilityMode() : null })", "returnByValue": True}
            }))
            eval_res = await ws.recv()

            print(f"=== CONSOLE LOGS ({len(console_msgs)}) ===")
            for m in console_msgs:
                print("  ", m)
            print(f"\n=== EVALUATED ATLAS STATE ===")
            print("  ", eval_res)
            print(f"\n=== RUNTIME EXCEPTIONS ({len(exceptions)}) ===")
            for ex in exceptions:
                print("  ", ex)
            print(f"\n=== NETWORK FAILURES ({len(network_fails)}) ===")
            for nf in network_fails:
                print("  ", nf)
    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(audit_browser())
