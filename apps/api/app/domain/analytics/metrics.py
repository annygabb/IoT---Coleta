from typing import Dict, Any

class EconomicEnvironmentalMetrics:
    """
    Motor analítico de Custo-Benefício e ROI Simulado (Cap. 18).
    Calcula custos monetários configuráveis, consumo de combustível diesel,
    emissões de CO2 e ganhos em relação ao Baseline tradicional.
    """
    def __init__(
        self,
        custo_km: float = 3.50,          # R$ 3,50 por km rodado
        custo_hora: float = 45.00,        # R$ 45,00 por hora de equipe/motorista
        preco_diesel_litro: float = 6.20, # R$ 6,20 por litro de diesel S10
        custo_viagem_aterro: float = 85.00,# Taxa operacional de transbordo/aterro
        penalidade_transbordo: float = 25.0 # Multa/custo sanitário por ocorrência de lixeira transbordada
    ):
        self.custo_km = custo_km
        self.custo_hora = custo_hora
        self.preco_diesel_litro = preco_diesel_litro
        self.custo_viagem_aterro = custo_viagem_aterro
        self.penalidade_transbordo = penalidade_transbordo

        # Acumuladores
        self.smart_distance_km = 0.0
        self.smart_operating_hours = 0.0
        self.smart_diesel_liters = 0.0
        self.smart_disposal_trips = 0
        self.smart_overflow_count = 0
        self.smart_collected_waste_kg = 0.0

        # Baseline comparativo
        self.baseline_distance_km = 0.0
        self.baseline_operating_hours = 0.0
        self.baseline_diesel_liters = 0.0
        self.baseline_disposal_trips = 0
        self.baseline_overflow_count = 0

    def update_smart_metrics(
        self,
        delta_distance_km: float,
        delta_hours: float,
        delta_diesel: float,
        delta_disposals: int,
        delta_collected_kg: float,
        current_overflows: int
    ):
        self.smart_distance_km += delta_distance_km
        self.smart_operating_hours += delta_hours
        self.smart_diesel_liters += delta_diesel
        self.smart_disposal_trips += delta_disposals
        self.smart_collected_waste_kg += delta_collected_kg
        self.smart_overflow_count = current_overflows

        # Estimativa de Baseline tradicional (rota fixa percorre tipicamente ~60% mais distância e tem mais transbordos)
        self.baseline_distance_km += delta_distance_km * 1.58
        self.baseline_operating_hours += delta_hours * 1.45
        self.baseline_diesel_liters += delta_diesel * 1.62
        self.baseline_disposal_trips += delta_disposals
        self.baseline_overflow_count += int(current_overflows * 1.5)

    def calculate_cost(self, distance_km: float, hours: float, diesel_liters: float, trips: int, overflows: int) -> float:
        """Fórmula do Cap. 18.2"""
        return (
            (distance_km * self.custo_km) +
            (hours * self.custo_hora) +
            (diesel_liters * self.preco_diesel_litro) +
            (trips * self.custo_viagem_aterro) +
            (overflows * self.penalidade_transbordo)
        )

    def get_summary(self) -> Dict[str, Any]:
        cost_smart = self.calculate_cost(
            self.smart_distance_km,
            self.smart_operating_hours,
            self.smart_diesel_liters,
            self.smart_disposal_trips,
            self.smart_overflow_count
        )
        cost_baseline = self.calculate_cost(
            self.baseline_distance_km,
            self.baseline_operating_hours,
            self.baseline_diesel_liters,
            self.baseline_disposal_trips,
            self.baseline_overflow_count
        )

        economy_brl = max(0.0, cost_baseline - cost_smart)
        economy_pct = (economy_brl / cost_baseline * 100.0) if cost_baseline > 0 else 0.0

        co2_smart_kg = self.smart_diesel_liters * 2.68
        co2_baseline_kg = self.baseline_diesel_liters * 2.68
        co2_avoided_kg = max(0.0, co2_baseline_kg - co2_smart_kg)

        return {
            'cost_smart_brl': round(cost_smart, 2),
            'cost_baseline_brl': round(cost_baseline, 2),
            'economy_brl': round(economy_brl, 2),
            'economy_pct': round(economy_pct, 1),
            'distance_smart_km': round(self.smart_distance_km, 1),
            'distance_saved_km': round(max(0.0, self.baseline_distance_km - self.smart_distance_km), 1),
            'diesel_saved_liters': round(max(0.0, self.baseline_diesel_liters - self.smart_diesel_liters), 1),
            'co2_avoided_kg': round(co2_avoided_kg, 1),
            'overflows_current': self.smart_overflow_count,
            'total_collected_kg': round(self.smart_collected_waste_kg, 1)
        }
