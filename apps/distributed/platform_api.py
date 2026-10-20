"""API v1 local de integração. Não abre portas nem altera a interface do laboratório."""
import json
from pathlib import Path
from fastapi import HTTPException, Query, Request


async def read_json(req,max_bytes=8*1024*1024):
    origin=req.headers.get('origin')
    if origin and origin not in ('http://127.0.0.1:8000','http://localhost:8000'):
        raise HTTPException(403,'Origem não autorizada para operação local')
    if req.headers.get('content-type','').split(';')[0]!='application/json':
        raise HTTPException(415,'Use application/json')
    raw=bytearray()
    async for chunk in req.stream():
        raw.extend(chunk)
        if len(raw)>max_bytes:raise HTTPException(413,'Limite de 8 MiB')
    try:return json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Número não finito')))
    except (ValueError,UnicodeDecodeError):raise HTTPException(400,'JSON inválido')


def install_platform_routes(app,get_ingestion):
    def call(function,*args,**kwargs):
        try:return function(*args,**kwargs)
        except ValueError as ex:raise HTTPException(400,str(ex))

    @app.get('/contracts/telemetry-1.0.schema.json')
    def schema():
        from .platform_contract import Telemetry
        return {'$schema':'https://json-schema.org/draft/2020-12/schema',**Telemetry.model_json_schema()}

    @app.get('/contracts/asyncapi.json')
    def asyncapi():
        return json.loads((Path(__file__).parents[2]/'contracts/asyncapi.json').read_text())

    @app.post('/api/v1/ingestao',status_code=202)
    async def single(req:Request):
        result=call(get_ingestion().batch,[await read_json(req)])
        if result['rejected']:raise HTTPException(400,result['rejected'])
        return result

    @app.post('/api/v1/ingestao/lote',status_code=202)
    async def batch(req:Request):
        body=await read_json(req)
        if not isinstance(body,dict):raise HTTPException(400,'Corpo deve ser objeto')
        return call(get_ingestion().batch,body.get('messages'))

    @app.get('/api/v1/telemetria')
    def history(device:str|None=None,start:str|None=None,end:str|None=None,measure:str|None=None,
                site:str|None=None,area:str|None=None,limit:int=Query(100,ge=1,le=1000),
                offset:int=Query(0,ge=0),order:str=Query('desc',pattern='^(asc|desc)$')):
        return call(get_ingestion().history,device=device,start=start,end=end,measure=measure,
                    site=site,area=area,limit=limit,offset=offset,order=order)

    @app.get('/api/v1/dispositivos/{identifier}/telemetria')
    def device_history(identifier:str,start:str|None=None,end:str|None=None,measure:str|None=None,
            limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0),order:str=Query('desc',pattern='^(asc|desc)$')):
        return call(get_ingestion().history,device=identifier,start=start,end=end,measure=measure,limit=limit,offset=offset,order=order)

    @app.get('/api/v1/dispositivos/{identifier}/estado')
    def latest(identifier:str):
        value=get_ingestion().latest(identifier)
        if not value:raise HTTPException(404,'Sem leitura para o dispositivo')
        return value

    @app.get('/api/v1/quarentena')
    def quarantine(limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0)):
        return get_ingestion().quarantine(limit=limit,offset=offset)

    def create_handler(kind):
        async def create(req:Request):return call(get_ingestion().catalog.create,kind,await read_json(req))
        return create

    def list_handler(kind):
        def listing(limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0)):
            return get_ingestion().catalog.list(kind,limit=limit,offset=offset)
        return listing

    for path,kind in [('catalogo/dominios','domains'),('catalogo/perfis','profiles'),
                      ('sites','sites'),('areas','areas'),('dispositivos','devices')]:
        app.add_api_route('/api/v1/'+path,create_handler(kind),methods=['POST'],status_code=201,name='create_'+kind)
        app.add_api_route('/api/v1/'+path,list_handler(kind),methods=['GET'],name='list_'+kind)

    @app.get('/api/v1/sites/{identifier}/areas')
    def site_areas(identifier:str,limit:int=Query(100,ge=1,le=1000),offset:int=Query(0,ge=0)):
        db=get_ingestion().store.db
        where="kind='areas' AND json_extract(payload,'$.site')=?"
        total=db.execute('SELECT count(*) FROM iot_catalog WHERE '+where,(identifier,)).fetchone()[0]
        rows=db.execute('SELECT payload FROM iot_catalog WHERE '+where+' ORDER BY id LIMIT ? OFFSET ?',(identifier,limit,offset))
        return {'items':[json.loads(r[0]) for r in rows],'total':total,'limit':limit,'offset':offset}
