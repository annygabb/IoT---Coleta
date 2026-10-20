"""Executa o fluxo real MQTT, falha controlada do enlace e canário. Usa dados sintéticos."""
import argparse,csv,json,os,subprocess,sys,tempfile,time,urllib.request,urllib.error,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--cloud-config');p.add_argument('--output',default=str(ROOT/'docs/evidence'));a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    rows=[];t0=time.monotonic(); log=(out/'runtime.log').open('w',encoding='utf-8')
    def request(path,body=None):
        req=urllib.request.Request('http://127.0.0.1:8000'+path,data=None if body is None else json.dumps(body).encode(),headers={'content-type':'application/json'})
        with urllib.request.urlopen(req,timeout=4) as r:return json.load(r)
    def wait(pred,limit=35):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            try:
                s=request('/api/state')
                if pred(s):return s
            except (urllib.error.URLError,KeyError):pass
            time.sleep(.3)
        raise AssertionError('Condição não atendida dentro do prazo')
    def record(label,s=None):
        s=s or request('/api/state');arc=s['architecture'];rows.append(dict(scenario=label,seconds=round(time.monotonic()-t0,2),received=arc['received'],pending=arc['pending_cloud'],synced=arc['synced'],sim_time=s['sim_time'],collected_kg=s['metrics']['total_collected_kg']));return s
    with tempfile.TemporaryDirectory() as temp:
        env={**os.environ,'SMARTWASTE_DATA':temp};cmd=[sys.executable,str(ROOT/'run_distributed.py'),'--no-browser']
        if a.cloud_config:cmd+=['--cloud-config',str(Path(a.cloud_config).resolve())]
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=log)
        try:
            normal=record('normal',wait(lambda s:s['architecture']['synced']>0 and s['architecture']['command_acks']>=3))
            assert len(normal['bins'])==32 and len(normal['trucks'])==3
            request('/api/control',{'action':'CLOUD_LINK','value':False});before=record('outage_start')
            for i in range(6):time.sleep(1);record('outage')
            after=request('/api/state');assert after['architecture']['pending_cloud']>before['architecture']['pending_cloud'];assert after['sim_time']!=before['sim_time']
            request('/api/control',{'action':'CLOUD_LINK','value':True})
            target=after['architecture']['received']
            recovered=record('recovered',wait(lambda s:(s['architecture']['synced']>=target and s['architecture']['pending_cloud']<=64) if a.cloud_config else s['architecture']['pending_cloud']==0,60))
            request('/api/control',{'action':'CANARY_START','selected':['BIN-01','BIN-07','BIN-11','BIN-25','BIN-30'],'faulty':True});rollback=record('canary_rollback',wait(lambda s:s.get('canary',{}).get('status')=='ROLLBACK',20))
            for action,value,key,expected in [('SET_STRATEGY','FIXED','strategy','FIXED'),('WEATHER','CHUVA_FORTE','weather','CHUVA_FORTE'),('BLOCK_ROAD',True,'eptg_blocked',True)]:
                request('/api/control',{'action':action,'value':value});wait(lambda s:s.get(key)==expected)
            request('/api/control',{'action':'PAUSE'});paused=wait(lambda s:s.get('is_paused'));time.sleep(1.2);assert request('/api/state')['sim_time']==paused['sim_time']
            request('/api/control',{'action':'RESUME'});wait(lambda s:not s.get('is_paused'))
            exported=request('/api/export');assert 'fog_token' not in json.dumps(exported)
            (out/'sample-events.json').write_text(json.dumps(exported,indent=2,ensure_ascii=False))
            result=dict(success=True,mqtt_real=True,cloud_environment='Supabase HTTPS' if a.cloud_config else 'emulador local HTTP',duration_seconds=round(time.monotonic()-t0,2),browser_verified=False,checks=['32 lixeiras e 3 caminhões','comandos confirmados pelo edge','operação continua com nuvem desconectada','eventos acumulados durante a falha confirmados após reconectar','canário com falha reverte','estratégia, clima, bloqueio, pausa e retomada','segredo ausente da exportação'],run_id=exported['state']['architecture']['run_id'],canary=rollback['canary'],latencies_ms=exported['state']['architecture']['latencies_ms'],recovery_target_events=target,recovery_snapshot=recovered['architecture'],telemetry_every=5 if a.cloud_config else 1)
            (out/'result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
            with (out/'timeline.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
            print(json.dumps(result,ensure_ascii=False))
        finally:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
if __name__=='__main__':main()
