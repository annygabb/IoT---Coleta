# Roteiro de Demonstração (15 Minutos) — SmartWaste DF

Este roteiro permite apresentar o sistema a bancas avaliadoras, professores ou equipes técnicas demonstrando a arquitetura IoT e o ganho operacional.

---

### Passo a Passo da Apresentação

1. **Abertura do Sistema:**
   * Abrir a aplicação web através de `http://localhost:5173` ou `http://localhost:8000`.
   * Destacar o status dos serviços e a ausência total de APIs pagas ou cartões de crédito (Princípio Open Source / R$ 0).

2. **Apresentação do Cenário de Brasília:**
   * Demonstrar o mapa 2D com o Plano Piloto (Eixos), Regiões Administrativas (Taguatinga, Ceilândia, Samambaia, Águas Claras, Lago Sul) e o Aterro Sanitário Samambaia.
   * Exibir a legenda dos sensores IoT: <50% verde, 50-69% amarelo, 70-84% laranja, 85-99% vermelho, ≥100% transbordo pulsante.

3. **Início da Simulação & Aceleração de Relógio:**
   * Clicar no botão **Play** e acelerar para **60x** (1 minuto simulado por segundo real).
   * Observar a geração orgânica de lixo nas lixeiras conforme o horário de pico.

4. **Ciclo IoT Completo (M1):**
   * Clicar no botão **"+Lixeira Crítica"** para forçar um evento de emergência (>85%).
   * Apontar para o console MQTT inferior: demonstrar a telemetria sendo emitida, o evento de alerta e o comando de despacho `ASSIGN_ROUTE` emitido com `command_id` idempotente.
   * Acompanhar o caminhão se deslocando pela malha rodoviária real, coletando o lixo da lixeira e reduzindo seu volume para o residual (~2%).

5. **Lotação & Ciclo de Descarte:**
   * Observar a barra de capacidade do caminhão (5.000 kg).
   * Ao atingir a capacidade máxima, o caminhão altera o estado para `HEADING_DISPOSAL` e viaja até o **Aterro Sanitário Samambaia**, descarregando os resíduos e retornando à operação.

6. **Bloqueio de Via & Recálculo Dinâmico:**
   * Clicar no botão **"Bloquear EPTG"** para simular uma colisão/interdição na principal artéria do DF.
   * Observar o recálculo em tempo real da rota dos caminhões desviando via Estrutural ou EPNB.

7. **Análise de Custo-Benefício & ROI (Cap. 18):**
   * Mostrar os cartões da aba **Custo & ROI**:
     * Economia financeira estimada (R$).
     * Distância economizada (km).
     * Litros de diesel e emissões de CO₂ evitadas.
     * Transbordos prevenidos pelo algoritmo inteligente comparado à Rota Fixa.

8. **Exportação de Dados:**
   * Clicar em **"Exportar Dados"** para baixar o snapshot em JSON contendo parâmetros, seed e KPIs para auditoria externa.
