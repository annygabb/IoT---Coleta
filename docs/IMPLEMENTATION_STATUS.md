# SmartWaste DF — Status de Implementação e Rastreabilidade

Última revisão documental: **07/09/2026**.

Este documento diferencia o que está **ativo no fluxo principal**, o que existe como **camada disponível** e o que é **evolução planejada**.

## 1. Status executivo

| Área | Status | Evidência | Observação |
|---|---|---|---|
| Backend FastAPI | Implementado | `apps/api/main.py` | Porta 8000, REST e WebSocket. |
| Simulação determinística | Implementado | `simulation/clock.py`, `simulation/prng.py` | Seed reproduzível. |
| 32 lixeiras | Implementado | `simulation/engine.py` | Cenário padrão. |
| 3 caminhões backend | Implementado | `simulation/engine.py` | Frota padrão Python. |
| Frota 1–10 na UI | Implementado no frontend | `index.html` | Ainda não parametriza backend. |
| Rota Fixa | Implementado | `routing/strategies.py` | Cíclica por caminhão. |
| Mais Próximo | Implementado | `routing/strategies.py` | Limiar de 20%. |
| VRP Smart | Implementado | `routing/strategies.py` | Heurística, não solver exato. |
| Dijkstra | Implementado | `routing/dijkstra.py` | Bloqueios e penalidade de pico. |
| Clima | Implementado | `simulation/engine.py` + UI | Fatores sintéticos. |
| Interdição | Implementado | `dijkstra.py`, `engine.py`, UI | Recalcula caminho. |
| MQTT | Implementado como broker virtual | `iot/broker.py` | Em memória; não é Mosquitto real. |
| WebSocket | Implementado | `api/v1/ws.py` | Snapshot + atualizações periódicas. |
| Decision Explainer | Implementado | `decisions/explainer.py` | Justificativa textual. |
| KPIs | Implementado | `analytics/metrics.py` | Parâmetros didáticos. |
| PDF | Implementado na UI | `index.html`, `apps/web/routing-docs-enhancements.js` | jsPDF/AutoTable. |
| SQLite | Camada disponível | `infrastructure/db/repository.py` | Não conectado ao fluxo principal. |
| PostGIS | Planejado/compatível | — | Não ativo. |
| MQTT físico | Planejado | — | Não ativo. |
| Testes | Implementado | `tests/` | 12 testes aprovados na revisão. |

## 2. Requisitos funcionais principais

| ID | Requisito | Status | Evidência |
|---|---|---|---|
| RF-001 | Simular cenário | Implementado | `SimulationEngine` |
| RF-002 | Seed determinística | Implementado | `DeterministicPRNG` |
| RF-003 | Malha DF simplificada | Implementado | `brasilia_network.py` |
| RF-004 | Lixeiras com capacidade e geração | Implementado | `SmartBin` + `engine.py` |
| RF-006 | Telemetria de nível/temperatura/bateria | Implementado | `engine.py` + contratos |
| RF-008 | Publish/subscribe estilo MQTT | Implementado em memória | `VirtualMQTTBroker` |
| RF-009 | Persistência automática da telemetria | **Parcial** | Camada SQLite existe; não está ligada ao motor |
| RF-010 | Estados visuais por ocupação | Implementado | UI + `SmartBin` |
| RF-013 | Caminhões com capacidade/carga/estado | Implementado | `CollectionTruck` |
| RF-014 | Movimento via rede | Implementado | `DijkstraRouter` |
| RF-018 | Envio ao aterro quando cheio | Implementado | `SimulationEngine` |
| RF-020 | Rota Fixa | Implementado | `FixedBaselineStrategy` |
| RF-021 | Mais Próximo | Implementado | `NearestPriorityStrategy` |
| RF-022 | VRP Smart | Implementado como heurística | `SmartVRPStrategy` |
| RF-023 | Recalcular rota em bloqueio | Implementado | `set_eptg_blocked` + Dijkstra |
| RF-024 | Penalidade de horário de pico | Implementado | Dijkstra `1.8x` em EPTG |
| RF-026 | Clima | Implementado | `set_weather` |
| RF-029 | Relógio e velocidade | Implementado | `SimulationClock` |
| RF-036 | KPIs | Implementado | `EconomicEnvironmentalMetrics` |
| RF-039 | Exportação JSON/PDF | Implementado | endpoint + UI |
| RF-045 | Explicação de despacho | Implementado | `DecisionExplainer` |

## 3. Definition of Done — estado atual

- [x] Execução simples via `.\run_lab.bat` ou `python run_lab.py`.
- [x] Laboratório sem API paga obrigatória.
- [x] Malha simplificada do DF.
- [x] 32 lixeiras.
- [x] 3 caminhões no backend.
- [x] Telemetria e broker virtual.
- [x] Lixeira crítica força reavaliação.
- [x] Caminhão coleta e descarrega no aterro.
- [x] Bloqueio altera caminho.
- [x] Clima altera velocidade.
- [x] Três políticas de roteamento disponíveis.
- [x] KPIs calculados.
- [x] Exportação JSON e PDF.
- [x] Justificativa textual de despacho.
- [x] 12 testes automatizados aprovados.
- [ ] Persistência integral do motor no SQLite.
- [ ] Broker MQTT real.
- [ ] Benchmark científico das três estratégias em múltiplas seeds.
- [ ] E2E automatizado da interface e do download do PDF.

## 4. Evidências

Veja [`TEST_EVIDENCE.md`](TEST_EVIDENCE.md).
