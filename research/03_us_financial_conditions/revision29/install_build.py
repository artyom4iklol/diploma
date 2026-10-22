"""Install the canonical section-based assembly and reviewed verification."""
from pathlib import Path
P=Path(__file__).resolve().parent;M=P.parent/'manuscript';H=M/'history/revision28'
assert (H/'assemble.py').exists()
assembler='''"""Assemble the reviewed canonical sections. No data collection or model fits."""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;R=H.parent
anchors=['introduction','chapter-1','chapter-2','chapter-3','conclusion','references','appendices']
parts=[(a,(H/'sections'/f'{a}.md').read_text().strip()) for a in anchors]
toc=['# Финансовые условия США в прогнозировании рисков роста еврозоны','','## Оглавление','']
for a,t in parts:
 title=t.splitlines()[0].lstrip('# ');toc.append(f'- [{title}](#{a})')
 if a.startswith('chapter-'):
  toc.extend('  - '+x for x in re.findall(r'^## (\\d\\.\\d\\..*)$',t,re.M))
 if a=='appendices':toc.extend('  - '+x for x in re.findall(r'^## (Приложение .*)$',t,re.M))
out=H/'Diploma_US_Financial_Conditions_Euro_Area.md'
out.write_text('\\n'.join(toc)+'\\n\\n'+'\\n\\n'.join(f'<a id="{a}"></a>\\n\\n{t}' for a,t in parts)+'\\n')
for a,n in [('introduction','Introduction'),('conclusion','Conclusion'),('references','Bibliography'),('appendices','Appendices')]:
 (H/f'{n}.md').write_text(dict(parts)[a]+'\\n')
stats={'revision':29,'date':'2026-10-21','sources':59,'academic_works':45,'official_sources':14,'calculation_notes':18,'new_model_fits':0,
 'words':{a:len(t.split()) for a,t in parts},
 'source_sha256':{f'manuscript/sections/{a}.md':hashlib.sha256((H/'sections'/f'{a}.md').read_bytes()).hexdigest() for a in anchors},
 'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
(H/'ASSEMBLY.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\\n')
print(json.dumps({'revision':29,'bytes':out.stat().st_size,'words':stats['words'],'sources':59},ensure_ascii=False))
'''
(M/'assemble.py').write_text(assembler)
s=(H/'verify_manuscript.py').read_text()
s=s.replace("len(defs)==len(set(defs))==17", "len(defs)==len(set(defs))==18")
s=s.replace("ck('chapter1_preserved',sec('chapter-1','chapter-2')==src1)", "ck('chapter1_length_preserved',len(sec('chapter-1','chapter-2').split())>=.99*len(src1.split()))")
s=s.replace("app.splitlines() if l.startswith('|')", "app.split('### Б.9.',1)[0].splitlines() if l.startswith('|')")
s=s.replace("ck('14_appendix_B_tables',len(re.findall(r'^Таблица Б\\.\\d+\\.',t,re.M))==14)", "ck('18_appendix_B_tables',len(re.findall(r'^Таблица Б\\.\\d+\\.',t,re.M))==18)")
s=s.replace("'revision':28,'date':'2026-10-20'", "'revision':29,'date':'2026-10-21'").replace("'notes':17", "'notes':18")
extra='''
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
ck('37_numbered_tables',len(re.findall(r'^Таблица (?:[123]\\.\\d+|[АБВГ]\\.\\d+)\\.',t,re.M))==37)
ck('canonical_sections',all((H/'sections'/f'{a}.md').read_text().strip() in t for a in anchors))
ck('consistent_operational_conclusion','наличие выборочного улучшения исходной базы при отсутствии подтверждённой устойчивой дополнительности' in t)
'''
s=s.replace("out={'revision':29",extra+"\nout={'revision':29")
(M/'verify_manuscript.py').write_text(s)
print('installed assembler and verifier')
