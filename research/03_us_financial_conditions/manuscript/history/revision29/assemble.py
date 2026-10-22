"""Assemble the reviewed canonical sections. No data collection or model fits."""
from pathlib import Path
import re,json,hashlib
H=Path(__file__).resolve().parent;R=H.parent
anchors=['introduction','chapter-1','chapter-2','chapter-3','conclusion','references','appendices']
parts=[(a,(H/'sections'/f'{a}.md').read_text().strip()) for a in anchors]
toc=['# Финансовые условия США в прогнозировании рисков роста еврозоны','','## Оглавление','']
for a,t in parts:
 title=t.splitlines()[0].lstrip('# ');toc.append(f'- [{title}](#{a})')
 if a.startswith('chapter-'):
  toc.extend('  - '+x for x in re.findall(r'^## (\d\.\d\..*)$',t,re.M))
 if a=='appendices':toc.extend('  - '+x for x in re.findall(r'^## (Приложение .*)$',t,re.M))
out=H/'Diploma_US_Financial_Conditions_Euro_Area.md'
out.write_text('\n'.join(toc)+'\n\n'+'\n\n'.join(f'<a id="{a}"></a>\n\n{t}' for a,t in parts)+'\n')
for a,n in [('introduction','Introduction'),('conclusion','Conclusion'),('references','Bibliography'),('appendices','Appendices')]:
 (H/f'{n}.md').write_text(dict(parts)[a]+'\n')
stats={'revision':29,'date':'2026-10-21','sources':59,'academic_works':45,'official_sources':14,'calculation_notes':18,'new_model_fits':0,
 'words':{a:len(t.split()) for a,t in parts},
 'source_sha256':{f'manuscript/sections/{a}.md':hashlib.sha256((H/'sections'/f'{a}.md').read_bytes()).hexdigest() for a in anchors},
 'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
(H/'ASSEMBLY.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'revision':29,'bytes':out.stat().st_size,'words':stats['words'],'sources':59},ensure_ascii=False))
