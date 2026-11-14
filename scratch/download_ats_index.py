import urllib.request, os, hashlib

url = 'https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_calibrated_ATS.csv'
dest = 'data/environment/raw/meda/mars2020_meda_calibrated_ATS.csv'
req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = resp.read()
with open(dest, 'wb') as f:
    f.write(data)
sha = hashlib.sha256(data).hexdigest()
print(f'Saved calibrated ATS index: {len(data)} bytes, SHA-256: {sha}')
