export type Source={id:string;law:string;article:string;title:string;lawTitle:string;text:string;url:string;snapshot:string;paragraph_number?:string|null;clause?:string|null;article_kind?:string;legal_status?:string};
export type ChatResponse={request_id:string;status:string;answer:string|null;sources:Source[];issues?:string[];verification?:{answer_mode?:string};trace?:{total_seconds?:number}};
export type Health={ready:boolean;embedding_model:string;embedding_dimension:number;corpus?:{laws:number;articles:number;chunks:number};provider:{ready:boolean;base_model:string;provider:string}};
export class ApiError extends Error{constructor(message:string,public kind:'connection'|'timeout'|'busy'|'request'|'server'){super(message)}}
export async function health(signal?:AbortSignal):Promise<Health>{const r=await fetch('/api/health',{signal});if(!r.ok)throw new ApiError('Yerel yanıt servisine bağlanılamadı.','connection');const data=await r.json();if(!data.ready||!data.provider?.ready)throw new ApiError('Model henüz hazır değil.','connection');return data;}
export async function ask(question:string,controller:AbortController):Promise<ChatResponse>{
 const timeout=setTimeout(()=>controller.abort(),120000);
 try{
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question}),signal:controller.signal});
  if(!r.ok){if(r.status===503)throw new ApiError('RAG bağlantısı bekleniyor. Yerel Qwen3 modeline ulaşılamıyor; yanıt üretilmedi.','connection');if(r.status===429)throw new ApiError('Yerel model şu anda meşgul. Biraz sonra yeniden deneyin.','busy');if(r.status===422||r.status===413)throw new ApiError('Soru veya kaynak bağlamı sınırı aşıldı. Sorunuzu kısaltarak yeniden deneyin.','request');throw new ApiError('Yanıt servisi isteği tamamlayamadı. Yanıt üretilmedi.','server');}
  const data:ChatResponse=await r.json();
  if(typeof data.status!=='string'||!Array.isArray(data.sources)||typeof data.request_id!=='string')throw new ApiError('Sunucudan geçersiz yanıt alındı.','server');
  // Never render a draft supplied alongside a rejected verification status.
  if(!['kaynak_alintisi_dogrulandi','kaynak_destegi_kontrol_edildi'].includes(data.status)){data.answer=null;data.sources=[];}
  return data;
 }catch(error){if(error instanceof ApiError)throw error;if(controller.signal.aborted)throw new ApiError('Yanıt zaman aşımına uğradı. Yerel işlem devam ediyor olabilir; yeniden denemeden önce bekleyin.','timeout');throw new ApiError('RAG bağlantısı bekleniyor. Yerel backend erişilemiyor; bağlantıyı kontrol edin.','connection');}finally{clearTimeout(timeout);}
}
