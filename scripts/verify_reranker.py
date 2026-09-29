"""Exercise the local model through WeKnora's production reranker constructor."""
import json
import httpx
from weknora_api import API,ROOT
from export_corpus import atomic_json

def main():
    docs=['내일 서울은 맑고 오후에 비가 옵니다.',
          '신혼부부 임대주택은 무주택 세대의 주거 안정을 지원하며 소득과 자산 기준을 확인합니다.',
          '컴퓨터 그래픽카드 드라이버를 업데이트합니다.']
    query='신혼부부 임대주택 신청 자격은 무엇인가요?'
    api=API()
    try:
        api.login()
        models=api.call('GET','/api/v1/models')['data']
        assert any(m['id']=='gov-local-reranker' and m['type']=='Rerank' for m in models)
        r=api.call('POST','/api/v1/models/gov-local-reranker/debug',
                   files={'input':(None,query),'documents':(None,json.dumps(docs,ensure_ascii=False))})['data']
        if not r['ok']: raise RuntimeError(r.get('error','Model debug failed'))
        ranks=r['raw_response']; assert len(ranks)==len(docs)
        assert sorted(x['index'] for x in ranks)==list(range(len(docs)))
        best=max(ranks,key=lambda x:x['relevance_score']); assert best['index']==1
        for x in ranks: assert 0<=x['relevance_score']<=1
        report={'model':'BAAI/bge-reranker-v2-m3','runtime':'local CPU',
                'weknora_model_id':'gov-local-reranker','korean_relevance_test':True,
                'elapsed_ms':r['elapsed_ms'],'results':ranks}
        atomic_json(ROOT/'data/reranker-verification.json',report)
        print(json.dumps(report,ensure_ascii=True))
        bad=httpx.post('http://127.0.0.1:'+api.config.get('RERANK_PORT','18768')+'/v1/rerank',json={'query':query,'documents':[]},trust_env=False)
        assert bad.status_code==400
    finally: api.close()

if __name__=='__main__': main()
