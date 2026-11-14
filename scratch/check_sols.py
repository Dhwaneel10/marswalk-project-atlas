import csv

with open('data/environment/raw/meda/mars2020_meda_calibrated_ATS.csv', 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    sols = {}
    for row in reader:
        if len(row) > 11 and row[6].strip():
            sol = int(row[6])
            ltst = row[10]
            sols.setdefault(sol, []).append(ltst)

print("Total distinct sols with ATS:", len(sols))
for sol, times in list(sols.items())[:10]:
    print(f"Sol {sol}: {len(times)} passes, times: {times[:3]}")
