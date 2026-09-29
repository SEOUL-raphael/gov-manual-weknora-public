"""Verify ALL corpus IDs on the server, then exercise hybrid search."""
import json
from collections import Counter
from export_corpus import atomic_json
from import_corpus import list_remote, remote_title
from weknora_api import API, ROOT

def main():
    runtime=json.loads((ROOT/'data/runtime.json').read_text())
    corpus=json.loads((ROOT/'data/corpus/manifest.json').read_text(encoding='utf-8'))
    api=API()
    try:
        api.login()
        kb=runtime['knowledge_base_id']
        remote=list_remote(api,kb)
        missing=[d['document_id'] for d in corpus['documents'] if remote_title(d) not in remote]
        matched=[remote[remote_title(d)] for d in corpus['documents'] if remote_title(d) in remote]
        states=dict(Counter(d['parse_status'] for d in matched))
        query='제주지역 행복주택 신혼부부 예비입주자 모집'
        hits=api.call('POST',f'/api/v1/knowledge-bases/{kb}/hybrid-search',json={
            'query_text':query,'match_count':10,'vector_threshold':0,'keyword_threshold':0})['data']
        housing_ids={remote[remote_title(d)]['id'] for d in corpus['documents']
                     if d['source_id']=='myhome_housing' and remote_title(d) in remote}
        myhome_hits=sum(h.get('knowledge_id') in housing_ids for h in hits)
        result={'expected_documents':corpus['exported_count'],'matched_documents':len(matched),
                'missing':missing,'parse_statuses':states,'query':query,'myhome_hits':myhome_hits,'hits':hits}
        atomic_json(ROOT/'data/live-verification.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('hits','missing')},ensure_ascii=True))
        assert not missing and states=={'completed':corpus['exported_count']},'Not all documents indexed'
        assert myhome_hits>0,'No myhome retrieval hit'
    finally:
        api.close()

if __name__=='__main__':
    main()
