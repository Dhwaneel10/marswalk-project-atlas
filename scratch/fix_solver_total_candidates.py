path = "src/marswalk/core/mission_plan_solver.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

old_block = """    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:"""

new_block = """    created_at_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    @property
    def total_candidates(self) -> int:
        return len(self.candidates)

    def to_dict(self) -> Dict[str, Any]:"""

assert old_block in text or old_block.replace("\n", "\r\n") in text, "old_block not found"
text = text.replace(old_block, new_block).replace(old_block.replace("\n", "\r\n"), new_block.replace("\n", "\r\n"))

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated mission_plan_solver.py successfully")
