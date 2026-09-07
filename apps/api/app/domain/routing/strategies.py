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

    Mantém um itinerário cíclico BIN-01 -> BIN-02 -> ... -> BIN-N e não usa
    telemetria de ocupação para mudar a prioridade. O cursor é independente por
    caminhão para evitar que cada novo despacho volte sempre ao primeiro ponto.
    """
    def __init__(self):
        self._last_selected_index_by_truck: Dict[str, int] = {}

    @staticmethod
    def _bin_order(bin_obj: SmartBin) -> int:
        numeric_id = bin_obj.id.replace("BIN-", "")
        return int(numeric_id) if numeric_id.isdigit() else 999999

    def select_next_bin(
        self,
        truck: CollectionTruck,
        available_bins: List[SmartBin],
        other_trucks: List[CollectionTruck],
        router: DijkstraRouter,
        is_peak_hour: bool = False
    ) -> Tuple[Optional[SmartBin], str]:
        if not available_bins:
            return None, "Nenhuma lixeira disponível no itinerário fixo."

        ordered_bins = sorted(available_bins, key=self._bin_order)
        targeted_ids = {
            t.target_bin_id
            for t in other_trucks
            if t.id != truck.id and t.target_bin_id
        }

        last_index = self._last_selected_index_by_truck.get(truck.id, -1)
        total_bins = len(ordered_bins)

        for offset in range(1, total_bins + 1):
            candidate_index = (last_index + offset) % total_bins
            candidate = ordered_bins[candidate_index]
            if candidate.id in targeted_ids:
                continue

            _, dist_km = router.find_shortest_path(truck.current_node, candidate.node_id, is_peak_hour)
            if dist_km == float('inf'):
                continue

            self._last_selected_index_by_truck[truck.id] = candidate_index
            return candidate, (
                f"Rota fixa cíclica: próximo ponto do itinerário é {candidate.id} ({candidate.name}). "
                f"Ocupação atual {candidate.fill_pct:.1f}% é monitorada, mas não altera a ordem de prioridade."
            )

        return None, "Nenhum ponto do itinerário fixo está disponível e alcançável neste momento."

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
