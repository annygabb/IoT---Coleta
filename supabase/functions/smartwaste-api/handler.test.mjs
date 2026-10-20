import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

let handler;
globalThis.Deno={serve(fn){handler=fn;},env:{get(name){return name==='SUPABASE_URL'?'https://database.test':'server-only';}}};
let source=await readFile(new URL('./index.ts',import.meta.url),'utf8');
source=source.replace("'./core.mjs'",JSON.stringify(new URL('./core.mjs',import.meta.url).href));
await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));

const event=()=>({event_id:'e1',run_id:'r1',device_id:'d1',bin_id:'BIN-01',sequence:1,simulated_at:'2026-10-19T08:00:00Z',emitted_at:'2026-10-19T08:00:00Z',fill_pct:95,temperature_c:25,battery_pct:90,operational_state:'CRITICA',sensor_status:'ONLINE',firmware_version:'1.0'});
const message=()=>({versao:'1.0',id_mensagem:'550e8400-e29b-41d4-a716-446655440000',dispositivo:'solo-01',tipo:'telemetria',timestamp:'2026-10-19T10:00:00Z',local:{site:'fazenda'},medidas:[{grandeza:'umidade_solo',valor:23.5,unidade:'%'}]});
const request=(action,body,token='x'.repeat(48))=>new Request('https://cloud.test/'+action,{method:'POST',headers:{'x-fog-token':token,'content-type':'application/json'},body:JSON.stringify(body)});

test('credencial inválida não consulta banco',async(t)=>{
 const old=globalThis.fetch;t.after(()=>globalThis.fetch=old);
 globalThis.fetch=()=>{throw Error('não deve consultar banco');};
 assert.equal((await handler(request('ingest',{events:[event()]},'bad'))).status,401);
});
test('handler grava válidos e informa inválidos separadamente',async(t)=>{
 const old=globalThis.fetch;t.after(()=>globalThis.fetch=old);let saved;
 globalThis.fetch=async(url,options)=>{
  if(url.includes('smartwaste_credentials'))return Response.json([{fog_id:'fog-1'}]);
  if(options?.method==='POST'){saved=JSON.parse(options.body);return new Response(null,{status:201});}
  return Response.json(saved||[]);
 };
 const response=await handler(request('ingest',{events:[event(),{...event(),event_id:'bad',battery_pct:-1}]}));
 assert.equal(response.status,200);const body=await response.json();
 assert.deepEqual(body.acknowledged,['e1']);assert.equal(body.rejected[0].event_id,'bad');assert.equal(saved.length,1);
});
test('falha de armazenamento não emite confirmação',async(t)=>{
 const old=globalThis.fetch;t.after(()=>globalThis.fetch=old);
 globalThis.fetch=async(url)=>url.includes('smartwaste_credentials')?Response.json([{fog_id:'fog-1'}]):new Response(null,{status:503});
 const response=await handler(request('ingest',{events:[event()]}));
 assert.equal(response.status,503);assert.equal((await response.json()).acknowledged,undefined);
});
test('handler canônico grava sensor rural com identidade da fog autenticada',async(t)=>{
 const old=globalThis.fetch;t.after(()=>globalThis.fetch=old);let saved;
 globalThis.fetch=async(url,options)=>{
  if(url.includes('smartwaste_credentials'))return Response.json([{fog_id:'fog-1'}]);
  if(options?.method==='POST'){saved=JSON.parse(options.body);return new Response(null,{status:201});}
  return Response.json(saved||[]);
 };
 const response=await handler(request('platform-ingest',{messages:[message()]}));
 assert.equal(response.status,200);assert.deepEqual((await response.json()).acknowledged,[message().id_mensagem]);
 assert.equal(saved[0].fog_id,'fog-1');assert.equal(saved[0].payload.dispositivo,'solo-01');
});
test('handler legado não confirma ID cujo conteúdo persistido é diferente',async(t)=>{
 const old=globalThis.fetch;t.after(()=>globalThis.fetch=old);
 globalThis.fetch=async(url,options)=>{
  if(url.includes('smartwaste_credentials'))return Response.json([{fog_id:'fog-1'}]);
  if(options?.method==='POST')return new Response(null,{status:201});
  return Response.json([{...event(),fill_pct:10}]);
 };
 const response=await handler(request('ingest',{events:[event()]}));const body=await response.json();
 assert.deepEqual(body.acknowledged,[]);assert.equal(body.rejected[0].error,'ID_CONFLICT');
});
