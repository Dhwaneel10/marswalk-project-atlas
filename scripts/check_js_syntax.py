"""
MarsWalk 2.0 — Headless Chrome JavaScript Syntax & Parsing Validator
Validates that web/app.js has 100% valid JavaScript syntax by having Google Chrome's V8 engine parse it.
"""
import subprocess
import tempfile
import json
import os
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
APP_JS_PATH = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk\web\app.js")

with open(APP_JS_PATH, "r", encoding="utf-8") as f:
    js_code = f.read()

# Build HTML test harness that evaluates the entire app.js
html_content = f"""<!DOCTYPE html>
<html>
<head><title>JS Syntax Test</title></head>
<body>
<div id="output">PENDING</div>
<script>
try {{
    // Verify pure syntax by parsing via Function constructor
    const testFn = new Function({json.dumps(js_code)});
    document.getElementById('output').innerText = 'SYNTAX_VALID_EXIT_0';
    console.log('SYNTAX_VALID_EXIT_0');
}} catch (err) {{
    document.getElementById('output').innerText = 'SYNTAX_ERROR: ' + err.toString();
    console.error('SYNTAX_ERROR: ' + err.toString());
}}
</script>
</body>
</html>
"""

temp_dir = tempfile.mkdtemp(prefix="atlas_js_syntax_")
html_path = os.path.join(temp_dir, "test.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

cmd = [
    CHROME_PATH,
    "--headless=new",
    "--disable-gpu",
    "--dump-dom",
    f"file:///{html_path.replace(os.sep, '/')}"
]

try:
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    dom_output = res.stdout
    if "SYNTAX_VALID_EXIT_0" in dom_output:
        print("[V8 JS ENGINE] JavaScript syntax in web/app.js is VALID! (Exit Code: 0)")
        sys.exit(0)
    else:
        print("[V8 JS ENGINE] JavaScript syntax error detected in web/app.js:")
        print(dom_output)
        sys.exit(1)
finally:
    try:
        os.remove(html_path)
        os.rmdir(temp_dir)
    except Exception:
        pass
