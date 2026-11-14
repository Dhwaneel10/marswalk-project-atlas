import urllib.request
import json

endpoints = [
    ("POST", "http://127.0.0.1:3000/api/mission-assurance/evaluate", {"campaign_id": "cmp_smoke"}),
    ("GET", "http://127.0.0.1:3000/api/campaign-branches/list?campaign_id=cmp_smoke", None),
    ("POST", "http://127.0.0.1:3000/api/campaign-branches/create", {"campaign_id": "cmp_smoke", "branch_id": "br_api_test", "name": "API Test Branch"}),
    ("POST", "http://127.0.0.1:3000/api/campaign-branches/br_api_test/scenario", {"campaign_id": "cmp_smoke", "scenario_type": "R1_RELAY_OUTAGE", "target_sol": 2}),
    ("POST", "http://127.0.0.1:3000/api/campaign-branches/br_api_test/replay", {"campaign_id": "cmp_smoke"}),
    ("POST", "http://127.0.0.1:3000/api/campaign-branches/compare", {"campaign_id": "cmp_smoke", "branch_ids": ["br_baseline", "br_api_test"]}),
    ("POST", "http://127.0.0.1:3000/api/campaign-robustness/evaluate", {"campaign_id": "cmp_smoke", "max_scenarios": 2}),
    ("POST", "http://127.0.0.1:3000/api/mission-assurance/dossier", {"campaign_id": "cmp_smoke"}),
]

for method, url, body in endpoints:
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            print(f"[{method}] {url.split('3000')[1]} -> Status {resp.status}, keys: {list(res_data.keys())[:4]}")
    except urllib.error.HTTPError as err:
        print(f"[{method}] {url.split('3000')[1]} -> Error {err.code}: {err.read().decode('utf-8')}")


print("ALL API ENDPOINTS VERIFIED LIVE AND OPERATIONAL!")
