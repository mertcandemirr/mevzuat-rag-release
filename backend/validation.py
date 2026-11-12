"""Strict model-selected, verbatim evidence. Never display unchecked model prose."""
import json,re

def validate(completion,sources,max_evidence=4):
 raw=completion['raw_completion'].strip()
 if raw.startswith('```'):raw=re.sub(r'^```(?:json)?\s*|\s*```$','',raw)
 try:result=json.loads(raw)
 except (ValueError,TypeError):return {'status':'inceleme_gerekli','answer':None,'sources':[],'issues':['invalid_model_json']}
 if not isinstance(result,dict) or not isinstance(result.get('evidence'),list) or type(result.get('insufficient')) is not bool:return {'status':'inceleme_gerekli','answer':None,'sources':[],'issues':['invalid_model_schema']}
 if result['insufficient']:return {'status':'yeterli_kaynak_yok','answer':None,'sources':[],'issues':['model_abstained']}
 catalog={c['evidence_id']:c for c in completion['catalog']};provided={s['document_id']:s for s in sources};chosen=[];issues=[]
 if not 1<=len(result['evidence'])<=max_evidence:issues.append('invalid_evidence_count')
 for key in result['evidence']:
  if not isinstance(key,str) or key not in catalog:issues.append('unknown_evidence_id');continue
  entry=catalog[key];s=provided.get(entry['source_id'])
  if s is None or entry['text']!=s['text']:issues.append('source_content_mismatch');continue
  if s.get('status')!='official_snapshot_matched' or not s.get('source_url'):issues.append('source_not_verified');continue
  if s['document_id'] not in [x['document_id'] for x in chosen]:chosen.append(s)
 if issues:return {'status':'inceleme_gerekli','answer':None,'sources':[],'issues':issues}
 # No free-form numerical/date claim is admitted; full provision text is copied exactly.
 answer='\n\n'.join(f"{s['law_number']} sayılı Kanun · Madde {s['article_number']} — {s['article_title']}\n{s['text']} [{s['document_id']}]" for s in chosen)
 return {'status':'kaynak_alintisi_dogrulandi','answer':answer,'sources':chosen,'issues':[],'verification':{'source_ids_valid':True,'quote_supported':True,'numbers_dates':'verbatim_source_only','semantic_legal_correctness':'NOT_RUN','answer_mode':'qwen_selected_verbatim_evidence'}}


def validate_quotes(completion,sources,question=''):
 # A broad enumeration question must not lose a sibling clause selected into context.
 expanded=[]
 try:
  draft=json.loads(completion['raw_completion']);keys=draft.get('evidence',[])
  for key in completion.get('selection_expansion',[]):
   if key not in keys:keys.append(key)
  if re.search(r'(?:hangi\s+(?:hak|koşul|şart|hâl|hal|durum)|\b(?:tüm|bütün)\b|nelerdir|ne kadar)',question.casefold()):
   by_id={s['document_id']:s for s in sources};catalog=completion['catalog'];selected=[by_id[e['source_id']] for e in catalog if e['evidence_id'] in keys and e['source_id'] in by_id]
   groups={(s['parent_id'],s.get('paragraph_number')) for s in selected if s.get('clause')}
   for parent,paragraph in groups:
    labels=[by_id[e['source_id']].get('clause') for e in catalog if e['source_id'] in by_id and by_id[e['source_id']]['parent_id']==parent and by_id[e['source_id']].get('paragraph_number')==paragraph and by_id[e['source_id']].get('clause')]
    if len(set(labels))!=len(labels):continue
    if sum(s.get('clause') is not None and s['parent_id']==parent and s.get('paragraph_number')==paragraph for s in selected)<2:continue
    siblings=[e for e in catalog if e['source_id'] in by_id and by_id[e['source_id']]['parent_id']==parent and by_id[e['source_id']].get('paragraph_number')==paragraph and (by_id[e['source_id']].get('clause') or by_id[e['source_id']].get('source_paragraph_index')==1)]
    for entry in siblings:
     if entry['evidence_id'] not in keys:keys.append(entry['evidence_id']);expanded.append(entry['source_id'])
  completion={**completion,'raw_completion':json.dumps({**draft,'evidence':keys})}
 except (ValueError,TypeError,KeyError):pass
 result=validate(completion,sources,max_evidence=16)
 if result['answer'] is None:return result
 try:
  check=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',(completion.get('verifier_raw') or '').strip()))
  if check.get('supported') is not True or check.get('answers_question') is not True:raise ValueError('relevance')
 except (ValueError,TypeError,AttributeError):return {'status':'inceleme_gerekli','answer':None,'sources':[],'issues':['model_source_relevance_check_failed']}
 result['verification'].update(list_completion_added_source_ids=expanded,preamble_expansion=completion.get('selection_expansion',[]),relevance_check='same_qwen_second_pass',answer_mode='qwen_selected_verbatim_evidence',semantic_legal_correctness='NOT_INDEPENDENTLY_REVIEWED')
 return result
