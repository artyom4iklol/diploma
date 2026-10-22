"""Package revision 29 and verify that all research inputs from 28 survive."""
from pathlib import Path
import hashlib,json,shutil,zipfile

P=Path(__file__).resolve().parent;R=P.parent;TASK=R.parent.parent
original=TASK/'input/thesis_us_financial_conditions_28_complete_manuscript_full.zip'
O=TASK/'output';O.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
allowed={'README.md','CHANGELOG.md','MANIFEST_SHA256.json'}|{'manuscript/'+n for n in [
 'Diploma_US_Financial_Conditions_Euro_Area.md','Introduction.md','Conclusion.md','Bibliography.md','Appendices.md',
 'assemble.py','verify_manuscript.py','ASSEMBLY.json','VERIFICATION.json','ASSEMBLY_NOTES.md']}
changed=[];same=[];oldnames=set()
with zipfile.ZipFile(original) as z:
 assert z.testzip() is None
 for info in z.infolist():
  if info.is_dir():continue
  parts=Path(info.filename).parts
  assert parts[0]==R.name
  n=str(Path(*parts[1:]));oldnames.add(n);f=R/n
  assert f.is_file(),('missing',n)
  old=sha(z.read(info.filename));new=sha(f.read_bytes())
  if old==new:same.append(n)
  else:
   assert n in allowed,('unexpected modification',n)
   if n!='MANIFEST_SHA256.json':changed.append({'path':n,'old_sha256':old,'new_sha256':new})

preserved={'revision':29,'date':'2026-10-21','source_archive_sha256':sha(original.read_bytes()),
 'original_files':len(oldnames),'all_original_files_retained':True,
 'byte_identical_original_files_before_manifest_update':len(same),
 'allowed_modified_files_excluding_manifest':changed,
 'research_data_articles_and_previous_results_unchanged':True,
 'previous_manuscript_preserved':sha((R/'manuscript/history/revision28/Diploma_US_Financial_Conditions_Euro_Area.md').read_bytes())}
(P/'ARCHIVE_PRESERVATION.json').write_text(json.dumps(preserved,ensure_ascii=False,indent=2)+'\n')
files=[f for f in sorted(R.rglob('*')) if f.is_file() and ('__pycache__' not in f.parts or str(f.relative_to(R)) in oldnames)]
manifest={'profile':'full','revision':29,'date':'2026-10-21','files':{str(f.relative_to(R)):sha(f.read_bytes()) for f in files if f!=R/'MANIFEST_SHA256.json'}}
(R/'MANIFEST_SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
files=[f for f in sorted(R.rglob('*')) if f.is_file() and ('__pycache__' not in f.parts or str(f.relative_to(R)) in oldnames)]
zpath=O/'thesis_us_financial_conditions_29_reviewed_full.zip'
with zipfile.ZipFile(zpath,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in files:z.write(f,str(Path(R.name)/f.relative_to(R)))
with zipfile.ZipFile(zpath) as z:
 assert z.testzip() is None
 for n,h in manifest['files'].items():assert sha(z.read(R.name+'/'+n))==h,n
for src in [R/'manuscript/Diploma_US_Financial_Conditions_Euro_Area.md',P/'Diploma_Review_and_Changes.md']:
 shutil.copy2(src,O/src.name)
summary={'files':len(files),'original_files':len(oldnames),'modified_original_files_excluding_manifest':len(changed),
 'all_original_research_materials_preserved':True,'zip_crc_passed':True,'manifest_verified':len(manifest['files']),
 'zip_bytes':zpath.stat().st_size,'zip_sha256':sha(zpath.read_bytes()),
 'outputs':[{'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f.read_bytes())} for f in sorted(O.iterdir()) if f.is_file()]}
(TASK/'packaging_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
