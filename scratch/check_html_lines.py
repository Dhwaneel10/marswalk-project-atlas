with open('web/index.html', 'rb') as f:
    lines = f.readlines()
for i in range(774, 784):
    print(i+1, repr(lines[i]))
