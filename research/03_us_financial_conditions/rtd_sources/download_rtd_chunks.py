"""Bounded recovery pass over ECB RTD observation years; successful chunks cached.

includeHistory responses contain vintage event timestamps. VALID_FROM must not
be interpreted automatically as the public release time of an Economic Bulletin.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,json,hashlib,io
import pandas as pd
P=Path(__file__).resolve().parent;O=P/'history_chunks';O.mkdir(exist_ok=True)
jobs=[(s,y) for s in ['esi','gdp'] for y in range(1995,2026)]
def get(job):
 s,y=job
 key='M.S0.S.Y_ESIND.F' if s=='esi' else 'Q.S0.S.G_GDPM_TO_C.E'
 start=f'{y}-01' if s=='esi' else f'{y}-Q1';end=f'{y}-12' if s=='esi' else f'{y}-Q4'
 url=f'https://data-api.ecb.europa.eu/service/data/RTD/{key}?includeHistory=true&startPeriod={start}&endPeriod={end}&format=csvdata'
 f=O/f'{s}_{y}.csv'
 try:
  if f.exists():b=f.read_bytes()
  else:
   with urllib.request.urlopen(url,timeout=15) as r:b=r.read()
  x=pd.read_csv(io.BytesIO(b));assert {'TIME_PERIOD','OBS_VALUE','VALID_FROM','ACTION'}<=set(x)
  assert len(x)>0
  f.write_bytes(b)
  stamps=x.VALID_FROM.dropna().astype(str)
  return dict(series=s,observation_year=y,url=url,file='history_chunks/'+f.name,status='verified_history_response',rows=len(x),periods=x.TIME_PERIOD.nunique(),vintage_event_dates=x.VALID_FROM.nunique(),rows_without_valid_from=int(x.VALID_FROM.isna().sum()),first_event=str(stamps.min()) if len(stamps) else None,last_event=str(stamps.max()) if len(stamps) else None,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
 except Exception as e:return dict(series=s,observation_year=y,url=url,status='not_recovered',error=str(e))
if __name__=='__main__':
 rows=[]
 with ThreadPoolExecutor(max_workers=4) as ex:
  for x in ex.map(get,jobs):
   rows.append(x);(P/'rtd_chunk_manifest.json').write_text(json.dumps(rows,indent=2))
   print(x['series'],x['observation_year'],x['status'],x.get('rows',x.get('error')),flush=True)
 print('Verified',sum(x['status']=='verified_history_response' for x in rows),'of',len(rows),flush=True)
