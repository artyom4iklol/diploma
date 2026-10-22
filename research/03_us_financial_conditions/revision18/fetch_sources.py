from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
P=Path(__file__).resolve().parent/'sources';P.mkdir(exist_ok=True)
items=[('bulletin_releases.html','https://www.ecb.europa.eu/press/economic-bulletin/html/all_releases.en.html'),('monthly_bulletins.html','https://www.ecb.europa.eu/press/economic-bulletin/mb/html/index.en.html')]
for y,i in [(2022,4),(2023,2),(2023,4),(2025,6)]:items.append((f'eb{y}{i:02d}.pdf',f'https://www.ecb.europa.eu/pub/pdf/ecbu/eb{y}{i:02d}.en.pdf'))
def get(item):
 name,url=item;f=P/name
 try:
  if f.exists():b=f.read_bytes()
  else:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:b=r.read()
   f.write_bytes(b)
  if name.endswith('.pdf'):assert b.startswith(b'%PDF')
  return dict(file=name,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),status='ok')
 except Exception as e:return dict(file=name,url=url,status='failed',error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:rows=list(ex.map(get,items))
(P/'download_manifest.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
