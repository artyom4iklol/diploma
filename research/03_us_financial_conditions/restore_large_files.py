"""Restore byte-identical large archive members from checked parts (offline)."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent

def restore(root=ROOT):
    count = 0
    for item in json.loads((root / 'LARGE_FILES.json').read_text()):
        data = b''.join((root / name).read_bytes() for name in item['parts'])
        assert len(data) == item['bytes'], item['paths']
        assert hashlib.sha256(data).hexdigest() == item['sha256'], item['paths']
        for name in item['paths']:
            target = root / name
            if target.exists():
                if target.read_bytes() != data:
                    raise RuntimeError(f'Refusing to overwrite modified file: {name}')
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            count += 1
    return count

if __name__ == '__main__':
    print(f'Restored and verified {restore()} files.')
