import csv
import json
import os
import hashlib
from scipy.io import netcdf_file

REPO_ROOT = os.path.abspath(r"E:\Python\NASA-Spaceapps\Marswalk")
RAW_DIR = os.path.join(REPO_ROOT, "data", "environment", "raw")
INDEX_PATH = os.path.join(REPO_ROOT, "data", "environment", "index", "source_acquisition_manifest.json")

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)

print(f"Total manifest products: {len(manifest['products'])}")
for prod in manifest["products"]:
    rel = prod["relative_path"]
    full = os.path.join(REPO_ROOT, rel)
    exists = os.path.exists(full)
    size = os.path.getsize(full) if exists else 0
    with open(full, "rb") as bf:
        sha = hashlib.sha256(bf.read()).hexdigest()
    match = (sha == prod["sha256_checksum"])
    print(f"Product: {prod['product_id']}")
    print(f"  Path: {rel} | Exists: {exists} | Size: {size} bytes")
    print(f"  SHA256 Match: {match} (Computed: {sha[:12]}... Manifest: {prod['sha256_checksum'][:12]}...)")
    
    if rel.endswith(".csv") or rel.endswith(".CSV"):
        with open(full, "r", encoding="utf-8", errors="replace") as cf:
            reader = csv.reader(cf)
            rows = [next(reader, None) for _ in range(3)]
            print(f"  Header: {rows[0]}")
            if rows[1]:
                print(f"  Sample Row 1: {rows[1]}")
    elif rel.endswith(".nc"):
        with netcdf_file(full, 'r', mmap=False) as nc:
            print(f"  NetCDF Dimensions: {list(nc.dimensions.keys())}")
            print(f"  NetCDF Variables: {list(nc.variables.keys())}")
    elif rel.endswith(".json"):
        with open(full, "r", encoding="utf-8") as jf:
            jd = json.load(jf)
            if isinstance(jd, list):
                print(f"  JSON List Count: {len(jd)}")
                if len(jd) > 0 and isinstance(jd[0], dict):
                    print(f"  JSON Sample Keys: {list(jd[0].keys())}")
            elif isinstance(jd, dict):
                print(f"  JSON Top Keys: {list(jd.keys())}")
    print()
