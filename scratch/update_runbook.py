section_13e = '''
### Milestone 13E: Atlas Joint Mission Co-Design Verification
To verify the Joint Mission Planner multi-objective optimization, submodular relay sweep, and Pareto frontier test suite:
```powershell
.\\.venv\\Scripts\\pytest.exe tests/test_milestone_13e_joint_planner.py -v
```
*Expected Result:* `15 passed in ~4.5s`.

To verify browser CDP interaction, interactive Pareto scatter analysis, 3D Theater candidate hierarchy, and 0 console errors:
```powershell
.\\.venv\\Scripts\\python.exe scripts/verify_joint_mission_browser.py
```
*Expected Result:* All 8 showcase screenshots captured in `outputs/conference_showcase/joint_mission/`, 0 console errors, 0 horizontal overflow.
'''

with open('docs/v2-demonstration-runbook.md', 'r', encoding='utf-8') as f:
    rb = f.read()

if 'Milestone 13E' not in rb:
    with open('docs/v2-demonstration-runbook.md', 'w', encoding='utf-8') as f:
        f.write(rb + '\n' + section_13e)
    print("Updated docs/v2-demonstration-runbook.md")
else:
    print("docs/v2-demonstration-runbook.md already has Milestone 13E")
