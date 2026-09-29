import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
import httpx
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from export_corpus import export
from import_corpus import checked_content, list_remote, remote_title, sync_document
from weknora_api import API, ApiError

class FakeAPI:
    def __init__(self):
        self.calls=[]
    def call(self,method,path,**kwargs):
        self.calls.append((method,path,kwargs))
        return {'data':{'id':'remote-id','parse_status':'pending'}}

class PipelineTests(unittest.TestCase):
    def test_export_preserves_source_and_filters_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source'
            source.mkdir()
            doc=str(uuid.uuid4())
            db=source/'gov_manual_rag.db'
            with sqlite3.connect(db) as c:
                c.execute('CREATE TABLE catalog_documents(id,title,agency,source_id,source_page_url,published_at,rag_status)')
                c.execute('INSERT INTO catalog_documents VALUES(?,?,?,?,?,?,?)',(doc,'행복주택','LH','myhome_housing','https://example.org/original','2026-01-01','READY'))
                c.execute('INSERT INTO catalog_documents VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),'실패','LH','myhome_housing','',None,'FAILED'))
            c.close()
            d=source/'data/documents'/doc
            d.mkdir(parents=True)
            (d/'content.md').write_text('<!-- page:2 -->\n청년 입주 자격\n![도표](assets/a.png)',encoding='utf-8')
            before={p.relative_to(source):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
            out=Path(tmp)/'export'
            first=export(source,out)
            second=export(source,out)
            self.assertEqual(first['exported_count'],1)
            self.assertEqual(first['documents'],second['documents'])
            text=checked_content(out,first['documents'][0])
            self.assertIn('https://example.org/original',text)
            self.assertIn('## 페이지 2',text)
            self.assertIn('청년 입주 자격',text)
            self.assertNotIn('(assets/a.png)',text)
            after={p.relative_to(source):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
            self.assertEqual(before,after)
            with self.assertRaises(ValueError):
                export(source,source/'unsafe')

    def test_missing_document_is_reported_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source'
            source.mkdir()
            with sqlite3.connect(source/'gov_manual_rag.db') as c:
                c.execute('CREATE TABLE catalog_documents(id,title,agency,source_id,source_page_url,published_at,rag_status)')
                c.execute('INSERT INTO catalog_documents VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),'Missing','A','S','',None,'READY'))
            c.close()
            result=export(source,Path(tmp)/'out')
            self.assertEqual(result['ready_count'],1)
            self.assertEqual(result['exported_count'],0)
            self.assertEqual(len(result['errors']),1)

    def test_changed_corpus_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.md'
            p.write_text('changed')
            with self.assertRaises(ValueError):
                checked_content(Path(tmp),{'path':'a.md','sha256':'bad','document_id':'doc'})

    def test_new_document_is_published_not_draft(self):
        api=FakeAPI()
        doc={'title':'Title','document_id':'abc','sha256':'hash'}
        state=sync_document(api,'kb',doc,'body',{}, {})
        self.assertEqual(api.calls[0][0],'POST')
        self.assertEqual(api.calls[0][2]['json']['status'],'publish')
        self.assertEqual(state['status'],'pending')

    def test_completed_document_does_not_reembed(self):
        api=FakeAPI()
        doc={'title':'Title','document_id':'abc','sha256':'hash'}
        state=sync_document(api,'kb',doc,'body',{remote_title(doc):{'id':'id','parse_status':'completed'}},{'sha256':'hash'})
        self.assertEqual(api.calls,[])
        self.assertEqual(state['status'],'completed')

    def test_lost_checkpoint_reconciles_existing_row(self):
        api=FakeAPI()
        doc={'title':'Title','document_id':'abc','sha256':'hash'}
        sync_document(api,'kb',doc,'body',{remote_title(doc):{'id':'existing','parse_status':'completed'}},{})
        self.assertEqual(api.calls[0][0:2],('PUT','/api/v1/knowledge/manual/existing'))

    def test_inflight_document_is_not_submitted_twice(self):
        api=FakeAPI()
        doc={'title':'Title','document_id':'abc','sha256':'new'}
        state=sync_document(api,'kb',doc,'body',{remote_title(doc):{'id':'id','parse_status':'processing'}},{'sha256':'old'})
        self.assertEqual(api.calls,[])
        self.assertEqual(state['sha256'],'old')

    def test_duplicate_remote_title_stops_resume(self):
        class DuplicateAPI:
            def call(self,*args,**kwargs):
                return {'total':2,'data':[{'id':'1','title':'T'},{'id':'2','title':'T'}]}
        with self.assertRaises(RuntimeError):
            list_remote(DuplicateAPI(),'kb')

    def test_api_failure_never_leaks_server_body(self):
        client=httpx.Client(base_url='http://localhost',transport=httpx.MockTransport(
            lambda request:httpx.Response(500,text='secret-key-do-not-log')))
        api=API(config={'API_PORT':'18766'},client=client)
        with self.assertRaises(ApiError) as error:
            api.call('POST','/api/v1/test',json={})
        self.assertNotIn('secret',str(error.exception))
        api.close()

    def test_compose_has_isolated_storage_and_loopback_ports(self):
        config=yaml.safe_load((ROOT/'compose.yaml').read_text())
        self.assertEqual(config['name'],'gov-manual-weknora')
        for service in config['services'].values():
            self.assertNotIn('container_name',service)
            for port in service.get('ports',[]):
                self.assertTrue(port.startswith('127.0.0.1:'))
            for volume in service.get('volumes',[]):
                self.assertNotIn('gov-manual-rag',volume)
                self.assertNotIn('docker.sock',volume)
        models=yaml.safe_load((ROOT/'config/builtin_models.yaml').read_text())
        embed=next(m for m in models['builtin_models'] if m['id']=='gov-nvidia-embedding')
        self.assertEqual(embed['parameters']['embedding_parameters']['dimension'],2048)
        self.assertEqual(embed['parameters']['provider'],'nvidia')

if __name__=='__main__':
    unittest.main()
