with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(30, 95):
    print(f"{i+1}: {lines[i]}", end="")
