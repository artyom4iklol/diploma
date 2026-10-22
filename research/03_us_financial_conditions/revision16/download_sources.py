from pathlib import Path
import urllib.request,concurrent.futures,json,hashlib
P=Path(__file__).resolve().parent/'sources';P.mkdir(exist_ok=True)
def get(item):
 name,url=item
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (academic data audit)'})
  with urllib.request.urlopen(req,timeout=18) as r:body=r.read();status=r.status
  ok=(body.startswith(b'%PDF') if name.endswith('.pdf') else len(body)>200)
  if ok:(P/name).write_bytes(body)
  return dict(file=name,url=url,status=status,ok=ok,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
 except Exception as e:return dict(file=name,url=url,ok=False,error=str(e))
items=[(f'esi_calendar_{y}.pdf',f'https://ec.europa.eu/economy_finance/db_indicators/surveys/documents/calendar/Publication%20dates%20{y}.pdf') for y in range(2010,2026)]
items += [('Miranda_Rey_NBER21722.pdf','https://www.nber.org/system/files/working_papers/w21722/w21722.pdf'),('Kaufmann_ECB2489.pdf','https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2489~26b7eca600.en.pdf'),('Bruno_Shin_BIS458.pdf','https://www.bis.org/publ/work458.pdf'),('Brandt_ECB2560.pdf','https://www.ecb.europa.eu/pub/pdf/scpwps/ecb.wp2560~f98f3c7d78.en.pdf'),('Habib_Venditti_2018.html','https://www.ecb.europa.eu/press/economic-bulletin/articles/2018/html/ecb.ebart201806_01.en.html'),('eurostat_gdp_metadata.html','https://ec.europa.eu/eurostat/cache/metadata/en/namq_10_esms.htm'),('nfci_current.html','https://www.chicagofed.org/research/data/nfci/current-data'),('ciss_metadata.html','https://data.ecb.europa.eu/data/datasets/CISS')]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:rows=list(ex.map(get,items))
(P/'download_log.json').write_text(json.dumps(rows,indent=2));print(json.dumps([{k:x[k] for k in ['file','ok','bytes','error'] if k in x} for x in rows],indent=2))
