with open("web/index.html", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines[2883:], 2884):
    if 'class="inspector-tab-panel' in l:
        print(f"Line {i}: {l.strip()[:80]}")
        break
