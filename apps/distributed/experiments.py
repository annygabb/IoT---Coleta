"""Evidência local persistente: amostras, ações de laboratório e lotes de nuvem."""
import json,uuid
from datetime import datetime,timezone
from statistics import mean

def now():return datetime.now(timezone.utc).isoformat()
def seconds(a,b):return max(0,(datetime.fromisoformat(b)-datetime.fromisoformat(a)).total_seconds())
def encode(x):return json.dumps(x,ensure_ascii=False,allow_nan=False)

def metrics(state):
    a=state.get('architecture',{});bins=state.get('bins',[]);trucks=state.get('trucks',[]);ca=state.get('canary',{})
    return dict(at=now(),run_id=a.get('run_id'),sequence=a.get('sequence'),sim_iso=state.get('sim_iso'),
        speed=state.get('speed'),strategy=state.get('strategy'),weather=state.get('weather'),paused=state.get('is_paused'),blocked=state.get('eptg_blocked'),
        cloud_enabled=a.get('cloud_link_enabled'),cloud_status=a.get('cloud_status'),pending=a.get('pending_cloud',0),received=a.get('received',0),synced=a.get('synced',0),
        mean_fill=round(mean(b['fill_pct'] for b in bins),2) if bins else None,critical_bins=sum(b['fill_pct']>=85 for b in bins),
        distance_km=round(sum(t['total_distance_km'] for t in trucks),2),collected_kg=round(sum(t['total_collected_kg'] for t in trucks),1),
        fill_by_bin={b['id']:b['fill_pct'] for b in bins},firmware=ca.get('versions',{}).copy(),canary_status=ca.get('status','IDLE'),campaign_id=ca.get('campaign_id'),
        canary_reports=ca.get('reports',0),canary_errors=ca.get('errors',0),cloud_attempts=a.get('cloud_attempts',0),cloud_successes=a.get('cloud_successes',0),
        cloud_failures=a.get('cloud_failures',0),cloud_payload_bytes=a.get('cloud_payload_bytes',0))

class Audit:
    def __init__(self,store,session_id=None):
        self.db=store.db;self.session_id=session_id or uuid.uuid4().hex
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS lab_actions(id TEXT PRIMARY KEY,session TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS lab_samples(id INTEGER PRIMARY KEY,session TEXT NOT NULL,payload TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS lab_batches(id INTEGER PRIMARY KEY,session TEXT NOT NULL,payload TEXT NOT NULL);
        """)
    def start(self,cid,action,requested,before,via='MQTT'):
        safe={k:requested[k] for k in ['value','selected','faulty'] if k in requested}
        item=dict(id=cid,session=self.session_id,action=action,requested=safe,via=via,status='QUEUED',at=now(),before=before,confirmed_at=None,ack_status=None,after=None,followup=None,error=None)
        with self.db:
            self.db.execute('INSERT INTO lab_actions VALUES(?,?,?)',(cid,self.session_id,encode(item)))
            self.db.execute('DELETE FROM lab_actions WHERE rowid NOT IN (SELECT rowid FROM lab_actions ORDER BY rowid DESC LIMIT 500)')
        return item
    def get(self,cid):
        row=self.db.execute('SELECT payload FROM lab_actions WHERE id=?',(cid,)).fetchone()
        return json.loads(row[0]) if row else None
    def save(self,item):
        with self.db:self.db.execute('UPDATE lab_actions SET payload=? WHERE id=?',(encode(item),item['id']))
    def confirm(self,cid,status,error=None):
        item=self.get(cid)
        if not item or item['confirmed_at']:return
        item.update(confirmed_at=now(),ack_status=status,status='REJECTED' if status=='REJECTED' else 'APPLIED',error=error)
        item['ack_ms']=round(seconds(item['at'],item['confirmed_at'])*1000,2);self.save(item)
    @staticmethod
    def matches(item,sample):
        action=item['action'];value=item['requested'].get('value')
        fields={'SET_SPEED':'speed','SET_STRATEGY':'strategy','WEATHER':'weather','BLOCK_ROAD':'blocked','CLOUD_LINK':'cloud_enabled'}
        if action in fields:return sample.get(fields[action])==value
        if action in ('PAUSE','RESUME'):return sample.get('paused')==(action=='PAUSE')
        if action=='CANARY_START':return sample.get('campaign_id')==item['id']
        return True
    def tick(self,sample):
        with self.db:
            self.db.execute('INSERT INTO lab_samples(session,payload) VALUES(?,?)',(self.session_id,encode(sample)))
            self.db.execute('DELETE FROM lab_samples WHERE id NOT IN (SELECT id FROM lab_samples ORDER BY id DESC LIMIT 1000)')
        for (raw,) in self.db.execute('SELECT payload FROM lab_actions WHERE session=?',(self.session_id,)).fetchall():
            item=json.loads(raw)
            if item['status'] not in ('APPLIED','OBSERVED'):continue
            # Dados de outra execução física não servem de comparação.
            if item['before'].get('run_id') and sample.get('run_id')!=item['before']['run_id']:continue
            if not item['after'] and self.matches(item,sample):
                item.update(after=sample,status='OBSERVED');self.save(item)
            elif item['after'] and not item['followup'] and seconds(item['after']['at'],sample['at'])>=10:
                item['followup']=sample;self.save(item)
    def batch(self,entry):
        safe={k:entry.get(k) for k in ['at','requested','acknowledged','payload_bytes','duration_ms','http_status','error']}
        with self.db:
            self.db.execute('INSERT INTO lab_batches(session,payload) VALUES(?,?)',(self.session_id,encode(safe)))
            self.db.execute('DELETE FROM lab_batches WHERE id NOT IN (SELECT id FROM lab_batches ORDER BY id DESC LIMIT 500)')
    def export(self):
        actions=[json.loads(p) for (p,) in self.db.execute('SELECT payload FROM lab_actions ORDER BY rowid DESC LIMIT 100')]
        for item in actions:
            end=(item['followup'] or {}).get('at') or now()
            item['overlapping_actions']=sum(other['id']!=item['id'] and other['session']==item['session'] and other['at']<=end and ((other.get('followup') or {}).get('at') or now())>=item['at'] for other in actions)
        return dict(session_id=self.session_id,actions=actions,samples=[json.loads(p) for (p,) in self.db.execute('SELECT payload FROM lab_samples WHERE session=? ORDER BY id',(self.session_id,))],
          batches=[json.loads(p) for (p,) in self.db.execute('SELECT payload FROM lab_batches WHERE session=? ORDER BY id',(self.session_id,))],
          limits=dict(actions=100,samples_retained=1000,batches_retained=500,followup_seconds=10),instrumentation_started_this_version=True)
