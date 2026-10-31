"""Lossless deterministic gzip cache for large research tables in GitHub.
This never overwrites a locally changed uncompressed file.
"""
from pathlib import Path
import gzip,hashlib,json,argparse
P=Path(__file__).resolve().parent
MANIFEST=P/'compressed_cache_manifest.json'
def digest(b):return hashlib.sha256(b).hexdigest()

def hydrate():
 if not MANIFEST.exists():return
 rows=json.loads(MANIFEST.read_text())
 for x in rows:
  dst=P/x['path'];src=P/x['compressed_path']
  if dst.exists():
   if digest(dst.read_bytes())!=x['sha256']:raise ValueError('Local cached file changed: '+x['path'])
   continue
  raw=src.read_bytes()
  if digest(raw)!=x['compressed_sha256']:raise ValueError('Compressed file changed: '+str(src))
  b=gzip.decompress(raw)
  if digest(b)!=x['sha256']:raise ValueError('Uncompressed checksum mismatch')
  dst.parent.mkdir(exist_ok=True,parents=True);dst.write_bytes(b)

def pack():
 rows=[]
 for p in sorted(P.rglob('*')):
  if not p.is_file() or p.suffix not in ['.csv','.jsonl'] or p.stat().st_size<250000:continue
  b=p.read_bytes();z=gzip.compress(b,compresslevel=9,mtime=0);q=p.with_name(p.name+'.gz');q.write_bytes(z)
  rows.append({'path':p.relative_to(P).as_posix(),'compressed_path':q.relative_to(P).as_posix(),'bytes':len(b),'sha256':digest(b),'compressed_bytes':len(z),'compressed_sha256':digest(z)})
 MANIFEST.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 (P/'.gitignore').write_text('__pycache__/\n*.pyc\n'+'\n'.join('/'+x['path'] for x in rows)+'\n')
 print('Lossless compressed cache:',len(rows),'files;',sum(x['bytes'] for x in rows),'->',sum(x['compressed_bytes'] for x in rows),'bytes')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--hydrate',action='store_true');args=a.parse_args()
 hydrate() if args.hydrate else pack()
