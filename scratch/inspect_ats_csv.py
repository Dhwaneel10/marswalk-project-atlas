import urllib.request

url = 'https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/logs/mars2020_meda_calibrated_ATS.csv'
req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
with urllib.request.urlopen(req, timeout=10) as resp:
    data = resp.read(2048)
    print('Fetched first 2KB of calibrated ATS CSV log:')
    print(data.decode('utf-8', errors='ignore'))
