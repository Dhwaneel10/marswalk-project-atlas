import urllib.request
import re

url = "https://planetarynames.wr.usgs.gov/GIS_Downloads"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as r:
    html = r.read().decode("utf-8")

# Find all links containing 'Mars' or 'mars'
links = re.findall(r'href=["\']([^"\']*mars[^"\']*)["\']', html, re.IGNORECASE)
print("Found links count:", len(links))
for link in sorted(set(links)):
    print(" -", link)
