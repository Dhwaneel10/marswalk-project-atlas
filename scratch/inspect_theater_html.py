with open('web/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [line.strip() for line in text.split('\n') if 'theater-controls' in line or 'btnTheater' in line or 'theaterInspector' in line]
for m in matches[:15]:
    print(m)
