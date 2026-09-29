"""Read-only, deterministic export of READY canonical documents to a separate corpus."""
import argparse
import collections
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def atomic_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def export(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or source in output.parents:
        raise ValueError('Export must be outside the existing project')
    with closing(sqlite3.connect((source / 'gov_manual_rag.db').as_uri()+'?mode=ro', uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT id,title,agency,source_id,source_page_url,published_at FROM catalog_documents WHERE rag_status='READY' ORDER BY id").fetchall()
    output.mkdir(parents=True, exist_ok=True)
    documents, errors, warnings = [], [], []
    for row in rows:
        doc_id = str(uuid.UUID(row['id']))
        directory = source / 'data/documents' / doc_id
        content_path = directory / 'content.md'
        if not content_path.is_file():
            errors.append({'document_id':doc_id,'reason':'missing content.md'})
            continue
        raw = content_path.read_bytes()
        body = raw.decode('utf-8-sig')
        if not body.strip():
            errors.append({'document_id':doc_id,'reason':'empty content.md'})
            continue
        title = row['title'] or doc_id
        if '\ufffd' in title:
            warnings.append({'document_id':doc_id,'reason':'source title contains replacement characters'})
        # Visible page headings survive Markdown parsing better than HTML comments.
        body = re.sub(r'<!--\s*page:(\d+)\s*-->', r'\n## 페이지 \1\n', body)
        # Do not send broken local image paths to a server that cannot access them.
        body = re.sub(r'!\[([^\]]*)\]\((?:\./)?assets/[^)]+\)', r'[그림: \1 — 원문 링크 참조]', body)
        content = (f'# {title}\n\n- 기관: {row["agency"] or ""}\n'
                   f'- 수집원: {row["source_id"]}\n- 발행일: {row["published_at"] or ""}\n'
                   f'- 원문: {row["source_page_url"] or ""}\n- 원본 문서 ID: {doc_id}\n\n---\n\n{body}')
        encoded = content.encode('utf-8')
        relative = f'{doc_id}.md'
        path = output / relative
        if not path.exists() or path.read_bytes() != encoded:
            temp = path.with_suffix('.tmp')
            temp.write_bytes(encoded)
            temp.replace(path)
        documents.append({**dict(row), 'document_id':doc_id, 'path':relative,
                          'sha256':hashlib.sha256(encoded).hexdigest(),
                          'source_sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(encoded)})
    report = {'generated_at':datetime.now(timezone.utc).isoformat(), 'source_root':str(source),
              'ready_count':len(rows), 'exported_count':len(documents),
              'source_counts':dict(collections.Counter(d['source_id'] for d in documents)),
              'documents':documents, 'errors':errors, 'warnings':warnings}
    atomic_json(output / 'manifest.json', report)
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('D:/gov-manual-rag'))
    p.add_argument('--output', type=Path, default=ROOT/'data/corpus')
    args = p.parse_args()
    report = export(args.source, args.output)
    print(json.dumps({k:v for k,v in report.items() if k!='documents'},ensure_ascii=True))
    if report['errors']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
