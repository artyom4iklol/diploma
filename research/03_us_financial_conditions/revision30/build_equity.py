"""Publication-constrained equity snapshots. Offline after fetch_sources.py."""
from pathlib import Path
import csv,io,re,zipfile,json,hashlib,subprocess
from datetime import datetime
import pandas as pd,numpy as np
from pypdf import PdfReader
P=Path(__file__).resolve().parent;R=P.parent;O=P/'results';S=P/'sources'
MS=pd.period_range('1994-01','2025-12',freq='M');QS=pd.period_range('1994Q1','2025Q4',freq='Q')
def legacy():
 out=[];coverage=[]
 with zipfile.ZipFile(R/'rtd_sources/rtd_monthly_pre2015.zip') as z:
  for name in sorted(z.namelist()):
   if not name.endswith('.csv'):continue
   rows=list(csv.reader(io.StringIO(z.read(name).decode('utf-8-sig'))));ids=[i for i,k in enumerate(rows[1]) if '_STOXX50E.HST' in k];assert len(ids)==1,(name,ids)
   j=ids[0];vm=re.search(r'_(\d{6})',name)[1];state={}
   for row in rows[9:]:
    if len(row)<=j:continue
    try:v=float(row[j].strip().replace('D','E'))
    except ValueError:continue
    dt=None
    for fmt in ['%b-%Y','%b-%y']:
     try:dt=datetime.strptime(row[0].strip(),fmt);break
     except ValueError:pass
    if dt is not None and dt.year>=1994:state[pd.Period(dt,freq='M')]=v
   dt=pd.Period(vm[:4]+'-'+vm[4:],freq='M').end_time.normalize();assert state and all(v>0 for v in state.values())
   coverage.append(dict(vintage_file=name,source_key=rows[1][j],months=len(state),first=str(min(state)),last=str(max(state))))
   if dt.year>=2010:out.append(dict(freeze=dt,public=dt,source=name,evidence='Official monthly vintage; month-end upper bound',values=state,raw_periods=set(state),updates={m:dt for m in state}))
 pd.DataFrame(coverage).to_csv(O/'equity_legacy_coverage.csv',index=False);return out

def events():
 a=pd.read_csv(S/'equity_history_all.csv');assert a.KEY.eq('RTD.M.S0.N.C_DJE50.X').all()
 assert set(range(1994,2026))==set(pd.to_datetime(a.TIME_PERIOD).dt.year)
 a['delete']=a.ACTION.eq('Delete');a['et']=pd.to_datetime(a.VALID_FROM.where(~a.delete,a.VALID_TO),utc=True);assert a.et.notna().all()
 a['period']=pd.PeriodIndex(a.TIME_PERIOD,freq='M');a['rank']=np.where(a.delete,0,1);a['value']=pd.to_numeric(a.OBS_VALUE,errors='coerce');return a.sort_values(['et','rank','period'])

def patches(cal):
 specs=[('202004','2020-06-03',['2020-04']),('202102','2021-03-10',['2021-01']),('202204','2022-06-08',['2022-04','2022-05'])]
 month_names=['Jan.','Feb.','Mar.','Apr.','May','June','July','Aug.','Sep.','Oct.','Nov.','Dec.'];monthmap={s:i+1 for i,s in enumerate(month_names)};out=[];evidence=[]
 for issue,freeze,need in specs:
  path=(R/'revision18/sources' if issue=='202204' else S)/f'eb{issue}.pdf'
  full=subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode('utf-8');table='4.3' if issue=='202204' else '2.3';needle=table+' Stock market indices';hits=[(i,s) for i,s in enumerate(full.split('\f')) if needle in s];assert hits
  i,s=hits[-1];(S/f'eb{issue}_equity.txt').write_text(s)
  sub=s[s.index(needle):];year=None;values={}
  for line in sub.splitlines():
   m=re.match(r'^\s*(?:(\d{4})\s+)?(Jan\.|Feb\.|Mar\.|Apr\.|May|June|July|Aug\.|Sep\.|Oct\.|Nov\.|Dec\.)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)',line)
   if not m:continue
   if m[1]:year=int(m[1])
   assert year is not None
   period=f'{year}-{monthmap[m[2]]:02d}'
   if period in need:
    val=float(m[4].replace(',',''));values[pd.Period(period,freq='M')]=val;evidence.append(dict(issue=issue,month=period,value=val,pdf_page=i+1,table=table+', column 2',printed_line=line.strip(),source_file=str(path.relative_to(R)),rounding='0.1 index points'))
  assert set(map(str,values))==set(need),(issue,values)
  c=cal[(cal.year==int(issue[:4]))&(cal.issue==int(issue[4:]))].iloc[0]
  out.append(dict(freeze=pd.Timestamp(freeze),public=c.public,values=values,source=f'eb{issue}.pdf table'+table,evidence=c.url))
  subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-r','110','-singlefile','-png',str(path),str(P/'logs'/f'eb{issue}_equity')],check=True,capture_output=True)
 pd.DataFrame(evidence).to_csv(O/'equity_bulletin_repairs.csv',index=False);return out

def snapshots(a,old,patch,cal,write_cross=True):
 out=old.copy();raw={};known=old[-1]['values'].copy();updates=old[-1]['updates'].copy();cross=[];nodes={}
 for et,g in a.groupby('et',sort=True):
  dt=et.tz_convert('Europe/Brussels').normalize().tz_localize(None)
  for row in g.itertuples():
   if row.delete:raw.pop(row.period,None)
   elif np.isfinite(row.value):raw[row.period]=float(row.value)
  if dt.year<2015:
   match=[s for s in old if s['freeze']==dt.to_period('M').end_time.normalize()]
   if match:
    both=set(raw)&set(match[0]['values']);d=[abs(raw[m]-match[0]['values'][m]) for m in both];cross.append(dict(freeze=str(dt.date()),legacy=match[0]['source'],paired=len(d),max_abs_difference=max(d) if d else None))
   continue
  if dt.year>2025:break
  cand=cal[cal.public.ge(dt)];assert len(cand);pub=cand.iloc[0].public;assert 0<=(pub-dt).days<=35
  nodes[dt]=dict(freeze=dt,public=pub,source='RTD_API_'+str(dt.date()),evidence=cand.iloc[0].url,raw=raw.copy(),changes={row.period:float(row.value) for row in g.itertuples() if not row.delete and np.isfinite(row.value)})
 for p in patch:
  nodes.setdefault(p['freeze'],dict(freeze=p['freeze'],public=p['public'],source=p['source'],evidence=p['evidence'],raw=None,changes={}))
  nodes[p['freeze']]['changes'].update(p['values']);nodes[p['freeze']]['source']+=' + published equity repair'
 active=set(old[-1]['values'])
 for dt,node in sorted(nodes.items()):
  if node['raw'] is not None:active=set(node['raw'])
  for m,v in node['changes'].items():known[m]=v;updates[m]=node['public']
  out.append({k:v for k,v in node.items() if k not in ['raw','changes']}|dict(values=known.copy(),raw_periods=active.copy(),updates=updates.copy()))
 if write_cross:pd.DataFrame(cross).to_csv(O/'equity_api_legacy_crosscheck.csv',index=False)
 return sorted(out,key=lambda s:s['freeze'])

def choose(sn,t,fd):
 z=[s for s in sn if s['freeze']<=t.end_time.normalize() and s['public']<=fd];assert z;return z[-1]

def eq(s):
 levels=pd.Series(s['values'],dtype=float).reindex(MS);z=levels[levels.index.month%3!=0];a=z.groupby(z.index.asfreq('Q')).mean().reindex(QS);n=z.notna().groupby(z.index.asfreq('Q')).sum().reindex(QS);a[n.ne(2)]=np.nan;return 100*np.log(a/a.shift(1))

def run():
 lock=json.loads((P/'protocol_lock.json').read_text());assert hashlib.sha256((P/'PROTOCOL.md').read_bytes()).hexdigest()==lock['sha256']
 cal=pd.read_csv(R/'revision18/sources/bulletin_calendar.csv');cal['public']=pd.to_datetime(cal.publication_date);old=legacy();a=events();patch=patches(cal);sn=snapshots(a,old,patch,cal);c0=pd.read_csv(R/'revision18/results/forecast_calendar_59.csv');frames=[];calendar=[];obs=[]
 for r in c0.itertuples():
  t=pd.Period(r.origin,freq='Q');fd=pd.Timestamp(r.forecast_date);s=choose(sn,t,fd);vals=eq(s);need=[q.asfreq('M','start')+i for q in [t-1,t] for i in [0,1]]
  calendar.append(dict(origin=str(t),forecast_date=str(fd.date()),equity_freeze=str(s['freeze'].date()),equity_public=str(s['public'].date()),source=s['source'],evidence=s['evidence'],eq=vals.loc[t],available=bool(pd.notna(vals.loc[t])),missing_months=';'.join(str(m) for m in need if m not in s['values']),retained_current_months=';'.join(str(m) for m in need if m in s['values'] and m not in s['raw_periods']),required_months=';'.join(map(str,need))))
  frames.extend(dict(origin=str(t),quarter=str(q),eq=v) for q,v in vals.items())
  for m,v in s['values'].items():
   assert s['updates'][m]<=fd
   obs.append(dict(origin=str(t),month=str(m),value=v,public_update=str(s['updates'][m].date()),retained_after_API_delete=bool(m not in s['raw_periods']),used_for_current_eq=bool(m in need)))
 c=pd.DataFrame(calendar);c.to_csv(O/'equity_calendar.csv',index=False);pd.DataFrame(frames).to_csv(O/'equity_frames.csv',index=False);pd.DataFrame(obs).to_csv(O/'equity_monthly_inputs.csv',index=False)
 tests=[]
 for ts in ['2018Q4','2020Q1','2023Q1']:
  t=pd.Period(ts,freq='Q');fd=t.end_time.normalize()+pd.Timedelta(days=15);a2=a.copy();future=a2.et>pd.Timestamp(fd,tz='Europe/Brussels').tz_convert('UTC');a2.loc[future&~a2.delete,'value']*=1.73
  x=eq(choose(sn,t,fd));y=eq(choose(snapshots(a2,old,patch,cal,False),t,fd));d=float((x-y).abs().max());assert d==0;tests.append(dict(origin=ts,future_rows_mutated=int(future.sum()),max_feature_change=d))
 targets=pd.read_csv(R/'revision18/results/evaluation_targets.csv');avail=targets.merge(c[['origin','available']],on='origin')
 result=dict(origins=len(c),complete_origins=int(c.available.sum()),missing_origins=c.loc[~c.available,['origin','missing_months']].to_dict('records'),evaluation_counts=avail[avail.available].groupby('h').size().to_dict(),all_public_dates_before_forecast=bool((pd.to_datetime(c.equity_public)<=pd.to_datetime(c.forecast_date)).all()),future_mutations=tests,current_history_used=False,repair_months=4,protocol_sha256=lock['sha256'])
 (O/'equity_data_validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':run()
