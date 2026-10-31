"""Download/cache official public sources. No model fitting or missing-value imputation."""
from pathlib import Path
import concurrent.futures as cf
import urllib.request, hashlib, json, datetime, time

ROOT=Path(__file__).resolve().parent
RAW=ROOT/'data/raw'
SOURCES={
 'AWMD_Sep2026.zip': ('https://eabcn.org/sites/default/files/2026-09/AWMD_Sep2026.zip','EABCN, AWM September 2026; EA21; late reconstructed history'),
 'fred_BAA10YM.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAA10YM','FRED; monthly Moody Baa minus 10-year Treasury yield'),
 'fred_GS10.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=GS10','Federal Reserve H.15 via FRED; monthly 10-year constant maturity'),
 'fred_TB3MS.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=TB3MS','Federal Reserve H.15 via FRED; monthly 3-month bill, discount basis'),
 'fred_VIXCLS.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS','CBOE via FRED; daily VIX, reconstructed history before methodology changes'),
 'fred_NFCI.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=NFCI','Chicago Fed via FRED; current NFCI, not historical vintages'),
 'fred_ANFCI.csv': ('https://fred.stlouisfed.org/graph/fredgraph.csv?id=ANFCI','Chicago Fed via FRED; current ANFCI, not historical vintages'),
 'ecfin_main_indicators_202610.zip': ('https://ec.europa.eu/economy_finance/db_indicators/surveys/documents/series/nace2_ecfin_2610/main_indicators_sa_nace2.zip','DG ECFIN official October 2026 main indicator release'),
 'ecb_stoxx50.csv': ('https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.DS.EI.DJES50I.HSTA?format=csvdata','ECB FM; monthly average EURO STOXX 50 price index; current series key'),
 'ecb_ciss_ea.csv': ('https://data-api.ecb.europa.eu/service/data/CISS/D.U2.Z0Z.4F.EC.SS_CIN.IDX?format=csvdata','ECB NEW daily CISS; current reconstructed history, supplementary control, not legacy weekly CISS'),
 'eurostat_gdp_EA21.json': ('https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp?lang=en&geo=EA21&freq=Q&na_item=B1GQ&unit=CLV20_MEUR&s_adj=SCA','Eurostat EA21 GDP, independent source check of post-1995 AWM GDP'),
 'ecfin_timeseries_page.html': ('https://economy-finance.ec.europa.eu/economic-forecast-and-surveys/business-and-consumer-surveys/download-business-and-consumer-survey-data/time-series_en','ECFIN source index and download provenance'),
 'eabcn_chronology.html': ('https://eabcn.org/dbc/peaksandtroughs/chronology-euro-area-business-cycles','CEPR/EABCN official peak/trough chronology and announcement dates'),
 'firth_method.html': ('https://data-science.meduniwien.ac.at/services/klinische-biometrie/software/statistische-software/firth-correction/','Firth / FLIC methodological explanation by method developers'),
 'puhr_2017_abstract.html': ('https://pubmed.ncbi.nlm.nih.gov/28295456/','Puhr et al. 2017, Statistics in Medicine, DOI 10.1002/sim.7273'),
}

def one(item):
 name,(url,note)=item;p=RAW/name
 if p.exists() and p.stat().st_size>100:
  b=p.read_bytes(); status='cached'
 else:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (academic reproducible research)','Accept':'*/*'})
  try:
   with urllib.request.urlopen(req,timeout=40) as r:b=r.read()
   if len(b)<100:raise ValueError('Unexpected short response')
   if name.endswith('.csv') and b'<' in b[:100]:raise ValueError('HTML returned for CSV')
   if name.endswith('.zip') and not b.startswith(b'PK'):raise ValueError('Not a ZIP')
   p.write_bytes(b);status='downloaded'
  except Exception as e:
   return {'file':name,'url':url,'description':note,'status':'failed','error':str(e)}
 return {'file':name,'url':url,'description':note,'status':status,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'retrieved_on':'2026-10-31','version_status':'current or reconstructed; not automatically point-in-time'}

def main():
 RAW.mkdir(parents=True,exist_ok=True)
 with cf.ThreadPoolExecutor(max_workers=5) as pool:
  rows=list(pool.map(one,SOURCES.items()))
 (ROOT/'data/source_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 for x in rows:print(x['file'],x['status'],x.get('bytes',x.get('error')) ,flush=True)

if __name__=='__main__':main()
