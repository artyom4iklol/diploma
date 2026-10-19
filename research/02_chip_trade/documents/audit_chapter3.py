"""Check manuscript numbers against saved evidence and inspect DOCX structure."""
from pathlib import Path
from zipfile import ZipFile
import json,hashlib,re
import numpy as np
from lxml import etree
from PIL import Image

HERE=Path(__file__).resolve().parent
E=json.loads((HERE/'chapter3_evidence.json').read_text())
E2=json.loads((HERE/'chapter2_evidence.json').read_text())
text=(HERE/'chapter3_content.md').read_text()
checks=[]

def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)

def fmt(x,n=2,positive=False):
 s=f'{x:+.{n}f}' if positive and x>0 else f'{x:.{n}f}'
 return s.replace('.',',').replace('-','−')

for reporter in (392,410):
 base=next(r for r in E['scenarios'] if r['reporter']==reporter and r['shift_pp']==0)
 previous=next(r for r in E2['memory_and_remaining_fixed_indices'] if r['reporter']==reporter and r['weight_year']==2024)
 check(f'{reporter}: independent saved Chapter 2 baseline',abs(base['variance_pp2']-previous['total_variance_pp2'])<1e-8)
 for r in [r for r in E['scenarios'] if r['reporter']==reporter]:
  shift=r['shift_pp'];ci=next(c for c in E['paired_intervals'] if c['reporter']==reporter and c['shift_pp']==shift and c['block_months']==12)
  lower=fmt(ci['ci_low'],3 if reporter==392 and shift==5 else 2)
  row='| '+' | '.join([fmt(shift,1,True),fmt(r['memory_share_pct']),fmt(r['sd_pp']),fmt(r['delta_sd_pp'],2,True),f"[{lower}; {fmt(ci['ci_high'])}]"])+ ' |'
  check(f'{reporter}/{shift}: manuscript row including CI',row in text)
 for c in [c for c in E['checks'] if c['reporter']==reporter]:
  check(f'{reporter}: variance identity',c['variance_identity_error_pp2']<1e-8)
  check(f'{reporter}: observability and normalized weights',c['finite_all'] and c['weights_nonnegative_and_sum_one'])
for shift in (-2.5,-5.):
 rs=[next(r for r in E['scenarios'] if r['reporter']==c and r['shift_pp']==shift) for c in (392,410)]
 row='| '+' | '.join([fmt(shift,1),*[fmt(r['remaining_export_change_pct_if_memory_unchanged']) for r in rs],*[fmt(r['extra_remaining_export_usd_if_memory_unchanged']/1e9) for r in rs]])+' |'
 check(f'{shift}: cost-independent expansion arithmetic',row in text)
for num in range(1,7):check(f'table 3.{num}: caption and text reference', len(re.findall(rf'(?:Таблица|таблиц[а-я]+) 3\.{num}\b',text))>=2 or (num==4 and 'таблицах 3.3 и 3.4' in text))
for num in range(1,4):check(f'figure 3.{num}: text reference',f'рисунке 3.{num}' in text)
check('four paragraphs',len(re.findall(r'^## 3\.[1-4] ',text,re.M))==4)
check('six unique sources',len(json.loads((HERE/'chapter3_source_audit.json').read_text())['sources'])==6)
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(HERE/'chapter3.docx') as z:
 root=etree.fromstring(z.read('word/document.xml'))
 check('native footnotes',len(root.findall('.//w:footnoteReference',ns))==7)
 check('three figures and six tables',len(root.findall('.//w:drawing',ns))==3 and len(root.findall('.//w:tbl',ns))==6)
 check('editable equations',len(root.findall('.//m:oMath',ns))>=3)
 check('no Word hyperlinks',not root.findall('.//w:hyperlink',ns))
 check('no external hyperlink relationship',all(b'relationships/hyperlink' not in z.read(n) for n in z.namelist() if n.endswith('.rels')))
 check('no unconverted math markup',b'$$' not in z.read('word/document.xml') and b'\\tag' not in z.read('word/document.xml'))
 for i in range(1,4):
  ar=np.asarray(Image.open(HERE/f'chapter3_assets/fig3_{i}.png').convert('RGB'))
  check(f'figure {i} monochrome',np.array_equal(ar[:,:,0],ar[:,:,1]) and np.array_equal(ar[:,:,1],ar[:,:,2]))
report=dict(status='passed',checks=checks,docx_sha256=hashlib.sha256((HERE/'chapter3.docx').read_bytes()).hexdigest(),
 note='Content checks and numerical consistency; visual QA is recorded separately after inspecting rendered pages.')
(HERE/'chapter3_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Passed',len(checks),'checks')
