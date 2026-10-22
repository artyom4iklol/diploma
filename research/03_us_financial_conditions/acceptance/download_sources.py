import urllib.request,urllib.error,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
p=Path(__file__).resolve().parent;(p/'sources').mkdir(exist_ok=True)
urls={'GW2006.pdf':'https://economia.uc3m.es/jgonzalo/teaching/PhdTimeSeries/GiacominiWhite.pdf','nfci_vintage_2020.csv':'https://alfred.stlouisfed.org/graph/alfredgraph.csv?id=NFCI&cosd=2019-01-01&coed=2020-12-31&vintage_date=2020-12-31','ciss_geo.csv':'https://data-api.ecb.europa.eu/service/data/CISS/D..Z0Z.4F.EC.SS_CIN.IDX?startPeriod=2025-12-01&endPeriod=2025-12-02&format=csvdata','gdp_vintage_metadata.html':'https://ec.europa.eu/eurostat/cache/metadata/en/euroind_vtg_esms.htm','eabcn_status.html':'https://eabcn.org/data/eabcn-real-time-database'}
def get(item):
 name,url=item
 try:
  with urllib.request.urlopen(url,timeout=20) as r:b=r.read();code=r.status;ctype=r.headers.get('Content-Type')
  (p/'sources'/name).write_bytes(b);return dict(file=name,url=url,status=code,bytes=len(b),saved=True,content_type=ctype)
 except Exception as e:return dict(file=name,url=url,error=str(e),saved=False)
log=list(ThreadPoolExecutor(5).map(get,urls.items()));(p/'download_log.json').write_text(json.dumps(log,indent=2));print(json.dumps(log,indent=2))
