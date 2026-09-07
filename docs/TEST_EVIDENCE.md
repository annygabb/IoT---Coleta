# SmartWaste DF — Evidências de Testes

Este documento reúne as evidências automatizadas usadas para validar o comportamento principal do laboratório.

> Execução realizada em 07/09/2026 com `python -m pytest tests -v --tb=short` sobre o código atualizado das estratégias de rota.

## Resultado geral

![Pytest — 12 testes aprovados](assets/pytest-12-passed.svg)

```text
12 passed
```

## Evidência específica das estratégias

![Testes das estratégias](assets/pytest-routing-strategies.svg)

### Rota Fixa

- percorre a ordem BIN de forma cíclica;
- não usa ocupação como limiar de prioridade;
- pula alvo já reservado por outro caminhão.

### Mais Próximo

- ignora pontos abaixo de 20%;
- considera candidatos a partir de 20%;
- seleciona pela menor distância viária entre os candidatos válidos.

### VRP Smart

- ignora pontos abaixo de 25%;
- considera candidatos a partir de 25%;
- gera justificativa contendo o score usado na decisão.

## Matriz de testes

| Arquivo | Teste | Evidência |
|---|---|---|
| `tests/integration/test_iot_flow.py` | `test_complete_vertical_slice_m1` | Lixeira crítica gera decisão, caminhão coleta e, quando cheio, segue ao aterro. |
| `tests/unit/test_contracts.py` | `test_valid_sensor_telemetry_payload` | Payload IoT válido é aceito. |
| `tests/unit/test_contracts.py` | `test_invalid_negative_fill_pct_rejected` | Ocupação negativa é rejeitada pelo schema. |
| `tests/unit/test_contracts.py` | `test_truck_command_idempotency_structure` | Comando de caminhão tem `command_id` e ação. |
| `tests/unit/test_routing_strategies.py` | `test_fixed_route_is_cyclic_and_does_not_use_fill_threshold` | Rota Fixa é cíclica e não prioriza ocupação. |
| `tests/unit/test_routing_strategies.py` | `test_fixed_route_skips_bin_targeted_by_another_truck` | Evita conflito de alvo. |
| `tests/unit/test_routing_strategies.py` | `test_nearest_requires_minimum_twenty_percent_fill` | `NEAREST` respeita 20%. |
| `tests/unit/test_routing_strategies.py` | `test_smart_vrp_requires_twenty_five_percent_and_reports_score` | `VRP_SMART` respeita 25% e reporta score. |
| `tests/unit/test_simulation_engine.py` | `test_deterministic_prng_reproducibility` | A mesma seed gera a mesma sequência. |
| `tests/unit/test_simulation_engine.py` | `test_simulation_clock_speed` | Aceleração de tempo funciona. |
| `tests/unit/test_simulation_engine.py` | `test_smart_bin_state_transitions` | Estados das lixeiras seguem as faixas definidas. |
| `tests/unit/test_simulation_engine.py` | `test_dijkstra_reroutes_when_eptg_is_blocked` | Bloqueio da EPTG altera a rota calculada. |

## Como reproduzir

```bash
python -m pytest tests -v --tb=short
```

## O que esses testes não provam

A suíte atual não prova, sozinha:

- precisão de custos reais do SLU;
- economia real de combustível;
- fidelidade da malha de Brasília;
- compatibilidade de PDF em todos os navegadores;
- experiência visual pixel-perfect;
- comportamento sob milhares de sensores;
- tolerância a falhas de uma rede MQTT física;
- persistência após reinício, pois o SQLite ainda não está conectado ao fluxo principal.

Esses itens exigem testes E2E, carga, integração externa e calibração com dados reais.
