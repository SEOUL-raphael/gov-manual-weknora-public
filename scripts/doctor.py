"""Inspect this isolated deployment without printing secrets or changing services."""
import json
import subprocess
import shutil
import hashlib
import httpx
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values
from export_corpus import atomic_json

ROOT=Path(__file__).resolve().parents[1]

def run(args):
    if args[0]=='docker':
        args=[shutil.which('docker') or 'C:/Program Files/Docker/Docker/resources/bin/docker.exe',*args[1:]]
    try:
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=40)
        return {'ok':p.returncode==0,'detail':(p.stdout+p.stderr).strip()[:1800]}
    except (OSError,subprocess.TimeoutExpired) as e:
        return {'ok':False,'detail':type(e).__name__}

def main():
    env=dotenv_values(ROOT/'.env')
    standalone=ROOT/'.tools/docker-compose-windows-x86_64.exe'
    docker_path=shutil.which('docker') or 'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
    compose_args=([str(standalone)] if not Path(docker_path).is_file() and standalone.is_file()
                  else [docker_path,'compose'])
    try:
        health=httpx.get('http://127.0.0.1:'+env.get('API_PORT','18766')+'/health',timeout=3,trust_env=False)
        api_health={'ok':health.status_code==200,'status_code':health.status_code}
    except httpx.HTTPError as e:
        api_health={'ok':False,'detail':type(e).__name__}
    report={'checked_at':datetime.now(timezone.utc).isoformat(),
            'upstream':run(['git','-c','safe.directory='+str(ROOT/'upstream'),'-C','upstream','rev-parse','HEAD']),
            'compose':run([*compose_args,'config','--quiet']),
            'docker':run(['docker','info','--format','{{.ServerVersion}}']),
            'api_health':api_health,
            'credentials_present':{k:bool(env.get(k)) for k in ('NVIDIA_API_KEY','MINIMAX_API_KEY','SYSTEM_AES_KEY')},
            'ui_url':'http://localhost:'+env.get('UI_PORT','18765')}
    p=ROOT/'data/corpus/manifest.json'
    if p.is_file():
        corpus=json.loads(p.read_text(encoding='utf-8'))
        report['corpus']={k:corpus[k] for k in ('ready_count','exported_count','source_counts','errors')}
    lock=json.loads((ROOT/'UPSTREAM.lock.json').read_text(encoding='utf-8'))
    report['upstream_pin_matches']=hashlib.sha256((ROOT/'config/weknora.yaml').read_bytes()).hexdigest()==lock['config_sha256']
    report['runtime_ready']=report['docker']['ok'] and report['compose']['ok'] and api_health['ok'] and report['upstream_pin_matches']
    (ROOT/'data').mkdir(exist_ok=True)
    atomic_json(ROOT/'data/doctor.json',report)
    print(json.dumps(report,ensure_ascii=True,indent=2))
    raise SystemExit(0 if report['runtime_ready'] else 2)

if __name__=='__main__':
    main()
