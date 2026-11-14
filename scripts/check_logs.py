import subprocess

cmd = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    r"--user-data-dir=C:\Users\dhwan\AppData\Local\Temp\chrome_test",
    "--virtual-time-budget=6000",
    "--dump-dom",
    "http://127.0.0.1:3000/"
]

res = subprocess.run(cmd, capture_output=True, text=True)
tag = '<div id="debugLogViewer"'
pos = res.stdout.find(tag)
print(f"Tag at pos {pos}:")
print(res.stdout[pos:pos+500])
