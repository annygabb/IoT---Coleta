import pytest
from apps.distributed.core import Store,Edge,Fog,Canary,decode

def test_outbox_survives_restart(tmp_path):
    p=tmp_path/'s.db'; s=Store(p); s.add_batch([('a',{'x':1})]); s.close(); s=Store(p); assert s.pending()==[('a',{'x':1})]; s.close()

def test_duplicate_and_selective_ack(tmp_path):
    s=Store(tmp_path/'s.db'); s.add_batch([('a',{}),('b',{})]); s.add_batch([('a',{})]); s.ack(['a','unknown']); assert [i for i,_ in s.pending()]==['b']

def test_atomic_capacity(tmp_path):
    s=Store(tmp_path/'s.db',capacity=1)
    with pytest.raises(RuntimeError): s.add_batch([('a',{}),('b',{})])
    assert s.count()==0

def test_command_dedup_after_restart(tmp_path):
    p=tmp_path/'s.db'; s=Store(p); e=Edge(s); c={'action':'SET_SPEED','value':360,'command_id':'one'}; assert e.command(c); s.close(); s=Store(p); assert not Edge(s).command(c)

def test_fog_decides_from_snapshot(tmp_path):
    e=Edge(Store(tmp_path/'e.db')); f=Fog(Store(tmp_path/'f.db')); assert f.receive(e.snapshot()); assert f.received==32; assert f.outstanding
    sampled=Edge(Store(tmp_path/'sampled.db'),telemetry_every=5); assert len(sampled.snapshot()['events'])==32; assert sampled.snapshot()['events']==[]; assert len(sampled.snapshot()['state']['bins'])==32

def test_old_snapshot_keeps_history(tmp_path):
    e=Edge(Store(tmp_path/'e.db')); f=Fog(Store(tmp_path/'f.db')); old=e.snapshot(); latest=e.snapshot(); f.receive(latest); assert not f.receive(old); assert f.last['sequence']==2; assert f.store.count()==64

def test_full_batch_not_acknowledged(tmp_path):
    e=Edge(Store(tmp_path/'e.db')); f=Fog(Store(tmp_path/'f.db',capacity=31))
    with pytest.raises(RuntimeError): f.receive(e.snapshot())
    assert f.store.count()==0; assert f.last is None

def test_control_waits_for_application_ack(tmp_path):
    f=Fog(Store(tmp_path/'f.db')); c={'command_id':'a','action':'PAUSE'}; f.enqueue(c); assert f.outstanding; f.ack({'command_id':'x'}); assert f.outstanding; f.ack({'command_id':'a'}); assert not f.outstanding

def test_canary_rolls_back_selected():
    c=Canary(); c.start(['BIN-01','BIN-07'],True,now=0); c.observe(now=1); assert c.status=='OBSERVING'; c.observe(now=11); c.observe(now=12); assert c.status=='ROLLBACK'; assert c.selected==['BIN-01','BIN-07']

def test_healthy_canary_ready():
    c=Canary(); c.start(['BIN-01'],False,now=0)
    for n in range(1,12): c.observe(now=n)
    assert c.status=='READY_FOR_NEXT_WAVE'
    c.start(['BIN-07'],True,now=12)
    for n in range(23,29): c.observe(now=n)
    assert c.status=='ROLLBACK'
    assert c.versions['BIN-01']=='2.0'
    assert c.versions['BIN-07']=='1.0'

def test_unknown_control_rejected(tmp_path):
    with pytest.raises(ValueError): Edge(Store(tmp_path/'e.db')).command({'command_id':'a','action':'DELETE_ALL'})

def test_json_must_be_object():
    for s in ['null','[]','1','bad']:
        with pytest.raises(ValueError): decode(s)


def test_local_cloud_acceptance_is_not_pending(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from apps.distributed import runtime
    monkeypatch.setattr(runtime,'DATA',tmp_path)
    monkeypatch.setattr(runtime,'config',lambda:{'fog_token':'test-only-local-token'})
    sample=Edge(Store(tmp_path/'edge-sample.db')).snapshot()['events'][0]
    sample['event_id']='one'
    with TestClient(runtime.cloud_app()) as client:
        for _ in range(2):
            r=client.post('/ingest',json={'events':[sample]},headers={'x-fog-token':'test-only-local-token'})
            assert r.status_code==200
            assert r.json()['acknowledged']==['one']
    saved=Store(tmp_path/'cloud.db')
    assert saved.count()==0
    assert len(saved.history())==1
    saved.close()
