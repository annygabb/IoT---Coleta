# SmartWaste DF — Digital Twin & Simulação IoT para Coleta Inteligente de Resíduos

> **Laboratório Open Source para o Distrito Federal / Brasília (Princípio de Custo Zero — R$ 0)**  
> Documentação Completa de Engenharia de Software, IoT, Roteamento VRP e Telemetria em Tempo Real.

---

## 📌 Visão Geral

O **SmartWaste DF** é uma plataforma educacional e experimental projetada para fechar o ciclo completo de um sistema de cidades inteligentes:
1. **Sensores Virtuais** geram telemetria contínua (nível de ocupação, distância ultrassônica, temperatura, bateria).
2. **Gateway IoT & Broker MQTT** transmitem e normalizam mensagens sob tópicos versionados (`smartwaste/df/...`).
3. **Backend FastAPI Modular** ingere, valida schemas Pydantic e avalia regras de criticidade sanitária.
4. **Motor de Decisão & VRP Smart** seleciona o caminhão ideal com base na urgência, proximidade e capacidade restante.
5. **Comandos Idempotentes** despacham atuadores de caminhões pela malha viária real de Brasília.
6. **Coleta e Descarte:** O caminhão esvazia a lixeira e, ao atingir a capacidade nominal (5.000 kg), é roteado para o **Aterro Sanitário de Brasília (Samambaia)**.
7. **Explicabilidade & Auditoria:** Toda decisão é persistida e explicada em linguagem natural na interface.

---

## 🚀 Como Executar

### 1. Início Rápido (1 Comando — DoD-01)
No Windows:
```cmd
run_lab.bat
```
Ou via terminal (Windows / macOS / Linux):
```bash
python run_lab.py
```
Acesse no navegador:
* **Aplicação Web:** [http://localhost:8000](http://localhost:8000) ou [http://localhost:5173](http://localhost:5173)
* **Documentação Interativa da API (OpenAPI):** [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Execução dos Testes Automatizados
```bash
python -m pytest tests
```

---

## 🗺️ Mapa de Brasília / DF

O sistema modela a bacia urbana do DF:
* **Plano Piloto:** Asa Sul, Asa Norte, Eixo Rodoviário (Eixão), Eixo Monumental, Esplanada, Rodoviária, Torre de TV, Lago Paranoá.
* **Regiões Administrativas:** Ceilândia, Taguatinga, Samambaia, Águas Claras, Guará, Sudoeste, Lago Sul/Norte.
* **Rodovias Principais:** EPTG (DF-085), Via Estrutural (DF-095), EPNB (DF-075).
* **Unidade de Descarte:** Aterro Sanitário de Brasília (DF-459, Samambaia).

---

## 📊 Arquitetura de Software

* **Backend:** FastAPI + Pydantic v2 + SQLite Local / PostGIS compatibility.
* **Broker:** Broker MQTT virtual em memória com QoS 1 e janela de idempotência para `command_id`.
* **Frontend:** PWA / Canvas 2D 60 FPS + Tailwind CSS + Lucide Icons + Chart.js.
* **Dois Modos:**
  * **🟢 Modo Laboratório:** Conectado via WebSocket bidirecional ao backend FastAPI.
  * **🟡 Modo Demo PWA:** Autônomo e offline-first no navegador via simulação local.

---

## 📜 Licença e Atribuição

* **Código do Projeto:** Licença MIT / Open Source.
* **OpenStreetMap (OSM):** Dados sob licença ODbL (Open Database License).
* **IPEDF (Instituto de Pesquisa e Estatística do DF):** Camada vetorial de Regiões Administrativas 2026 em Domínio Público.
