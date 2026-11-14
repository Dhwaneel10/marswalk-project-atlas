import urllib.request, os, hashlib

files = [
    ('https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_derived_env/sol_0000_0089/sol_0010/WE__0010___________DER_TIRS________________P04.CSV',
     'data/environment/raw/meda/WE__0010___________DER_TIRS________________P04.CSV'),
    ('https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_calibrated_env/sol_0000_0089/sol_0010/WE__0010___________CAL_ATS_________________P01.CSV',
     'data/environment/raw/meda/WE__0010___________CAL_ATS_________________P01.CSV')
]

for url, dest in files:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        sha = hashlib.sha256(data).hexdigest()
        print(f'Saved {os.path.basename(dest)}: {len(data)} bytes, SHA-256: {sha}')
    except Exception as e:
        print(f'Failed {os.path.basename(dest)}: {e}')
