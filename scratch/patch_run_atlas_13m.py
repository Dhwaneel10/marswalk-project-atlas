with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update imports
old_imp = "    environmental_raster_api,\n    APIError,"
new_imp = """    environmental_raster_api,
    environment_validation_catalog_api,
    environment_validation_collocate_api,
    environment_validation_evaluate_api,
    environment_validation_calibrate_api,
    environment_validation_experiments_api,
    environment_validation_representativeness_api,
    APIError,"""

if old_imp in content:
    content = content.replace(old_imp, new_imp, 1)
    print("Patched imports successfully")
else:
    # Try CRLF
    old_imp_crlf = "    environmental_raster_api,\r\n    APIError,"
    new_imp_crlf = """    environmental_raster_api,\r
    environment_validation_catalog_api,\r
    environment_validation_collocate_api,\r
    environment_validation_evaluate_api,\r
    environment_validation_calibrate_api,\r
    environment_validation_experiments_api,\r
    environment_validation_representativeness_api,\r
    APIError,"""
    if old_imp_crlf in content:
        content = content.replace(old_imp_crlf, new_imp_crlf, 1)
        print("Patched imports (CRLF) successfully")
    else:
        print("Warning: import anchor not found!")

# 2. Add GET routes
get_anchor = '            elif clean_path in ("/api/compiler/sample-intent", "/api/v1/compiler/sample-intent"):'
get_routes = """            elif clean_path in ("/api/environment-validation/catalog", "/api/v1/environment-validation/catalog"):
                res = environment_validation_catalog_api()
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/collocate", "/api/v1/environment-validation/collocate"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_collocate_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/evaluate", "/api/v1/environment-validation/evaluate"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_evaluate_api(qp)
                self.send_json_response(res, 200)
                return
            elif clean_path in ("/api/environment-validation/experiments", "/api/v1/environment-validation/experiments"):
                qp = {k: v[0] for k, v in query_params.items()} if "query_params" in locals() and query_params else {}
                res = environment_validation_experiments_api(qp)
                self.send_json_response(res, 200)
                return
""" + get_anchor

if get_anchor in content:
    content = content.replace(get_anchor, get_routes, 1)
    print("Patched GET routes successfully")
else:
    print("Warning: GET anchor not found!")

# 3. Add POST routes
post_anchor = '            elif clean_path in ("/api/compiler/validate", "/api/v1/compiler/validate"):'
post_routes = """            elif clean_path in ("/api/environment-validation/calibrate", "/api/v1/environment-validation/calibrate"):
                result = environment_validation_calibrate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/representativeness", "/api/v1/environment-validation/representativeness"):
                result = environment_validation_representativeness_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/collocate", "/api/v1/environment-validation/collocate"):
                result = environment_validation_collocate_api(payload)
                self.send_json_response(result, 200)
                return
            elif clean_path in ("/api/environment-validation/evaluate", "/api/v1/environment-validation/evaluate"):
                result = environment_validation_evaluate_api(payload)
                self.send_json_response(result, 200)
                return
""" + post_anchor

if post_anchor in content:
    content = content.replace(post_anchor, post_routes, 1)
    print("Patched POST routes successfully")
else:
    print("Warning: POST anchor not found!")

with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated scripts/run_atlas.py")
