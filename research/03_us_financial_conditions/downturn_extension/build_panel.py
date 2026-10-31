"""Build harmonised EA21 late-history panel; retain source coverage and missing values."""
from pathlib import Path
import io,zipfile,json,hashlib
import numpy as np,pandas as pd,openpyxl
P=Path(__file__).resolve().parent;RAW=P/'data/raw';OUT=P/'data/processed'
QS=pd.period_range('1970Q1','2025Q4',freq='Q')

def annual_source():
 with zipfile.ZipFile(RAW/'AWMD_Sep2026.zip') as z:
  w=openpyxl.load_workbook(io.BytesIO(z.read('AWMD_Sep2026.xlsx')),read_only=True,data_only=True)
  out={}
  for name in ['AWMD_Updated','AWMD_exIreland']:
   a=list(w[name].values);d=pd.DataFrame(a[1:],columns=a[0]);d=d[d.Period.notna()].copy();d.index=pd.PeriodIndex(d.Period.str.replace('-','',regex=False),freq='Q');out[name]=d
  definitions=[list(r[:8]) for r in w['Definitions'].values if r[0] in ['YER','LTN','STN']]
 return out,definitions

def monthly_fred(name):
 d=pd.read_csv(RAW/f'fred_{name}.csv');values=pd.to_numeric(d.iloc[:,1],errors='coerce');return pd.Series(values.to_numpy(),index=pd.to_datetime(d.iloc[:,0]).dt.to_period('M')).sort_index()

def qmean_monthly(s):
 a=s.groupby(s.index.asfreq('Q')).agg(['mean','count']);return a['mean'].where(a['count'].eq(3)),a['count']

def daily_mean(dates,values):
 s=pd.Series(pd.to_numeric(values,errors='coerce').to_numpy(),index=pd.to_datetime(dates).dt.to_period('Q'));a=s.groupby(level=0).agg(['mean','count']);return a['mean'].where(a['count'].ge(40)),a['count']

def eurostat_series(path):
 d=json.loads(path.read_text());dims=d['id'];sizes=d['size'];time=d['dimension']['time']['category']['index'];pairs=[]
 for label,k in time.items():
  # All dimensions other than time are singleton because they were filtered in the source URL.
  if any(n!=1 for j,n in enumerate(sizes) if dims[j]!='time'):raise ValueError('Unexpected unfiltered Eurostat dimension')
  v=d['value'].get(str(k),np.nan);pairs.append((pd.Period(label,freq='Q'),v))
 return pd.Series(dict(pairs),dtype=float),d

def build(write=True):
 awm,defs=annual_source();a=awm['AWMD_Updated'];b=awm['AWMD_exIreland'];d=pd.DataFrame(index=QS)
 for src,dest in [('YER','gdp'),('STN','eu_short'),('LTN','eu_long')]:d[dest]=pd.to_numeric(a[src],errors='coerce').reindex(QS)
 d['gdp_exIreland']=pd.to_numeric(b.YER,errors='coerce').reindex(QS)
 for c in ['gdp','gdp_exIreland']:d['growth' if c=='gdp' else 'growth_exIreland']=100*np.log(d[c]/d[c].shift(1))
 d['eu_curve']=d.eu_long-d.eu_short
 coverage=[]
 for s,col in [('BAA10YM','credit'),('GS10','us_long'),('TB3MS','us_short')]:
  values=monthly_fred(s);q,n=qmean_monthly(values);d[col]=q.reindex(QS);d[col+'_n']=n.reindex(QS)
  coverage.append({'source':s,'first':str(values.index.min()),'last':str(values.index.max()),'nonmissing':int(values.notna().sum())})
 d['us_curve']=d.us_long-d.us_short
 for s,col in [('VIXCLS','vix'),('NFCI','nfci'),('ANFCI','anfci')]:
  raw=pd.read_csv(RAW/f'fred_{s}.csv');
  if s=='VIXCLS':q,n=daily_mean(raw.iloc[:,0],raw.iloc[:,1])
  else:
   v=pd.Series(pd.to_numeric(raw.iloc[:,1],errors='coerce').to_numpy(),index=pd.to_datetime(raw.iloc[:,0]).dt.to_period('Q'));v=v.groupby(level=0).agg(['mean','count']);q=v['mean'].where(v['count'].ge(10));n=v['count']
  d[col]=q.reindex(QS);d[col+'_n']=n.reindex(QS)
 with zipfile.ZipFile(RAW/'ecfin_main_indicators_202610.zip') as z:
  w=openpyxl.load_workbook(io.BytesIO(z.read('main_indicators_nace2.xlsx')),read_only=True,data_only=True);rows=list(w['MONTHLY'].values);headers=rows[0];idx=headers.index('EA.ESI')
  month={pd.Period(r[0],freq='M'):float(r[idx]) for r in rows[1:] if hasattr(r[0],'year') and isinstance(r[idx],(int,float))}
  s=pd.Series(month);q,n=qmean_monthly(s);d['esi']=q.reindex(QS);d['esi_n']=n.reindex(QS)
  info='\n'.join(' '.join(str(v) for v in r if v is not None) for r in w['INFO'].values);assert 'Bulgaria' in info and 'January 2026' in info
 raw=pd.read_csv(RAW/'ecb_stoxx50.csv');assert raw.KEY.nunique()==1;s=pd.Series(pd.to_numeric(raw.OBS_VALUE,errors='coerce').to_numpy(),index=pd.PeriodIndex(raw.TIME_PERIOD,freq='M'));assert not s.index.duplicated().any();q,n=qmean_monthly(s);d['equity_level']=q.reindex(QS);d['equity']=100*np.log(d.equity_level/d.equity_level.shift(1));d['equity_n']=n.reindex(QS)
 raw=pd.read_csv(RAW/'ecb_ciss_ea.csv');assert raw.KEY.nunique()==1 and 'SS_CIN' in raw.KEY.iloc[0];q,n=daily_mean(raw.TIME_PERIOD,raw.OBS_VALUE);d['ciss']=q.reindex(QS);d['ciss_n']=n.reindex(QS)
 peaks=[('1974Q3','1975Q1'),('1980Q1','1982Q3'),('1992Q1','1993Q3'),('2008Q1','2009Q2'),('2011Q3','2013Q1'),('2019Q4','2020Q2')]
 d['cepr']=0
 for peak,trough in peaks:d.loc[(d.index>pd.Period(peak))&(d.index<=pd.Period(trough)),'cepr']=1
 for base,out in [('growth','gdp_lag'),('eu_curve','eu_curve_lag'),('credit','credit_lag'),('us_curve','us_curve_lag'),('esi','esi_lag'),('equity','equity_lag'),('vix','vix_lag'),('ciss','ciss_lag'),('nfci','nfci_lag'),('anfci','anfci_lag')]:d[out]=d[base].shift(1)
 external,meta=eurostat_series(RAW/'eurostat_gdp_EA21.json');ext=external.reindex(QS);joint=d.gdp.notna()&ext.notna();reldiff=(d.gdp[joint]/ext[joint]-1).abs();reconciliation={'n':int(joint.sum()),'max_relative_level_difference':float(reldiff.max()),'mean_relative_level_difference':float(reldiff.mean()),'eurostat_updated':meta.get('updated'),'reason_if_not_exact':'AWM fixed September 2026 versus Eurostat October 2026; revisions expected, not a silent splice'}
 ext_growth=100*np.log(ext/ext.shift(1));compare=(d.growth.notna()&ext_growth.notna());flip=(np.signbit(d.growth[compare])!=np.signbit(ext_growth[compare]));reconciliation['growth_sign_flips']=list(map(str,flip[flip].index));reconciliation['max_growth_difference_pp']=float((d.growth-ext_growth).abs().max())
 assert len(d)==224 and d.index.is_unique and not d[['gdp','eu_short','eu_long','credit','us_long','us_short']].isna().any().any()
 assert np.isfinite(d.growth.iloc[1:]).all() and d.index.max()==pd.Period('2025Q4')
 audit={'date':'2026-10-31','area':'EA21 fixed reconstructed area; no moving-area GDP splice','rows':len(d),'gdp_definition':defs,'source_coverage':coverage,'reconciliation':reconciliation,'growth_units':'percent q/q log, not annualized','missing_policy':'no zero replacement, interpolation or cross-source GDP splice','features':{c:{'first':str(d[c].first_valid_index()),'last':str(d[c].last_valid_index()),'missing':int(d[c].isna().sum())} for c in d},'counts':{str(start):{'rows':int(len(d.loc[start:'2006Q4'])),'negative_growth':int(d.loc[start:'2006Q4','growth'].lt(0).sum())} for start in ['1970Q2','1985Q1','1990Q1','1995Q1']},'evaluation_counts':{'quarters':76,'negative_growth':int(d.loc['2007Q1':'2025Q4','growth'].lt(0).sum()),'negative_exIreland':int(d.loc['2007Q1':'2025Q4','growth_exIreland'].lt(0).sum())}}
 if write:
  OUT.mkdir(exist_ok=True,parents=True);d.rename_axis('quarter').to_csv(OUT/'quarterly_panel.csv');
  pd.DataFrame({'quarter':d.index.astype(str),'eurostat_gdp_EA21':ext.to_numpy(),'eurostat_growth':ext_growth.to_numpy(),'awm_growth':d.growth.to_numpy()}).to_csv(OUT/'gdp_crosscheck.csv',index=False)
  (P/'checks/data_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 return d,audit

if __name__=='__main__':
 d,a=build();print(json.dumps({'rows':len(d),'evaluation':a['evaluation_counts'],'external_check':a['reconciliation'],'features':a['features']},ensure_ascii=False,indent=2))
