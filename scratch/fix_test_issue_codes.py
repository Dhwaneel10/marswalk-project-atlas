path = "tests/test_milestone_13k_mission_compiler.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("assert \"ERR_GEO_START_OOB\" in issue_codes", "assert \"ERR_OUT_OF_BOUNDS_START_COORDINATES\" in issue_codes")
text = text.replace("assert \"ERR_GEO_SLOPE_EXCESSIVE\" in issue_codes", "assert \"ERR_INVALID_SLOPE_LIMIT\" in issue_codes")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated test issue codes")
