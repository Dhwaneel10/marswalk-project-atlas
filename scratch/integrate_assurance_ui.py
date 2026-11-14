# Integration of Atlas Mission Assurance Engine into web/app.js
from pathlib import Path

app_js_path = Path("web/app.js")
content = app_js_path.read_text(encoding="utf-8")

# 1. Update inspector tabs declarations around line 846
target_decl = "const tabBtnCampaignOperations = document.getElementById('tabBtnCampaignOperations');"
replacement_decl = """const tabBtnCampaignOperations = document.getElementById('tabBtnCampaignOperations');
  const tabMissionAssurance = document.getElementById('tabMissionAssurance');
  const tabBtnMissionAssurance = document.getElementById('tabBtnMissionAssurance');
  const btnHeaderMissionAssurance = document.getElementById('btnHeaderMissionAssurance');"""

if target_decl in content and "tabMissionAssurance" not in content[:content.find(target_decl)+500]:
    content = content.replace(target_decl, replacement_decl, 1)

# 2. Update switchInspectorTab panels dictionary
target_panels = "const panels = { tabMissionControl, tabExperimentStudio, tabRobustnessLab, tabRehearsalDirector, tabJointMissionStudio, tabCampaignOperations, tabPlan, tabResults, tabScenarios, tabWorkspaces };"
replacement_panels = "const panels = { tabMissionControl, tabExperimentStudio, tabRobustnessLab, tabRehearsalDirector, tabJointMissionStudio, tabCampaignOperations, tabMissionAssurance, tabPlan, tabResults, tabScenarios, tabWorkspaces };"

if target_panels in content:
    content = content.replace(target_panels, replacement_panels, 1)

# 3. Update cockpit-mode check in switchInspectorTab
target_cockpit = "|| tabId === 'tabCampaignOperations')"
replacement_cockpit = "|| tabId === 'tabCampaignOperations' || tabId === 'tabMissionAssurance')"

if target_cockpit in content:
    content = content.replace(target_cockpit, replacement_cockpit, 1)

# 4. Add tab listener right after tabBtnCampaignOperations listener
target_listener = "if (tabBtnCampaignOperations) {\n    tabBtnCampaignOperations.addEventListener('click', () => switchInspectorTab('tabCampaignOperations'));\n  }"
replacement_listener = """if (tabBtnCampaignOperations) {
    tabBtnCampaignOperations.addEventListener('click', () => switchInspectorTab('tabCampaignOperations'));
  }
  if (tabBtnMissionAssurance) {
    tabBtnMissionAssurance.addEventListener('click', () => switchInspectorTab('tabMissionAssurance'));
  }
  if (btnHeaderMissionAssurance) {
    btnHeaderMissionAssurance.addEventListener('click', () => switchInspectorTab('tabMissionAssurance'));
  }"""

if target_listener not in content:
    target_listener = target_listener.replace("\n", "\r\n")
    replacement_listener = replacement_listener.replace("\n", "\r\n")

if target_listener in content:
    content = content.replace(target_listener, replacement_listener, 1)
else:
    print("Warning: target_listener not matched cleanly, will check alternative")

# 5. Add initMissionAssuranceEngine() call in startup
target_startup = "initMoccEngine();\n      if (params.get('mocc') === '1' || params.get('tab') === 'mocc') {\n        switchInspectorTab('tabCampaignOperations');\n      }"
replacement_startup = """initMoccEngine();
      if (params.get('mocc') === '1' || params.get('tab') === 'mocc') {
        switchInspectorTab('tabCampaignOperations');
      }
      // Milestone 13I: Initialize Atlas Mission Assurance Lab
      initMissionAssuranceEngine();
      if (params.get('assurance') === '1' || params.get('tab') === 'assurance' || params.get('tab') === 'mission_assurance') {
        switchInspectorTab('tabMissionAssurance');
      }"""

if target_startup not in content:
    target_startup = target_startup.replace("\n", "\r\n")
    replacement_startup = replacement_startup.replace("\n", "\r\n")

if target_startup in content:
    content = content.replace(target_startup, replacement_startup, 1)
else:
    print("Warning: target_startup not matched cleanly!")

app_js_path.write_text(content, encoding="utf-8")
print("Initial hook replacements completed.")
