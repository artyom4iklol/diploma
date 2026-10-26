"""Descriptive feasibility calculations; phase coefficients are not causal effects."""
from pathlib import Path
import csv,json,math
import numpy as np

R=Path(__file__).resolve().parent/'results'
rows=list(csv.DictReader(open(R/'pilot_panel.csv')))
key=lambda r:(r['partner'],r['product'],r['indicators'],r['time'])
assert len({key(r)for r in rows})==len(rows)
data={key(r):(float(r['value'])if r['value']!=''else None)for r in rows}
PRODUCTS={'BEV_new':'87038010','PHEV_petrol_new':'87036010','HEV_petrol_new':'87034010'}
months=sorted({r['time']for r in rows});assert len(months)==60
Q='SUPPLEMENTARY_QUANTITY';V='VALUE_IN_EUROS'
core=[r for r in rows if r['product']in PRODUCTS.values()]
assert len(core)==1800 and all(r['value']!=''for r in core)
def annual(partner,code,indicator,year):
 a=[data[(partner,code,indicator,t)]for t in months if t.startswith(str(year))]
 assert len(a)==12 and all(x is not None for x in a)
 return sum(a)
summary=[]
for group,code in PRODUCTS.items():
 for year in [2023,2024,2025]:
  q=annual('CN',code,Q,year);v=annual('CN',code,V,year);totalq=annual('EXT_EU27_2020',code,Q,year)
  summary.append({'category':group,'cn8':code,'year':year,'vehicles':q,'value_eur':v,'customs_unit_value_eur':v/q,'china_share_of_extra_eu_category_pct':100*q/totalq})
with open(R/'china_new_vehicle_summary.csv','w',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
def decompose(y0,y1,indicator):
 totals={y:sum(annual('EXT_EU27_2020',c,indicator,y)for c in PRODUCTS.values())for y in [y0,y1]}
 shares={y:sum(annual('CN',c,indicator,y)for c in PRODUCTS.values())/totals[y]for y in [y0,y1]}
 parts=[]
 for group,c in PRODUCTS.items():
  a={y:annual('EXT_EU27_2020',c,indicator,y)for y in [y0,y1]}
  w={y:a[y]/totals[y]for y in [y0,y1]};s={y:annual('CN',c,indicator,y)/a[y]for y in [y0,y1]}
  within=(w[y0]+w[y1])/2*(s[y1]-s[y0]);mix=(s[y0]+s[y1])/2*(w[y1]-w[y0])
  parts.append({'category':group,'within_category_share_pp':within*100,'extra_eu_import_mix_pp':mix*100})
 error=sum(p['within_category_share_pp']+p['extra_eu_import_mix_pp']for p in parts)-(shares[y1]-shares[y0])*100
 assert abs(error)<1e-10,error
 return {'start_year':y0,'end_year':y1,'indicator':indicator,'china_share_start_pct':100*shares[y0],'china_share_end_pct':100*shares[y1],'change_pp':100*(shares[y1]-shares[y0]),'within_category_share_pp':sum(p['within_category_share_pp']for p in parts),'extra_eu_import_mix_pp':sum(p['extra_eu_import_mix_pp']for p in parts),'components':parts,'identity_error_pp':error,'scope':'Three CN8 groups only: new BEVs and new petrol PHEVs/HEVs; not all passenger cars or retail registrations.'}
decomp=[decompose(a,b,i)for a,b in [(2023,2025),(2024,2025)]for i in [Q,V]]
(R/'share_decomposition.json').write_text(json.dumps(decomp,ensure_ascii=False,indent=2))

# Fixed before estimation: Jan 2021-Dec 2025, linear trend, calendar-month effects;
# June 2024 announcement, July-October provisional phase, November 2024 onward final phase.
# Relative composition is measured against all other extra-EU origins, not untreated firms.
names=['constant','linear_monthly_trend']+['calendar_month_'+str(m)for m in range(2,13)]+['announcement_June_2024','provisional_July_October_2024','definitive_November_2024_December_2025']
X=[]
for t,month in enumerate(months):
 m=int(month[-2:]);X.append([1,t]+[int(m==k)for k in range(2,13)]+[int(month=='2024-06'),int('2024-07'<=month<='2024-10'),int(month>='2024-11')])
X=np.array(X,float);assert np.linalg.matrix_rank(X)==X.shape[1]
models=[]
for group in ['PHEV_petrol_new','HEV_petrol_new']:
 c=PRODUCTS[group];b=PRODUCTS['BEV_new'];Y=[]
 for t in months:
  cn=data[('CN',c,Q,t)];bn=data[('CN',b,Q,t)]
  rest=data[('EXT_EU27_2020',c,Q,t)]-cn;restb=data[('EXT_EU27_2020',b,Q,t)]-bn
  assert min(cn,bn,rest,restb)>0
  Y.append(math.log(cn/bn)-math.log(rest/restb))
 y=np.array(Y);beta=np.linalg.lstsq(X,y,rcond=None)[0];e=y-X@beta;bread=np.linalg.inv(X.T@X);Z=X*e[:,None]
 for lag in [6,12]:
  meat=Z.T@Z
  for l in range(1,lag+1):
   gamma=Z[l:].T@Z[:-l];meat+=(1-l/(lag+1))*(gamma+gamma.T)
  cov=bread@meat@bread*len(y)/(len(y)-X.shape[1]);assert np.linalg.eigvalsh((cov+cov.T)/2).min()>-1e-8
  for name in names[-3:]:
   j=names.index(name);se=math.sqrt(max(0,cov[j,j]));lo=float(beta[j]-1.96*se);hi=float(beta[j]+1.96*se)
   models.append({'category':group,'term':name,'months':len(y),'parameters':X.shape[1],'HAC_lags':lag,'coefficient_log_relative_ratio':float(beta[j]),'se_HAC_small_sample_adjusted':se,'asymptotic_95_interval_log_ratio':[lo,hi],'relative_ratio_multiplier':math.exp(float(beta[j])),'asymptotic_95_interval_multiplier':[math.exp(lo),math.exp(hi)],'interpretation':'Descriptive shift in China hybrid/BEV ratio relative to rest-of-extra-EU hybrid/BEV ratio, conditional on trend and seasonality. Not a causal tariff coefficient; intervals are asymptotic and the post-period is short.'})
(R/'descriptive_phase_models.json').write_text(json.dumps(models,ensure_ascii=False,indent=2))
# Official Eurostat news benchmark is rounded: 2025 electric imports approximately EUR15bn, China 42%.
def sum_allow_missing(partner,codes,indicator,year):
 rr=[data[(partner,c,indicator,t)]for c in codes for t in months if t.startswith(str(year))]
 assert all(v is not None for v in rr);return sum(rr)
allbev=['87038010','87038090']
world=sum_allow_missing('EXT_EU27_2020',allbev,V,2025);china=sum_allow_missing('CN',allbev,V,2025)
benchmark={'official_news_url':'https://ec.europa.eu/eurostat/web/products-eurostat-news/w/ddn-20261013-1','scope':'new and used BEVs, CN87038010+87038090, 2025, import value','extra_eu_value_eur':world,'china_value_eur':china,'china_share_pct':100*china/world,'rounded_eur_billion':round(world/1e9,1),'rounded_china_share_pct':round(100*china/world),'published_benchmarks':{'eur_billion':15.0,'china_share_pct':42},'matches_published_rounding':round(world/1e9,1)==15.0 and round(100*china/world)==42}
assert benchmark['matches_published_rounding']
(R/'published_total_crosscheck.json').write_text(json.dumps(benchmark,ensure_ascii=False,indent=2))
print('Core complete:',len(core),'cells; duplicate keys absent; decomposition identity passed; published rounded totals matched')
print('China new vehicle table:',json.dumps(summary,ensure_ascii=False))
print('Quantity decompositions:',json.dumps([x for x in decomp if x['indicator']==Q],ensure_ascii=False))
print('Phase models:',json.dumps([x for x in models if 'definitive'in x['term']],ensure_ascii=False))
