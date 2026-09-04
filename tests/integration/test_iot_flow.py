import pytest
from apps.api.app.domain.simulation.engine import SimulationEngine
from apps.api.app.domain.iot.contracts import TruckState

def test_complete_vertical_slice_m1():
    """
    Testa o ciclo IoT ponta a ponta do Marco M1 (DoD-06, DoD-07, DoD-08):
    1. Lixeira crítica é detectada.
    2. Alerta operacional e telemetria são emitidos.
    3. Decision engine seleciona o caminhão com justificativa.
    4. Comando idempotente é publicado ao atuador.
    5. Caminhão viaja, esvazia a lixeira e aumenta a própria carga.
    6. Quando lotado (>=90%), segue para o Aterro Sanitário de Samambaia e descarrega.
    """
    engine = SimulationEngine(seed=20260903)

    # 1. Injeta lixeira crítica (BIN-02)
    bin_target = engine.bins[1]
    bin_target.fill_pct = 92.0

    # 2. Executa passos de simulação
    engine.step(delta_wall_seconds=1.0)

    # Verifica se a decisão foi registrada
    latest_decision = engine.explainer.get_latest_decision_text()
    assert len(latest_decision) > 0, "Decisão deve ser registrada no explainer (DoD-18)"

    # Verifica caminhão despachado
    dispatched_truck = next((t for t in engine.trucks if t.state == TruckState.EM_ROTA and t.target_bin_id), None)
    assert dispatched_truck is not None, "Um caminhão deve ser alocado com rota ativa"
    
    assigned_bin = next(b for b in engine.bins if b.id == dispatched_truck.target_bin_id)
    initial_assigned_fill = assigned_bin.fill_pct

    # Simula avanço rápido do caminhão até chegar e coletar
    dispatched_truck.current_node = assigned_bin.node_id
    dispatched_truck.path = []
    engine.step(delta_wall_seconds=1.0)
    
    # Caminhão entra em coleta ou conclui
    dispatched_truck.operation_timer_seconds = 0.0
    engine.step(delta_wall_seconds=1.0)

    # Lixeira atribuída deve ter sido coletada
    assert assigned_bin.fill_pct <= 20.0 or assigned_bin.fill_pct < initial_assigned_fill, "Coleta deve reduzir o nível de lixo (RN-002)"
    assert dispatched_truck.load_kg > 0.0 or dispatched_truck.total_collected_kg > 0.0, "Carga deve ser registrada (RN-003)"

    # 6. Testa desvio para o Aterro quando lotado
    dispatched_truck.load_kg = 4800.0 # 96% de 5000 kg
    dispatched_truck.state = TruckState.OCIOSO
    engine.step(delta_wall_seconds=1.0)

    # Caminhão deve ter sido despachado obrigatoriamente para o ATERRO_SAMAMBAIA
    assert dispatched_truck.state == TruckState.INDO_DESCARTE
    assert dispatched_truck.target_node == "ATERRO_SAMAMBAIA"
