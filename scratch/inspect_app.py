with open('src/marswalk/app.py', 'r', encoding='utf-8') as f:
    lines = [f.readline() for _ in range(50)]
print("--- src/marswalk/app.py top lines ---")
print("".join(lines))
