from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from apps.api.app.domain.simulation.engine import SimulationEngine
from apps.api.app.domain.iot.contracts import RoutingStrategyType, WeatherType

router = APIRouter()

# Instância Singleton do motor de simulação compartilhada no backend
_engine = SimulationEngine()

def get_engine() -> SimulationEngine:
    return _engine

@router.get("/health", summary="Verificação de Saúde do Serviço")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SmartWaste DF Modular Backend",
        "version": "2.6",
        "zero_cost": True
    }

@router.get("/ready", summary="Prontidão das Dependências")
def readiness_check():
    engine = get_engine()
    return {
        "status": "READY",
        "nodes_loaded": len(engine.bins),
        "trucks_active": len(engine.trucks),
        "db": "CONNECTED_SQLITE_LOCAL",
        "mqtt": "IN_MEMORY_BROKER_READY"
    }

@router.get("/api/v1/state", summary="Estado Completo da Simulação")
def get_current_state():
    return get_engine().get_full_state()

@router.post("/api/v1/scenarios/{scenario_id}/pause", summary="Pausar Simulação")
def pause_scenario(scenario_id: str):
    get_engine().clock.pause()
    return {"status": "PAUSED", "scenario_id": scenario_id}

@router.post("/api/v1/scenarios/{scenario_id}/resume", summary="Retomar Simulação")
def resume_scenario(scenario_id: str):
    get_engine().clock.resume()
    return {"status": "RUNNING", "scenario_id": scenario_id}

@router.post("/api/v1/scenarios/{scenario_id}/speed", summary="Alterar Velocidade do Relógio")
def set_scenario_speed(scenario_id: str, speed: float = Query(..., ge=0.0, le=1440.0)):
    get_engine().clock.set_speed(speed)
    return {"status": "SPEED_UPDATED", "speed": speed}

@router.post("/api/v1/scenarios/{scenario_id}/strategy", summary="Alterar Estratégia de Roteamento")
def change_strategy(scenario_id: str, strategy: RoutingStrategyType):
    engine = get_engine()
    engine.strategy_type = strategy
    engine._dispatch_trucks_if_needed()
    return {"status": "STRATEGY_UPDATED", "strategy": strategy.value}

@router.post("/api/v1/scenarios/{scenario_id}/weather", summary="Alterar Clima")
def change_weather(scenario_id: str, weather: WeatherType):
    engine = get_engine()
    engine.set_weather(weather)
    return {"status": "WEATHER_UPDATED", "weather": weather.value}

@router.post("/api/v1/roads/block", summary="Bloquear ou Desbloquear Via EPTG")
def toggle_road_block(blocked: bool = Query(...)):
    engine = get_engine()
    engine.set_eptg_blocked(blocked)
    return {"status": "ROAD_BLOCK_UPDATED", "road": "EPTG", "blocked": blocked}

@router.post("/api/v1/alerts/force-critical", summary="Forçar Lixeira Crítica (Teste de Estresse)")
def force_critical(bin_id: str = None):
    engine = get_engine()
    target_bin = engine.force_critical_bin(bin_id)
    return {"status": "CRITICAL_INJECTED", "bin": target_bin.to_dict()}

@router.get("/api/v1/export", summary="Exportar Snapshot de Dados em JSON")
def export_data():
    engine = get_engine()
    return {
        "metadata": {
            "application": "SmartWaste DF",
            "seed": engine.seed,
            "sim_time": engine.clock.get_iso_sim_time(),
            "strategy": engine.strategy_type.value
        },
        "metrics": engine.metrics.get_summary(),
        "trucks": [t.to_dict() for t in engine.trucks],
        "bins": [b.to_dict() for b in engine.bins]
    }
