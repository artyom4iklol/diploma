from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent
manifest=json.loads((P/'MANIFEST_SHA256.json').read_text())
for row in manifest['files']:
 f=P/row['path'];assert f.is_file(),row['path'];b=f.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
print('Verified',len(manifest['files']),'files; profile:',manifest['profile'])
