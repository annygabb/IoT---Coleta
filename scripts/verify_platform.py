"""Ensaio local com processos, MQTT real, API HTTP e nuvem emulada; não acessa o Supabase."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
import paho.mqtt.client as mqtt

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output');parser.add_argument('--clients',action='store_true');args=parser.parse_args()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def get(path):
        with opener.open('http://127.0.0.1:8000'+path,timeout=2) as r:return json.load(r)
    def post(path,body):
        request=urllib.request.Request('http://127.0.0.1:8000'+path,data=json.dumps(body).encode(),headers={'content-type':'application/json'})
        with opener.open(request,timeout=2) as r:return r.status,json.load(r)
    def wait(predicate,timeout=20):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:
                result=predicate()
                if result:return result
            except (OSError,KeyError):pass
            time.sleep(.1)
        raise RuntimeError('Tempo limite no ensaio local')
    processes=[];client=None
    with tempfile.TemporaryDirectory(prefix='smartwaste-test-') as temporary:
        data=Path(temporary);configuration=data/'config.json'
        configuration.write_text(json.dumps({'cloud_url':'http://127.0.0.1:8002','fog_token':'local-test-token-only-01234567890123456789'}))
        env={**os.environ,'SMARTWASTE_DATA':str(data),'SMARTWASTE_CONFIG':str(configuration)}
        try:
            commands=[['-m','apps.distributed.broker']]+[
                ['-m','uvicorn',f'apps.distributed.runtime:{role}_app','--factory','--host','127.0.0.1','--port',str(port),'--log-level','error']
                for role,port in [('edge',8001),('fog',8000),('cloud',8002)]]
            with (data/'services.log').open('w') as log:
                for command in commands:processes.append(subprocess.Popen([sys.executable,*command],cwd=ROOT,env=env,stdout=log,stderr=log))
                wait(lambda:get('/api/state').get('bins'))
                state=wait(lambda:(lambda s:s if s['architecture']['synced'] else None)(get('/api/state')))
                assert len(state['bins'])==32 and len(state['trucks'])==3
                for path,item in [
                    ('catalogo/dominios',{'id':'agricultura','name':'Agricultura'}),
                    ('catalogo/perfis',{'id':'solo','domain':'agricultura','interval_seconds':3600,'measures':[{'name':'umidade_solo','unit':'%','min':0,'max':100}]}),
                    ('sites',{'id':'fazenda','name':'Fazenda'}),
                    ('dispositivos',{'id':'solo-01','profile':'solo','site':'fazenda'})]:post('/api/v1/'+path,item)
                message={'versao':'1.0','id_mensagem':str(uuid.uuid4()),'tipo':'telemetria','dispositivo':'solo-01',
                    'timestamp':'2026-10-20T12:00:00Z','local':{'site':'fazenda'},
                    'medidas':[{'grandeza':'umidade_solo','valor':23.5,'unidade':'%'}]}
                status,response=post('/api/v1/ingestao',message);assert status==202 and response['accepted']
                client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2);acks=[]
                client.on_message=lambda c,u,m:acks.append(json.loads(m.payload))
                client.connect('127.0.0.1',1883);client.loop_start()
                subscribed=[];client.on_subscribe=lambda *args:subscribed.append(True)
                client.subscribe('smartwaste/fazenda/agricultura/solo-01/ack',1);wait(lambda:subscribed)
                message['id_mensagem']=str(uuid.uuid4());message['timestamp']='2026-10-20T13:00:00Z'
                client.publish('smartwaste/fazenda/agricultura/solo-01/telemetria',json.dumps(message),qos=1).wait_for_publish(timeout=3)
                wait(lambda:acks);assert acks[0]['accepted']==[message['id_mensagem']]
                wait(lambda:get('/api/v1/telemetria?device=solo-01')['total']==2)
                clients=[]
                if args.clients:
                    for command in [[sys.executable,'examples/platform_publish.py'],['node','examples/platform_publish.mjs'],['java','examples/PlatformPublish.java']]:
                        result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30,check=True)
                        assert result.stdout.startswith('202'),result.stdout
                        clients.append(command[0].split('/')[-1])
                state=wait(lambda:(lambda s:s if s['architecture']['canonical_pending']==0 else None)(get('/api/state')))
                history=get('/api/v1/telemetria?device=solo-01')
                assert history['messages'][0]['timestamp']=='2026-10-20T13:00:00.000000Z'
                evidence={'bins':len(state['bins']),'trucks':len(state['trucks']),
                    'mqtt_connected':state['architecture']['mqtt_connected'],'legacy_synced':state['architecture']['synced'],
                    'rural_messages':history['total'],'mqtt_application_ack':bool(acks[0]['accepted']),
                    'canonical_pending':state['architecture']['canonical_pending'],
                    'canonical_cloud_status':state['architecture']['canonical_cloud_status'],'cloud_target':'local-emulator','http_clients_verified':clients}
                text=json.dumps(evidence,indent=2)
                if args.output:Path(args.output).write_text(text+'\n',encoding='utf-8')
                print(text)
        finally:
            if client:client.disconnect();client.loop_stop()
            for process in processes:
                if process.poll() is None:process.terminate()
            for process in processes:
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':main()
