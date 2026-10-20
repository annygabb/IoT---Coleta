import test from 'node:test';import assert from 'node:assert/strict';import{validateBatch,publicRow,partitionBatch,validateCanonical,partitionCanonical,historyParams}from'./core.mjs';
const event=()=>({event_id:'e1',run_id:'r1',device_id:'d1',bin_id:'BIN-01',sequence:1,simulated_at:'2026-10-19T08:00:00Z',emitted_at:'2026-10-19T08:00:00Z',fill_pct:95,temperature_c:25,battery_pct:90,operational_state:'CRITICA',sensor_status:'ONLINE',firmware_version:'1.0'});
test('identidade vem da autenticação',()=>assert.equal(validateBatch({events:[{...event(),fog_id:'invasor'}]},'fog-df-01')[0].fog_id,'fog-df-01'));
test('faixas e valores não finitos',()=>{for(const fill of [-1,121,NaN,Infinity])assert.throws(()=>validateBatch({events:[{...event(),fill_pct:fill}]},'fog'))});
test('estados operacionais separados da saúde',()=>assert.throws(()=>validateBatch({events:[{...event(),sensor_status:'CRITICA'}]},'fog')));
test('lotes vazios, longos e duplicados',()=>{for(const events of [[],Array(101).fill(event()),[event(),event()]])assert.throws(()=>validateBatch({events},'fog'))});
test('transbordo permitido e campos extras omitidos',()=>{const row=validateBatch({events:[{...event(),fill_pct:115,secret:'x'}]},'fog')[0];assert.equal(row.fill_pct,115);assert.equal(row.secret,undefined);assert.equal(publicRow({...row,token_hash:'x'}).token_hash,undefined)});
test('data impossível é rejeitada',()=>assert.throws(()=>validateBatch({events:[{...event(),emitted_at:'2026-02-30T00:00:00Z'}]},'fog')));

test('lote misto não bloqueia registros válidos',()=>{
 const result=partitionBatch({events:[event(),{...event(),event_id:'bad',battery_pct:-1},{...event(),event_id:'e2'}]},'fog');
 assert.deepEqual(result.rows.map(x=>x.event_id),['e1','e2']);assert.equal(result.rejected[0].event_id,'bad');assert.equal(result.rejected[0].retryable,false);
});
const message=()=>({versao:'1.0',id_mensagem:'550e8400-e29b-41d4-a716-446655440000',dispositivo:'solo-01',tipo:'telemetria',timestamp:'2026-10-19T10:00:00Z',local:{site:'fazenda'},medidas:[{grandeza:'umidade_solo',valor:23.5,unidade:'%'}]});
test('contrato canônico aceita sensor rural e normaliza UTC',()=>{
 const a=message();a.timestamp='2026-10-19T07:00:00-03:00';assert.equal(validateCanonical(a).timestamp,'2026-10-19T10:00:00.000000Z');
});
test('contrato canônico rejeita erros de tipo, versão, data e duplicação de grandeza',()=>{
 for(const patch of [{versao:'2.0'},{timestamp:'2026-02-30T00:00:00Z'},{timestamp:'2026-10-19T10:00:00'},
   {id_mensagem:'bad'},{medidas:[{grandeza:'umidade_solo',valor:true,unidade:'%'}]},
   {medidas:[...message().medidas,...message().medidas]},{unknown:'field'}])assert.throws(()=>validateCanonical({...message(),...patch}));
});
test('canônico mantém válidos e rejeita somente a mensagem ruim',()=>{
 const r=partitionCanonical({messages:[message(),{...message(),id_mensagem:'550e8400-e29b-41d4-a716-446655440001',versao:'99'}]},'fog');
 assert.equal(r.rows.length,1);assert.equal(r.rejected.length,1);assert.equal(r.rows[0].fog_id,'fog');
});
test('consulta histórica usa medição com filtros e limite',()=>{
 const p=historyParams(new URL('https://example.test/history?device_id=d1&start=2026-10-18T00:00:00Z&limit=20&offset=5&order=asc'),'fog');
 assert.equal(p.get('order'),'simulated_at.asc,event_id.asc');assert.equal(p.get('device_id'),'eq.d1');assert.equal(p.get('offset'),'5');
 assert.throws(()=>historyParams(new URL('https://example.test/history?start=bad'),'fog'));
 assert.throws(()=>historyParams(new URL('https://example.test/history?limit=999999'),'fog'));
});
test('UTC fora dos anos 1 a 9999 é recusado por mensagem',()=>{
 for(const timestamp of ['0000-01-01T00:00:00Z','0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00']){
  const r=partitionCanonical({messages:[{...message(),timestamp}]},'fog');assert.equal(r.rows.length,0);assert.equal(r.rejected.length,1);
 }
});
