"""Standard-library integrity check before dependency installation."""
import argparse, hashlib, json
from pathlib import Path
def verify(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'BUNDLE-MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file(): raise ValueError('Invalid bundle path')
        with path.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        if path.stat().st_size!=item['bytes'] or digest!=item['sha256']: raise ValueError('Checksum mismatch: '+item['path'])
    print('Verified bundle files:',len(manifest['files']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);verify(p.parse_args().root)
