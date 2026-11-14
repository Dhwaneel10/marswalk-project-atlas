with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
match = re.search(r'from marswalk\.api\.service import \((.*?)\)', text, re.DOTALL)
if match:
    print("Found service import block!")
    print(match.group(0)[:300], "...")
