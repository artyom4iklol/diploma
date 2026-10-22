"""Acquire a bounded set of official historical CSV snapshots; modelling is offline."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
import io,json,hashlib,time
import pandas as pd

P=Path(__file__).resolve().parent
S=P/'sources';S.mkdir(exist_ok=True)
def fetch_one(item):
 name,url=item
 path=S/name;path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():data=path.read_bytes()
 else:
  err=None
  for attempt in range(3):
   try:
    req=Request(url,headers={'User-Agent':'Academic thesis replication data download'})
    with urlopen(req,timeout=45) as f:data=f.read()
    path.write_bytes(data);err=None;break
   except Exception as e:err=e;time.sleep(1+attempt)
  if err:raise err
 rec=dict(path=name,url=url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),retrieved_at=datetime.now(timezone.utc).isoformat())
 if path.suffix=='.csv':
  d=pd.read_csv(io.BytesIO(data));assert len(d.columns)==2,(name,d.columns)
  dt=pd.to_datetime(d.iloc[:,0]);v=pd.to_numeric(d.iloc[:,1],errors='coerce');valid=v.notna()
  assert valid.sum()>500 and not dt.duplicated().any(),name
  rec.update(columns=list(d.columns),n=int(valid.sum()),first_observation=str(dt[valid].min().date()),last_observation=str(dt[valid].max().date()))
 return rec

def url(series,cutoff,start='1995-01-01',end=None):
 return 'https://alfred.stlouisfed.org/graph/alfredgraph.csv?'+urlencode(dict(id=series,cosd=start,coed=end or cutoff,vintage_date=cutoff))

def run():
 manifest=json.loads((P.parent/'revision16/sources/nfci_vintages/manifest.json').read_text())
 items=[('anfci_vintages/anfci_'+r['vintage_date']+'.csv',url('ANFCI',r['vintage_date'])) for r in manifest]
 items += [('current/'+series.lower()+'_2026-10-16.csv',url(series,'2026-10-16',end='2025-12-31')) for series in ['NFCI','ANFCI']]
 # Extra weekly snapshots bracket the 2017 redefinition; they do not set forecasts.
 for date in ['2017-08-30','2017-09-06','2017-09-07','2017-09-13','2017-09-20','2017-09-27','2017-10-04']:
  items.append(('method2017/anfci_'+date+'.csv',url('ANFCI',date,start='1971-01-01')))
 sources=[
  ('ANFCI_about.html','https://www.chicagofed.org/research/data/nfci/about'),
  ('ANFCI_method2017.html','https://www.chicagofed.org/publications/chicago-fed-letter/2017/386'),
  ('ANFCI_method2017.pdf','https://www.chicagofed.org/-/media/publications/chicago-fed-letter/2017/cfl386-pdf.pdf?sc_lang=en'),
  ('NFCI_launch2011.html','https://www.chicagofed.org/utilities/newsroom/news-releases/2011/04-05-nfci-release'),
  ('ANFCI_alfred_metadata.html','https://alfred.stlouisfed.org/series?seid=ANFCI'),
  ('ANFCI_fred_metadata.html','https://fred.stlouisfed.org/series/ANFCI'),
  ('NFCI_fred_metadata.html','https://fred.stlouisfed.org/series/NFCI'),
  ('Chicago_legal.html','https://www.chicagofed.org/utilities/legal-notices'),
  ('FRED_legal.html','https://fred.stlouisfed.org/legal/'),
  ('ECB_legal.html','https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html'),
  ('EC_legal.html','https://commission.europa.eu/legal-notice_en'),
 ]
 # Two concurrent byte transfers avoid hammering the public service.
 records=[];errors=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  jobs={pool.submit(fetch_one,x):x for x in items+sources}
  for future in as_completed(jobs):
   name,u=jobs[future]
   try:records.append(future.result())
   except Exception as e:errors.append(dict(path=name,url=u,error=str(e)))
   if (len(records)+len(errors))%10==0:print('completed',len(records),'errors',len(errors),flush=True)
 records.sort(key=lambda x:x['path'])
 (S/'download_manifest.json').write_text(json.dumps(dict(files=records,errors=errors),ensure_ascii=False,indent=2))
 byname={x['path']:x for x in records}
 vintage=[]
 for x in manifest:
  key='anfci_vintages/anfci_'+x['vintage_date']+'.csv'
  if key in byname:vintage.append(dict(origin=x['origin'],vintage_date=x['vintage_date'],**byname[key]))
 (S/'anfci_vintages/manifest.json').write_text(json.dumps(vintage,ensure_ascii=False,indent=2))
 assert len(vintage)==59,(len(vintage),errors)
 print(json.dumps(dict(historical_versions=len(vintage),other_sources=len(records)-len(vintage),errors=errors),ensure_ascii=False,indent=2))

if __name__=='__main__':run()
