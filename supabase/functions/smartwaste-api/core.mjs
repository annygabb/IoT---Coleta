const fields=['event_id','run_id','device_id','bin_id','sequence','simulated_at','emitted_at','fill_pct','temperature_c','battery_pct','operational_state','sensor_status','firmware_version'];
export function publicRow(row){return Object.fromEntries([...fields,'received_at','fog_id'].filter(k=>row[k]!==undefined).map(k=>[k,row[k]]));}
export function validateBatch(body,fogId){
 if(!body||!Array.isArray(body.events)||body.events.length<1||body.events.length>100)throw Error('events must contain 1 to 100 items');
 const seen=new Set();
 return body.events.map(e=>{
  if(!e||typeof e!=='object'||Array.isArray(e))throw Error('invalid event');
  for(const k of ['event_id','run_id','device_id','bin_id','firmware_version'])if(typeof e[k]!=='string'||!/^[-\w.]{1,100}$/.test(e[k]))throw Error('invalid '+k);
  if(seen.has(e.event_id))throw Error('duplicate event_id in batch');seen.add(e.event_id);
  if(!Number.isSafeInteger(e.sequence)||e.sequence<0)throw Error('invalid sequence');
  for(const [k,min,max] of [['fill_pct',0,120],['temperature_c',-50,150],['battery_pct',0,100]])if(typeof e[k]!=='number'||!Number.isFinite(e[k])||e[k]<min||e[k]>max)throw Error('invalid '+k);
  for(const k of ['simulated_at','emitted_at'])if(typeof e[k]!=='string'||!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(e[k])||!Number.isFinite(Date.parse(e[k])))throw Error('invalid '+k);
  for(const k of ['simulated_at','emitted_at']){const parts=/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/.exec(e[k]);if(!parts)throw Error('invalid '+k);const [y,m,d,h,minute,sec]=parts.slice(1).map(Number);const check=new Date(Date.UTC(y,m-1,d));if(check.getUTCFullYear()!==y||check.getUTCMonth()!==m-1||check.getUTCDate()!==d||h>23||minute>59||sec>59)throw Error('invalid '+k);}
  if(!['NORMAL','ATENCAO','ALTA','CRITICA','TRANSBORDO','EM_COLETA'].includes(e.operational_state))throw Error('invalid operational_state');
  if(!['ONLINE','STALE','OFFLINE','FAULTY'].includes(e.sensor_status))throw Error('invalid sensor_status');
  return {...Object.fromEntries(fields.map(k=>[k,e[k]])),fog_id:fogId};
 });
}


// Partição por mensagem, preservando a API de validação legada para consumidores existentes.
export function partitionBatch(body,fogId){
 if(!body||!Array.isArray(body.events)||body.events.length<1||body.events.length>100)throw Error('events must contain 1 to 100 items');
 const rows=[],rejected=[],seen=new Set();
 body.events.forEach((event,index)=>{
  try{
   const row=validateBatch({events:[event]},fogId)[0];
   if(seen.has(row.event_id))throw Error('duplicate event_id in batch');
   seen.add(row.event_id);rows.push(row);
  }catch(e){rejected.push({index,event_id:typeof event?.event_id==='string'?event.event_id:null,error:e.message,retryable:false});}
 });
 // IDs repetidos no mesmo lote são recusados em conjunto para não emitir resultados conflitantes.
 const conflicts=new Set(rejected.filter(r=>r.error==='duplicate event_id in batch').map(r=>r.event_id));
 return {rows:rows.filter(r=>!conflicts.has(r.event_id)),rejected};
}

export function utcTimestamp(value){
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/.test(value))throw Error('invalid timestamp');
 const [y,m,d,h,minute,second]=value.slice(0,19).split(/[-T:]/).map(Number);
 const calendar=new Date(0);calendar.setUTCFullYear(y,m-1,d);calendar.setUTCHours(0,0,0,0);
 if(y<1||calendar.getUTCFullYear()!==y||calendar.getUTCMonth()!==m-1||calendar.getUTCDate()!==d||h>23||minute>59||second>59)throw Error('invalid timestamp');
 const date=new Date(value);if(!Number.isFinite(date.getTime())||date.getUTCFullYear()<1||date.getUTCFullYear()>9999)throw Error('invalid timestamp');
 const fraction=(value.match(/\.(\d+)/)?.[1]||'').padEnd(6,'0');
 return date.toISOString().slice(0,-1)+fraction.slice(3)+'Z';
}
const identifier=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
function exactKeys(obj,allowed){if(!obj||typeof obj!=='object'||Array.isArray(obj)||Object.keys(obj).some(k=>!allowed.includes(k)))throw Error('invalid fields');}
export function validateCanonical(message){
 exactKeys(message,['versao','id_mensagem','dispositivo','tipo','timestamp','via','local','medidas']);
 if(message.versao!=='1.0'||message.tipo!=='telemetria'||!identifier(message.dispositivo))throw Error('invalid version, type or device');
 if(typeof message.id_mensagem!=='string'||!(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/).test(message.id_mensagem))throw Error('invalid id_mensagem');
 if(!Array.isArray(message.medidas)||message.medidas.length<1||message.medidas.length>32)throw Error('invalid measures');
 const seen=new Set();
 const medidas=message.medidas.map(m=>{
  exactKeys(m,['grandeza','valor','unidade']);
  if(!identifier(m.grandeza)||typeof m.valor!=='number'||!Number.isFinite(m.valor)||typeof m.unidade!=='string'||!(/^[!-~]{1,32}$/).test(m.unidade)||seen.has(m.grandeza))throw Error('invalid measure');
  seen.add(m.grandeza);return {...m};
 });
 const result={versao:'1.0',id_mensagem:message.id_mensagem,dispositivo:message.dispositivo,tipo:'telemetria',timestamp:utcTimestamp(message.timestamp),medidas};
 if(message.via!=null){if(!identifier(message.via))throw Error('invalid gateway');result.via=message.via;}
 if(message.local!=null){
  exactKeys(message.local,['site','area']);if(!identifier(message.local.site)||(message.local.area!=null&&!identifier(message.local.area)))throw Error('invalid location');
  result.local={site:message.local.site};if(message.local.area!=null)result.local.area=message.local.area;
 }
 return result;
}
export function partitionCanonical(body,fogId){
 if(!body||!Array.isArray(body.messages)||body.messages.length<1||body.messages.length>100)throw Error('messages must contain 1 to 100 items');
 const rows=[],rejected=[],seen=new Set();
 body.messages.forEach((m,index)=>{
  try{
   const message=validateCanonical(m);if(seen.has(message.id_mensagem))throw Error('duplicate id_mensagem in batch');seen.add(message.id_mensagem);
   rows.push({fog_id:fogId,id_mensagem:message.id_mensagem,device_id:message.dispositivo,measured_at:message.timestamp,payload:message});
  }catch(e){rejected.push({index,id_mensagem:typeof m?.id_mensagem==='string'?m.id_mensagem:null,error:e.message,retryable:false});}
 });
 const conflicts=new Set(rejected.filter(r=>r.error==='duplicate id_mensagem in batch').map(r=>r.id_mensagem));
 return {rows:rows.filter(r=>!conflicts.has(r.id_mensagem)),rejected};
}
export function historyParams(url,fogId,canonical=false){
 const q=url.searchParams,limit=q.get('limit')||'100',offset=q.get('offset')||'0',order=q.get('order')||'desc';
 if(!/^\d+$/.test(limit)||+limit<1||+limit>1000||!/^\d+$/.test(offset)||!Number.isSafeInteger(+offset)||!['asc','desc'].includes(order))throw Error('invalid pagination');
 const time=canonical?'measured_at':'simulated_at',id=canonical?'id_mensagem':'event_id';
 const params=new URLSearchParams({fog_id:'eq.'+fogId,select:canonical?'id_mensagem,device_id,measured_at,received_at,payload':fields.concat('received_at','fog_id').join(','),order:time+'.'+order+','+id+'.'+order,limit,offset});
 for(const field of ['run_id','device_id'])if(q.has(field)){
  if(canonical&&field==='run_id')throw Error('run_id belongs to legacy history');
  const v=q.get(field);if(!/^[-\w.]{1,100}$/.test(v))throw Error('invalid '+field);params.set(field,'eq.'+v);
 }
 const start=q.has('start')?utcTimestamp(q.get('start')):null,end=q.has('end')?utcTimestamp(q.get('end')):null;
 if(start&&end&&start>end)throw Error('invalid interval');
 if(start)params.append(time,'gte.'+start);if(end)params.append(time,'lte.'+end);
 return params;
}
