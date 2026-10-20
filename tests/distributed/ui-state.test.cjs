const test=require('node:test'),assert=require('node:assert/strict'),ui=require('../../apps/distributed/ui-state.js');
test('desconexão mostra fila e continuidade local',()=>{const x=ui.cloud({cloud_link_enabled:false,pending_cloud:64});assert.equal(x.tone,'warning');assert.match(x.detail,/64/);assert.equal(x.busy,false)});
test('reconexão não é confirmada por um envio antigo',()=>{const x=ui.cloud({cloud_link_enabled:true,cloud_status:'CONNECTING',last_sync:'2026-10-19T08:00:00Z'});assert.equal(x.tone,'loading');assert.equal(x.busy,true)});
test('apenas confirmação nova libera estado conectado',()=>assert.equal(ui.cloud({cloud_status:'CONNECTED',pending_cloud:32}).tone,'success'));
test('erro não aparece como conectado',()=>assert.equal(ui.cloud({cloud_status:'ERROR',cloud_error:'401'}).tone,'error'));
test('instalação aguarda ACK e snapshot novo',()=>{const x=ui.canary({status:'IDLE'},{},{id:'a',version:'2.0'});assert.equal(x.busy,true);assert.equal(x.resolved,false)});
test('ACK rejeitado mostra erro',()=>{const x=ui.canary({},{a:{status:'REJECTED',error:'indisponível'}},{id:'a',version:'2.0'});assert.equal(x.failed,true);assert.equal(x.detail,'indisponível')});
test('observação mostra versão e carregamento',()=>{const x=ui.canary({status:'OBSERVING',version:'2.0',campaign_id:'a'},{a:{status:'APPLIED'}},{id:'a',version:'2.0'});assert.equal(x.resolved,true);assert.equal(x.busy,true);assert.match(x.title,/2.0/)});
test('aprovação mantém versão por sensor',()=>{const x=ui.canary({status:'READY_FOR_NEXT_WAVE',version:'2.0',versions:{'BIN-01':'2.0'}});assert.equal(x.tone,'success');assert.match(x.summary,/v1.0: 31/);assert.match(x.summary,/v2.0: 1/)});
test('rollback mostra versão efetiva anterior',()=>{const x=ui.canary({status:'ROLLBACK',version:'2.0-faulty',versions:{'BIN-01':'1.0'}});assert.equal(x.busy,false);assert.match(x.summary,/v1.0: 32/);assert.doesNotMatch(x.summary,/faulty/)});

test('campanha concluída antes da próxima consulta não trava carregamento',()=>{const x=ui.canary({status:'ROLLBACK',version:'2.0-faulty',campaign_id:'a'},{a:{status:'APPLIED'}},{id:'a',version:'2.0-faulty'});assert.equal(x.resolved,true);assert.equal(x.busy,false)});
test('general commands resolve only by matching ACK and explain delays',()=>{
 const {command}=require('../../apps/distributed/ui-state.js');
 const p={id:'x',action:'WEATHER',at:0};
 assert.equal(command(p,{other:{status:'APPLIED'}},16000).resolved,false);
 assert.match(command(p,{},16000).text,/Ainda sem confirmação/);
 assert.equal(command(p,{x:{status:'APPLIED'}},500).resolved,true);
 assert.match(command(p,{x:{status:'REJECTED',error:'inválido'}},500).text,/rejeitou/);
});
