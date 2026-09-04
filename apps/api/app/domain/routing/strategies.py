from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict, Any
from apps.api.app.domain.waste.bin import SmartBin
from apps.api.app.domain.fleet.truck import CollectionTruck
from apps.api.app.domain.routing.dijkstra import DijkstraRouter
from apps.api.app.domain.geo.brasilia_network import BRASILIA_NODES

class BaseRoutingStrategy(ABC):
    @abstractmethod
    def select_next_bin(
        self,
        truck: CollectionTruck,
        available_bins: List[SmartBin],
        other_trucks: List[CollectionTruck],
        router: DijkstraRouter,
        is_peak_hour: bool = False
    ) -> Tuple[Optional[SmartBin], str]:
        """
        Seleciona a próxima lixeira a ser atendida pelo caminhão.
        Retorna (lixeira_escolhida, justificativa_textual).
        """
        pass

class FixedBaselineStrategy(BaseRoutingStrategy):
    """
    Estratégia Tradicional de Rota Fixa (Baseline SLU pré-IoT).
    Visita todas as lixeiras em ordem estrita de itinerário sem considerar o nível do sensor.
    """
    def select_next_bin(
        self,
        truck: CollectionTruck,
        available_bins: List[SmartBin],
        other_trucks: List[CollectionTruck],
        router: DijkstraRouter,
        is_peak_hour: bool = False
    ) -> Tuple[Optional[SmartBin], str]:
        if not available_bins:
            return None, "Nenhuma lixeira elegível no roteiro."

        # Ordenação fixa por ID numérico sequencial
        sorted_bins = sorted(
            [b for b in available_bins if not any(t.id != truck.id and t.target_bin_id == b.id for t in other_trucks)],
            key=lambda b: int(b.id.replace("BIN-", "")) if b.id.replace("BIN-", "").isdigit() else 999
        )

        if not sorted_bins:
            return None, "Todas as lixeiras do itinerário já estão sob atendimento."

        chosen = sorted_bins[0]
        return chosen, f"Itinerário pré-definido sequencial atendendo {chosen.id} ({chosen.name}) independente de telemetria."

class NearestPriorityStrategy(BaseRoutingStrategy):
    """
    Heurística Gulosa de Ponto Mais Próximo (Nearest Neighbor).
    Atende o ponto geograficamente mais próximo com nível >= 20%.
    """
    def select_next_bin(
        self,
        truck: CollectionTruck,
        available_bins: List[SmartBin],
        other_trucks: List[CollectionTruck],
        router: DijkstraRouter,
        is_peak_hour: bool = False
    ) -> Tuple[Optional[SmartBin], str]:
        candidates = [
            b for b in available_bins
            if b.fill_pct >= 20.0 and not any(t.id != truck.id and t.target_bin_id == b.id for t in other_trucks)
        ]

        if not candidates:
            return None, "Nenhuma lixeira com carga mínima (>=20%) disponível."

        best_bin = None
        min_dist = float('inf')

        for b in candidates:
            _, dist_km = router.find_shortest_path(truck.current_node, b.node_id, is_peak_hour)
            if dist_km < min_dist:
                min_dist = dist_km
                best_bin = b

        if best_bin:
            return best_bin, f"Heurística gulosa: menor distância física até {best_bin.id} ({min_dist:.1f} km)."
        return None, "Nenhum caminho viável para os candidatos."

class SmartVRPStrategy(BaseRoutingStrategy):
    """
    Estratégia VRP Smart IoT Adaptativa (Cap. 15.2).
    Combina urgência do sensor, tempo até transbordo, distância viária real e capacidade do caminhão.
    """
    def select_next_bin(
        self,
        truck: CollectionTruck,
        available_bins: List[SmartBin],
        other_trucks: List[CollectionTruck],
        router: DijkstraRouter,
        is_peak_hour: bool = False
    ) -> Tuple[Optional[SmartBin], str]:
        # Filtrar lixeiras já alvo de outro caminhão
        candidates = [
            b for b in available_bins
            if b.fill_pct >= 25.0 and not any(t.id != truck.id and t.target_bin_id == b.id for t in other_trucks)
        ]

        if not candidates:
            return None, "Todas as lixeiras monitoradas operam em níveis seguros (<25%)."

        best_bin = None
        highest_score = -float('inf')
        reason_factors: Dict[str, Any] = {}

        for b in candidates:
            _, dist_km = router.find_shortest_path(truck.current_node, b.node_id, is_peak_hour)
            if dist_km == float('inf'):
                continue

            # Multiplicador de urgência proporcional ao risco sanitário
            urgency_weight = b.fill_pct
            if b.fill_pct >= 100.0:
                urgency_weight *= 4.0 # Transbordo imediato!
            elif b.fill_pct >= 85.0:
                urgency_weight *= 2.8 # Crítico
            elif b.fill_pct >= 70.0:
                urgency_weight *= 1.6 # Alta

            # Penalidade se a lixeira tiver mais lixo do que a capacidade restante do caminhão
            capacity_penalty = 1.0
            if b.current_waste_kg > truck.available_capacity_kg:
                capacity_penalty = 0.70

            # Score = (Urgência^1.8 * Capacidade) / (Distância + 2.0)
            score = ((urgency_weight ** 1.8) * capacity_penalty) / (dist_km + 2.0)

            if score > highest_score:
                highest_score = score
                best_bin = b
                reason_factors = {
                    'fill_pct': round(b.fill_pct, 1),
                    'dist_km': round(dist_km, 1),
                    'urgency_weight': round(urgency_weight, 1),
                    'score': round(score, 1)
                }

        if best_bin:
            justification = (
                f"VRP Smart IoT: {best_bin.id} ({best_bin.name}) selecionada com score {reason_factors.get('score')} "
                f"(Lotação: {reason_factors.get('fill_pct')}%, Distância: {reason_factors.get('dist_km')} km)."
            )
            return best_bin, justification

        return None, "Sem rotas disponíveis para os candidatos avaliados."
