# ADR 0001: Adoção de Monólito Modular para o SmartWaste DF

## Status
Aceito.

## Contexto
O SmartWaste DF necessita simular um ciclo completo de IoT urbana (sensores, gateways, broker MQTT, motor de decisão, despacho de caminhões e streaming de telemetria). A arquitetura deve permitir execução 100% local, em hardware padrão de desenvolvimento, sem requerer múltiplos microsserviços pesados nem nuvem externa, mas mantendo separação estrita de domínios para possibilitar evolução futura.

## Decisão
Implementar o backend como um **Monólito Modular** em Python 3 com FastAPI e Pydantic, isolando os módulos de domínio:
* `simulation`: controle temporal, relógio, agendador e determinismo via seed.
* `iot`: contratos de telemetria, gateway, broker e emissores virtuais.
* `fleet`: estados dos caminhões, capacidade, consumo e atuadores.
* `routing`: solucionador de rotas, Dijkstra, baseline e VRP Smart.
* `waste`: lixeiras, taxas horárias e limites sanitários.
* `geo`: malha viária e nós geográficos do Distrito Federal.
* `analytics`: cálculo de custos operacionais, emissões de CO₂ e transbordos.
* `decisions`: registro de justificativas de despacho e explicabilidade.

## Consequências
* Inicialização simplificada com um único comando local.
* Zero dependência de SaaS ou nuvem gerenciada.
* Facilidade para rodar testes unitários e de integração de ponta a ponta sem orquestração complexa de rede.
* Interfaces internas desacopladas para eventual extração de serviços isolados.
