"""Download pinned public model files and verify Hugging Face LFS SHA256."""
import hashlib
import json
from pathlib import Path
import httpx
import truststore
truststore.inject_into_ssl()
ROOT=Path(__file__).resolve().parents[1]
MODEL='BAAI/bge-reranker-v2-m3'

def main():
    target=ROOT/'data/models/bge-reranker-v2-m3'; target.mkdir(parents=True,exist_ok=True)
    lock_path=ROOT/'config/reranker.lock.json'
    pinned=json.loads(lock_path.read_text()) if lock_path.exists() else None
    with httpx.Client(follow_redirects=True,timeout=300,trust_env=False) as c:
        revision='/revision/'+pinned['revision'] if pinned else ''
        r=c.get('https://huggingface.co/api/models/'+MODEL+revision,params={'blobs':'true'}); r.raise_for_status(); info=r.json()
        wanted={'config.json','model.safetensors','tokenizer.json','tokenizer_config.json','special_tokens_map.json','sentencepiece.bpe.model','README.md'}
        files=[]
        for f in info['siblings']:
            name=f['rfilename']
            if name not in wanted: continue
            path=target/name; expected=next((x['sha256'] for x in pinned['files'] if x['file']==name),None) if pinned else f.get('lfs',{}).get('sha256')
            if path.exists() and expected and hashlib.file_digest(path.open('rb'),'sha256').hexdigest()==expected:
                files.append({'file':name,'sha256':expected});continue
            print('Downloading '+name,flush=True)
            temp=path.with_suffix(path.suffix+'.part'); digest=hashlib.sha256(); size=0
            with c.stream('GET',f'https://huggingface.co/{MODEL}/resolve/{info["sha"]}/{name}') as response:
                response.raise_for_status()
                with temp.open('wb') as out:
                    for block in response.iter_bytes(1024*1024):
                        out.write(block);digest.update(block);size+=len(block)
                        if size%(128*1024*1024)==0: print(f'{name}: {size//(1024*1024)} MiB',flush=True)
            actual=digest.hexdigest()
            if expected and expected!=actual: raise ValueError('Model checksum mismatch')
            temp.replace(path);files.append({'file':name,'sha256':actual})
        assert wanted-{'sentencepiece.bpe.model','special_tokens_map.json'} <= {f['file'] for f in files}
        lock={'model':MODEL,'revision':info['sha'],'files':files}
        (ROOT/'config/reranker.lock.json').write_text(json.dumps(lock,indent=2),encoding='utf-8')
        print('Model download and SHA256 verification complete',flush=True)
if __name__=='__main__': main()
