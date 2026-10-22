from pathlib import Path
import urllib.request,hashlib,json,concurrent.futures,subprocess
P=Path(__file__).resolve().parent/'sources'
items=[('Giacomini_White_2003.pdf','https://econwpa.ub.uni-muenchen.de/econ-wp/em/papers/0308/0308001.pdf'),('Matheson_IMF_2011.pdf','https://www.imf.org/-/media/Websites/IMF/imported-full-text-pdf/external/pubs/ft/wp/2011/_wp1193.ashx')]
def get(item):
 name,url=item;f=P/name
 try:
  if f.exists():b=f.read_bytes()
  else:
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as r:b=r.read()
   assert b.startswith(b'%PDF');f.write_bytes(b)
  subprocess.run(['pdftotext','-layout',str(f),str(f.with_suffix('.txt'))],check=True)
  return dict(file=name,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),status='downloaded')
 except Exception as e:return dict(file=name,url=url,status='failed',error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:rows=list(ex.map(get,items))
(P/'method_download_manifest.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
