"""WeKnora's documents/results contract -> local TEI texts/score contract."""
import json
import urllib.request
from http.server import BaseHTTPRequestHandler,HTTPServer

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,status,payload):
        data=json.dumps(payload).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path!='/health': return self.reply(404,{})
        try:
            with urllib.request.urlopen('http://reranker:80/health',timeout=10) as r:
                return self.reply(r.status,{'status':'ok'})
        except Exception: return self.reply(503,{'status':'not_ready'})
    def do_POST(self):
        if self.path!='/v1/rerank': return self.reply(404,{})
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=2_000_000: return self.reply(413,{'error':'Request size limit'})
            data=json.loads(self.rfile.read(size));query=data['query'];docs=data['documents']
            if not isinstance(query,str) or not query.strip() or not isinstance(docs,list) or not 1<=len(docs)<=100 or not all(isinstance(d,str) and d.strip() for d in docs):
                return self.reply(400,{'error':'Invalid query or documents'})
            body=json.dumps({'query':query,'texts':docs,'truncate':True}).encode()
            req=urllib.request.Request('http://reranker:80/rerank',data=body,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=180) as r: ranks=json.load(r)
            results=[{'index':v['index'],'relevance_score':v['score'],'document':{'text':docs[v['index']]}} for v in ranks]
            return self.reply(200,{'model':'BAAI/bge-reranker-v2-m3','results':results})
        except (ValueError,KeyError,TypeError): return self.reply(400,{'error':'Invalid request'})
        except Exception: return self.reply(502,{'error':'Local reranker unavailable'})

HTTPServer(('0.0.0.0',8080),Handler).serve_forever()
