with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
post_blocks = [line for line in text.split('\n') if 'elif path == "/api/' in line or 'if path == "/api/' in line]
print(f"Total API routes in run_atlas.py: {len(post_blocks)}")
for b in post_blocks[-15:]:
    print(" ", b.strip())
