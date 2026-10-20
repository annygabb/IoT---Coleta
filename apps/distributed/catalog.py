"""Catálogo persistente, extensível por configuração e API local."""
import json
from pathlib import Path
from pydantic import Field, StrictInt, model_validator
from .platform_contract import ContractModel, IDENTIFIER


class Domain(ContractModel):
    id: str = Field(pattern=IDENTIFIER)
    name: str = Field(min_length=1,max_length=200)


class ProfileMeasure(ContractModel):
    name: str = Field(pattern=IDENTIFIER)
    unit: str = Field(pattern=r'^[!-~]{1,32}$')
    min: float
    max: float

    @model_validator(mode='after')
    def valid_range(self):
        if self.min > self.max: raise ValueError('Faixa invertida')
        return self


class Profile(ContractModel):
    id: str = Field(pattern=IDENTIFIER)
    domain: str = Field(pattern=IDENTIFIER)
    interval_seconds: StrictInt = Field(ge=1,le=31536000)
    measures: list[ProfileMeasure] = Field(min_length=1,max_length=32)

    @model_validator(mode='after')
    def distinct(self):
        if len({m.name for m in self.measures}) != len(self.measures):
            raise ValueError('Grandezas repetidas no perfil')
        return self


class Area(Domain):
    site: str = Field(pattern=IDENTIFIER)


class Device(ContractModel):
    id: str = Field(pattern=IDENTIFIER)
    profile: str = Field(pattern=IDENTIFIER)
    site: str = Field(pattern=IDENTIFIER)
    area: str | None = Field(default=None,pattern=IDENTIFIER)


MODELS={'domains':Domain,'profiles':Profile,'sites':Domain,'areas':Area,'devices':Device}


class Catalog:
    def __init__(self,store):
        self.store=store; self.db=store.db
        with store.lock, self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS iot_catalog(kind TEXT,id TEXT,payload TEXT NOT NULL,PRIMARY KEY(kind,id))')
        if not store.get('catalog:bootstrap:1'):
            config=Path(__file__).with_name('catalog-default.json')
            for kind,items in json.loads(config.read_text(encoding='utf-8')).items():
                for item in items:
                    if not self.get(kind,item['id']):self.create(kind,item)
            store.put('catalog:bootstrap:1',True)

    def get(self,kind,identifier):
        if kind not in MODELS:raise ValueError('Tipo de cadastro inválido')
        row=self.db.execute('SELECT payload FROM iot_catalog WHERE kind=? AND id=?',(kind,identifier)).fetchone()
        return json.loads(row[0]) if row else None

    def create(self,kind,item):
        if kind not in MODELS:raise ValueError('Tipo de cadastro inválido')
        item=MODELS[kind].model_validate(item).model_dump(exclude_none=True)
        with self.store.lock, self.db:
            if self.get(kind,item['id']):raise ValueError('Identificador já cadastrado')
            for field,target in [('domain','domains'),('profile','profiles'),('site','sites'),('area','areas')]:
                if item.get(field) and not self.get(target,item[field]):raise ValueError('Referência não cadastrada: '+field)
            if kind=='devices' and item.get('area') and self.get('areas',item['area'])['site']!=item['site']:
                raise ValueError('Área pertence a outro local')
            self.db.execute('INSERT INTO iot_catalog VALUES(?,?,?)',(kind,item['id'],json.dumps(item,allow_nan=False)))
        return item

    def list(self,kind,limit=100,offset=0):
        if kind not in MODELS or not 1<=limit<=1000 or offset<0:raise ValueError('Consulta inválida')
        rows=self.db.execute('SELECT payload FROM iot_catalog WHERE kind=? ORDER BY id LIMIT ? OFFSET ?',(kind,limit,offset)).fetchall()
        total=self.db.execute('SELECT count(*) FROM iot_catalog WHERE kind=?',(kind,)).fetchone()[0]
        return {'items':[json.loads(r[0]) for r in rows],'total':total,'limit':limit,'offset':offset}

    def enrich(self,message):
        device=self.get('devices',message['dispositivo'])
        if not device:raise ValueError('Dispositivo não cadastrado')
        profile=self.get('profiles',device['profile'])
        local=message.get('local',{})
        if local.get('site',device['site'])!=device['site'] or local.get('area',device.get('area'))!=device.get('area'):
            raise ValueError('Local diverge do cadastro do dispositivo')
        expected={m['name']:m for m in profile['measures']}; issues=[]
        for measure in message['medidas']:
            definition=expected.get(measure['grandeza'])
            if not definition:raise ValueError('Grandeza ausente no perfil: '+measure['grandeza'])
            if definition['unit']!=measure['unidade']:raise ValueError('Unidade diverge do perfil')
            if not definition['min']<=measure['valor']<=definition['max']:
                issues.append({'measure':measure['grandeza'],'reason':'OUT_OF_RANGE'})
        location={'site':device['site']}
        if device.get('area'):location['area']=device['area']
        return {**message,'local':location}, {'domain':profile['domain'],'profile':profile['id'],
            'quality':{'status':'SUSPECT' if issues else 'VALID','issues':issues}}
