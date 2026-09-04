from typing import Optional
from apps.api.app.domain.iot.contracts import BinState

class SmartBin:
    """
    Entidade de Lixeira Inteligente com Sensor Virtual IoT acoplado.
    Capacidade em litros, densidade média do resíduo (0.4 kg/L) e estados semânticos de ocupação.
    """
    def __init__(
        self,
        bin_id: str,
        name: str,
        ra: str,
        node_id: str,
        bin_type: str = "Residencial",
        capacity_liters: float = 1200.0,
        initial_fill_pct: float = 30.0,
        generation_rate: float = 1.0
    ):
        self.id = bin_id
        self.name = name
        self.ra = ra
        self.node_id = node_id
        self.bin_type = bin_type
        self.capacity_liters = capacity_liters
        self.fill_pct = initial_fill_pct
        self.generation_rate = generation_rate
        self.sensor_battery = 100.0
        self.temperature_c = 26.0
        self.last_collected_sim_time: Optional[str] = None

    @property
    def current_waste_kg(self) -> float:
        """Massa atual estimada de resíduo em kg (densidade média urbana = 0.40 kg/L)."""
        return (self.fill_pct / 100.0) * (self.capacity_liters * 0.40)

    @property
    def max_capacity_kg(self) -> float:
        return self.capacity_liters * 0.40

    @property
    def state(self) -> BinState:
        if self.fill_pct >= 100.0:
            return BinState.TRANSBORDO
        elif self.fill_pct >= 85.0:
            return BinState.CRITICA
        elif self.fill_pct >= 70.0:
            return BinState.ALTA
        elif self.fill_pct >= 50.0:
            return BinState.ATENCAO
        else:
            return BinState.NORMAL

    def add_waste(self, kg: float):
        added_pct = (kg / self.max_capacity_kg) * 100.0
        self.fill_pct = min(120.0, self.fill_pct + added_pct)

    def collect(self, truck_available_capacity_kg: float) -> float:
        """
        Esvazia a lixeira até o limite disponível no caminhão.
        Retorna a quantidade de kg efetivamente coletada.
        """
        waste_to_collect = min(self.current_waste_kg, truck_available_capacity_kg)
        remaining_waste_kg = max(0.0, self.current_waste_kg - waste_to_collect)
        
        # Reduz nível para o residual configurável (ex: ~2% residual de parede)
        self.fill_pct = max(2.0, (remaining_waste_kg / self.max_capacity_kg) * 100.0)
        return waste_to_collect

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ra': self.ra,
            'node_id': self.node_id,
            'bin_type': self.bin_type,
            'capacity_liters': self.capacity_liters,
            'fill_pct': round(self.fill_pct, 1),
            'current_waste_kg': round(self.current_waste_kg, 1),
            'state': self.state.value,
            'battery_pct': round(self.sensor_battery, 1),
            'temperature_c': round(self.temperature_c, 1)
        }
