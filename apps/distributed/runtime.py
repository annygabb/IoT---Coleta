"""Serviços edge/fog separados, MQTT 3.1.1 real e sincronização HTTPS em lotes."""
import asyncio, json, os, queue, time, uuid, urllib.request, hmac, sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from .core import Store, Edge, Fog, decode, utc
from .experiments import Audit,metrics
from .ingestion import Ingestion
from .platform_api import install_platform_routes
from .sync_result import apply_result,transport_batch
from apps.api.app.domain.geo.brasilia_network import BRASILIA_NODES, BRASILIA_ROADS
ROOT=Path(__file__).resolve().parents[2]
DATA=Path(os.getenv('SMARTWASTE_DATA',str(ROOT/'data/distributed')))
PREFIX='smartwaste/df/'


def config():
    p=os.getenv('SMARTWASTE_CONFIG')
    return json.loads(Path(p).read_text()) if p else {}


class Network:
    def __init__(self, role):
        self.tx_messages=0; self.tx_bytes=0; self.rx_messages=0; self.rx_bytes=0; self.invalid_messages=0
        self.connected=False; self.inbox=queue.Queue(maxsize=10000); self.error=None
        self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=role+'-'+uuid.uuid4().hex,protocol=mqtt.MQTTv311)
        self.client.reconnect_delay_set(1,10)
        topics=['commands','snapshot-acks'] if role=='edge' else ['snapshots','command-acks']
        def connected(client,userdata,flags,reason,properties):
            self.connected=not reason.is_failure
            if self.connected:
                for t in topics: client.subscribe(PREFIX+t,1)
                if role=='fog':client.subscribe('smartwaste/+/+/+/telemetria',1)
        def disconnected(client,userdata,flags,reason,properties): self.connected=False
        def message(client,userdata,msg):
            try:
                if len(msg.payload)>1048576: raise ValueError('Mensagem grande demais')
                self.inbox.put_nowait((msg.topic,decode(msg.payload)))
                self.rx_messages+=1; self.rx_bytes+=len(msg.payload)
            except (ValueError,queue.Full): self.invalid_messages+=1; self.error='Mensagem inválida ou fila MQTT saturada'
        self.client.on_connect=connected; self.client.on_disconnect=disconnected; self.client.on_message=message
        self.client.connect_async('127.0.0.1',1883,30); self.client.loop_start()

    def send(self, topic, obj):
        return self.send_topic(PREFIX+topic,obj)

    def send_topic(self,topic,obj):
        raw=json.dumps(obj,allow_nan=False).encode('utf-8')
        sent=self.client.publish(topic,raw,qos=1)
        if sent.rc==mqtt.MQTT_ERR_SUCCESS:self.tx_messages+=1; self.tx_bytes+=len(raw)

    def stats(self):return dict(tx_messages=self.tx_messages,tx_payload_bytes=self.tx_bytes,rx_messages=self.rx_messages,rx_payload_bytes=self.rx_bytes,invalid_messages=self.invalid_messages)

    def drain(self):
        while True:
            try: yield self.inbox.get_nowait()
            except queue.Empty: break

    def close(self): self.client.disconnect(); self.client.loop_stop()


def edge_app():
    state={}
    @asynccontextmanager
    async def life(app):
        store=Store(DATA/'edge.db'); cfg=config(); edge=Edge(store,telemetry_every=cfg.get('telemetry_every',5 if cfg.get('cloud_url','').startswith('https://') else 1)); net=Network('edge'); state.update(edge=edge,net=net,error=None)
        async def worker():
            last=time.monotonic(); snap=0; resend=0
            while True:
                now=time.monotonic(); edge.engine.step(min(now-last,.2)); last=now
                for topic,c in net.drain():
                    if topic.endswith('snapshot-acks'): store.ack(c.get('acknowledged',[]))
                    else:
                        try:
                            applied=edge.command(c); ack=dict(command_id=c.get('command_id'),status='APPLIED' if applied else 'DUPLICATE',at=utc())
                        except (ValueError,KeyError,TypeError) as ex: ack=dict(command_id=c.get('command_id'),status='REJECTED',error=str(ex),at=utc())
                        net.send('command-acks',ack)
                if now-snap>=1:
                    try: edge.transport_stats=net.stats(); edge.snapshot(); state['error']=None
                    except (RuntimeError,sqlite3.Error) as ex: state['error']=str(ex)
                    snap=now
                if net.connected and now-resend>=.5:
                    for _,s in store.pending(4): net.send('snapshots',s)
                    resend=now
                await asyncio.sleep(.05)
        task=asyncio.create_task(worker())
        try: yield
        finally: task.cancel(); await asyncio.gather(task,return_exceptions=True); net.close(); store.close()
    app=FastAPI(lifespan=life)
    @app.get('/health')
    def health(): return dict(status='ok',mqtt_connected=state['net'].connected,queue_error=state['error'],pending_fog=state['edge'].store.count())
    return app


def fog_app():
    state={}; cfg=config()
    @asynccontextmanager
    async def life(app):
        store=Store(DATA/'fog.db'); fog=Fog(store); net=Network('fog')
        state.update(fog=fog,net=net,cloud_link_enabled=True,cloud_error=None,last_sync=None,synced=0,queue_error=None,latencies_ms=[],cloud_status="CONNECTING",sync_in_progress=False,cloud_generation=0,cloud_attempts=0,cloud_successes=0,cloud_failures=0,cloud_payload_bytes=0,canonical_cloud_status='IDLE',canonical_cloud_error=None)
        state['audit']=Audit(store)
        async def worker():
            while True:
                for topic,s in net.drain():
                    if topic.endswith('/telemetria'):
                        result=fog.ingestion.mqtt(topic,s)
                        if hasattr(net,'send_topic'):net.send_topic(topic.rsplit('/',1)[0]+'/ack',result)
                    elif topic.endswith('command-acks'):
                        fog.ack(s); state['audit'].confirm(s.get('command_id'),s.get('status'),s.get('error'))
                    else:
                        try:
                            fresh=fog.receive(s)
                            if fresh:state['audit'].tick(metrics(current()))
                            net.send('snapshot-acks',dict(acknowledged=[f'{s["run_id"]}-{s["sequence"]}']))
                            state['queue_error']=None
                        except (ValueError,KeyError,TypeError,RuntimeError,sqlite3.Error) as ex: state['queue_error']=str(ex)
                if net.connected:
                    for v in list(fog.outstanding.values()):
                        if time.monotonic()-v['sent']>=2: net.send('commands',v['command']); v['sent']=time.monotonic()
                await asyncio.sleep(.1)
        async def sync():
            delay=1
            while True:
                if state['cloud_link_enabled']:
                    batch=store.pending(100)
                    if batch:
                        generation=state["cloud_generation"]; state["sync_in_progress"]=True
                        batch,raw=transport_batch(batch,'events'); state['cloud_attempts']+=1; state['cloud_payload_bytes']+=len(raw); attempt_started=time.monotonic()
                        def send():
                            req=urllib.request.Request(cfg['cloud_url'].rstrip('/')+'/ingest',data=raw,headers={'content-type':'application/json','x-fog-token':cfg['fog_token']})
                            start=time.monotonic()
                            with urllib.request.urlopen(req,timeout=15) as response: body=json.load(response); http_status=response.status
                            return body,(time.monotonic()-start)*1000,http_status
                        try:
                            body,ms,http_status=await asyncio.to_thread(send)
                            ids=apply_result(store,batch,body);state['cloud_successes']+=1
                            state['audit'].batch(dict(at=utc(),requested=len(batch),acknowledged=len(ids),payload_bytes=len(raw),duration_ms=round(ms,2),http_status=http_status,error=None))
                            store.ack(ids); state['synced']+=len(ids); state['last_sync']=utc(); state['cloud_error']=None; delay=1
                            if state['cloud_link_enabled'] and generation==state['cloud_generation']: state['cloud_status']='CONNECTED'
                            state['latencies_ms']=(state['latencies_ms']+[round(ms,2)])[-200:]
                            state['audit'].tick(metrics(current()))
                        except Exception as ex:
                            state['cloud_failures']+=1
                            state['audit'].batch(dict(at=utc(),requested=len(batch),acknowledged=0,payload_bytes=len(raw),duration_ms=round((time.monotonic()-attempt_started)*1000,2),http_status=getattr(ex,'code',None),error=type(ex).__name__))
                            state['cloud_error']=type(ex).__name__+': '+str(ex); delay=min(30,delay*2)
                            if state['cloud_link_enabled'] and generation==state['cloud_generation']: state['cloud_status']='ERROR'
                        finally: state['sync_in_progress']=False
                await asyncio.sleep(delay)
        async def sync_canonical():
            delay=1
            while True:
                batch=fog.ingestion.pending(100)
                if state['cloud_link_enabled'] and batch:
                    batch,raw=transport_batch(batch,'messages')
                    def send_platform():
                        req=urllib.request.Request(cfg['cloud_url'].rstrip('/')+'/platform-ingest',data=raw,
                            headers={'content-type':'application/json','x-fog-token':cfg['fog_token']})
                        with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
                    try:
                        result=await asyncio.to_thread(send_platform)
                        apply_result(store,batch,result,canonical=True)
                        state['canonical_cloud_status']='CONNECTED';state['canonical_cloud_error']=None;delay=1
                    except Exception as ex:
                        state['canonical_cloud_status']='PENDING_CLOUD_UPDATE' if getattr(ex,'code',None)==404 else 'ERROR'
                        state['canonical_cloud_error']=type(ex).__name__;delay=min(30,delay*2)
                await asyncio.sleep(delay)
        tasks=[asyncio.create_task(worker()),asyncio.create_task(sync()),asyncio.create_task(sync_canonical())]
        try: yield
        finally:
            for t in tasks: t.cancel()
            await asyncio.gather(*tasks,return_exceptions=True); net.close(); store.close()
    app=FastAPI(lifespan=life)
    install_platform_routes(app,lambda:state['fog'].ingestion)
    @app.get('/',response_class=HTMLResponse)
    def home(): return (ROOT/'apps/distributed/dashboard.html').read_text(encoding='utf-8')
    @app.get('/ui-state.js')
    def ui_state(): return Response((ROOT/'apps/distributed/ui-state.js').read_text(encoding='utf-8'),media_type='text/javascript')
    @app.get('/legacy',response_class=HTMLResponse)
    def legacy(): return (ROOT/'index.html').read_text(encoding='utf-8')
    @app.get('/health')
    def health(): return dict(status='ok',mqtt_connected=state['net'].connected)
    @app.get('/api/state')
    def current():
        s=state['fog'].state(); s['architecture'].update({k:state[k] for k in ['cloud_link_enabled','cloud_error','last_sync','synced','queue_error','latencies_ms','cloud_status','sync_in_progress','cloud_attempts','cloud_successes','cloud_failures','cloud_payload_bytes','canonical_cloud_status','canonical_cloud_error']}); s['architecture']['mqtt_connected']=state['net'].connected; s['architecture']['cloud_url']=cfg['cloud_url']; s['architecture']['fog_mqtt']=getattr(state['net'],'stats',lambda:{})()
        s['architecture']['telemetry_every']=cfg.get('telemetry_every',5 if cfg['cloud_url'].startswith('https://') else 1)
        s['architecture']['canonical_pending']=state['fog'].store.db.execute("SELECT count(*) FROM iot_messages WHERE cloud_route='canonical' AND cloud_ack=0").fetchone()[0]
        return s
    @app.get('/api/network')
    def network(): return dict(nodes=BRASILIA_NODES,roads=BRASILIA_ROADS)
    @app.get('/api/history')
    def history(): return dict(events=state['fog'].store.history())
    def evidence():return state['audit'].export()
    @app.get('/api/experiments')
    def experiments():return evidence()
    @app.get('/api/export')
    def export(): return dict(synthetic_data=True,students=['Anny','Arthur','Eduardo','Jéssica'],state=current(),events=state['fog'].store.history(10000),evidence=evidence(),platform=state['fog'].ingestion.history(limit=1000),quarantine=state['fog'].ingestion.quarantine())
    @app.get('/api/export.pdf')
    async def export_pdf(limit:int=Query(default=1000,ge=1,le=10000)):
        from .pdf_export import build_pdf
        payload=dict(exported_at=utc(),limit=limit,state=current(),events=state['fog'].store.history(limit),evidence=evidence())
        data=await asyncio.to_thread(build_pdf,payload)
        return Response(data,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=smartwaste-dados.pdf','Cache-Control':'no-store'})
    @app.post('/api/control')
    async def control(req:Request):
        raw=await req.body()
        if len(raw)>8192: raise HTTPException(413,'Limite 8 KiB')
        try: c=decode(raw)
        except ValueError: raise HTTPException(400,'JSON inválido')
        action=c.get('action')
        if action=='CLOUD_LINK':
            if type(c.get('value')) is not bool: raise HTTPException(400,'Booleano obrigatório')
            change_id=uuid.uuid4().hex; state['audit'].start(change_id,action,c,metrics(current()),via='LOCAL_FOG')
            state['cloud_link_enabled']=c['value']; state['cloud_generation']+=1
            state['cloud_status']='CONNECTING' if c['value'] else 'DISCONNECTED'
            if c['value']: state['cloud_error']=None
            state['audit'].confirm(change_id,'APPLIED'); state['audit'].tick(metrics(current()))
            return dict(status='APPLIED',cloud_status=state['cloud_status'],change_id=change_id)
        if action not in ['PAUSE','RESUME','SET_SPEED','SET_STRATEGY','WEATHER','BLOCK_ROAD','FORCE_CRITICAL','CANARY_START']: raise HTTPException(400,'Ação inválida')
        if not state['net'].connected: raise HTTPException(503,'Broker desconectado')
        if action=='CANARY_START' and state['fog'].last and state['fog'].last['canary']['status']=='OBSERVING': raise HTTPException(409,'Campanha em observação')
        c['command_id']=uuid.uuid4().hex
        try:state['audit'].start(c['command_id'],action,c,metrics(current()))
        except ValueError:raise HTTPException(400,'Valores inválidos para registrar o comando')
        state['fog'].enqueue(c)
        return dict(status='QUEUED_UNTIL_ACK',command_id=c['command_id'])
    return app


def cloud_app():
    cfg=config(); state={}
    @asynccontextmanager
    async def life(app):
        state['store']=Store(DATA/'cloud.db')
        state['ingestion']=Ingestion(state['store'],validate_catalog=False)
        try: yield
        finally: state['store'].close()
    app=FastAPI(lifespan=life)
    def authorize(req):
        if not hmac.compare_digest(req.headers.get('x-fog-token',''),cfg['fog_token']): raise HTTPException(401,'Credencial inválida')
    @app.get('/health')
    def health(): return dict(status='ok',local_emulator=True)
    @app.post('/ingest')
    async def ingest(req:Request):
        authorize(req); raw=await req.body()
        if len(raw)>262144: raise HTTPException(413,'Limite 256 KiB')
        try:
            body=decode(raw); events=body['events']
            if not isinstance(events,list) or not 1<=len(events)<=100: raise ValueError('Lote inválido')
            from .platform_contract import validate_legacy,legacy_identity
            accepted=[];rejected=[]
            for index,event in enumerate(events):
                try:
                    validate_legacy(event)
                    old=state['store'].db.execute('SELECT payload FROM events WHERE id=?',(event['event_id'],)).fetchone()
                    if old and legacy_identity(json.loads(old[0]))!=legacy_identity(event):
                        raise ValueError('ID_CONFLICT')
                    accepted.append(event)
                except ValueError as ex:
                    rejected.append(dict(index=index,event_id=event.get('event_id') if isinstance(event,dict) else None,error=str(ex),retryable=False))
            state['store'].add_batch([(e['event_id'],e) for e in accepted])
            state['store'].ack([e['event_id'] for e in accepted])
        except (ValueError,KeyError,TypeError): raise HTTPException(400,'Eventos inválidos')
        return dict(acknowledged=list(dict.fromkeys(e['event_id'] for e in accepted)),rejected=rejected)
    @app.post('/platform-ingest')
    async def platform_ingest(req:Request):
        authorize(req)
        from .platform_api import read_json
        body=await read_json(req,max_bytes=262144)
        if not isinstance(body,dict) or not isinstance(body.get('messages'),list) or not 1<=len(body['messages'])<=100:
            raise HTTPException(400,'messages deve conter 1 a 100 itens')
        result=state['ingestion'].batch(body['messages'],source='fog',cloud_route='central')
        return dict(acknowledged=result['accepted'],rejected=[{**r,'retryable':False} for r in result['rejected']])
    @app.get('/history')
    def history(req:Request): authorize(req); return dict(events=state['store'].history())
    return app
