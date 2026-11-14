# Project Atlas — Reusable Antigravity Engineering Skillpack

## Overview
Milestone 12G introduces a project-specific, reusable **Antigravity Engineering Skillpack** located in [`.agents/skills/`](file:///E:/Python/NASA-Spaceapps/Marswalk/.agents/skills/). These Skills codify MarsWalk's architectural rules, planetary science integrity standards, automated browser testing, and regression quality gates into declarative, reusable agent capabilities.

---

## 1. Skill Inventory

| Skill Name | Directory | Primary Purpose | Activation Criteria |
| :--- | :--- | :--- | :--- |
| **`marswalk-regression-guardian`** | [`.agents/skills/marswalk-regression-guardian/`](file:///E:/Python/NASA-Spaceapps/Marswalk/.agents/skills/marswalk-regression-guardian/SKILL.md) | Enforces test-driven verification, JS syntax audits, preflight readiness checks, operational data protection, and full regression runs. | When modifying Python core logic, running tests, refactoring modules, or executing quality gates. |
| **`marswalk-scientific-integrity`** | [`.agents/skills/marswalk-scientific-integrity/`](file:///E:/Python/NASA-Spaceapps/Marswalk/.agents/skills/marswalk-scientific-integrity/SKILL.md) | Audits data provenance (USGS CTX 20m Jezero DEM, PDS4 atmosphere), coordinates (`ESRI:103885`), units, and enforces mandatory non-probabilistic truth disclosures. | When working on route costs, elevation, terrain analysis, scenario metrics, or exporting evidence bundles. |
| **`marswalk-browser-acceptance`** | [`.agents/skills/marswalk-browser-acceptance/`](file:///E:/Python/NASA-Spaceapps/Marswalk/.agents/skills/marswalk-browser-acceptance/SKILL.md) | Automates end-to-end Chrome DevTools Protocol (CDP) verification across desktop ($1920\times1080$) and laptop ($1366\times768$) viewports with screenshot capture. | When updating frontend UI (`web/index.html`, `web/app.js`, `web/styles.css`), checking state transitions, or auditing user workflows. |

---

## 2. Skill Architecture & Standards

All Skills conform to Antigravity Customization System standards:
1. **YAML Frontmatter:** Valid `name` and descriptive `description` explaining exact capabilities and trigger criteria.
2. **Project-Relative Paths:** Uses `.venv\Scripts\python.exe` and repo-relative paths, avoiding fragile hardcoded host paths.
3. **Data Safety Priority:** Explicit prohibitions against deleting or overwriting operational mission campaigns, observation logs, or user experiments.
4. **Authentic Science Integrity:** Mandatory prohibition against claiming simulated scenario frequencies as physical Martian probabilities or claiming routes are certified safe for astronauts.

---

## 3. Verification & Usability Demonstration

Each Skill has been exercised and validated on actual project tasks:
- **`marswalk-regression-guardian`:** Successfully audited `web/app.js` with node, executed focused test suite `tests/test_milestone_12f_rehearsal.py` (13/13 passing), and verified preflight check (12/12 passing).
- **`marswalk-scientific-integrity`:** Verified dataset ID `USGS_CTX_DTM_JEZERO_20M`, SHA-256 hash `875e7e80c170b84e...`, CRS `ESRI:103885`, and confirmed non-probabilistic disclosures in all models.
- **`marswalk-browser-acceptance`:** Successfully ran automated CDP audit across $1920\times1080$ and $1366\times768$ viewports with 0 horizontal overflows and verified screenshot capture.
