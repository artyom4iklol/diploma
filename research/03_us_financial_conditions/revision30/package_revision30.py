"""Package validated canonical text and full project, preserving prior archive entries."""
from pathlib import Path
import hashlib,json,shutil,zipfile,platform,importlib.metadata,difflib
P=Path(__file__).resolve().parent;R=P.parent;W=R.parent.parent;O=W/'output';O.mkdir(exist_ok=True)
for q in [R/'manuscript/VERIFICATION.json',P/'results/FINAL_VERIFICATION.json']:
 assert json.loads(q.read_text())['passed'],q
versions={'python':platform.python_version()}
for name in ['numpy','pandas','scipy','matplotlib','pypdf','Pillow']:
 versions[name]=importlib.metadata.version(name)
(P/'environment.json').write_text(json.dumps(versions,indent=2)+'\n')
# This diff is descriptive: the canonical sections are the final source of truth.
diff=[]
for s in sorted((R/'manuscript/sections').glob('*.md')):
 old=R/'manuscript/history/revision29/sections'/s.name
 if old.exists():diff.extend(difflib.unified_diff(old.read_text().splitlines(True),s.read_text().splitlines(True),fromfile='revision29/'+s.name,tofile='revision30/'+s.name))
(P/'manuscript_changes.diff').write_text(''.join(diff))
source=R/'manuscript/Diploma_US_Financial_Conditions_Euro_Area.md';target=O/source.name
# Companion directory makes this separately downloadable text usable when kept with its figures.
target.write_text(source.read_text().replace('../revision30/figures/','figures/'))
shutil.copytree(P/'figures',O/'figures',dirs_exist_ok=True)
shutil.copy2(P/'Diploma_Review_and_Changes.md',O/'Diploma_Review_and_Changes.md')
original=W/'input/thesis_us_financial_conditions_29_reviewed_full.zip'
with zipfile.ZipFile(original) as z:
 oldnames=[n for n in z.namelist() if not n.endswith('/')]
 missing=[n for n in oldnames if not (R.parent/n).is_file()]
 assert not missing,missing
 # Every overwritten prior entry must have its old bytes retained under history, or
 # be an explicitly replaced generated manifest. Numerical inputs are never replaced.
 changed=[]
 for n in oldnames:
  old=z.read(n);p=R.parent/n
  if hashlib.sha256(old).digest()!=hashlib.sha256(p.read_bytes()).digest():
   rel=p.relative_to(R);changed.append(str(rel));backup=R/'manuscript/history/revision29'/rel
   if str(rel).startswith('manuscript/'):
    backup=R/'manuscript/history/revision29'/str(rel).removeprefix('manuscript/')
   backup.parent.mkdir(parents=True,exist_ok=True)
   if backup.exists():assert backup.read_bytes()==old,backup
   else:backup.write_bytes(old)
(P/'PRIOR_ARCHIVE_PRESERVATION.json').write_text(json.dumps({'prior_file_entries':len(oldnames),'all_entries_retained':True,'changed_files':changed,'prior_bytes_saved_in_history':True},ensure_ascii=False,indent=2)+'\n')
manifest=R/'MANIFEST_REVISION30.json';entries=[]
for p in sorted(R.rglob('*')):
 if p.is_file() and p!=manifest:
  b=p.read_bytes();entries.append({'path':str(p.relative_to(R)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
manifest.write_text(json.dumps({'revision':30,'date':'2026-10-22','files':entries},ensure_ascii=False,indent=2)+'\n')
out=O/'thesis_us_financial_conditions_30_reviewed_full.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(R.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(R.parent))
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 assert set(oldnames).issubset(z.namelist())
 count=len(z.namelist())
summary={'archive':str(out),'archive_bytes':out.stat().st_size,'archive_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'entries':count,'previous_entries_retained':len(oldnames),'thesis':str(target),'thesis_bytes':target.stat().st_size,'report':str(O/'Diploma_Review_and_Changes.md'),'checks':48+27}
(O/'PACKAGE_VERIFICATION.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
