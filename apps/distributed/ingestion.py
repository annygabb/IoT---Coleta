"""Pipeline comum de ingestão: validação, catálogo, deduplicação e quarentena."""
import hashlib
import json
from .catalog import Catalog
from .platform_contract import validate_message, timestamp


def encode(value):
    return json.dumps(value,ensure_ascii=True,allow_nan=False,sort_keys=True,separators=(',',':'))


class Ingestion:
    def __init__(self,store,validate_catalog=True):
        self.store=store; self.db=store.db; self.catalog=Catalog(store)
        self.validate_catalog=validate_catalog
        with store.lock, self.db:
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS iot_messages(id TEXT PRIMARY KEY,device TEXT NOT NULL,
                    measured_at TEXT NOT NULL,received_at TEXT NOT NULL,payload TEXT NOT NULL,metadata TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS iot_message_time ON iot_messages(measured_at,id);
                CREATE INDEX IF NOT EXISTS iot_device_time ON iot_messages(device,measured_at,id);
                CREATE TABLE IF NOT EXISTS iot_quarantine(fingerprint TEXT PRIMARY KEY,payload TEXT NOT NULL,
                    reason TEXT NOT NULL,source TEXT NOT NULL,received_at TEXT NOT NULL);
            ''')
            columns={r[1] for r in self.db.execute('PRAGMA table_info(iot_messages)')}
            if 'cloud_route' not in columns:self.db.execute("ALTER TABLE iot_messages ADD COLUMN cloud_route TEXT NOT NULL DEFAULT 'canonical'")
            if 'cloud_ack' not in columns:self.db.execute('ALTER TABLE iot_messages ADD COLUMN cloud_ack INTEGER NOT NULL DEFAULT 0')
            if 'observed_at' not in columns:
                self.db.execute("ALTER TABLE iot_messages ADD COLUMN observed_at TEXT NOT NULL DEFAULT ''")
                self.db.execute('UPDATE iot_messages SET observed_at=measured_at')
                from .platform_contract import to_canonical
                for (raw,) in self.db.execute('SELECT payload FROM events').fetchall():
                    try:
                        event=json.loads(raw);message=to_canonical(event)
                        self.db.execute('UPDATE iot_messages SET observed_at=? WHERE id=?',(timestamp(event['emitted_at']),message['id_mensagem']))
                    except (ValueError,KeyError,TypeError):pass
            self.db.execute('CREATE INDEX IF NOT EXISTS iot_device_observed ON iot_messages(device,observed_at DESC,id)')

    def reject(self,message,reason,source='ingestion'):
        # JSON não padrão não entra no armazenamento; representação segura fica na DLQ.
        try:
            json.dumps(message,ensure_ascii=False,allow_nan=False).encode('utf-8')
            raw=encode(message)
        except (ValueError,TypeError,UnicodeError):raw=encode({'invalid_repr':repr(message)[:8192]})
        fingerprint=hashlib.sha256((source+'\0'+raw+'\0'+reason).encode()).hexdigest()
        from .core import utc
        self.db.execute('INSERT OR IGNORE INTO iot_quarantine VALUES(?,?,?,?,?)',(fingerprint,raw,reason,source,utc()))

    def batch(self,messages,source='http',cloud_route='canonical',observed_at=None):
        if not isinstance(messages,list) or not 1<=len(messages)<=5000:
            raise ValueError('Lote deve conter entre 1 e 5.000 mensagens')
        result={'accepted':[],'duplicates':[],'rejected':[]}
        from .core import utc
        with self.store.lock, self.db:
            for index,message in enumerate(messages):
                identifier=message.get('id_mensagem') if isinstance(message,dict) else None
                try:
                    normalized=validate_message(message)
                    if self.validate_catalog:normalized,metadata=self.catalog.enrich(normalized)
                    else:metadata={'quality':{'status':'SCHEMA_VALID','issues':[]}}
                    raw=encode(normalized)
                    observation=timestamp(observed_at) if observed_at else normalized['timestamp']
                    old=self.db.execute('SELECT payload FROM iot_messages WHERE id=?',(normalized['id_mensagem'],)).fetchone()
                    if old and old[0]!=raw:
                        raise ValueError('ID_CONFLICT: ID já existe com outro conteúdo')
                    if old:result['duplicates'].append(normalized['id_mensagem'])
                    else:
                        self.db.execute('INSERT INTO iot_messages(id,device,measured_at,received_at,payload,metadata,cloud_route,observed_at) VALUES(?,?,?,?,?,?,?,?)',(
                            normalized['id_mensagem'],normalized['dispositivo'],normalized['timestamp'],utc(),raw,encode(metadata),cloud_route,observation))
                    result['accepted'].append(normalized['id_mensagem'])
                except ValueError as ex:
                    reason=str(ex)
                    self.reject(message,reason,source)
                    result['rejected'].append({'index':index,'id_mensagem':identifier,
                        'code':'ID_CONFLICT' if reason.startswith('ID_CONFLICT') else 'INVALID_MESSAGE','error':reason})
        return result

    def mqtt(self,topic,message):
        try:
            normalized=validate_message(message)
            device=self.catalog.get('devices',normalized['dispositivo'])
            if not device:raise ValueError('Dispositivo não cadastrado')
            profile=self.catalog.get('profiles',device['profile'])
            expected=f"smartwaste/{device['site']}/{profile['domain']}/{device['id']}/telemetria"
            if topic!=expected:raise ValueError('Tópico diverge do cadastro ou da mensagem')
        except ValueError as ex:
            with self.store.lock,self.db:self.reject(message,str(ex),'mqtt-canonical')
            return {'accepted':[],'duplicates':[],'rejected':[{'index':0,'code':'TOPIC_OR_MESSAGE_INVALID','error':str(ex)}]}
        return self.batch([message],source='mqtt-canonical')

    def pending(self,limit=100):
        with self.store.lock:
            return [(i,json.loads(p)) for i,p in self.db.execute("SELECT id,payload FROM iot_messages WHERE cloud_route='canonical' AND cloud_ack=0 ORDER BY measured_at,id LIMIT ?",(limit,))]

    def ack(self,ids):
        with self.store.lock,self.db:self.db.executemany('UPDATE iot_messages SET cloud_ack=1 WHERE id=?',[(i,) for i in ids])

    def history(self,device=None,start=None,end=None,measure=None,site=None,area=None,limit=100,offset=0,order='desc'):
        if type(limit) is not int or not 1<=limit<=1000 or type(offset) is not int or offset<0 or order not in ('asc','desc'):
            raise ValueError('Paginação ou ordenação inválida')
        start=timestamp(start) if start else None;end=timestamp(end) if end else None
        if start and end and start>end:raise ValueError('Início posterior ao fim')
        where=[];params=[]
        for column,value,op in [('device',device,'='),('measured_at',start,'>='),('measured_at',end,'<=')]:
            if value is not None:where.append(f'{column}{op}?');params.append(value)
        if site is not None:where.append("json_extract(payload,'$.local.site')=?");params.append(site)
        if area is not None:where.append("json_extract(payload,'$.local.area')=?");params.append(area)
        if measure is not None:
            where.append("EXISTS(SELECT 1 FROM json_each(iot_messages.payload,'$.medidas') m WHERE json_extract(m.value,'$.grandeza')=?)");params.append(measure)
        clause=' WHERE '+' AND '.join(where) if where else ''
        with self.store.lock:
            total=self.db.execute('SELECT count(*) FROM iot_messages'+clause,params).fetchone()[0]
            rows=self.db.execute('SELECT payload,metadata,received_at FROM iot_messages'+clause+
                f' ORDER BY measured_at {order},id {order} LIMIT ? OFFSET ?',params+[limit,offset]).fetchall()
        return {'messages':[{**json.loads(p),**json.loads(m),'received_at':r} for p,m,r in rows],
            'total':total,'limit':limit,'offset':offset,'order':order}

    def latest(self,device):
        with self.store.lock:
            row=self.db.execute('SELECT payload,metadata,received_at,observed_at FROM iot_messages WHERE device=? ORDER BY observed_at DESC,measured_at DESC,id DESC LIMIT 1',(device,)).fetchone()
        if not row:return None
        payload,metadata,received,observed=row
        return {**json.loads(payload),**json.loads(metadata),'received_at':received,'observed_at':observed}

    def quarantine(self,limit=100,offset=0):
        if not 1<=limit<=1000 or offset<0:raise ValueError('Paginação inválida')
        with self.store.lock:
            total=self.db.execute('SELECT count(*) FROM iot_quarantine').fetchone()[0]
            rows=self.db.execute('SELECT fingerprint,payload,reason,source,received_at FROM iot_quarantine ORDER BY received_at DESC,fingerprint LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return {'items':[dict(id=i,payload=json.loads(p),error=r,source=s,received_at=t) for i,p,r,s,t in rows],
            'total':total,'limit':limit,'offset':offset}
