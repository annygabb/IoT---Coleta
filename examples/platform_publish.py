"""Cliente HTTP nativo: usa um dispositivo já cadastrado pelo catálogo inicial."""
import json
import urllib.request
import uuid
from datetime import datetime,timezone

message={'versao':'1.0','id_mensagem':str(uuid.uuid4()),'tipo':'telemetria',
    'dispositivo':'sensor-BIN-01','timestamp':datetime.now(timezone.utc).isoformat(),
    'medidas':[{'grandeza':'nivel_enchimento','valor':65,'unidade':'%'}]}
request=urllib.request.Request('http://127.0.0.1:8000/api/v1/ingestao',
    data=json.dumps(message).encode(),headers={'content-type':'application/json'})
with urllib.request.urlopen(request,timeout=5) as response:print(response.status,response.read().decode())
