import json
import jsonschema
from jsonschema import Draft202012Validator

schemas = [
    'schemas/api/v1/joint-mission-evaluation.schema.json',
    'schemas/api/v1/joint-mission-optimization.schema.json'
]

for s_path in schemas:
    with open(s_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    Draft202012Validator.check_schema(schema)
    print(f"Schema {s_path} is valid Draft 2020-12!")
