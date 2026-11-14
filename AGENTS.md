# MarsWalk Project Rules

## Scope
- Work only inside E:\Python\NASA-Spaceapps\Marswalk.
- Do not modify sibling projects or unrelated files.
- Inspect existing files before creating or changing anything.

## Research and science
- Read docs/research-report.md and docs/challenge-brief.md when available.
- Verify important scientific claims against primary sources.
- Preserve dataset provenance, attribution, coordinate systems, units and no-data masks.
- Never invent measurements or present synthetic data as real Martian observations.
- Distinguish measured data, derived quantities and model estimates.
- Never call a modeled route operationally safe for astronauts.

## Development workflow
- For substantial changes, present a plan and acceptance criteria before editing.
- Work in small, testable stages.
- Do not install dependencies, download large datasets, or delete files without asking first.
- Ask before downloading any individual dataset larger than 100 MB.
- Keep tests alongside the implementation.
- Run relevant tests after changes and report actual results.
- Do not claim that a test, browser check or scientific validation passed unless it was performed.
- Preserve working functionality and explain breaking changes before making them.

## Priorities
1. A working, validated Martian route-planning prototype.
2. Reproducible scientific calculations and traceable data sources.
3. Clear route comparison and scientific explanation.
4. Visual polish and optional features only after the core works.
