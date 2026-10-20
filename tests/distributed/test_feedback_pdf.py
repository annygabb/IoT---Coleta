import time
from fastapi.testclient import TestClient
from apps.distributed.core import Edge,Fog,Store
from apps.distributed import runtime

def test_rejected_command_is_available_for_feedback(tmp_path):
    f=Fog(Store(tmp_path/'fog.db'))
    f.enqueue({'command_id':'c1','action':'CANARY_START'})
    f.ack({'command_id':'c1','status':'REJECTED','error':'Campanha em andamento'})
    assert f.state()['architecture']['command_results']['c1']['status']=='REJECTED'
    assert not f.outstanding

def test_pdf_download_and_cloud_feedback(monkeypatch,tmp_path):
    edge=Edge(Store(tmp_path/'source.db'));snapshot=edge.snapshot()
    class Network:
        connected=True
        def __init__(self,role):self.sent=False
        def drain(self):
            if not self.sent:self.sent=True;yield 'smartwaste/df/snapshots',snapshot
        def send(self,*args):pass
        def close(self):pass
    monkeypatch.setattr(runtime,'DATA',tmp_path)
    monkeypatch.setattr(runtime,'Network',Network)
    monkeypatch.setattr(runtime,'config',lambda:{'fog_token':'test-secret','cloud_url':'http://127.0.0.1:9'})
    with TestClient(runtime.fog_app()) as client:
        for _ in range(30):
            if client.get('/api/state').json().get('bins'):break
            time.sleep(.05)
        response=client.post('/api/control',json={'action':'CLOUD_LINK','value':False})
        assert response.json()['cloud_status']=='DISCONNECTED'
        assert client.get('/api/state').json()['architecture']['cloud_status']=='DISCONNECTED'
        response=client.get('/api/export.pdf?limit=2')
        assert response.status_code==200
        assert response.headers['content-type']=='application/pdf'
        assert 'smartwaste-dados.pdf' in response.headers['content-disposition']
        assert response.content.startswith(b'%PDF-')
        assert client.get('/api/export.pdf?limit=0').status_code==422
        assert client.get('/api/export.pdf?limit=10001').status_code==422
        response=client.post('/api/control',json={'action':'CLOUD_LINK','value':True})
        assert response.json()['cloud_status']=='CONNECTING'
        assert client.get('/ui-state.js').status_code==200
