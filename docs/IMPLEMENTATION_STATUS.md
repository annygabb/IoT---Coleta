# Estado da implementação - 20/10/2026

O repositório agora contém o código distribuído testado. A versão base continua em `run_lab.py`; a versão atual abre com `run_distributed.py`.

| Implementado | Evidência |
|---|---|
| MQTT real entre processos | Ensaio com AMQTT e Paho |
| Fila persistente e reenvio | Testes de reinício e ACK seletivo |
| Contrato canônico de telemetria 1.0 | Schema e AsyncAPI em `contracts/` |
| Catálogo persistente por API | Domínio, perfil, local, área e dispositivo |
| Validação individual e quarentena | Teste de 5.000 mensagens: 4.997 aceitas e três isoladas |
| Histórico por medição | Filtros, paginação e proteção de estado após reinício |
| Código da nova API de nuvem | Preparado, sem implantação remota nesta etapa |

O painel e as rotas permanecem preservados. Novas leituras canônicas permanecem na fila local se o Supabase antigo ainda responder 404 ao endpoint preparado. O fluxo legado das lixeiras continua compatível.

Faltam: teste real de 72 horas, dimensionamento da fila, autenticação de usuários e papéis, TLS/ACL MQTT por dispositivo, cifragem local e outros requisitos da plataforma completa. Não declarar conformidade integral ou SLA com base nos testes locais.

Detalhes e passo a passo: [guia da atualização](ATUALIZACAO_PLATAFORMA_IOT.md).
