path = "scripts/verify_mission_compiler_browser.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

import re

# Replace eval_js("...") with eval_js("(() => { ... })()")
def wrap_iife(match):
    inner = match.group(1)
    if inner.startswith("(() =>") or inner.startswith("Boolean("):
        return f'eval_js("{inner}")'
    return f'eval_js("(() => {{ {inner} }})()")'

text = re.sub(r'eval_js\("([^"]+)"\)', wrap_iife, text)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated verify_mission_compiler_browser.py with IIFE scoping")
