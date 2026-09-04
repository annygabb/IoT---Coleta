from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SensorStatus(str, Enum):
    ONLINE = "ONLINE"
    STALE = "STALE"
    OFFLINE = "OFFLINE"
    FAULTY = "FAULTY"

class BinState(str, Enum):
    NORMAL = "NORMAL"         # 0 - 49%
    ATENCAO = "ATENCAO"       # 50 - 69%
    ALTA = "ALTA"             # 70 - 84%
    CRITICA = "CRITICA"       # 85 - 99%
    TRANSBORDO = "TRANSBORDO" # >= 100%
    EM_COLETA = "EM_COLETA"

class TruckState(str, Enum):
    OCIOSO = "OCIOSO"
    DESPACHADO = "DESPACHADO"
    EM_ROTA = "EM_ROTA"
    COLETANDO = "COLETANDO"
    CHEIO = "CHEIO"
    INDO_DESCARTE = "INDO_DESCARTE"
    DESCARREGANDO = "DESCARREGANDO"

class RoutingStrategyType(str, Enum):
    FIXED_BASELINE = "FIXED"
    NEAREST_PRIORITY = "NEAREST"
    VRP_SMART = "VRP_SMART"

class WeatherType(str, Enum):
    SECO = "SECO"
    CHUVA_LEVE = "CHUVA_LEVE"
    CHUVA_FORTE = "CHUVA_FORTE"
    TEMPESTADE = "TEMPESTADE"

# Telemetria emitida pelo sensor (Cap. 6.3)
class SensorTelemetryPayload(BaseModel):
    schema_version: str = "1.0"
    event_id: str
    sensor_id: str
    bin_id: str
    sim_time: str
    fill_pct: float = Field(ge=0.0, description="Percentual de ocupação (0 a >100%)")
    distance_cm: float = Field(ge=0.0, description="Distância medida pelo sensor ultrassônico")
    temperature_c: float = Field(description="Temperatura interna em graus Celsius")
    battery_pct: float = Field(ge=0.0, le=100.0, description="Percentual de bateria")
    signal_quality: int = Field(ge=0, le=100, description="Qualidade do sinal de rede (0 a 100)")
    status: SensorStatus = SensorStatus.ONLINE
    lat: float
    lon: float

# Alerta Operacional (Cap. 4.1 RF-012)
class OperationalAlert(BaseModel):
    schema_version: str = "1.0"
    alert_id: str
    sim_time: str
    bin_id: str
    region: str
    fill_pct: float
    severity: str # WARNING, CRITICAL, OVERFLOW
    message: str

# Comando enviado ao atuador do caminhão (Cap. 13.3)
class TruckCommand(BaseModel):
    schema_version: str = "1.0"
    command_id: str = Field(description="Identificador único para garantia de idempotência")
    correlation_id: str
    truck_id: str
    action: str # ASSIGN_ROUTE, COLLECT_BIN, GO_TO_DISPOSAL, STOP
    target_node: str
    target_bin_id: Optional[str] = None
    route_sequence: List[str] = []
    issued_sim_time: str

# Confirmação de execução do atuador (Cap. 13.2)
class ActuatorAcknowledgement(BaseModel):
    schema_version: str = "1.0"
    ack_id: str
    command_id: str
    truck_id: str
    status: str # SUCCESS, IN_PROGRESS, REJECTED
    executed_sim_time: str
    details: Dict[str, Any] = {}

# Decisão de Roteamento (Cap. 15 / DoD-18)
class RoutingDecisionLog(BaseModel):
    schema_version: str = "1.0"
    decision_id: str
    sim_time: str
    strategy: RoutingStrategyType
    truck_id: str
    target_bin_id: Optional[str]
    reason: str
    factors: Dict[str, Any] = {}
