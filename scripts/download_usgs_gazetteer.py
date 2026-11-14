import os
import zipfile
import urllib.request

KMZ_URL = "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MARS_nomenclature_center_pts.kmz"
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
KMZ_PATH = os.path.join(RAW_DIR, "MARS_nomenclature_center_pts.kmz")
KML_PATH = os.path.join(RAW_DIR, "MARS_nomenclature_center_pts.kml")

print(f"Downloading USGS Mars Nomenclature KMZ ({KMZ_URL})...")
req = urllib.request.Request(KMZ_URL, headers={"User-Agent": "Mozilla/5.0 (MarsWalk Data Pipeline)"})
with urllib.request.urlopen(req) as resp, open(KMZ_PATH, "wb") as f:
    f.write(resp.read())

print(f"Downloaded KMZ: {os.path.getsize(KMZ_PATH)} bytes.")

print("Extracting doc.kml...")
with zipfile.ZipFile(KMZ_PATH, "r") as z:
    names = z.namelist()
    print("Files in KMZ:", names)
    with z.open(names[0]) as source, open(KML_PATH, "wb") as target:
        target.write(source.read())

print(f"Extracted KML: {os.path.getsize(KML_PATH)} bytes.")
