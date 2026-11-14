---
name: marswalk-regression-guardian
description: >-
  Executes disciplined test-driven verification and regression quality gates for MarsWalk 2.0 / Project Atlas.
  Identifies focused test suites, validates JavaScript syntax, checks Draft 2020-12 schemas, runs preflight
  readiness checks, distinguishes pre-existing vs newly introduced failures, and enforces operational data preservation.
---

# MarsWalk Regression Guardian Skill

## Purpose
Enforce repeatable, disciplined test-driven verification across MarsWalk 2.0 / Project Atlas without weakening assertions or risking operational data loss.

## Operational Directives & Quality Gates
1. **Targeted First, Broad Second:** Always run the narrowest relevant test module before running broader repository regression batteries.
2. **Never Weaken Assertions:** When a test fails, fix the underlying defect or update outdated expectations with explicit rationale—never delete or weaken assertions merely to achieve a passing test run.
3. **Data Safety Guarantee:** Never delete or overwrite operational workspace records in `data/workspaces/` (`missions/`, `campaigns/`, `experiments/`, `rehearsals/`, `events/`). Use isolated temporary fixtures or mock IDs prefixed with `test_` or `cmp_test_`.
4. **JavaScript Syntax Verification:** Always run `node --check web/app.js` whenever frontend scripts are modified.
5. **Atlas Preflight Check:** Verify Atlas server readiness via `scripts/preflight_check.py` on port 3000.

## Verified Command Reference (Windows PowerShell)

### 1. Focused Unit & Integration Tests
```powershell
# Run dedicated test suite for a specific milestone or module
.\.venv\Scripts\python.exe -m pytest tests/test_milestone_12f_rehearsal.py -v

# Run with short summary
.\.venv\Scripts\python.exe -m pytest tests/test_milestone_12f_rehearsal.py -q
```

### 2. Milestone Test Suites
```powershell
# Run all Milestone 12 tests
.\.venv\Scripts\python.exe -m pytest -k "test_milestone_12" -v

# Run all Milestone 11 multi-sol campaign tests
.\.venv\Scripts\python.exe -m pytest -k "test_milestone_11" -q
```

### 3. Frontend & Preflight Validation
```powershell
# Validate JavaScript syntax (using available Cursor node helper or system node)
& "C:\Users\dhwan\AppData\Local\Programs\cursor\resources\app\resources\helpers\node.exe" --check web/app.js

# Verify 12/12 Atlas system preflight checkpoints
.\.venv\Scripts\python.exe scripts/preflight_check.py --port 3000
```

### 4. Full Repository Regression Suite
```powershell
# Run complete test suite (714+ tests) with timing
.\.venv\Scripts\python.exe -m pytest -q
```

## Verification Checklist
- [ ] Narrow unit tests pass with zero failures.
- [ ] No operational campaigns or mission workspaces were deleted or modified.
- [ ] Frontend JavaScript passes `node --check`.
- [ ] Relevant benchmarks satisfy latency budgets (<3.0s).
- [ ] JSON Schema Draft 2020-12 validation passes.
- [ ] Full regression suite passes without regression.
