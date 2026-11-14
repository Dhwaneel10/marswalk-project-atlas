path = "README.md"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = "- **Milestone 13J Atlas Fleet Intelligence:**"
new_line = """- **Milestone 13K Goal-Driven Mission Design Compiler:** [`docs/milestone-13k-final-report.md`](docs/milestone-13k-final-report.md) — Natural-language mission intent parsing, remote sensing validation, Directed Acyclic Task Graph (DAG) decomposition, hard vs soft constraint engine, 7-level hierarchical fleet synthesis of 8 operational postures, non-dominated Pareto frontier extraction, forensic causal compilation debugger with 1-click relaxation, 6-scenario benchmark lab (Campaigns A–F), Atlas Mission Design Studio 2.0 interface, and 18-screenshot conference showcase gallery.
- **Milestone 13J Atlas Fleet Intelligence:**"""

assert target in text, "target not found"
text = text.replace(target, new_line, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated README.md with Milestone 13K")
