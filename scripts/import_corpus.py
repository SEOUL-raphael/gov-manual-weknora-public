"""Resumable import via official manual-Markdown API; never claims queued=complete."""
import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from export_corpus import atomic_json
from weknora_api import API, ROOT

def remote_title(doc):
    # Source UUID disambiguates real catalog entries with identical titles.
    return f'{doc["title"]} [GMR:{doc["document_id"]}]'

def list_remote(api, kb):
    result = {}
    page = 1
    seen_ids = set()
    while True:
        payload = api.call('GET',f'/api/v1/knowledge-bases/{kb}/knowledge',params={'page':page,'page_size':100})
        rows = payload['data']
        for row in rows:
            if row['id'] in seen_ids:
                raise RuntimeError('Non-advancing server pagination')
            seen_ids.add(row['id'])
            if row['title'] in result:
                raise RuntimeError('Duplicate remote title; refusing an ambiguous resume')
            result[row['title']] = row
        if len(seen_ids)>=payload['total']:
            return result
        if not rows:
            raise RuntimeError('Server returned an incomplete document listing')
        page += 1

def checked_content(corpus, doc):
    path = (corpus/doc['path']).resolve()
    if corpus.resolve() not in path.parents:
        raise ValueError('Document path escapes corpus')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=doc['sha256']:
        raise ValueError('Corpus checksum mismatch: '+doc['document_id'])
    return raw.decode('utf-8')

def sync_document(api, kb, doc, content, remote, previous):
    item = remote.get(remote_title(doc))
    # A local completed flag alone is not trusted; the server must still have the row.
    if item and previous.get('sha256')==doc['sha256'] and item.get('parse_status')=='completed':
        return {'knowledge_id':item['id'],'sha256':doc['sha256'],'status':'completed'}
    if item and item.get('parse_status') in ('pending','processing'):
        return {'knowledge_id':item['id'],'sha256':previous.get('sha256'),
                'status':item['parse_status']}
    payload = {'title':remote_title(doc),'content':content,'status':'publish','channel':'api',
               'process_config':{'enable_multimodel':False,'graph_enabled':False,
                                 'question_generation_config':{'enabled':False},
                                 'chunking_config':{'chunk_size':800,'chunk_overlap':100,
                                                    'separators':['\n\n','\n','。','. ',' ']}}}
    if item:
        # Also reconciles an accepted POST whose response was lost before the local checkpoint.
        result = api.call('PUT','/api/v1/knowledge/manual/'+item['id'],json=payload)['data']
    else:
        result = api.call('POST',f'/api/v1/knowledge-bases/{kb}/knowledge/manual',json=payload)['data']
    return {'knowledge_id':result['id'],'sha256':doc['sha256'],
            'status':result.get('parse_status','pending')}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=10,help='New/update submissions; 0=all')
    p.add_argument('--wait',type=int,default=600,help='Seconds to wait per document; 0=queue only')
    p.add_argument('--source-id',help='Optional source subset, e.g. myhome_housing')
    p.add_argument('--dry-run',action='store_true')
    args = p.parse_args()
    if args.limit<0 or args.wait<0:
        p.error('limit/wait must be nonnegative')
    corpus = ROOT/'data/corpus'
    manifest = json.loads((corpus/'manifest.json').read_text(encoding='utf-8'))
    if manifest['errors'] or manifest['ready_count']!=manifest['exported_count']:
        raise RuntimeError('Incomplete corpus; fix export before importing')
    docs = [d for d in manifest['documents'] if not args.source_id or d['source_id']==args.source_id]
    if args.dry_run:
        for doc in docs:
            checked_content(corpus,doc)
        print(json.dumps({'validated_documents':len(docs),'new_submissions_limit':args.limit,
                          'network_requests':0}))
        return
    runtime = json.loads((ROOT/'data/runtime.json').read_text(encoding='utf-8'))
    kb = runtime['knowledge_base_id']
    state_path = ROOT/'data/import-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'knowledge_base_id':kb,'documents':{}}
    if state['knowledge_base_id']!=kb:
        raise RuntimeError('Import state belongs to another KB')
    api = API()
    submitted = 0
    try:
        api.login()
        remote = list_remote(api,kb)
        for doc in docs:
            prior = state['documents'].get(doc['document_id'],{})
            item = remote.get(remote_title(doc))
            if item and prior.get('sha256')==doc['sha256'] and item.get('parse_status')=='completed':
                prior['status']='completed'
                continue
            if args.limit and submitted>=args.limit:
                break
            result = sync_document(api,kb,doc,checked_content(corpus,doc),remote,prior)
            state['documents'][doc['document_id']]=result
            atomic_json(state_path,state)
            submitted+=1
            deadline=time.monotonic()+args.wait
            while args.wait and result['status'] not in ('completed','failed'):
                if time.monotonic()>=deadline:
                    raise RuntimeError('Indexing still pending; checkpoint saved. Re-run to resume.')
                time.sleep(3)
                item=api.call('GET','/api/v1/knowledge/'+result['knowledge_id'])['data']
                result['status']=item['parse_status']
                atomic_json(state_path,state)
            print(doc['document_id'],result['status'],flush=True)
            if result['status']=='failed':
                raise RuntimeError('Document indexing failed; inspect WeKnora task details, then retry')
        atomic_json(state_path,state)
        print(json.dumps({'submitted_or_waited':submitted,
                          'checkpoint_statuses':dict(Counter(d['status'] for d in state['documents'].values()))}))
    finally:
        api.close()

if __name__=='__main__':
    main()
