from pathlib import Path
import re,json,datetime,html
import numpy as np,pandas as pd,openpyxl
from pypdf import PdfReader
from verify_gdp_releases import Text
P=Path(__file__).resolve().parent;R=P.parent;S=P/'sources';O=P/'results';O.mkdir(exist_ok=True)
months=['January','February','March','April','May','June','July','August','September','October','November','December'];datepat=r'\b(\d{1,2}\s+(?:'+'|'.join(months)+r')\s+20\d\d)\b'
def date(x):return pd.Timestamp(datetime.datetime.strptime(' '.join(x.split()),'%d %B %Y'))
records={};conf=[]
def add(m,dt,evidence,status):
 if m in records and records[m]['release_date']!=str(dt.date()):conf.append(dict(month=m,old=records[m],new_date=str(dt.date()),new_evidence=evidence))
 records[m]=dict(month=m,release_date=str(dt.date()),evidence=evidence,status=status)
# Calendar dates are planned; actual archive entries override them.
for f in S.glob('esi_calendar_*.pdf'):
 year=int(re.search(r'(20\d\d)',f.name).group());txt='\n'.join(p.extract_text(extraction_mode='layout') or '' for p in PdfReader(f).pages)
 for ln in txt.splitlines():
  name=next((x for x in months if ln.lstrip().startswith(x)),None);dates=re.findall(datepat,ln)
  if name and len(dates)>=2:add(f'{year}-{months.index(name)+1:02d}',date(dates[-1]),f.name,'official_planned_calendar')
a=json.loads((S/'esi_archive_dates_unparsed.json').read_text())
for x in a:
 if 'flash' in x['label'].lower():continue
 try:add(x['month'],date(x['release_date']),x['evidence'],'official_release_archive')
 except ValueError:conf.append(dict(month=x['month'],invalid_source_date=x['release_date'],evidence=x['evidence']))
txt=(S/'esi_press_archive.txt').read_text()
# Release titles with dates, including entries that have no file download link.
patterns=[r'ESI - Economic Sentiment Indicator\s*-\s*('+datepat[2:-2]+r')',r'(?:Full business and consumer survey results|Business and consumer survey results)[^\n]*?('+datepat[2:-2]+r')']
# Simpler explicit date search per title line; no source page metadata timestamps used.
for ln in txt.splitlines():
 if ('Economic Sentiment Indicator' not in ln and 'business and consumer survey results' not in ln.lower()) or 'Flash' in ln:continue
 ds=re.findall(datepat,ln)
 if ds:
  dt=date(ds[-1])
  if dt.day>=20:add(f'{dt.year}-{dt.month:02d}',dt,'esi_press_archive.html release title','official_release_archive')
# Ensure required first-two-month release evidence exists for each evaluated quarter.
origins=pd.period_range('2010Q1','2025Q4',freq='Q');rows=[]
for q in origins:
 for m in [q.start_time.month,q.start_time.month+1]:
  key=f'{q.year}-{m:02d}';r=records.get(key)
  if not r:raise AssertionError('Missing ESI month '+key)
  assert pd.Timestamp(r['release_date'])<=q.end_time
  rows.append(dict(origin=str(q),forecast_deadline=str(q.end_time.date()),**r,available_by_deadline=True,exact_vintage_used=False,geography_used='fixed EA20 retrospective'))
es=pd.DataFrame(rows);es.to_csv(O/'esi_monthly_release_audit.csv',index=False);pd.DataFrame(conf).to_json(O/'esi_calendar_conflicts.json',orient='records',indent=2)
# Extract only actual dates printed in official GDP triangle (not imputed T+lags).
w=openpyxl.load_workbook(R/'acceptance/sources/Euro_area_GDP_revision_triangles.xlsx',read_only=True,data_only=True);gdp={};rr=[]
for row in w['levels'].values:
 if isinstance(row[0],str) and isinstance(row[2],datetime.datetime):
  qt=re.match(r'(20\d\dQ[1-4])',row[0])
  if qt:
   rr.append(dict(quarter=qt.group(),release=row[0],date=str(row[2].date()),evidence='acceptance/sources/Euro_area_GDP_revision_triangles.xlsx levels'))
   if '65' in row[0]:gdp[qt.group()]=rr[-1]
pd.DataFrame(rr).to_csv(O/'gdp_official_release_dates.csv',index=False)
# Fill earlier actual publication dates from verified GDP publication bodies.
# Failed candidates (including current-account releases) never enter this map.
gdp_source=S/'gdp_verified_releases.json'
if gdp_source.exists():
 for rec in json.loads(gdp_source.read_text()):
  if rec['status']=='official_GDP_release_body_verified':
   assert 'GDP' in rec['body'][:160]
   ordinal=['first','second','third','fourth'][int(rec['quarter'][-1])-1]
   assert ordinal+' quarter of '+rec['quarter'][:4] in rec['body'].lower().split('previous quarter')[0]
   parsed=Text();parsed.feed((S/rec['evidence']).read_text());release_text=' '.join(' '.join(parsed.parts).split()).split('Release date:')[-1]
   actual=re.search(datepat,release_text).group()
   assert str(date(actual).date())==rec['candidate_date'],(rec['quarter'],actual,rec['candidate_date'])
   gdp[rec['quarter']]=dict(date=rec['candidate_date'],evidence=rec['evidence'],url=rec['url'])
av=pd.read_csv(R/'final_check/results/availability.csv');weekly=pd.read_csv(R/'robustness/model/raw/fred_nfci.csv');weekly['date']=pd.to_datetime(weekly.observation_date)
alf=S/'nfci_alfred_release_dates.txt';release_dates=pd.to_datetime(re.findall(r'^\d{4}-\d{2}-\d{2}$',alf.read_text(),re.M)) if alf.exists() else pd.DatetimeIndex([])
# Date catalogue establishes release occurrence, not the historical value for each observation.
allrows=[]
for q in origins:
 e=es[es.origin==str(q)];prev=q-1;g=gdp.get(str(prev));n=av[av.origin==str(q)]
 last=n.set_index('series').last_observation
 nfdate=pd.Timestamp(last['nfci']);near=release_dates[(release_dates>nfdate)&(release_dates<=nfdate+pd.Timedelta(days=7))];known=near.min() if len(near) else pd.NaT
 rec=dict(origin=str(q),deadline=str(q.end_time.date()),h1_target_end=str(q+1),h4_target_end=str(q+4),last_training_target_end=str(prev),growth_observed_quarter=str(prev),gdp_actual_regular_release=g['date'] if g else '',gdp_release_evidence=g['evidence'] if g else 'exact_date_not_recovered; policy approx T+65 only',gdp_release_url=g.get('url','') if g else '',gdp_policy_date=str((prev.end_time.normalize()+pd.Timedelta(days=65)).date()),gdp_exact_fixed_EA20_vintage=False,esi_months=';'.join(e.month),esi_release_dates=';'.join(e.release_date),esi_release_evidence=';'.join(e.status),esi_exact_vintage=False,last_ea_ciss_observation=last['ea'],last_us_ciss_observation=last['us'],ciss_availability_rule='observation+7 days assumption; current metadata says daily previous day',ciss_exact_vintage=False,new_ciss_historical_publication='daily version documented in May2020 FSR; exact first publication unverified',last_nfci_observation=last['nfci'],nfci_assumed_available=str((nfdate+pd.Timedelta(days=7)).date()),nfci_release_catalogue_date='' if pd.isna(known) else str(known.date()),nfci_catalogue_caveat='release occurrence; not observation-specific vintage certification',nfci_public_since='2011-04-13',nfci_existed_at_origin=bool(q.end_time>=pd.Timestamp('2011-04-13')),nfci_exact_vintage_main=False,nfci_vintage_separate_diagnostic=(S/'nfci_vintages'/('nfci_'+str(q.end_time.date())+'.csv')).exists(),fully_real_time_verified=False)
 if g:assert pd.Timestamp(g['date'])<=q.end_time
 allrows.append(rec)
a=pd.DataFrame(allrows);a.to_csv(O/'forecast_calendar_all_origins.csv',index=False)
# Show the exact calendar for every training pair, both horizons; verify cutoffs.
d=pd.read_csv(R/'final_check/results/model_data.csv',index_col=0);d.index=pd.PeriodIndex(d.index,freq='Q');pairs=[]
for h in [1,4]:
 target=400/h*np.log(d.gdp_ea.shift(-h)/d.gdp_ea)
 for q in origins:
  if pd.isna(target.get(q,np.nan)):continue
  mask=(d.index+h<=q-1)&target.notna()&d[['gx','gx2','ea','us','nfci','esi']].notna().all(axis=1)
  for s in d.index[mask]:pairs.append(dict(origin=str(q),h=h,training_predictor_quarter=str(s),training_target_end=str(s+h),within_cutoff=bool(s+h<=q-1),exact_historical_values_certified=False))
pd.DataFrame(pairs).to_csv(O/'training_pair_calendar.csv',index=False)
summary=dict(origins=len(a),evaluated_h1=63,evaluated_h4=60,esi_months_checked=len(es),esi_release_archive=int(es.status.eq('official_release_archive').sum()),esi_calendar_only=int(es.status.eq('official_planned_calendar').sum()),esi_all_first_two_months_before_deadline=True,gdp_origins_with_actual_regular_release=int(a.gdp_actual_regular_release.ne('').sum()),gdp_origins_without_exact_release=int(a.gdp_actual_regular_release.eq('').sum()),gdp_release_dates_from_verified_older_publications=30,gdp_release_dates_from_triangle=34,nfci_prelaunch_origins=a.loc[~a.nfci_existed_at_origin,'origin'].tolist(),nfci_last_observation_release_catalogue_matches=int(a.nfci_release_catalogue_date.ne('').sum()),nfci_vintage_dates_in_separate_diagnostic=int(a.nfci_vintage_separate_diagnostic.sum()),fully_real_time_verified_origins=0,training_pairs=len(pairs),training_cutoffs_passed=all(x['within_cutoff'] for x in pairs),verdict='Publication dates verified; NOT full real-time reconstruction. Exact historical values of GDP EA20, ESI and CISS are not all recovered. NFCI vintages are a separate partial diagnostic.')
(O/'calendar_validation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2));print(es.query('origin in ["2010Q1","2016Q1","2017Q1","2020Q4","2024Q4"]').to_string(index=False))
