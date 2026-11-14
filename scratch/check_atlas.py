import asyncio
import json
import subprocess
import time
import urllib.request
import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9230
TMP_DIR = r"C:\Users\dhwan\AppData\Local\Temp\chrome_clean_test"
proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    f"--remote-debugging-port={PORT}",
    f"--user-data-dir={TMP_DIR}",
    "--disable-extensions",
    "--no-first-run",
    "--disable-gpu",
    "--window-size=1920,1080",
    "about:blank"
])
time.sleep(1.5)

async def check():
    tabs = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list").read().decode())
    print("Available targets:", [(t.get("type"), t.get("url")) for t in tabs])
    page_target = next(t for t in tabs if t.get("type") == "page")
    ws_url = page_target["webSocketDebuggerUrl"]
    print("Connecting to page target:", ws_url)

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 3, "method": "Page.navigate", "params": {"url": "http://127.0.0.1:3000/?mode=demo"}}))
        await ws.recv()

        await asyncio.sleep(4.0)

        for expr in [
            "document.location.href",
            "document.title",
            "document.readyState",
            "Boolean(window.THREE)",
            "Boolean(window.__atlas)",
            "document.getElementById('demoShowcaseHUD').className",
            "document.getElementById('showcaseStepIndicator').textContent"
        ]:
            await ws.send(json.dumps({"id": 100, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == 100:
                    print(f"{expr} => {msg.get('result', {}).get('result', {}).get('value')}")
                    break

try:
    asyncio.run(check())
finally:
    proc.kill()
