path = "src/marswalk/core/mission_intent_validator.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Fix objective validation in _validate_science_intent
old_obj_block = """        # Check if requested objectives have any matching instrument in catalog
        for obj in sci.primary_objectives:
            matching = [
                i_id for i_id, i_spec in INSTRUMENT_CATALOG.items()
                if any(comp_obj.value == obj or obj in comp_obj.value or comp_obj.value in obj for comp_obj in i_spec.compatible_objectives)
            ]
            if not matching:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNSUPPORTED_SCIENCE_OBJECTIVE",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Science objective '{obj}' is not supported by any instrument in catalog.",
                    affected_field="science.primary_objectives",
                    suggested_resolution="Select from supported objective categories.",
                ))"""

new_obj_block = """        OBJECTIVE_SYNONYMS = {
            "GEOLOGIC_MAPPING": ["GEOLOGICAL_CHARACTERIZATION", "SURFACE_MORPHOLOGY"],
            "MINERALOGIC_SPECTROSCOPY": ["MINERALOGICAL_INVESTIGATION"],
            "ELEMENTAL_CHEMISTRY": ["MINERALOGICAL_INVESTIGATION", "GEOLOGICAL_CHARACTERIZATION"],
            "ORGANIC_SPECTROSCOPY": ["ASTROBIOLOGY_BIOSIGNATURE_SURVEY", "MINERALOGICAL_INVESTIGATION"],
            "SUBSURFACE_STRATIGRAPHY": ["GEOLOGICAL_CHARACTERIZATION", "SURFACE_MORPHOLOGY"],
            "ATMOSPHERIC_METEOROLOGY": ["ATMOSPHERIC_OBSERVATION", "ENVIRONMENTAL_MONITORING"],
            "SAMPLE_EXTRACTION": ["GEOLOGICAL_CHARACTERIZATION", "ASTROBIOLOGY_BIOSIGNATURE_SURVEY"],
            "GEOLOGICAL_CHARACTERIZATION": ["GEOLOGICAL_CHARACTERIZATION"],
            "MINERALOGICAL_INVESTIGATION": ["MINERALOGICAL_INVESTIGATION"],
            "SURFACE_MORPHOLOGY": ["SURFACE_MORPHOLOGY"],
            "ATMOSPHERIC_OBSERVATION": ["ATMOSPHERIC_OBSERVATION"],
            "ENVIRONMENTAL_MONITORING": ["ENVIRONMENTAL_MONITORING"],
            "ASTROBIOLOGY_BIOSIGNATURE_SURVEY": ["ASTROBIOLOGY_BIOSIGNATURE_SURVEY"],
        }

        # Check if requested objectives have any matching instrument in catalog
        for obj in sci.primary_objectives:
            synonyms = OBJECTIVE_SYNONYMS.get(obj, [obj])
            matching = [
                i_id for i_id, i_spec in INSTRUMENT_CATALOG.items()
                if any(any(s == comp_obj.value or s in comp_obj.value or comp_obj.value in s for s in synonyms) for comp_obj in i_spec.compatible_objectives)
            ]
            if not matching:
                issues.append(IntentValidationIssue(
                    issue_code="ERR_UNSUPPORTED_SCIENCE_OBJECTIVE",
                    severity=ValidationSeverity.ERROR.value,
                    message=f"Science objective '{obj}' is not supported by any instrument in catalog.",
                    affected_field="science.primary_objectives",
                    suggested_resolution="Select from supported objective categories.",
                ))"""

# 2. Fix rover compatibility in _validate_cross_intent_consistency
old_comp_block = """                        # Check if rover has any instrument compatible with target objective
                        for inst_id in r_cfg.instrument_ids:
                            if inst_id in INSTRUMENT_CATALOG:
                                inst = INSTRUMENT_CATALOG[inst_id]
                                if any(m.science_objective == tgt.objective for m in inst.operating_modes):
                                    can_observe = True
                                    break"""

new_comp_block = """                        # Check if rover has any instrument mode compatible with target objective
                        for mode_key, profile in INSTRUMENT_CATALOG.items():
                            if profile.instrument_id.value in r_cfg.instrument_ids:
                                for comp_obj in profile.compatible_objectives:
                                    if comp_obj.value == tgt.objective or tgt.objective in comp_obj.value or comp_obj.value in tgt.objective:
                                        can_observe = True
                                        break
                            if can_observe:
                                break"""

assert old_obj_block in text or old_obj_block.replace("\n", "\r\n") in text, "old_obj_block not found"
text = text.replace(old_obj_block, new_obj_block).replace(old_obj_block.replace("\n", "\r\n"), new_obj_block.replace("\n", "\r\n"))

assert old_comp_block in text or old_comp_block.replace("\n", "\r\n") in text, "old_comp_block not found"
text = text.replace(old_comp_block, new_comp_block).replace(old_comp_block.replace("\n", "\r\n"), new_comp_block.replace("\n", "\r\n"))

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated mission_intent_validator.py objectives and rover checks successfully")
