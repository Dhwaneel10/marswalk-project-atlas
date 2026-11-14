with open('scripts/run_atlas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'def do_' in line or 'handle_' in line or 'relay' in line:
        print(f"{i+1}: {line.strip()}")
