"""Build the release representation in a new, previously unused directory."""
import argparse,hashlib,json,tempfile
from pathlib import Path
import faiss
from sentence_transformers import SentenceTransformer
from backend.resources import EMBEDDING,REVISIONS,model_dir,rows_and_hash

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    target=parser.parse_args().output
    if target.exists():raise FileExistsError(target)
    rows,digest=rows_and_hash()
    model=SentenceTransformer(model_dir(EMBEDDING),device='cpu')
    docs=[f"passage: {r['law_title']} {r['law_number']} Madde {r['article_number']} {r['article_title']} {r['text']}" for r in rows]
    if any(len(model.tokenizer.encode(d))>model.max_seq_length for d in docs):raise ValueError('Uzun chunk')
    idx=faiss.IndexFlatIP(768)
    idx.add(model.encode(docs,batch_size=8,normalize_embeddings=True))
    target.parent.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        stage=Path(tmp)/'index';stage.mkdir()
        f=stage/'vectors.faiss';faiss.write_index(idx,str(f))
        meta=dict(embedding=EMBEDDING,revision=REVISIONS[EMBEDDING],rows=idx.ntotal,dimension=idx.d,corpus_hash=digest,index_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        (stage/'manifest.json').write_text(json.dumps(meta,indent=2))
        stage.rename(target)
if __name__=='__main__':main()
