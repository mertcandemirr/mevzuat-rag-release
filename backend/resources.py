"""Pinned model artifacts and validated, read-only release corpus."""
import hashlib
import json
import os
from pathlib import Path

import faiss
from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/kanunlar'
INDEX = Path(os.getenv('INDEX_DIR', ROOT / 'data/index'))
EMBEDDING = 'intfloat/multilingual-e5-base'
RERANKER = 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'
REVISIONS = {EMBEDDING:'d128750597153bb5987e10b1c3493a34e5a4502a',
             RERANKER:'1427fd652930e4ba29e8149678df786c240d8825'}

def model_dir(name):
    opts = dict(revision=REVISIONS[name],allow_patterns=['*.json','*.safetensors','*.model','*.txt'])
    try:
        return snapshot_download(name,local_files_only=True,**opts) if complete(name,opts) else snapshot_download(name,**opts)
    except OSError as exc:
        raise RuntimeError(f'Model yüklenemedi: {name}') from exc

def complete(name,opts):
    try:
        path=Path(snapshot_download(name,local_files_only=True,**opts))
    except OSError:
        return False
    return all((path/f).is_file() for f in ['config.json','model.safetensors','tokenizer_config.json','tokenizer.json'])

def rows_and_hash():
    inventory=json.loads((DATA/'kaynaklar.json').read_text())
    for law in inventory:
        for name, expected in law['files'].items():
            source = DATA / 'kaynaklar' / name
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ValueError(f'Kaynak özeti uyuşmuyor: {name}')
    rows=json.loads((DATA/'chunks.json').read_text())
    if {r['law_number'] for r in rows} != {entry['law'] for entry in inventory}:
        raise ValueError('Kaynak listesi ve aktif kanunlar uyuşmuyor')
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return rows,digest

def load_index():
    rows,digest=rows_and_hash()
    meta=json.loads((INDEX/'manifest.json').read_text())
    file=INDEX/'vectors.faiss'
    if (meta['corpus_hash'],meta['embedding'],meta['revision'],meta['dimension'])!=(digest,EMBEDDING,REVISIONS[EMBEDDING],768):
        raise ValueError('İndeks ile korpus veya embedding sürümü uyuşmuyor')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=meta['index_sha256']:
        raise ValueError('FAISS dosya özeti uyuşmuyor')
    idx=faiss.read_index(str(file))
    if idx.ntotal!=len(rows) or idx.d!=768:
        raise ValueError('FAISS boyutu/kayıt sayısı farklı')
    return rows,idx
