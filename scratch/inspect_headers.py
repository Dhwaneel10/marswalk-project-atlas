import csv

def inspect_csv(path, n=5):
    print(f"=== {path} ===")
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        header = next(reader)
        print("Columns (", len(header), "):", header)
        for i, row in enumerate(reader):
            if i < n:
                print(f"Row {i+1}:", row[:8])

inspect_csv('data/environment/raw/meda/WE__0010___________DER_TIRS________________P04.CSV', 3)
inspect_csv('data/environment/raw/meda/WE__0010___________CAL_ATS_________________P01.CSV', 3)
