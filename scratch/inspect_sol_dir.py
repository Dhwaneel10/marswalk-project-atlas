import urllib.request
import re

url = 'https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_derived_env/sol_0000_0089/sol_0010/'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    links = re.findall(r'href=[\'"]([^\'">?]+)[\'"]', html)
    print('Found links in sol_0000_0089:', len(links))
    for l in links[:20]:
        print('  ', l)
except Exception as e:
    print('Error:', e)
