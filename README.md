# SmartWaste DF

**Engenharia de Software — Anny, Arthur e Eduardo**

Laboratório de coleta inteligente de resíduos no Distrito Federal. O cenário representa **32 lixeiras e três caminhões virtuais**, com sensores, estratégias de atendimento e caminhos calculados por Dijkstra.

![Arquitetura da evolução](docs/assets/arquitetura-evolucao.png)

## Versões e material da atividade

Este repositório público contém o **código da versão base**, com broker em memória, e a **documentação da evolução para edge, fog e nuvem**, atualizada em 19/10/2026. A implementação distribuída testada foi entregue no pacote da atividade. Os resultados dessa implementação não correspondem à execução do código antigo pelo clone público.

| Material | Conteúdo |
|---|---|
| [Relatório da atividade](docs/RELATORIO_ATIVIDADE.md) | Objetivo, metodologia, mudanças, evidências e limitações |
| [Relatório acadêmico em PDF](docs/entrega/SmartWaste_Relatorio_Faculdade.pdf) | Documento para leitura e submissão |
| [Apresentação em PowerPoint](docs/entrega/SmartWaste_Apresentacao_Atualizada.pptx) | Slides editáveis com link para este repositório |
| [Apresentação em PDF](docs/entrega/SmartWaste_Apresentacao_Atualizada.pdf) | Versão para apresentar ou consultar |
| [Guia da evolução distribuída](docs/EVOLUCAO_DISTRIBUIDA.md) | Protocolos, persistência, controle e exportação |
| [Guia completo da versão base](README_VERSAO_BASE.md) | Interface e implementação original |

## O problema estudado

Uma rota fixa pode visitar lixeiras quase vazias enquanto outras se aproximam do transbordo. Telemetria de ocupação ajuda a priorizar os atendimentos. O laboratório permite observar como demanda, localização, capacidade do caminhão, clima e bloqueios influenciam decisões.

A **estratégia escolhe o destino**. O **Dijkstra escolhe o caminho** até ele. As estratégias disponíveis no modelo são rota fixa, mais próxima e Smart VRP. A política Smart é uma heurística do projeto, não um otimizador global que garante a melhor solução.

## Evolução para edge, fog e nuvem

| Camada | Papel implementado no pacote distribuído | Motivo |
|---|---|---|
| Edge | Simula sensores, movimentação e execução de comandos | Mantém medição e atuação próximas aos dispositivos |
| Fog | Recebe MQTT, decide rotas e mantém fila SQLite | Coordena a operação mesmo com o enlace da nuvem interrompido |
| Nuvem | Recebe lotes por HTTPS e persiste em Postgres | Mantém histórico remoto independente do navegador |

A comunicação **edge–fog usa MQTT 3.1.1 real, QoS 1**, com broker local AMQTT e cliente Paho. A comunicação **fog–nuvem usa HTTPS** para uma API no **Supabase Free**, hospedada em **São Paulo (`sa-east-1`)**. O painel consulta a fog localmente. O produto Supabase Edge Functions desempenha o papel de nuvem nesta arquitetura.

Os dispositivos continuam virtuais. MQTT entre processos e a hospedagem da nuvem são reais. A indisponibilidade da internet não equivale à indisponibilidade da fog: encerrar a fog interrompe novas decisões.

### O que mudou e por quê

- **Broker em memória para MQTT por TCP:** torna observável a comunicação entre processos separados.
- **Decisão separada da execução:** a fog usa a visão da frota e envia comandos à edge.
- **Fila SQLite:** guarda eventos antes da confirmação e permite reenvio após falhas de conexão.
- **IDs de evento e execução:** evitam duplicar histórico e distinguem reinícios.
- **Envio em lotes:** reduz a quantidade de chamadas em relação a enviar cada leitura individualmente.
- **Confirmação visível:** o painel acompanha o ACK pelo `command_id`, apresenta rejeição e explica atrasos.
- **Exportação em PDF:** mostra comunicação, fila e valores antes/depois de cada ação.

## Evidências da evolução

**47 testes automatizados aprovados no pacote distribuído:** 30 Python, 11 da apresentação de estados em JavaScript e seis do contrato da função de nuvem. Uma integração adicional com MQTT real e emulador local verificou desconexão/reconexão, canário saudável, reversão da versão com falha, ACK de velocidade e geração do PDF.

Uma integração remota anterior, de 42,14 segundos, também passou com MQTT local e Supabase por HTTPS. No ponto de recuperação, havia **160 eventos recebidos, 128 confirmados e 32 pendentes**. O total confirmado passou de 32 para 128 enquanto novas leituras chegavam. Isso não significa que a fila terminou vazia.

![Contadores no ponto de recuperação remota](docs/assets/recuperacao-supabase.png)

O teste da API retornou HTTP 401 sem credencial, manteve uma linha após dois envios do mesmo evento e rejeitou uma data impossível com HTTP 400. Esses resultados estão resumidos no [relatório](docs/RELATORIO_ATIVIDADE.md) e no [registro público de evidências](docs/evidencias/testes-resumo.json).

## Exportação e interpretação dos dados

O PDF da evolução inclui métricas MQTT, bytes de payload, lotes de nuvem, status HTTP, duração dos envios e gráfico da fila. Cada ação registra:

1. O estado conhecido antes do envio.
2. A confirmação ou rejeição da edge.
3. A primeira amostra compatível com a alteração.
4. Outra amostra após pelo menos dez segundos reais.

Se várias ações ocorrem na mesma janela, o documento sinaliza sobreposição. As diferenças também incluem a evolução normal do modelo. O histórico de alterações começa na atualização e não reconstrói ações antigas.

## Execução do código atualmente publicado

Para executar a **versão base presente neste repositório**:

```bash
python -m pip install fastapi uvicorn pydantic pytest
python run_lab.py
```

No Windows, também existe `run_lab.bat`. A aplicação usa `http://localhost:8000`. Os testes da base são executados com:

```bash
python -m pytest tests -v --tb=short
```

O iniciador `run_distributed.py` e as dependências distribuídas pertencem ao pacote da evolução. No pacote privado, `INICIAR_SMARTWASTE.bat` utiliza Python 3.12 e a configuração local já fornecida. A documentação técnica identifica os caminhos desse pacote sem afirmar que eles já fazem parte do código público.

## Publicação e privacidade

A documentação pública não contém o JSON privado de conexão, tokens, chaves administrativas, bancos SQLite locais ou o ZIP privado. Cada grupo que reproduzir a hospedagem deve usar seu próprio projeto e suas credenciais. O painel não recebe a chave administrativa do Supabase.

## Limites

Os dados são sintéticos. Custos, diesel, CO₂ e ganhos operacionais do modelo não representam medições de campo. Não há comprovação de economia real nem de ganho de latência contra a arquitetura anterior. A interface de demonstração anterior permanece independente do painel distribuído.

O Supabase Free possui cotas. Em 19/10/2026, a [página oficial](https://supabase.com/pricing) informava US$ 0/mês, 500 MB de banco e 5 GB de saída, com pausa após uma semana de inatividade. A região São Paulo é configuração de hospedagem, não garantia de desempenho. O experimento precisa controlar retenção e volume.

## Referências

- [MQTT 3.1.1 — OASIS](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html)
- [Supabase — preços e limites](https://supabase.com/pricing)
- [Supabase — Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Cliente Paho MQTT para Python](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html)
