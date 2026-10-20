"""Resultados da nuvem só resolvem itens explicitamente identificados e conhecidos."""
from .ingestion import Ingestion
from .platform_contract import to_canonical


def apply_result(store,batch,body,canonical=False):
    sent=dict(batch)
    ids=body.get('acknowledged') if isinstance(body,dict) else None
    rejected=body.get('rejected',[]) if isinstance(body,dict) else None
    if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids) or not isinstance(rejected,list):
        raise ValueError('Confirmação inválida')
    if len(ids)!=len(set(ids)) or not set(ids)<=sent.keys():raise ValueError('IDs de confirmação inválidos')
    refused=[]
    for row in rejected:
        key='id_mensagem' if canonical else 'event_id'
        if not isinstance(row,dict) or not isinstance(row.get(key),str) or row[key] not in sent:
            raise ValueError('ID de rejeição inválido')
        if row[key] in ids or row[key] in [r[0] for r in refused]:raise ValueError('Resultado conflitante')
        if type(row.get('retryable',False)) is not bool or not isinstance(row.get('error'),str):
            raise ValueError('Rejeição inválida')
        refused.append((row[key],row['error'],row.get('retryable',False)))
    platform=Ingestion(store)
    with store.lock,store.db:
        for identifier,error,retryable in refused:
            if retryable:continue
            platform.reject(sent[identifier],error,'cloud-canonical' if canonical else 'cloud-legacy')
            if canonical:store.db.execute('UPDATE iot_messages SET cloud_ack=2 WHERE id=?',(identifier,))
            else:
                store.db.execute('UPDATE events SET acked=2 WHERE id=?',(identifier,))
                try:message_id=to_canonical(sent[identifier])['id_mensagem']
                except ValueError:continue
                store.db.execute('UPDATE iot_messages SET cloud_ack=2 WHERE id=?',(message_id,))
        if canonical:store.db.executemany('UPDATE iot_messages SET cloud_ack=1 WHERE id=?',[(i,) for i in ids])
        else:
            store.db.executemany('UPDATE events SET acked=1 WHERE id=?',[(i,) for i in ids])
            for identifier in ids:
                try:message_id=to_canonical(sent[identifier])['id_mensagem']
                except ValueError:continue
                store.db.execute('UPDATE iot_messages SET cloud_ack=1 WHERE id=?',(message_id,))
    return ids


def transport_batch(items,key,max_bytes=262144):
    import json
    selected=[];size=len(json.dumps({key:[]}).encode())
    for identifier,message in items:
        extra=len(json.dumps(message,allow_nan=False).encode())+(2 if selected else 0)
        if size+extra>max_bytes:break
        selected.append((identifier,message));size+=extra
    if items and not selected:raise ValueError('Mensagem individual excede limite do transporte')
    raw=json.dumps({key:[message for _,message in selected]},allow_nan=False).encode()
    return selected,raw
