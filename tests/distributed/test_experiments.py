from apps.distributed.core import Store
from apps.distributed.experiments import Audit

def sample(t=0,**kw):return dict(at=f'2026-10-19T12:00:{t:02d}+00:00',run_id='run1',sequence=t,speed=60,**kw)

def test_observe_matching_state_then_followup_and_persist(tmp_path):
 s=Store(tmp_path/'audit.db');a=Audit(s);a.start('x','SET_SPEED',{'value':360,'fog_token':'excluded'},sample());a.confirm('x','APPLIED');a.tick(sample(1));assert a.get('x')['after'] is None
 a.tick({**sample(2),'speed':360});a.tick({**sample(11),'speed':360});assert a.get('x')['followup'] is None
 a.tick({**sample(12),'speed':360});assert a.get('x')['followup']['speed']==360
 assert 'fog_token' not in str(a.export());s.close();s=Store(tmp_path/'audit.db');assert Audit(s).export()['actions'][0]['id']=='x';s.close()

def test_rejection_and_new_run_never_compared(tmp_path):
 s=Store(tmp_path/'a.db');a=Audit(s);a.start('x','PAUSE',{},sample());a.confirm('x','REJECTED','invalid');a.tick(sample(2,paused=True));assert a.get('x')['after'] is None
 a.start('y','PAUSE',{},sample());a.confirm('y','APPLIED');a.tick({**sample(3,paused=True),'run_id':'different'});assert a.get('y')['after'] is None;s.close()

def test_overlap_and_batch_allowlist(tmp_path):
 s=Store(tmp_path/'a.db');a=Audit(s);a.start('x','PAUSE',{},sample());a.start('y','RESUME',{},sample());a.confirm('x','APPLIED')
 from apps.distributed.experiments import now
 a.tick({**sample(paused=True),'at':now()});a.batch(dict(at=now(),requested=32,acknowledged=32,payload_bytes=400,duration_ms=20,http_status=200,fog_token='secret'))
 ev=a.export();assert next(i for i in ev['actions'] if i['id']=='x')['overlapping_actions']==1;assert 'secret' not in str(ev);s.close()
