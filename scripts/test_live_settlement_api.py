import urllib.request
import json
from marswalk.api.contracts import validate_contract

url = 'http://127.0.0.1:3000/api/settlement/status'
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))

print('Received status response from live daemon:')
print(f"Status: {data.get('status')}, Sol: {data.get('current_sol')}, Power: {data.get('power', {}).get('generation_gross_kw')} kW")
is_valid, errors = validate_contract(data, 'settlement-engine')
print(f"Contract validation against settlement-engine.schema.json: is_valid={is_valid}, errors={errors}")
assert is_valid, f"Schema validation failed: {errors}"
print("API endpoint /api/settlement/status PASSED schema validation!")
