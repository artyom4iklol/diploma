"""Offline reconstruction of a conservative, historically implementable information set.

Retain previously public observations when RTD temporarily deletes a series.
Never splice GDP levels across vintages: transform GDP within each snapshot.
Public availability is the bulletin release, not the RTD freeze timestamp.
"""
from pathlib import Path
import json,re,hashlib
import numpy as np,pandas as pd

P=Path(__file__).resolve().parent
ROOT=P.parent
RTD=ROOT/'rtd_sources'
O=P/'results';O.mkdir(exist_ok=True)
QS=pd.period_range('1995Q1','2025Q4',freq='Q')
MS=pd.period_range('1995-01','2025-12',freq='M')

def bulletin_calendar():
 s=(P/'sources/bulletin_releases.html').read_text();rows=[]
 for date,part in re.findall(r'<dt isoDate="([^"]+)">(.*?)(?=<dt |$)',s,re.S):
  m=re.search(r'href="([^"]*eb(\d{4})(\d{2})(?:~[\da-f]+)?\.en\.(?:html|pdf))"',part)
  if m:rows.append(dict(publication_date=date,year=int(m[2]),issue=int(m[3]),url='https://www.ecb.europa.eu'+m[1]))
 b=pd.DataFrame(rows).sort_values('publication_date');b.to_csv(P/'sources/bulletin_calendar.csv',index=False)
 assert all(b[b.year.eq(y)].issue.nunique()==8 for y in range(2015,2026))
 return b

def load_events(kind):
 a=pd.concat([pd.read_csv(x) for x in sorted((RTD/'history_chunks').glob(kind+'_*.csv'))],ignore_index=True)
 a['delete']=a.ACTION.eq('Delete')
 a['event_time']=pd.to_datetime(a.VALID_FROM.where(~a.delete,a.VALID_TO),utc=True)
 a['value']=pd.to_numeric(a.OBS_VALUE,errors='coerce').where(~a.delete,np.nan)
 a['period']=pd.PeriodIndex(a.TIME_PERIOD.str.replace('-Q','Q'),freq='Q' if kind=='gdp' else 'M')
 a['rank']=np.where(a.delete,0,1)
 return a.sort_values(['event_time','rank','period'])

def transformed_gdp(state):
 y=pd.Series(state,dtype=float).reindex(QS)
 return {'g1':400*np.log(y/y.shift(1)),'g4':100*np.log(y/y.shift(4))}

def parse_patches(cal):
 months={x:i+1 for i,x in enumerate(['Jan.','Feb.','Mar.','Apr.','May','June','July','Aug.','Sep.','Oct.','Nov.','Dec.'])}
 records=[];patches=[]
 for issue,freeze in [('202204','2022-06-08'),('202302','2023-03-15'),('202304','2023-06-14'),('202506','2025-09-10')]:
  f=P/'sources'/('eb'+issue+'.txt');s=f.read_text();a=s.rfind('2.6 Opinion surveys');b=s.find('\n2.7 Summary',a);assert a>=0 and b>a
  text=s[a:b];page=s[:a].count('\f')+1;year=None;v={}
  for line in text.splitlines():
   m=re.match(r'^\s*(?:(\d{4})\s+)?(Jan\.|Feb\.|Mar\.|Apr\.|May|June|July|Aug\.|Sep\.|Oct\.|Nov\.|Dec\.)\s+(-?\d+\.\d+)\s',line)
   if not m:continue
   if m[1]:year=int(m[1])
   assert year is not None,(issue,line)
   period=pd.Period(f'{year}-{months[m[2]]:02d}',freq='M');v[period]=float(m[3])
   records.append(dict(issue=issue,kind='esi',period=str(period),value=float(m[3]),source_page=page,printed_table='2.6',source_file=f'eb{issue}.pdf',source_line=line.strip()))
  assert len(v)>=5,(issue,v)
  info=cal[(cal.year.eq(int(issue[:4])))&(cal.issue.eq(int(issue[4:])))].iloc[0]
  patch=dict(freeze=pd.Timestamp(freeze),public=pd.Timestamp(info.publication_date),esi=v,gdp={},source=f'eb{issue}.pdf',url=info.url)
  if issue=='202204':
   a=s.rfind('2.1 GDP and expenditure components');b=s.find('\n2.2 ',a);g=s[a:b]
   c=g[g.index('quarter-on-quarter percentage changes'):g.index('annual percentage changes')]
   d=g[g.index('annual percentage changes'):g.index('contributions to quarter-on-quarter')]
   qoq=float(re.search(r'^2022 Q1\s+(-?[\d.]+)',c,re.M)[1]);yoy=float(re.search(r'^2022 Q1\s+(-?[\d.]+)',d,re.M)[1])
   assert qoq==0.6 and yoy==5.4
   patch['gdp']={'g1':{pd.Period('2022Q1'):400*np.log1p(qoq/100)},'g4':{pd.Period('2022Q1'):100*np.log1p(yoy/100)}}
   for kind,value,printed in [('g1',patch['gdp']['g1'][pd.Period('2022Q1')],qoq),('g4',patch['gdp']['g4'][pd.Period('2022Q1')],yoy)]:records.append(dict(issue=issue,kind=kind,period='2022Q1',value=value,printed_value=printed,source_page=s[:a].count('\f')+1,printed_table='2.1',source_file=f'eb{issue}.pdf',source_line='q/q 0.6%; y/y 5.4%; rounded published growth, not reconstructed GDP levels'))
  patches.append(patch)
 pd.DataFrame(records).to_csv(O/'bulletin_repairs.csv',index=False)
 return patches

def build_snapshots(kind,cal,patches,events=None):
 out=[]
 old=pd.read_csv(RTD/'extracted'/f'{kind}_legacy_vintages.csv')
 for vm,g in old.groupby('vintage_month',sort=True):
  vm=str(vm);qdate=pd.Period(vm[:4]+'-'+vm[4:],freq='M').end_time.normalize()
  if qdate.year<2010:continue
  freq='Q' if kind=='gdp' else 'M';state=pd.Series(g.value.to_numpy(),index=pd.PeriodIndex(g.period,freq=freq))
  data=transformed_gdp(state) if kind=='gdp' else {'esi':state.reindex(MS)}
  out.append(dict(freeze=qdate,public=qdate,source='legacy_'+vm,public_evidence='official issue month; conservative month-end upper bound',**data))
 a=load_events(kind) if events is None else events
 raw={};known={};last_updates={}
 # Replay all pre-2015 events too, but prefer standalone legacy snapshots for that period.
 timelines={}
 for et,g in a.groupby('event_time',sort=True):
  freeze=et.tz_convert('Europe/Brussels').normalize().tz_localize(None)
  for r in g.itertuples():
   if r.delete:raw.pop(r.period,None)
   else:raw[r.period]=float(r.value)
  if freeze.year<2015:continue
  future=cal[pd.to_datetime(cal.publication_date).ge(freeze)]
  assert len(future),('no published bulletin',freeze)
  pub=pd.Timestamp(future.iloc[0].publication_date)
  assert 0<=(pub-freeze).days<=35,(freeze,pub)
  timelines[freeze]=dict(freeze=freeze,public=pub,raw=raw.copy(),source='RTD_API_'+str(freeze.date()),public_evidence=future.iloc[0].url)
 for p in patches:
  # Some whole vintages (June 2022) are absent from these RTD series.
  timelines.setdefault(p['freeze'],dict(freeze=p['freeze'],public=p['public'],raw=None,source=p['source'],public_evidence=p['url']))
 patch_by_date={p['freeze']:p for p in patches}
 for freeze,node in sorted(timelines.items()):
  if node['raw'] is not None:
   if kind=='gdp':
    updates=transformed_gdp(node['raw'])
    for col,values in updates.items():
     known.setdefault(col,{})
     for period,val in values.dropna().items():known[col][period]=float(val)
   else:
    known.setdefault('esi',{})
    for period,val in node['raw'].items():known['esi'][period]=float(val)
  patch=patch_by_date.get(freeze)
  if patch:
   updates=patch['gdp'] if kind=='gdp' else {'esi':patch['esi']}
   for col,values in updates.items():known.setdefault(col,{}).update(values)
   node['source']+=' + published_table_repair'
  vals={k:pd.Series(v,dtype=float).reindex(QS if kind=='gdp' else MS) for k,v in known.items()}
  out.append({k:v for k,v in node.items() if k!='raw'}|vals)
 return sorted(out,key=lambda x:x['freeze'])

def choose(snapshots,origin,forecast_date):
 cutoff=origin.end_time.normalize()
 eligible=[x for x in snapshots if x['freeze']<=cutoff and x['public']<=forecast_date]
 assert eligible,(origin,forecast_date)
 return eligible[-1]

def feature_frame(origin,g,e,n):
 d=pd.DataFrame(index=QS)
 d['gx']=g['g1'].shift(1)
 d['esi']=e['esi'][e['esi'].index.month%3!=0].groupby(e['esi'][e['esi'].index.month%3!=0].index.asfreq('Q')).mean()
 d['esi_count']=e['esi'].notna().astype(int)[e['esi'].index.month%3!=0].groupby(e['esi'][e['esi'].index.month%3!=0].index.asfreq('Q')).sum()
 d.loc[d.esi_count.ne(2),'esi']=np.nan
 for q in QS[QS<=origin]:
  xx=n[(n.index>=q.start_time)&(n.index+pd.Timedelta(days=7)<=q.end_time)]
  d.at[q,'nfci']=xx.mean()
 return d

def load_nfci(t):
 f=ROOT/'revision16/sources/nfci_vintages'/('nfci_'+str(t.end_time.date())+'.csv')
 a=pd.read_csv(f);assert a.columns[1]=='NFCI_'+str(t.end_time.date()).replace('-','')
 n=pd.Series(pd.to_numeric(a.iloc[:,1],errors='coerce').to_numpy(),index=pd.to_datetime(a.iloc[:,0])).dropna().sort_index()
 assert n.index.max()<=t.end_time
 return n

def make_data():
 cal=bulletin_calendar();patches=parse_patches(cal);gdp=build_snapshots('gdp',cal,patches);esi=build_snapshots('esi',cal,patches)
 rows=[];allframes=[];targets=[];frames={};forecast_ends=pd.period_range('2011Q2','2025Q4',freq='Q')
 latest_nfci_file=ROOT/'robustness/model/raw/fred_nfci.csv';a=pd.read_csv(latest_nfci_file)
 nfci_latest=pd.Series(pd.to_numeric(a.NFCI,errors='coerce').to_numpy(),index=pd.to_datetime(a.observation_date)).dropna()
 latest_g=gdp[-1]
 for t in forecast_ends:
  fdate=t.end_time.normalize()+pd.Timedelta(days=15)
  g=choose(gdp,t,fdate);e=choose(esi,t,fdate);n=load_nfci(t)
  v=feature_frame(t,g,e,n);v['quarter']=v.index.astype(str)
  # Same GDP/ESI vintages; replace only NFCI with the already collected revised series.
  nv=feature_frame(t,g,e,nfci_latest).nfci
  v['nfci_revised']=nv
  for h in [1,4]:v[f'y{h}']=g[f'g{h}'].shift(-h)
  frames[str(t)]=v.copy()
  z=v.copy();z.insert(0,'origin',str(t));allframes.append(z.reset_index(drop=True))
  rows.append(dict(origin=str(t),forecast_date=str(fdate.date()),macro_freeze_cutoff=str(t.end_time.date()),gdp_freeze=str(g['freeze'].date()),gdp_public_available=str(g['public'].date()),gdp_evidence=g['public_evidence'],esi_freeze=str(e['freeze'].date()),esi_public_available=str(e['public'].date()),esi_evidence=e['public_evidence'],nfci_vintage=str(t.end_time.date()),last_nfci_observation_used=str(n[(n.index>=t.start_time)&(n.index+pd.Timedelta(days=7)<=t.end_time)].index.max().date()),gx=v.at[t,'gx'],esi=v.at[t,'esi'],nfci=v.at[t,'nfci'],all_predictors_present=bool(v.loc[t,['gx','esi','nfci']].notna().all()),gdp_source=g['source'],esi_source=e['source']))
  for h in [1,4]:
   if t+h>pd.Period('2025Q4'):continue
   targetq=t+h;deadline=(targetq+2).end_time.normalize()
   valid=[x for x in gdp if x['public']<=deadline and x['freeze']>targetq.end_time.normalize() and pd.notna(x[f'g{h}'].get(targetq,np.nan))]
   assert valid,(t,h,deadline)
   chosen=valid[-1]
   targets.append(dict(origin=str(t),h=h,target_start=str(t+1),target_end=str(targetq),maturity_deadline=str(deadline.date()),matured_snapshot=str(chosen['freeze'].date()),matured_public_date=str(chosen['public'].date()),actual=float(chosen[f'g{h}'].at[targetq]),actual_latest=float(latest_g[f'g{h}'].at[targetq]),latest_snapshot=str(latest_g['freeze'].date()),target_definition='within-vintage log growth, moving policy concept, six-month maturity bound'))
 calendar=pd.DataFrame(rows);assert len(calendar)==59 and calendar.all_predictors_present.all(),calendar[~calendar.all_predictors_present]
 calendar.to_csv(O/'forecast_calendar_59.csv',index=False);pd.concat(allframes,ignore_index=True).to_csv(O/'vintaged_model_frames.csv',index=False);pd.DataFrame(targets).to_csv(O/'evaluation_targets.csv',index=False)
 # Compare API replays with independent pre-2015 archive snapshots after transformation.
 cross=[]
 for kind in ['gdp','esi']:
  a=load_events(kind);state={}
  for et,z in a.groupby('event_time',sort=True):
   dt=et.tz_convert('Europe/Brussels');
   for r in z.itertuples():
    if r.delete:state.pop(r.period,None)
    else:state[r.period]=float(r.value)
   if dt.year not in [2011,2012,2013,2014] or dt.month not in [3,6,9,12]:continue
   old=[x for x in (gdp if kind=='gdp' else esi) if x['source']=='legacy_'+dt.strftime('%Y%m')]
   if not old:continue
   if kind=='gdp':u=transformed_gdp(state)['g1'];w=old[0]['g1']
   else:u=pd.Series(state).reindex(MS);w=old[0]['esi']
   paired=pd.concat([u,w],axis=1).dropna();error=float((paired.iloc[:,0]-paired.iloc[:,1]).abs().max())
   cross.append(dict(kind=kind,freeze=str(dt.date()),paired=len(paired),max_abs_difference=error))
 pd.DataFrame(cross).to_csv(O/'api_legacy_crosscheck.csv',index=False)
 # Validate non-anticipation at reconstruction level, not merely forecast row slicing.
 mutation=[]
 for tstr in ['2018Q4','2020Q1','2023Q1']:
  t=pd.Period(tstr,freq='Q');fdate=t.end_time.normalize()+pd.Timedelta(days=15)
  for kind,snapshots in [('gdp',gdp),('esi',esi)]:
   a=load_events(kind);future=a.event_time.dt.tz_convert('Europe/Brussels').dt.tz_localize(None)>fdate
   a.loc[future&~a.delete,'value']*=1.73
   changed=build_snapshots(kind,cal,patches,a);before=choose(snapshots,t,fdate);after=choose(changed,t,fdate)
   keys=['g1','g4'] if kind=='gdp' else ['esi']
   err=max(float((before[k]-after[k]).dropna().abs().max()) for k in keys)
   assert err<1e-12
   mutation.append(dict(origin=tstr,series=kind,future_event_rows_mutated=int(future.sum()),max_input_difference=err))
 validation=dict(origins=59,complete_origin_predictors=int(calendar.all_predictors_present.sum()),evaluated_pairs=len(targets),GDP_legacy_vintage_crosschecks=sum(x['kind']=='gdp' for x in cross),ESI_legacy_vintage_crosschecks=sum(x['kind']=='esi' for x in cross),API_legacy_max_difference=max(x['max_abs_difference'] for x in cross),public_dates_pass=bool((pd.to_datetime(calendar.gdp_public_available)<=pd.to_datetime(calendar.forecast_date)).all() and (pd.to_datetime(calendar.esi_public_available)<=pd.to_datetime(calendar.forecast_date)).all()),future_mutation=mutation,repairs='published rounded values; retained prior public ESI history during API deletion; no imputed GDP levels',geography='historical moving policy concept; retained older ESI definitions during archive gap',important_limit='Conservative implementable archived-information experiment, not exact reconstruction of all market-available information or every internal vintage')
 (O/'data_validation.json').write_text(json.dumps(validation,indent=2));print(json.dumps(validation,indent=2))
 return frames,pd.DataFrame(targets)

if __name__=='__main__':make_data()
