import sys
sys.path.insert(0, 'src')
import re

with open('src/marswalk/api/service.py', 'r', encoding='utf-8') as f:
    text = f.read()

routes = re.findall(r'@app\.(?:get|post|put|delete)\(["\']([^"\']+)["\']', text)
print(f"Total endpoints in service.py: {len(routes)}")
for r in sorted(routes):
    print(f"  {r}")

# Check how terrain is loaded in service.py
terrain_matches = [line.strip() for line in text.split('\n') if 'terrain' in line.lower() and ('load' in line.lower() or 'grid' in line.lower() or 'global' in line.lower())]
print(f"\nTerrain mentions in service.py: {len(terrain_matches)}")
for m in terrain_matches[:10]:
    print(f"  {m}")
