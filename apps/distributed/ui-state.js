/* Modelos de apresentação puros, usados pelo navegador e pelos testes Node. */
(function(root){
function cloud(a={},pending=null){
 const count=Number(a.pending_cloud||0);
 if(pending!==null)return{title:pending?'Conectando à nuvem…':'Desconectando da nuvem…',detail:'Aguardando confirmação da fog.',tone:'loading',busy:true};
 if(a.cloud_link_enabled===false)return{title:'Nuvem desconectada',detail:count+' leituras pendentes. A coleta local continua. Um lote já em andamento ainda pode concluir.',tone:'warning',busy:false};
 if(a.cloud_status==='ERROR')return{title:'Erro na conexão',detail:'O envio não foi confirmado. As leituras permanecem na fila. '+(a.cloud_error||''),tone:'error',busy:false};
 if(a.cloud_status==='CONNECTED')return{title:count?'Conectada · sincronizando':'Conectada · envio confirmado',detail:'Última confirmação: '+(a.last_sync?new Date(a.last_sync).toLocaleTimeString('pt-BR'):'—')+'. '+count+' leituras em trânsito.',tone:'success',busy:!!a.sync_in_progress};
 return{title:'Reconectando à nuvem…',detail:'Enlace habilitado. Aguardando uma nova confirmação de gravação; '+count+' leituras pendentes.',tone:'loading',busy:true};
}
function versions(ca={}){
 const counts={};
 for(let i=1;i<=32;i++){const id='BIN-'+String(i).padStart(2,'0'),v=ca.versions?.[id]||'1.0';counts[v]=(counts[v]||0)+1}
 return Object.entries(counts).sort(([a],[b])=>a.localeCompare(b)).map(([v,n])=>'v'+v+': '+n+' sensores').join(' · ');
}
function canary(ca={},results={},pending=null){
 const summary=versions(ca),base={summary,resolved:false,failed:false};
 if(pending){
  const ack=results[pending.id];
  if(ack?.status==='REJECTED')return{...base,title:'Campanha não iniciada',detail:ack.error||'A edge rejeitou o comando.',tone:'error',busy:false,resolved:true,failed:true};
  if(!(['APPLIED','DUPLICATE'].includes(ack?.status)&&ca.campaign_id===pending.id&&ca.version===pending.version&&['OBSERVING','READY_FOR_NEXT_WAVE','ROLLBACK'].includes(ca.status)))
   return{...base,title:'Instalando versão '+pending.version+'…',detail:'Comando enviado. Aguardando confirmação da edge e a leitura da versão em uso.',tone:'loading',busy:true};
  base.resolved=true;
 }
 if(ca.status==='OBSERVING')return{...base,title:'Observando versão '+ca.version+'…',detail:'Coletando amostras durante pelo menos 10 segundos. '+(ca.errors||0)+' erros em '+(ca.reports||0)+' relatos do grupo de teste.',tone:'loading',busy:true};
 if(ca.status==='READY_FOR_NEXT_WAVE')return{...base,title:'Versão '+ca.version+' aprovada',detail:'O grupo concluiu a observação e mantém a versão testada. Uma próxima onda é manual.',tone:'success',busy:false};
 if(ca.status==='ROLLBACK')return{...base,title:'Reversão concluída',detail:'A versão '+ca.version+' apresentou falhas. Os sensores do teste voltaram às versões anteriores.',tone:'warning',busy:false};
 return{...base,title:'Versão inicial em operação',detail:'Escolha uma versão para iniciar o teste em cinco sensores.',tone:'neutral',busy:false};
}
function command(pending,results={},now=Date.now()){
 if(!pending)return null;
 const ack=results[pending.id];
 if(ack?.status==='REJECTED')return{resolved:true,text:'A edge rejeitou '+pending.action+': '+(ack.error||'Verifique os parâmetros.')};
 if(['APPLIED','DUPLICATE'].includes(ack?.status))return{resolved:true,text:'Alteração confirmada pela edge: '+pending.action+'. O PDF registra o estado observado e a amostra após 10 segundos.'};
 return{resolved:false,text:now-pending.at>15000?'Ainda sem confirmação da edge: '+pending.action+'. Verifique a conexão MQTT e o terminal da edge.':'Comando enviado: '+pending.action+'. Aguardando confirmação da edge…'};
}
const api={cloud,canary,versions,command};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.SmartWasteUI=api;
})(globalThis);
