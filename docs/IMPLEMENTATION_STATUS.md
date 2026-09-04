# SmartWaste DF — Status de Implementação e Rastreabilidade

Este documento rastreia o cumprimento dos requisitos funcionais, não funcionais, regras de negócio e critérios do DoD (Definition of Done) descritos no documento oficial do projeto.

Última atualização: 2026-09-03T23:40:00-03:00

---

## 1. Marcos e Entregas (MoSCoW)

| Marco | Descrição | Status | Evidência / Teste | Limitação Atual | Próxima Ação |
|---|---|---|---|---|---|
| **M0 — Fundação** | Repositório, monólito modular, contratos Pydantic, schemas de banco, health checks | **Implementado** | `apps/api/main.py`, `tests/unit/test_contracts.py` | Execução em host local com suporte a container | Integrar migrações |
| **M1 — Ciclo IoT Mínimo** | Sensor → Gateway → Broker MQTT/EventBus → Backend → Decisão → Atuador → Caminhão → Coleta → WebSocket | **Implementado** | `tests/integration/test_iot_flow.py`, `apps/api/app/domain/` | 32 lixeiras e 3 caminhões no cenário padrão | Refinar matriz OSRM |
| **M2 — Mapa DF** | RAs de Brasília, malha viária, lixeiras georreferenciadas e pontos de descarte | **Implementado** | `apps/api/app/domain/geo/brasilia_network.py` | Geometria simplificada para performance web | Importar shapefiles oficiais IPEDF 2026 |
| **M3 — Jogo 2D / Simulação Visual** | Canvas 2D, estados visuais semânticos, relógio simulado, timeline e inspetor | **Implementado** | `index.html` (Canvas engine 60fps) | Modo híbrido Demo PWA / Laboratório WebSocket | Adicionar texturas adicionais |
| **M4 — Logística** | Capacidade dos caminhões (5.000 kg), consumo de diesel, retorno obrigatório ao Aterro Sanitário Samambaia | **Implementado** | `apps/api/app/domain/fleet/truck.py` | Modelo de consumo estimado por L/km | Calibração com dados históricos SLU |
| **M5 — Otimização** | Comparação VRP Smart vs Baseline Rota Fixa vs Nearest | **Implementado** | `apps/api/app/domain/routing/strategies.py` | Solver heurístico determinístico com penalty matrix | Integrar binding OR-Tools C++ opcional |
| **M6 — Ambiente** | Impacto de chuva, tempestade, tráfego por horário e bloqueio da EPTG | **Implementado** | `apps/api/app/domain/simulation/engine.py` | Fatores climáticos sintéticos | Importador de CSV INMET histórico |
| **M7 — Analytics** | KPIs de custo (R$), CO₂ evitado, diesel poupado, transbordos evitados, exportação JSON | **Implementado** | `apps/api/app/domain/analytics/` | Fatores parametrizados | Dashboards Grafana opcionais |

---

## 2. Rastreabilidade dos Requisitos Funcionais (RF)

| ID | Requisito Funcional | Status | Arquivo / Módulo |
|---|---|---|---|
| RF-001 | Criar e alternar cenários de simulação | Implementado | `apps/api/app/domain/simulation/engine.py` |
| RF-002 | Definir seed determinística para reprodução | Implementado | `apps/api/app/domain/simulation/prng.py` |
| RF-003 | RAs de Brasília e conexões | Implementado | `apps/api/app/domain/geo/brasilia_network.py` |
| RF-004 | Lixeiras com capacidade e perfil de geração | Implementado | `apps/api/app/domain/waste/bin.py` |
| RF-005 | Vincular sensor virtual a cada lixeira | Implementado | `apps/api/app/domain/iot/sensor.py` |
| RF-006 | Leituras de nível, temperatura, bateria e status | Implementado | `apps/api/app/domain/iot/contracts.py` |
| RF-007 | Encaminhar leituras via gateway virtual | Implementado | `apps/api/app/domain/iot/gateway.py` |
| RF-008 | Publicar e consumir telemetria MQTT | Implementado | `apps/api/app/domain/iot/broker.py` |
| RF-009 | Persistir telemetria e eventos com timestamp | Implementado | `apps/api/app/infrastructure/db/repository.py` |
| RF-010 | Exibir lixeiras por faixas de ocupação (<50%, 50-69%, 70-84%, 85-99%, ≥100%) | Implementado | `index.html` (Canvas Renderer) |
| RF-011 | Detectar níveis de atenção, alto, crítico e transbordo | Implementado | `apps/api/app/domain/waste/bin.py` |
| RF-012 | Gerar alertas operacionais | Implementado | `apps/api/app/domain/iot/broker.py` |
| RF-013 | Caminhões com capacidade, carga, estado e consumo | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-014 | Movimentação em rede viária sem teletransporte | Implementado | `apps/api/app/domain/routing/dijkstra.py` |
| RF-015 | Simular tempo de atendimento/coleta | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-016 | Atualizar nível da lixeira após coleta | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-017 | Atualizar carga do caminhão após coleta | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-018 | Enviar caminhão ao Aterro Sanitário Samambaia quando lotado | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-019 | Descarregar veículo e registrar evento | Implementado | `apps/api/app/domain/fleet/truck.py` |
| RF-020 | Rota fixa sequencial para baseline | Implementado | `apps/api/app/domain/routing/strategies.py` |
| RF-021 | Rota heurística por proximidade | Implementado | `apps/api/app/domain/routing/strategies.py` |
| RF-022 | Rota otimizada VRP Smart com restrição de capacidade | Implementado | `apps/api/app/domain/routing/strategies.py` |
| RF-023 | Recalcular rota após bloqueios ou eventos críticos | Implementado | `apps/api/app/domain/simulation/engine.py` |
| RF-024 | Simulação de trânsito por horário de pico | Implementado | `apps/api/app/domain/simulation/engine.py` |
| RF-025 | Simular bloqueios de via (ex: EPTG) | Implementado | `apps/api/app/domain/geo/brasilia_network.py` |
| RF-026 | Simular clima (Seco, Chuva Leve, Chuva Forte, Tempestade) | Implementado | `apps/api/app/domain/simulation/engine.py` |
| RF-029 | Controle do relógio: pausar, retomar, acelerar (1x a 1440x) | Implementado | `apps/api/app/domain/simulation/clock.py` |
| RF-036 | Cálculo de KPIs em tempo real (Custo, CO₂, Transbordos) | Implementado | `apps/api/app/domain/analytics/metrics.py` |
| RF-039 | Exportação de resultados em JSON | Implementado | `apps/api/app/api/v1/endpoints.py` & UI |
| RF-045 | Exibir explicação para decisões de despacho | Implementado | `apps/api/app/domain/decisions/explainer.py` |

---

## 3. Definition of Done (DoD) Checklist

- [x] **DoD-01**: Laboratório executável com comando simples e claro (`run_lab.bat` / `python run_server.py`).
- [x] **DoD-02**: R$ 0 em custos de licença, APIs de mapas pagas ou contas de nuvem.
- [x] **DoD-03**: Interface acessível em desktop e celular sem quebra visual.
- [x] **DoD-04**: Malha do Distrito Federal carregada com nós geográficos reais (Plano Piloto, Taguatinga, Ceilândia, Samambaia, Águas Claras, Guará, Lago Sul/Norte).
- [x] **DoD-05**: Pelo menos 20 lixeiras (32 implementadas) e 2 caminhões (3 implementados).
- [x] **DoD-06**: Telemetria estruturada percorre Sensor → Gateway → Broker → Backend → Banco/Memória.
- [x] **DoD-07**: Lixeira crítica (>85%) dispara decisão e comando idempotente de despacho.
- [x] **DoD-08**: Caminhão se desloca, coleta resíduo, enche até o limite e descarrega no Aterro Sanitário Samambaia.
- [x] **DoD-09**: Bloqueio de via (ex: EPTG) provoca recálculo dinâmico imediato.
- [x] **DoD-10**: Chuva e tempestade reduzem velocidade e alteram tempo de percurso.
- [x] **DoD-11**: Comparação entre Baseline e VRP Smart na mesma seed.
- [x] **DoD-12**: KPIs de distância, tempo, transbordos, emissões de CO₂ e custo monetário calculados.
- [x] **DoD-13**: Exportação estruturada dos dados da simulação.
- [x] **DoD-14**: Testes unitários e de integração implementados e validados com pytest.
- [x] **DoD-17**: Nenhuma decisão relevante existe apenas na animação — há registro e telemetria rastreável.
- [x] **DoD-18**: Sistema exibe justificativa textual para cada decisão de despacho.
