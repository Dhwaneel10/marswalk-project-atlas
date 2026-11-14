with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(700, min(770, len(lines))):
    print(f"{i+1}: {lines[i]}", end="")
