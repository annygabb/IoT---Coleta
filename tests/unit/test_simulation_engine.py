import pytest
from apps.api.app.domain.simulation.prng import DeterministicPRNG
from apps.api.app.domain.simulation.clock import SimulationClock
from apps.api.app.domain.routing.dijkstra import DijkstraRouter
from apps.api.app.domain.waste.bin import SmartBin
from apps.api.app.domain.iot.contracts import BinState

def test_deterministic_prng_reproducibility():
    prng1 = DeterministicPRNG(seed=20260903)
    prng2 = DeterministicPRNG(seed=20260903)

    seq1 = [prng1.random() for _ in range(50)]
    seq2 = [prng2.random() for _ in range(50)]

    assert seq1 == seq2, "Mesma seed deve produzir exatamente a mesma sequência de números aleatórios (DoD-11)"

def test_simulation_clock_speed():
    clock = SimulationClock(start_seconds=0)
    clock.set_speed(60.0) # 1 segundo real = 60 segundos simulados
    delta_sim = clock.tick(delta_wall_seconds=2.0)
    assert delta_sim == 120.0
    assert clock.sim_time_seconds == 120.0
    assert clock.get_time_string() == "00:02:00"

def test_smart_bin_state_transitions():
    bin_obj = SmartBin(
        bin_id="TEST-BIN",
        name="Lixeira Teste",
        ra="Plano Piloto",
        node_id="TORRE_TV",
        capacity_liters=1000.0,
        initial_fill_pct=40.0
    )
    assert bin_obj.state == BinState.NORMAL

    bin_obj.fill_pct = 55.0
    assert bin_obj.state == BinState.ATENCAO

    bin_obj.fill_pct = 75.0
    assert bin_obj.state == BinState.ALTA

    bin_obj.fill_pct = 88.0
    assert bin_obj.state == BinState.CRITICA

    bin_obj.fill_pct = 105.0
    assert bin_obj.state == BinState.TRANSBORDO

def test_dijkstra_reroutes_when_eptg_is_blocked():
    router = DijkstraRouter()
    path_normal, dist_normal = router.find_shortest_path("TAGUA_CENTRO", "GARAGEM_SLU")
    assert "AGUAS_CLARAS" in path_normal

    # Bloqueia EPTG
    router.set_eptg_blocked(True)
    path_blocked, dist_blocked = router.find_shortest_path("TAGUA_CENTRO", "GARAGEM_SLU")

    # A rota deve desviar (ex: via EPNB ou Estrutural) e percorrer uma distância maior
    assert path_blocked != path_normal, "Bloqueio da EPTG deve forçar desvio de rota viária (DoD-09)"
    assert dist_blocked >= dist_normal
