# SmartWaste DF - integração IoT, versão de 20/10/2026

**Engenharia de Software: Anny, Arthur, Eduardo e Jéssica**  
Projeto: https://github.com/annygabb/IoT---Coleta

Esta versão implementa os quatro pontos aprovados: mensagens padronizadas, catálogo de sensores, separação de erros de lote e tratamento de dados atrasados. O painel e o motor de rotas foram preservados. A apresentação PowerPoint não foi alterada nesta etapa.

## 1. Como iniciar no Windows

Extraia o ZIP em uma pasta nova. Não substitua a pasta da versão anterior antes de guardar uma cópia dos seus dados.

- **Teste inteiramente local:** abra `INICIAR_LOCAL.bat`. Ele usa Python 3.12, instala as dependências e inicia MQTT, edge, fog e nuvem emulada.
- **Supabase já configurado:** no pacote privado, abra `ATUALIZAR_E_ABRIR.bat`. O JSON de conexão já acompanha esse pacote. O pacote público não inclui esse arquivo.
- O painel abre em `http://127.0.0.1:8000`. Mantenha o terminal aberto; Ctrl+C encerra os serviços.

Execução manual, no CMD:

```bat
py -3.12 -m venv .venv312
.venv312\Scripts\python -m pip install -r requirements-distributed.txt
.venv312\Scripts\python run_distributed.py
```

Para usar a conexão existente, o último comando fica:

```bat
.venv312\Scripts\python run_distributed.py --cloud-config SmartWaste_Conexao_Privada.json
```

Os comandos Python foram verificados no ambiente Linux desta entrega. Os arquivos `.bat` foram preparados para o Windows e precisam ser executados no seu computador para validar o comportamento da instalação local.

## 2. O que mudou, e por quê

| Ponto | Antes | Agora | Por que isso ajuda |
|---|---|---|---|
| Mensagens | Campos específicos de lixeira | Envelope canônico 1.0 e adaptador do formato existente | Outros sensores podem usar a integração sem conhecer a estrutura do simulador. |
| Cadastro | Sensores definidos pelo motor | Catálogo persistente de domínio, perfil, local, área e dispositivo | Um sensor de solo pode ser cadastrado por API, sem alterar o motor de coleta. |
| Lotes | Falha de um item podia bloquear o lote inteiro | Válidos são aceitos; inválidos têm resultado individual e quarentena | Uma bateria inválida não impede salvar as outras leituras. |
| Histórico | Ordem de chegada/inserção | Ordenação, filtros e paginação pelo horário da medição | Leituras atrasadas entram no lugar correto da série. |
| Último estado | Sequência protegia principalmente o mesmo boot | Observação real separada do relógio simulado | Reiniciar a simulação não faz `/estado` escolher a leitura do boot anterior. |
| Envio | Limite apenas de quantidade | Limites de quantidade e bytes no sincronizador | Um conjunto de mensagens grandes não fica preso em erro 413. |
| Deduplicação | Identificador único | ID estável e detecção de conteúdo conflitante | Um ID repetido com outro conteúdo não é tratado como reenvio válido. |

Os ganhos são comportamentos comprovados pelos testes, não percentuais de economia ou de desempenho medidos em produção.

## 3. Mensagem canônica em linguagem simples

“Canônica” significa um formato comum. Cada leitura informa quem mediu, quando mediu e quais valores encontrou.

```json
{
  "versao": "1.0",
  "id_mensagem": "550e8400-e29b-41d4-a716-446655440000",
  "dispositivo": "solo-01",
  "tipo": "telemetria",
  "timestamp": "2026-10-20T12:00:00Z",
  "local": {"site": "fazenda", "area": "talhao-07"},
  "medidas": [
    {"grandeza": "umidade_solo", "valor": 23.5, "unidade": "%"}
  ]
}
```

- `versao`: identifica as regras do contrato. Esta entrega aceita 1.0.
- `id_mensagem`: UUID único. Reenviar a mesma leitura conserva o ID; outra leitura recebe outro ID.
- `dispositivo`: precisa estar no catálogo local.
- `timestamp`: exige data possível e fuso horário. A API normaliza para UTC.
- `medidas`: lista de grandezas, valores numéricos finitos e unidades compatíveis com o perfil.
- `local`: se omitido, a ingestão local usa o cadastro. Se enviado com outro local, a mensagem é recusada.

No SmartWaste, o adaptador gera um UUID determinístico a partir do `event_id` existente, inclusive para eventos antigos sem envelope canônico. Os campos antigos continuam disponíveis para o painel e para a função hospedada atual. O envelope é adicionado a cada evento do snapshot MQTT; isso aumenta os bytes transmitidos no laboratório. Não foi medida a diferença de consumo de energia.

Os contratos estão em `contracts/telemetry-1.0.schema.json` e `contracts/asyncapi.json`, também disponíveis em `/contracts/...` na API local. O contrato cobre **telemetria** nesta etapa; não declara suporte completo a eventos, comandos canônicos ou GeoJSON do documento de referência.

## 4. Como funciona o catálogo

| Cadastro | Exemplo | Relação |
|---|---|---|
| Domínio | `residuos`, `agricultura` | Agrupa tipos de aplicação. |
| Perfil | `lixeira`, `solo` | Define grandezas, unidades, faixas válidas e intervalo esperado. |
| Local | `brasilia`, `fazenda` | Lugar onde o dispositivo está instalado. |
| Área | `talhao-07` | Subdivisão de um local. |
| Dispositivo | `sensor-BIN-01`, `solo-01` | Usa um perfil e pertence a um local; área é opcional. |

O arquivo `apps/distributed/catalog-default.json` carrega inicialmente o cenário de resíduos e os 32 sensores. Cadastros novos persistem no SQLite. Não há tela nova de cadastro: a gestão desta etapa é feita por API. Atualização e exclusão de cadastros não estão implementadas.

Uma grandeza não prevista ou unidade incompatível é recusada. Uma medida numérica fora da faixa do perfil é preservada com `quality.status = SUSPECT`: assim, o dado suspeito fica identificável para análise. Isso difere de um erro estrutural, como uma data impossível. O perfil armazena o intervalo esperado; a determinação automática de presença online/offline por perfil permanece para outra etapa.

## 5. API local e teste passo a passo

Com o laboratório aberto, acesse `http://127.0.0.1:8000/docs`. A documentação interativa permite executar os exemplos abaixo. Use **Try it out**, informe o JSON e clique em **Execute**.

### Passo 1: cadastrar um domínio

`POST /api/v1/catalogo/dominios`

```json
{"id":"agricultura","name":"Agricultura"}
```

### Passo 2: cadastrar o perfil

`POST /api/v1/catalogo/perfis`

```json
{"id":"solo","domain":"agricultura","interval_seconds":3600,"measures":[{"name":"umidade_solo","unit":"%","min":0,"max":100}]}
```

### Passo 3: cadastrar o local e a área

`POST /api/v1/sites`

```json
{"id":"fazenda","name":"Fazenda didática"}
```

`POST /api/v1/areas`

```json
{"id":"talhao-07","site":"fazenda","name":"Talhão 07"}
```

### Passo 4: cadastrar o sensor

`POST /api/v1/dispositivos`

```json
{"id":"solo-01","profile":"solo","site":"fazenda","area":"talhao-07"}
```

### Passo 5: enviar uma leitura

Use a mensagem da seção 3 em `POST /api/v1/ingestao`. O retorno esperado é 202 com o ID em `accepted`. Se repetir o mesmo conteúdo, o retorno também inclui esse ID em `duplicates`, sem criar outra linha.

Se o ID já tiver sido usado com outro conteúdo, o retorno indica `ID_CONFLICT`. Gere um novo UUID para uma nova medição. Não altere o conteúdo de um evento que já foi aceito.

### Passo 6: testar erro individual

Em `POST /api/v1/ingestao/lote`, envie `{"messages":[mensagem_valida,mensagem_invalida]}` com objetos JSON completos no lugar desses nomes. Na inválida, use outro UUID e `timestamp` igual a `2026-02-30T12:00:00Z`.

O endpoint de lote retorna 202, lista os aceitos em `accepted` e o erro com índice em `rejected`. O índice começa em zero. Em `/api/v1/quarentena`, confira o conteúdo recusado e o motivo. O endpoint individual retorna 400 para mensagem inválida. Repetições do mesmo erro não criam novas linhas idênticas de quarentena.

Limites: até 5.000 mensagens e 8 MiB na API local de lote; até 100 mensagens e 256 KiB em cada requisição de sincronização com a nuvem. O sincronizador divide o envio pelo número de itens e pelos bytes reais do JSON.

### Passo 7: consultar dados atrasados

Envie outra leitura, com UUID novo e data dois dias anterior. Consulte:

```text
/api/v1/telemetria?device=solo-01&order=asc&limit=100&offset=0
/api/v1/telemetria?site=fazenda&area=talhao-07&measure=umidade_solo
/api/v1/telemetria?start=2026-10-18T00:00:00Z&end=2026-10-21T00:00:00Z
/api/v1/dispositivos/solo-01/estado
```

O histórico mostra a leitura na posição da medição. O último estado do sensor genérico continua sendo a leitura de timestamp mais recente, não a última recebida.

## 6. Horários e reinício: por que há mais de uma data

No simulador existem dois relógios: o cenário pode avançar uma hora enquanto passam poucos segundos reais.

- `simulated_at`: horário dentro do cenário; é o eixo do histórico canônico adaptado do SmartWaste.
- `emitted_at`: horário real em que a edge emitiu a leitura.
- `received_at`: horário em que a camada receptora a guardou.
- `captured_at`: horário real do snapshot; impede um snapshot de um boot antigo de regredir o painel.
- `observed_at`: no último estado adaptado, conserva a emissão real; nos sensores canônicos nativos, usa o próprio timestamp de medição.

Por isso, `/estado` de uma lixeira adaptada pode retornar o boot mais novo, mesmo que seu relógio simulado tenha reiniciado para uma data anterior. O histórico por medição e o estado operacional mais recente respondem a perguntas diferentes.

Sensores nativos precisam manter o relógio de medição correto. Não foram implementados NTP, correção de relógio defeituoso ou alarmes genéricos. Leituras externas de solo são guardadas e consultadas, mas não passam a controlar rotas ou irrigação automaticamente.

## 7. MQTT nativo

O tópico desta instalação local é:

```text
smartwaste/{site}/{dominio}/{dispositivo}/telemetria
```

Exemplo: `smartwaste/fazenda/agricultura/solo-01/telemetria`.

Publique a mesma mensagem canônica com QoS 1. A ingestão compara tópico, dispositivo, local e domínio com o catálogo. A confirmação de aplicação sai no mesmo caminho com final `/ack` e contém `accepted`, `duplicates` e `rejected`.

O tópico correto é validado na aplicação. Isso **não implementa ACL no broker**. O broker continua restrito ao computador, sem TLS/autenticação individual; não foi aberto à rede. O PUBACK do protocolo não substitui a confirmação de gravação da aplicação. Um publicador nativo deve conservar sua própria pendência até receber essa confirmação.

## 8. Quarentena, pendência e confirmação

| Estado | Significado |
|---|---|
| Pendente | Ainda deve ser enviado ou reenviado. |
| Confirmado pela nuvem | A nuvem informou o ID após persistir o evento. |
| Quarentena | Evento inválido ou conflito permanente, conservado para diagnóstico; não representa entrega à nuvem. |
| Suspeito | Estrutura válida, mas valor fora da faixa do perfil; dado conservado com indicação de qualidade. |

Falhas de rede continuam pendentes, com espera progressiva. Rejeição transitória explícita também continua pendente. Uma rejeição permanente identificada pela nuvem é isolada; IDs estranhos, repetidos ou conflitantes numa resposta não resolvem silenciosamente a fila.

Na tabela legada, `acked=0` significa pendente, `acked=1` confirmado e `acked=2` isolado. Nos novos registros, `cloud_ack` usa os mesmos valores. O histórico original é conservado. Não há botão de reprocessamento da quarentena nesta etapa; uma correção deve ser analisada e reenviada com identidade apropriada, sem apagar a evidência do erro.

## 9. Supabase: o que está pronto e o que está hospedado

O laboratório usa HTTPS com a configuração existente quando iniciado pelo modo Supabase. As lixeiras continuam no contrato legado aceito pela função já publicada; o adaptador local faz a validação preventiva e registra a forma canônica localmente.

O código atualizado da função está no pacote, **mas não foi publicado por esta entrega**. O SQL `supabase/platform-schema-proposal.sql` também é uma proposta não aplicada. Ele acrescenta armazenamento canônico e índices, sem remover a tabela antiga.

Após uma revisão e implantação separadas, a função preparada oferece:

- `/ingest`: resultado individual para eventos legados e conferência de conflitos com conteúdo persistido.
- `/platform-ingest`: telemetria canônica, inclusive sensores rurais.
- `/history`: consultas legadas por horário da medição, filtros e paginação.
- `/platform-history`: histórico canônico autenticado pela identidade da fog.

Enquanto a função antiga estiver hospedada, sensores canônicos novos permanecem na fila local se `/platform-ingest` retornar 404. A API mostra `canonical_cloud_status=PENDING_CLOUD_UPDATE`. Isso não significa que foram sincronizados. Não exclua o banco local. No modo nuvem emulada, os dois fluxos já funcionam.

O catálogo detalhado é validado na fog; a ingestão canônica central preparada verifica esquema e identidade da fog, sem implementar catálogo central multi-inquilino. Login de usuários, papéis, cifragem local, retenção e teste de 72 horas continuam fora desta etapa. Nenhum plano pago ou mudança de região foi contratado.

Referência técnica consultada: https://supabase.com/docs/guides/functions . O índice de changelog em Markdown não pôde ser lido pelo mecanismo de consulta; esta entrega não depende de uma nova API do provedor nem declara homologação remota.

## 10. Exemplos em três linguagens

Com o laboratório local aberto, os exemplos abaixo publicam uma leitura no sensor inicial `sensor-BIN-01`:

```bat
.venv312\Scripts\python examples\platform_publish.py
node examples/platform_publish.mjs
java examples/PlatformPublish.java
```

Foram executados com retorno 202 em Python, Node e Java 17. Node e Java são opcionais: não são necessários para abrir o painel. Os exemplos enviam leituras à integração e não modificam a física da simulação.

## 11. Testes e evidências desta versão

- 60 testes Python aprovados; um aviso de descontinuação da dependência Starlette/AnyIO permanece.
- 28 testes JavaScript aprovados, incluindo o handler HTTP da função com banco simulado, validação e estados do painel.
- Ensaio com broker MQTT real e processos separados: 32 lixeiras, 3 caminhões, 64 eventos legados confirmados na amostra e duas leituras rurais recebidas por HTTP/MQTT.
- ACK de aplicação MQTT verificado; fila canônica zerada após confirmação pela nuvem emulada.
- Clientes Python, JavaScript e Java executados com sucesso no mesmo ensaio.
- Lote de 5.000 mensagens: 4.997 aceitas e três recusadas.
- Reenvio após reinício, colisão de ID, datas impossíveis/extremas, Unicode inválido, limite de bytes, leitura atrasada e migração de SQLite antigo cobertos por testes.
- Arquivos do painel, motor, malha e estratégias de rota comparados por SHA-256 com a base e preservados.

As saídas ficam em `docs/evidence-platform/`. São testes locais; não comprovam 72 horas sem internet, SLA, carga de 1.000 mensagens/s ou cobertura de 70%.

Para repetir os testes:

```bat
.venv312\Scripts\python -m pytest tests -q
node --test supabase/functions/smartwaste-api/core.test.mjs supabase/functions/smartwaste-api/handler.test.mjs tests/distributed/ui-state.test.cjs
.venv312\Scripts\python scripts\verify_platform.py --clients
```

O ensaio integrado precisa das portas 1883, 8000, 8001 e 8002 livres: encerre primeiro o painel que já estiver aberto. A opção `--clients` exige Node e Java; sem ela, apenas os processos Python e o cliente MQTT são necessários.

## 12. Dados antigos, disco e publicação pública

A migração SQLite é aditiva: acrescenta coluna de horário e tabelas de catálogo, telemetria e quarentena. Não apaga o histórico anterior. Novos snapshots e reenvios são convertidos pelo adaptador; eventos antigos já confirmados que não voltarem a passar pela ingestão continuam disponíveis no histórico legado, sem promessa de conversão retroativa integral.

A nova forma canônica ocupa armazenamento adicional. A fila legada continua limitada a 100 mil itens pendentes; a fila canônica depende do disco disponível e não ganhou política automática de retenção. Esta versão não resolve a capacidade de 72 horas identificada na análise. Não se deve aumentar a frequência e assumir armazenamento gratuito ilimitado.

O pacote privado contém o JSON de conexão existente para uso local. Não publique esse ZIP ou JSON no GitHub. O pacote público remove configurações privadas, bancos e ambientes virtuais. Antes de publicar dados novos, revise também os arquivos de evidências que você gerar: eles podem conter informações reais do seu ambiente.

O GitHub recebe o código público, esta documentação e os slides atualizados. A publicação não aplica o SQL remoto nem implanta a função Supabase.
