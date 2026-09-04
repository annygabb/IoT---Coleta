import uuid
from typing import List, Dict, Any, Optional
from apps.api.app.domain.simulation.clock import SimulationClock
from apps.api.app.domain.simulation.prng import DeterministicPRNG
from apps.api.app.domain.geo.brasilia_network import BRASILIA_NODES, BRASILIA_ROADS
from apps.api.app.domain.routing.dijkstra import DijkstraRouter
from apps.api.app.domain.waste.bin import SmartBin
from apps.api.app.domain.fleet.truck import CollectionTruck
from apps.api.app.domain.routing.strategies import (
    BaseRoutingStrategy, FixedBaselineStrategy, NearestPriorityStrategy, SmartVRPStrategy
)
from apps.api.app.domain.iot.broker import VirtualMQTTBroker
from apps.api.app.domain.decisions.explainer import DecisionExplainer
from apps.api.app.domain.analytics.metrics import EconomicEnvironmentalMetrics
from apps.api.app.domain.iot.contracts import (
    SensorStatus, BinState, TruckState, RoutingStrategyType, WeatherType
)

class SimulationEngine:
    """
    Motor Central de Simulação e Orquestração do SmartWaste DF.
    Desacoplado do relógio da interface, orientado a eventos e determinístico por seed (RF-002, RNF-008).
    """
    def __init__(self, seed: int = 20260903):
        self.seed = seed
        self.prng = DeterministicPRNG(seed)
        self.clock = SimulationClock(start_seconds=8 * 3600) # Inicia às 08:00
        self.router = DijkstraRouter()
        self.broker = VirtualMQTTBroker()
        self.explainer = DecisionExplainer()
        self.metrics = EconomicEnvironmentalMetrics()

        self.strategy_type = RoutingStrategyType.VRP_SMART
        self.strategy_map: Dict[RoutingStrategyType, BaseRoutingStrategy] = {
            RoutingStrategyType.FIXED_BASELINE: FixedBaselineStrategy(),
            RoutingStrategyType.NEAREST_PRIORITY: NearestPriorityStrategy(),
            RoutingStrategyType.VRP_SMART: SmartVRPStrategy()
        }

        self.weather = WeatherType.SECO
        self.weather_speed_factor = 1.0
        self.waste_rate_multiplier = 1.0

        self.bins: List[SmartBin] = []
        self.trucks: List[CollectionTruck] = []
        
        self._initialize_entities()

    def _initialize_entities(self):
        # 32 Lixeiras Inteligentes distribuídas em Brasília (Cap. 12)
        initial_configs = [
            ("BIN-01", "Torre de TV Feira", "Plano Piloto", "TORRE_TV", "Turístico", 1200, 45, 1.2),
            ("BIN-02", "Rodoviária Plataforma Sup.", "Plano Piloto", "RODOVIARIA_PLANO", "Comercial", 2000, 82, 2.2),
            ("BIN-03", "Rodoviária Piso Inf.", "Plano Piloto", "RODOVIARIA_PLANO", "Comercial", 2000, 75, 2.0),
            ("BIN-04", "Esplanada Bloco C", "Plano Piloto", "ESPLANADA", "Governamental", 1000, 35, 0.8),
            ("BIN-05", "Praça dos Três Poderes", "Plano Piloto", "CONGRESSO", "Turístico", 1200, 50, 1.1),
            ("BIN-06", "CLN 108 Norte Comércio", "Plano Piloto", "ASA_NORTE_100", "Comercial", 1000, 68, 1.3),
            ("BIN-07", "SQN 305 Norte Residencial", "Plano Piloto", "ASA_NORTE_100", "Residencial", 800, 30, 0.6),
            ("BIN-08", "CLN 412 Norte Gastronomia", "Plano Piloto", "ASA_NORTE_400", "Comercial", 1500, 79, 1.6),
            ("BIN-09", "Parque Olhos D’Água", "Plano Piloto", "ASA_NORTE_FIM", "Parque", 1000, 40, 0.9),
            ("BIN-10", "CLS 104 Sul Restaurantes", "Plano Piloto", "ASA_SUL_100", "Comercial", 1500, 75, 1.7),
            ("BIN-11", "SQS 308 Sul Residencial", "Plano Piloto", "ASA_SUL_100", "Residencial", 800, 22, 0.5),
            ("BIN-12", "CLS 405 Sul Gastronomia", "Plano Piloto", "ASA_SUL_400", "Comercial", 1500, 88, 1.9),
            ("BIN-13", "Estação Metro 114 Sul", "Plano Piloto", "ASA_SUL_400", "Comercial", 1200, 62, 1.3),
            ("BIN-14", "Pontão do Lago Sul", "Lago Sul", "PONTE_COSTA_SILVA", "Turístico", 1500, 86, 1.8),
            ("BIN-15", "Orla da Ponte JK", "Lago Sul", "PONTE_JK", "Turístico", 1200, 78, 1.5),
            ("BIN-16", "QI 09 Lago Sul Comercial", "Lago Sul", "LAGO_SUL", "Comercial", 1000, 38, 0.8),
            ("BIN-17", "Deck Norte / Shopping", "Lago Norte", "LAGO_NORTE", "Comercial", 1200, 54, 1.0),
            ("BIN-18", "Terraço Shopping Octogonal", "Sudoeste", "SUDOESTE", "Comercial", 1500, 65, 1.4),
            ("BIN-19", "CLSW 301 Sudoeste", "Sudoeste", "SUDOESTE", "Residencial", 1000, 48, 0.9),
            ("BIN-20", "Feira do Guará", "Guará", "GUARA_CENTRO", "Comercial", 2000, 91, 2.3),
            ("BIN-21", "Pólo de Moda Guará II", "Guará", "GUARA_CENTRO", "Comercial", 1000, 42, 0.9),
            ("BIN-22", "Parque Águas Claras", "Águas Claras", "AGUAS_CLARAS", "Parque", 1200, 70, 1.4),
            ("BIN-23", "Estação Águas Claras Metrô", "Águas Claras", "AGUAS_CLARAS", "Comercial", 1800, 84, 2.1),
            ("BIN-24", "Praça do Relógio Taguatinga", "Taguatinga", "TAGUA_CENTRO", "Comercial", 2000, 89, 2.4),
            ("BIN-25", "Taguatinga Shopping", "Taguatinga", "TAGUA_SUL", "Comercial", 2000, 74, 1.8),
            ("BIN-26", "Taguaparque Norte", "Taguatinga", "TAGUA_NORTE", "Parque", 1200, 35, 0.7),
            ("BIN-27", "Pistão Sul Comercial", "Taguatinga", "TAGUA_SUL", "Comercial", 1500, 66, 1.3),
            ("BIN-28", "Feira Central Ceilândia", "Ceilândia", "CEILANDIA_CENTRO", "Comercial", 2500, 93, 2.6),
            ("BIN-29", "Estação Ceilândia Centro", "Ceilândia", "CEILANDIA_CENTRO", "Comercial", 1800, 72, 1.7),
            ("BIN-30", "P-Norte Ceilândia", "Ceilândia", "CEILANDIA_NORTE", "Residencial", 1200, 50, 1.0),
            ("BIN-31", "Guariroba QNN 18", "Ceilândia", "CEILANDIA_SUL", "Residencial", 1000, 41, 0.8),
            ("BIN-32", "Samambaia Norte Quadra 400", "Samambaia", "SAMAMBAIA_NORTE", "Residencial", 1200, 58, 1.1)
        ]

        self.bins = [
            SmartBin(
                bin_id=cfg[0],
                name=cfg[1],
                ra=cfg[2],
                node_id=cfg[3],
                bin_type=cfg[4],
                capacity_liters=cfg[5],
                initial_fill_pct=cfg[6],
                generation_rate=cfg[7]
            )
            for cfg in initial_configs
        ]

        # 3 Caminhões Coletores do SLU
        self.trucks = [
            CollectionTruck("TR-01", "SLU Asa Express (TR-01)", "#10b981", 5000.0, "GARAGEM_SLU", 45.0),
            CollectionTruck("TR-02", "SLU Águas/Taguatinga (TR-02)", "#06b6d4", 5000.0, "TAGUA_CENTRO", 42.0),
            CollectionTruck("TR-03", "SLU Ceilândia/Oeste (TR-03)", "#f59e0b", 5000.0, "CEILANDIA_CENTRO", 40.0)
        ]

    def set_weather(self, weather: WeatherType):
        self.weather = weather
        if weather == WeatherType.SECO:
            self.weather_speed_factor = 1.0
        elif weather == WeatherType.CHUVA_LEVE:
            self.weather_speed_factor = 0.95
        elif weather == WeatherType.CHUVA_FORTE:
            self.weather_speed_factor = 0.70
        elif weather == WeatherType.TEMPESTADE:
            self.weather_speed_factor = 0.50

        self.broker.publish("smartwaste/df/environment/weather", {
            "sim_time": self.clock.get_iso_sim_time(),
            "weather": weather.value,
            "speed_factor": self.weather_speed_factor
        })

    def set_eptg_blocked(self, blocked: bool):
        self.router.set_eptg_blocked(blocked)
        self.broker.publish("smartwaste/df/environment/traffic", {
            "sim_time": self.clock.get_iso_sim_time(),
            "road": "EPTG_DF_085",
            "blocked": blocked
        })
        # Força recálculo para caminhões em rota
        for t in self.trucks:
            if t.state == TruckState.EM_ROTA and t.target_node:
                new_path, _ = self.router.find_shortest_path(t.current_node, t.target_node)
                t.path = new_path
                t.path_progress = 0.0

    def force_critical_bin(self, bin_id: Optional[str] = None) -> SmartBin:
        target = None
        if bin_id:
            target = next((b for b in self.bins if b.id == bin_id), None)
        if not target:
            target = next((b for b in self.bins if b.fill_pct < 85.0), self.bins[0])

        target.fill_pct = 95.0
        self.broker.publish("smartwaste/df/alerts", {
            "alert_id": f"ALT-{uuid.uuid4().hex[:6].upper()}",
            "sim_time": self.clock.get_iso_sim_time(),
            "bin_id": target.id,
            "region": target.ra,
            "fill_pct": target.fill_pct,
            "severity": "CRITICAL",
            "message": f"Lixeira {target.id} ({target.name}) atingiu nível crítico de 95%."
        })
        self._dispatch_trucks_if_needed()
        return target

    def _dispatch_trucks_if_needed(self):
        strategy = self.strategy_map[self.strategy_type]
        hour = (self.clock.sim_time_seconds / 3600) % 24
        is_peak = (7.5 <= hour <= 9.5) or (17.5 <= hour <= 19.5)

        for truck in self.trucks:
            # Se caminhão estiver ocioso ou livre, avalia próximo destino
            if truck.state == TruckState.OCIOSO:
                # Se caminhão estiver com carga >= 90%, obrigatoriamente vai ao Aterro
                if truck.is_full:
                    truck.state = TruckState.INDO_DESCARTE
                    truck.target_node = "ATERRO_SAMAMBAIA"
                    truck.target_bin_id = None
                    path, _ = self.router.find_shortest_path(truck.current_node, "ATERRO_SAMAMBAIA", is_peak)
                    truck.path = path
                    truck.path_progress = 0.0

                    reason = f"Caminhão com carga de {truck.load_kg:.0f} kg ({truck.load_kg/truck.capacity_kg*100:.0f}%). Desvio obrigatório para o Aterro Sanitário Samambaia."
                    self.explainer.record_decision(
                        self.clock.get_iso_sim_time(),
                        self.strategy_type,
                        truck.id,
                        None,
                        reason,
                        {"load_kg": truck.load_kg, "capacity_kg": truck.capacity_kg}
                    )

                    # Publica comando idempotente MQTT
                    cmd_id = f"CMD-{uuid.uuid4().hex[:8].upper()}"
                    self.broker.publish(f"smartwaste/df/trucks/{truck.id}/commands", {
                        "command_id": cmd_id,
                        "action": "GO_TO_DISPOSAL",
                        "target_node": "ATERRO_SAMAMBAIA",
                        "truck_id": truck.id,
                        "issued_sim_time": self.clock.get_iso_sim_time()
                    })
                    continue

                # Seleciona próxima lixeira pela estratégia ativa
                chosen_bin, justification = strategy.select_next_bin(
                    truck, self.bins, self.trucks, self.router, is_peak
                )

                if chosen_bin:
                    path, _ = self.router.find_shortest_path(truck.current_node, chosen_bin.node_id, is_peak)
                    truck.assign_route(path, chosen_bin.id, chosen_bin.node_id)
                    
                    self.explainer.record_decision(
                        self.clock.get_iso_sim_time(),
                        self.strategy_type,
                        truck.id,
                        chosen_bin.id,
                        justification,
                        {"fill_pct": chosen_bin.fill_pct, "bin_ra": chosen_bin.ra}
                    )

                    cmd_id = f"CMD-{uuid.uuid4().hex[:8].upper()}"
                    self.broker.publish(f"smartwaste/df/trucks/{truck.id}/commands", {
                        "command_id": cmd_id,
                        "action": "ASSIGN_ROUTE",
                        "target_bin_id": chosen_bin.id,
                        "target_node": chosen_bin.node_id,
                        "truck_id": truck.id,
                        "issued_sim_time": self.clock.get_iso_sim_time()
                    })

    def step(self, delta_wall_seconds: float):
        """Executa um passo de simulação discreto ordenado no tempo."""
        delta_sim_seconds = self.clock.tick(delta_wall_seconds)
        if delta_sim_seconds <= 0.0:
            return

        sim_hours = delta_sim_seconds / 3600.0
        hour_of_day = (self.clock.sim_time_seconds / 3600) % 24

        # Fator diurno de geração de lixo (Cap. 11.3)
        time_factor = 1.0
        if 7.0 <= hour_of_day <= 9.0 or 18.0 <= hour_of_day <= 21.0:
            time_factor = 1.7 # Pico residencial
        elif 12.0 <= hour_of_day <= 14.0:
            time_factor = 1.9 # Pico comercial
        elif 1.0 <= hour_of_day <= 5.0:
            time_factor = 0.2 # Madrugada

        # 1. Atualização das Lixeiras
        current_overflows = 0
        for b in self.bins:
            noise = 0.85 + self.prng.uniform(0.0, 0.3)
            added_kg = b.generation_rate * time_factor * self.weather_speed_factor * self.waste_rate_multiplier * noise * (delta_sim_seconds / 60.0)
            b.add_waste(added_kg)
            b.temperature_c = 25.0 + (hour_of_day / 4.0)
            b.sensor_battery = max(10.0, b.sensor_battery - (0.00002 * delta_sim_seconds))

            if b.fill_pct >= 100.0:
                current_overflows += 1

            # Emite telemetria periódica MQTT com probabilidade proporcional
            if self.prng.random() < (0.015 * (delta_sim_seconds / 5.0)):
                self.broker.publish(f"smartwaste/df/bins/{b.id}/telemetry", {
                    "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
                    "bin_id": b.id,
                    "sim_time": self.clock.get_iso_sim_time(),
                    "fill_pct": round(b.fill_pct, 1),
                    "distance_cm": round((1.0 - (min(100.0, b.fill_pct) / 100.0)) * 120.0, 1),
                    "temperature_c": round(b.temperature_c, 1),
                    "battery_pct": round(b.sensor_battery, 1),
                    "status": "TRANSBORDO" if b.fill_pct >= 100 else ("CRITICA" if b.fill_pct >= 85 else "ONLINE")
                })

        # 2. Atualização dos Caminhões
        delta_distance_total = 0.0
        delta_diesel_total = 0.0
        delta_disposals_total = 0
        delta_collected_total = 0.0

        for truck in self.trucks:
            effective_speed_kmh = truck.base_speed_kmh * self.weather_speed_factor
            if self.router.is_eptg_blocked():
                effective_speed_kmh *= 0.85

            if truck.state in (TruckState.EM_ROTA, TruckState.INDO_DESCARTE):
                if not truck.path or len(truck.path) <= 1:
                    # Chegou ao nó de destino
                    if truck.state == TruckState.INDO_DESCARTE and truck.current_node == "ATERRO_SAMAMBAIA":
                        truck.start_disposal(duration_s=25.0)
                    elif truck.target_bin_id:
                        target_bin = next((b for b in self.bins if b.id == truck.target_bin_id), None)
                        if target_bin and truck.current_node == target_bin.node_id:
                            truck.start_collection(duration_s=15.0)
                        else:
                            truck.state = TruckState.OCIOSO
                    else:
                        truck.state = TruckState.OCIOSO
                else:
                    # Deslocamento no segmento
                    curr_node_key = truck.path[0]
                    next_node_key = truck.path[1]
                    # Distância do segmento aproximada (km)
                    _, seg_km = self.router.find_shortest_path(curr_node_key, next_node_key)
                    seg_km = max(1.0, seg_km)

                    # Avanço do caminhão no tempo simulado
                    step_km = (effective_speed_kmh * sim_hours)
                    step_km = min(step_km, seg_km)
                    truck.path_progress += (step_km / seg_km)

                    fuel_used = truck.calculate_fuel(step_km, self.weather_speed_factor, 1.0)
                    truck.total_distance_km += step_km
                    delta_distance_total += step_km
                    delta_diesel_total += fuel_used

                    if truck.path_progress >= 1.0:
                        truck.current_node = next_node_key
                        truck.path.pop(0)
                        truck.path_progress = 0.0

            elif truck.state == TruckState.COLETANDO:
                truck.operation_timer_seconds -= delta_sim_seconds
                if truck.operation_timer_seconds <= 0.0:
                    target_bin = next((b for b in self.bins if b.id == truck.target_bin_id), None)
                    if target_bin:
                        collected_kg = target_bin.collect(truck.available_capacity_kg)
                        truck.complete_collection(collected_kg)
                        delta_collected_total += collected_kg

                        # Emite ACK de coleta
                        self.broker.publish(f"smartwaste/df/trucks/{truck.id}/acks", {
                            "ack_id": f"ACK-{uuid.uuid4().hex[:6].upper()}",
                            "truck_id": truck.id,
                            "bin_id": target_bin.id,
                            "collected_kg": round(collected_kg, 1),
                            "residual_fill_pct": round(target_bin.fill_pct, 1),
                            "sim_time": self.clock.get_iso_sim_time(),
                            "status": "COLLECTED"
                        })
                    else:
                        truck.state = TruckState.OCIOSO

            elif truck.state == TruckState.DESCARREGANDO:
                truck.operation_timer_seconds -= delta_sim_seconds
                if truck.operation_timer_seconds <= 0.0:
                    unloaded_kg = truck.complete_disposal()
                    delta_disposals_total += 1

                    self.broker.publish(f"smartwaste/df/trucks/{truck.id}/acks", {
                        "ack_id": f"ACK-{uuid.uuid4().hex[:6].upper()}",
                        "truck_id": truck.id,
                        "location": "ATERRO_SAMAMBAIA",
                        "unloaded_kg": round(unloaded_kg, 1),
                        "sim_time": self.clock.get_iso_sim_time(),
                        "status": "DISCHARGED"
                    })

        # 3. Atualização das Métricas Globais
        self.metrics.update_smart_metrics(
            delta_distance_km=delta_distance_total,
            delta_hours=sim_hours,
            delta_diesel=delta_diesel_total,
            delta_disposals=delta_disposals_total,
            delta_collected_kg=delta_collected_total,
            current_overflows=current_overflows
        )

        # 4. Avaliação contínua de despacho de caminhões
        self._dispatch_trucks_if_needed()

    def get_full_state(self) -> Dict[str, Any]:
        """Retorna o estado serializável completo da simulação para REST ou WebSocket."""
        return {
            'sim_time': self.clock.get_time_string(),
            'sim_iso': self.clock.get_iso_sim_time(),
            'sim_day': self.clock.sim_day,
            'is_paused': self.clock.is_paused,
            'speed': self.clock.speed_multiplier,
            'strategy': self.strategy_type.value,
            'weather': self.weather.value,
            'eptg_blocked': self.router.is_eptg_blocked(),
            'latest_decision': self.explainer.get_latest_decision_text(),
            'metrics': self.metrics.get_summary(),
            'bins': [b.to_dict() for b in self.bins],
            'trucks': [t.to_dict() for t in self.trucks],
            'recent_mqtt_messages': self.broker.get_recent_messages(limit=10)
        }
