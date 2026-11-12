"""Use the same source-selection/verification prompts through local Ollama."""
import hashlib,json,os,time
from fastapi import FastAPI,HTTPException
from huggingface_hub import snapshot_download
import requests
from transformers import AutoTokenizer
from backend.grounding import generate_grounded

app=FastAPI()
BASE='Qwen/Qwen3-4B-Instruct-2507'
MODEL='qwen3:4b-instruct-2507-q4_K_M'
URL=os.environ.get('OLLAMA_URL','http://host.docker.internal:11434')
tokenizer=None
@app.get('/health')
def health():
    try:
        response=requests.get(URL+'/api/tags',timeout=3);response.raise_for_status()
        item=next(m for m in response.json()['models'] if m['name']==MODEL and m['digest'].startswith('0edcdef34593'))
    except (requests.RequestException,KeyError,StopIteration,ValueError) as exc:
        raise HTTPException(503,'Yerel Ollama veya beklenen model kullanılamıyor') from exc
    return dict(ready=True,provider='ollama',base_model=BASE,model=MODEL,revision=item['digest'])
@app.post('/generate')
def generate(req:dict):
    global tokenizer
    info=health()
    if tokenizer is None:
        path=snapshot_download('mlx-community/Qwen3-4B-Instruct-2507-4bit',revision='50d427756c6b1b2fe0c0a10f67fbda1fc8e82c1b',allow_patterns=['*.json','*.txt','*.jinja'])
        tokenizer=AutoTokenizer.from_pretrained(path)
    started=time.monotonic();calls=0
    def infer(prompt,limit):
        nonlocal calls
        calls+=1
        r=requests.post(URL+'/api/generate',json=dict(model=MODEL,prompt=prompt,raw=True,stream=False,options=dict(temperature=0,num_ctx=8192,num_predict=limit)),timeout=110)
        r.raise_for_status()
        return r.json()['response']
    sources=req['sources']
    try:
        result=generate_grounded(req['question'],sources,tokenizer,infer,req.get('retrieval_question'))
    except ValueError as exc:
        if str(exc)=='context_budget_exceeded':raise HTTPException(413,str(exc)) from exc
        raise
    prompt=result.pop('prompt')
    return dict(**result,request_id=req['request_id'],inference_passes=calls,generation_number=None,mlx_peak_bytes=None,seconds=time.monotonic()-started,provider_info=info,prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),context_sha256=hashlib.sha256(json.dumps(sources,sort_keys=True,ensure_ascii=False).encode()).hexdigest())
