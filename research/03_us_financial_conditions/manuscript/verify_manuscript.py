"""Validate assembly and numerical conclusions using stored forecasts; no fits."""
from pathlib import Path
import re,json,hashlib
import numpy as np
import pandas as pd
H=Path(__file__).resolve().parent;R=H.parent
t=(H/'Diploma_US_Financial_Conditions_Euro_Area.md').read_text();checks={}
def ck(n,v):
 checks[n]=bool(v)
 if not v:raise AssertionError(n)
def sec(a,b):return t.split(f'<a id="{a}"></a>\n\n',1)[1].split(f'<a id="{b}"></a>',1)[0].strip()
anchors=['introduction','chapter-1','chapter-2','chapter-3','conclusion','references','appendices']
ck('sections_complete',all(t.count(f'<a id="{a}"></a>')==1 for a in anchors))
ck('sections_ordered',[t.index(f'<a id="{a}"></a>') for a in anchors]==sorted(t.index(f'<a id="{a}"></a>') for a in anchors))
ck('four_appendices',len(re.findall(r'^## Приложение [АБВГ]\.',t,re.M))==4)
ck('ten_paragraphs',len(re.findall(r'^## [123]\.\d\.',t,re.M))==10)
ck('no_placeholders','<!--' not in t and 'TODO' not in t)
ck('balanced_fences',sum(l.startswith('```') for l in t.splitlines())%2==0)
ck('fourteen_equations',len(re.findall(r'\\tag\{[12]\.\d+\}',t))==14)
ck('one_mermaid',t.count('```mermaid')==1)
bib=sec('references','appendices');entries=re.findall(r'^(\d+)\. (.+)$',bib,re.M)
ck('bibliography_1_62',[int(n) for n,_ in entries]==list(range(1,63)))
cited=set()
for raw in re.findall(r'\[(\d[^\]\n]*)\](?!\()',t.replace(bib,'')):
 if re.match(r'\d+[,.]\d',raw):continue
 for p in raw.split(';'):
  m=re.match(r'\s*(\d+)(?:[–-](\d+))?',p)
  if m:cited.update(range(int(m[1]),int(m[2] or m[1])+1))
ck('all_citations_resolved',cited==set(range(1,63)))
defs=re.findall(r'^\[\^([^\]]+)\]:',t,re.M);uses=re.findall(r'\[\^([^\]]+)\](?!:)',t)
ck('notes_unique',len(defs)==len(set(defs))==19)
ck('notes_resolved',set(defs)==set(uses))
src1=(R/'chapter1/Chapter_1_US_Financial_Conditions_Euro_Area.md').read_text().split('## Список использованных источников к главе 1')[0].strip()
ck('chapter1_length_preserved',len(sec('chapter-1','chapter-2').split())>=.99*len(src1.split()))
for n,next_a,fn in [(2,'chapter-3','chapter2/Chapter_2_Empirical_Analysis.md'),(3,'conclusion','chapter3/Chapter_3_Recommendations.md')]:
 src=(R/fn).read_text().split('## Источники и примечания к главе')[0].strip();new=sec('chapter-'+str(n),next_a)
 old_rows=[l for l in src.splitlines() if l.startswith('|')]; new_rows=iter(l for l in new.splitlines() if l.startswith('|'))
 ck(f'chapter{n}_tables_preserved',all(any(line==old_line for line in new_rows) for old_line in old_rows))
 ck(f'chapter{n}_length_preserved',len(new.split())>=.99*len(src.split()))
old=(R/'chapter2/Appendix_Chapter_2_Additional_Experiments.md').read_text()
app=t.split('## Приложение Б.',1)[1].split('## Приложение В.',1)[0]
ck('appendix_tables_preserved',[l for l in old.splitlines() if l.startswith('|')]==[l for l in app.split('### Б.9.',1)[0].splitlines() if l.startswith('|')])
ck('20_appendix_B_tables',len(re.findall(r'^Таблица Б\.\d+\.',t,re.M))==20)
ck('consistent_object',t.count('Объектом исследования является совокупная экономическая динамика еврозоны в условиях международных финансовых взаимосвязей.')==2)
f=pd.read_csv(R/'revision25/results/forecasts.csv');s=pd.read_csv(R/'revision25/results/scores.csv')
ck('4520_forecasts',len(f)==4520)
loss=(f.actual-f.forecast)*(.1-(f.actual<f.forecast).astype(int))
ck('losses_recomputed',np.allclose(f.loss,loss,atol=1e-10,rtol=1e-10))
ck('violations_recomputed',np.array_equal(f.hit,(f.actual<f.forecast).astype(int)))
agg=f.groupby(['variant','config','h','model'],as_index=False).agg(n=('loss','size'),mean_loss=('loss','mean'),hits=('hit','sum'))
j=agg.merge(s,on=['variant','config','h','model'],suffixes=('_a','_b'))
ck('80_scores_recomputed',len(j)==80 and np.allclose(j.mean_loss_a,j.mean_loss_b,atol=1e-10) and np.array_equal(j.hits_a,j.hits_b))
def val(h,m,c='Q_raw',v='expanding'):
 return s[(s.h==h)&(s.model==m)&(s.config==c)&(s.variant==v)].iloc[0]
raw=f[(f.variant=='expanding')&(f.config=='Q_raw')]
ck('58_55_dates',all(raw[raw.h==h].groupby('model').size().eq(n).all() for h,n in [(1,58),(4,55)]))
g=[100*(1-val(h,m).mean_loss/val(h,'AR_ESI').mean_loss) for h in [1,4] for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']]
ck('raw_gains',[round(x,1) for x in g]==[9.2,9.1,23.2,42.5])
gg=[100*(1-val(h,'AR_ESI','Q_clip_g').mean_loss/val(h,'AR_ESI').mean_loss) for h in [1,4]]
ck('guard_gains',[round(x,1) for x in gg]==[26.3,51.5])
ck('hist_beats_us',all(val(h,m,c,v).mean_loss>val(h,'HIST',c,v).mean_loss for h in [1,4] for m in ['AR_ESI_NFCI','AR_ESI_ANFCI'] for c in ['Q_raw','M2_raw','Q_clip_g','M2_clip_g'] for v in ['expanding','rolling52']))
ck('guarded_base_beats_us',all(val(h,m,c,v).mean_loss>val(h,'AR_ESI',c,v).mean_loss for h in [1,4] for m in ['AR_ESI_NFCI','AR_ESI_ANFCI'] for c in ['Q_clip_g','M2_clip_g'] for v in ['expanding','rolling52']))
omit=raw[raw.origin!='2020Q4'].groupby(['h','model']).loss.mean()
ck('single_date_removes_gain',all(omit[h,m]>omit[h,'AR_ESI'] for h in [1,4] for m in ['AR_ESI_NFCI','AR_ESI_ANFCI']))
recent=raw[raw.episode=='2022_2025'];ck('recent_no_violations',recent.hit.sum()==0 and len(recent)==145)
inf=pd.read_csv(R/'revision25/results/rolling52_inference.csv')
ck('h1_no_holm_rejections',(inf[inf.h==1].p_holm20>=.05).all())
ck('h4_L4_no_holm_rejections',(inf[(inf.h==4)&(inf.L==4)].p_holm20>=.05).all())
sig=inf[(inf.h==4)&(inf.L==8)&(inf.p_holm20<.05)]
ck('h4_L8_favours_hist',len(sig)==2 and (sig.benchmark=='HIST').all() and (sig.difference>0).all())

# Independent consistency checks of the new diagnostics and their exact tables.
dc=pd.read_csv(R/'revision29/results/loss_decomposition.csv')
dc0=dc.merge(agg,on=['variant','config','h','model'],suffixes=('','_old'))
ck('80_decompositions',len(dc0)==80 and np.allclose(dc0.loss,dc0.mean_loss) and np.allclose(dc0.loss_below+dc0.loss_above,dc0.loss))
common=pd.read_csv(R/'revision29/results/common_origins_scores.csv')
common0=f[f.origin.isin(sorted(set(f[f.h==1].origin)&set(f[f.h==4].origin)))].groupby(['variant','config','h','model']).loss.mean()
ck('80_common_origin_scores',len(common)==80 and common.n.eq(55).all() and np.allclose(common.set_index(['variant','config','h','model']).mean_loss.sort_index(),common0.sort_index()))
blocks=pd.read_csv(R/'revision29/results/four_origin_block_omissions.csv')
bs=pd.read_csv(R/'revision29/results/four_origin_block_summary.csv')
ck('4280_block_comparisons',len(blocks)==4280 and len(bs)==80)
b0=blocks.query("variant=='expanding' and config=='Q_raw'")
ck('hist_wins_all_blocks',(b0[b0.benchmark=='HIST'].difference>0).all())
base=b0[b0.benchmark=='AR_ESI']
ck('block_reversals_contain_2020Q4',np.array_equal(base.difference.gt(0),base.contains_2020Q4))
ph=pd.read_csv(R/'revision29/results/h4_nonoverlap_phases.csv')
pv=ph.pivot(index='phase',columns='model',values='mean_loss')
ck('20_phase_rows',len(ph)==20 and sorted(ph.groupby('phase').n.first())==[13,14,14,14])
ck('phase_hist_wins',all((pv.HIST<pv[m]).all() for m in ['AR_ESI_ANFCI','AR_ESI_NFCI']))
ck('phase_anfci_beats_nfci',(pv.AR_ESI_ANFCI<pv.AR_ESI_NFCI).all())
ck('phase_base_not_uniform',(pv.AR_ESI_ANFCI<pv.AR_ESI).sum()==2 and (pv.AR_ESI_NFCI<pv.AR_ESI).sum()==1)
annex=(R/'revision29/Additional_Appendix.md').read_text().strip()
ck('new_appendix_exact',annex in t)
oldtext=(H/'history/revision28/Diploma_US_Financial_Conditions_Euro_Area.md').read_text()
oldwords=len(oldtext.split());newwords=len(t.split())
ck('overall_length_preserved',newwords>=oldwords)
ck('43_numbered_tables',len(re.findall(r'^Таблица (?:[123]\.\d+|[АБВГ]\.\d+)\.',t,re.M))==43)
ck('canonical_sections',all((H/'sections'/f'{a}.md').read_text().strip() in t for a in anchors))
ck('consistent_operational_conclusion','наличие выборочного улучшения исходной базы при отсутствии подтверждённой устойчивой дополнительности' in t)

out={'revision':30,'date':'2026-10-22','passed':all(checks.values()),'checks':checks,'references':62,'notes':19,'raw_gains_pct':g,'guard_improvements_pct':gg,'new_model_fits':904,'sha256':hashlib.sha256((H/'Diploma_US_Financial_Conditions_Euro_Area.md').read_bytes()).hexdigest()}
(H/'VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':out['passed'],'checks':len(checks),'references':62,'notes':19}))
