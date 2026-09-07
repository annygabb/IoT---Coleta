from apps.api.app.domain.fleet.truck import CollectionTruck
from apps.api.app.domain.routing.dijkstra import DijkstraRouter
from apps.api.app.domain.routing.strategies import (
    FixedBaselineStrategy,
    NearestPriorityStrategy,
    SmartVRPStrategy,
)
from apps.api.app.domain.waste.bin import SmartBin


def make_bin(bin_id: str, node_id: str, fill_pct: float, capacity_liters: float = 1000.0):
    return SmartBin(
        bin_id=bin_id,
        name=f"Teste {bin_id}",
        ra="Teste",
        node_id=node_id,
        capacity_liters=capacity_liters,
        initial_fill_pct=fill_pct,
        generation_rate=1.0,
    )


def make_truck(truck_id: str = "TR-T", node_id: str = "GARAGEM_SLU"):
    return CollectionTruck(
        truck_id=truck_id,
        name=truck_id,
        color="#000000",
        capacity_kg=5000.0,
        initial_node=node_id,
    )


def test_fixed_route_is_cyclic_and_does_not_use_fill_threshold():
    strategy = FixedBaselineStrategy()
    router = DijkstraRouter()
    truck = make_truck()
    bins = [
        make_bin("BIN-01", "GARAGEM_SLU", 2.0),
        make_bin("BIN-02", "TAGUA_CENTRO", 90.0),
        make_bin("BIN-03", "AGUAS_CLARAS", 50.0),
    ]

    first, _ = strategy.select_next_bin(truck, bins, [truck], router)
    second, _ = strategy.select_next_bin(truck, bins, [truck], router)
    third, _ = strategy.select_next_bin(truck, bins, [truck], router)
    fourth, _ = strategy.select_next_bin(truck, bins, [truck], router)

    assert [first.id, second.id, third.id, fourth.id] == [
        "BIN-01",
        "BIN-02",
        "BIN-03",
        "BIN-01",
    ]


def test_fixed_route_skips_bin_targeted_by_another_truck():
    strategy = FixedBaselineStrategy()
    router = DijkstraRouter()
    truck = make_truck("TR-A")
    other = make_truck("TR-B")
    other.target_bin_id = "BIN-01"
    bins = [
        make_bin("BIN-01", "GARAGEM_SLU", 50.0),
        make_bin("BIN-02", "TAGUA_CENTRO", 50.0),
    ]

    chosen, _ = strategy.select_next_bin(truck, bins, [truck, other], router)

    assert chosen.id == "BIN-02"


def test_nearest_requires_minimum_twenty_percent_fill():
    strategy = NearestPriorityStrategy()
    router = DijkstraRouter()
    truck = make_truck(node_id="GARAGEM_SLU")
    bins = [
        make_bin("BIN-01", "GARAGEM_SLU", 19.0),
        make_bin("BIN-02", "GUARA_CENTRO", 25.0),
    ]

    chosen, reason = strategy.select_next_bin(truck, bins, [truck], router)

    assert chosen.id == "BIN-02"
    assert "menor distância" in reason


def test_smart_vrp_requires_twenty_five_percent_and_reports_score():
    strategy = SmartVRPStrategy()
    router = DijkstraRouter()
    truck = make_truck(node_id="GARAGEM_SLU")
    bins = [
        make_bin("BIN-01", "GARAGEM_SLU", 24.0),
        make_bin("BIN-02", "GUARA_CENTRO", 30.0),
    ]

    chosen, reason = strategy.select_next_bin(truck, bins, [truck], router)

    assert chosen.id == "BIN-02"
    assert "score" in reason.lower()
