import uuid
from typing import Dict, Any, Optional
from apps.api.app.domain.iot.contracts import RoutingDecisionLog, RoutingStrategyType

class DecisionExplainer:
    """
    Registrador e gerador de explicabilidade para decisões de despacho e replanejamento (RF-045, DoD-18).
    Permite auditar por que cada caminhão foi redirecionado.
    """
    def __init__(self):
        self.logs = []

    def record_decision(
        self,
        sim_time: str,
        strategy: RoutingStrategyType,
        truck_id: str,
        target_bin_id: Optional[str],
        reason: str,
        factors: Optional[Dict[str, Any]] = None
    ) -> RoutingDecisionLog:
        log_entry = RoutingDecisionLog(
            decision_id=f"DEC-{uuid.uuid4().hex[:8].upper()}",
            sim_time=sim_time,
            strategy=strategy,
            truck_id=truck_id,
            target_bin_id=target_bin_id,
            reason=reason,
            factors=factors or {}
        )
        self.logs.insert(0, log_entry)
        if len(self.logs) > 100:
            self.logs.pop()
        return log_entry

    def get_latest_decision_text(self) -> str:
        if self.logs:
            return f"[{self.logs[0].sim_time}] {self.logs[0].reason}"
        return "Sistema em prontidão operacional. Nenhuma decisão recente."
