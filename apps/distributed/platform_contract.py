"""Contrato de telemetria 1.0 e adaptação do formato legado, sem dependência de rede."""
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, field_validator, model_validator

IDENTIFIER = r'^[A-Za-z0-9_-]{1,100}$'


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})', value):
        raise ValueError('Data deve usar ISO 8601 com fuso horário')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    except (ValueError,OverflowError) as ex:
        raise ValueError('Data UTC fora do calendário suportado') from ex


class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Measure(ContractModel):
    grandeza: str = Field(pattern=IDENTIFIER)
    valor: StrictFloat
    unidade: str = Field(pattern=r'^[!-~]{1,32}$')


class Location(ContractModel):
    site: str = Field(pattern=IDENTIFIER)
    area: str | None = Field(default=None, pattern=IDENTIFIER)


class Telemetry(ContractModel):
    versao: Literal['1.0']
    id_mensagem: str = Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',json_schema_extra={'format':'uuid'})
    dispositivo: str = Field(pattern=IDENTIFIER)
    tipo: Literal['telemetria']
    timestamp: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$',json_schema_extra={'format':'date-time'})
    via: str | None = Field(default=None, pattern=IDENTIFIER)
    local: Location | None = None
    medidas: list[Measure] = Field(min_length=1, max_length=32)

    @field_validator('id_mensagem')
    @classmethod
    def identifier(cls, value):
        parsed = uuid.UUID(value)
        if str(parsed) != value:
            raise ValueError('UUID deve usar formato canônico minúsculo')
        return value

    @field_validator('timestamp')
    @classmethod
    def measured_at(cls, value):
        return timestamp(value)

    @model_validator(mode='after')
    def unique_measures(self):
        names = [m.grandeza for m in self.medidas]
        if len(names) != len(set(names)):
            raise ValueError('Grandezas repetidas na mesma mensagem')
        return self


def validate_message(value):
    return Telemetry.model_validate(value).model_dump(exclude_none=True)


def validate_legacy(event):
    if not isinstance(event, dict):
        raise ValueError('Evento deve ser objeto')
    for key in ('event_id','run_id','device_id','bin_id','firmware_version'):
        if not isinstance(event.get(key), str) or not re.fullmatch(r'[-\w.]{1,100}', event[key], re.ASCII):
            raise ValueError('Identificador inválido: '+key)
    if type(event.get('sequence')) is not int or not 0 <= event['sequence'] <= 9007199254740991:
        raise ValueError('Sequência inválida')
    for key, low, high in (('fill_pct',0,120),('temperature_c',-50,150),('battery_pct',0,100)):
        value=event.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('Valor inválido: '+key)
    timestamp(event.get('simulated_at')); timestamp(event.get('emitted_at'))
    if event.get('operational_state') not in ('NORMAL','ATENCAO','ALTA','CRITICA','TRANSBORDO','EM_COLETA'):
        raise ValueError('Estado operacional inválido')
    if event.get('sensor_status') not in ('ONLINE','STALE','OFFLINE','FAULTY'):
        raise ValueError('Saúde do sensor inválida')
    return event


def to_canonical(event):
    validate_legacy(event)
    # Namespace e ID legado tornam a conversão determinística inclusive após reinício.
    identifier=str(uuid.uuid5(uuid.NAMESPACE_URL, 'smartwaste:telemetry:'+event['event_id']))
    return validate_message(dict(versao='1.0',id_mensagem=identifier,
        dispositivo=event['device_id'],tipo='telemetria',timestamp=event['simulated_at'],
        via='edge-df-01',local={'site':'brasilia'},medidas=[
            {'grandeza':name,'valor':event[key],'unidade':unit}
            for name,key,unit in [('nivel_enchimento','fill_pct','%'),
                ('temperatura','temperature_c','Cel'),('bateria','battery_pct','%')]]))


LEGACY_FIELDS=('event_id','run_id','device_id','bin_id','sequence','simulated_at','emitted_at',
    'fill_pct','temperature_c','battery_pct','operational_state','sensor_status','firmware_version')


def legacy_identity(event):
    return {key:timestamp(event[key]) if key in ('simulated_at','emitted_at') else event[key]
            for key in LEGACY_FIELDS}
