import json,time,hashlib,gc,re,threading,os
from pathlib import Path
import numpy as np
from rank_bm25 import BM25Okapi
from backend.terms import tokens
from backend.scope import scoped_references
from backend.query import expand
from backend.resources import DATA, load_index, model_dir, EMBEDDING, RERANKER
ROOT=Path(__file__).resolve().parents[1]
class Engine:
 def __init__(self):
  import torch,faiss
  from sentence_transformers import SentenceTransformer,CrossEncoder
  from huggingface_hub import snapshot_download
  torch.set_num_threads(1);self.torch=torch;self.faiss=faiss;self.lock=threading.Lock();start=time.perf_counter()
  self.rows,self.index=load_index()
  self.lookup={r['document_id']:r for r in self.rows}
  self.embedding_id=EMBEDDING
  self.encoder=SentenceTransformer(model_dir(EMBEDDING),device=os.getenv('RETRIEVAL_DEVICE','cpu'),local_files_only=True)
  self.embedding_load_count=1
  self.reranker_id=RERANKER
  self.ce=CrossEncoder(model_dir(RERANKER),device=os.getenv('RETRIEVAL_DEVICE','cpu'),max_length=512,local_files_only=True)
  self.docs=[self.header(r)+' '+r['text'] for r in self.rows];self.bm=BM25Okapi([tokens(d) for d in self.docs]);self.token_sets=[set(tokens(d)) for d in self.docs];self.load_seconds=time.perf_counter()-start;self.index_build_count=0;self.coverage={'laws':len({r['law_number'] for r in self.rows}),'articles':len({r['parent_id'] for r in self.rows}),'chunks':len(self.rows)};self.searchable={i for i,r in enumerate(self.rows) if r.get('legal_status','snapshot_current')=='snapshot_current'}
 def header(self,r):return f"{r['law_title']} {r['law_number']} Madde {r['article_number']} {r['article_title']}"
 def retrieve(self,q):
  with self.lock:
   self.faiss.omp_set_num_threads(1)
   start=time.perf_counter();pair,error=scoped_references(q,{r["law_number"] for r in self.rows})
   if error:return [],{'scope_error':error}
   if any(not any((r['law_number'],r['article_number'])==p for r in self.rows) for p in pair):return [],{'scope_error':'missing_explicit_reference','references':pair}
   if any(not any((r['law_number'],r['article_number'])==p and i in self.searchable for i,r in enumerate(self.rows)) for p in pair):return [],{'scope_error':'repealed_or_temporal_reference','references':pair}
   historical=re.search(r'\b(19\d{2}|20\d{2})\s*yıl',q)
   if historical and historical[1]!='2026':return [],{'scope_error':'historical_version_not_available'}
   search_query,expanded_terms=expand(q)
   vec=np.asarray(self.encoder.encode(['query: '+search_query],normalize_embeddings=True,show_progress_bar=False),dtype='float32');distance,ids=self.index.search(vec,len(self.rows));dense=[i for _,i in sorted(zip(distance[0].tolist(),ids[0].tolist()),key=lambda x:(-x[0],x[1])) if i in self.searchable][:50]
   score=self.bm.get_scores(tokens(search_query));qt=set(tokens(search_query));sparse=[int(i) for i in np.argsort(-score,kind='stable') if int(i) in self.searchable and qt & self.token_sets[int(i)]][:50]
   fused={}
   for ch in [dense,sparse]:
    for rank,i in enumerate(ch,1):fused[i]=fused.get(i,0)+1/(60+rank)
   hybrid=sorted(fused,key=lambda i:(-fused[i],i));pins=[i for i,r in enumerate(self.rows) if i in self.searchable and (r['law_number'],r['article_number']) in pair];order=pins+[i for i in hybrid if i not in pins];candidates=order[:80]
   scores=self.ce.predict([(search_query,self.header(self.rows[i])+'\n'+self.rows[i]['text']) for i in candidates],batch_size=4,show_progress_bar=False)
   reranked=[i for _,i in sorted(zip(scores.tolist(),candidates),key=lambda x:-x[0])];ranked=[i for i in reranked if i in pins]+[i for i in reranked if i not in pins]
   dense_anchor_parents=list(dict.fromkeys(self.rows[i]['parent_id'] for i in dense[:5]))[:2]
   # Protect independent dense evidence from cross-channel/reranker displacement, for every query.
   parent_order=list(dict.fromkeys([self.rows[i]['parent_id'] for i in pins]+([] if pair else [self.rows[i]['parent_id'] for i in ranked[:1]]+dense_anchor_parents+[self.rows[i]['parent_id'] for i in ranked])))
   parents=[]
   for parent in parent_order:
    if parent not in parents:parents.append(parent)
    if len(parents)==4:break
   # Preserve article variety, then expand short parent provisions without test-target lookup.
   selected=[]
   for parent in parents:
    siblings=[i for i,r in enumerate(self.rows) if r['parent_id']==parent]
    if sum(len(self.rows[i]['text']) for i in siblings)<3800:items=siblings
    else:items=list(dict.fromkeys(siblings[:1]+[i for i in ranked if self.rows[i]['parent_id']==parent][:4]))
    selected.extend(items)
   # Prioritize each parent's best evidence before round-robin supplemental clauses.
   primary=[next((i for i in ranked if self.rows[i]['parent_id']==p),next(i for i,r in enumerate(self.rows) if r['parent_id']==p)) for p in parents];expanded=primary+[i for i in selected if i not in primary];context=[];chars=0
   for i in expanded:
    if chars+len(self.rows[i]['text'])>10000:continue
    context.append(self.rows[i]);chars+=len(self.rows[i]['text'])
   def names(order):return [self.rows[i]['document_id'] for i in order]
   trace={'dense':names(dense),'bm25':names(sparse),'hybrid':names(hybrid),'candidate_ids':names(candidates),'reranker':names(reranked),'after_exact_protection':names(ranked),'selected_parents':parents,'dense_anchor_parents':dense_anchor_parents,'reranker_anchor_parents':list(dict.fromkeys(self.rows[i]['parent_id'] for i in ranked))[:2],'expanded_context':[r['document_id'] for r in context],'references':pair,'search_query':search_query,'expanded_terms':expanded_terms,'candidate_depth':80,'retrieval_seconds':time.perf_counter()-start,'embedding_model':self.embedding_id,'embedding_dimension':768,'index_build_count':0,'max_dense_similarity':float(distance[0][0])}
   # Lexical overlap is a conservative relevance guard, not a legal entailment classifier.
   if not pair and not sparse:return [],{**trace,'scope_error':'no_lexical_evidence'}
   return context,trace
