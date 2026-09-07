/*
 * SmartWaste DF - Routing & PDF documentation enhancements
 * Loaded by the FastAPI integrated laboratory after the base simulator script.
 *
 * Goals:
 * 1) keep frontend routing behavior aligned with backend strategies;
 * 2) synchronize strategy selection with the FastAPI engine;
 * 3) make the exported PDF explain route criteria, strengths and trade-offs.
 */
(() => {
  'use strict';

  const ROUTING_STRATEGY_INFO = {
    FIXED: {
      label: 'Rota Fixa',
      short: 'Itinerário cíclico por BIN-ID, sem usar a lotação como prioridade.',
      criteria: 'BIN-01 → BIN-02 → ... → BIN-32 → reinicia. Pula ponto já atribuído a outro caminhão ou sem caminho viável.',
      advantages: 'Previsível, simples de auditar, baixa complexidade operacional.',
      limitations: 'Pode visitar lixeiras pouco cheias e ignorar urgências mais distantes; tende a gerar km desnecessários.'
    },
    NEAREST: {
      label: 'Mais Próximo',
      short: 'Heurística gulosa que atende o ponto elegível de menor distância viária.',
      criteria: 'Considera lixeiras com lotação ≥ 20% e escolhe a menor distância pelo Dijkstra na malha atual.',
      advantages: 'Decisão rápida, reduz deslocamento imediato, fácil de explicar.',
      limitations: 'O melhor próximo passo não garante a melhor rota global; pode adiar pontos críticos mais distantes.'
    },
    VRP_SMART: {
      label: 'VRP Smart',
      short: 'Heurística adaptativa que combina urgência, distância e capacidade restante.',
      criteria: 'Lixeiras ≥ 25%; score = (urgência^1,8 × penalidade_capacidade) / (distância_km + 2).',
      advantages: 'Prioriza risco de transbordo sem ignorar deslocamento e capacidade; reage à telemetria e à malha viária.',
      limitations: 'É uma heurística, não um solucionador VRP exato; qualidade depende dos pesos e da fidelidade dos dados simulados.'
    }
  };

  const fixedRouteCursorByTruck = new Map();

  function strategyInfo(code = simState.strategy) {
    return ROUTING_STRATEGY_INFO[code] || ROUTING_STRATEGY_INFO.VRP_SMART;
  }

  function binNumber(bin) {
    const n = Number.parseInt(String(bin.id).replace('BIN-', ''), 10);
    return Number.isFinite(n) ? n : Number.MAX_SAFE_INTEGER;
  }

  function findShortestPathWithDistance(startNodeId, targetNodeId) {
    if (startNodeId === targetNodeId) {
      return { path: [startNodeId], distanceKm: 0 };
    }

    const adj = buildAdjacencyList();
    const distances = {};
    const previous = {};
    const queue = [{ node: startNodeId, dist: 0 }];

    for (const node in MAP_NODES) {
      distances[node] = Infinity;
      previous[node] = null;
    }
    distances[startNodeId] = 0;

    while (queue.length > 0) {
      queue.sort((a, b) => a.dist - b.dist);
      const current = queue.shift();
      if (!current || current.dist > distances[current.node]) continue;
      if (current.node === targetNodeId) break;

      for (const neighbor of (adj[current.node] || [])) {
        const candidateDistance = current.dist + neighbor.weight;
        if (candidateDistance < distances[neighbor.node]) {
          distances[neighbor.node] = candidateDistance;
          previous[neighbor.node] = current.node;
          queue.push({ node: neighbor.node, dist: candidateDistance });
        }
      }
    }

    if (!Number.isFinite(distances[targetNodeId])) {
      return { path: [startNodeId], distanceKm: Infinity };
    }

    const path = [];
    let cursor = targetNodeId;
    while (cursor) {
      path.unshift(cursor);
      cursor = previous[cursor];
    }

    return { path, distanceKm: distances[targetNodeId] };
  }

  function sendTruckToGarage(truck) {
    const route = findShortestPathWithDistance(truck.currentNode, 'GARAGEM_SLU');
    truck.state = 'OCIOSO';
    truck.targetNode = 'GARAGEM_SLU';
    truck.targetBinId = null;
    truck.path = route.path;
    truck.pathProgress = 0;
  }

  // Replaces the base browser solver so the three UI modes use the same rules as the backend.
  solveNextTargetForTruck = function solveNextTargetForTruckAligned(truck) {
    if (truck.loadKg >= truck.capacityKg * 0.90) {
      const route = findShortestPathWithDistance(truck.currentNode, 'ATERRO_SAMAMBAIA');
      truck.state = 'INDO_DESCARTE';
      truck.targetNode = 'ATERRO_SAMAMBAIA';
      truck.targetBinId = null;
      truck.path = route.path;
      truck.pathProgress = 0;
      addTimelineEvent(
        'DESP_ATERRO',
        `Caminhão ${truck.id} com ${Math.round((truck.loadKg / truck.capacityKg) * 100)}% de carga. Roteado ao Aterro Samambaia.`
      );
      return;
    }

    const notAssignedToAnotherTruck = (bin) => !TRUCKS.some(
      (otherTruck) => otherTruck.id !== truck.id && otherTruck.targetBinId === bin.id
    );

    let chosenBin = null;
    let chosenRoute = null;
    let reasonText = '';

    if (simState.strategy === 'FIXED') {
      const ordered = SMART_BINS
        .filter(notAssignedToAnotherTruck)
        .slice()
        .sort((a, b) => binNumber(a) - binNumber(b));

      if (ordered.length > 0) {
        const lastIndex = fixedRouteCursorByTruck.get(truck.id) ?? -1;
        for (let offset = 1; offset <= ordered.length; offset += 1) {
          const candidateIndex = (lastIndex + offset) % ordered.length;
          const candidate = ordered[candidateIndex];
          const route = findShortestPathWithDistance(truck.currentNode, candidate.node);
          if (Number.isFinite(route.distanceKm)) {
            chosenBin = candidate;
            chosenRoute = route;
            fixedRouteCursorByTruck.set(truck.id, candidateIndex);
            reasonText = `${truck.id} segue Rota Fixa para ${candidate.id} (${candidate.name}). Lotação ${Math.round(candidate.fillPct)}% é monitorada, mas não altera a prioridade do itinerário.`;
            break;
          }
        }
      }
    } else if (simState.strategy === 'NEAREST') {
      const candidates = SMART_BINS.filter(
        (bin) => bin.fillPct >= 20 && notAssignedToAnotherTruck(bin)
      );
      let bestDistance = Infinity;

      for (const candidate of candidates) {
        const route = findShortestPathWithDistance(truck.currentNode, candidate.node);
        if (route.distanceKm < bestDistance) {
          bestDistance = route.distanceKm;
          chosenBin = candidate;
          chosenRoute = route;
        }
      }

      if (chosenBin) {
        reasonText = `${truck.id} escolheu o ponto mais próximo: ${chosenBin.id} (${chosenBin.name}), ${bestDistance.toFixed(1)} km pela malha viária, lotação ${Math.round(chosenBin.fillPct)}%.`;
      }
    } else {
      const candidates = SMART_BINS.filter(
        (bin) => bin.fillPct >= 25 && notAssignedToAnotherTruck(bin)
      );
      let bestScore = -Infinity;
      let bestDistance = Infinity;
      let bestCapacityPenalty = 1;

      for (const candidate of candidates) {
        const route = findShortestPathWithDistance(truck.currentNode, candidate.node);
        if (!Number.isFinite(route.distanceKm)) continue;

        let urgency = candidate.fillPct;
        if (candidate.fillPct >= 100) urgency *= 4.0;
        else if (candidate.fillPct >= 85) urgency *= 2.8;
        else if (candidate.fillPct >= 70) urgency *= 1.6;

        const estimatedWasteKg = candidate.capacity * (candidate.fillPct / 100) * 0.40;
        const availableCapacityKg = Math.max(0, truck.capacityKg - truck.loadKg);
        const capacityPenalty = estimatedWasteKg > availableCapacityKg ? 0.70 : 1.0;
        const score = (Math.pow(urgency, 1.8) * capacityPenalty) / (route.distanceKm + 2.0);

        if (score > bestScore) {
          bestScore = score;
          bestDistance = route.distanceKm;
          bestCapacityPenalty = capacityPenalty;
          chosenBin = candidate;
          chosenRoute = route;
        }
      }

      if (chosenBin) {
        const capacityNote = bestCapacityPenalty < 1 ? 'com penalidade de capacidade' : 'capacidade compatível';
        reasonText = `${truck.id} despachado pelo VRP Smart para ${chosenBin.id} (${chosenBin.name}) com score ${bestScore.toFixed(1)}: ${Math.round(chosenBin.fillPct)}% de lotação, ${bestDistance.toFixed(1)} km e ${capacityNote}.`;
      }
    }

    if (!chosenBin || !chosenRoute) {
      sendTruckToGarage(truck);
      return;
    }

    truck.state = 'EM_ROTA';
    truck.targetBinId = chosenBin.id;
    truck.targetNode = chosenBin.node;
    truck.path = chosenRoute.path;
    truck.pathProgress = 0;
    addTimelineEvent('DISPATCH', reasonText);
  };

  const baseChangeStrategy = changeStrategy;
  changeStrategy = function changeStrategyDocumented(strategy) {
    simState.strategy = strategy;
    const info = strategyInfo(strategy);
    playBeep(680, 'sine', 0.07);
    addTimelineEvent('STRATEGY', `${info.label} ativada. ${info.short}`);
    TRUCKS.forEach((truck) => solveNextTargetForTruck(truck));

    // In laboratory mode, keep the backend engine on the same selected strategy.
    fetch(`/api/v1/scenarios/default/strategy?strategy=${encodeURIComponent(strategy)}`, { method: 'POST' })
      .catch(() => {
        // The standalone/demo interface may not have a FastAPI backend. Local simulation keeps working.
      });

    return typeof baseChangeStrategy === 'undefined' ? undefined : strategy;
  };

  const baseResetSimulation = resetSimulation;
  resetSimulation = function resetSimulationWithRouteCursor() {
    fixedRouteCursorByTruck.clear();
    return baseResetSimulation();
  };

  function addPdfSectionTitle(doc, number, title, y) {
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(10);
    doc.text(`${number}. ${title}`, 14, y);
  }

  function addPdfFooter(doc, activeStrategyLabel) {
    const pages = doc.internal.getNumberOfPages();
    for (let page = 1; page <= pages; page += 1) {
      doc.setPage(page);
      const height = doc.internal.pageSize.getHeight();
      const width = doc.internal.pageSize.getWidth();
      doc.setDrawColor(226, 232, 240);
      doc.line(14, height - 10, width - 14, height - 10);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(100, 116, 139);
      doc.text(`SmartWaste DF | Estratégia ativa: ${activeStrategyLabel}`, 14, height - 5.5);
      doc.text(`Página ${page} de ${pages}`, width - 14, height - 5.5, { align: 'right' });
    }
  }

  // Replaces the base exporter with a report that documents the three routing strategies.
  exportSimulationPDF = function exportSimulationPDFDocumented() {
    if (!window.jspdf || !window.jspdf.jsPDF) {
      alert('Biblioteca jsPDF carregando. Aguarde alguns instantes e tente novamente.');
      return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const activeInfo = strategyInfo();
    const nowStr = new Date().toLocaleString('pt-BR');

    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, pageWidth, 29, 'F');
    doc.setFillColor(16, 185, 129);
    doc.rect(0, 27.5, pageWidth, 1.5, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(14);
    doc.text('SMARTWASTE DF - RELATÓRIO OPERACIONAL IoT', 14, 11);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(203, 213, 225);
    doc.setFontSize(8.2);
    doc.text('Digital Twin e simulação de coleta inteligente de resíduos no Distrito Federal', 14, 18);
    doc.setFontSize(7.5);
    doc.text(`Emissão: ${nowStr} | Seed: ${currentSeed} | Estratégia: ${activeInfo.label} (${simState.strategy})`, 14, 24);

    let y = 36;
    addPdfSectionTitle(doc, 1, 'PARÂMETROS DA SIMULAÇÃO', y);
    y += 4;
    const blockedRoad = ROAD_SEGMENTS.find((road) => road.id === simState.blockedRoadId);
    const roadStatus = blockedRoad ? `Interdição: ${blockedRoad.name}` : 'Fluxo viário normal';
    doc.autoTable({
      startY: y,
      theme: 'grid',
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 8 },
      bodyStyles: { fontSize: 7.8, textColor: [30, 41, 59] },
      columnStyles: { 0: { fontStyle: 'bold', cellWidth: 40 }, 1: { cellWidth: 51 }, 2: { fontStyle: 'bold', cellWidth: 40 }, 3: { cellWidth: 51 } },
      body: [
        ['Tempo simulado', `${formatClock(simState.simTimeSeconds)} (Dia ${simState.simDay})`, 'Frota ativa', `${TRUCKS.length} caminhão(ões)`],
        ['Estratégia ativa', `${activeInfo.label} (${simState.strategy})`, 'Clima', `${simState.weather} (${simState.weatherFactor}x)`],
        ['Malha viária', roadStatus, 'Pontos IoT', `${SMART_BINS.length} lixeiras monitoradas`]
      ]
    });

    y = doc.lastAutoTable.finalY + 8;
    addPdfSectionTitle(doc, 2, 'ESTRATÉGIAS DE ROTEAMENTO - COMO DECIDEM', y);
    y += 4;
    doc.autoTable({
      startY: y,
      theme: 'grid',
      head: [['Estratégia', 'Como decide', 'Vantagens', 'Desvantagens / limites']],
      headStyles: { fillColor: [15, 118, 110], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 7.2 },
      bodyStyles: { fontSize: 6.8, valign: 'top', cellPadding: 1.5 },
      columnStyles: { 0: { cellWidth: 27, fontStyle: 'bold' }, 1: { cellWidth: 57 }, 2: { cellWidth: 49 }, 3: { cellWidth: 49 } },
      body: [
        ['Rota Fixa', ROUTING_STRATEGY_INFO.FIXED.criteria, ROUTING_STRATEGY_INFO.FIXED.advantages, ROUTING_STRATEGY_INFO.FIXED.limitations],
        ['Mais Próximo', ROUTING_STRATEGY_INFO.NEAREST.criteria, ROUTING_STRATEGY_INFO.NEAREST.advantages, ROUTING_STRATEGY_INFO.NEAREST.limitations],
        ['VRP Smart', ROUTING_STRATEGY_INFO.VRP_SMART.criteria, ROUTING_STRATEGY_INFO.VRP_SMART.advantages, ROUTING_STRATEGY_INFO.VRP_SMART.limitations]
      ],
      didParseCell(data) {
        if (data.section === 'body') {
          const rowCode = ['FIXED', 'NEAREST', 'VRP_SMART'][data.row.index];
          if (rowCode === simState.strategy) data.cell.styles.fillColor = [236, 253, 245];
        }
      }
    });

    y = doc.lastAutoTable.finalY + 5;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(15, 23, 42);
    doc.text('Metodologia do VRP Smart:', 14, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.2);
    const smartMethod = 'Candidatos com lotação >=25%. Urgência = lotação, multiplicada por 1,6 a partir de 70%, 2,8 a partir de 85% e 4,0 a partir de 100%. Se a massa estimada não couber na capacidade restante do caminhão, aplica-se penalidade 0,70. Score = (urgência^1,8 x penalidade) / (distância_km + 2). Maior score vence. Trata-se de uma heurística adaptativa, não de um solucionador matemático VRP exato.';
    const methodLines = doc.splitTextToSize(smartMethod, pageWidth - 28);
    doc.text(methodLines, 14, y + 4);

    y += 4 + methodLines.length * 3.2 + 6;
    addPdfSectionTitle(doc, 3, 'INDICADORES OPERACIONAIS', y);
    y += 4;
    const estimatedBaselineDistance = simState.totalDistanceKm * 1.42;
    const estimatedBaselineCost = simState.baselineTotalCost;
    const savings = Math.max(0, estimatedBaselineCost - simState.smartTotalCost);
    const savingsPct = estimatedBaselineCost > 0 ? (savings / estimatedBaselineCost) * 100 : 0;
    doc.autoTable({
      startY: y,
      theme: 'striped',
      head: [['Indicador', `Estratégia ativa: ${activeInfo.label}`, 'Baseline estimado', 'Leitura']],
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 7.3 },
      bodyStyles: { fontSize: 7.1 },
      body: [
        ['Custo operacional', `R$ ${simState.smartTotalCost.toFixed(2)}`, `R$ ${estimatedBaselineCost.toFixed(2)}`, `Economia simulada: R$ ${savings.toFixed(2)} (${savingsPct.toFixed(1)}%)`],
        ['Distância', `${simState.totalDistanceKm.toFixed(1)} km`, `${estimatedBaselineDistance.toFixed(1)} km`, 'Comparativo produzido pelo modelo de simulação'],
        ['Resíduos coletados', `${Math.round(simState.totalWasteCollectedKg)} kg`, '-', `${(simState.totalWasteCollectedKg / 1000).toFixed(2)} t`],
        ['Diesel estimado', `${(simState.totalDistanceKm * 0.35).toFixed(1)} L`, '-', 'Consumo-base: 0,35 L/km'],
        ['CO2 estimado', `${(simState.totalDistanceKm * 0.35 * 2.68).toFixed(1)} kg`, '-', 'Fator: 2,68 kg CO2/L'],
        ['Transbordos atuais', String(simState.overflowIncidentsCurrent), '-', `${simState.overflowIncidentsPrevented} prevenção(ões) registrada(s)`],
        ['Mensagens MQTT', String(simState.mqttCount), 'N/A', 'Telemetria da simulação']
      ]
    });

    doc.addPage();
    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, pageWidth, 17, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(11);
    doc.text(`4. FROTA OPERACIONAL - ${TRUCKS.length} CAMINHÃO(ÕES)`, 14, 11);
    doc.autoTable({
      startY: 22,
      theme: 'grid',
      head: [['ID', 'Caminhão', 'Nó atual', 'Carga', '%', 'Coletado', 'Km', 'Aterro', 'Estado', 'Alvo']],
      headStyles: { fillColor: [30, 41, 59], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 6.8 },
      bodyStyles: { fontSize: 6.5 },
      body: TRUCKS.map((truck) => [
        truck.id,
        truck.name,
        truck.currentNode,
        `${Math.round(truck.loadKg)}/${truck.capacityKg} kg`,
        `${Math.round((truck.loadKg / truck.capacityKg) * 100)}%`,
        `${Math.round(truck.totalCollectedKg)} kg`,
        `${truck.totalDistanceKm.toFixed(1)}`,
        String(truck.disposalTrips),
        truck.state,
        truck.targetBinId || truck.targetNode || '-'
      ])
    });

    doc.addPage();
    doc.setFillColor(15, 23, 42);
    doc.rect(0, 0, pageWidth, 17, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(11);
    doc.text(`5. TELEMETRIA DAS ${SMART_BINS.length} LIXEIRAS IoT`, 14, 11);
    doc.autoTable({
      startY: 22,
      theme: 'grid',
      head: [['ID', 'Ponto', 'Região', 'Tipo', 'Cap.', 'Lotação', 'Status', 'Bateria', 'Temp.']],
      headStyles: { fillColor: [15, 118, 110], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 6.8 },
      bodyStyles: { fontSize: 6.3 },
      body: SMART_BINS.map((bin) => {
        let status = 'Normal';
        if (bin.fillPct >= 100) status = 'Transbordo';
        else if (bin.fillPct >= 85) status = 'Crítica';
        else if (bin.fillPct >= 70) status = 'Alta';
        else if (bin.fillPct >= 50) status = 'Atenção';
        return [bin.id, bin.name, bin.ra, bin.type, `${bin.capacity} L`, `${Math.round(bin.fillPct)}%`, status, `${Math.round(bin.battery)}%`, `${bin.temp.toFixed(1)}°C`];
      })
    });

    let finalY = doc.lastAutoTable.finalY + 7;
    if (finalY > 270) {
      doc.addPage();
      finalY = 22;
    }
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(9);
    doc.text('6. NOTA DE INTERPRETAÇÃO', 14, finalY);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.2);
    doc.setTextColor(71, 85, 105);
    const disclaimer = 'Os valores de custo, economia, combustível, CO2, geração de resíduos e baseline são resultados do modelo de simulação e servem para comparação educacional/experimental. Não representam medição oficial do SLU/DF. A malha viária é simplificada e o VRP Smart é heurístico; resultados variam conforme seed, clima, interdições, frota e telemetria.';
    doc.text(doc.splitTextToSize(disclaimer, pageWidth - 28), 14, finalY + 5);

    addPdfFooter(doc, activeInfo.label);
    const safeTime = formatClock(simState.simTimeSeconds).replaceAll(':', '-');
    doc.save(`SmartWaste_DF_Relatorio_${safeTime}.pdf`);
    addTimelineEvent('EXPORT', `Relatório PDF exportado com metodologia das rotas. Estratégia ativa: ${activeInfo.label}.`);
  };

  // Expose the strategy guide for debugging/documentation without coupling to window state.
  window.SMARTWASTE_ROUTING_STRATEGY_INFO = ROUTING_STRATEGY_INFO;
})();
