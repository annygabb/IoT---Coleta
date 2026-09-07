import heapq
from typing import Dict, List, Tuple
from apps.api.app.domain.geo.brasilia_network import BRASILIA_NODES, BRASILIA_ROADS

class DijkstraRouter:
    """
    Roteador de caminhos mínimos sobre a malha de Brasília.
    Suporta pesos dinâmicos de trânsito e penalidade infinita em caso de via bloqueada (RN-006).
    """
    def __init__(self):
        self.blocked_road_ids = set()

    def set_road_block(self, road_id: str, is_blocked: bool):
        if is_blocked:
            self.blocked_road_ids.add(road_id)
        else:
            self.blocked_road_ids.discard(road_id)

    def is_eptg_blocked(self) -> bool:
        return any(r in self.blocked_road_ids for r in ['ROAD_EPTG_2', 'ROAD_EPTG_3'])

    def set_eptg_blocked(self, blocked: bool):
        self.set_road_block('ROAD_EPTG_2', blocked)
        self.set_road_block('ROAD_EPTG_3', blocked)

    def _build_adjacency(self, is_peak_hour: bool = False) -> Dict[str, List[Tuple[str, float, str]]]:
        adj: Dict[str, List[Tuple[str, float, str]]] = {node_id: [] for node_id in BRASILIA_NODES}

        for road in BRASILIA_ROADS:
            road_id = road['id']
            if road_id in self.blocked_road_ids:
                continue # Via interditada / custo infinito

            weight = road['length_km']
            if is_peak_hour and road.get('is_eptg'):
                weight *= 1.8 # Congestionamento nos horários de pico

            adj[road['from']].append((road['to'], weight, road_id))
            adj[road['to']].append((road['from'], weight, road_id))

        return adj

    def find_shortest_path(self, start_node: str, target_node: str, is_peak_hour: bool = False) -> Tuple[List[str], float]:
        """
        Calcula a sequência de nós e a distância total em km até o destino.
        Retorna (lista_de_nos, distancia_km).
        """
        if start_node == target_node:
            return [start_node], 0.0

        adj = self._build_adjacency(is_peak_hour)
        distances: Dict[str, float] = {node_id: float('inf') for node_id in BRASILIA_NODES}
        previous: Dict[str, str] = {node_id: None for node_id in BRASILIA_NODES}

        distances[start_node] = 0.0
        pq: List[Tuple[float, str]] = [(0.0, start_node)]

        while pq:
            curr_dist, curr_node = heapq.heappop(pq)

            if curr_node == target_node:
                break

            if curr_dist > distances[curr_node]:
                continue

            for neighbor, weight, _ in adj.get(curr_node, []):
                new_dist = curr_dist + weight
                if new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = curr_node
                    heapq.heappush(pq, (new_dist, neighbor))

        # Reconstrução da rota
        if distances[target_node] == float('inf'):
            return [start_node], float('inf') # Sem rota viável devido a bloqueios

        path = []
        curr = target_node
        while curr:
            path.append(curr)
            curr = previous[curr]

        path.reverse()
        return path, distances[target_node]
