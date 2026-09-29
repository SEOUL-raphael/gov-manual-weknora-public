"""Fresh installation bundle: no keys, accounts, documents or live volumes."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def run(args):
    return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True).stdout
def main(output):
    output=output.resolve()
    if output.exists() or output.is_relative_to(ROOT): raise ValueError('Use a new destination outside checkout')
    docker=shutil.which('docker') or 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
    tracked=run(['git','-c','safe.directory='+str(ROOT),'ls-files','-z']).split('\0')
    if not any(tracked): raise ValueError('Stage reviewed release files first')
    output.mkdir(parents=True)
    for name in filter(None,tracked):
        p=Path(name)
        if p.parts[0] in ('data','upstream','.venv','.secrets') or name=='.env': raise ValueError('Private path staged')
        dest=output/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dest)
    lock=json.loads((ROOT/'config/reranker.lock.json').read_text())
    modeldir=Path('data/models/bge-reranker-v2-m3')
    for item in lock['files']:
        src=ROOT/modeldir/item['file']
        with src.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        if digest!=item['sha256']: raise ValueError('Model integrity failure')
        dest=output/modeldir/item['file'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    print('Downloading Python wheels',flush=True)
    subprocess.run([sys.executable,'-m','pip','download','--only-binary=:all:','--dest',str(output/'wheels'),'-r',str(ROOT/'requirements.lock.txt')],check=True)
    images=sorted(set(run([docker,'compose','config','--images']).splitlines()))
    for image in images: run([docker,'image','inspect',image])
    print('Exporting '+str(len(images))+' Docker images',flush=True)
    subprocess.run([docker,'save','-o',str(output/'images.tar'),*images],check=True)
    files=[]
    for path in sorted(output.rglob('*')):
        if not path.is_file():continue
        with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        files.append({'path':path.relative_to(output).as_posix(),'bytes':path.stat().st_size,'sha256':digest})
    manifest={'created_at':datetime.now(timezone.utc).isoformat(),'platform':'Windows x64 / Python 3.12 / Docker Linux amd64','fresh_install':True,'contains_secrets':False,'contains_documents':False,'inference_requires_internet':True,'images':images,'files':files}
    (output/'BUNDLE-MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('Bundle ready: '+str(output),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);main(p.parse_args().output)
