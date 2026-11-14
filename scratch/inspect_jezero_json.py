import json
with open('web/data/jezero_mission_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Keys:", list(data.keys()))
if 'metadata' in data:
    print("Metadata:", data['metadata'])
if 'landing_site' in data:
    print("Landing site:", data['landing_site'])
if 'waypoints' in data:
    print("Waypoints count:", len(data['waypoints']))
    print("Sample waypoint:", data['waypoints'][0])
if 'elevation_grid' in data:
    grid = data['elevation_grid']
    print(f"Elevation grid shape: {len(grid)} x {len(grid[0]) if grid else 0}")
