from pathlib import Path
import urllib.request,concurrent.futures,json
P=Path(__file__).resolve().parent/'sources'
items=[('esi_calendar_2017.pdf','https://economy-finance.ec.europa.eu/system/files/2017-01/schedule_2017.pdf'),('esi_calendar_2021.pdf','https://economy-finance.ec.europa.eu/system/files/2020-12/publication_dates_2021.pdf'),('esi_calendar_2020.pdf','https://economy-finance.ec.europa.eu/document/download/f9b1f857-6d70-49c0-8bcd-fa7678551cbc_en?filename=publication_dates_2020.pdf'),('nfci_launch_2011.html','https://www.chicagofed.org/utilities/newsroom/news-releases/2011/04-05-nfci-release'),('ecb_fsr_may2020.html','https://www.ecb.europa.eu/press/financial-stability-publications/fsr/html/ecb.fsr202005~1b75555f66.en.html')]
items += [(f'esi_release_2016_{m:02d}.pdf',f'https://ec.europa.eu/economy_finance/db_indicators/surveys/documents/2016/bcs_2016_{m:02d}_en.pdf') for m in [1,2,4,5,7,8,10,11]]
def get(x):
 name,url=x
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=12) as r:b=r.read()
  ok=b.startswith(b'%PDF') if name.endswith('.pdf') else len(b)>1000
  if ok:(P/name).write_bytes(b)
  return dict(file=name,url=url,ok=ok,bytes=len(b))
 except Exception as e:return dict(file=name,url=url,ok=False,error=str(e))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:rs=list(ex.map(get,items))
(P/'additional_downloads2.json').write_text(json.dumps(rs,indent=2));print(rs)
