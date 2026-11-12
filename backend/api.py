import os,json,time,uuid,logging,threading
from contextlib import asynccontextmanager
from urllib.parse import urlparse
import requests,psutil
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from backend.rag import Engine
from backend.validation import validate,validate_quotes
log=logging.getLogger('uvicorn.error');engine=None;gate=threading.Lock()
LLM_URL=os.getenv('MEVZUAT_LLM_URL','http://127.0.0.1:8012').rstrip('/')
if urlparse(LLM_URL).hostname not in ('127.0.0.1','localhost','::1','host.docker.internal','worker'):raise RuntimeError('Only loopback model providers are permitted')
@asynccontextmanager
async def lifespan(app):
 global engine
 engine=Engine();log.info('RAG_READY embedding=%s dimension=768 load_count=1 reused_faiss=true seconds=%.3f',engine.embedding_id,engine.load_seconds);yield
app=FastAPI(title='Mevzuat Yerel API',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5174','http://localhost:5174'],allow_methods=['POST','GET'],allow_headers=['Content-Type'])
class ChatRequest(BaseModel):
 question:str|None=Field(default=None,max_length=4000)
 message:str|None=Field(default=None,max_length=4000)
 messages:list[dict]|None=Field(default=None,max_length=50)
@app.get('/api/health')
def health():
 try:
  r=requests.get(LLM_URL+'/health',timeout=3);r.raise_for_status();provider=r.json()
  if not provider.get('ready') or provider.get('base_model')!='Qwen/Qwen3-4B-Instruct-2507':raise ValueError('Unexpected model')
 except (requests.RequestException,ValueError) as exc:raise HTTPException(503,detail={'error':'model_unavailable','provider':'mlx','model':'Qwen/Qwen3-4B-Instruct-2507'}) from exc
 return {'ready':engine is not None,'embedding_model':engine.embedding_id,'embedding_dimension':768,'embedding_load_count':engine.embedding_load_count,'index_build_count':engine.index_build_count,'rag_load_seconds':engine.load_seconds,'rss_bytes':psutil.Process().memory_info().rss,'provider':provider,'corpus':engine.coverage,'retrieval':{'dense':'FAISS IndexFlatIP','sparse':'BM25Okapi','fusion':'RRF k=60','reranker':engine.reranker_id}}
def ui_source(s):return {**s,'id':s['document_id'],'law':s['law_number'],'article':s['article_number'],'title':s['article_title'],'lawTitle':s['law_title'],'url':s['source_url'],'snapshot':s.get('verified_at','Tarih bilinmiyor')}
@app.post('/api/chat')
@app.post('/api/v1/chat',include_in_schema=False)
def chat(req:ChatRequest):
 question=(req.question or req.message or next((m.get('content','') for m in reversed(req.messages or []) if m.get('role')=='user'),''))
 if not isinstance(question,str) or not question.strip() or len(question)>4000:raise HTTPException(422,detail='Geçerli bir soru gereklidir.')
 if not gate.acquire(blocking=False):raise HTTPException(429,detail='Yerel model meşgul. Tekrar deneyin.')
 try:
  request_id=uuid.uuid4().hex;start=time.perf_counter();sources,trace=engine.retrieve(question)
  if not sources:return {'request_id':request_id,'status':'yeterli_kaynak_yok','answer':None,'sources':[],'issues':[trace.get('scope_error','no_sources')],'trace':trace}
  payload={'request_id':request_id,'question':question,'sources':sources,'answer_mode':'source_quotes','retrieval_question':trace.get('search_query',question)}
  try:
   response=requests.post(LLM_URL+'/generate',json=payload,timeout=120)
   if response.status_code==413:raise HTTPException(413,detail={'error':'context_budget_exceeded','request_id':request_id})
   if response.status_code==429:raise HTTPException(429,detail={'error':'model_busy','request_id':request_id})
   response.raise_for_status();completion=response.json()
  except requests.RequestException as exc:
   log.error('MODEL_UNAVAILABLE request=%s provider=mlx base_model=Qwen/Qwen3-4B-Instruct-2507 error=%s',request_id,type(exc).__name__)
   raise HTTPException(503,detail={'error':'model_unavailable','request_id':request_id}) from exc
  except ValueError as exc:raise HTTPException(502,detail={'error':'invalid_model_response'}) from exc
  result=validate_quotes(completion,sources,question) if completion.get('answer_mode')=='source_quotes' else validate(completion,sources)
  if result['answer'] is not None and not any(s['parent_id'] in (trace['dense_anchor_parents']+trace.get('reranker_anchor_parents',[])+[f'{law}:normal:{article}' for law,article in trace.get('references',[])]) for s in result['sources']):
   result={'status':'inceleme_gerekli','answer':None,'sources':[],'issues':['model_selection_disagrees_with_independent_dense_evidence']}
  audit_dir=os.getenv('MEVZUAT_AUDIT_DIR')
  if audit_dir:
   from pathlib import Path
   target=Path(audit_dir);target.mkdir(parents=True,exist_ok=True);(target/(request_id+'.json')).write_text(json.dumps({'completion':completion,'trace':trace,'validation':result},ensure_ascii=False,indent=2))
  trace.update(llm_http_source_ids=[s['document_id'] for s in sources],llm_sent_source_ids=[c['source_id'] for c in completion['catalog']],prompt_sha256=completion['prompt_sha256'],context_sha256=completion['context_sha256'],generation_number=completion['generation_number'],inference_passes=completion.get('inference_passes',1),provider=completion['provider_info'],llm_seconds=completion['seconds'],total_seconds=time.perf_counter()-start,mlx_peak_bytes=completion['mlx_peak_bytes'],backend_rss_bytes=psutil.Process().memory_info().rss)
  log.info('CHAT_COMPLETE request=%s provider=mlx model=%s generation=%s status=%s context=%s',request_id,completion['provider_info']['model'],completion['generation_number'],result['status'],trace['llm_sent_source_ids'])
  # Raw model draft stays in the worker logs/test trace. It is not a public answer field.
  return {'request_id':request_id,**result,'sources':[ui_source(s) for s in result['sources']],'trace':trace}
 finally:gate.release()
