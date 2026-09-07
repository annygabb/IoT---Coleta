# SmartWaste DF — Digital Twin & Simulação IoT para Coleta Inteligente de Resíduos

> Laboratório open source e de custo zero para simular coleta inteligente de resíduos no Distrito Federal. O projeto reúne sensores virtuais, telemetria IoT, broker MQTT em memória, backend FastAPI, malha viária simplificada de Brasília, frota de caminhões, três estratégias de roteamento comparáveis, eventos operacionais e relatório PDF.

> **Importante:** o SmartWaste DF é uma simulação educacional/experimental. Custos, geração de resíduos, consumo, emissões, baseline e ganhos apresentados pelo sistema não são medições oficiais do SLU/GDF.

---

## 1. Como o sistema funciona

O fluxo completo do laboratório é:

1. **Lixeiras inteligentes virtuais** geram ocupação, temperatura, bateria e demais dados de sensor.
2. **Broker MQTT virtual** representa o transporte das mensagens IoT.
3. **Backend FastAPI** mantém o motor de simulação e expõe REST/WebSocket.
4. **Motor de decisão** filtra os pontos que podem ser atendidos e escolhe um alvo conforme a estratégia ativa.
5. **Dijkstra** calcula o caminho pela malha viária até o alvo escolhido, respeitando bloqueios e custo de trânsito.
6. **Caminhões virtuais** percorrem a rota, coletam o resíduo e, quando necessário, seguem para o Aterro Sanitário de Samambaia.
7. **Painel operacional** mostra mapa, frota, bins, rotas, alertas, KPIs e timeline.
8. **Exportar PDF** registra o cenário e explica também como as três estratégias de rota funcionam.

---

## 2. Como executar

### Windows — PowerShell

Na pasta do projeto:

```powershell
.\run_lab.bat
```

ou:

```powershell
python run_lab.py
```

> No PowerShell, use `./` ou `.\` antes de um `.bat` localizado na pasta atual. Digitar apenas `run_lab.bat` pode não funcionar dependendo do contexto do terminal.

### Windows — CMD

```cmd
run_lab.bat
```

### macOS / Linux

```bash
python run_lab.py
```

### Endereços

- Aplicação integrada: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws/scenarios/default`

### Dependências principais

```bash
pip install fastapi uvicorn pydantic pytest
```

### Testes

```bash
python -m pytest tests
```

A execução recomendada é pela porta **8000**, porque o FastAPI injeta automaticamente o módulo `apps/web/routing-docs-enhancements.js`, responsável por manter as regras do seletor de rotas da interface alinhadas ao backend e por usar a versão atualizada do relatório PDF.

---

## 3. O que cada parte da tela faz

### Barra superior

| Controle | Função |
|---|---|
| **Simulador / status** | Mostra se a interface está no simulador local ou conectada ao laboratório FastAPI/WebSocket. |
| **Relógio** | Horário e dia simulados. O reset volta para `00:00:00`. |
| **Play/Pause** | Pausa ou retoma o avanço automático da simulação. |
| **Avanço manual** | Executa um pequeno avanço do relógio sem alterar permanentemente a velocidade. |
| **1x, 5x, 15x, 30x, 60x, 360x** | Acelera o tempo simulado. |
| **Frota 1–10** | Altera a quantidade de caminhões visíveis/operacionais no simulador da interface. |
| **Seletor de rota** | Alterna entre `VRP_SMART`, `FIXED` e `NEAREST`. |
| **Clima** | Aplica fator de velocidade para seco, chuva leve, chuva forte ou tempestade. |
| **Interdição** | Bloqueia/libera uma via e força o recálculo dos caminhos. |
| **Áudio** | Ativa/desativa efeitos sonoros. |
| **Ajuda** | Exibe o guia rápido e atalhos. |
| **Reset** | Reinicia relógio, KPIs, eventos, bins e caminhões. |
| **Exportar PDF** | Gera o relatório operacional com metodologia de roteamento, KPIs, frota e telemetria. |

### Painel esquerdo — Camadas e regiões

- **Lixeiras inteligentes:** mostra os 32 pontos IoT.
- **Frota SLU:** mostra os caminhões.
- **Vetores de rota:** mostra os deslocamentos planejados.
- **Heatmap de resíduos:** destaca áreas com maior ocupação.
- **Regiões do DF:** organiza/foca Plano Piloto, Taguatinga, Ceilândia, Águas Claras, Samambaia, Guará, Lago Sul e demais áreas modeladas.
- **+ Lixeira Crítica:** injeta um evento de estresse para observar a reação do despacho.
- **Interditar Via Aleatória:** cria uma interrupção na malha para testar replanejamento.

### Mapa central

O mapa é um **grafo viário simplificado** de Brasília/DF. O algoritmo de estratégia escolhe o **alvo** e o Dijkstra escolhe o **caminho** até esse alvo.

- Uma via bloqueada deixa de participar do caminho.
- Em horário de pico, trechos modelados da EPTG recebem penalidade de custo `1,8x`.
- Clique em caminhões e lixeiras para inspecionar os dados.
- Zoom e pan permitem acompanhar regiões e rotas.

### Painel direito

- **Operação:** detalhe do item selecionado e do estado operacional.
- **VRP vs Baseline:** comparação dos indicadores simulados.
- **Frota & Bins:** carga/estado dos caminhões e situação das lixeiras.
- **Última Decisão de Despacho:** explica o motivo do último alvo escolhido.

### Timeline de Operações & MQTT

Registra telemetria, alertas, despachos, coleta, descarregamento, mudança de estratégia, clima, bloqueios, exportações e demais eventos do laboratório.

---

## 4. Regras que valem para todas as estratégias

### Estado das lixeiras

| Ocupação | Estado |
|---:|---|
| `< 50%` | Normal |
| `50–69%` | Atenção |
| `70–84%` | Alta |
| `85–99%` | Crítica |
| `>= 100%` | Transbordo |

A massa estimada usa densidade de laboratório de **0,40 kg/L**:

```text
massa_kg = (ocupacao_pct / 100) × capacidade_litros × 0,40
```

### Caminhões e aterro

- Capacidade padrão do backend: **5.000 kg**.
- A interface possui templates adicionais para experimentar diferentes frotas.
- Ao atingir **90% da capacidade**, a prioridade passa a ser o **Aterro Sanitário de Samambaia**, independentemente da estratégia selecionada.
- Depois do descarregamento, o caminhão volta a receber coletas.

### Evitar dois caminhões no mesmo ponto

Se uma lixeira já está atribuída a outro caminhão, ela é removida dos candidatos do novo despacho.

### Dijkstra

As estratégias abaixo não desenham a rua diretamente. Elas escolhem **qual lixeira atender**. Em seguida, o `DijkstraRouter` calcula o menor caminho disponível na malha.

Se não existir caminho por causa de interdições, a distância é tratada como infinita e o ponto não pode vencer a decisão naquele momento.

---

## 5. Seletor de rotas: diferença entre Rota Fixa, Mais Próximo e VRP Smart

O seletor permite executar o mesmo cenário com três filosofias diferentes de decisão.

### 5.1 Rota Fixa — `FIXED`

**Objetivo:** representar um baseline previsível, semelhante a um itinerário definido previamente e sem usar a lotação como prioridade.

**Como foi definida:**

```text
BIN-01 -> BIN-02 -> ... -> BIN-32 -> BIN-01 -> ...
```

Cada caminhão mantém seu próprio cursor na sequência. Quando recebe um novo despacho:

1. procura o próximo BIN da ordem numérica;
2. não usa `fill_pct` para alterar a prioridade;
3. pula um BIN temporariamente se outro caminhão já estiver indo para ele;
4. pula um BIN sem caminho viável;
5. segue para o próximo item alcançável;
6. depois de `BIN-32`, reinicia em `BIN-01`.

**Vantagens**

- simples e previsível;
- fácil de auditar e reproduzir;
- baixa complexidade de decisão;
- excelente baseline para medir o que a telemetria acrescenta.

**Desvantagens**

- pode coletar uma lixeira quase vazia;
- pode deixar uma lixeira crítica esperando porque ela está mais adiante no itinerário;
- não reage à demanda em tempo real;
- pode gerar quilômetros desnecessários.

**Use quando:** quiser comparar uma operação rígida/pré-definida contra políticas adaptativas.

---

### 5.2 Mais Próximo — `NEAREST`

**Objetivo:** reduzir o deslocamento da **próxima decisão**.

**Como foi definida:**

1. considera somente lixeiras com `fill_pct >= 20%`;
2. remove pontos já atribuídos a outro caminhão;
3. calcula a menor distância viária com Dijkstra para cada candidato;
4. escolhe o candidato de menor distância.

```text
alvo = candidato com menor distancia_viaria
```

**Vantagens**

- rápido e simples;
- normalmente reduz o deslocamento imediato;
- usa a posição atual do caminhão;
- reage melhor que a rota fixa quando a demanda está espalhada.

**Desvantagens**

- é uma heurística gulosa/local;
- o melhor próximo passo não garante a melhor rota total;
- uma lixeira crítica mais distante pode perder para uma lixeira apenas moderada que esteja perto;
- não usa capacidade restante como critério de prioridade.

**Use quando:** quiser medir o benefício da proximidade sem adicionar pesos de criticidade/capacidade.

---

### 5.3 VRP Smart — `VRP_SMART`

**Objetivo:** equilibrar **urgência + distância + capacidade restante**.

> O VRP Smart atual é uma **heurística adaptativa inspirada em VRP**. Ele não é um solver matemático exato de Vehicle Routing Problem e não garante o ótimo global da frota.

Primeiro, apenas lixeiras com `fill_pct >= 25%` entram como candidatas.

#### Peso de urgência

```text
urgencia = fill_pct

se fill_pct >= 100%: urgencia = fill_pct × 4,0
se fill_pct >= 85% : urgencia = fill_pct × 2,8
se fill_pct >= 70% : urgencia = fill_pct × 1,6
```

Assim, uma lixeira crítica/transbordando ganha peso muito maior que uma lixeira apenas moderada.

#### Penalidade de capacidade

Se a massa estimada do ponto for maior que a capacidade restante do caminhão:

```text
capacity_penalty = 0,70
```

Caso contrário:

```text
capacity_penalty = 1,00
```

#### Score final

```text
score = (urgencia^1,8 × capacity_penalty) / (distancia_km + 2,0)
```

O candidato com **maior score** vence.

O `+ 2,0` reduz instabilidade quando dois pontos estão muito próximos do caminhão e impede uma divisão problemática por distância próxima de zero.

**Vantagens**

- prioriza risco de transbordo;
- continua penalizando longas distâncias;
- considera se o conteúdo estimado cabe na capacidade restante;
- reage à telemetria, à posição e à malha viária;
- gera justificativa de despacho auditável.

**Desvantagens**

- depende da calibração dos pesos/limiares;
- não garante ótimo global;
- leituras de sensor ruins influenciam a decisão;
- em operação real, os parâmetros precisariam ser calibrados com dados históricos e restrições adicionais.

**Use quando:** quiser testar uma política adaptativa baseada em risco e telemetria.

---

## 6. Comparação direta

| Critério | Rota Fixa | Mais Próximo | VRP Smart |
|---|---|---|---|
| Código | `FIXED` | `NEAREST` | `VRP_SMART` |
| Limiar de ocupação | Não define prioridade | `>=20%` | `>=25%` |
| Lotação altera prioridade? | Não | Só pelo limiar | Sim |
| Criticidade 70/85/100% | Não | Não | Sim |
| Distância | Usada para chegar ao item da sequência | Critério principal | Parte do score |
| Capacidade restante | Só regra geral do aterro | Só regra geral do aterro | Penalidade no score + regra do aterro |
| Reage a interdição | Caminho é recalculado | Sim | Sim |
| Ótimo global garantido | Não | Não | Não |
| Melhor característica | Previsibilidade | Menor deslocamento imediato | Equilíbrio entre urgência, distância e capacidade |
| Principal risco | Coleta desnecessária | Miopia gulosa | Dependência de calibração |

### Exemplo

Considere:

- BIN-A: 35%, 1 km;
- BIN-B: 92%, 5 km;
- BIN-C: 60%, 2 km.

Tendência:

- **Rota Fixa:** escolhe o próximo item da sequência, independentemente de A/B/C estarem mais cheios ou próximos.
- **Mais Próximo:** tende a escolher A, porque passou de 20% e está a 1 km.
- **VRP Smart:** tende a favorecer B porque 92% recebe multiplicador crítico, desde que distância e capacidade não derrubem seu score.

---

## 7. Clima, trânsito e interdições

| Clima | Fator de velocidade |
|---|---:|
| Seco | `1,00x` |
| Chuva leve | `0,95x` |
| Chuva forte | `0,70x` |
| Tempestade | `0,50x` |

Nos horários de pico modelados, trechos da EPTG recebem peso `1,8x` no Dijkstra. Uma via interditada é removida do grafo enquanto o bloqueio estiver ativo.

---

## 8. Métricas do laboratório

Parâmetros atuais do modelo analítico:

| Parâmetro | Valor |
|---|---:|
| Custo por km | R$ 3,50/km |
| Custo de equipe/operação | R$ 45,00/h |
| Diesel de referência | R$ 6,20/L |
| Viagem/descarga no aterro | R$ 85,00 |
| Penalidade simulada de transbordo | R$ 25,00/ocorrência |
| Consumo base | 0,35 L/km |
| Fator de CO2 | 2,68 kg CO2/L |

O baseline de custo/distância é **estimado pelo modelo de simulação** para comparação interna. Não é dado oficial.

---

## 9. O que mudou no PDF

O botão **Exportar PDF** agora registra explicitamente a metodologia das rotas. O relatório inclui:

1. parâmetros do cenário: relógio, dia, frota, clima, via e estratégia ativa;
2. tabela **Rota Fixa x Mais Próximo x VRP Smart**;
3. como cada estratégia decide;
4. vantagens de cada estratégia;
5. desvantagens/limitações de cada estratégia;
6. fórmula e limiares do VRP Smart;
7. KPIs operacionais e ambientais;
8. desempenho da frota;
9. auditoria das lixeiras IoT;
10. nota metodológica informando que custos/baseline são simulados e que o VRP Smart é heurístico;
11. rodapé com estratégia ativa e paginação.

O PDF continua sendo gerado no navegador com **jsPDF + AutoTable**.

---

## 10. Arquitetura relevante

```text
IoT---Coleta/
├─ index.html
├─ run_lab.py
├─ run_lab.bat
├─ apps/
│  ├─ api/
│  │  ├─ main.py                       # FastAPI + injeção do módulo integrado
│  │  └─ app/
│  │     ├─ api/v1/                    # REST + WebSocket
│  │     └─ domain/
│  │        ├─ analytics/              # custos, diesel, CO2 e comparativos
│  │        ├─ fleet/                  # caminhões
│  │        ├─ geo/                    # grafo de Brasília
│  │        ├─ iot/                    # contratos/broker virtual
│  │        ├─ routing/                # Dijkstra + estratégias
│  │        ├─ simulation/             # motor/relógio/seed
│  │        └─ waste/                  # lixeiras e telemetria
│  └─ web/
│     └─ routing-docs-enhancements.js  # alinhamento da UI + PDF metodológico
├─ docs/
└─ tests/
```

O módulo `routing-docs-enhancements.js` é carregado automaticamente quando a aplicação é aberta por `http://localhost:8000`. Ele:

- alinha o solver local do navegador aos limiares e à fórmula do backend;
- torna a Rota Fixa realmente cíclica;
- usa distância viária no Mais Próximo;
- aplica urgência/capacidade no VRP Smart;
- envia a troca de estratégia para `/api/v1/scenarios/default/strategy`;
- substitui o exportador PDF pela versão documentada.

---

## 11. Endpoints úteis

| Método | Endpoint | Finalidade |
|---|---|---|
| `GET` | `/health` | Saúde do serviço |
| `GET` | `/ready` | Prontidão das dependências |
| `GET` | `/api/v1/state` | Snapshot da simulação |
| `POST` | `/api/v1/scenarios/{id}/pause` | Pausar |
| `POST` | `/api/v1/scenarios/{id}/resume` | Retomar |
| `POST` | `/api/v1/scenarios/{id}/speed` | Velocidade |
| `POST` | `/api/v1/scenarios/{id}/strategy` | Estratégia de rota |
| `POST` | `/api/v1/scenarios/{id}/weather` | Clima |
| `POST` | `/api/v1/scenarios/{id}/reset` | Reset |
| `POST` | `/api/v1/roads/block` | Bloquear/liberar EPTG no backend |
| `POST` | `/api/v1/alerts/force-critical` | Forçar ponto crítico |
| `GET` | `/api/v1/export` | Snapshot JSON |

---

## 12. Atalhos

| Tecla | Ação |
|---|---|
| `Espaço` | Play/Pause |
| `1` a `6` | Velocidades |
| `R` | Reset |
| `B` | Interdição |
| `C` | Forçar lixeira crítica |
| `L` | Painel esquerdo |
| `T` | Timeline |
| `H` | Heatmap |
| `?` | Ajuda |
| `Esc` | Fechar/limpar seleção |

---

## 13. Limitações conhecidas

- O VRP Smart é heurístico e não um solver exato.
- O grafo viário é simplificado e didático.
- Custos, emissões e baseline são parametrizados/simulados.
- A interface permite selecionar 1–10 caminhões, enquanto o backend Python mantém atualmente 3 caminhões canônicos; acima de 3, o redimensionamento pertence ao simulador da interface.
- Existe uma camada SQLite no código, mas ela ainda não está conectada ao fluxo operacional principal; `/ready` informa isso explicitamente.
- O frontend usa bibliotecas via CDN; para uma operação completamente offline essas dependências precisam ser empacotadas localmente.
- Abrir somente `index.html` usa o fallback estático original. Para garantir as regras e o PDF descritos neste README, execute `run_lab.bat`/`run_lab.py` e acesse `http://localhost:8000`.

Possíveis evoluções: OR-Tools, PostGIS, broker MQTT real, persistência histórica, autenticação, cenários versionados e comparação automatizada entre múltiplas seeds.

---

## 14. Licença e atribuição

- Código: **MIT / Open Source**.
- OpenStreetMap: respeitar ODbL quando dados derivados forem usados.
- IPEDF e demais fontes públicas: manter a licença/atribuição aplicável ao conjunto utilizado.

---

## Resumo rápido

```text
ROTA FIXA
sequência cíclica -> previsível, mas não prioriza urgência

MAIS PRÓXIMO
menor distância entre bins >=20% -> rápido, mas guloso

VRP SMART
maior score entre bins >=25%
urgência + distância + capacidade -> adaptativo, porém heurístico
```
