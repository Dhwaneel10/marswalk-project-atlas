import json
with open('web/data/jezero_mission_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Grid metadata:", data.get('grid'))
print("Routes count:", len(data.get('routes', [])))
if data.get('routes'):
    print("Sample route keys:", list(data['routes'][0].keys()))
