"""Validate the literature audit without downloading or estimating anything."""
from pathlib import Path
import json, hashlib, re, csv, gzip

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
reg=json.loads((HERE/'source_registry.json').read_text())
rows=reg['records']
ids={r['id'] for r in rows}
assert len(rows)==len(ids)==73
dois=[r['doi'].casefold() for r in rows if r.get('doi')]
assert len(dois)==len(set(dois))==54
assert all(r['identity_verified'] and r['identity_evidence'] for r in rows)
for r in rows:
 for key in ['model','target','data_and_period','horizon','evaluation','authors_finding','reviewer_assessment','use_in_diploma','reading_scope','checked_fragments','consulted_version']:
  assert isinstance(r[key],str) and r[key].strip(),(r['id'],key)
 assert r['primary_url'].startswith('https://'),r['id']
 if r['pdf_available']:
  assert r['pdf_pages']>0 and re.fullmatch('[0-9a-f]{64}',r['pdf_sha256']),r['id']
  if r['existing_repo_pdf']:
   p=REPO/r['existing_repo_pdf'];assert p.is_file(),p
   assert hashlib.sha256(p.read_bytes()).hexdigest()==r['pdf_sha256'],r['id']
 else:
  assert r['pdf_pages'] is None and r['pdf_sha256'] is None,r['id']
assert sum(r['pdf_available'] for r in rows)==57
assert sum(r['fulltext_status']=='Официальный полный HTML' for r in rows)==3
assert sum(r['fulltext_status']=='Полный текст не получен' for r in rows)==13
review=(HERE/'CRITICAL_REVIEW.md').read_text()
citations=set(re.findall(r'\b(?:S\d{2}|L\d{2}|N\d{2})\b',review))
assert citations<=ids,citations-ids
assert set(re.findall(r'^\[((?:S|L|N)\d{2})\]',review,re.M))==ids
with (HERE/'source_matrix.csv').open(encoding='utf-8-sig',newline='') as f:matrix=list(csv.DictReader(f))
assert [r['id'] for r in matrix]==[r['id'] for r in rows]
data=json.loads((HERE/'data_documentation_registry.json').read_text())['records']
assert len(data)==len({r['url'] for r in data})==30
checked=0
for r in data:
 if r['sha256']:
  p=REPO/r['existing_repo_path'];assert p.is_file(),p
  assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['id'];checked+=1
assert checked==13
with gzip.open(HERE/'crossref_metadata_snapshot.json.gz','rt',encoding='utf-8') as f:json.load(f)
print(json.dumps({'publications':73,'unique_dois':54,'pdf_copies':57,'official_html':3,'no_fulltext':13,'data_documents':30,'frozen_data_responses_hash_checked':checked,'citations_and_matrix_consistent':True},ensure_ascii=False,indent=2))
