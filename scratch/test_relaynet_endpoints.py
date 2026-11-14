import urllib.request
import json

def test_endpoint(name, url, method="GET", payload=None):
    headers = {"Content-Type": "application/json"} if payload else {}
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"[{name}] {resp.status} OK - Keys: {list(res.keys())[:5]}")
        return res

print("--- Testing RelayNet Endpoints on Local Server ---")

# 1. LOS
los_payload = {
    "origin": {"row": 117, "col": 157, "antenna_height_m": 10.0, "id": "BASE"},
    "target": {"row": 138, "col": 114, "antenna_height_m": 2.5, "id": "THREE_FORKS"},
    "max_range_m": 3000.0
}
res_los = test_endpoint("POST /api/relaynet/los", "http://127.0.0.1:3000/api/relaynet/los", "POST", los_payload)
print(f"  Status: {res_los.get('status')}, Distance: {res_los.get('ground_distance_m')}m, Min clearance: {res_los.get('min_clearance_m')}m")

# 2. Graph
graph_payload = {
    "base_station": {"node_id": "BASE", "row": 117, "col": 157, "antenna_height_m": 10.0},
    "rover_unit": {"node_id": "PERSEVERANCE", "row": 138, "col": 114, "antenna_height_m": 2.5},
    "relays": [
        {"relay_id": "MRN_01", "row": 78, "col": 134, "antenna_height_m": 15.0, "is_active": True}
    ]
}
res_graph = test_endpoint("POST /api/relaynet/graph", "http://127.0.0.1:3000/api/relaynet/graph", "POST", graph_payload)
print(f"  Rover status: {res_graph.get('rover_status')}, Hop count: {res_graph.get('hop_count')}, Active path: {res_graph.get('active_path')}")

# 3. Optimize
opt_payload = {
    "base_station": {"node_id": "BASE", "row": 117, "col": 157, "antenna_height_m": 10.0},
    "target_units": [
        {"node_id": "SCOUT_DELTA", "row": 50, "col": 80, "antenna_height_m": 2.5},
        {"node_id": "EVA_CREW", "row": 30, "col": 50, "antenna_height_m": 2.0}
    ],
    "relay_budget": 2
}
res_opt = test_endpoint("POST /api/relaynet/optimize", "http://127.0.0.1:3000/api/relaynet/optimize", "POST", opt_payload)
print(f"  Selected relays: {[r['node_id'] for r in res_opt.get('selected_relays', [])]}, Coverage: {res_opt.get('coverage_percentage')}%")

# 4. Timeline
timeline_payload = {
    "base_station": {"id": "BASE", "rc": [117, 157], "antenna_h": 10.0},
    "relays": [
        {"id": "MRN_01", "rc": [78, 134], "antenna_h": 15.0}
    ]
}
res_time = test_endpoint("POST /api/relaynet/timeline", "http://127.0.0.1:3000/api/relaynet/timeline", "POST", timeline_payload)
print(f"  Summary: Checkpoints: {res_time['summary']['total_checkpoints']}, Availability: {res_time['summary']['connectivity_availability_pct']}%, Gaps: {res_time['summary']['gap_count']}")

print("--- ALL RELAYNET SERVER API ENDPOINTS VALIDATED SUCCESSFULLY ---")
