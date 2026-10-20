import copy
import uuid
import pytest
from apps.distributed.core import Store, Edge, Fog


def platform():
    from apps.distributed.ingestion import Ingestion
    return Ingestion


def canonical(event):
    from apps.distributed.platform_contract import to_canonical
    return to_canonical(event)


def event(i=1):
    return dict(event_id=f'run-1-{i}-BIN-01', run_id='run-1', device_id='sensor-BIN-01',
                bin_id='BIN-01', sequence=i, simulated_at=f'2026-10-19T10:00:{i%60:02d}Z',
                emitted_at='2026-10-20T12:00:00Z', fill_pct=95, temperature_c=25,
                battery_pct=90, operational_state='CRITICA', sensor_status='ONLINE', firmware_version='1.0')


def test_adapter_stable_uuid_and_units():
    a=canonical(event()); b=canonical(event())
    assert a==b and str(uuid.UUID(a['id_mensagem']))==a['id_mensagem']
    assert a['timestamp']=='2026-10-19T10:00:01.000000Z'
    assert a['medidas'][0]==dict(grandeza='nivel_enchimento',valor=95.0,unidade='%')
    assert a['dispositivo']=='sensor-BIN-01'


@pytest.mark.parametrize('changes',[{'fill_pct':True},{'battery_pct':float('nan')},
    {'simulated_at':'2026-02-30T00:00:00Z'},{'emitted_at':'2026-10-19T10:00:00'},
    {'operational_state':'INVALID'},{'sequence':True}])
def test_adapter_rejects_invalid_legacy(changes):
    with pytest.raises(ValueError):canonical({**event(),**changes})


def test_catalog_persists_and_new_domain_needs_no_code(tmp_path):
    from apps.distributed.catalog import Catalog
    s=Store(tmp_path/'s.db'); c=Catalog(s)
    c.create('domains',{'id':'agricultura','name':'Agricultura'})
    c.create('profiles',{'id':'solo','domain':'agricultura','interval_seconds':3600,
        'measures':[{'name':'umidade_solo','unit':'%','min':0,'max':100}]})
    c.create('sites',{'id':'fazenda','name':'Fazenda'})
    c.create('areas',{'id':'talhao','site':'fazenda','name':'Talhão'})
    c.create('devices',{'id':'solo-01','profile':'solo','site':'fazenda','area':'talhao'})
    s.close(); s=Store(tmp_path/'s.db'); c=Catalog(s)
    assert c.get('devices','solo-01')['profile']=='solo'
    with pytest.raises(ValueError):c.create('devices',{'id':'outro','profile':'missing','site':'fazenda'})
    with pytest.raises(ValueError):c.create('domains',{'id':'agricultura','name':'Outro'})


def test_batch_isolates_invalid_and_deduplicates_after_restart(tmp_path):
    s=Store(tmp_path/'s.db'); p=platform()(s)
    a=canonical(event()); bad={**a,'id_mensagem':str(uuid.uuid4()),'timestamp':'2026-02-30T00:00:00Z'}
    result=p.batch([a,bad])
    assert result['accepted']==[a['id_mensagem']]
    assert len(result['rejected'])==1 and result['rejected'][0]['index']==1
    assert p.history()['total']==1 and p.quarantine()['total']==1
    s.close(); s=Store(tmp_path/'s.db'); p=platform()(s)
    assert p.batch([a])['duplicates']==[a['id_mensagem']]
    assert p.history()['total']==1


def test_uuid_collision_is_not_silently_accepted(tmp_path):
    p=platform()(Store(tmp_path/'s.db')); a=canonical(event()); p.batch([a])
    changed=copy.deepcopy(a); changed['medidas'][0]['valor']=40
    r=p.batch([changed]); assert not r['accepted'] and r['rejected'][0]['code']=='ID_CONFLICT'


def test_batch_5000_keeps_4997(tmp_path):
    p=platform()(Store(tmp_path/'s.db'))
    rows=[canonical(event(i)) for i in range(5000)]
    for i in (7,50,4999): rows[i]['versao']='99.0'
    r=p.batch(rows)
    assert len(r['accepted'])==4997 and len(r['rejected'])==3


def test_measurement_order_filters_and_latest(tmp_path):
    p=platform()(Store(tmp_path/'s.db'))
    old=canonical(event(1)); old['timestamp']='2026-10-17T10:00:00Z'
    new=canonical(event(2)); new['timestamp']='2026-10-19T10:00:00+00:00'
    p.batch([new]);p.batch([old])
    h=p.history(device='sensor-BIN-01',start='2026-10-17T00:00:00Z',order='asc',limit=1)
    assert h['total']==2 and h['messages'][0]['id_mensagem']==old['id_mensagem']
    assert p.latest('sensor-BIN-01')['id_mensagem']==new['id_mensagem']
    assert p.history(start='2026-10-18T00:00:00Z')['total']==1
    with pytest.raises(ValueError):p.history(start='bad')


def test_suspect_measure_is_preserved_with_quality(tmp_path):
    p=platform()(Store(tmp_path/'s.db')); a=canonical(event());a['medidas'][0]['valor']=121
    r=p.batch([a]);assert r['accepted']
    assert p.history()['messages'][0]['quality']['status']=='SUSPECT'


def test_same_id_bad_retry_does_not_overwrite_quarantine(tmp_path):
    p=platform()(Store(tmp_path/'s.db'));a=canonical(event());a['versao']='99'
    p.batch([a]);p.batch([a]);assert p.quarantine()['total']==1


def test_fog_mixed_snapshot_does_not_queue_bad_event(tmp_path):
    edge=Edge(Store(tmp_path/'e.db')); snap=edge.snapshot();snap['events'][0]['battery_pct']=-1
    fog=Fog(Store(tmp_path/'f.db'));fog.receive(snap)
    assert fog.store.count()==31
    assert platform()(fog.store).quarantine()['total']==1


def test_legacy_history_uses_measurement_not_arrival(tmp_path):
    s=Store(tmp_path/'s.db');new=event(2);old=event(1)
    s.add_batch([(new['event_id'],new)]);s.add_batch([(old['event_id'],old)])
    assert s.history()[0]['sequence']==2


def test_fog_rejects_previous_boot_snapshot_by_emission_time(tmp_path):
    a=Edge(Store(tmp_path/'a.db')); b=Edge(Store(tmp_path/'b.db'));fog=Fog(Store(tmp_path/'f.db'))
    old=a.snapshot(); new=b.snapshot()
    old['captured_at']='2026-10-19T10:00:00Z';new['captured_at']='2026-10-19T11:00:00Z'
    assert fog.receive(new)
    assert not fog.receive(old)
    assert fog.last['run_id']==new['run_id']


def test_mqtt_topic_must_match_registry(tmp_path):
    p=platform()(Store(tmp_path/'s.db')); a=canonical(event())
    result=p.mqtt('smartwaste/brasilia/residuos/sensor-BIN-01/telemetria',a)
    assert result['accepted']
    result=p.mqtt('smartwaste/brasilia/residuos/sensor-BIN-02/telemetria',a)
    assert result['rejected'] and p.quarantine()['total']==1


def test_cloud_results_are_atomic_and_selective(tmp_path):
    from apps.distributed.sync_result import apply_result
    s=Store(tmp_path/'s.db');a=event(1);b=event(2)
    s.add_batch([(a['event_id'],a),(b['event_id'],b)])
    batch=s.pending()
    with pytest.raises(ValueError):apply_result(s,batch,{'acknowledged':['foreign']})
    assert s.count()==2
    with pytest.raises(ValueError):apply_result(s,batch,{'acknowledged':[a['event_id']],
        'rejected':[{'event_id':'foreign','error':'bad'}]})
    assert s.count()==2
    result=apply_result(s,batch,{'acknowledged':[a['event_id']],
        'rejected':[{'event_id':b['event_id'],'error':'invalid date','retryable':False}]})
    assert result==[a['event_id']] and s.count()==0
    assert platform()(s).quarantine()['total']==1
    assert len(s.history())==2


def test_transient_cloud_rejection_stays_pending(tmp_path):
    from apps.distributed.sync_result import apply_result
    s=Store(tmp_path/'s.db');s.add_batch([('a',event())])
    apply_result(s,s.pending(),{'acknowledged':[],
        'rejected':[{'event_id':'a','error':'temporarily unavailable','retryable':True}]})
    assert s.count()==1


def test_platform_pending_and_ack_are_separate_from_legacy(tmp_path):
    p=platform()(Store(tmp_path/'s.db')); a=canonical(event())
    p.batch([a]); assert len(p.pending())==1
    p.ack([a['id_mensagem']]); assert not p.pending()
    assert p.history()['total']==1


@pytest.fixture
def api(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from apps.distributed import runtime
    class Network:
        connected=True
        def __init__(self,role):pass
        def drain(self):return iter(())
        def send(self,*args):pass
        def close(self):pass
    monkeypatch.setattr(runtime,'DATA',tmp_path)
    monkeypatch.setattr(runtime,'Network',Network)
    monkeypatch.setattr(runtime,'config',lambda:{'fog_token':'test-only-token','cloud_url':'http://127.0.0.1:9'})
    with TestClient(runtime.fog_app()) as client:
        yield client


def test_http_platform_contract_and_partial_batch(api):
    a=canonical(event());bad={**a,'versao':'99'}
    response=api.post('/api/v1/ingestao/lote',json={'messages':[a,bad]})
    assert response.status_code==202
    assert len(response.json()['accepted'])==1 and len(response.json()['rejected'])==1
    assert api.get('/api/v1/quarentena').json()['total']==1
    assert api.get('/api/v1/dispositivos/sensor-BIN-01/telemetria').json()['total']==1
    assert api.get('/api/v1/dispositivos/sensor-BIN-01/estado').json()['id_mensagem']==a['id_mensagem']
    assert api.post('/api/v1/ingestao',json=bad).status_code==400
    assert api.get('/api/v1/telemetria?start=bad').status_code==400
    assert api.get('/api/v1/telemetria?limit=0').status_code==422
    assert api.get('/api/v1/telemetria?order=invalid').status_code==422
    schema=api.get('/contracts/telemetry-1.0.schema.json').json()
    assert schema['properties']['versao']['const']=='1.0'
    assert api.get('/contracts/asyncapi.json').json()['asyncapi']=='3.0.0'
    assert api.get('/api/v1/catalogo/perfis').json()['total']>=1


def test_api_registers_rural_sensor_and_ingests_it(api):
    for path,item in [
        ('catalogo/dominios',{'id':'agricultura','name':'Agricultura'}),
        ('catalogo/perfis',{'id':'solo','domain':'agricultura','interval_seconds':3600,
            'measures':[{'name':'umidade_solo','unit':'%','min':0,'max':100}]}),
        ('sites',{'id':'fazenda','name':'Fazenda'}),
        ('areas',{'id':'talhao','site':'fazenda','name':'Talhão 7'}),
        ('dispositivos',{'id':'solo-01','profile':'solo','site':'fazenda','area':'talhao'})]:
        assert api.post('/api/v1/'+path,json=item).status_code==201
    a=canonical(event());a['dispositivo']='solo-01';a['local']={'site':'fazenda','area':'talhao'}
    a['medidas']=[{'grandeza':'umidade_solo','valor':23.5,'unidade':'%'}]
    assert api.post('/api/v1/ingestao',json=a).status_code==202
    h=api.get('/api/v1/telemetria?site=fazenda&area=talhao&measure=umidade_solo').json()
    assert h['total']==1 and h['messages'][0]['domain']=='agricultura'


def test_old_sqlite_is_migrated_without_losing_payload(tmp_path):
    import sqlite3,json
    path=tmp_path/'old.db';db=sqlite3.connect(path)
    db.execute('CREATE TABLE events(id TEXT PRIMARY KEY,payload TEXT NOT NULL,acked INTEGER NOT NULL DEFAULT 0)')
    db.execute('INSERT INTO events VALUES(?,?,0)',('one',json.dumps(event())))
    db.commit();db.close();s=Store(path)
    assert s.pending()[0][1]==event()
    assert s.history()[0]['event_id']==event()['event_id']


@pytest.mark.parametrize('value',['0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00'])
def test_utc_overflow_is_one_rejection_not_a_batch_failure(tmp_path,value):
    p=platform()(Store(tmp_path/'s.db'));bad=canonical(event());bad['timestamp']=value
    good=canonical(event(2));r=p.batch([bad,good])
    assert r['accepted']==[good['id_mensagem']] and len(r['rejected'])==1


def test_latest_across_boots_uses_real_observation_time(tmp_path):
    a=Edge(Store(tmp_path/'a.db'));b=Edge(Store(tmp_path/'b.db'));f=Fog(Store(tmp_path/'f.db'))
    a.engine.clock.sim_time_seconds+=3600
    f.receive(a.snapshot());fresh=b.snapshot();f.receive(fresh)
    expected=canonical(fresh['events'][0])['id_mensagem']
    assert f.ingestion.latest('sensor-BIN-01')['id_mensagem']==expected


def test_transport_batches_respect_byte_limit():
    from apps.distributed.sync_result import transport_batch
    a=canonical(event());a['medidas']=[{'grandeza':f'm{i}','valor':3.14,'unidade':'x'*32} for i in range(32)]
    items=[(str(i),a) for i in range(100)]
    batch,raw=transport_batch(items,'messages')
    assert len(raw)<=262144 and 0<len(batch)<100
    import json
    assert len(json.loads(raw)['messages'])==len(batch)


def test_invalid_unicode_is_quarantined_without_rolling_back_good_messages(tmp_path):
    p=platform()(Store(tmp_path/'s.db'));a=canonical(event());bad={**canonical(event(2)),'extra':'\ud800'}
    result=p.batch([a,bad]);assert result['accepted']==[a['id_mensagem']]
    assert len(result['rejected'])==1 and p.history()['total']==1
    import json
    json.dumps(p.quarantine(),ensure_ascii=False).encode('utf-8')


def test_cloud_legacy_conflicting_retry_is_not_acknowledged(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from apps.distributed import runtime
    monkeypatch.setattr(runtime,'DATA',tmp_path)
    monkeypatch.setattr(runtime,'config',lambda:{'fog_token':'test-only-token'})
    with TestClient(runtime.cloud_app()) as client:
        headers={'x-fog-token':'test-only-token'};a=event()
        assert client.post('/ingest',json={'events':[a]},headers=headers).json()['acknowledged']
        b={**a,'fill_pct':50}
        result=client.post('/ingest',json={'events':[b]},headers=headers).json()
        assert result['acknowledged']==[] and result['rejected'][0]['error']=='ID_CONFLICT'
