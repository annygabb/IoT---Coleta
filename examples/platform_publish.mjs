import {randomUUID} from 'node:crypto';
const message={versao:'1.0',id_mensagem:randomUUID(),tipo:'telemetria',
 dispositivo:'sensor-BIN-01',timestamp:new Date().toISOString(),
 medidas:[{grandeza:'nivel_enchimento',valor:65,unidade:'%'}]};
const response=await fetch('http://127.0.0.1:8000/api/v1/ingestao',{
 method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(message),signal:AbortSignal.timeout(5000)});
console.log(response.status,await response.text());if(!response.ok)process.exitCode=1;
