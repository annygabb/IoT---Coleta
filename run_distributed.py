"""Inicializador local. Nenhuma porta é exposta na internet."""
import argparse, json, os, secrets, signal, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(); p.add_argument('--cloud-config'); p.add_argument('--external-broker',action='store_true'); p.add_argument('--no-browser',action='store_true'); a=p.parse_args()
    data=Path(os.getenv('SMARTWASTE_DATA',str(ROOT/'data/distributed'))); data.mkdir(parents=True,exist_ok=True)
    cfg=Path(a.cloud_config).resolve() if a.cloud_config else data/'local-config.json'
    if not a.cloud_config and not cfg.exists(): cfg.write_text(json.dumps(dict(cloud_url='http://127.0.0.1:8002',fog_id='fog-df-01',fog_token=secrets.token_urlsafe(48))))
    if not cfg.exists(): p.error('Arquivo de conexão não encontrado')
    env={**os.environ,'SMARTWASTE_CONFIG':str(cfg),'SMARTWASTE_DATA':str(data)}; children=[]
    def start(args): children.append(subprocess.Popen([sys.executable,*args],cwd=ROOT,env=env))
    def stop(sig,frame): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    try:
        if not a.external_broker: start(['-m','apps.distributed.broker']); time.sleep(1)
        for role,port in [('edge',8001),('fog',8000),*([('cloud',8002)] if not a.cloud_config else [])]:
            start(['-m','uvicorn',f'apps.distributed.runtime:{role}_app','--factory','--host','127.0.0.1','--port',str(port),'--log-level','warning'])
        deadline=time.monotonic()+25
        while True:
            if any(c.poll() is not None for c in children): raise RuntimeError('Serviço encerrou. Verifique dependências e portas 1883/8000/8001/8002.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=1) as r: ready=json.load(r)['mqtt_connected']
                if ready: break
            except Exception: pass
            if time.monotonic()>deadline: raise RuntimeError('Não foi possível iniciar MQTT/fog')
            time.sleep(.3)
        print('Painel: http://127.0.0.1:8000 | Ctrl+C para encerrar',flush=True)
        if not a.no_browser: webbrowser.open('http://127.0.0.1:8000')
        while all(c.poll() is None for c in children): time.sleep(.5)
    except KeyboardInterrupt: pass
    finally:
        for c in children:
            if c.poll() is None: c.terminate()
        for c in children:
            try: c.wait(timeout=5)
            except subprocess.TimeoutExpired: c.kill(); c.wait()
if __name__=='__main__': main()
