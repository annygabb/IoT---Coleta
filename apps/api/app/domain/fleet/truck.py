from typing import List, Optional, Dict, Any
from apps.api.app.domain.iot.contracts import TruckState

class CollectionTruck:
    """
    Entidade de Caminhão Coletor de Resíduos Urbanos do SLU.
    Possui capacidade máxima (5.000 kg), consumo parametrizado e máquina de estados canônica.
    """
    def __init__(
        self,
        truck_id: str,
        name: str,
        color: str,
        capacity_kg: float = 5000.0,
        initial_node: str = "GARAGEM_SLU",
        base_speed_kmh: float = 40.0,
        base_consumption_l_per_km: float = 0.35 # ~2.8 km/L
    ):
        self.id = truck_id
        self.name = name
        self.color = color
        self.capacity_kg = capacity_kg
        self.load_kg = 0.0
        self.current_node = initial_node
        self.target_node = initial_node
        self.target_bin_id: Optional[str] = None
        self.state = TruckState.OCIOSO

        self.path: List[str] = []
        self.path_progress: float = 0.0 # 0.0 a 1.0 no segmento atual
        self.base_speed_kmh = base_speed_kmh
        self.base_consumption_l_km = base_consumption_l_per_km

        # Métricas acumuladas
        self.total_distance_km = 0.0
        self.total_collected_kg = 0.0
        self.disposal_trips = 0
        self.fuel_consumed_liters = 0.0

        # Temporizador de operação
        self.operation_timer_seconds = 0.0

    @property
    def available_capacity_kg(self) -> float:
        return max(0.0, self.capacity_kg - self.load_kg)

    @property
    def is_full(self) -> bool:
        """Considera lotado quando atinge 90% da capacidade nominal (RN-004)."""
        return self.load_kg >= (self.capacity_kg * 0.90)

    def calculate_fuel(self, distance_km: float, weather_factor: float, traffic_factor: float) -> float:
        """
        Cálculo simplificado de combustível (Cap. 14.3):
        combustivel_l = distancia_km * consumo_base_l_km * fator_carga * fator_transito * fator_clima
        """
        load_factor = 1.0 + (self.load_kg / self.capacity_kg) * 0.30 # +30% de consumo com carga cheia
        consumed = distance_km * self.base_consumption_l_km * load_factor * traffic_factor * weather_factor
        self.fuel_consumed_liters += consumed
        return consumed

    def assign_route(self, path: List[str], target_bin_id: Optional[str], target_node: str):
        self.path = path
        self.path_progress = 0.0
        self.target_bin_id = target_bin_id
        self.target_node = target_node
        self.state = TruckState.EM_ROTA

    def start_collection(self, duration_s: float = 12.0):
        self.state = TruckState.COLETANDO
        self.operation_timer_seconds = duration_s

    def complete_collection(self, collected_kg: float):
        self.load_kg = min(self.capacity_kg, self.load_kg + collected_kg)
        self.total_collected_kg += collected_kg
        self.target_bin_id = None
        if self.is_full:
            self.state = TruckState.CHEIO
        else:
            self.state = TruckState.OCIOSO

    def start_disposal(self, duration_s: float = 20.0):
        self.state = TruckState.DESCARREGANDO
        self.operation_timer_seconds = duration_s

    def complete_disposal(self):
        unloaded = self.load_kg
        self.load_kg = 0.0
        self.disposal_trips += 1
        self.state = TruckState.OCIOSO
        return unloaded

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'capacity_kg': self.capacity_kg,
            'load_kg': round(self.load_kg, 1),
            'load_pct': round((self.load_kg / self.capacity_kg) * 100.0, 1),
            'current_node': self.current_node,
            'target_node': self.target_node,
            'target_bin_id': self.target_bin_id,
            'state': self.state.value,
            'total_distance_km': round(self.total_distance_km, 2),
            'total_collected_kg': round(self.total_collected_kg, 1),
            'disposal_trips': self.disposal_trips,
            'fuel_consumed_liters': round(self.fuel_consumed_liters, 2)
        }
