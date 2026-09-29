"""Create a dedicated account/knowledge base. Re-running preserves the existing KB."""
import json
from pathlib import Path
from weknora_api import API, ROOT, ApiError
from export_corpus import atomic_json

KB_NAME = '정부 편람·주거정책 — WeKnora 비교 실험'

def main():
    api = API()
    try:
        # Register only after an explicit invalid-credentials response, never on a timeout.
        try:
            api.login()
        except ApiError as exc:
            if 'HTTP 401' not in str(exc):
                raise
            api.call('POST','/api/v1/auth/register',json={
                'username':'gov_admin','email':api.config['ADMIN_EMAIL'],
                'password':api.config['ADMIN_PASSWORD']})
            api.login()
        models = api.call('GET','/api/v1/models')['data']
        available = {m['id'] for m in models}
        required = {'gov-nvidia-embedding','gov-minimax-chat'}
        if not required.issubset(available):
            raise RuntimeError('Built-in models missing; inspect app startup logs before importing')
        matches = [kb for kb in api.call('GET','/api/v1/knowledge-bases')['data'] if kb['name']==KB_NAME]
        if len(matches)>1:
            raise RuntimeError('Ambiguous knowledge-base names')
        kb = matches[0] if matches else api.call('POST','/api/v1/knowledge-bases',json={
            'name':KB_NAME,'type':'document',
            'description':'gov-manual-rag READY 문서의 별도 사본. 원문 URL과 페이지 구분 유지.',
            'embedding_model_id':'gov-nvidia-embedding','summary_model_id':'gov-minimax-chat',
            'chunking_config':{'chunk_size':800,'chunk_overlap':100,'separators':['\n\n','\n','。','. ',' ']},
            'vlm_config':{'enabled':False},'extract_config':{'enabled':False},
            'question_generation_config':{'enabled':False},
            'storage_provider_config':{'provider':'local'},
        })['data']
        if kb['embedding_model_id']!='gov-nvidia-embedding':
            raise RuntimeError('Existing KB uses a different embedding model; refusing to modify it')
        (ROOT/'data').mkdir(exist_ok=True)
        atomic_json(ROOT/'data/runtime.json',{'knowledge_base_id':kb['id'],'knowledge_base_name':kb['name']})
        print('Knowledge base ready:',kb['id'])
        print('UI: http://localhost:'+api.config.get('UI_PORT','18765'))
        print('Local sign-in credentials: .env (not printed)')
    finally:
        api.close()

if __name__=='__main__':
    main()
