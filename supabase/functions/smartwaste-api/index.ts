import {partitionBatch,partitionCanonical,historyParams,publicRow,utcTimestamp} from './core.mjs';
const reply=(status,body)=>new Response(JSON.stringify(body),{status,headers:{'content-type':'application/json','cache-control':'no-store'}});
const legacyFields=['event_id','run_id','device_id','bin_id','sequence','simulated_at','emitted_at','fill_pct','temperature_c','battery_pct','operational_state','sensor_status','firmware_version'];
const legacyIdentity=row=>legacyFields.map(key=>['simulated_at','emitted_at'].includes(key)?utcTimestamp(row[key]):row[key]);
const stable=value=>JSON.stringify(value,(_key,item)=>item&&typeof item==='object'&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(k=>[k,item[k]])):item);
async function readBody(req){
 const reader=req.body?.getReader();if(!reader)throw Error('body required');
 let size=0;const chunks=[];
 while(true){const {value,done}=await reader.read();if(done)break;size+=value.length;if(size>262144){await reader.cancel();throw Error('BODY_TOO_LARGE');}chunks.push(value);}
 const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
Deno.serve(async(req)=>{
 const url=new URL(req.url);const action=url.pathname.split('/').filter(Boolean).pop();
 if(req.method==='GET'&&action==='health')return reply(200,{status:'ok',service:'SmartWaste cloud',version:'1.1',synthetic_data:true});
 if(!['ingest','history','platform-ingest','platform-history'].includes(action))return reply(404,{error:'not found'});
 const write=action==='ingest'||action==='platform-ingest';
 if((write&&req.method!=='POST')||(!write&&req.method!=='GET'))return reply(405,{error:'method not allowed'});
 const secret=req.headers.get('x-fog-token')||'';
 if(secret.length<32||secret.length>256)return reply(401,{error:'invalid fog credentials'});
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(secret)))).map(x=>x.toString(16).padStart(2,'0')).join('');
 const base=Deno.env.get('SUPABASE_URL');const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
 const headers={apikey:key,Authorization:'Bearer '+key,'content-type':'application/json'};
 try{
  const auth=await fetch(base+'/rest/v1/smartwaste_credentials?token_hash=eq.'+hash+'&enabled=eq.true&select=fog_id',{headers});
  if(!auth.ok)return reply(503,{error:'identity store unavailable'});
  const identities=await auth.json();if(identities.length!==1)return reply(401,{error:'invalid fog credentials'});
  const fogId=identities[0].fog_id,canonical=action.startsWith('platform-');
  if(write){
   let result;
   try{const body=await readBody(req);result=canonical?partitionCanonical(body,fogId):partitionBatch(body,fogId);}
   catch(e){return reply(e.message==='BODY_TOO_LARGE'?413:400,{error:String(e.message)});}
   const {rows,rejected}=result;
   const table=canonical?'smartwaste_canonical_events':'smartwaste_events',id=canonical?'id_mensagem':'event_id';
   if(rows.length){
    const saved=await fetch(base+'/rest/v1/'+table+'?on_conflict=fog_id,'+id,{method:'POST',headers:{...headers,Prefer:'resolution=ignore-duplicates,return=minimal'},body:JSON.stringify(rows)});
    if(!saved.ok)return reply(503,{error:'storage unavailable; retain events locally'});
   }
   let acknowledged=rows.map(row=>row[id]);
   if(rows.length){
    // A leitura após escrita também detecta duas requisições concorrentes com mesmo UUID e conteúdo distinto.
    const params=new URLSearchParams({fog_id:'eq.'+fogId,[id]:'in.('+acknowledged.join(',')+')',select:canonical?'id_mensagem,payload':legacyFields.join(','),limit:'100'});
    const found=await fetch(base+'/rest/v1/'+table+'?'+params,{headers});
    if(!found.ok)return reply(503,{error:'confirmation unavailable; retain messages locally'});
    const stored=await found.json();const persisted=new Map(stored.map(row=>[row[id],canonical?row.payload:legacyIdentity(row)]));
    acknowledged=[];
    for(const row of rows){
     if(!persisted.has(row[id]))return reply(503,{error:'confirmation incomplete; retain messages locally'});
     if(stable(canonical?row.payload:legacyIdentity(row))!==stable(persisted.get(row[id])))rejected.push({[id]:row[id],error:'ID_CONFLICT',retryable:false});
     else acknowledged.push(row[id]);
    }
   }
   return reply(200,{acknowledged,rejected,count:acknowledged.length});
  }
  let params;try{params=historyParams(url,fogId,canonical);}catch(e){return reply(400,{error:e.message});}
  const found=await fetch(base+'/rest/v1/'+(canonical?'smartwaste_canonical_events':'smartwaste_events')+'?'+params,{headers});
  if(!found.ok)return reply(503,{error:'history unavailable'});
  const rows=await found.json();return reply(200,canonical?{messages:rows,limit:+params.get('limit'),offset:+params.get('offset')}:{events:rows.map(publicRow),limit:+params.get('limit'),offset:+params.get('offset')});
 }catch{return reply(503,{error:'cloud temporarily unavailable; retain events locally'});}
});
