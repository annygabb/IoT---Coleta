"""Fronteiras de rede, fila durável e modelos locais. Sem estado compartilhado entre serviços."""
import json, sqlite3, uuid, time, math, threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from apps.api.app.domain.simulation.engine import SimulationEngine
from apps.api.app.domain.geo.brasilia_network import BRASILIA_NODES
from apps.api.app.domain.iot.contracts import TruckState, RoutingStrategyType, WeatherType


def utc():
    return datetime.now(timezone.utc).isoformat()


def decode(payload):
    obj = json.loads(payload)
    if not isinstance(obj, dict):
        raise ValueError('Mensagem deve ser objeto JSON')
    return obj


class Store:
    def __init__(self, path, capacity=100000):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,payload TEXT NOT NULL,acked INTEGER NOT NULL DEFAULT 0); CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY,v TEXT NOT NULL);')
        columns={row[1] for row in self.db.execute('PRAGMA table_info(events)')}
        if 'measured_at' not in columns:
            self.db.execute("ALTER TABLE events ADD COLUMN measured_at TEXT NOT NULL DEFAULT ''")
            for identifier,raw in self.db.execute('SELECT id,payload FROM events').fetchall():
                self.db.execute('UPDATE events SET measured_at=? WHERE id=?',(self.event_time(json.loads(raw)),identifier))
        self.db.execute('CREATE INDEX IF NOT EXISTS events_measurement_time ON events(measured_at)')
        self.db.commit()
        self.capacity = capacity

    @staticmethod
    def event_time(payload):
        from .platform_contract import timestamp
        value=payload.get('timestamp') or payload.get('simulated_at') or payload.get('captured_at') or payload.get('emitted_at')
        try:return timestamp(value) if value else ''
        except ValueError:return '' 

    def get(self, k, default=None):
        r = self.db.execute('SELECT v FROM kv WHERE k=?', (k,)).fetchone()
        return json.loads(r[0]) if r else default

    def put(self, k, v):
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO kv VALUES(?,?)', (k, json.dumps(v, allow_nan=False)))

    def add_batch(self, items):
        # O mesmo ID nunca recebe outro conteúdo em um reenvio.
        rows = {i: (json.dumps(p, allow_nan=False),self.event_time(p)) for i, p in items}
        with self.lock, self.db:
            fresh = [(i,p,t) for i,(p,t) in rows.items() if not self.db.execute('SELECT 1 FROM events WHERE id=?', (i,)).fetchone()]
            if self.count() + len(fresh) > self.capacity:
                raise RuntimeError('Fila cheia: mensagens não foram confirmadas')
            self.db.executemany('INSERT INTO events(id,payload,measured_at) VALUES(?,?,?)', fresh)

    def pending(self, limit=100):
        return [(i,json.loads(p)) for i,p in self.db.execute('SELECT id,payload FROM events WHERE acked=0 ORDER BY rowid LIMIT ?', (limit,))]

    def ack(self, ids):
        with self.lock, self.db:
            self.db.executemany('UPDATE events SET acked=1 WHERE id=?', [(i,) for i in ids])

    def count(self):
        return self.db.execute('SELECT count(*) FROM events WHERE acked=0').fetchone()[0]

    def history(self, limit=100):
        return [json.loads(p) for (p,) in self.db.execute('SELECT payload FROM events ORDER BY measured_at DESC,rowid DESC LIMIT ?', (limit,))]

    def close(self):
        self.db.close()


class Canary:
    def __init__(self):
        self.campaign_id=None; self.versions={}; self.previous_versions={}; self.status='IDLE'; self.selected=[]; self.version='1.0'; self.reports=0; self.errors=0; self.controls=0; self.started=0

    def start(self, selected, faulty=False, now=None):
        if self.status=='OBSERVING': raise ValueError('Campanha já em observação')
        if not isinstance(selected,list) or not 1<=len(selected)<=10 or len(set(selected))!=len(selected) or any(x not in [f'BIN-{i:02d}' for i in range(1,33)] for x in selected):
            raise ValueError('Selecione de 1 a 10 sensores válidos e distintos')
        self.selected=selected; self.version='2.0-faulty' if faulty else '2.0'; self.status='OBSERVING'; self.started=time.monotonic() if now is None else now
        self.reports=self.errors=self.controls=0
        self.previous_versions={sensor:self.versions.get(sensor,'1.0') for sensor in selected}
        for sensor in selected: self.versions[sensor]=self.version

    def observe(self, now=None):
        if self.status!='OBSERVING': return
        self.reports+=len(self.selected); self.controls+=32-len(self.selected)
        if self.version.endswith('faulty'): self.errors+=len(self.selected)
        if (time.monotonic() if now is None else now)-self.started>=10 and self.reports>=max(5,len(self.selected)) and self.controls>=5:
            self.status='ROLLBACK' if self.errors/self.reports>0.05 else 'READY_FOR_NEXT_WAVE'
            if self.status=='ROLLBACK': self.versions.update(self.previous_versions)

    def as_dict(self):
        return dict(status=self.status,selected=self.selected,version=self.version,reports=self.reports,errors=self.errors,controls=self.controls,versions=self.versions.copy(),campaign_id=self.campaign_id)


class Edge:
    def __init__(self, store, telemetry_every=1):
        self.telemetry_every=max(1,min(60,int(telemetry_every)))
        self.store=store; self.engine=SimulationEngine(); self.engine._dispatch_trucks_if_needed=lambda:None
        # Novo boot tem identidade própria. Histórico e comandos persistem, física reinicia.
        self.run_id=uuid.uuid4().hex; self.seq=0; self.canary=Canary()

    def snapshot(self):
        self.seq+=1; self.canary.observe()
        e=self.engine; state=e.get_full_state()
        simulated=(datetime(2026,9,3,tzinfo=timezone.utc)+timedelta(days=e.clock.sim_day-1,seconds=e.clock.sim_time_seconds)).isoformat()
        state['sim_iso']=simulated
        for t,row in zip(e.trucks,state['trucks']): row.update(path=t.path[:],path_progress=t.path_progress)
        events=[]
        for b in (state['bins'] if (self.seq-1)%self.telemetry_every==0 else []):
            version=self.canary.versions.get(b['id'],'1.0')
            events.append(dict(event_id=f'{self.run_id}-{self.seq}-{b["id"]}', run_id=self.run_id,device_id='sensor-'+b['id'],bin_id=b['id'],sequence=self.seq,simulated_at=simulated,emitted_at=utc(),fill_pct=b['fill_pct'],temperature_c=b['temperature_c'],battery_pct=b['battery_pct'],operational_state=b['state'],sensor_status='FAULTY' if version.endswith('faulty') else 'ONLINE',firmware_version=version))
        from .platform_contract import to_canonical
        for event in events:event['canonical']=to_canonical(event)
        s=dict(captured_at=utc(),run_id=self.run_id,sequence=self.seq,state=state,events=events,canary=self.canary.as_dict(),transport=getattr(self,'transport_stats',{}))
        self.store.add_batch([(f'{self.run_id}-{self.seq}',s)])
        return s

    def command(self, c):
        cid=c.get('command_id'); action=c.get('action'); e=self.engine
        if not isinstance(cid,str) or not 1<=len(cid)<=100: raise ValueError('command_id inválido')
        if self.store.get('command:'+cid): return False
        if action in ('ASSIGN_ROUTE','GO_TO_DISPOSAL'):
            t=next((t for t in e.trucks if t.id==c.get('truck_id')),None); path=c.get('route_sequence')
            if not t or not isinstance(path,list) or not 1<=len(path)<=200 or path[0]!=t.current_node or any(n not in BRASILIA_NODES for n in path):
                raise ValueError('Rota incompatível com posição do atuador')
            t.assign_route(path[:],c.get('target_bin_id'),c['target_node'])
            if action=='GO_TO_DISPOSAL': t.state=TruckState.INDO_DESCARTE
        elif action=='PAUSE': e.clock.pause()
        elif action=='RESUME': e.clock.resume()
        elif action=='SET_SPEED':
            v=c.get('value')
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1440: raise ValueError('Velocidade inválida')
            e.clock.set_speed(v)
        elif action=='SET_STRATEGY': e.strategy_type=RoutingStrategyType(c['value'])
        elif action=='WEATHER': e.set_weather(WeatherType(c['value']))
        elif action=='BLOCK_ROAD':
            if type(c.get('value')) is not bool: raise ValueError('Booleano obrigatório')
            e.set_eptg_blocked(c['value'])
        elif action=='FORCE_CRITICAL': e.force_critical_bin(c.get('value'))
        elif action=='CANARY_START':
            self.canary.start(c.get('selected'),c.get('faulty') is True)
            self.canary.campaign_id=cid
        else: raise ValueError('Ação desconhecida')
        self.store.put('command:'+cid,True)
        return True


class Fog:
    def __init__(self, store):
        from .ingestion import Ingestion
        self.ingestion=Ingestion(store)
        self.store=store; self.engine=SimulationEngine(); self.last=None; self.last_seen=None; self.received=0; self.duplicates=0; self.outstanding={}; self.acks=0; self.command_results={}
        self.engine.broker.subscribe('smartwaste/df/trucks/#',self.capture)

    def capture(self, topic, c):
        if not topic.endswith('/commands'): return
        t=next(t for t in self.engine.trucks if t.id==c['truck_id'])
        cmd={**c,'route_sequence':t.path[:]}
        self.outstanding[t.id]={'command':cmd,'sent':0}

    def enqueue(self, c): self.outstanding['control:'+c['command_id']]={'command':c,'sent':0}

    def ack(self, c):
        for k,v in list(self.outstanding.items()):
            if v['command']['command_id']==c.get('command_id'):
                del self.outstanding[k]; self.acks+=1
                self.command_results[c['command_id']]={name:c[name] for name in ['status','error','at'] if name in c}
                while len(self.command_results)>100: self.command_results.pop(next(iter(self.command_results)))

    def receive(self, s):
        if not isinstance(s.get('state'),dict) or not isinstance(s.get('events'),list) or not isinstance(s.get('sequence'),int): raise ValueError('Snapshot inválido')
        # Guarda histórico antigo, mas não deixa leitura atrasada regredir o painel.
        from .platform_contract import to_canonical,validate_message,timestamp
        valid=[]
        for event in s['events']:
            try:
                message=to_canonical(event)
                if 'canonical' in event and validate_message(event['canonical'])!=message:
                    raise ValueError('Envelope canônico diverge do evento de origem')
                result=self.ingestion.batch([message],source='mqtt',cloud_route='legacy',observed_at=event['emitted_at'])
                if result['accepted']:valid.append((event['event_id'],event))
            except (ValueError,TypeError,KeyError) as ex:
                with self.store.lock,self.store.db:self.ingestion.reject(event,str(ex),'mqtt-legacy')
        self.store.add_batch(valid)
        captured=s.get('captured_at') or max((e.get('emitted_at','') for e in s['events'] if isinstance(e,dict)),default='')
        captured=timestamp(captured) if captured else ''
        latest_time=self.store.get('fog:latest_time','')
        if captured and latest_time and captured<latest_time:
            self.duplicates+=1;return False
        k='seq:'+s['run_id']
        if s['sequence']<=self.store.get(k,-1): self.duplicates+=1; return False
        e=self.engine; st=s['state']
        for b,row in zip(e.bins,st['bins']): b.fill_pct=row['fill_pct']; b.sensor_battery=row['battery_pct']; b.temperature_c=row['temperature_c']
        for t,row in zip(e.trucks,st['trucks']):
            for field in ['current_node','target_node','target_bin_id','load_kg','path','path_progress','total_distance_km','total_collected_kg']:
                setattr(t,field,row[field])
            t.state=TruckState.DESPACHADO if t.id in self.outstanding else TruckState(row['state'])
        e.clock.sim_time_seconds=int(st['sim_time'][:2])*3600+int(st['sim_time'][3:5])*60+int(st['sim_time'][6:8])
        e.strategy_type=RoutingStrategyType(st['strategy']); e.router.set_eptg_blocked(st['eptg_blocked'])
        self.last=s; self.last_seen=time.monotonic(); self.store.put(k,s['sequence']); self.received+=len(valid)
        if captured:self.store.put('fog:latest_time',captured)
        e._dispatch_trucks_if_needed()
        return True

    def state(self):
        st=dict(self.last['state']) if self.last else {}
        st['latest_decision']=self.engine.explainer.get_latest_decision_text()
        st['canary']=self.last['canary'] if self.last else {}
        st['architecture']=dict(received=self.received,duplicates=self.duplicates,pending_cloud=self.store.count(),edge_age_seconds=round(time.monotonic()-self.last_seen,1) if self.last_seen else None,command_acks=self.acks,command_results=self.command_results.copy(),run_id=self.last['run_id'] if self.last else None,mqtt_real=True,quarantined=self.ingestion.quarantine(limit=1)['total'],sequence=self.last['sequence'] if self.last else None,edge_mqtt=self.last.get('transport',{}) if self.last else {})
        return st
