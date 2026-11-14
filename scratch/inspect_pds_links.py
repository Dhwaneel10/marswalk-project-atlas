import urllib.request
import re

base_page = 'https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html'
try:
    req = urllib.request.Request(base_page, headers={'User-Agent': 'MarsWalk/2.0 ResearchBot'})
    with urllib.request.urlopen(req, timeout=10) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    links = re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)
    print('Found links:', len(links))
    meda_links = [l for l in links if 'meda' in l.lower() or 'pds4' in l.lower()]
    for l in meda_links:
        print('  ', l)
except Exception as e:
    print('Error:', e)
