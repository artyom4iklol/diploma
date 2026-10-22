"""Public official data only. Successful bytes retained with hashes and URLs."""
from pathlib import Path
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,hashlib
P=Path(__file__).resolve().parent;S=P/'sources'
items=[('equity_history_all.csv','https://data-api.ecb.europa.eu/service/data/RTD/M.S0.N.C_DJE50.X?includeHistory=true&startPeriod=1994-01&endPeriod=2025-12&format=csvdata'),('eb202004.pdf','https://www.ecb.europa.eu/pub/pdf/ecbu/eb202004.en.pdf'),('eb202102.pdf','https://www.ecb.europa.eu/pub/pdf/ecbu/eb202102.en.pdf'),('Cho_Rho_Appendix.pdf','https://seunghwarho.github.io/docs/Appendix.pdf')]
def get(item):
 name,url=item;p=S/name
 try:
  with urlopen(Request(url,headers={'User-Agent':'Academic thesis research'}),timeout=45) as r:b=r.read()
  assert b.startswith(b'%PDF-' if name.endswith('.pdf') else b'KEY,')
  p.write_bytes(b);out=dict(file=name,url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),retrieved=datetime.now(timezone.utc).isoformat())
 except Exception as e:out=dict(file=name,url=url,error=str(e))
 print(out,flush=True);return out
if __name__=='__main__':
 with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(get,items))
 (S/'download_log.json').write_text(json.dumps(rows,indent=2)+'\n')
