import urllib.request

url = 'https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_derived_env/sol_0000_0089/sol_0010/WE__0010___________DER_TIRS________________P04.CSV'
req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = resp.read(2048)
    print('Fetched first 2KB of real TIRS CSV:')
    print(data.decode('utf-8', errors='ignore'))
