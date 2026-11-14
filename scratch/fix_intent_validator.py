path = "src/marswalk/core/mission_intent_validator.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_inst_block = """        # Check required instruments against authoritative INSTRUMENT_CATALOG
        for inst_id in sci.required_instruments:
            if inst_id not in INSTRUMENT_CATALOG:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNKNOWN_INSTRUMENT",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Required instrument '{inst_id}' does not exist in authoritative catalog.",
                    affected_field="science.required_instruments",
                    suggested_resolution=f"Select from available instruments: {list(INSTRUMENT_CATALOG.keys())}",
                ))"""

new_inst_block = """        # Check required instruments against authoritative INSTRUMENT_CATALOG
        known_instruments = {profile.instrument_id.value for profile in INSTRUMENT_CATALOG.values()}
        for inst_id in sci.required_instruments:
            if inst_id not in known_instruments and inst_id not in INSTRUMENT_CATALOG:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNKNOWN_INSTRUMENT",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Required instrument '{inst_id}' does not exist in authoritative catalog.",
                    affected_field="science.required_instruments",
                    suggested_resolution=f"Select from available instruments: {sorted(list(known_instruments))}",
                ))"""

old_obj_block = """        # Check if requested objectives have any matching instrument in catalog
        for obj in sci.primary_objectives:
            matching = [
                i_id for i_id, i_spec in INSTRUMENT_CATALOG.items()
                if any(m.science_objective == obj for m in i_spec.operating_modes)
            ]"""

new_obj_block = """        # Check if requested objectives have any matching instrument in catalog
        for obj in sci.primary_objectives:
            matching = [
                i_id for i_id, i_spec in INSTRUMENT_CATALOG.items()
                if any(comp_obj.value == obj or obj in comp_obj.value or comp_obj.value in obj for comp_obj in i_spec.compatible_objectives)
            ]"""

assert old_inst_block in text or old_inst_block.replace("\n", "\r\n") in text, "old_inst_block not found"
text = text.replace(old_inst_block, new_inst_block).replace(old_inst_block.replace("\n", "\r\n"), new_inst_block.replace("\n", "\r\n"))

assert old_obj_block in text or old_obj_block.replace("\n", "\r\n") in text, "old_obj_block not found"
text = text.replace(old_obj_block, new_obj_block).replace(old_obj_block.replace("\n", "\r\n"), new_obj_block.replace("\n", "\r\n"))

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated mission_intent_validator.py successfully")
