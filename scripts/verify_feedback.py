"""Teste local com MQTT real dos estados de nuvem, canário e PDF."""
import json,os,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    def api(path,body=None,pdf=False):
        req=urllib.request.Request('http://127.0.0.1:8000'+path,data=None if body is None else json.dumps(body).encode(),headers={'content-type':'application/json'})
        with urllib.request.urlopen(req,timeout=15) as r:return r.read() if pdf else json.load(r)
    def wait(predicate,timeout=20):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:
                st=api('/api/state')
                if predicate(st):return st
            except (OSError,KeyError):pass
            time.sleep(.2)
        raise AssertionError('Estado esperado não chegou')
    with tempfile.TemporaryDirectory() as data:
        log=open(Path(data)/'runtime.log','w')
        proc=subprocess.Popen([sys.executable,str(ROOT/'run_distributed.py'),'--no-browser'],cwd=ROOT,env={**os.environ,'SMARTWASTE_DATA':data},stdout=log,stderr=log)
        try:
            wait(lambda s:s['architecture']['cloud_status']=='CONNECTED')
            assert api('/api/control',{'action':'CLOUD_LINK','value':False})['cloud_status']=='DISCONNECTED'
            wait(lambda s:s['architecture']['cloud_status']=='DISCONNECTED' and s['architecture']['pending_cloud']>=32)
            assert api('/api/control',{'action':'CLOUD_LINK','value':True})['cloud_status']=='CONNECTING'
            wait(lambda s:s['architecture']['cloud_status']=='CONNECTED')
            selected=['BIN-01','BIN-07','BIN-11','BIN-25','BIN-30']
            healthy=api('/api/control',{'action':'CANARY_START','selected':selected,'faulty':False})
            good=wait(lambda s:s['canary'].get('campaign_id')==healthy['command_id'] and s['canary']['status']=='READY_FOR_NEXT_WAVE')
            assert all(good['canary']['versions'][i]=='2.0' for i in selected)
            bad=api('/api/control',{'action':'CANARY_START','selected':selected,'faulty':True})
            active=wait(lambda s:s['canary'].get('campaign_id')==bad['command_id'] and s['canary']['status']=='OBSERVING')
            assert all(active['canary']['versions'][i]=='2.0-faulty' for i in selected)
            back=wait(lambda s:s['canary']['status']=='ROLLBACK')
            assert all(back['canary']['versions'][i]=='2.0' for i in selected)
            speed=api('/api/control',{'action':'SET_SPEED','value':360})
            wait(lambda s:s.get('speed')==360)
            time.sleep(11)
            evidence=api('/api/experiments')
            change=next(i for i in evidence['actions'] if i['id']==speed['command_id'])
            assert change['after']['speed']==360 and change['followup']['speed']==360
            assert change['ack_status'] in ('APPLIED','DUPLICATE')
            assert evidence['batches'] and evidence['samples']
            assert api('/api/state')['architecture']['fog_mqtt']['rx_messages']>0
            target=ROOT/'docs/evidence-export';target.mkdir(exist_ok=True)
            (target/'export.json').write_text(json.dumps(api('/api/export'),ensure_ascii=False,indent=2),encoding='utf-8')
            pdf=api('/api/export.pdf?limit=12',pdf=True)
            assert pdf.startswith(b'%PDF-')
            (target/'relatorio-exemplo.pdf').write_bytes(pdf)
            print(json.dumps({'success':True,'mqtt_real':True,'cloud_states':['CONNECTED','DISCONNECTED','CONNECTING','CONNECTED'],'healthy':'READY_FOR_NEXT_WAVE','faulty':'ROLLBACK','restored_version':'2.0','pdf_download':True}))
        finally:
            proc.terminate()
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            log.close()
if __name__=='__main__':main()
