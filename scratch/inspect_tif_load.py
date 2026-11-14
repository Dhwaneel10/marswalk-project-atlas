with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [line for line in text.split('\n') if 'jezero_ready_20m.tif' in line or 'load_and_process_terrain' in line]
for m in matches:
    print(m)
